import threading

import numpy as np
import pytest

import voice_clone.audio.pipeline as pipeline_module
from tests.conftest import FakeEngine
from voice_clone.audio.devices import AudioDevice
from voice_clone.audio.pipeline import ConversionPipeline
from voice_clone.errors import DeviceNotFoundError


def _make(engine, in_rate=48000, out_rate=48000, **kwargs):
    inp = AudioDevice(0, "Mic", 1, 0, float(in_rate))
    out = AudioDevice(1, "BlackHole 2ch", 2, 2, float(out_rate))
    return ConversionPipeline(engine, inp, out, **kwargs)


def _block(pipeline, rate):
    frames = rate * 250 // 1000
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
    assert _make(fake_engine).engine_input_length == 12000


@pytest.mark.parametrize("rate", [48000, 44100])
def test_every_convert_call_gets_fixed_length_input(fake_engine, rate):
    pipeline = _make(fake_engine, in_rate=rate, out_rate=rate)

    for _ in range(60):
        pipeline.process_block(_block(pipeline, rate))

    assert set(fake_engine.convert_lengths) == {12000}


@pytest.mark.parametrize("rate", [48000, 44100])
def test_every_output_block_has_exact_length_and_dtype(fake_engine, rate):
    pipeline = _make(fake_engine, in_rate=rate, out_rate=rate)
    expected = rate * 250 // 1000

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
    hop = np.zeros(pipeline._hop, dtype=np.float32)
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

    assert fake_engine.convert_lengths == [12000]


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
        input_stream.callback(np.full((12000, 1), 0.1, dtype=np.float32), 12000, None, None)

        assert levels.wait(timeout=5)
    finally:
        pipeline.stop()


def test_output_callback_fills_buffer_with_converted_audio(fake_engine, fake_sd):
    levels = threading.Event()
    pipeline = _make(fake_engine, on_levels=lambda i, o: levels.set())
    pipeline.start()
    try:
        FakeStream.instances[0].callback(
            np.full((12000, 1), 0.1, dtype=np.float32), 12000, None, None
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
        def convert(self, audio):
            raise RuntimeError("boom")

    errors: list[Exception] = []
    done = threading.Event()
    pipeline = _make(BrokenEngine(), on_error=lambda e: (errors.append(e), done.set()))
    pipeline.start()
    try:
        FakeStream.instances[0].callback(
            np.full((12000, 1), 0.1, dtype=np.float32), 12000, None, None
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
