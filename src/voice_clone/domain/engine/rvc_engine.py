import logging
import math
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np
import torch
import torch.nn.functional as F
from scipy.signal import medfilt
from torch import nn

from voice_clone.domain.engine.download import BaseModelPaths
from voice_clone.domain.engine.vendor.models import (
    SynthesizerTrnMs256NSFsid,
    SynthesizerTrnMs256NSFsid_nono,
    SynthesizerTrnMs768NSFsid,
    SynthesizerTrnMs768NSFsid_nono,
)
from voice_clone.domain.errors import ModelLoadError, ProfileError
from voice_clone.domain.profiles.discovery import VoiceProfile

logger = logging.getLogger(__name__)

INPUT_SAMPLE_RATE = 16000
MIN_SEMITONES = -12
MAX_SEMITONES = 12
F0_MIN_HZ = 50.0
F0_MAX_HZ = 1100.0
F0_MEL_MIN = 1127 * math.log(1 + F0_MIN_HZ / 700)
F0_MEL_MAX = 1127 * math.log(1 + F0_MAX_HZ / 700)
PITCH_HOP = 160
CONTENT_PAD = 320
INDEX_NEIGHBOURS = 8
V1_FEATURE_LAYER = 9
PITCH_FRAME_MS = 10
LOUDNESS_FRAME = 640
LOUDNESS_HOP = 160
LOUDNESS_FLOOR = 1e-3
DECODE_MARGIN_FRAMES = 10
RMVPE_THRESHOLD = 0.03
RMVPE_FRAME_MULTIPLE = 32


class ContentEncoder(Protocol):
    def encode(self, audio: torch.Tensor, version: str) -> torch.Tensor: ...


class PitchExtractor(Protocol):
    def extract(self, audio: np.ndarray) -> np.ndarray: ...


@dataclass
class _LoadedVoice:
    net_g: nn.Module
    target_rate: int
    version: str
    has_pitch: bool
    index_path: Path | None
    index: Any | None = None
    index_vectors: np.ndarray | None = None
    index_loaded: bool = False


class RvcEngine:
    index_rate: float = 0.5
    protect: float = 0.67
    loudness_follow: float = 0.5
    pitch_smoothing_ms: int = 30

    def __init__(
        self,
        base_models: BaseModelPaths,
        device: torch.device | None = None,
        content_encoder: ContentEncoder | None = None,
        pitch_extractor: PitchExtractor | None = None,
        cpu_threads: int = 0,
        precision: str = "auto",
    ) -> None:
        from voice_clone.domain.engine.device import use_half_precision

        self._base_models = base_models
        self._device = device if device is not None else _default_device()
        self._dtype = (
            torch.float16 if use_half_precision(self._device, precision) else torch.float32
        )
        if self._device.type == "cuda":
            torch.backends.cudnn.benchmark = True
        elif self._device.type == "cpu":
            from voice_clone.domain.engine.device import configure_cpu_threads

            configure_cpu_threads(cpu_threads)
        self.time_stages = False
        self.stage_seconds: dict[str, float] = {}
        self._content_encoder = content_encoder
        self._pitch_extractor = pitch_extractor
        self._voice: _LoadedVoice | None = None
        self._semitones = 0
        self._lock = threading.Lock()

    @property
    def input_sample_rate(self) -> int:
        return INPUT_SAMPLE_RATE

    @property
    def precision(self) -> str:
        return "fp16" if self._dtype == torch.float16 else "fp32"

    @property
    def output_sample_rate(self) -> int:
        voice = self._voice
        return voice.target_rate if voice is not None else 0

    def set_pitch(self, semitones: int) -> None:
        self._semitones = max(MIN_SEMITONES, min(MAX_SEMITONES, int(semitones)))

    def load(self, profile: VoiceProfile) -> None:
        with self._lock:
            self._ensure_base_encoders()
            voice = _load_voice(profile, self._device, self._dtype)
            if self.index_rate > 0:
                _ensure_index(voice)
            self._voice = voice
        logger.info(
            "Loaded voice %s (%s, %d Hz, f0=%s, index=%s) on %s, %s",
            profile.name,
            voice.version,
            voice.target_rate,
            voice.has_pitch,
            voice.index_path is not None,
            self._device,
            self.precision,
        )

    def convert(self, audio: np.ndarray, tail: int | None = None) -> np.ndarray:
        """Convert 16 kHz audio to the voice.

        With `tail`, only the last `tail` input samples are returned. The whole input is
        still used as context, but only the end is synthesized, which is faster and keeps
        long context within GPU limits.
        """
        voice = self._voice
        if voice is None:
            raise ModelLoadError("No voice is loaded.")
        if len(audio) == 0:
            return np.zeros(0, dtype=np.float32)
        audio = np.ascontiguousarray(audio, dtype=np.float32)
        if tail is not None:
            tail = max(1, min(int(tail), len(audio)))
        with self._lock:
            converted, source = self._infer(voice, audio, tail)
        expected = round(len(source) * voice.target_rate / INPUT_SAMPLE_RATE)
        return _follow_loudness(source, _fit_length(converted, expected), self.loudness_follow)

    def _infer(
        self, voice: _LoadedVoice, audio: np.ndarray, tail: int | None
    ) -> tuple[np.ndarray, np.ndarray]:
        """Return the converted audio and the part of `audio` it covers."""
        assert self._content_encoder is not None and self._pitch_extractor is not None
        padded = _pad_tail(audio, CONTENT_PAD)
        clock = _StageClock(self._device, self.time_stages)
        with torch.inference_mode():
            tensor = torch.from_numpy(padded).to(self._device).unsqueeze(0)
            live = self._content_encoder.encode(tensor, voice.version).float()
            clock.lap("encode")
            feats = self._blend_index(voice, live)
            clock.lap("index")
            feats = _upsample_frames(feats)
            live = _upsample_frames(live)
            frames = feats.shape[1]
            net_args: tuple[torch.Tensor, ...] = ()
            if voice.has_pitch:
                pitch, pitchf = self._pitch_tensors(padded, frames)
                clock.lap("pitch")
                frames = min(frames, pitch.shape[1])
                feats, pitch, pitchf = feats[:, :frames], pitch[:, :frames], pitchf[:, :frames]
                feats = self._protect_consonants(feats, live[:, :frames], pitchf)
                net_args = (pitch, pitchf)
            feats = feats.to(self._dtype)
            lengths = torch.tensor([frames], dtype=torch.long, device=self._device)
            sid = torch.zeros(1, dtype=torch.long, device=self._device)
            if tail is None:
                output = voice.net_g.infer(feats, lengths, *net_args, sid)[0]
                decoded = output.squeeze().float().cpu().numpy()
                clock.lap("synth")
                self.stage_seconds = clock.stages
                return decoded, audio
            start = len(audio) - tail
            first = max(0, start // PITCH_HOP - DECODE_MARGIN_FRAMES)
            last = min(frames, math.ceil(len(audio) / PITCH_HOP))
            output = voice.net_g.infer(
                feats, lengths, *net_args, sid, skip_head=first, return_length=last - first
            )[0]
            decoded = output.squeeze().float().cpu().numpy()
            clock.lap("synth")
        self.stage_seconds = clock.stages
        offset = round((start - first * PITCH_HOP) * voice.target_rate / INPUT_SAMPLE_RATE)
        return decoded[offset:], audio[start:]

    def _protect_consonants(
        self, feats: torch.Tensor, live: torch.Tensor, pitchf: torch.Tensor
    ) -> torch.Tensor:
        """On unvoiced frames (consonants, breaths) use less of the index mix.

        The index often has no good match for consonants, so mixing it in there blurs words.
        """
        protect = min(1.0, max(0.0, float(self.protect)))
        if protect <= 0:
            return feats
        voiced = (pitchf > 0).unsqueeze(-1).to(feats.dtype)
        keep = voiced + (1 - voiced) * (1 - protect)
        return feats * keep + live * (1 - keep)

    def _pitch_tensors(self, audio: np.ndarray, frames: int) -> tuple[torch.Tensor, torch.Tensor]:
        assert self._pitch_extractor is not None
        f0 = np.asarray(self._pitch_extractor.extract(audio), dtype=np.float32)
        f0 = _smooth_pitch(f0, int(self.pitch_smoothing_ms) // PITCH_FRAME_MS)
        f0 = f0 * 2.0 ** (self._semitones / 12)
        f0 = _fit_length(f0, frames)
        coarse = _coarse_pitch(f0)
        pitch = torch.from_numpy(coarse).to(self._device).unsqueeze(0)
        pitchf = torch.from_numpy(f0).to(self._device).unsqueeze(0)
        return pitch, pitchf

    def _blend_index(self, voice: _LoadedVoice, feats: torch.Tensor) -> torch.Tensor:
        if self.index_rate <= 0 or voice.index_path is None:
            return feats
        _ensure_index(voice)
        if voice.index is None or voice.index_vectors is None:
            return feats
        query = np.ascontiguousarray(feats[0].cpu().numpy(), dtype=np.float32)
        if query.shape[1] != voice.index_vectors.shape[1]:
            return feats
        _single_thread_faiss()
        scores, neighbours = voice.index.search(query, INDEX_NEIGHBOURS)
        weights = np.square(1.0 / np.maximum(scores, 1e-9))
        weights /= weights.sum(axis=1, keepdims=True)
        retrieved = np.sum(voice.index_vectors[neighbours] * weights[:, :, None], axis=1)
        retrieved_tensor = torch.from_numpy(retrieved.astype(np.float32)).to(feats.device)
        return self.index_rate * retrieved_tensor.unsqueeze(0) + (1 - self.index_rate) * feats

    def _ensure_base_encoders(self) -> None:
        if self._content_encoder is None:
            self._content_encoder = _HubertContentEncoder(
                self._base_models.contentvec_dir, self._device, self._dtype
            )
        if self._pitch_extractor is None:
            self._pitch_extractor = _RmvpePitchExtractor(self._base_models.rmvpe_path, self._device)


class _HubertContentEncoder:
    def __init__(
        self, model_dir: Path, device: torch.device, dtype: torch.dtype = torch.float32
    ) -> None:
        from transformers import HubertConfig, HubertModel

        class HubertWithFinalProj(HubertModel):
            def __init__(self, config: HubertConfig) -> None:
                super().__init__(config)
                self.final_proj = nn.Linear(config.hidden_size, config.classifier_proj_size)

        try:
            config = HubertConfig.from_json_file(str(model_dir / "config.json"))
            model = HubertWithFinalProj(config)
            weights = torch.load(
                model_dir / "pytorch_model.bin", map_location="cpu", weights_only=True
            )
            weights = _adapt_weight_norm_keys(weights, set(model.state_dict()))
            missing, unexpected = model.load_state_dict(weights, strict=False)
        except Exception as error:
            logger.exception("Could not load ContentVec from %s", model_dir)
            raise ModelLoadError(
                "Could not load the ContentVec base model. Delete the models folder and "
                "download it again."
            ) from error
        if missing:
            logger.warning("ContentVec missing weights: %s", missing)
        if unexpected:
            logger.debug("ContentVec unused weights: %s", unexpected)
        self._model = model.eval().to(device, dtype)
        self._dtype = dtype
        self._all_layers = self._model.encoder.layers
        self._v1_layers = (
            None
            if config.do_stable_layer_norm
            else nn.ModuleList(list(self._all_layers)[:V1_FEATURE_LAYER])
        )

    def encode(self, audio: torch.Tensor, version: str) -> torch.Tensor:
        audio = audio.to(self._dtype)
        if version != "v1":
            return self._model(audio).last_hidden_state
        if self._v1_layers is None:
            outputs = self._model(audio, output_hidden_states=True)
            return self._model.final_proj(outputs.hidden_states[V1_FEATURE_LAYER])
        self._model.encoder.layers = self._v1_layers
        try:
            hidden = self._model(audio).last_hidden_state
        finally:
            self._model.encoder.layers = self._all_layers
        return self._model.final_proj(hidden)


class _RmvpePitchExtractor:
    def __init__(
        self, model_path: Path, device: torch.device, recurrent_on_cpu: bool | None = None
    ) -> None:
        from voice_clone.domain.engine.vendor.rmvpe import RMVPE

        try:
            self._rmvpe = RMVPE(str(model_path), is_half=False, device=str(device))
        except Exception as error:
            logger.exception("Could not load RMVPE from %s", model_path)
            raise ModelLoadError(
                "Could not load the RMVPE pitch model. Delete the models folder and "
                "download it again."
            ) from error
        if recurrent_on_cpu is None:
            recurrent_on_cpu = device.type == "mps"
        self._recurrent_device = torch.device("cpu") if recurrent_on_cpu else None
        if self._recurrent_device is not None:
            self._rmvpe.model.fc.to(self._recurrent_device)

    def extract(self, audio: np.ndarray) -> np.ndarray:
        if self._recurrent_device is None:
            f0 = self._rmvpe.infer_from_audio(audio, thred=RMVPE_THRESHOLD)
            return np.asarray(f0, dtype=np.float32)
        with torch.no_grad():
            mel = self._rmvpe.extract_mel(audio, center=True)
            hidden = _rmvpe_hidden(self._rmvpe.model, mel, self._recurrent_device)
        f0 = self._rmvpe.decode(hidden.squeeze(0).numpy(), thred=RMVPE_THRESHOLD)
        return np.asarray(f0, dtype=np.float32)


def _rmvpe_hidden(
    model: nn.Module, mel: torch.Tensor, recurrent_device: torch.device
) -> torch.Tensor:
    frames = mel.shape[-1]
    pad = RMVPE_FRAME_MULTIPLE * math.ceil(frames / RMVPE_FRAME_MULTIPLE) - frames
    padded = F.pad(mel, (0, pad))
    x = model.cnn(model.unet(padded.float().transpose(-1, -2).unsqueeze(1)))
    x = x.transpose(1, 2).flatten(-2)
    return model.fc(x.to(recurrent_device))[:, :frames]


def _default_device() -> torch.device:
    from voice_clone.domain.engine.device import select_torch_device

    return select_torch_device()


def _adapt_weight_norm_keys(weights: dict[str, Any], model_keys: set[str]) -> dict[str, Any]:
    adapted = dict(weights)
    for key in list(adapted):
        if key.endswith(".weight_g"):
            new_key = key[: -len(".weight_g")] + ".parametrizations.weight.original0"
        elif key.endswith(".weight_v"):
            new_key = key[: -len(".weight_v")] + ".parametrizations.weight.original1"
        else:
            continue
        if key not in model_keys and new_key in model_keys:
            adapted[new_key] = adapted.pop(key)
    return adapted


def _load_voice(
    profile: VoiceProfile, device: torch.device, dtype: torch.dtype = torch.float32
) -> _LoadedVoice:
    name = profile.model_path.name
    try:
        checkpoint = torch.load(profile.model_path, map_location="cpu", weights_only=True)
    except Exception as error:
        logger.exception("Could not read %s", profile.model_path)
        raise ModelLoadError(
            f"Could not read the voice model {name}. The file may be damaged or in an "
            "unsupported format."
        ) from error
    try:
        config = list(checkpoint["config"])
        weights = checkpoint["weight"]
    except (KeyError, TypeError) as error:
        raise ProfileError(
            f"{name} is not an RVC voice model (missing config or weights)."
        ) from error
    has_pitch = bool(checkpoint.get("f0", 1))
    version = str(checkpoint.get("version", "v1"))
    synth_class = _synthesizer_class(version, has_pitch)
    try:
        config[-3] = weights["emb_g.weight"].shape[0]
        target_rate = int(config[-1])
        net_g = synth_class(*config, is_half=dtype == torch.float16)
        net_g.load_state_dict(weights, strict=False)
    except Exception as error:
        logger.exception("Could not build the synthesizer for %s", name)
        raise ModelLoadError(f"Could not load the voice model {name}.") from error
    if hasattr(net_g, "enc_q"):
        del net_g.enc_q
    net_g = net_g.eval().to(device, dtype)
    return _LoadedVoice(net_g, target_rate, version, has_pitch, profile.index_path)


def _ensure_index(voice: _LoadedVoice) -> None:
    if voice.index_loaded:
        return
    voice.index, voice.index_vectors = _load_index(voice.index_path)
    voice.index_loaded = True


def _synthesizer_class(version: str, has_pitch: bool) -> type[nn.Module]:
    classes: dict[tuple[str, bool], type[nn.Module]] = {
        ("v1", True): SynthesizerTrnMs256NSFsid,
        ("v2", True): SynthesizerTrnMs768NSFsid,
        ("v1", False): SynthesizerTrnMs256NSFsid_nono,
        ("v2", False): SynthesizerTrnMs768NSFsid_nono,
    }
    try:
        return classes[(version, has_pitch)]
    except KeyError as error:
        raise ProfileError(f"Unsupported RVC model version: {version}.") from error


def _load_index(index_path: Path | None) -> tuple[Any | None, np.ndarray | None]:
    if index_path is None:
        return None, None
    try:
        import faiss

        _single_thread_faiss()
        index = faiss.read_index(str(index_path))
        vectors = index.reconstruct_n(0, index.ntotal)
    except Exception:
        logger.warning("Could not use index %s, continuing without it", index_path, exc_info=True)
        return None, None
    return index, np.ascontiguousarray(vectors, dtype=np.float32)


def _upsample_frames(feats: torch.Tensor) -> torch.Tensor:
    doubled = F.interpolate(feats.permute(0, 2, 1), scale_factor=2, mode="nearest")
    return doubled.permute(0, 2, 1)


def _smooth_pitch(f0: np.ndarray, frames: int) -> np.ndarray:
    """Median-filter the voiced pitch to remove single-frame jumps; unvoiced stays 0."""
    if frames < 2:
        return f0
    voiced = f0 > 0
    if voiced.sum() < 2:
        return f0
    window = frames if frames % 2 else frames + 1
    positions = np.arange(len(f0))
    filled = np.interp(positions, positions[voiced], np.log(f0[voiced]))
    smoothed = np.exp(medfilt(filled, window))
    return np.where(voiced, smoothed, 0.0).astype(np.float32)


def _follow_loudness(source: np.ndarray, converted: np.ndarray, amount: float) -> np.ndarray:
    """Scale the converted audio so its loudness follows the 16 kHz source by `amount` (0-1)."""
    amount = min(1.0, max(0.0, float(amount)))
    if amount <= 0 or len(converted) == 0 or len(source) == 0:
        return converted
    source_env = _loudness_envelope(source, len(converted))
    out_env = _loudness_envelope(converted, len(converted), len(converted) / len(source))
    gain = (source_env / np.maximum(out_env, LOUDNESS_FLOOR)) ** amount
    return (converted * gain).astype(np.float32)


def _loudness_envelope(audio: np.ndarray, length: int, scale: float = 1.0) -> np.ndarray:
    frame = max(1, round(LOUDNESS_FRAME * scale))
    hop = max(1, round(LOUDNESS_HOP * scale))
    padded = np.pad(audio.astype(np.float64), (frame // 2, frame // 2))
    starts = np.arange(0, max(1, len(padded) - frame + 1), hop)
    power = np.cumsum(np.concatenate([[0.0], np.square(padded)]))
    ends = np.minimum(starts + frame, len(padded))
    rms = np.sqrt((power[ends] - power[starts]) / np.maximum(ends - starts, 1))
    centres = starts * (length / max(len(audio), 1))
    return np.interp(np.arange(length), centres, rms).astype(np.float32)


def _coarse_pitch(f0: np.ndarray) -> np.ndarray:
    mel = 1127 * np.log(1 + f0 / 700)
    voiced = mel > 0
    mel[voiced] = (mel[voiced] - F0_MEL_MIN) * 254 / (F0_MEL_MAX - F0_MEL_MIN) + 1
    mel = np.clip(mel, 1, 255)
    return np.rint(mel).astype(np.int64)


def _pad_tail(audio: np.ndarray, amount: int) -> np.ndarray:
    mode = "reflect" if len(audio) > amount else "edge"
    return np.pad(audio, (0, amount), mode=mode)


def _fit_length(values: np.ndarray, length: int) -> np.ndarray:
    if len(values) >= length:
        return values[:length]
    return np.pad(values, (0, length - len(values)))


def _single_thread_faiss() -> None:
    import faiss

    faiss.omp_set_num_threads(1)


class _StageClock:
    def __init__(self, device: torch.device, enabled: bool) -> None:
        self._device = device
        self._enabled = enabled
        self.stages: dict[str, float] = {}
        self._last = time.perf_counter() if enabled else 0.0

    def lap(self, name: str) -> None:
        if not self._enabled:
            return
        if self._device.type == "cuda":
            torch.cuda.synchronize(self._device)
        elif self._device.type == "mps":
            torch.mps.synchronize()
        now = time.perf_counter()
        self.stages[name] = now - self._last
        self._last = now
