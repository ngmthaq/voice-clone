from pathlib import Path

import numpy as np
import pytest
import torch

from voice_clone.engine.download import BaseModelPaths
from voice_clone.engine.rvc_engine import RvcEngine
from voice_clone.engine.vendor.models import SynthesizerTrnMs768NSFsid
from voice_clone.errors import ModelLoadError
from voice_clone.profiles.discovery import VoiceProfile

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
