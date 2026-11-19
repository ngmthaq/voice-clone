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
