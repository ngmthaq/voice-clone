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


def test_white_noise_level_drops_at_least_10_db_after_learning():
    noise = _noise(6)

    out = NoiseReducer(RATE).process(noise)

    drop = _rms_db(noise[3 * RATE :]) - _rms_db(out[3 * RATE :])
    assert drop >= 10


def test_clear_tone_after_learning_noise_keeps_most_of_its_energy():
    tone = np.concatenate([np.zeros(3 * RATE, dtype=np.float32), _tone(3)])
    reducer = NoiseReducer(RATE)

    out = reducer.process(_noise(6) + tone)

    start = 3 * RATE + RATE // 2
    delay = reducer.delay_samples
    expected = tone[start - delay : -delay].astype(np.float64)
    kept = np.sum(out[start:].astype(np.float64) ** 2) / np.sum(expected**2)
    assert kept >= 0.9


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
