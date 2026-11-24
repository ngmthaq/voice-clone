import asyncio
import time
from pathlib import Path

import pytest
from textual.widgets import Button, Checkbox, Input, ProgressBar

import voice_clone.domain.config as config
import voice_clone.views.main_screen as main_screen
import voice_clone.views.train_panel_widget as train_panel
from voice_clone.domain.audio import AudioDevice
from voice_clone.domain.errors import TrainingError, TrainingStoppedError
from voice_clone.views import HomeScreen, MainScreen, TrainScreen
from voice_clone.views.app import VoiceCloneApp
from voice_clone.views.train_panel_widget import STOPPED_MESSAGE, _Event, _parse_paths

MIC = AudioDevice(0, "Mic", 1, 0, 48000.0)
BLACKHOLE = AudioDevice(1, "BlackHole 2ch", 2, 2, 48000.0)


@pytest.fixture
def environment(tmp_path, monkeypatch) -> Path:
    voices = tmp_path / "voices"
    voices.mkdir()
    (tmp_path / "rec.m4a").write_bytes(b"x")
    monkeypatch.setattr(config, "settings_path", lambda: tmp_path / "settings.toml")
    monkeypatch.setattr(main_screen, "voices_dir", lambda: voices)
    monkeypatch.setattr(main_screen, "list_input_devices", lambda: [MIC])
    monkeypatch.setattr(main_screen, "list_output_devices", lambda: [BLACKHOLE])
    monkeypatch.setattr(main_screen, "base_models_present", lambda _: True)
    monkeypatch.setattr(train_panel, "voices_dir", lambda: voices)
    monkeypatch.setattr(train_panel, "training_dir", lambda: tmp_path / "training")
    return tmp_path


def _run(body):
    async def scenario():
        app = VoiceCloneApp()
        async with app.run_test(size=(100, 80)) as pilot:
            await pilot.pause()
            app.screen.query_one("#open-train").press()
            await pilot.pause()
            return await body(app, pilot)

    return asyncio.run(scenario())


async def _press_start(app, pilot, recording: Path) -> None:
    app.screen.query_one("#train-inputs", Input).value = str(recording)
    app.screen.query_one("#train-name", Input).value = "me"
    await pilot.pause()
    app.screen.query_one("#train-button", Button).press()
    await pilot.pause()


async def _wait_until_finished(app, pilot) -> None:
    await app.workers.wait_for_complete()
    await pilot.pause(train_panel.REFRESH_SECONDS * 2)


def _status(app) -> str:
    return str(app.screen.query_one("#train-status").render())


def test_home_opens_each_screen_and_escape_goes_back(environment):
    async def scenario():
        app = VoiceCloneApp()
        async with app.run_test(size=(100, 80)) as pilot:
            await pilot.pause()
            seen = [type(app.screen)]
            for button in ("#open-changer", "#open-train"):
                app.screen.query_one(button).press()
                await pilot.pause()
                seen.append(type(app.screen))
                await pilot.press("escape")
                await pilot.pause()
                seen.append(type(app.screen))
            return seen

    assert asyncio.run(scenario()) == [
        HomeScreen,
        MainScreen,
        HomeScreen,
        TrainScreen,
        HomeScreen,
    ]


def test_start_without_recordings_shows_an_error(environment):
    async def body(app, pilot):
        app.screen.query_one("#train-button", Button).press()
        await pilot.pause()
        return _status(app), app.screen.query_one("#train-panel").running

    status, running = _run(body)

    assert "Add at least one recording" in status
    assert not running


def test_existing_voice_needs_replace_ticked(environment):
    (environment / "voices" / "me").mkdir()
    (environment / "voices" / "me" / "me.pth").write_bytes(b"x")

    async def body(app, pilot):
        await _press_start(app, pilot, environment / "rec.m4a")
        return _status(app)

    assert "already exists" in _run(body)


def test_trained_voice_shows_in_the_voice_changer(environment, monkeypatch):
    seen = {}

    def fake_train(options, applio, training_root, voices_root, report, prepare, pause_hint):
        seen["options"] = options
        report("Step 4/4: Training")
        (voices_root / options.name).mkdir()
        (voices_root / options.name / f"{options.name}.pth").write_bytes(b"x")
        return voices_root / options.name

    monkeypatch.setattr(train_panel, "train_voice", fake_train)

    async def body(app, pilot):
        app.screen.query_one("#train-epochs", Input).value = "50"
        app.screen.query_one("#train-restart", Checkbox).value = True
        await _press_start(app, pilot, environment / "rec.m4a")
        await _wait_until_finished(app, pilot)
        screen = app.screen
        result = (
            _status(app),
            screen.query_one("#train-name").disabled,
            str(screen.query_one("#train-log").lines[0].text),
        )
        await pilot.press("escape")
        await pilot.pause()
        app.screen.query_one("#open-changer").press()
        await pilot.pause()
        return (*result, app.screen.query_one("#voice-select").value)

    status, name_disabled, first_log, voice = _run(body)

    assert seen["options"].epochs == 50
    assert seen["options"].restart is True
    assert seen["options"].inputs == [environment / "rec.m4a"]
    assert "Voice 'me' is ready" in status
    assert voice == "me"
    assert not name_disabled
    assert first_log == "Step 4/4: Training"


def test_stop_training_and_back_is_blocked_while_training(environment, monkeypatch):
    def fake_train(options, applio, *args, **kwargs):
        runner = applio._runner
        while not runner.stopped:
            time.sleep(0.01)
        raise TrainingStoppedError("stopped")

    monkeypatch.setattr(train_panel, "train_voice", fake_train)

    async def body(app, pilot):
        await _press_start(app, pilot, environment / "rec.m4a")
        screen = app.screen
        await pilot.press("escape")
        await pilot.pause()
        during = (
            app.screen is screen,
            screen.query_one("#train-name").disabled,
            str(screen.query_one("#train-button", Button).label),
        )
        screen.query_one("#train-button", Button).press()
        await _wait_until_finished(app, pilot)
        after = (_status(app), str(screen.query_one("#train-button", Button).label))
        await pilot.press("escape")
        await pilot.pause()
        return during, after, type(app.screen)

    during, after, final_screen = _run(body)

    assert during == (True, True, "Stop training")
    assert after == (STOPPED_MESSAGE, "Start training")
    assert final_screen is HomeScreen


def test_training_error_is_shown(environment, monkeypatch):
    def fake_train(*args, **kwargs):
        raise TrainingError("Python 3.12 was not found.")

    monkeypatch.setattr(train_panel, "train_voice", fake_train)

    async def body(app, pilot):
        await _press_start(app, pilot, environment / "rec.m4a")
        await _wait_until_finished(app, pilot)
        return _status(app), app.screen.query_one("#train-progress").display

    status, progress_shown = _run(body)

    assert status == "Error: Python 3.12 was not found."
    assert not progress_shown


def test_epoch_lines_move_the_progress_bar(environment):
    async def body(app, pilot):
        panel = app.screen.query_one("#train-panel")
        panel._target_epochs = 200
        panel._voice_name = "me"
        panel._events.append(_Event("line", "me | epoch=50 | step=1000 | time=10:00:00"))
        await pilot.pause(train_panel.REFRESH_SECONDS * 2)
        bar = app.screen.query_one("#train-progress", ProgressBar)
        return bar.progress, bar.total, _status(app)

    assert _run(body) == (50.0, 200, "Training: epoch 50 of 200")


@pytest.mark.parametrize(
    ("text", "platform", "expected"),
    [
        ("", "darwin", []),
        ("/a/one.m4a /b/two.wav", "darwin", [Path("/a/one.m4a"), Path("/b/two.wav")]),
        ("/a/my\\ voice.m4a", "darwin", [Path("/a/my voice.m4a")]),
        ("'/a/my voice.m4a' /b/x.wav", "darwin", [Path("/a/my voice.m4a"), Path("/b/x.wav")]),
        (
            '"C:\\rec\\my voice.m4a" D:\\x.wav',
            "win32",
            [Path("C:\\rec\\my voice.m4a"), Path("D:\\x.wav")],
        ),
    ],
)
def test_parse_paths(text, platform, expected):
    assert _parse_paths(text, platform) == expected


def test_parse_paths_keeps_an_existing_path_with_spaces_whole(tmp_path):
    folder = tmp_path / "my recordings"
    folder.mkdir()

    assert _parse_paths(str(folder)) == [folder]


def test_training_options_are_saved_and_restored(environment, monkeypatch):
    seen = {}

    def fake_train(options, applio, training_root, voices_root, report, prepare, pause_hint):
        seen["options"] = options
        return voices_root / options.name

    monkeypatch.setattr(train_panel, "train_voice", fake_train)

    async def start(app, pilot):
        app.screen.query_one("#train-epochs", Input).value = "120"
        app.screen.query_one("#train-batch-size", Input).value = "4"
        app.screen.query_one("#train-save-every", Input).value = "5"
        await _press_start(app, pilot, environment / "rec.m4a")
        await _wait_until_finished(app, pilot)

    async def reopen(app, pilot):
        return [
            app.screen.query_one(f"#{field_id}", Input).value
            for field_id in ("train-name", "train-epochs", "train-batch-size", "train-save-every")
        ]

    _run(start)

    assert seen["options"].save_every == 5
    assert _run(reopen) == ["me", "120", "4", "5"]


def _start_blocking_training(monkeypatch):
    release = __import__("threading").Event()

    def fake_train(options, applio, training_root, voices_root, report, prepare, pause_hint):
        release.wait(10)
        return voices_root / options.name

    monkeypatch.setattr(train_panel, "train_voice", fake_train)
    return release


@pytest.mark.parametrize("key", ["q", "r"])
def test_quit_and_restart_need_a_second_press_while_training(environment, monkeypatch, key):
    release = _start_blocking_training(monkeypatch)

    async def body(app, pilot):
        await _press_start(app, pilot, environment / "rec.m4a")
        app.screen.query_one("#train-log").focus()
        await pilot.press(key)
        await pilot.pause()
        after_first = (app.is_running, app.screen.query_one("#train-panel").running)
        await pilot.press(key)
        await pilot.pause()
        release.set()
        return after_first, app.return_value

    after_first, return_value = _run(body)

    assert after_first == (True, True)
    assert return_value == ("restart" if key == "r" else None)


def test_a_different_key_does_not_confirm(environment, monkeypatch):
    release = _start_blocking_training(monkeypatch)

    async def body(app, pilot):
        await _press_start(app, pilot, environment / "rec.m4a")
        app.screen.query_one("#train-log").focus()
        await pilot.press("q")
        await pilot.press("r")
        await pilot.pause()
        still_running = app.is_running
        release.set()
        await _wait_until_finished(app, pilot)
        return still_running

    assert _run(body) is True
