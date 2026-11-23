import asyncio
import sys

import pytest
from textual.widgets import Button

import voice_clone.config as config
import voice_clone.ui.setup_screen as setup_screen
from voice_clone.app import VoiceCloneApp
from voice_clone.engine.download import base_model_files
from voice_clone.errors import ModelDownloadError
from voice_clone.setup_check import Facts
from voice_clone.ui import HomeScreen, SetupScreen


@pytest.fixture
def environment(tmp_path, monkeypatch):
    models = tmp_path / "models"
    monkeypatch.setattr(config, "settings_path", lambda: tmp_path / "settings.toml")
    monkeypatch.setattr(setup_screen, "models_dir", lambda: models)

    def facts():
        return Facts(
            platform="darwin",
            machine="arm64",
            python_version=(3, 12, 8),
            models_dir=models,
            model_files=base_model_files(models),
            input_devices=["Mic"],
            output_devices=["BlackHole 2ch"],
            compute="mps",
            voices=["me"],
            ffmpeg=None,
            git="/bin/git",
            python312="/bin/python3.12",
        )

    monkeypatch.setattr(setup_screen, "gather_facts", facts)
    return models


def _fill_models(models_dir, on_progress=None):
    for file in base_model_files(models_dir):
        file.path.parent.mkdir(parents=True, exist_ok=True)
        file.path.write_bytes(b"x")
        if on_progress is not None:
            on_progress(f"Downloaded {file.name}", 1.0)


def _run(body):
    async def scenario():
        app = VoiceCloneApp()
        async with app.run_test(size=(100, 80)) as pilot:
            await pilot.pause()
            app.screen.query_one("#open-setup").press()
            await _settle(app, pilot)
            return await body(app, pilot)

    return asyncio.run(scenario())


async def _settle(app, pilot):
    await pilot.pause()
    await app.workers.wait_for_complete()
    await pilot.pause()


def _status(app):
    return str(app.screen.query_one("#setup-status").render())


def _lines(app):
    return [str(widget.render()) for widget in app.screen.query(".check-line")]


def test_missing_models_show_the_download_button(environment):
    async def body(app, pilot):
        return (
            type(app.screen),
            app.screen.query_one("#download-models").display,
            str(app.screen.query_one("#download-models", Button).label),
            _status(app),
            [line for line in _lines(app) if "Base models" in line],
        )

    screen, button_shown, label, status, model_lines = _run(body)

    assert screen is SetupScreen
    assert button_shown
    assert label == "Download base models (about 560 MB)"
    assert status == "The voice changer needs: base models."
    assert model_lines[0].startswith("✗ Base models: Missing:")


def test_download_fills_the_models_and_checks_again(environment, monkeypatch):
    monkeypatch.setattr(setup_screen, "ensure_base_models", _fill_models)

    async def body(app, pilot):
        app.screen.query_one("#download-models", Button).press()
        await _settle(app, pilot)
        await _settle(app, pilot)
        return app.screen.query_one("#download-models").display, _status(app)

    button_shown, status = _run(body)

    assert not button_shown
    assert status == "The voice changer is ready. Training needs the items marked ✗."


def test_failed_download_shows_the_error_and_retry(environment, monkeypatch):
    def failing(models_dir, on_progress=None):
        raise ModelDownloadError("Could not download rmvpe.pt.")

    monkeypatch.setattr(setup_screen, "ensure_base_models", failing)

    async def body(app, pilot):
        app.screen.query_one("#download-models", Button).press()
        await _settle(app, pilot)
        button = app.screen.query_one("#download-models", Button)
        return _status(app), str(button.label), button.disabled

    assert _run(body) == ("Error: Could not download rmvpe.pt.", "Retry download", False)


def test_everything_ready(environment, monkeypatch):
    _fill_models(environment)
    real = setup_screen.gather_facts

    def ready():
        facts = real()
        facts.ffmpeg = "/bin/ffmpeg"
        facts.applio_installed = True
        return facts

    monkeypatch.setattr(setup_screen, "gather_facts", ready)

    async def body(app, pilot):
        return app.screen.query_one("#download-models").display, _status(app)

    assert _run(body) == (False, "Everything is ready.")


def test_escape_goes_back_home(environment):
    async def body(app, pilot):
        await pilot.press("escape")
        await pilot.pause()
        return type(app.screen)

    assert _run(body) is HomeScreen


class FakeApplio:
    installed = False
    script = "print('cloned Applio', flush=True)"

    def __init__(self, root, runner):
        self._runner = runner

    def ensure_installed(self, report):
        report("Step 1/4: Downloading Applio 3.7.1…")
        self._runner([sys.executable, "-c", self.script])
        FakeApplio.installed = True
        report("Applio 3.7.1 is installed.")


@pytest.fixture
def fake_applio(environment, monkeypatch):
    FakeApplio.installed = False
    FakeApplio.script = "print('cloned Applio', flush=True)"
    monkeypatch.setattr(setup_screen, "Applio", FakeApplio)
    real = setup_screen.gather_facts

    def facts():
        result = real()
        result.applio_installed = FakeApplio.installed
        return result

    monkeypatch.setattr(setup_screen, "gather_facts", facts)
    return FakeApplio


async def _wait_for(pilot, condition, timeout=10.0):
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while not condition() and loop.time() < deadline:
        await pilot.pause(0.05)


def _applio_line(app):
    return next(line for line in _lines(app) if line[2:].startswith("Applio:"))


def test_install_applio_shows_its_output_and_then_checks_again(fake_applio):
    async def body(app, pilot):
        button = app.screen.query_one("#install-applio", Button)
        shown_before = button.display
        button.press()
        await _wait_for(pilot, lambda: fake_applio.installed)
        await pilot.pause(setup_screen.LOG_REFRESH_SECONDS * 2)
        await _settle(app, pilot)
        log = [str(line.text) for line in app.screen.query_one("#applio-log").lines]
        return shown_before, log, _applio_line(app), button.display

    shown_before, log, applio_line, shown_after = _run(body)

    assert shown_before
    assert log == [
        "Step 1/4: Downloading Applio 3.7.1…",
        "cloned Applio",
        "Applio 3.7.1 is installed.",
    ]
    assert applio_line.startswith("✓ Applio")
    assert not shown_after


def test_stop_install_applio(fake_applio):
    fake_applio.script = "import time; print('working', flush=True); time.sleep(30)"

    async def body(app, pilot):
        button = app.screen.query_one("#install-applio", Button)
        button.press()
        await pilot.pause()
        during = (str(button.label), button.disabled, app.screen.query_one("#check-again").disabled)
        await pilot.press("escape")
        await pilot.pause()
        still_here = isinstance(app.screen, SetupScreen)
        button.press()
        await _wait_for(pilot, lambda: _status(app) == setup_screen.APPLIO_STOPPED_MESSAGE)
        return during, still_here, _status(app), str(button.label)

    during, still_here, status, label = _run(body)

    assert during == ("Stop install", False, True)
    assert still_here
    assert status == setup_screen.APPLIO_STOPPED_MESSAGE
    assert label == "Install Applio (several GB)"
    assert not fake_applio.installed


def test_install_applio_is_hidden_without_git(fake_applio, monkeypatch):
    real = setup_screen.gather_facts

    def no_git():
        result = real()
        result.git = None
        return result

    monkeypatch.setattr(setup_screen, "gather_facts", no_git)

    async def body(app, pilot):
        return app.screen.query_one("#install-applio").display

    assert _run(body) is False


def test_measure_speed_hidden_until_models_are_there(environment):
    async def body(app, pilot):
        return app.screen.query_one("#performance-section").display

    assert _run(body) is False


def test_measure_speed_saves_the_best_preset_and_says_so(environment, monkeypatch):
    _fill_models(environment)
    calls = []

    def fake_measure(on_result=None):
        calls.append(True)
        result = setup_screen.bench.BenchResult(300, [0.5, 0.5])
        on_result("balanced", result)
        return "balanced", {"balanced": result}

    monkeypatch.setattr(setup_screen.bench, "measure_and_save", fake_measure)

    async def body(app, pilot):
        button = app.screen.query_one("#measure-speed", Button)
        shown = app.screen.query_one("#performance-section").display
        button.press()
        await _settle(app, pilot)
        return shown, _status(app), button.disabled

    shown, status, disabled = _run(body)

    assert shown and calls and not disabled
    assert status == (
        "This computer keeps up with Balanced (load 0.50). Saved: the Voice changer now uses it."
    )


def test_measure_speed_reports_when_even_minimal_is_too_slow(environment, monkeypatch):
    _fill_models(environment)
    slow = setup_screen.bench.BenchResult(1000, [1.3])
    monkeypatch.setattr(
        setup_screen.bench, "measure_and_save", lambda on_result=None: (None, {"minimal": slow})
    )

    async def body(app, pilot):
        app.screen.query_one("#measure-speed", Button).press()
        await _settle(app, pilot)
        return _status(app)

    assert _run(body).startswith("Even Minimal is too slow on this computer (load 1.30).")
