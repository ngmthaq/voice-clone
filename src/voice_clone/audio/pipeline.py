import logging
import queue
import threading
import time
from collections.abc import Callable
from typing import Any, Protocol

import numpy as np
import sounddevice as sd
import soxr
from scipy.signal import butter, sosfilt

from voice_clone.audio.devices import AudioDevice
from voice_clone.audio.noise_gate import GateSettings, NoiseGate
from voice_clone.audio.ring_buffer import RingBuffer
from voice_clone.errors import DeviceNotFoundError

logger = logging.getLogger(__name__)

LevelCallback = Callable[[float, float], None]
ErrorCallback = Callable[[Exception], None]

ENGINE_INPUT_RATE = 16000
# Small on purpose: if conversion falls behind, drop the oldest audio instead of building a
# delay that keeps playing after you stop talking.
QUEUE_BLOCKS = 2
RING_BLOCKS = 4
# Converted audio waiting to be played is capped at this many blocks. The microphone and the
# output device run on separate clocks, so without a cap the delay slowly grows.
MAX_OUTPUT_BACKLOG_BLOCKS = 2
# How fast the measured load follows new blocks (0-1; higher reacts faster).
LOAD_SMOOTHING = 0.3
FIFO_PRIME_MS = 50
OUTPUT_PRIME_MS = 40
POLL_SECONDS = 0.1
JOIN_SECONDS = 5.0
# Removes mains hum (50/60 Hz) and rumble below the voice range, like the training data filter.
HUM_FILTER_HZ = 90
HUM_FILTER_ORDER = 8
MIN_CONTEXT_MS = 200
MAX_CONTEXT_MS = 2000


class _Engine(Protocol):
    input_sample_rate: int
    output_sample_rate: int

    def convert(self, audio: np.ndarray, tail: int | None = None) -> np.ndarray: ...


class ConversionPipeline:
    def __init__(
        self,
        engine: _Engine,
        input_device: AudioDevice,
        output_device: AudioDevice,
        on_levels: LevelCallback | None = None,
        on_error: ErrorCallback | None = None,
        block_ms: int = 400,
        context_ms: int = 1000,
        crossfade_ms: int = 80,
        gate_settings: GateSettings | None = None,
    ) -> None:
        self._engine = engine
        self._input_device = input_device
        self._output_device = output_device
        self._on_levels = on_levels
        self._on_error = on_error
        self._gate_settings = gate_settings or GateSettings()
        self._input_rate = int(input_device.default_samplerate)
        self._output_rate = int(output_device.default_samplerate)
        self._engine_in_rate = engine.input_sample_rate
        self._engine_out_rate = engine.output_sample_rate
        self._block_seconds = block_ms / 1000
        self._input_frames = self._input_rate * block_ms // 1000
        self._output_frames = self._output_rate * block_ms // 1000
        self._hop = self._engine_in_rate * block_ms // 1000
        self._context_samples = self._context_length(context_ms)
        self._crossfade_samples = self._engine_in_rate * crossfade_ms // 1000
        self._engine_ratio = self._engine_out_rate / self._engine_in_rate

        self._queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=QUEUE_BLOCKS)
        self._ring = RingBuffer(self._output_frames * RING_BLOCKS)
        self._stop_event = threading.Event()
        self._worker: threading.Thread | None = None
        self._streams: list[Any] = []
        self.dropped_blocks = 0
        self._reported_drops = 0
        # Conversion time divided by the audio length (smoothed). Above 1.0 the computer is
        # too slow for the current settings and audio gets dropped.
        self.load = 0.0

        self._reset_state()

    @property
    def engine_input_length(self) -> int:
        return self._context_samples + self._hop

    @property
    def _engine_tail(self) -> int:
        return self._hop + self._crossfade_samples

    @property
    def is_running(self) -> bool:
        return self._worker is not None and self._worker.is_alive()

    def start(self) -> None:
        if self._worker is not None:
            return
        self._reset_state()
        self.dropped_blocks = 0
        self._reported_drops = 0
        self.load = 0.0
        self._stop_event.clear()
        self._open_streams()
        self._worker = threading.Thread(
            target=self._run_worker, name="voice-clone-pipeline", daemon=True
        )
        self._worker.start()
        try:
            for stream in self._streams:
                stream.start()
        except Exception as exc:
            self.stop()
            raise DeviceNotFoundError(f"Could not start audio streams: {exc}") from exc

    def stop(self) -> None:
        self._stop_event.set()
        streams, self._streams = self._streams, []
        for stream in streams:
            _close_stream(stream)
        worker, self._worker = self._worker, None
        if worker is not None and worker is not threading.current_thread():
            worker.join(timeout=JOIN_SECONDS)
        if self.dropped_blocks:
            logger.warning("Conversion fell behind: dropped %d audio blocks", self.dropped_blocks)

    def set_gate_settings(self, settings: GateSettings) -> None:
        self._gate_settings = settings
        self._gate.configure(settings)

    def set_context_ms(self, context_ms: int) -> None:
        """Change how much earlier audio the model hears. The next hop uses the new length.

        More context helps the model recognise sounds (clearer words) and adds no delay, but
        each conversion takes longer. If it gets too slow, audio blocks are dropped.
        """
        self._context_samples = self._context_length(context_ms)

    def _context_length(self, context_ms: int) -> int:
        context_ms = max(MIN_CONTEXT_MS, min(MAX_CONTEXT_MS, int(context_ms)))
        return self._engine_in_rate * context_ms // 1000

    def warm_up(self) -> None:
        self._engine.convert(
            np.zeros(self.engine_input_length, dtype=np.float32), tail=self._engine_tail
        )

    def process_block(self, block: np.ndarray) -> np.ndarray:
        block16 = self._input_resampler.resample_chunk(np.asarray(block, dtype=np.float32))
        block16 = self._remove_hum(block16)
        self._fifo = np.concatenate([self._fifo, block16])
        bodies: list[np.ndarray] = []
        while len(self._fifo) >= self._hop:
            hop, self._fifo = self._fifo[: self._hop], self._fifo[self._hop :]
            bodies.append(self._convert_hop(hop))
        if not bodies:
            return self._take_output_block(np.zeros(0, dtype=np.float32))
        resampled = self._output_resampler.resample_chunk(np.concatenate(bodies))
        return self._take_output_block(resampled)

    def _remove_hum(self, audio: np.ndarray) -> np.ndarray:
        if len(audio) == 0:
            return audio
        filtered, self._hum_state = sosfilt(self._hum_sos, audio, zi=self._hum_state)
        return filtered.astype(np.float32, copy=False)

    def _convert_hop(self, hop: np.ndarray) -> np.ndarray:
        hop = self._gate.process(hop)
        context = self._context_samples  # read once: the UI thread may change it
        engine_input = np.concatenate([_fit_history(self._history, context), hop])
        self._history = engine_input[len(engine_input) - context :]
        body_len = round(self._hop * self._engine_ratio)

        silent = not hop.any()
        if silent and self._last_hop_silent:
            # The model turns silence into faint noise, so output true silence instead.
            # The first silent hop still runs, so the last word fades out naturally.
            self._tail = np.zeros_like(self._tail)
            return np.zeros(body_len, dtype=np.float32)
        self._last_hop_silent = silent

        # Only the new hop plus the crossfade is played, so only that much is synthesized.
        converted = np.asarray(
            self._engine.convert(engine_input, tail=self._engine_tail), dtype=np.float32
        )
        fade_len = len(self._tail)
        segment = _tail_or_pad(converted, body_len + fade_len)

        head = segment[:body_len].copy()
        if fade_len:
            ramp = np.linspace(0.0, 1.0, fade_len, endpoint=False, dtype=np.float32)
            head[:fade_len] = self._tail * (1.0 - ramp) + head[:fade_len] * ramp
        self._tail = segment[body_len:].copy()
        return head

    def _reset_state(self) -> None:
        self._input_resampler = soxr.ResampleStream(
            self._input_rate, self._engine_in_rate, 1, dtype="float32"
        )
        self._output_resampler = soxr.ResampleStream(
            self._engine_out_rate, self._output_rate, 1, dtype="float32"
        )
        self._hum_sos = butter(
            HUM_FILTER_ORDER, HUM_FILTER_HZ, btype="highpass", fs=self._engine_in_rate, output="sos"
        )
        self._hum_state = np.zeros((self._hum_sos.shape[0], 2))
        self._gate = NoiseGate(self._engine_in_rate, self._gate_settings)
        self._last_hop_silent = False
        self._history = np.zeros(self._context_samples, dtype=np.float32)
        self._fifo = np.zeros(self._engine_in_rate * FIFO_PRIME_MS // 1000, dtype=np.float32)
        fade_len = round(self._crossfade_samples * self._engine_ratio)
        self._tail = np.zeros(fade_len, dtype=np.float32)
        self._pending = np.zeros(self._output_rate * OUTPUT_PRIME_MS // 1000, dtype=np.float32)
        self._drain_queue()
        self._ring.clear()

    def _take_output_block(self, resampled: np.ndarray) -> np.ndarray:
        pending = np.concatenate([self._pending, resampled.astype(np.float32, copy=False)])
        n = self._output_frames
        if len(pending) < n:
            pending = np.concatenate([pending, np.zeros(n - len(pending), dtype=np.float32)])
        self._pending = pending[n:]
        return pending[:n]

    def _drain_queue(self) -> None:
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                return

    def _open_streams(self) -> None:
        in_device, out_device = self._input_device, self._output_device
        opened: list[Any] = []
        try:
            opened.append(
                sd.InputStream(
                    device=in_device.index,
                    channels=1,
                    samplerate=self._input_rate,
                    blocksize=self._input_frames,
                    dtype="float32",
                    callback=self._input_callback,
                )
            )
            opened.append(
                sd.OutputStream(
                    device=out_device.index,
                    channels=min(2, out_device.max_output_channels),
                    samplerate=self._output_rate,
                    blocksize=self._output_frames,
                    dtype="float32",
                    callback=self._output_callback,
                )
            )
        except Exception as exc:
            for stream in opened:
                _close_stream(stream)
            failed = out_device if opened else in_device
            raise DeviceNotFoundError(
                f"Could not open audio device '{failed.name}': {exc}"
            ) from exc
        self._streams = opened

    def _input_callback(self, indata: np.ndarray, frames: int, time_info: Any, status: Any) -> None:
        block = indata[:, 0].copy()
        try:
            self._queue.put_nowait(block)
        except queue.Full:
            # Behind: throw away the oldest waiting block, so what is played stays recent.
            self.dropped_blocks += 1
            try:
                self._queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self._queue.put_nowait(block)
            except queue.Full:
                pass

    def _output_callback(
        self, outdata: np.ndarray, frames: int, time_info: Any, status: Any
    ) -> None:
        outdata[:] = self._ring.read(frames)[:, None]

    def _update_load(self, seconds: float) -> None:
        ratio = seconds / self._block_seconds
        self.load = self.load + LOAD_SMOOTHING * (ratio - self.load) if self.load else ratio

    def _report_drops(self) -> None:
        dropped = self.dropped_blocks
        if dropped != self._reported_drops:
            logger.warning(
                "Conversion fell behind: dropped %d audio block(s) (total %d)",
                dropped - self._reported_drops,
                dropped,
            )
            self._reported_drops = dropped

    def _run_worker(self) -> None:
        while not self._stop_event.is_set():
            try:
                block = self._queue.get(timeout=POLL_SECONDS)
            except queue.Empty:
                continue
            try:
                started = time.perf_counter()
                output = self.process_block(block)
                self._update_load(time.perf_counter() - started)
                self._ring.write(output)
                self._ring.trim(self._output_frames * MAX_OUTPUT_BACKLOG_BLOCKS)
                self._report_drops()
                if self._on_levels is not None:
                    self._on_levels(_rms(block), _rms(output))
            except Exception as exc:
                logger.exception("Conversion pipeline failed")
                if self._on_error is not None:
                    self._on_error(exc)
                return


def _fit_history(history: np.ndarray, length: int) -> np.ndarray:
    """Keep the newest `length` samples, padding older missing audio with silence."""
    if len(history) >= length:
        return history[len(history) - length :]
    return np.concatenate([np.zeros(length - len(history), dtype=np.float32), history])


def _tail_or_pad(audio: np.ndarray, length: int) -> np.ndarray:
    if len(audio) >= length:
        return audio[len(audio) - length :]
    return np.concatenate([np.zeros(length - len(audio), dtype=np.float32), audio])


def _rms(audio: np.ndarray) -> float:
    if len(audio) == 0:
        return 0.0
    value = float(np.sqrt(np.mean(np.square(audio, dtype=np.float64))))
    return min(1.0, max(0.0, value))


def _close_stream(stream: Any) -> None:
    for action in (stream.stop, stream.close):
        try:
            action()
        except Exception:
            logger.debug("Error while closing audio stream", exc_info=True)
