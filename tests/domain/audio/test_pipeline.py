import threading

import numpy as np
import pytest

import voice_clone.domain.audio.pipeline as pipeline_module
from tests.conftest import FakeEngine
from voice_clone.domain.audio.devices import AudioDevice
from voice_clone.domain.audio.pipeline import SETTLE_BLOCKS, ConversionPipeline
from voice_clone.domain.errors import DeviceNotFoundError


def _make(engine, in_rate=48000, out_rate=48000, **kwargs):
    inp = AudioDevice(0, "Mic", 1, 0, float(in_rate))
    out = AudioDevice(1, "BlackHole 2ch", 2, 2, float(out_rate))
    return ConversionPipeline(engine, inp, out, **kwargs)


def _block(pipeline, rate):
    frames = pipeline._input_frames
    return (np.random.default_rng(0).standard_normal(frames) * 0.1).astype(np.float32)


class FakeStream:
    instances: list["FakeStream"] = []
    fail = False

    def __init__(self, **kwargs):
        if FakeStream.fail and type(self) is FakeOutputStream:
            raise RuntimeError("no such device")
        self.callback = kwargs["callback"]
        self.started = False
        self.closed = False
        FakeStream.instances.append(self)

    def start(self):
        self.started = True

    def stop(self):
        pass

    def close(self):
        self.closed = True


class FakeInputStream(FakeStream):
    pass


class FakeOutputStream(FakeStream):
    pass


@pytest.fixture
def fake_sd(monkeypatch):
    FakeStream.instances = []
    FakeStream.fail = False

    class FakeSd:
        InputStream = FakeInputStream
        OutputStream = FakeOutputStream

    monkeypatch.setattr(pipeline_module, "sd", FakeSd)
    return FakeSd


def test_engine_input_length_is_context_plus_hop(fake_engine):
    assert _make(fake_engine).engine_input_length == 16000 * (1000 + 400) // 1000


@pytest.mark.parametrize("rate", [48000, 44100])
def test_every_convert_call_gets_fixed_length_input(fake_engine, rate):
    pipeline = _make(fake_engine, in_rate=rate, out_rate=rate)

    for _ in range(60):
        pipeline.process_block(_block(pipeline, rate))

    assert set(fake_engine.convert_lengths) == {pipeline.engine_input_length}


@pytest.mark.parametrize("rate", [48000, 44100])
def test_every_output_block_has_exact_length_and_dtype(fake_engine, rate):
    pipeline = _make(fake_engine, in_rate=rate, out_rate=rate)
    expected = pipeline._output_frames

    outputs = [pipeline.process_block(_block(pipeline, rate)) for _ in range(60)]

    assert all(o.shape == (expected,) and o.dtype == np.float32 for o in outputs)


def test_constant_engine_output_has_no_jumps_between_blocks():
    engine = FakeEngine(value=0.5)
    pipeline = _make(engine)
    outputs = [pipeline.process_block(_block(pipeline, 48000)) for _ in range(20)]

    stream = np.concatenate(outputs[4:])

    assert np.max(np.abs(np.diff(stream))) < 0.05


def test_crossfade_ramps_previous_tail_down_into_new_block():
    engine = FakeEngine(value=1.0)
    pipeline = _make(engine, crossfade_ms=50)
    pipeline._gate.process = lambda audio: audio
    hop = np.full(pipeline._hop, 0.1, dtype=np.float32)
    pipeline._convert_hop(hop)
    engine.value = 0.0

    head = pipeline._convert_hop(hop)

    fade = head[: len(pipeline._tail)]
    assert fade[0] == pytest.approx(1.0)
    assert np.all(np.diff(fade) < 0)
    assert head[len(fade) :].max() == 0.0


def test_warm_up_calls_engine_with_fixed_length(fake_engine):
    pipeline = _make(fake_engine)

    pipeline.warm_up()

    assert fake_engine.convert_lengths == [pipeline.engine_input_length]


def test_start_opens_and_starts_both_streams(fake_engine, fake_sd):
    pipeline = _make(fake_engine)

    pipeline.start()
    try:
        assert pipeline.is_running
        assert [s.started for s in FakeStream.instances] == [True, True]
    finally:
        pipeline.stop()


def test_stop_closes_streams_and_ends_worker(fake_engine, fake_sd):
    pipeline = _make(fake_engine)
    pipeline.start()

    pipeline.stop()

    assert not pipeline.is_running
    assert all(s.closed for s in FakeStream.instances)


def test_stop_twice_is_safe(fake_engine, fake_sd):
    pipeline = _make(fake_engine)
    pipeline.start()
    pipeline.stop()

    pipeline.stop()

    assert not pipeline.is_running


def test_stop_before_start_is_safe(fake_engine):
    pipeline = _make(fake_engine)

    pipeline.stop()

    assert not pipeline.is_running


def test_running_pipeline_reports_levels_from_input_callback(fake_engine, fake_sd):
    levels = threading.Event()
    pipeline = _make(fake_engine, on_levels=lambda i, o: levels.set())
    pipeline.start()
    try:
        input_stream = FakeStream.instances[0]
        input_stream.callback(np.full((19200, 1), 0.1, dtype=np.float32), 19200, None, None)

        assert levels.wait(timeout=5)
    finally:
        pipeline.stop()


def test_output_callback_fills_buffer_with_converted_audio(fake_engine, fake_sd):
    levels = threading.Event()
    pipeline = _make(fake_engine, on_levels=lambda i, o: levels.set())
    pipeline.start()
    try:
        FakeStream.instances[0].callback(
            np.full((19200, 1), 0.1, dtype=np.float32), 19200, None, None
        )
        levels.wait(timeout=5)
        out = np.zeros((12000, 2), dtype=np.float32)

        FakeStream.instances[1].callback(out, 12000, None, None)

        assert np.abs(out).max() > 0.1
    finally:
        pipeline.stop()


def test_stream_open_failure_raises_device_not_found(fake_engine, fake_sd):
    FakeStream.fail = True
    pipeline = _make(fake_engine)

    with pytest.raises(DeviceNotFoundError):
        pipeline.start()

    assert not pipeline.is_running


def test_engine_error_calls_on_error_and_ends_worker(fake_sd):
    class BrokenEngine(FakeEngine):
        def convert(self, audio, tail=None):
            raise RuntimeError("boom")

    errors: list[Exception] = []
    done = threading.Event()
    pipeline = _make(BrokenEngine(), on_error=lambda e: (errors.append(e), done.set()))
    pipeline.start()
    try:
        FakeStream.instances[0].callback(
            np.full((19200, 1), 0.1, dtype=np.float32), 19200, None, None
        )

        assert done.wait(timeout=5)
        pipeline._worker.join(timeout=5)
        assert not pipeline.is_running
        assert str(errors[0]) == "boom"
    finally:
        pipeline.stop()


def _tone(freq, seconds=2.0, rate=16000):
    t = np.arange(int(seconds * rate)) / rate
    return (0.5 * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def _settled_rms(audio):
    return float(np.sqrt(np.mean(np.square(audio[len(audio) // 2 :]))))


def test_hum_filter_removes_mains_hum(fake_engine):
    pipeline = _make(fake_engine)
    hum = _tone(50)

    filtered = pipeline._remove_hum(hum)

    assert _settled_rms(filtered) < _settled_rms(hum) * 0.02


def test_hum_filter_keeps_voice_frequencies(fake_engine):
    pipeline = _make(fake_engine)
    voice = _tone(200)

    filtered = pipeline._remove_hum(voice)

    assert _settled_rms(filtered) == pytest.approx(_settled_rms(voice), rel=0.05)


def test_hum_filter_is_continuous_across_blocks(fake_engine):
    whole_pipeline, chunked_pipeline = _make(fake_engine), _make(fake_engine)
    audio = _tone(50) + _tone(200)

    whole = whole_pipeline._remove_hum(audio)
    chunked = np.concatenate(
        [chunked_pipeline._remove_hum(chunk) for chunk in np.array_split(audio, 8)]
    )

    np.testing.assert_allclose(chunked, whole, atol=1e-5)


def test_silence_skips_the_engine_and_outputs_zeros(fake_engine):
    pipeline = _make(fake_engine)
    silence = np.zeros(pipeline._input_frames, dtype=np.float32)

    outputs = [pipeline.process_block(silence) for _ in range(10)]

    assert len(fake_engine.convert_lengths) <= 1
    assert np.abs(np.concatenate(outputs[2:])).max() == 0.0


def test_dropped_blocks_are_logged_while_running(fake_engine, caplog):
    pipeline = _make(fake_engine)
    pipeline.dropped_blocks = 2

    with caplog.at_level("WARNING"):
        pipeline._report_drops()
        pipeline._report_drops()

    assert [r.getMessage() for r in caplog.records] == [
        "Conversion fell behind: dropped 2 audio block(s) (total 2)"
    ]


def test_set_context_ms_changes_engine_input_on_next_hop(fake_engine):
    pipeline = _make(fake_engine)
    pipeline._gate.process = lambda hop: hop
    for _ in range(5):
        pipeline.process_block(_block(pipeline, 48000))

    pipeline.set_context_ms(1200)
    fake_engine.convert_lengths.clear()
    for _ in range(5):
        pipeline.process_block(_block(pipeline, 48000))

    assert set(fake_engine.convert_lengths) == {16000 * (1200 + 400) // 1000}


def test_set_context_ms_is_clamped(fake_engine):
    pipeline = _make(fake_engine)

    pipeline.set_context_ms(50)

    assert pipeline.engine_input_length == 16000 * (200 + 400) // 1000


def test_pipeline_asks_engine_only_for_hop_plus_crossfade():
    class TailEngine(FakeEngine):
        tails: list = []

        def convert(self, audio, tail=None):
            self.tails.append(tail)
            return super().convert(audio, tail)

    engine = TailEngine()
    pipeline = _make(engine)
    pipeline._gate.process = lambda hop: hop

    pipeline.process_block(_block(pipeline, 48000))

    assert set(engine.tails) == {16000 * (400 + 80) // 1000}


def test_full_queue_drops_oldest_block_and_keeps_newest(fake_engine):
    pipeline = _make(fake_engine)
    blocks = [np.full((10, 1), float(i), dtype=np.float32) for i in range(4)]

    for block in blocks:
        pipeline._input_callback(block, 10, None, None)

    queued = [pipeline._queue.get_nowait()[0] for _ in range(pipeline._queue.qsize())]
    assert queued == [2.0, 3.0]
    assert pipeline.dropped_blocks == 2


def test_worker_caps_output_backlog_and_measures_load(fake_engine, fake_sd):
    blocks = threading.Semaphore(0)
    pipeline = _make(fake_engine, on_levels=lambda i, o: blocks.release())
    pipeline._ring.write(np.ones(pipeline._output_frames * 3, dtype=np.float32))
    pipeline.start()
    try:
        pipeline._ring.write(np.ones(pipeline._output_frames * 3, dtype=np.float32))
        for _ in range(SETTLE_BLOCKS + 1):
            FakeStream.instances[0].callback(
                np.full((19200, 1), 0.1, dtype=np.float32), 19200, None, None
            )
            assert blocks.acquire(timeout=5)

        assert pipeline._ring.available <= pipeline._output_frames * 2
        assert pipeline.load > 0
    finally:
        pipeline.stop()


def test_first_blocks_after_start_do_not_count_as_load(fake_engine):
    pipeline = _make(fake_engine, block_ms=400)
    slow_start = [1.2] * SETTLE_BLOCKS

    for seconds in slow_start:
        pipeline._update_load(seconds)
    settled_load = pipeline.load
    pipeline._update_load(0.2)

    assert settled_load == 0.0
    assert pipeline.load == pytest.approx(0.5)


def test_start_waits_for_settling_again(fake_engine, fake_sd):
    pipeline = _make(fake_engine, block_ms=400)
    for _ in range(SETTLE_BLOCKS + 1):
        pipeline._update_load(0.2)
    pipeline.start()
    pipeline.stop()

    pipeline._update_load(1.2)

    assert pipeline.load == 0.0


def test_hum_filter_zero_turns_it_off(fake_engine):
    pipeline = _make(fake_engine, hum_filter_hz=0)
    audio = _tone(50)

    assert np.array_equal(pipeline._remove_hum(audio), audio)


def test_crossfade_is_never_longer_than_a_block(fake_engine):
    pipeline = _make(fake_engine, block_ms=100, crossfade_ms=200)

    assert pipeline._crossfade_samples == pipeline._hop


def test_noise_reduction_on_runs_reducer_on_each_block(fake_engine, monkeypatch):
    pipeline = _make(fake_engine, noise_reduction=True)
    calls = []
    original = pipeline._reducer.process
    monkeypatch.setattr(
        pipeline._reducer, "process", lambda audio: calls.append(len(audio)) or original(audio)
    )

    pipeline.process_block(_block(pipeline, 48000))

    assert len(calls) == 1


def test_noise_reduction_off_skips_reducer(fake_engine, monkeypatch):
    pipeline = _make(fake_engine, noise_reduction=False)
    calls = []
    monkeypatch.setattr(pipeline._reducer, "process", lambda audio: calls.append(1) or audio)

    pipeline.process_block(_block(pipeline, 48000))

    assert calls == []


def test_noise_reduction_can_be_switched_while_running(fake_engine, monkeypatch):
    pipeline = _make(fake_engine, noise_reduction=True)
    calls = []
    original = pipeline._reducer.process
    monkeypatch.setattr(
        pipeline._reducer, "process", lambda audio: calls.append(1) or original(audio)
    )
    block = _block(pipeline, 48000)

    pipeline.set_noise_reduction(False)
    pipeline.process_block(block)
    off_calls = len(calls)
    pipeline.set_noise_reduction(True)
    pipeline.process_block(block)

    assert (off_calls, len(calls)) == (0, 1)


def test_turning_noise_reduction_on_resets_reducer(fake_engine, monkeypatch):
    pipeline = _make(fake_engine, noise_reduction=False)
    resets = []
    monkeypatch.setattr(pipeline._reducer, "reset", lambda: resets.append(1))

    pipeline.set_noise_reduction(True)

    assert resets == [1]


def test_setting_noise_reduction_on_while_already_on_does_not_reset(fake_engine, monkeypatch):
    pipeline = _make(fake_engine, noise_reduction=True)
    resets = []
    monkeypatch.setattr(pipeline._reducer, "reset", lambda: resets.append(1))

    pipeline.set_noise_reduction(True)

    assert resets == []
