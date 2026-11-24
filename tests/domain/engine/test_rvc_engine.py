from pathlib import Path

import numpy as np
import pytest
import torch

from voice_clone.domain.engine import rvc_engine
from voice_clone.domain.engine.download import BaseModelPaths
from voice_clone.domain.engine.rvc_engine import RvcEngine
from voice_clone.domain.engine.vendor.models import SynthesizerTrnMs768NSFsid
from voice_clone.domain.errors import ModelLoadError
from voice_clone.domain.profiles.discovery import VoiceProfile

TARGET_RATE = 40000
CONFIG = [
    1025, 32, 192, 192, 768, 2, 6, 3, 0, "1", [3, 7, 11], [[1, 3, 5], [1, 3, 5], [1, 3, 5]],
    [10, 10, 2, 2], 512, [16, 16, 4, 4], 109, 256, TARGET_RATE,
]  # fmt: skip


class FakeEncoder:
    def encode(self, audio, version):
        frames = (audio.shape[1] - 400) // 320 + 1
        return torch.randn(1, frames, 768 if version == "v2" else 256)


class FakePitch:
    def extract(self, audio):
        f0 = np.full(len(audio) // 160 + 1, 200.0, dtype=np.float32)
        f0[::7] = 0
        return f0


@pytest.fixture(scope="module")
def v2_profile(tmp_path_factory):
    path = tmp_path_factory.mktemp("voice") / "v2.pth"
    net = SynthesizerTrnMs768NSFsid(*CONFIG, is_half=False)
    torch.save({"weight": net.state_dict(), "config": CONFIG, "f0": 1, "version": "v2"}, path)
    return VoiceProfile("v2", path, None)


def _engine():
    return RvcEngine(
        BaseModelPaths(Path("x"), Path("y")),
        torch.device("cpu"),
        FakeEncoder(),
        FakePitch(),
    )


@pytest.fixture
def engine(v2_profile):
    instance = _engine()
    instance.load(v2_profile)
    return instance


def test_output_sample_rate_comes_from_checkpoint(engine):
    assert engine.output_sample_rate == TARGET_RATE


@pytest.mark.parametrize("samples", [4000, 12000, 16000])
def test_convert_length_matches_target_rate(engine, samples):
    audio = (np.random.default_rng(1).standard_normal(samples) * 0.1).astype(np.float32)

    out = engine.convert(audio)

    assert len(out) == round(samples * TARGET_RATE / 16000)


def test_convert_returns_finite_float32(engine):
    out = engine.convert(np.zeros(12000, dtype=np.float32))

    assert out.dtype == np.float32 and np.isfinite(out).all()


def test_convert_empty_audio_returns_empty(engine):
    assert len(engine.convert(np.zeros(0, dtype=np.float32))) == 0


def test_set_pitch_clamps_high_value(engine):
    engine.set_pitch(99)

    assert engine._semitones == 12


def test_set_pitch_clamps_low_value(engine):
    engine.set_pitch(-99)

    assert engine._semitones == -12


def test_convert_before_load_raises_model_load_error():
    with pytest.raises(ModelLoadError):
        _engine().convert(np.zeros(100, dtype=np.float32))


def test_load_non_checkpoint_file_raises_model_load_error(tmp_path):
    bad = tmp_path / "bad.pth"
    bad.write_bytes(b"not a checkpoint")

    with pytest.raises(ModelLoadError):
        _engine().load(VoiceProfile("bad", bad, None))


def test_full_protect_keeps_live_features_on_unvoiced_frames(engine):
    feats = torch.ones(1, 4, 3)
    live = torch.zeros(1, 4, 3)
    pitchf = torch.tensor([[200.0, 0.0, 180.0, 0.0]])
    engine.protect = 1.0

    out = engine._protect_consonants(feats, live, pitchf)

    assert out[0, :, 0].tolist() == [1.0, 0.0, 1.0, 0.0]


def test_partial_protect_mixes_unvoiced_frames(engine):
    engine.protect = 0.25

    out = engine._protect_consonants(
        torch.ones(1, 2, 1), torch.zeros(1, 2, 1), torch.tensor([[0.0, 150.0]])
    )

    assert out[0, :, 0].tolist() == pytest.approx([0.75, 1.0])


def test_zero_protect_leaves_features_unchanged(engine):
    engine.protect = 0.0
    feats = torch.ones(1, 2, 1)

    out = engine._protect_consonants(feats, torch.zeros(1, 2, 1), torch.tensor([[0.0, 0.0]]))

    assert torch.equal(out, feats)


def test_pitch_smoothing_removes_single_frame_jump():
    f0 = np.array([200, 200, 400, 200, 200, 0, 0], dtype=np.float32)

    out = rvc_engine._smooth_pitch(f0, 3)

    assert out[:5] == pytest.approx([200] * 5) and out[5:].tolist() == [0.0, 0.0]


def test_pitch_smoothing_off_returns_same_values():
    f0 = np.array([200, 400, 200], dtype=np.float32)

    assert rvc_engine._smooth_pitch(f0, 0) is f0


def test_follow_loudness_full_matches_source_level():
    rng = np.random.default_rng(2)
    source = (rng.standard_normal(16000) * 0.2).astype(np.float32)
    converted = (rng.standard_normal(40000) * 0.02).astype(np.float32)

    out = rvc_engine._follow_loudness(source, converted, 1.0)

    rms = float(np.sqrt(np.mean(np.square(out[4000:-4000]))))
    assert rms == pytest.approx(0.2, rel=0.15)


def test_follow_loudness_zero_returns_output_unchanged():
    converted = np.full(100, 0.3, dtype=np.float32)

    assert rvc_engine._follow_loudness(np.ones(40, dtype=np.float32), converted, 0) is converted


def test_follow_loudness_keeps_length_and_dtype(engine):
    engine.loudness_follow = 0.5
    engine.pitch_smoothing_ms = 30

    out = engine.convert((np.random.default_rng(3).standard_normal(12000) * 0.1).astype(np.float32))

    assert len(out) == 30000 and out.dtype == np.float32 and np.isfinite(out).all()


@pytest.mark.parametrize("tail", [6400, 7680, 12000])
def test_convert_tail_returns_only_the_end(engine, tail):
    audio = (np.random.default_rng(4).standard_normal(16000) * 0.1).astype(np.float32)

    out = engine.convert(audio, tail=tail)

    assert len(out) == round(tail * TARGET_RATE / 16000)
    assert out.dtype == np.float32 and np.isfinite(out).all()


def test_convert_tail_decodes_only_the_last_frames(engine):
    calls = []
    infer = engine._voice.net_g.infer

    def spy(*args, **kwargs):
        calls.append(kwargs)
        return infer(*args, **kwargs)

    engine._voice.net_g.infer = spy
    engine.convert(np.zeros(16000, dtype=np.float32), tail=6400)

    assert calls[0]["skip_head"] == (16000 - 6400) // 160 - rvc_engine.DECODE_MARGIN_FRAMES
    assert calls[0]["return_length"] == 100 - calls[0]["skip_head"]


def test_stage_times_recorded_when_enabled(engine):
    engine.time_stages = True

    engine.convert(np.zeros(12000, dtype=np.float32), tail=4000)

    assert set(engine.stage_seconds) == {"encode", "index", "pitch", "synth"}
    assert all(value >= 0 for value in engine.stage_seconds.values())


def test_stage_times_empty_when_disabled(engine):
    engine.convert(np.zeros(12000, dtype=np.float32))

    assert engine.stage_seconds == {}


@pytest.fixture
def index_loads(monkeypatch):
    calls = []

    def fake_load_index(path):
        calls.append(path)
        return None, None

    monkeypatch.setattr(rvc_engine, "_load_index", fake_load_index)
    return calls


def test_index_not_loaded_while_index_is_off(v2_profile, index_loads):
    instance = _engine()
    instance.index_rate = 0
    instance.load(VoiceProfile("v2", v2_profile.model_path, Path("voice.index")))

    instance.convert(np.zeros(12000, dtype=np.float32))

    assert index_loads == []


def test_index_loaded_once_when_turned_on_later(v2_profile, index_loads):
    instance = _engine()
    instance.index_rate = 0
    instance.load(VoiceProfile("v2", v2_profile.model_path, Path("voice.index")))
    instance.index_rate = 0.5

    instance.convert(np.zeros(12000, dtype=np.float32))
    instance.convert(np.zeros(12000, dtype=np.float32))

    assert index_loads == [Path("voice.index")]


def test_index_loaded_with_voice_when_index_is_on(v2_profile, index_loads):
    instance = _engine()
    instance.load(VoiceProfile("v2", v2_profile.model_path, Path("voice.index")))

    assert index_loads == [Path("voice.index")]


@pytest.fixture(scope="module")
def tiny_contentvec(tmp_path_factory):
    from transformers import HubertConfig, HubertModel

    folder = tmp_path_factory.mktemp("contentvec")
    config = HubertConfig(
        hidden_size=32,
        num_hidden_layers=12,
        num_attention_heads=2,
        intermediate_size=64,
        conv_dim=(16,) * 7,
        num_conv_pos_embeddings=16,
        num_conv_pos_embedding_groups=2,
        classifier_proj_size=8,
    )
    config.to_json_file(str(folder / "config.json"))
    torch.manual_seed(0)
    weights = HubertModel(config).state_dict()
    weights["final_proj.weight"] = torch.randn(8, 32)
    weights["final_proj.bias"] = torch.randn(8)
    torch.save(weights, folder / "pytorch_model.bin")
    return folder


def test_v1_encoder_skips_layers_but_matches_layer_nine(tiny_contentvec):
    encoder = rvc_engine._HubertContentEncoder(tiny_contentvec, torch.device("cpu"))
    audio = torch.randn(1, 8000)

    with torch.inference_mode():
        full = encoder._model(audio, output_hidden_states=True)
        expected = encoder._model.final_proj(full.hidden_states[rvc_engine.V1_FEATURE_LAYER])
        got = encoder.encode(audio, "v1")

    assert torch.allclose(got, expected, atol=1e-5)
    assert len(encoder._model.encoder.layers) == 12


def test_v2_encoder_returns_last_hidden_state(tiny_contentvec):
    encoder = rvc_engine._HubertContentEncoder(tiny_contentvec, torch.device("cpu"))
    audio = torch.randn(1, 8000)

    with torch.inference_mode():
        expected = encoder._model(audio).last_hidden_state
        got = encoder.encode(audio, "v2")

    assert torch.allclose(got, expected)


def test_cpu_engine_stays_fp32_when_fp16_is_asked():
    engine = RvcEngine(
        BaseModelPaths(Path("x"), Path("y")),
        torch.device("cpu"),
        FakeEncoder(),
        FakePitch(),
        precision="fp16",
    )

    assert engine.precision == "fp32"


def test_half_voice_converts_to_float32(v2_profile, monkeypatch):
    monkeypatch.setattr(
        "voice_clone.domain.engine.device.use_half_precision", lambda device, precision: True
    )
    engine = RvcEngine(
        BaseModelPaths(Path("x"), Path("y")),
        torch.device("cpu"),
        FakeEncoder(),
        FakePitch(),
        precision="fp16",
    )
    engine.load(v2_profile)

    out = engine.convert(np.zeros(12000, dtype=np.float32), tail=4000)

    assert engine.precision == "fp16"
    assert next(engine._voice.net_g.parameters()).dtype == torch.float16
    assert out.dtype == np.float32 and np.isfinite(out).all()


def test_half_content_encoder_returns_half(tiny_contentvec):
    encoder = rvc_engine._HubertContentEncoder(tiny_contentvec, torch.device("cpu"), torch.float16)

    with torch.inference_mode():
        out = encoder.encode(torch.randn(1, 8000), "v2")

    assert out.dtype == torch.float16


@pytest.fixture(scope="module")
def tiny_rmvpe(tmp_path_factory):
    from voice_clone.domain.engine.vendor.rmvpe import E2E

    torch.manual_seed(0)
    path = tmp_path_factory.mktemp("rmvpe") / "rmvpe.pt"
    torch.save(E2E(4, 1, (2, 2)).state_dict(), path)
    return path


def test_rmvpe_split_matches_the_original_network(tiny_rmvpe):
    extractor = rvc_engine._RmvpePitchExtractor(tiny_rmvpe, torch.device("cpu"))
    mel = torch.randn(1, 128, 75)

    with torch.no_grad():
        expected = extractor._rmvpe.mel2hidden(mel)
        got = rvc_engine._rmvpe_hidden(extractor._rmvpe.model, mel, torch.device("cpu"))

    assert got.shape == expected.shape
    assert torch.allclose(got, expected, atol=1e-6)


def test_rmvpe_with_recurrent_on_cpu_gives_same_pitch(tiny_rmvpe):
    audio = (np.random.default_rng(3).standard_normal(14000) * 0.1).astype(np.float32)
    whole = rvc_engine._RmvpePitchExtractor(tiny_rmvpe, torch.device("cpu"), False)
    split = rvc_engine._RmvpePitchExtractor(tiny_rmvpe, torch.device("cpu"), True)

    np.testing.assert_allclose(split.extract(audio), whole.extract(audio), rtol=1e-5)


@pytest.mark.parametrize(("device", "on_cpu"), [("cpu", False), ("cuda", False), ("mps", True)])
def test_rmvpe_moves_recurrent_part_to_cpu_only_on_apple_gpus(
    tiny_rmvpe, monkeypatch, device, on_cpu
):
    monkeypatch.setattr("voice_clone.domain.engine.vendor.rmvpe.RMVPE.__init__", _cpu_rmvpe_init)

    extractor = rvc_engine._RmvpePitchExtractor(tiny_rmvpe, torch.device(device))

    assert (extractor._recurrent_device is not None) is on_cpu


def _cpu_rmvpe_init(self, model_path, is_half=False, device=None):
    from voice_clone.domain.engine.vendor.rmvpe import E2E

    self.model = E2E(4, 1, (2, 2))
