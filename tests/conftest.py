import numpy as np
import pytest

from voice_clone.audio.devices import AudioDevice


class FakeEngine:
    input_sample_rate = 16000

    def __init__(self, output_sample_rate: int = 40000, value: float = 0.5) -> None:
        self.output_sample_rate = output_sample_rate
        self.value = value
        self.convert_lengths: list[int] = []

    def convert(self, audio: np.ndarray, tail: int | None = None) -> np.ndarray:
        self.convert_lengths.append(len(audio))
        kept = len(audio) if tail is None else min(tail, len(audio))
        length = round(kept * self.output_sample_rate / self.input_sample_rate)
        return np.full(length, self.value, dtype=np.float32)


@pytest.fixture
def fake_engine() -> FakeEngine:
    return FakeEngine()


@pytest.fixture
def input_device() -> AudioDevice:
    return AudioDevice(0, "Mic", 1, 0, 48000.0)


@pytest.fixture
def output_device() -> AudioDevice:
    return AudioDevice(1, "BlackHole 2ch", 2, 2, 48000.0)
