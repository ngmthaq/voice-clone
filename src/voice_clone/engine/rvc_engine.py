import logging
import math
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np
import torch
import torch.nn.functional as F
from torch import nn

from voice_clone.engine.download import BaseModelPaths
from voice_clone.engine.vendor.models import (
    SynthesizerTrnMs256NSFsid,
    SynthesizerTrnMs256NSFsid_nono,
    SynthesizerTrnMs768NSFsid,
    SynthesizerTrnMs768NSFsid_nono,
)
from voice_clone.errors import ModelLoadError, ProfileError
from voice_clone.profiles.discovery import VoiceProfile

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


class ContentEncoder(Protocol):
    def encode(self, audio: torch.Tensor, version: str) -> torch.Tensor:
        """Map (1, samples) 16 kHz audio to (1, frames, dim); dim is 256 for v1, 768 for v2."""
        ...


class PitchExtractor(Protocol):
    def extract(self, audio: np.ndarray) -> np.ndarray:
        """Map 16 kHz mono audio to f0 in Hz, one value per 10 ms (0 = unvoiced)."""
        ...


@dataclass
class _LoadedVoice:
    net_g: nn.Module
    target_rate: int
    version: str
    has_pitch: bool
    index: Any | None
    index_vectors: np.ndarray | None


class RvcEngine:
    index_rate: float = 0.5

    def __init__(
        self,
        base_models: BaseModelPaths,
        device: torch.device | None = None,
        content_encoder: ContentEncoder | None = None,
        pitch_extractor: PitchExtractor | None = None,
    ) -> None:
        self._base_models = base_models
        self._device = device if device is not None else _default_device()
        self._content_encoder = content_encoder
        self._pitch_extractor = pitch_extractor
        self._voice: _LoadedVoice | None = None
        self._semitones = 0
        self._lock = threading.Lock()

    @property
    def input_sample_rate(self) -> int:
        return INPUT_SAMPLE_RATE

    @property
    def output_sample_rate(self) -> int:
        voice = self._voice
        return voice.target_rate if voice is not None else 0

    def set_pitch(self, semitones: int) -> None:
        self._semitones = max(MIN_SEMITONES, min(MAX_SEMITONES, int(semitones)))

    def load(self, profile: VoiceProfile) -> None:
        with self._lock:
            self._ensure_base_encoders()
            voice = _load_voice(profile, self._device)
            self._voice = voice
        logger.info(
            "Loaded voice %s (%s, %d Hz, f0=%s, index=%s) on %s",
            profile.name,
            voice.version,
            voice.target_rate,
            voice.has_pitch,
            voice.index is not None,
            self._device,
        )

    def convert(self, audio: np.ndarray) -> np.ndarray:
        voice = self._voice
        if voice is None:
            raise ModelLoadError("No voice is loaded.")
        expected = round(len(audio) * voice.target_rate / INPUT_SAMPLE_RATE)
        if len(audio) == 0:
            return np.zeros(0, dtype=np.float32)
        with self._lock:
            converted = self._infer(voice, np.ascontiguousarray(audio, dtype=np.float32))
        return _fit_length(converted, expected)

    def _infer(self, voice: _LoadedVoice, audio: np.ndarray) -> np.ndarray:
        assert self._content_encoder is not None and self._pitch_extractor is not None
        padded = _pad_tail(audio, CONTENT_PAD)
        with torch.inference_mode():
            tensor = torch.from_numpy(padded).to(self._device).unsqueeze(0)
            feats = self._content_encoder.encode(tensor, voice.version).float()
            feats = self._blend_index(voice, feats)
            feats = F.interpolate(feats.permute(0, 2, 1), scale_factor=2, mode="nearest")
            feats = feats.permute(0, 2, 1)
            frames = feats.shape[1]
            net_args: tuple[torch.Tensor, ...] = ()
            if voice.has_pitch:
                pitch, pitchf = self._pitch_tensors(padded, frames)
                frames = min(frames, pitch.shape[1])
                feats, pitch, pitchf = feats[:, :frames], pitch[:, :frames], pitchf[:, :frames]
                net_args = (pitch, pitchf)
            lengths = torch.tensor([frames], dtype=torch.long, device=self._device)
            sid = torch.zeros(1, dtype=torch.long, device=self._device)
            output = voice.net_g.infer(feats, lengths, *net_args, sid)[0]
        return output.squeeze().float().cpu().numpy()

    def _pitch_tensors(self, audio: np.ndarray, frames: int) -> tuple[torch.Tensor, torch.Tensor]:
        assert self._pitch_extractor is not None
        f0 = np.asarray(self._pitch_extractor.extract(audio), dtype=np.float32)
        f0 = f0 * 2.0 ** (self._semitones / 12)
        f0 = _fit_length(f0, frames)
        coarse = _coarse_pitch(f0)
        pitch = torch.from_numpy(coarse).to(self._device).unsqueeze(0)
        pitchf = torch.from_numpy(f0).to(self._device).unsqueeze(0)
        return pitch, pitchf

    def _blend_index(self, voice: _LoadedVoice, feats: torch.Tensor) -> torch.Tensor:
        if voice.index is None or voice.index_vectors is None or self.index_rate <= 0:
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
                self._base_models.contentvec_dir, self._device
            )
        if self._pitch_extractor is None:
            self._pitch_extractor = _RmvpePitchExtractor(self._base_models.rmvpe_path, self._device)


class _HubertContentEncoder:
    def __init__(self, model_dir: Path, device: torch.device) -> None:
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
        self._model = model.float().eval().to(device)

    def encode(self, audio: torch.Tensor, version: str) -> torch.Tensor:
        audio = audio.float()
        outputs = self._model(audio, output_hidden_states=True)
        if version == "v1":
            return self._model.final_proj(outputs.hidden_states[V1_FEATURE_LAYER])
        return outputs.last_hidden_state


class _RmvpePitchExtractor:
    def __init__(self, model_path: Path, device: torch.device) -> None:
        from voice_clone.engine.vendor.rmvpe import RMVPE

        try:
            self._rmvpe = RMVPE(str(model_path), is_half=False, device=str(device))
        except Exception as error:
            logger.exception("Could not load RMVPE from %s", model_path)
            raise ModelLoadError(
                "Could not load the RMVPE pitch model. Delete the models folder and "
                "download it again."
            ) from error

    def extract(self, audio: np.ndarray) -> np.ndarray:
        return np.asarray(self._rmvpe.infer_from_audio(audio, thred=0.03), dtype=np.float32)


def _default_device() -> torch.device:
    from voice_clone.engine.device import select_torch_device

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


def _load_voice(profile: VoiceProfile, device: torch.device) -> _LoadedVoice:
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
        net_g = synth_class(*config, is_half=False)
        net_g.load_state_dict(weights, strict=False)
    except Exception as error:
        logger.exception("Could not build the synthesizer for %s", name)
        raise ModelLoadError(f"Could not load the voice model {name}.") from error
    if hasattr(net_g, "enc_q"):
        del net_g.enc_q
    net_g = net_g.float().eval().to(device)
    index, index_vectors = _load_index(profile.index_path)
    return _LoadedVoice(net_g, target_rate, version, has_pitch, index, index_vectors)


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
    """Keep faiss single-threaded on the calling thread.

    torch and faiss each bundle their own libomp; a multi-threaded faiss search then
    segfaults on macOS. The OpenMP thread count is per thread, so this must run on the
    thread that searches (the audio worker), not only where the index was loaded.
    """
    import faiss

    faiss.omp_set_num_threads(1)
