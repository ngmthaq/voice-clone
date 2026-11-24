from typing import Protocol

import numpy as np

from voice_clone.domain.profiles.discovery import VoiceProfile


class VoiceEngine(Protocol):
    @property
    def input_sample_rate(self) -> int: ...

    @property
    def output_sample_rate(self) -> int: ...

    def load(self, profile: VoiceProfile) -> None: ...

    def set_pitch(self, semitones: int) -> None: ...

    def convert(self, audio: np.ndarray, tail: int | None = None) -> np.ndarray: ...
