import asyncio

import pytest
import torch

import voice_clone.domain.config as config
import voice_clone.views.main_screen as main_screen
from voice_clone.domain.audio import AudioDevice
from voice_clone.views.app import VoiceCloneApp

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
    monkeypatch.setattr(main_screen, "select_torch_device", lambda: torch.device("mps"))


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


@pytest.mark.parametrize(
    "saved, expected",
    [
        ("", "balanced"),
        (
            "index_percent = 40\nprotect_percent = 75\nloudness_percent = 60\n"
            "pitch_smoothing_ms = 50\ncontext_ms = 300\nblock_ms = 600\ncrossfade_ms = 60\n",
            "light",
        ),
        ("context_ms = 300\nblock_ms = 600\ncrossfade_ms = 60\n", "custom"),
        ("context_ms = 700\n", "custom"),
        ("context_ms = 300\nblock_ms = 600\ncrossfade_ms = 60\ngate_hold_ms = 900\n", "custom"),
    ],
)
def test_performance_preset_matches_saved_settings(empty_environment, tmp_path, saved, expected):
    (tmp_path / "settings.toml").write_text(saved)

    async def body(app, pilot):
        return app.screen.query_one("#preset-select").value

    assert _run(body) == expected


def test_choosing_a_preset_sets_every_advanced_value_and_saves(empty_environment, tmp_path):
    (tmp_path / "settings.toml").write_text(
        "protect_percent = 10\nhum_filter_hz = 0\ngate_hold_ms = 900\n"
    )

    async def body(app, pilot):
        app.screen.query_one("#preset-select").value = "ultra"
        await pilot.pause()
        return [
            app.screen.query_one(f"#{field_id}").value
            for field_id in ("context-ms", "block-ms", "crossfade-ms")
        ], app.screen.query_one("#preset-select").value

    fields, preset = _run(body)

    assert fields == ["2000", "200", "60"]
    assert preset == "ultra"
    saved = config.load_settings()
    assert (saved.context_ms, saved.block_ms, saved.crossfade_ms) == (2000, 200, 60)
    assert (
        saved.index_percent,
        saved.protect_percent,
        saved.pitch_smoothing_ms,
        saved.hum_filter_hz,
        saved.gate_hold_ms,
        saved.gate_open_above_db,
    ) == (60, 50, 20, 90, 600, 5.0)


def test_editing_a_speed_field_switches_preset_to_custom(empty_environment):
    async def body(app, pilot):
        app.screen.query_one("#context-ms").value = "800"
        await pilot.pause()
        return app.screen.query_one("#preset-select").value

    assert _run(body) == "custom"


@pytest.mark.parametrize("field_id, value", [("protect-percent", "20"), ("gate-hold", "800")])
def test_editing_any_advanced_value_switches_preset_to_custom(empty_environment, field_id, value):
    async def body(app, pilot):
        app.screen.query_one(f"#{field_id}").value = value
        await pilot.pause()
        return app.screen.query_one("#preset-select").value

    assert _run(body) == "custom"


def test_minimal_preset_is_first_and_sets_lowest_values(empty_environment):
    async def body(app, pilot):
        select = app.screen.query_one("#preset-select")
        first = next(value for _, value in select._options if isinstance(value, str))
        select.value = "minimal"
        await pilot.pause()
        return first

    assert _run(body) == "minimal"
    saved = config.load_settings()
    assert (saved.index_percent, saved.context_ms, saved.block_ms) == (0, 200, 1000)


def test_pipeline_started_after_the_screen_closed_is_stopped(empty_environment, monkeypatch):
    stopped = []

    class FakePipeline:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def warm_up(self) -> None:
            pass

        def start(self) -> None:
            pass

        def stop(self) -> None:
            stopped.append(True)

    class FakeEngine:
        def load(self, profile) -> None:
            pass

        def set_pitch(self, semitones) -> None:
            pass

    async def scenario():
        app = VoiceCloneApp()
        async with app.run_test(size=(100, 50)) as pilot:
            await open_voice_changer(app, pilot)
            screen = app.screen
            screen._engine = FakeEngine()
            app.pop_screen()
            await pilot.pause()
            return screen

    screen = asyncio.run(scenario())
    monkeypatch.setattr(main_screen, "ConversionPipeline", FakePipeline)
    profile = main_screen.VoiceProfile("v", None, None)

    main_screen.MainScreen._start_pipeline.__wrapped__(screen, MIC, BLACKHOLE, profile, 0)

    assert stopped == [True]


def test_stop_resets_the_level_meters(empty_environment):
    class FinishingPipeline:
        """Reports its last block while stopping, as the worker thread can."""

        load = 0.0
        dropped_blocks = 0

        def __init__(self, screen) -> None:
            self._screen = screen

        def stop(self) -> None:
            self._screen._store_levels(0.2, 0.2)

    async def body(app, pilot):
        screen = app.screen
        screen._pipeline = FinishingPipeline(screen)
        screen._converting = True
        screen._store_levels(0.2, 0.2)
        await pilot.pause(0.3)
        while_running = (
            screen.query_one("#input-meter").level,
            screen.query_one("#output-meter").level,
        )
        screen.toggle()
        await pilot.pause(0.3)
        after_stop = (
            screen.query_one("#input-meter").level,
            screen.query_one("#output-meter").level,
        )
        return while_running, after_stop

    assert _run(body) == ((0.2, 0.2), (0.0, 0.0))


def test_fresh_cpu_only_install_starts_on_minimal(empty_environment, monkeypatch):
    monkeypatch.setattr(main_screen, "select_torch_device", lambda: torch.device("cpu"))

    async def body(app, pilot):
        return app.screen.query_one("#preset-select").value

    assert _run(body) == "minimal"


def test_saved_settings_win_over_the_cpu_default(empty_environment, monkeypatch, tmp_path):
    (tmp_path / "settings.toml").write_text("block_ms = 400\n")
    monkeypatch.setattr(main_screen, "select_torch_device", lambda: torch.device("cpu"))

    async def body(app, pilot):
        return app.screen.query_one("#preset-select").value

    assert _run(body) == "balanced"
