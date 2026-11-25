import numpy as np
import pytest

from voice_clone.domain.audio.noise_reducer import NoiseReducer

RATE = 16000


def _noise(seconds, sigma=0.02, seed=0):
    return (np.random.default_rng(seed).standard_normal(int(seconds * RATE)) * sigma).astype(
        np.float32
    )


def _tone(seconds, amplitude=0.3, freq=1000):
    t = np.arange(int(seconds * RATE)) / RATE
    return (amplitude * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def _rms_db(audio):
    return 20 * np.log10(np.sqrt(np.mean(audio.astype(np.float64) ** 2)) + 1e-12)


def _chunked(reducer, audio, size):
    parts = [reducer.process(audio[i : i + size]) for i in range(0, len(audio), size)]
    return np.concatenate(parts)


@pytest.mark.parametrize("size", [0, 1, 100, 255, 256, 257, 512, 1000, 4801])
def test_output_has_same_length_and_dtype_as_input(size):
    reducer = NoiseReducer(RATE)

    out = reducer.process(_noise(1)[:size])

    assert out.shape == (size,)
    assert out.dtype == np.float32


def test_delay_samples_is_frame_size():
    assert NoiseReducer(RATE).delay_samples == 512


@pytest.mark.parametrize("size", [1, 7, 100, 255, 256, 257, 1000])
def test_chunked_output_matches_one_shot(size):
    audio = _noise(1) + _tone(1)
    expected = NoiseReducer(RATE).process(audio)

    actual = _chunked(NoiseReducer(RATE), audio, size)

    np.testing.assert_allclose(actual, expected, atol=1e-5)


def test_empty_chunks_between_data_do_not_change_output():
    audio = _noise(0.5)
    expected = NoiseReducer(RATE).process(audio)
    reducer = NoiseReducer(RATE)

    parts = []
    for i in range(0, len(audio), 300):
        parts.append(reducer.process(audio[i : i + 300]))
        parts.append(reducer.process(np.zeros(0, dtype=np.float32)))

    np.testing.assert_allclose(np.concatenate(parts), expected, atol=1e-5)


def test_first_delay_samples_of_output_are_zero():
    reducer = NoiseReducer(RATE)

    out = reducer.process(_noise(1))

    assert np.abs(out[: reducer.delay_samples]).max() < 1e-6


def test_white_noise_level_drops_at_least_8_db_after_learning():
    noise = _noise(6)

    out = NoiseReducer(RATE).process(noise)

    drop = _rms_db(noise[3 * RATE :]) - _rms_db(out[3 * RATE :])
    assert drop >= 8


def test_clear_tone_after_learning_noise_keeps_most_of_its_energy():
    tone = np.concatenate([np.zeros(3 * RATE, dtype=np.float32), _tone(3)])
    reducer = NoiseReducer(RATE)

    out = reducer.process(_noise(6) + tone)

    start = 3 * RATE + RATE // 2
    delay = reducer.delay_samples
    expected = tone[start - delay : -delay].astype(np.float64)
    kept = np.sum(out[start:].astype(np.float64) ** 2) / np.sum(expected**2)
    assert kept >= 0.9


def _speech_like(seconds):
    t = np.arange(int(seconds * RATE)) / RATE
    pitch = 130 + 25 * np.sin(2 * np.pi * 0.9 * t)
    phase = 2 * np.pi * np.cumsum(pitch) / RATE
    voice = sum(np.sin(k * phase) / k**1.2 for k in range(1, 55))
    syllables = 0.55 + 0.45 * np.sin(2 * np.pi * 4 * t) ** 2
    syllables[(t % 1.0) >= 0.85] = 0.0
    return (0.03 * voice * syllables).astype(np.float32)


def _band_db(audio, low, high):
    power = np.abs(np.fft.rfft(audio.astype(np.float64))) ** 2
    freqs = np.fft.rfftfreq(len(audio), 1 / RATE)
    return 10 * np.log10(power[(freqs >= low) & (freqs < high)].sum())


def test_long_speech_keeps_its_high_frequencies():
    speech = np.concatenate([np.zeros(RATE, dtype=np.float32), _speech_like(9)])
    reducer = NoiseReducer(RATE)

    out = reducer.process(speech + _noise(10, sigma=0.001))

    delay = reducer.delay_samples
    last_second = slice(9 * RATE, 10 * RATE)
    clean = speech[9 * RATE - delay : 10 * RATE - delay]
    assert _band_db(out[last_second], 3500, 8000) - _band_db(clean, 3500, 8000) > -3


def test_noise_that_gets_louder_is_learned_within_5_seconds():
    quiet = _noise(3, sigma=0.002, seed=1)
    loud = _noise(7, sigma=0.02, seed=2)
    audio = np.concatenate([quiet, loud])

    out = NoiseReducer(RATE).process(audio)

    window = slice(8 * RATE, 9 * RATE)
    assert _rms_db(audio[window]) - _rms_db(out[window]) >= 8


def test_silence_stays_silent_and_finite():
    out = NoiseReducer(RATE).process(np.zeros(RATE, dtype=np.float32))

    assert np.all(out == 0)


def test_tiny_values_stay_finite():
    audio = np.full(RATE, 1e-20, dtype=np.float32)

    out = NoiseReducer(RATE).process(audio)

    assert np.all(np.isfinite(out))


def test_reset_makes_reducer_act_like_a_new_one():
    audio = _noise(1) + _tone(1)
    reducer = NoiseReducer(RATE)
    reducer.process(_noise(2, sigma=0.1, seed=5))
    reducer.reset()

    actual = reducer.process(audio)

    np.testing.assert_allclose(actual, NoiseReducer(RATE).process(audio), atol=1e-6)
