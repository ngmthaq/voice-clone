import tomllib
from pathlib import Path

import pytest

import voice_clone.controllers.train_controller as tc
import voice_clone.domain.config as config
from voice_clone.controllers.train_controller import (
    DEFAULT_OPTIONS,
    STOPPED_MESSAGE,
    UI_PAUSE_HINT,
    TrainController,
)
from voice_clone.domain.config import Settings
from voice_clone.domain.errors import TrainingStoppedError, VoiceCloneError
from voice_clone.domain.training import TrainOptions


class FakeRunner:
    def __init__(self, on_line=None, on_transient=None) -> None:
        self.on_line = on_line
        self.on_transient = on_transient
        self.stop_calls = 0

    def stop(self) -> None:
        self.stop_calls += 1


class FakeApplio:
    def __init__(self, root, runner=None) -> None:
        self.root = root
        self.runner = runner


@pytest.fixture
def env(tmp_path, monkeypatch) -> Path:
    voices = tmp_path / "voices"
    voices.mkdir()
    (tmp_path / "rec.m4a").write_bytes(b"x")
    monkeypatch.setattr(config, "settings_path", lambda: tmp_path / "settings.toml")
    monkeypatch.setattr(tc, "voices_dir", lambda: voices)
    monkeypatch.setattr(tc, "training_dir", lambda: tmp_path / "training")
    monkeypatch.setattr(tc, "StreamingRunner", FakeRunner)
    monkeypatch.setattr(tc, "Applio", FakeApplio)
    return tmp_path


def check(controller, env, **overrides):
    args = dict(
        inputs_text=str(env / "rec.m4a"),
        name=" me ",
        epochs_text="50",
        sample_rate=32000,
        batch_size_text="4",
        save_every_text="5",
        restart=True,
        force=False,
    )
    args.update(overrides)
    return controller.check_options(**args)


def options(name="me", epochs=200) -> TrainOptions:
    return TrainOptions(name=name, inputs=[], epochs=epochs)


def test_check_options_builds_train_options(env):
    result = check(TrainController(), env)

    assert result == TrainOptions(
        name="me",
        inputs=[env / "rec.m4a"],
        epochs=50,
        sample_rate=32000,
        batch_size=4,
        save_every=5,
        restart=True,
        force=False,
    )


def test_check_options_saves_last_used_settings(env):
    check(TrainController(), env)

    saved = tomllib.loads((env / "settings.toml").read_text())
    assert (
        saved["train_name"],
        saved["train_epochs"],
        saved["train_batch_size"],
        saved["train_sample_rate"],
        saved["train_save_every"],
    ) == ("me", 50, 4, 32000, 5)


def test_form_defaults_come_from_saved_settings(env):
    config.save_settings(
        Settings(
            train_name="saved",
            train_epochs=77,
            train_batch_size=3,
            train_save_every=9,
            train_sample_rate=48000,
        )
    )

    controller = TrainController()

    assert (
        controller.default_name,
        controller.default_epochs,
        controller.default_batch_size,
        controller.default_save_every,
        controller.default_sample_rate((32000, 40000, 48000)),
    ) == ("saved", 77, 3, 9, 48000)


def test_default_sample_rate_falls_back_when_saved_rate_is_not_allowed(env):
    config.save_settings(Settings(train_sample_rate=48000))

    rate = TrainController().default_sample_rate((32000, 40000))

    assert rate == DEFAULT_OPTIONS.sample_rate


def test_check_options_rejects_empty_inputs(env):
    with pytest.raises(VoiceCloneError, match="Add at least one recording"):
        check(TrainController(), env, inputs_text="  ")


def test_check_options_rejects_missing_path(env):
    with pytest.raises(VoiceCloneError, match="does not exist"):
        check(TrainController(), env, inputs_text=str(env / "nope.wav"))


def test_check_options_rejects_non_number_epochs(env):
    with pytest.raises(VoiceCloneError, match="Epochs must be a whole number."):
        check(TrainController(), env, epochs_text="abc")


def test_check_options_rejects_bad_name(env):
    with pytest.raises(VoiceCloneError, match="Voice name may only use"):
        check(TrainController(), env, name="bad name!")


def test_check_options_rejects_existing_voice_without_force(env):
    (env / "voices" / "me").mkdir()
    (env / "voices" / "me" / "x.pth").write_bytes(b"x")

    with pytest.raises(VoiceCloneError, match="A voice named 'me' already exists"):
        check(TrainController(), env)


def test_check_options_accepts_existing_voice_with_force(env):
    (env / "voices" / "me").mkdir()
    (env / "voices" / "me" / "x.pth").write_bytes(b"x")

    result = check(TrainController(), env, force=True)

    assert result.force is True


def test_check_options_survives_a_failed_settings_save(env, monkeypatch):
    def broken_save(settings):
        raise OSError("disk full")

    monkeypatch.setattr(tc, "save_settings", broken_save)

    result = check(TrainController(), env)

    assert result.name == "me"


def test_train_reports_steps_then_done(env, monkeypatch):
    seen = {}

    def fake_train(opts, applio, root, voices_root, report, prepare, pause_hint):
        seen["applio"] = applio
        seen["pause_hint"] = pause_hint
        seen["root"] = root
        report("Step 1/4")

    monkeypatch.setattr(tc, "train_voice", fake_train)
    controller = TrainController()
    controller.start(options())

    controller.train(options())

    assert controller.drain_events() == [("step", "Step 1/4"), ("done", "me")]
    assert seen["pause_hint"] == UI_PAUSE_HINT
    assert seen["applio"].runner is controller._runner
    assert seen["root"] == env / "training"


def test_runner_callbacks_push_line_and_transient_events(env):
    controller = TrainController()
    controller.start(options())

    controller._runner.on_line("hello")
    controller._runner.on_transient("tick")

    assert controller.drain_events() == [("line", "hello"), ("transient", "tick")]


def test_start_sets_running_and_target_epochs(env):
    controller = TrainController()

    controller.start(options(epochs=120))

    assert (controller.running, controller.stopping, controller.target_epochs) == (True, False, 120)


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (TrainingStoppedError("stopped"), ("failed", STOPPED_MESSAGE)),
        (VoiceCloneError("boom"), ("failed", "Error: boom")),
        (RuntimeError("boom"), ("failed", "Error: boom")),
    ],
)
def test_train_turns_errors_into_failed_events(env, monkeypatch, error, expected):
    def fake_train(*args, **kwargs):
        raise error

    monkeypatch.setattr(tc, "train_voice", fake_train)
    controller = TrainController()
    controller.start(options())

    controller.train(options())

    assert controller.drain_events() == [expected]


def test_train_cli_runs_without_runner_report_or_pause_hint(env, monkeypatch):
    seen = {}

    def fake_train(opts, applio, root, voices_root, **kwargs):
        seen.update(opts=opts, applio=applio, root=root, voices_root=voices_root, kwargs=kwargs)

    monkeypatch.setattr(tc, "train_voice", fake_train)
    opts = options()

    TrainController().train_cli(opts)

    assert seen["opts"] is opts
    assert seen["applio"].runner is None
    assert seen["root"] == env / "training"
    assert seen["voices_root"] == env / "voices"
    assert seen["kwargs"] == {}


def test_train_cli_lets_errors_propagate(env, monkeypatch):
    def fake_train(*args, **kwargs):
        raise VoiceCloneError("boom")

    monkeypatch.setattr(tc, "train_voice", fake_train)

    with pytest.raises(VoiceCloneError, match="boom"):
        TrainController().train_cli(options())


def test_drain_events_empties_the_queue(env):
    controller = TrainController()
    controller.start(options())
    controller._runner.on_line("a")

    first = controller.drain_events()
    second = controller.drain_events()

    assert (first, second) == ([("line", "a")], [])


def test_epoch_progress_returns_epochs_done_for_the_voice(env):
    controller = TrainController()
    controller.start(options(name="me", epochs=200))

    progress = controller.epoch_progress("me | epoch=50 | step=1000 | time=10:00:00")

    assert progress == 50.0


def test_epoch_progress_is_capped_at_target_epochs(env):
    controller = TrainController()
    controller.start(options(name="me", epochs=40))

    progress = controller.epoch_progress("me | epoch=50 | step=1000 | time=10:00:00")

    assert progress == 40.0


def test_epoch_progress_ignores_another_voice(env):
    controller = TrainController()
    controller.start(options(name="zed", epochs=200))

    assert controller.epoch_progress("alice | epoch=50 | step=1 | time=1") is None


def test_epoch_progress_ignores_lines_without_an_epoch(env):
    controller = TrainController()
    controller.start(options(name="me", epochs=200))

    assert controller.epoch_progress("me loading data") is None


def test_stop_before_start_returns_false(env):
    assert TrainController().stop() is False


def test_stop_stops_the_runner_once(env):
    controller = TrainController()
    controller.start(options())
    runner = controller._runner

    results = (controller.stop(), controller.stop())

    assert results == (True, False)
    assert runner.stop_calls == 1
    assert controller.stopping is True


def test_finish_clears_running_and_stopping(env):
    controller = TrainController()
    controller.start(options())
    controller.stop()

    controller.finish()

    assert (controller.running, controller.stopping) == (False, False)
    assert controller.stop() is False


def test_stop_on_unmount_stops_an_existing_runner(env):
    controller = TrainController()
    controller.start(options())
    runner = controller._runner

    controller.stop_on_unmount()

    assert runner.stop_calls == 1


def test_stop_on_unmount_without_runner_does_nothing(env):
    TrainController().stop_on_unmount()


def test_busy_message_is_none_when_idle(env):
    controller = TrainController()

    assert controller.busy_message is None


def test_busy_message_reports_training_while_running(env):
    controller = TrainController()

    controller.start(options())

    assert controller.busy_message == "Training is running."


def test_busy_message_is_none_after_finish(env):
    controller = TrainController()
    controller.start(options())

    controller.finish()

    assert controller.busy_message is None


def test_controllers_are_busy_reporters():
    from voice_clone.controllers import (
        BusyReporter,
        ChangerController,
        SetupController,
    )

    assert isinstance(TrainController(), BusyReporter)
    assert isinstance(SetupController(), BusyReporter)
    assert isinstance(ChangerController.__dict__["busy_message"], property)
