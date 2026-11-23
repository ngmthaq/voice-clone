import numpy as np
import pytest

from voice_clone.audio.ring_buffer import RingBuffer


def test_read_returns_written_samples_in_order():
    ring = RingBuffer(8)
    ring.write(np.arange(5, dtype=np.float32))

    out = ring.read(5)

    assert out.tolist() == [0, 1, 2, 3, 4]
    assert ring.available == 0


def test_underrun_zero_pads_the_read():
    ring = RingBuffer(8)
    ring.write(np.array([1, 2], dtype=np.float32))

    out = ring.read(5)

    assert out.tolist() == [1, 2, 0, 0, 0]


def test_overflow_overwrites_oldest_samples():
    ring = RingBuffer(4)
    ring.write(np.array([1, 2, 3], dtype=np.float32))
    ring.write(np.array([4, 5, 6], dtype=np.float32))

    assert ring.read(4).tolist() == [3, 4, 5, 6]


def test_write_larger_than_capacity_keeps_newest_samples():
    ring = RingBuffer(3)

    ring.write(np.arange(10, dtype=np.float32))

    assert ring.read(3).tolist() == [7, 8, 9]


def test_wraparound_preserves_order():
    ring = RingBuffer(4)
    ring.write(np.array([1, 2, 3], dtype=np.float32))
    ring.read(2)
    ring.write(np.array([4, 5, 6], dtype=np.float32))

    assert ring.read(4).tolist() == [3, 4, 5, 6]


def test_clear_empties_buffer():
    ring = RingBuffer(4)
    ring.write(np.ones(3, dtype=np.float32))

    ring.clear()

    assert ring.available == 0


def test_non_positive_capacity_is_rejected():
    with pytest.raises(ValueError):
        RingBuffer(0)


def test_trim_drops_oldest_samples_beyond_limit():
    buffer = RingBuffer(8)
    buffer.write(np.arange(6, dtype=np.float32))

    assert buffer.trim(2) == 4
    assert buffer.read(4).tolist() == [4.0, 5.0, 0.0, 0.0]


def test_trim_below_limit_keeps_everything():
    buffer = RingBuffer(8)
    buffer.write(np.ones(3, dtype=np.float32))

    assert buffer.trim(5) == 0
    assert buffer.available == 3
