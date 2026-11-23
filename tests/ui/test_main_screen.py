import asyncio

import pytest

import voice_clone.config as config
import voice_clone.ui.main_screen as main_screen
from voice_clone.app import VoiceCloneApp
from voice_clone.audio import AudioDevice

MIC = AudioDevice(0, "Mic", 1, 0, 48000.0)
BLACKHOLE = AudioDevice(1, "BlackHole 2ch", 2, 2, 48000.0)


async def open_voice_changer(app, pilot) -> None:
    await pilot.pause()
    app.screen.query_one("#open-changer").press()
    await pilot.pause()


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
            await open_voice_changer(app, pilot)
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
            await open_voice_changer(app, pilot)
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


def test_disabled_button_does_not_change_on_hover(empty_environment):
    async def body(app, pilot):
        button = app.screen.query_one("#start-button")
        button.disabled = True
        button.scroll_visible(animate=False)
        await pilot.pause()
        before = (button.styles.background, button.styles.border_top)
        await pilot.hover("#start-button")
        await pilot.pause()
        return before, (button.styles.background, button.styles.border_top)

    before, hovered = _run(body)

    assert hovered == before


def test_index_percent_shows_saved_value_and_is_saved(empty_environment, tmp_path):
    (tmp_path / "settings.toml").write_text("index_percent = 70\n")

    async def body(app, pilot):
        shown = app.screen.query_one("#index-percent").value
        app.screen.query_one("#index-percent").value = "40"
        await pilot.pause()
        return shown

    assert _run(body) == "70"
    assert config.load_settings().index_percent == 40


def test_index_percent_out_of_range_is_not_saved(empty_environment):
    async def body(app, pilot):
        app.screen.query_one("#index-percent").value = "150"
        await pilot.pause()

    _run(body)

    assert config.load_settings().index_percent == 50


def test_index_percent_change_applies_to_running_engine(empty_environment):
    class FakeEngine:
        index_rate = 0.5

    async def body(app, pilot):
        engine = FakeEngine()
        app.screen._engine = engine
        app.screen.query_one("#index-percent").value = "80"
        await pilot.pause()
        return engine.index_rate

    assert _run(body) == 0.8


@pytest.mark.parametrize(
    ("field_id", "name", "value"),
    [
        ("protect-percent", "protect_percent", 40),
        ("loudness-percent", "loudness_percent", 60),
        ("pitch-smoothing", "pitch_smoothing_ms", 30),
        ("context-ms", "context_ms", 1200),
    ],
)
def test_voice_match_value_is_saved(empty_environment, field_id, name, value):
    async def body(app, pilot):
        app.screen.query_one(f"#{field_id}").value = str(value)
        await pilot.pause()

    _run(body)

    assert getattr(config.load_settings(), name) == value


def test_voice_match_changes_apply_to_running_engine_and_pipeline(empty_environment):
    class FakeEngine:
        index_rate = 0.5

    class FakePipeline:
        context_ms = None

        def set_context_ms(self, value):
            self.context_ms = value

    async def body(app, pilot):
        engine, pipeline = FakeEngine(), FakePipeline()
        app.screen._engine = engine
        app.screen._pipeline = pipeline
        app.screen.query_one("#protect-percent").value = "50"
        app.screen.query_one("#loudness-percent").value = "100"
        app.screen.query_one("#pitch-smoothing").value = "40"
        app.screen.query_one("#context-ms").value = "1500"
        await pilot.pause()
        app.screen._pipeline = None
        return (
            engine.protect,
            engine.loudness_follow,
            engine.pitch_smoothing_ms,
            pipeline.context_ms,
        )

    assert _run(body) == (0.5, 1.0, 40, 1500)


def test_advanced_reset_restores_all_advanced_defaults(empty_environment, tmp_path):
    (tmp_path / "settings.toml").write_text(
        "index_percent = 90\nprotect_percent = 10\ncontext_ms = 300\nblock_ms = 200\n"
        "hum_filter_hz = 0\ngate_hold_ms = 900\ngate_open_above_db = 12.0\n"
    )

    async def body(app, pilot):
        app.screen.query_one("#tabs").active = "advanced-tab"
        await pilot.pause()
        app.screen.query_one("#advanced-reset").press()
        await pilot.pause()
        return app.screen.query_one("#gate-hold").value

    assert _run(body) == "500"

    saved = config.load_settings()
    assert (
        saved.index_percent,
        saved.protect_percent,
        saved.context_ms,
        saved.block_ms,
        saved.hum_filter_hz,
        saved.gate_hold_ms,
        saved.gate_open_above_db,
    ) == (50, 67, 1000, 400, 90, 500, 6.0)


@pytest.mark.parametrize(
    "field_id, name, value",
    [
        ("block-ms", "block_ms", 250),
        ("crossfade-ms", "crossfade_ms", 40),
        ("hum-filter-hz", "hum_filter_hz", 0),
    ],
)
def test_speed_value_is_saved(empty_environment, field_id, name, value):
    async def body(app, pilot):
        app.screen.query_one(f"#{field_id}").value = str(value)
        await pilot.pause()

    _run(body)

    assert getattr(config.load_settings(), name) == value


def test_voice_changer_keeps_saved_training_options(empty_environment, tmp_path):
    (tmp_path / "settings.toml").write_text('train_name = "alex"\ntrain_epochs = 77\n')

    async def body(app, pilot):
        app.screen.query_one("#context-ms").value = "500"
        await pilot.pause()

    _run(body)

    saved = config.load_settings()
    assert (saved.train_name, saved.train_epochs, saved.context_ms) == ("alex", 77, 500)


def test_simple_tab_is_shown_first_with_devices_and_pitch(empty_environment):
    async def body(app, pilot):
        tabs = app.screen.query_one("#tabs")
        pane = app.screen.query_one("#simple-tab")
        return tabs.active, [
            bool(pane.query(selector))
            for selector in ("#input-select", "#pitch-row", "#index-percent")
        ]

    assert _run(body) == ("simple-tab", [True, True, False])


def test_advanced_tab_holds_voice_match_and_gate(empty_environment):
    async def body(app, pilot):
        pane = app.screen.query_one("#advanced-tab")
        return [
            bool(pane.query(f"#{field_id}"))
            for field_id in ("index-percent", "protect-percent", "context-ms", "gate-hold")
        ]

    assert _run(body) == [True, True, True, True]


def test_all_settings_are_disabled_while_running(empty_environment):
    async def body(app, pilot):
        screen = app.screen
        screen._converting = True
        screen._refresh_controls()
        await pilot.pause()
        settings = list(screen.query("#tabs Select, #tabs Input, #tabs Button"))
        locked = all(widget.disabled for widget in settings)
        stop_enabled = not screen.query_one("#start-button").disabled
        screen._converting = False
        screen._refresh_controls()
        await pilot.pause()
        unlocked = not any(widget.disabled for widget in settings)
        return len(settings) > 10, locked, stop_enabled, unlocked

    assert _run(body) == (True, True, True, True)


def test_slow_conversion_shows_warning(empty_environment):
    class SlowPipeline:
        load = 1.3
        dropped_blocks = 4

        def stop(self):
            pass

    async def body(app, pilot):
        app.screen._pipeline = SlowPipeline()
        app.screen._converting = True
        await pilot.pause(0.3)
        status = str(app.screen.query_one("#status").render())
        app.screen._converting = False
        app.screen._pipeline = None
        return status

    status = _run(body)
    assert "Too slow" in status
    assert "130%" in status
    assert "4 block(s) dropped" in status
