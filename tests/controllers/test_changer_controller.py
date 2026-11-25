import logging
import tomllib

import pytest
import torch

import voice_clone.controllers.changer_controller as cc
import voice_clone.domain.config as config
from tests.conftest import FakeEngine
from voice_clone.controllers.changer_controller import ChangerController, StartRequest
from voice_clone.domain.audio import AudioDevice

MIC = AudioDevice(0, "Mic", 1, 0, 48000.0)
MIC2 = AudioDevice(2, "Other Mic", 1, 0, 48000.0)
BLACKHOLE = AudioDevice(1, "BlackHole 2ch", 2, 2, 48000.0)
SPEAKERS = AudioDevice(3, "Speakers", 0, 2, 48000.0)


class FakeTimer:
    def __init__(self, delay, callback) -> None:
        self.delay = delay
        self.callback = callback
        self.stopped = False

    def stop(self) -> None:
        self.stopped = True


class TimerLog:
    def __init__(self) -> None:
        self.timers: list[FakeTimer] = []

    def __call__(self, delay, callback) -> FakeTimer:
        timer = FakeTimer(delay, callback)
        self.timers.append(timer)
        return timer


class EngineStub(FakeEngine):
    def __init__(self) -> None:
        super().__init__()
        self.loaded: list[str] = []
        self.pitches: list[int] = []

    def load(self, profile) -> None:
        self.loaded.append(profile.name)

    def set_pitch(self, semitones) -> None:
        self.pitches.append(semitones)


class FakePipeline:
    instances: list["FakePipeline"] = []
    stop_hook = None

    def __init__(self, engine, input_device, output_device, **kwargs) -> None:
        self.kwargs = kwargs
        self.calls: list[str] = []
        self.load = 0.0
        self.dropped_blocks = 0
        FakePipeline.instances.append(self)

    def warm_up(self) -> None:
        self.calls.append("warm_up")

    def start(self) -> None:
        self.calls.append("start")

    def stop(self) -> None:
        self.calls.append("stop")
        if FakePipeline.stop_hook:
            FakePipeline.stop_hook()

    def set_context_ms(self, value) -> None:
        pass

    def set_gate_settings(self, settings) -> None:
        pass

    def set_noise_reduction(self, on) -> None:
        self.calls.append(f"noise_reduction={on}")


def make_voice(voices, name):
    folder = voices / name
    folder.mkdir(parents=True)
    (folder / "model.pth").write_bytes(b"x")


@pytest.fixture
def env(tmp_path, monkeypatch):
    voices = tmp_path / "voices"
    voices.mkdir()
    settings_file = tmp_path / "settings.toml"
    monkeypatch.setattr(config, "settings_path", lambda: settings_file)
    monkeypatch.setattr(cc, "voices_dir", lambda: voices)
    monkeypatch.setattr(cc, "list_input_devices", lambda: [MIC, MIC2])
    monkeypatch.setattr(cc, "list_output_devices", lambda: [SPEAKERS, BLACKHOLE])
    monkeypatch.setattr(cc, "select_torch_device", lambda: torch.device("mps"))
    monkeypatch.setattr(cc, "base_models_present", lambda _: True)
    monkeypatch.setattr(cc, "ConversionPipeline", FakePipeline)
    FakePipeline.instances = []
    FakePipeline.stop_hook = None
    return voices, settings_file


@pytest.fixture
def timers() -> TimerLog:
    return TimerLog()


@pytest.fixture
def loaded(env, timers):
    voices, _ = env
    make_voice(voices, "alice")
    make_voice(voices, "bob")
    controller = ChangerController(timers)
    controller.load()
    return controller


def saved_toml(path) -> dict:
    return tomllib.loads(path.read_text())


def test_load_lists_voices_found_in_voices_folder(loaded):
    assert loaded.voice_names == ["alice", "bob"]


def test_load_defaults_to_first_input_virtual_output_and_first_voice(loaded):
    assert (loaded.input_name, loaded.output_name, loaded.voice_name) == (
        "Mic",
        "BlackHole 2ch",
        "alice",
    )


def test_load_prefers_saved_device_and_voice_names(env, timers):
    voices, _ = env
    make_voice(voices, "alice")
    make_voice(voices, "bob")
    config.save_settings(
        config.Settings(input_device="Other Mic", output_device="Speakers", profile="bob")
    )
    controller = ChangerController(timers)

    controller.load()

    assert (controller.input_name, controller.output_name, controller.voice_name) == (
        "Other Mic",
        "Speakers",
        "bob",
    )


def test_load_without_voices_leaves_voice_unset(env, timers):
    controller = ChangerController(timers)

    controller.load()

    assert controller.voice_names == [] and controller.voice_name is None


def test_nothing_is_saved_before_load(env, timers):
    _, settings_file = env
    controller = ChangerController(timers)

    controller.change_pitch(3)
    controller.flush_save()

    assert timers.timers == [] and not settings_file.exists()


def test_initial_status_without_voices_is_no_voices_warning(env, timers):
    controller = ChangerController(timers)
    controller.load()

    assert controller.initial_status() == (cc.NO_VOICES_MESSAGE, "warning")


def test_initial_status_without_virtual_device_is_warning(env, timers, monkeypatch):
    voices, _ = env
    make_voice(voices, "alice")
    monkeypatch.setattr(cc, "list_output_devices", lambda: [SPEAKERS])
    controller = ChangerController(timers)
    controller.load()

    assert controller.initial_status() == (cc.NO_VIRTUAL_DEVICE_MESSAGE, "warning")


def test_initial_status_is_ready_when_all_present(loaded):
    assert loaded.initial_status() == cc.READY_STATUS


def test_begin_start_returns_request_and_loading_status(loaded):
    request, status = loaded.begin_start()

    assert isinstance(request, StartRequest)
    assert (request.input_device, request.output_device) == (MIC, BLACKHOLE)
    assert (request.profile.name, request.pitch) == ("alice", 0)
    assert status == cc.LOADING_STATUS and loaded.working


def test_begin_start_without_voice_warns_no_voices(env, timers):
    controller = ChangerController(timers)
    controller.load()

    request, status = controller.begin_start()

    assert request is None and status == (cc.NO_VOICES_MESSAGE, "warning")


def test_begin_start_without_output_warns_no_virtual_device(loaded):
    loaded.select_output(None)

    request, status = loaded.begin_start()

    assert request is None and status == (cc.NO_VIRTUAL_DEVICE_MESSAGE, "warning")


def test_begin_start_without_input_is_error(loaded):
    loaded.select_input(None)

    request, status = loaded.begin_start()

    assert request is None and status == ("Error: Select a microphone first.", "error")


def test_begin_start_checks_voice_before_output_and_input(loaded):
    loaded.select_voice(None)
    loaded.select_output(None)
    loaded.select_input(None)

    _, status = loaded.begin_start()

    assert status == (cc.NO_VOICES_MESSAGE, "warning")


def test_start_pipeline_warms_up_then_starts(loaded):
    engine = EngineStub()
    loaded._engine = engine
    request, _ = loaded.begin_start()

    pipeline = loaded.start_pipeline(request)

    assert pipeline.calls == ["warm_up", "start"]
    assert engine.loaded == ["alice"] and engine.pitches == [0]


def test_start_pipeline_loads_same_voice_only_once(loaded):
    engine = EngineStub()
    loaded._engine = engine
    request, _ = loaded.begin_start()

    loaded.start_pipeline(request)
    loaded.start_pipeline(request)

    assert engine.loaded == ["alice"]


def test_start_succeeded_sets_converting_and_running_status(loaded):
    request, _ = loaded.begin_start()
    loaded._engine = EngineStub()
    pipeline = loaded.start_pipeline(request)

    status = loaded.start_succeeded(pipeline)

    assert status == cc.RUNNING_STATUS
    assert loaded.converting and not loaded.working


def test_stop_stops_pipeline_and_returns_ready(loaded):
    loaded._engine = EngineStub()
    request, _ = loaded.begin_start()
    pipeline = loaded.start_pipeline(request)
    loaded.start_succeeded(pipeline)

    status = loaded.stop()

    assert status == cc.READY_STATUS
    assert pipeline.calls[-1] == "stop" and not loaded.converting


def test_levels_are_zero_after_stop_even_if_pipeline_reports_while_stopping(loaded):
    loaded._engine = EngineStub()
    request, _ = loaded.begin_start()
    pipeline = loaded.start_pipeline(request)
    loaded.start_succeeded(pipeline)
    FakePipeline.stop_hook = lambda: loaded._store_levels(0.2, 0.2)
    loaded._store_levels(0.2, 0.2)

    loaded.stop_pipeline()

    state = loaded.tick()
    assert (state.input_level, state.output_level) == (0.0, 0.0)


def test_store_levels_is_ignored_when_not_converting(loaded):
    loaded._store_levels(0.4, 0.4)

    state = loaded.tick()

    assert (state.input_level, state.output_level) == (0.0, 0.0)


def test_store_levels_and_error_only_set_fields_without_logging(loaded, caplog):
    loaded._converting = True

    with caplog.at_level(logging.DEBUG):
        loaded._store_levels(0.3, 0.1)
        loaded._store_error(RuntimeError("boom"))

    assert caplog.records == []
    assert (loaded._input_level, loaded._output_level) == (0.3, 0.1)
    assert str(loaded._pipeline_error) == "boom"


def test_start_failed_returns_error_and_clears_flags(loaded):
    loaded.begin_start()

    status = loaded.start_failed("no model")

    assert status == ("Error: no model", "error")
    assert not loaded.working and not loaded.converting


def test_tick_with_pipeline_error_returns_stop_message_and_clears_error(loaded):
    loaded._converting = True
    loaded._store_error(RuntimeError("device lost"))

    first = loaded.tick()
    second = loaded.tick()

    assert first.stop_message == "device lost"
    assert second.stop_message is None


def test_tick_with_blank_error_message_uses_type_name(loaded):
    loaded._converting = True
    loaded._store_error(RuntimeError())

    assert loaded.tick().stop_message == "RuntimeError"


def start_running(controller) -> FakePipeline:
    controller._engine = EngineStub()
    request, _ = controller.begin_start()
    pipeline = controller.start_pipeline(request)
    controller.start_succeeded(pipeline)
    return pipeline


def test_tick_warns_slow_with_percent_once_per_run(loaded):
    pipeline = start_running(loaded)
    pipeline.load = 0.95

    first = loaded.tick()
    second = loaded.tick()

    assert first.status is not None
    assert "95%" in first.status[0] and "dropped" not in first.status[0]
    assert first.status[1] == "warning"
    assert second.status is None


def test_tick_slow_warning_mentions_dropped_blocks(loaded):
    pipeline = start_running(loaded)
    pipeline.dropped_blocks = 3

    status = loaded.tick().status

    assert status is not None and "3 block(s) dropped" in status[0]


def test_tick_has_no_status_when_fast(loaded):
    pipeline = start_running(loaded)
    pipeline.load = 0.5

    assert loaded.tick().status is None


def test_slow_warning_repeats_in_a_new_run(loaded):
    pipeline = start_running(loaded)
    pipeline.load = 0.95
    loaded.tick()
    loaded.stop()
    pipeline = start_running(loaded)
    pipeline.load = 0.95

    assert loaded.tick().status is not None


def test_pipeline_receives_store_callbacks(loaded):
    pipeline = start_running(loaded)

    assert pipeline.kwargs["on_levels"] == loaded._store_levels
    assert pipeline.kwargs["on_error"] == loaded._store_error


def test_change_pitch_clamps_to_range(loaded):
    loaded.change_pitch(40)
    high = loaded.pitch
    loaded.change_pitch(-40)

    assert (high, loaded.pitch) == (12, -12)


def test_change_pitch_updates_running_engine(loaded):
    start_running(loaded)

    loaded.change_pitch(5)

    assert loaded._engine.pitches[-1] == 5


def test_change_pitch_does_not_touch_engine_when_not_converting(loaded):
    loaded._engine = EngineStub()

    loaded.change_pitch(5)

    assert loaded._engine.pitches == []


def test_change_schedules_one_timer_with_save_delay(loaded, timers):
    loaded.change_pitch(2)

    assert [timer.delay for timer in timers.timers] == [cc.SAVE_DELAY_SECONDS]


def test_second_change_stops_the_first_timer(loaded, timers):
    loaded.change_pitch(2)
    loaded.change_pitch(3)

    first, second = timers.timers
    assert first.stopped and not second.stopped


def test_nothing_is_written_until_flush(loaded, env):
    _, settings_file = env

    loaded.change_pitch(4)

    assert not settings_file.exists()


def test_flush_writes_new_value_and_keeps_other_saved_keys(loaded, env):
    _, settings_file = env
    config.save_settings(config.Settings(train_name="my-voice"))
    loaded.change_pitch(4)

    loaded.flush_save()

    saved = saved_toml(settings_file)
    assert saved["pitch"] == 4 and saved["train_name"] == "my-voice"


def test_timer_callback_flushes_the_save(loaded, timers, env):
    _, settings_file = env
    loaded.select_voice("bob")

    timers.timers[-1].callback()

    assert saved_toml(settings_file)["profile"] == "bob"


def test_flush_without_pending_change_writes_nothing(loaded, env):
    _, settings_file = env

    loaded.flush_save()

    assert not settings_file.exists()


def test_flush_logs_warning_and_does_not_raise_on_os_error(loaded, monkeypatch, caplog):
    def fail(_):
        raise OSError("disk full")

    monkeypatch.setattr(cc, "save_settings", fail)
    loaded.change_pitch(1)

    with caplog.at_level(logging.WARNING):
        loaded.flush_save()

    assert any("Could not save settings" in r.message for r in caplog.records)


def test_select_preset_ultra_sets_options_gate_and_preset_key(loaded):
    expected_options = config.PERFORMANCE_PRESETS["ultra"][1]

    applied = loaded.select_preset("ultra")

    assert applied and loaded.preset_key == "ultra"
    assert loaded.voice_options["block_ms"] == int(expected_options["block_ms"])
    assert loaded.gate.hold_ms == expected_options["gate_hold_ms"]


def test_select_unknown_preset_returns_false(loaded):
    assert loaded.select_preset("nope") is False


def test_reset_advanced_restores_default_options(loaded):
    loaded.set_voice_option("block_ms", 999)

    loaded.reset_advanced()

    assert loaded.voice_options["block_ms"] == int(config.Settings().block_ms)


def test_set_gate_value_updates_gate_and_schedules_save(loaded, timers):
    loaded.set_gate_value("hold_ms", "250")

    assert loaded.gate.hold_ms == 250 and len(timers.timers) == 1


def test_first_start_on_cpu_without_saved_settings_uses_minimal_preset(env, timers, monkeypatch):
    monkeypatch.setattr(cc, "select_torch_device", lambda: torch.device("cpu"))
    controller = ChangerController(timers)
    controller.load()

    assert controller.preset_key == cc.FIRST_START_CPU_PRESET


def test_saved_settings_win_over_first_start_cpu_preset(env, timers, monkeypatch):
    monkeypatch.setattr(cc, "select_torch_device", lambda: torch.device("cpu"))
    config.save_settings(config.Settings(pitch=7))
    controller = ChangerController(timers)

    assert controller.pitch == 7


def test_busy_message_is_none_when_idle(loaded):
    assert loaded.busy_message is None


def test_busy_message_while_loading_voice(loaded):
    loaded.begin_start()

    assert loaded.busy_message == "The voice is loading."


def test_busy_message_while_downloading_models(loaded):
    loaded._models_ready = False
    loaded.begin_download()

    assert loaded.busy_message == "Base models are downloading."


def test_back_status_waits_only_while_working(loaded):
    idle = loaded.back_status()
    loaded.begin_download()

    assert idle is None and loaded.back_status() == cc.WAIT_STATUS


def test_download_failed_returns_error_and_clears_working(loaded):
    loaded.begin_download()

    status = loaded.download_failed("offline")

    assert status == ("Error: offline", "error") and not loaded.working


def test_download_finished_marks_models_ready_and_returns_initial_status(loaded):
    loaded._models_ready = False
    loaded.begin_download()

    status = loaded.download_finished()

    assert status == cc.READY_STATUS
    assert loaded.models_ready and not loaded.working


def test_download_status_prefixes_message(loaded):
    assert loaded.download_status("10%") == ("Downloading… 10%", "")


def test_set_gate_value_open_below_voice_db_is_float_and_saved(loaded, env):
    _, settings_file = env

    loaded.set_gate_value("open_below_voice_db", "12.5")
    loaded.flush_save()

    assert loaded.gate.open_below_voice_db == 12.5
    assert saved_toml(settings_file)["gate_open_below_voice_db"] == 12.5


def test_set_noise_reduction_updates_property_and_is_saved(loaded, env):
    _, settings_file = env

    loaded.set_noise_reduction(False)
    loaded.flush_save()

    assert loaded.noise_reduction is False
    assert saved_toml(settings_file)["noise_reduction"] is False


def test_set_noise_reduction_updates_running_pipeline(loaded):
    pipeline = start_running(loaded)

    loaded.set_noise_reduction(False)

    assert pipeline.calls[-1] == "noise_reduction=False"


def test_start_pipeline_passes_noise_reduction_from_settings(env, timers):
    voices, _ = env
    make_voice(voices, "alice")
    config.save_settings(config.Settings(noise_reduction=False))
    controller = ChangerController(timers)
    controller.load()

    pipeline = start_running(controller)

    assert pipeline.kwargs["noise_reduction"] is False


def test_select_preset_keeps_noise_reduction_and_sets_open_below_voice_db(loaded):
    loaded.set_noise_reduction(False)
    loaded.set_gate_value("open_below_voice_db", "5")

    loaded.select_preset("ultra")

    assert loaded.noise_reduction is False
    assert loaded.gate.open_below_voice_db == 20.0


def test_reset_advanced_restores_noise_reduction_and_open_below_voice_db(loaded):
    loaded.set_noise_reduction(False)
    loaded.set_gate_value("open_below_voice_db", "5")

    loaded.reset_advanced()

    assert loaded.noise_reduction is True
    assert loaded.gate.open_below_voice_db == 20.0


def test_old_settings_without_new_keys_load_defaults(env, timers):
    _, settings_file = env
    settings_file.write_text("gate_hold_ms = 700\n")
    controller = ChangerController(timers)

    controller.load()

    assert controller.gate.open_below_voice_db == 20.0
    assert controller.noise_reduction is True
