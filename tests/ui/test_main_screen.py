import asyncio

import pytest

import voice_clone.config as config
import voice_clone.ui.main_screen as main_screen
from voice_clone.app import VoiceCloneApp
from voice_clone.audio import AudioDevice

MIC = AudioDevice(0, "Mic", 1, 0, 48000.0)
BLACKHOLE = AudioDevice(1, "BlackHole 2ch", 2, 2, 48000.0)


@pytest.fixture
def empty_environment(tmp_path, monkeypatch):
    (tmp_path / "voices").mkdir()
    monkeypatch.setattr(config, "settings_path", lambda: tmp_path / "settings.toml")
    monkeypatch.setattr(main_screen, "voices_dir", lambda: tmp_path / "voices")
    monkeypatch.setattr(main_screen, "list_input_devices", lambda: [MIC])
    monkeypatch.setattr(main_screen, "list_output_devices", lambda: [BLACKHOLE])


def test_no_voices_shows_status_message(empty_environment):
    async def scenario():
        app = VoiceCloneApp()
        async with app.run_test(size=(100, 50)) as pilot:
            await pilot.pause()
            return str(app.screen.query_one("#status").render())

    status = asyncio.run(scenario())

    assert main_screen.NO_VOICES_MESSAGE in status


def test_q_key_quits_app(empty_environment):
    async def scenario():
        app = VoiceCloneApp()
        async with app.run_test(size=(100, 50)) as pilot:
            await pilot.pause()
            await pilot.press("q")
            await pilot.pause()
        return app.return_code

    assert asyncio.run(scenario()) in (0, None)


def _run(scenario_body):
    async def scenario():
        app = VoiceCloneApp()
        async with app.run_test(size=(100, 60)) as pilot:
            await pilot.pause()
            return await scenario_body(app, pilot)

    return asyncio.run(scenario())


def test_gate_inputs_show_saved_values_and_defaults(empty_environment, tmp_path):
    (tmp_path / "settings.toml").write_text("gate_hold_ms = 700\n")

    async def body(app, pilot):
        screen = app.screen
        return (
            screen.query_one("#gate-hold").value,
            screen.query_one("#gate-pre-open").value,
            screen.query_one("#gate-open-db").value,
        )

    assert _run(body) == ("700", "100", "6")


def test_changing_a_gate_value_is_saved(empty_environment, tmp_path):
    async def body(app, pilot):
        app.screen.query_one("#gate-hold").value = "800"
        await pilot.pause()

    _run(body)

    assert config.load_settings().gate_hold_ms == 800


def test_invalid_gate_value_is_not_saved(empty_environment):
    async def body(app, pilot):
        app.screen.query_one("#gate-pre-open").value = "5000"
        await pilot.pause()

    _run(body)

    assert config.load_settings().gate_pre_open_ms == 100


def test_reset_restores_gate_defaults(empty_environment, tmp_path):
    (tmp_path / "settings.toml").write_text("gate_hold_ms = 900\ngate_open_above_db = 12.0\n")

    async def body(app, pilot):
        app.screen.query_one("#gate-reset").press()
        await pilot.pause()
        return app.screen.query_one("#gate-hold").value

    assert _run(body) == "500"
    assert config.load_settings().gate_open_above_db == 6.0


def test_disabled_button_does_not_change_on_hover(empty_environment):
    async def body(app, pilot):
        button = app.screen.query_one("#start-button")
        button.disabled = True
        await pilot.pause()
        before = (button.styles.background, button.styles.border_top)
        await pilot.hover("#start-button")
        await pilot.pause()
        return before, (button.styles.background, button.styles.border_top)

    before, hovered = _run(body)

    assert hovered == before
