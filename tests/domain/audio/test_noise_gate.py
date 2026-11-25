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


def _envelope(n: int) -> np.ndarray:
    t = np.arange(n) / RATE
    return 0.4 + 0.6 * np.sin(2 * np.pi * 3 * t) ** 2


def _voiced(seconds: float, f0: float, seed: int = 0) -> np.ndarray:
    n = int(seconds * RATE)
    t = np.arange(n) / RATE
    wave = sum(np.sin(2 * np.pi * f0 * h * t) / h for h in range(1, 30))
    return (0.03 * wave * _envelope(n) + _noise(seconds, db=-66, seed=seed)).astype(np.float32)


def _nasal(seconds: float) -> np.ndarray:
    n = int(seconds * RATE)
    t = np.arange(n) / RATE
    wave = np.sin(2 * np.pi * 110 * t) + 0.5 * np.sin(2 * np.pi * 220 * t)
    wave += 0.1 * np.sin(2 * np.pi * 330 * t)
    return (0.04 * wave * _envelope(n)).astype(np.float32)


def _tap(
    freq: float = 120.0, amp: float = 0.7, decay: float = 0.03, seconds: float = 0.1
) -> np.ndarray:
    k = np.arange(int(seconds * RATE))
    body = amp * np.exp(-k / (decay * RATE)) * np.sin(2 * np.pi * freq * k / RATE)
    click = 0.05 * amp * np.random.default_rng(7).standard_normal(len(k))
    return (body + click * np.exp(-k / (0.005 * RATE))).astype(np.float32)


def _level_db(audio: np.ndarray) -> float:
    return 20 * np.log10(max(float(np.sqrt(np.mean(np.square(audio)))), 1e-9))


def _tap_drop_db(gate: NoiseGate, before: np.ndarray, tap: np.ndarray) -> float:
    gate.process(before)
    out = gate.process(np.concatenate([tap, np.zeros(RATE // 2, dtype=np.float32)]))
    return _level_db(tap) - _level_db(out[: len(tap)])


def _in_chunks(gate: NoiseGate, audio: np.ndarray, size: int = 6400) -> np.ndarray:
    return np.concatenate([gate.process(audio[i : i + size]) for i in range(0, len(audio), size)])


def _tap_in_silence() -> tuple[np.ndarray, np.ndarray]:
    return _noise(0.5, db=-66), _tap()


def _tap_after_speech() -> tuple[np.ndarray, np.ndarray]:
    lead = np.concatenate([_noise(1.0, db=-66), _voiced(2.0, 150), _noise(1.0, db=-66, seed=1)])
    return lead, _tap()


def test_tap_in_silence_is_muted() -> None:
    lead, tap = _tap_in_silence()

    drop = _tap_drop_db(NoiseGate(RATE), lead, tap)

    assert drop >= 20.0


def test_tap_after_speech_is_muted() -> None:
    lead, tap = _tap_after_speech()

    drop = _tap_drop_db(NoiseGate(RATE), lead, tap)

    assert drop >= 20.0


def test_tap_while_gate_is_still_holding_after_speech_is_muted() -> None:
    lead = np.concatenate([_noise(1.0, db=-66), _voiced(2.0, 150), _noise(0.1, db=-66, seed=1)])

    drop = _tap_drop_db(NoiseGate(RATE), lead, _tap())

    assert drop >= 20.0


@pytest.mark.parametrize("freq", [60.0, 180.0])
def test_taps_of_other_pitches_are_muted(freq: float) -> None:
    lead, _ = _tap_after_speech()

    drop = _tap_drop_db(NoiseGate(RATE), lead, _tap(freq=freq, amp=0.9))

    assert drop >= 20.0


def test_tap_is_muted_when_audio_comes_in_chunks() -> None:
    lead, tap = _tap_after_speech()
    gate = NoiseGate(RATE)
    _in_chunks(gate, lead)

    out = _in_chunks(gate, np.concatenate([tap, np.zeros(RATE // 2, dtype=np.float32)]))

    assert _level_db(tap) - _level_db(out[: len(tap)]) >= 20.0


def test_tap_passes_when_bump_blocking_is_off() -> None:
    lead, tap = _tap_after_speech()

    drop = _tap_drop_db(NoiseGate(RATE, GateSettings(block_bumps=False)), lead, tap)

    assert drop < 20.0


def test_tap_in_silence_passes_when_bump_blocking_is_off() -> None:
    lead, tap = _tap_in_silence()

    drop = _tap_drop_db(NoiseGate(RATE, GateSettings(block_bumps=False)), lead, tap)

    assert drop < 20.0


def test_bump_blocking_can_be_turned_off_while_running() -> None:
    lead, tap = _tap_after_speech()
    gate = NoiseGate(RATE)
    gate.process(lead)
    gate.configure(GateSettings(block_bumps=False))

    out = gate.process(np.concatenate([tap, np.zeros(RATE // 2, dtype=np.float32)]))

    assert _level_db(tap) - _level_db(out[: len(tap)]) < 20.0


def test_voice_level_does_not_rise_after_a_tap() -> None:
    lead, tap = _tap_after_speech()
    gate = NoiseGate(RATE)
    gate.process(lead)
    before = gate._voice_db

    gate.process(np.concatenate([tap, np.zeros(RATE // 2, dtype=np.float32)]))

    assert gate._voice_db == before


def test_normal_word_passes_after_a_tap() -> None:
    lead, tap = _tap_after_speech()
    gate = NoiseGate(RATE)
    gate.process(lead)
    gate.process(np.concatenate([tap, _noise(0.5, db=-66, seed=3)]))
    word = _voiced(1.0, 150, seed=4)

    out = gate.process(word)

    np.testing.assert_allclose(out[RATE // 5 :], word[RATE // 5 :])


def _speech_cases() -> dict[str, np.ndarray]:
    plosive = _voiced(1.0, 150, seed=5)
    plosive[: int(0.015 * RATE)] = (
        0.1 * np.random.default_rng(6).standard_normal(int(0.015 * RATE))
    ).astype(np.float32)
    return {
        "f0_150": _voiced(1.5, 150),
        "f0_100": _voiced(1.5, 100),
        "f0_90": _voiced(1.5, 90),
        "nasal": _nasal(1.5),
        "plosive": plosive,
    }


@pytest.mark.parametrize("name", ["f0_150", "f0_100", "f0_90", "nasal", "plosive"])
def test_speech_is_the_same_with_and_without_bump_blocking(name: str) -> None:
    audio = np.concatenate([_noise(1.0, db=-66), _speech_cases()[name]])
    blocking = NoiseGate(RATE, GateSettings(block_bumps=True))
    passing = NoiseGate(RATE, GateSettings(block_bumps=False))

    out_blocking = blocking.process(audio)
    out_passing = passing.process(audio)

    assert np.array_equal(out_blocking, out_passing)
    assert np.abs(out_blocking[RATE:]).max() > 0.0


def test_chunked_speech_is_the_same_with_and_without_bump_blocking() -> None:
    audio = np.concatenate([_noise(1.0, db=-66), _speech_cases()["f0_100"]])

    out_blocking = _in_chunks(NoiseGate(RATE), audio)
    out_passing = _in_chunks(NoiseGate(RATE, GateSettings(block_bumps=False)), audio)

    assert np.array_equal(out_blocking, out_passing)


def _thud() -> np.ndarray:
    return _tap(freq=150.0, amp=0.9, decay=0.1, seconds=0.4)


def _chunked_drop_db(lead: np.ndarray, bump: np.ndarray, offset: int) -> float:
    gate = NoiseGate(RATE)
    _in_chunks(gate, lead)
    audio = np.concatenate([np.zeros(offset, dtype=np.float32), bump, np.zeros(RATE, np.float32)])
    out = _in_chunks(gate, audio)
    window = slice(offset, offset + len(bump))
    return _level_db(bump) - _level_db(out[window])


def _silent_lead() -> np.ndarray:
    return _noise(1.6, db=-66)


def _speech_lead() -> np.ndarray:
    return np.concatenate([_noise(1.0, db=-66), _voiced(2.0, 150), _noise(1.0, db=-66, seed=1)])


@pytest.mark.parametrize("offset", [0, 100, 250, 300, 315])
def test_tap_starting_inside_a_frame_is_muted_after_speech(offset: int) -> None:
    drop = _chunked_drop_db(_speech_lead(), _tap(), offset)

    assert drop >= 20.0


@pytest.mark.parametrize("offset", [0, 100, 250, 300, 315])
def test_tap_starting_inside_a_frame_is_muted_in_silence(offset: int) -> None:
    drop = _chunked_drop_db(_silent_lead(), _tap(), offset)

    assert drop >= 20.0


@pytest.mark.parametrize("offset", [0, 100, 250, 300])
def test_long_thud_is_muted_after_speech(offset: int) -> None:
    drop = _chunked_drop_db(_speech_lead(), _thud(), offset)

    assert drop >= 20.0


@pytest.mark.parametrize("offset", [0, 100, 250, 300])
def test_long_thud_is_muted_in_silence(offset: int) -> None:
    drop = _chunked_drop_db(_silent_lead(), _thud(), offset)

    assert drop >= 20.0


def test_speech_after_a_long_thud_is_not_cut() -> None:
    speech = _voiced(1.0, 150, seed=4)
    audio = np.concatenate([_speech_lead(), _thud(), _noise(0.3, db=-66, seed=2), speech])

    out_blocking = _in_chunks(NoiseGate(RATE), audio)
    out_passing = _in_chunks(NoiseGate(RATE, GateSettings(block_bumps=False)), audio)

    start = len(audio) - len(speech)
    np.testing.assert_array_equal(out_blocking[start:], out_passing[start:])
