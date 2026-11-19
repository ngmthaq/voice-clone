import numpy as np

from voice_clone.audio.noise_gate import NoiseGate

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
    from voice_clone.audio.noise_gate import GateSettings

    gate = NoiseGate(RATE)
    gate.process(_noise(1.0, db=-41))
    gate.process(_speech(0.3))
    gate.configure(GateSettings(hold_ms=0, pre_open_ms=0, open_above_floor_db=6.0))

    after = gate.process(_noise(0.5, db=-41, seed=4))

    assert np.abs(after[int(0.1 * RATE) :]).max() == 0.0
