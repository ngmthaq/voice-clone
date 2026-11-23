import logging
from collections.abc import Callable, Sequence
from dataclasses import replace

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.timer import Timer
from textual.validation import Number
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    ProgressBar,
    Select,
    Static,
    TabbedContent,
    TabPane,
)

from voice_clone.audio import (
    AudioDevice,
    ConversionPipeline,
    GateSettings,
    find_device_by_name,
    find_virtual_output,
    list_input_devices,
    list_output_devices,
)
from voice_clone.config import (
    CUSTOM_PRESET,
    PERFORMANCE_PRESETS,
    Settings,
    apply_preset,
    load_settings,
    matching_preset,
    save_settings,
    settings_saved,
)
from voice_clone.engine import (
    RvcEngine,
    base_models_present,
    ensure_base_models,
    select_torch_device,
)
from voice_clone.engine.download import base_model_paths
from voice_clone.errors import VoiceCloneError
from voice_clone.paths import models_dir, voices_dir
from voice_clone.profiles import VoiceProfile, discover_profiles
from voice_clone.ui.fields import labeled_field
from voice_clone.ui.level_meter_widget import LevelMeterWidget

logger = logging.getLogger(__name__)

MIN_PITCH = -12
MAX_PITCH = 12
METER_REFRESH_SECONDS = 0.1
SAVE_DELAY_SECONDS = 0.3
NO_VIRTUAL_DEVICE_MESSAGE = (
    "No virtual audio device found. Install BlackHole 2ch (macOS) or VB-CABLE (Windows)."
)
NO_VOICES_MESSAGE = (
    "No voices found. Go back (Esc) and choose 'Train a voice', "
    "or put a voice in voices/<name>/model.pth"
)
SLOW_LOAD = 0.9
SLOW_MESSAGE = (
    "Too slow for this computer: converting takes {percent}% of real time{dropped}, so the "
    "voice lags and drops. Stop, pick a lighter Performance preset on the Simple tab "
    "(try Light), then Start again."
)
DEFAULT_GATE = GateSettings()
GATE_SETTING_NAMES = {
    "hold_ms": "gate_hold_ms",
    "pre_open_ms": "gate_pre_open_ms",
    "open_above_floor_db": "gate_open_above_db",
}
DEFAULT_SETTINGS = Settings()
ADVANCED_VOICE_FIELDS = (
    (
        "index-percent",
        "Index voice (%)",
        "index_percent",
        0,
        100,
        "0 = your live voice, 100 = the trained voice (closer match, less clear)",
    ),
    (
        "protect-percent",
        "Protect consonants (%)",
        "protect_percent",
        0,
        100,
        "Keeps consonants (s, t, k) clear when Index is high. 0 = off",
    ),
    (
        "loudness-percent",
        "Follow mic volume (%)",
        "loudness_percent",
        0,
        100,
        "0 = the model sets the volume, 100 = it follows how loud you speak",
    ),
    (
        "pitch-smoothing",
        "Pitch smoothing (ms)",
        "pitch_smoothing_ms",
        0,
        200,
        "Removes pitch jumps that sound like a wobble. 0 = off",
    ),
)
SPEED_FIELDS = (
    (
        "context-ms",
        "Context (ms)",
        "context_ms",
        200,
        2000,
        "More = clearer words, no extra delay, but more CPU/GPU. Lower it if audio drops",
    ),
    (
        "block-ms",
        "Block size (ms)",
        "block_ms",
        100,
        1000,
        "Audio is converted in blocks this long. Smaller = less delay, but more CPU/GPU",
    ),
    (
        "crossfade-ms",
        "Crossfade (ms)",
        "crossfade_ms",
        10,
        200,
        "Blends one block into the next. Raise it if you hear clicks between blocks",
    ),
    (
        "hum-filter-hz",
        "Hum filter (Hz)",
        "hum_filter_hz",
        0,
        200,
        "Cuts mains hum and rumble below this pitch. 0 = off",
    ),
)
VOICE_FIELDS = (*ADVANCED_VOICE_FIELDS, *SPEED_FIELDS)
GATE_FIELDS = (
    (
        "gate-hold",
        "Hold (ms)",
        "hold_ms",
        0,
        2000,
        "integer",
        "How long the mic stays open after you stop. Lower cuts room echo sooner",
    ),
    (
        "gate-pre-open",
        "Open early (ms)",
        "pre_open_ms",
        0,
        400,
        "integer",
        "Opens this much before a word, so soft first sounds (s, f, h) are kept",
    ),
    (
        "gate-open-db",
        "Above noise (dB)",
        "open_above_floor_db",
        0,
        30,
        "number",
        "How much louder than background hiss your voice must be. Raise it if noise gets in",
    ),
)


class MainScreen(Screen[None]):
    SUB_TITLE = "Voice changer"
    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("space", "toggle", "Start/Stop"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._settings = _first_start_settings() or load_settings()
        self._inputs: list[AudioDevice] = []
        self._outputs: list[AudioDevice] = []
        self._profiles: list[VoiceProfile] = []
        self._engine: RvcEngine | None = None
        self._loaded_profile: str | None = None
        self._pipeline: ConversionPipeline | None = None
        self._pitch = self._settings.pitch
        self._voice_options = {
            name: int(getattr(self._settings, name)) for _, _, name, *_ in VOICE_FIELDS
        }
        self._gate = GateSettings(
            hold_ms=self._settings.gate_hold_ms,
            pre_open_ms=self._settings.gate_pre_open_ms,
            open_above_floor_db=self._settings.gate_open_above_db,
        )
        self._models_ready = False
        self._working = False
        self._converting = False
        self._initialised = False
        self._input_level = 0.0
        self._output_level = 0.0
        self._pipeline_error: Exception | None = None
        self._slow_warned = False
        self._save_timer: Timer | None = None
        self._pending_save: dict[str, object] | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="panel"):
            with Vertical(classes="page"):
                with TabbedContent(id="tabs"):
                    with TabPane("Simple", id="simple-tab"):
                        yield from labeled_field(
                            "Input microphone",
                            Select[str]([], id="input-select", prompt="Select a microphone"),
                        )
                        yield from labeled_field(
                            "Output device",
                            Select[str]([], id="output-select", prompt="Select an output device"),
                        )
                        yield from labeled_field(
                            "Voice",
                            Select[str]([], id="voice-select", prompt="Select a voice"),
                        )
                        yield from labeled_field(
                            "Pitch (semitones)",
                            Horizontal(
                                Button("-", id="pitch-down"),
                                Label("", id="pitch-label"),
                                Button("+", id="pitch-up"),
                                id="pitch-row",
                            ),
                        )
                        yield from labeled_field(
                            "Performance",
                            Select[str](
                                [
                                    *(
                                        (label, key)
                                        for key, (label, _) in PERFORMANCE_PRESETS.items()
                                    ),
                                    ("Custom: set on the Advanced tab", CUSTOM_PRESET),
                                ],
                                value=matching_preset(self._preset_values()),
                                allow_blank=False,
                                id="preset-select",
                            ),
                            "Pick what fits this computer. Sets every Advanced setting; if the "
                            "app says it is too slow, pick a lighter one.",
                        )
                    with TabPane("Advanced", id="advanced-tab"):
                        for field in ADVANCED_VOICE_FIELDS:
                            yield from self._voice_field(field)
                        for field in SPEED_FIELDS:
                            yield from self._voice_field(field)
                        for field_id, label, name, minimum, maximum, kind, hint in GATE_FIELDS:
                            default = _format_number(getattr(DEFAULT_GATE, name))
                            yield from labeled_field(
                                label,
                                Input(
                                    _format_number(getattr(self._gate, name)),
                                    placeholder=f"default {default}",
                                    type=kind,
                                    validators=[Number(minimum=minimum, maximum=maximum)],
                                    id=field_id,
                                ),
                                hint,
                                "gate-field",
                            )
                        yield Button("Reset Advanced settings to defaults", id="advanced-reset")
                with Vertical(id="controls"):
                    yield Button("Start", id="start-button", variant="primary")
                    yield LevelMeterWidget("Input", id="input-meter")
                    yield LevelMeterWidget("Output", id="output-meter")
                    yield ProgressBar(total=1.0, show_eta=False, id="download-progress")
                    yield Static("", id="status")
        yield Footer()

    def _voice_field(self, field: tuple[str, str, str, int, int, str]) -> ComposeResult:
        field_id, label, name, minimum, maximum, hint = field
        yield from labeled_field(
            label,
            Input(
                str(self._voice_options[name]),
                placeholder=f"default {getattr(DEFAULT_SETTINGS, name)}",
                type="integer",
                validators=[Number(minimum=minimum, maximum=maximum)],
                id=field_id,
            ),
            hint,
            "voice-field",
        )

    def on_mount(self) -> None:
        self.query_one("#download-progress", ProgressBar).display = False
        self._populate_selects()
        self._initialised = True
        self._refresh_pitch_label()
        self.set_interval(METER_REFRESH_SECONDS, self._refresh_live_state)
        self._models_ready = base_models_present(models_dir())
        if self._models_ready:
            self._show_initial_status()
        else:
            self._download_models()
        self._refresh_controls()

    def on_unmount(self) -> None:
        self._stop_pipeline()
        self._flush_save()

    @property
    def busy_message(self) -> str | None:
        if not self._working:
            return None
        return "The voice is loading." if self._models_ready else "Base models are downloading."

    def toggle(self) -> None:
        if self._working:
            return
        if self._converting:
            self._stop_pipeline()
            self._set_status("Ready")
            self._refresh_controls()
        else:
            self._begin_start()

    def action_toggle(self) -> None:
        self.toggle()

    def action_back(self) -> None:
        if self._working:
            self._set_status("Please wait until loading or the download is done.", "warning")
            return
        self.dismiss()

    @on(Button.Pressed, "#start-button")
    def _on_start_pressed(self) -> None:
        self.toggle()

    @on(Button.Pressed, "#pitch-down")
    def _on_pitch_down(self) -> None:
        self._change_pitch(self._pitch - 1)

    @on(Button.Pressed, "#pitch-up")
    def _on_pitch_up(self) -> None:
        self._change_pitch(self._pitch + 1)

    @on(Input.Changed, ".gate-field Input")
    def _on_gate_changed(self, event: Input.Changed) -> None:
        if not event.value or (event.validation_result and not event.validation_result.is_valid):
            return
        name = next(name for field_id, _, name, *_ in GATE_FIELDS if field_id == event.input.id)
        value = float(event.value) if name == "open_above_floor_db" else int(event.value)
        self._apply_gate(replace(self._gate, **{name: value}))
        self._sync_preset_select()

    @on(Input.Changed, ".voice-field Input")
    def _on_voice_option_changed(self, event: Input.Changed) -> None:
        if not event.value or (event.validation_result and not event.validation_result.is_valid):
            return
        name = next(name for field_id, _, name, *_ in VOICE_FIELDS if field_id == event.input.id)
        self._voice_options[name] = int(event.value)
        self._apply_voice_options()
        self._schedule_save()
        self._sync_preset_select()

    @on(Select.Changed, "#preset-select")
    def _on_preset_changed(self, event: Select.Changed) -> None:
        preset = PERFORMANCE_PRESETS.get(str(event.value))
        if preset is None:
            return
        _, values = preset
        self._voice_options.update({name: int(values[name]) for name in self._voice_options})
        self._gate = GateSettings(
            **{name: values[GATE_SETTING_NAMES[name]] for name in GATE_SETTING_NAMES}
        )
        for field_id, _, name, *_ in VOICE_FIELDS:
            self.query_one(f"#{field_id}", Input).value = str(self._voice_options[name])
        for field_id, _, name, *_ in GATE_FIELDS:
            self.query_one(f"#{field_id}", Input).value = _format_number(getattr(self._gate, name))

    def _preset_values(self) -> dict[str, float]:
        gate = {setting: getattr(self._gate, name) for name, setting in GATE_SETTING_NAMES.items()}
        return {**self._voice_options, **gate}

    def _sync_preset_select(self) -> None:
        if not self.is_mounted:
            return
        select = self.query_one("#preset-select", Select)
        preset = matching_preset(self._preset_values())
        if select.value != preset:
            select.value = preset

    @on(Button.Pressed, "#advanced-reset")
    def _on_advanced_reset(self) -> None:
        for field_id, _, name, *_ in (*ADVANCED_VOICE_FIELDS, *SPEED_FIELDS):
            self.query_one(f"#{field_id}", Input).value = str(getattr(DEFAULT_SETTINGS, name))
        for field_id, _, name, *_ in GATE_FIELDS:
            self.query_one(f"#{field_id}", Input).value = _format_number(
                getattr(DEFAULT_GATE, name)
            )
        self._apply_gate(DEFAULT_GATE)

    def _apply_voice_options(
        self, engine: RvcEngine | None = None, pipeline: ConversionPipeline | None = None
    ) -> None:
        options = self._voice_options
        engine = engine or self._engine
        pipeline = pipeline or self._pipeline
        if engine is not None:
            engine.index_rate = options["index_percent"] / 100
            engine.protect = options["protect_percent"] / 100
            engine.loudness_follow = options["loudness_percent"] / 100
            engine.pitch_smoothing_ms = options["pitch_smoothing_ms"]
        if pipeline is not None:
            pipeline.set_context_ms(options["context_ms"])

    def _apply_gate(self, settings: GateSettings) -> None:
        self._gate = settings
        if self._pipeline is not None:
            self._pipeline.set_gate_settings(settings)
        self._schedule_save()

    @on(Select.Changed)
    def _on_selection_changed(self) -> None:
        self._schedule_save()

    def _populate_selects(self) -> None:
        self._inputs = list_input_devices()
        self._outputs = list_output_devices()
        self._profiles = discover_profiles(voices_dir())

        saved_input = find_device_by_name(self._inputs, self._settings.input_device) or (
            self._inputs[0] if self._inputs else None
        )
        saved_output = find_device_by_name(self._outputs, self._settings.output_device)
        output = saved_output or find_virtual_output(self._outputs)
        saved_profile = next((p for p in self._profiles if p.name == self._settings.profile), None)
        default_profile = saved_profile or (self._profiles[0] if self._profiles else None)

        self._fill_select("#input-select", [d.name for d in self._inputs], saved_input)
        self._fill_select("#output-select", [d.name for d in self._outputs], output)
        self._fill_select("#voice-select", [p.name for p in self._profiles], default_profile)

    def _fill_select(
        self, selector: str, names: Sequence[str], chosen: AudioDevice | VoiceProfile | None
    ) -> None:
        select = self.query_one(selector, Select)
        select.set_options((name, name) for name in names)
        if chosen is not None:
            select.value = chosen.name

    def _show_initial_status(self) -> None:
        if not self._profiles:
            self._set_status(NO_VOICES_MESSAGE, "warning")
        elif find_virtual_output(self._outputs) is None:
            self._set_status(NO_VIRTUAL_DEVICE_MESSAGE, "warning")
        else:
            self._set_status("Ready")

    @work(thread=True, exclusive=True, group="download")
    def _download_models(self) -> None:
        self.app.call_from_thread(self._set_download_visible, True)
        self.app.call_from_thread(self._set_status, "Downloading…")
        try:
            ensure_base_models(models_dir(), self._report_download)
        except VoiceCloneError as exc:
            self.app.call_from_thread(self._download_failed, str(exc))
            return
        self.app.call_from_thread(self._download_finished)

    def _report_download(self, message: str, fraction: float) -> None:
        self.app.call_from_thread(self._show_download_progress, message, fraction)

    def _show_download_progress(self, message: str, fraction: float) -> None:
        self.query_one("#download-progress", ProgressBar).update(progress=fraction)
        self._set_status(f"Downloading… {message}")

    def _download_finished(self) -> None:
        self._models_ready = True
        self._working = False
        self._set_download_visible(False)
        self._show_initial_status()
        self._refresh_controls()

    def _download_failed(self, message: str) -> None:
        self._working = False
        self._set_download_visible(False)
        self._set_status(f"Error: {message}", "error")
        self._refresh_controls()

    def _begin_start(self) -> None:
        if not self._models_ready:
            self._working = True
            self._refresh_controls()
            self._download_models()
            return
        input_device = self._selected_device(self._inputs, "#input-select")
        output_device = self._selected_device(self._outputs, "#output-select")
        profile = self._selected_profile()
        if profile is None:
            self._set_status(NO_VOICES_MESSAGE, "warning")
            return
        if output_device is None:
            self._set_status(NO_VIRTUAL_DEVICE_MESSAGE, "warning")
            return
        if input_device is None:
            self._set_status("Error: Select a microphone first.", "error")
            return
        self._working = True
        self._pipeline_error = None
        self._set_status("Loading voice…")
        self._refresh_controls()
        self._start_pipeline(input_device, output_device, profile, self._pitch)

    @work(thread=True, exclusive=True, group="pipeline")
    def _start_pipeline(
        self,
        input_device: AudioDevice,
        output_device: AudioDevice,
        profile: VoiceProfile,
        pitch: int,
    ) -> None:
        try:
            engine = self._get_engine()
            engine.set_pitch(pitch)
            self._apply_voice_options(engine=engine)
            if self._loaded_profile != profile.name:
                engine.load(profile)
                self._loaded_profile = profile.name
            pipeline = ConversionPipeline(
                engine,
                input_device,
                output_device,
                on_levels=self._store_levels,
                on_error=self._store_error,
                block_ms=self._voice_options["block_ms"],
                context_ms=self._voice_options["context_ms"],
                crossfade_ms=self._voice_options["crossfade_ms"],
                hum_filter_hz=self._voice_options["hum_filter_hz"],
                gate_settings=self._gate,
            )
            pipeline.warm_up()
            pipeline.start()
        except VoiceCloneError as exc:
            self._call_ui(self._start_failed, str(exc))
        except Exception as exc:
            logger.exception("Could not start voice conversion")
            self._call_ui(self._start_failed, str(exc) or type(exc).__name__)
        else:
            if not self._call_ui(self._start_succeeded, pipeline):
                # The app closed while the voice was loading: nobody owns this pipeline.
                pipeline.stop()

    def _call_ui(self, callback: Callable[..., object], *args: object) -> bool:
        """Run `callback` on the UI thread. False if the app or this screen is gone."""
        if not self.is_attached:
            return False
        try:
            self.app.call_from_thread(callback, *args)
        except RuntimeError:
            logger.debug("UI is gone; dropping %s", callback.__name__)
            return False
        return True

    def _get_engine(self) -> RvcEngine:
        if self._engine is None:
            self._engine = RvcEngine(
                base_model_paths(models_dir()),
                cpu_threads=self._settings.cpu_threads,
                precision=self._settings.precision,
            )
        return self._engine

    def _start_succeeded(self, pipeline: ConversionPipeline) -> None:
        self._pipeline = pipeline
        self._working = False
        self._converting = True
        self._slow_warned = False
        self._set_status("Running", "running")
        self._refresh_controls()

    def _start_failed(self, message: str) -> None:
        self._working = False
        self._converting = False
        self._set_status(f"Error: {message}", "error")
        self._refresh_controls()

    def _stop_pipeline(self) -> None:
        pipeline, self._pipeline = self._pipeline, None
        self._converting = False
        if pipeline is not None:
            pipeline.stop()
        # Zero after stop(): the worker may still report the block it was converting.
        self._input_level = 0.0
        self._output_level = 0.0

    @work(thread=True, exclusive=True, group="stop")
    def _stop_after_error(self, message: str) -> None:
        self._stop_pipeline()
        self.app.call_from_thread(self._start_failed, message)

    def _store_levels(self, input_rms: float, output_rms: float) -> None:
        if not self._converting:
            return
        self._input_level = input_rms
        self._output_level = output_rms

    def _store_error(self, error: Exception) -> None:
        self._pipeline_error = error

    def _refresh_live_state(self) -> None:
        self.query_one("#input-meter", LevelMeterWidget).level = self._input_level
        self.query_one("#output-meter", LevelMeterWidget).level = self._output_level
        error, self._pipeline_error = self._pipeline_error, None
        if error is not None and self._converting:
            self._converting = False
            self._working = True
            self._refresh_controls()
            self._stop_after_error(str(error) or type(error).__name__)
            return
        self._warn_if_too_slow()

    def _warn_if_too_slow(self) -> None:
        pipeline = self._pipeline
        if pipeline is None or not self._converting or self._slow_warned:
            return
        dropped = pipeline.dropped_blocks
        if pipeline.load < SLOW_LOAD and not dropped:
            return
        self._slow_warned = True
        logger.warning("Conversion too slow: load %.2f, dropped %d", pipeline.load, dropped)
        self._set_status(
            SLOW_MESSAGE.format(
                percent=round(pipeline.load * 100),
                dropped=f", {dropped} block(s) dropped" if dropped else "",
            ),
            "warning",
        )

    def _change_pitch(self, value: int) -> None:
        self._pitch = max(MIN_PITCH, min(MAX_PITCH, value))
        self._refresh_pitch_label()
        if self._engine is not None and self._converting:
            self._engine.set_pitch(self._pitch)
        self._schedule_save()

    def _refresh_pitch_label(self) -> None:
        self.query_one("#pitch-label", Label).update(f"{self._pitch:+d}")

    def _refresh_controls(self) -> None:
        locked = self._working or self._converting
        for widget in self.query("#tabs Select, #tabs Input, #tabs Button"):
            widget.disabled = locked
        start = self.query_one("#start-button", Button)
        start.disabled = self._working
        if self._converting:
            start.label = "Stop"
            start.variant = "error"
        else:
            start.label = "Start" if self._models_ready else "Retry download"
            start.variant = "primary"

    def _set_status(self, message: str, kind: str = "") -> None:
        status = self.query_one("#status", Static)
        status.update(message)
        status.set_classes(kind)

    def _set_download_visible(self, visible: bool) -> None:
        self.query_one("#download-progress", ProgressBar).display = visible
        if visible:
            self._working = True
            self._refresh_controls()

    def _selected_device(self, devices: list[AudioDevice], selector: str) -> AudioDevice | None:
        value = self.query_one(selector, Select).value
        return find_device_by_name(devices, value if isinstance(value, str) else None)

    def _selected_profile(self) -> VoiceProfile | None:
        value = self.query_one("#voice-select", Select).value
        return next((p for p in self._profiles if p.name == value), None)

    def _selected_name(self, selector: str) -> str | None:
        value = self.query_one(selector, Select).value
        return value if isinstance(value, str) else None

    def _schedule_save(self) -> None:
        """Save shortly after the last change, so typing a value does not write on every key.

        The values are taken now: when the delayed write runs, or the screen is closing, the
        widgets may already be gone.
        """
        if not self._initialised:
            return
        self._pending_save = dict(
            input_device=self._selected_name("#input-select"),
            output_device=self._selected_name("#output-select"),
            profile=self._selected_name("#voice-select"),
            pitch=self._pitch,
            **self._voice_options,
            gate_hold_ms=self._gate.hold_ms,
            gate_pre_open_ms=self._gate.pre_open_ms,
            gate_open_above_db=self._gate.open_above_floor_db,
        )
        if self._save_timer is not None:
            self._save_timer.stop()
        self._save_timer = self.set_timer(SAVE_DELAY_SECONDS, self._flush_save)

    def _flush_save(self) -> None:
        if self._save_timer is not None:
            self._save_timer.stop()
            self._save_timer = None
        values, self._pending_save = self._pending_save, None
        if values is None:
            return
        try:
            save_settings(load_settings().model_copy(update=values))
        except OSError:
            logger.warning("Could not save settings", exc_info=True)


def _format_number(value: float) -> str:
    return f"{value:g}"


FIRST_START_CPU_PRESET = "minimal"


def _first_start_settings() -> Settings | None:
    if settings_saved() or select_torch_device().type != "cpu":
        return None
    logger.info("No GPU found: starting with the %s preset", FIRST_START_CPU_PRESET)
    return apply_preset(Settings(), FIRST_START_CPU_PRESET)
