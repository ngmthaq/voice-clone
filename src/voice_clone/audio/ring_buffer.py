import threading

import numpy as np


class RingBuffer:
    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self._capacity = capacity
        self._data = np.zeros(capacity, dtype=np.float32)
        self._read_pos = 0
        self._count = 0
        self._lock = threading.Lock()

    @property
    def available(self) -> int:
        with self._lock:
            return self._count

    def write(self, data: np.ndarray) -> int:
        samples = np.asarray(data, dtype=np.float32).reshape(-1)
        written = len(samples)
        if written > self._capacity:
            samples = samples[-self._capacity :]
        n = len(samples)
        with self._lock:
            write_pos = (self._read_pos + self._count) % self._capacity
            first = min(n, self._capacity - write_pos)
            self._data[write_pos : write_pos + first] = samples[:first]
            self._data[: n - first] = samples[first:]
            overflow = self._count + n - self._capacity
            if overflow > 0:
                self._read_pos = (self._read_pos + overflow) % self._capacity
                self._count = self._capacity
            else:
                self._count += n
        return written

    def read(self, n: int) -> np.ndarray:
        out = np.zeros(n, dtype=np.float32)
        with self._lock:
            take = min(n, self._count)
            first = min(take, self._capacity - self._read_pos)
            out[:first] = self._data[self._read_pos : self._read_pos + first]
            out[first:take] = self._data[: take - first]
            self._read_pos = (self._read_pos + take) % self._capacity
            self._count -= take
        return out

    def trim(self, max_samples: int) -> int:
        with self._lock:
            excess = self._count - max(0, max_samples)
            if excess <= 0:
                return 0
            self._read_pos = (self._read_pos + excess) % self._capacity
            self._count -= excess
            return excess

    def clear(self) -> None:
        with self._lock:
            self._read_pos = 0
            self._count = 0
