import numpy as np

FRAME_SIZE = 512
HOP_SIZE = 256
OVER_SUBTRACT = 4.0
GAIN_FLOOR = 0.18
POWER_SMOOTHING = 0.15
NOISE_RISE_PER_FRAME = 1.01
GAIN_UP_WEIGHT = 0.8
GAIN_DOWN_WEIGHT = 0.4
SILENCE_POWER = 1e-12
EPSILON = 1e-12


class NoiseReducer:
    """Removes steady background noise (crowd murmur, fan, hiss) with a spectral filter.

    It learns a noise level for each frequency and turns down the bins that sit close to it.
    Output is the input delayed by a fixed FRAME_SIZE samples, and has the same length.
    """

    def __init__(self, sample_rate: int) -> None:
        self.sample_rate = sample_rate
        self._window = np.sqrt(np.hanning(FRAME_SIZE + 1)[:FRAME_SIZE]).astype(np.float32)
        self.reset()

    @property
    def delay_samples(self) -> int:
        return FRAME_SIZE

    def reset(self) -> None:
        bins = FRAME_SIZE // 2 + 1
        self._pending = np.zeros(HOP_SIZE, dtype=np.float32)
        self._overlap = np.zeros(FRAME_SIZE, dtype=np.float32)
        self._ready = np.zeros(HOP_SIZE, dtype=np.float32)
        self._noise: np.ndarray | None = None
        self._smooth_power = np.zeros(bins, dtype=np.float64)
        self._gain = np.ones(bins, dtype=np.float64)

    def process(self, audio: np.ndarray) -> np.ndarray:
        audio = np.asarray(audio, dtype=np.float32)
        count = len(audio)
        if count == 0:
            return audio.copy()
        self._pending = np.concatenate([self._pending, audio])
        produced: list[np.ndarray] = [self._ready]
        offset = 0
        while len(self._pending) - offset >= FRAME_SIZE:
            frame = self._pending[offset : offset + FRAME_SIZE]
            produced.append(self._process_frame(frame))
            offset += HOP_SIZE
        self._pending = self._pending[offset:]
        available = np.concatenate(produced)
        self._ready = available[count:]
        return available[:count]

    def _process_frame(self, frame: np.ndarray) -> np.ndarray:
        spectrum = np.fft.rfft(frame * self._window)
        power = spectrum.real.astype(np.float64) ** 2 + spectrum.imag.astype(np.float64) ** 2
        self._update_noise(power)
        gain = self._smoothed_gain(power)
        synthesized = np.fft.irfft(spectrum * gain, n=FRAME_SIZE).astype(np.float32)
        synthesized *= self._window
        self._overlap += synthesized
        out = self._overlap[:HOP_SIZE].copy()
        self._overlap = np.concatenate([self._overlap[HOP_SIZE:], np.zeros(HOP_SIZE, np.float32)])
        return out

    def _update_noise(self, power: np.ndarray) -> None:
        if self._noise is None:
            if power.mean() < SILENCE_POWER:
                return
            self._smooth_power = power.copy()
            self._noise = power.copy()
            return
        self._smooth_power += POWER_SMOOTHING * (power - self._smooth_power)
        rising = self._noise * NOISE_RISE_PER_FRAME
        self._noise = np.maximum(np.minimum(self._smooth_power, rising), EPSILON)

    def _smoothed_gain(self, power: np.ndarray) -> np.ndarray:
        if self._noise is None:
            return self._gain
        target = np.maximum(1.0 - OVER_SUBTRACT * self._noise / (power + EPSILON), GAIN_FLOOR)
        weight = np.where(target > self._gain, GAIN_UP_WEIGHT, GAIN_DOWN_WEIGHT)
        self._gain = self._gain + weight * (target - self._gain)
        return self._gain
