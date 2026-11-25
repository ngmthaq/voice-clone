import numpy as np
import pytest

from voice_clone.domain.audio.noise_gate import (
    FRAME_MS,
    MIN_THRESHOLD_DB,
    VOICE_FALL_DB_PER_FRAME,
    GateSettings,
    NoiseGate,
)

RATE = 16000


def _noise(seconds: float, db: float, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return (rng.standard_normal(int(seconds * RATE)) * 10 ** (db / 20)).astype(np.float32)


def _speech(seconds: float) -> np.ndarray:
    t = np.arange(int(seconds * RATE)) / RATE
    return (0.2 * np.sin(2 * np.pi * 180 * t)).astype(np.float32)


def test_background_hiss_is_silenced() -> None:
    gate = NoiseGate(RATE)

    out = gate.process(_noise(2.0, db=-41))

    assert np.abs(out[RATE:]).max() == 0.0


def test_speech_passes_through() -> None:
    gate = NoiseGate(RATE)
    gate.process(_noise(1.0, db=-41))
    speech = _speech(1.0)

    out = gate.process(speech)

    np.testing.assert_allclose(out[RATE // 10 :], speech[RATE // 10 :])


def test_gate_stays_open_briefly_after_speech_then_closes() -> None:
    gate = NoiseGate(RATE)
    gate.process(_noise(1.0, db=-41))
    gate.process(_speech(0.5))

    after = gate.process(_noise(1.0, db=-41, seed=1))

    assert np.abs(after[: RATE // 10]).max() > 0.0
    assert np.abs(after[int(0.7 * RATE) :]).max() == 0.0


def test_gain_changes_are_ramped_without_clicks() -> None:
    gate = NoiseGate(RATE)
    gate.process(np.zeros(RATE, dtype=np.float32) + 1e-4)

    out = gate.process(np.full(RATE // 10, 0.5, dtype=np.float32))

    assert np.max(np.abs(np.diff(out))) < 0.05


def test_digital_silence_does_not_lower_the_noise_floor() -> None:
    gate = NoiseGate(RATE)
    gate.process(np.zeros(RATE // 10, dtype=np.float32))

    out = gate.process(_noise(2.0, db=-41))

    assert np.abs(out[RATE:]).max() == 0.0


def test_gate_opens_before_a_word_starts() -> None:
    gate = NoiseGate(RATE)
    gate.process(_noise(1.0, db=-41))
    soft_start = _noise(0.2, db=-41, seed=2)
    block = np.concatenate([soft_start, _speech(0.2)])

    out = gate.process(block)

    pre_open = int(0.08 * RATE)
    assert np.abs(out[len(soft_start) - pre_open : len(soft_start)]).max() > 0.0
    assert np.abs(out[: int(0.05 * RATE)]).max() == 0.0


def test_short_pause_between_words_stays_open() -> None:
    gate = NoiseGate(RATE)
    gate.process(_noise(1.0, db=-41))
    gate.process(_speech(0.3))

    pause = gate.process(_noise(0.4, db=-41, seed=3))

    assert np.count_nonzero(pause) > 0.9 * len(pause)


def test_settings_can_change_while_running() -> None:
    gate = NoiseGate(RATE)
    gate.process(_noise(1.0, db=-41))
    gate.process(_speech(0.3))
    gate.configure(GateSettings(hold_ms=0, pre_open_ms=0, open_above_floor_db=6.0))

    after = gate.process(_noise(0.5, db=-41, seed=4))

    assert np.abs(after[int(0.1 * RATE) :]).max() == 0.0


def _open_share(out: np.ndarray) -> float:
    return np.count_nonzero(out) / len(out)


def _gate_with_user_heard(settings: GateSettings | None = None) -> NoiseGate:
    gate = NoiseGate(RATE, settings)
    gate.process(_noise(1.0, db=-60))
    gate.process(_noise(1.0, db=-20, seed=1))
    return gate


def test_neighbour_below_the_user_stays_closed_after_a_pause() -> None:
    gate = _gate_with_user_heard()
    gate.process(_noise(2.0, db=-60, seed=2))

    out = gate.process(_noise(2.0, db=-45, seed=3))

    assert _open_share(out) == 0.0


def test_neighbour_stays_closed_after_a_long_pause_and_long_neighbour_speech() -> None:
    gate = _gate_with_user_heard()
    gate.process(_noise(10.0, db=-60, seed=2))

    out = gate.process(_noise(10.0, db=-45, seed=3))

    assert _open_share(out) == 0.0


def test_soft_user_word_stays_open_after_a_loud_pop() -> None:
    gate = _gate_with_user_heard()
    gate.process(_noise(0.04, db=-3, seed=2))

    out = gate.process(_noise(2.0, db=-30, seed=3))

    assert _open_share(out) > 0.99


def test_sound_above_the_floor_opens_before_any_voice_is_heard() -> None:
    gate = NoiseGate(RATE)
    gate.process(_noise(1.0, db=-60))

    out = gate.process(_noise(1.0, db=-45, seed=1))

    assert _open_share(out[RATE // 10 :]) > 0.99


def test_neighbour_opens_when_voice_rule_is_off() -> None:
    gate = _gate_with_user_heard(GateSettings(open_below_voice_db=0.0))
    gate.process(_noise(2.0, db=-60, seed=2))

    out = gate.process(_noise(2.0, db=-45, seed=3))

    assert _open_share(out[RATE // 10 :]) > 0.99


def test_silence_does_not_change_the_voice_level() -> None:
    gate = _gate_with_user_heard()
    before = gate._voice_db

    gate.process(_noise(2.0, db=-60, seed=2))

    assert gate._voice_db == before


def test_voice_level_falls_slowly_per_passing_frame() -> None:
    gate = _gate_with_user_heard(GateSettings(open_below_voice_db=0.0))
    before = gate._voice_db
    frames = 10

    gate.process(_noise(frames * FRAME_MS / 1000, db=-45, seed=2))

    assert before - gate._voice_db == pytest.approx(frames * VOICE_FALL_DB_PER_FRAME)


def test_voice_level_never_falls_below_the_threshold() -> None:
    gate = NoiseGate(RATE)
    gate.process(_noise(1.0, db=-60))
    gate.process(_noise(0.1, db=-45, seed=1))

    gate.process(_noise(30.0, db=-45, seed=2))

    assert gate._voice_db >= MIN_THRESHOLD_DB


def test_voice_rule_can_change_while_running() -> None:
    gate = _gate_with_user_heard()
    gate.process(_noise(2.0, db=-60, seed=2))
    closed = gate.process(_noise(1.0, db=-45, seed=3))

    gate.configure(GateSettings(open_below_voice_db=0.0))
    opened = gate.process(_noise(1.0, db=-45, seed=4))

    assert _open_share(closed) == 0.0
    assert _open_share(opened[RATE // 10 :]) > 0.99
