from dataclasses import dataclass

import numpy as np

FRAME_MS = 20
MIN_THRESHOLD_DB = -55.0
DIGITAL_SILENCE_DB = -90.0
FLOOR_RISE_DB_PER_FRAME = 0.05
VOICE_FALL_DB_PER_FRAME = 0.01
VOICE_RISE = 0.1
BUMP_CUTOFF_HZ = 250.0
BUMP_MIN_JUMP_DB = 18.0
BUMP_MIN_LOW_SHARE = 0.85
BUMP_MIN_ABOVE_VOICE_DB = 6.0
BUMP_MIN_LEVEL_DB = -12.0
BUMP_HOLD_MS = 150
BUMP_TAIL_RISE_DB = 3.0


@dataclass(frozen=True)
class GateSettings:
    hold_ms: int = 500
    pre_open_ms: int = 100
    open_above_floor_db: float = 6.0
    open_below_voice_db: float = 20.0
    block_bumps: bool = True


class NoiseGate:
    """Silences the mic between words, so the model does not turn hiss into noise.

    It learns the mic's noise floor (the quietest recent level) and opens a few dB above
    it. It also learns the voice level (rising quickly toward steady speech, falling very slowly,
    and unchanged in silence) and, when set, opens only for sound
    within a set number of dB of it, so quieter voices nearby stay out. Each call gets a
    whole block, so the gate can open a little before a word starts.
    After speech it stays open for a while, so word endings and short pauses are not cut.
    Short, loud, low-pitched bursts (hand taps, setting the mic down) keep it shut,
    including their ringing tail.
    Gain changes are ramped over one frame to avoid clicks.
    """

    def __init__(self, sample_rate: int, settings: GateSettings | None = None) -> None:
        self._frame = sample_rate * FRAME_MS // 1000
        bin_hz = sample_rate / self._frame
        self._bump_bins = int(BUMP_CUTOFF_HZ / bin_hz) + 1
        self._recent_db: list[float] = []
        self._bump_left = 0
        self._in_tail = False
        self._started_bump = False
        self._floor_db: float | None = None
        self._voice_db: float | None = None
        self._hold_left = 0
        self._gain = 0.0
        self.configure(settings or GateSettings())

    def configure(self, settings: GateSettings) -> None:
        self._hold_frames = settings.hold_ms // FRAME_MS
        self._pre_frames = settings.pre_open_ms // FRAME_MS
        self._open_above_db = settings.open_above_floor_db
        self._open_below_voice_db = settings.open_below_voice_db
        self._block_bumps = settings.block_bumps
        self._bump_frames = BUMP_HOLD_MS // FRAME_MS
        self._hold_left = min(self._hold_left, self._hold_frames)

    @property
    def threshold_db(self) -> float:
        floor = self._floor_db if self._floor_db is not None else MIN_THRESHOLD_DB
        return max(floor + self._open_above_db, MIN_THRESHOLD_DB)

    def process(self, audio: np.ndarray) -> np.ndarray:
        out = np.asarray(audio, dtype=np.float32).copy()
        starts = range(0, len(out), self._frame)
        frames = [out[s : s + self._frame] for s in starts]
        history = list(self._recent_db)
        first = len(history)
        levels = [_db(frame) for frame in frames]
        blocked: list[bool] = []
        onsets: list[bool] = []
        for index, (frame, level_db) in enumerate(zip(frames, levels, strict=True)):
            blocked.append(self._is_bump_blocked(frame, level_db, history, first + index))
            onsets.append(self._started_bump)
            history.append(level_db)
        self._recent_db = history[-2:]
        for index in range(1, len(frames)):
            if onsets[index] and not blocked[index - 1]:
                base_db = _baseline(history, first + index - 1)
                if base_db is None or levels[index - 1] - base_db >= BUMP_MIN_JUMP_DB:
                    blocked[index - 1] = True
        is_open = [
            False if skip else self._is_open(_db(frame))
            for frame, skip in zip(frames, blocked, strict=True)
        ]
        is_open = _open_early(is_open, self._pre_frames)
        is_open = [o and not skip for o, skip in zip(is_open, blocked, strict=True)]
        for start, frame_open, skip in zip(starts, is_open, blocked, strict=True):
            frame = out[start : start + self._frame]
            if skip:
                frame[:] = 0.0
                self._gain = 0.0
                continue
            target = 1.0 if frame_open else 0.0
            ramp = np.linspace(self._gain, target, len(frame), endpoint=False, dtype=np.float32)
            out[start : start + self._frame] = frame * ramp
            self._gain = target
        return out

    def _is_bump_blocked(
        self, frame: np.ndarray, level_db: float, history: list[float], index: int
    ) -> bool:
        self._started_bump = False
        if not self._block_bumps:
            return False
        if self._is_bump(frame, level_db, _baseline(history, index)):
            self._bump_left = self._bump_frames
            self._in_tail = True
            self._started_bump = True
            return True
        if self._bump_left > 0:
            self._bump_left -= 1
            return True
        if self._in_tail:
            prev_db = history[index - 1] if index > 0 else None
            self._in_tail = self._is_tail(frame, level_db, prev_db)
            return self._in_tail
        return False

    def _is_bump(self, frame: np.ndarray, level_db: float, base_db: float | None) -> bool:
        if level_db <= self.threshold_db:
            return False
        if base_db is not None and level_db - base_db < BUMP_MIN_JUMP_DB:
            return False
        min_db = BUMP_MIN_LEVEL_DB
        if self._voice_db is not None:
            min_db = self._voice_db + BUMP_MIN_ABOVE_VOICE_DB
        if level_db < min_db:
            return False
        return self._is_low_pitched(frame)

    def _is_tail(self, frame: np.ndarray, level_db: float, prev_db: float | None) -> bool:
        if level_db <= self.threshold_db:
            return False
        if prev_db is not None and level_db - prev_db > BUMP_TAIL_RISE_DB:
            return False
        return self._is_low_pitched(frame)

    def _is_low_pitched(self, frame: np.ndarray) -> bool:
        power = np.abs(np.fft.rfft(frame)) ** 2
        total = float(power.sum())
        return total > 0 and float(power[: self._bump_bins].sum()) / total >= BUMP_MIN_LOW_SHARE

    def _is_open(self, level_db: float) -> bool:
        if level_db > DIGITAL_SILENCE_DB:
            if self._floor_db is None or level_db < self._floor_db:
                self._floor_db = level_db
            else:
                self._floor_db += FLOOR_RISE_DB_PER_FRAME
        passes_floor = level_db > self.threshold_db
        self._track_voice(level_db, passes_floor)
        if passes_floor and self._near_voice(level_db):
            self._hold_left = self._hold_frames
            return True
        if self._hold_left > 0:
            self._hold_left -= 1
            return True
        return False

    def _track_voice(self, level_db: float, passes_floor: bool) -> None:
        if not passes_floor:
            return
        if self._voice_db is None:
            self._voice_db = level_db
        elif level_db > self._voice_db:
            self._voice_db += VOICE_RISE * (level_db - self._voice_db)
        else:
            self._voice_db = max(self._voice_db - VOICE_FALL_DB_PER_FRAME, self.threshold_db)

    def _near_voice(self, level_db: float) -> bool:
        if self._open_below_voice_db <= 0 or self._voice_db is None:
            return True
        return level_db >= self._voice_db - self._open_below_voice_db


def _baseline(history: list[float], index: int) -> float | None:
    recent = history[max(0, index - 2) : index]
    return min(recent) if recent else None


def _open_early(is_open: list[bool], frames: int) -> list[bool]:
    result = list(is_open)
    for index, frame_open in enumerate(is_open):
        if frame_open:
            for earlier in range(max(0, index - frames), index):
                result[earlier] = True
    return result


def _db(frame: np.ndarray) -> float:
    rms = float(np.sqrt(np.mean(np.square(frame, dtype=np.float64)))) if len(frame) else 0.0
    return 20.0 * np.log10(max(rms, 1e-6))
