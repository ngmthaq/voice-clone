import logging
from collections.abc import Callable, Sequence

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
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

from voice_clone.controllers import ChangerController
from voice_clone.controllers.changer_controller import DOWNLOADING_STATUS, StartRequest
from voice_clone.domain.audio import ConversionPipeline, GateSettings
from voice_clone.domain.config import CUSTOM_PRESET, PERFORMANCE_PRESETS, Settings
from voice_clone.domain.errors import VoiceCloneError
from voice_clone.views.fields import labeled_field
from voice_clone.views.level_meter_widget import LevelMeterWidget

logger = logging.getLogger(__name__)

METER_REFRESH_SECONDS = 0.1
DEFAULT_GATE = GateSettings()
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
        self._controller = ChangerController(set_timer=self.set_timer)

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
                                value=self._controller.preset_key,
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
                                    _format_number(getattr(self._controller.gate, name)),
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
                str(self._controller.voice_options[name]),
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
        self._controller.load()
        self._fill_select(
            "#input-select", self._controller.input_names, self._controller.input_name
        )
        self._fill_select(
            "#output-select", self._controller.output_names, self._controller.output_name
        )
        self._fill_select(
            "#voice-select", self._controller.voice_names, self._controller.voice_name
        )
        self._refresh_pitch_label()
        self.set_interval(METER_REFRESH_SECONDS, self._refresh_live_state)
        if self._controller.models_ready:
            self._set_status(*self._controller.initial_status())
        else:
            self._download_models()
        self._refresh_controls()

    def on_unmount(self) -> None:
        self._controller.stop_pipeline()
        self._controller.flush_save()

    @property
    def busy_message(self) -> str | None:
        return self._controller.busy_message

    def toggle(self) -> None:
        controller = self._controller
        if controller.working:
            return
        if controller.converting:
            self._set_status(*controller.stop())
            self._refresh_controls()
        else:
            self._begin_start()

    def action_toggle(self) -> None:
        self.toggle()

    def action_back(self) -> None:
        status = self._controller.back_status()
        if status is not None:
            self._set_status(*status)
            return
        self.dismiss()

    @on(Button.Pressed, "#start-button")
    def _on_start_pressed(self) -> None:
        self.toggle()

    @on(Button.Pressed, "#pitch-down")
    def _on_pitch_down(self) -> None:
        self._change_pitch(self._controller.pitch - 1)

    @on(Button.Pressed, "#pitch-up")
    def _on_pitch_up(self) -> None:
        self._change_pitch(self._controller.pitch + 1)

    @on(Input.Changed, ".gate-field Input")
    def _on_gate_changed(self, event: Input.Changed) -> None:
        if not event.value or (event.validation_result and not event.validation_result.is_valid):
            return
        name = next(name for field_id, _, name, *_ in GATE_FIELDS if field_id == event.input.id)
        self._controller.set_gate_value(name, event.value)
        self._sync_preset_select()

    @on(Input.Changed, ".voice-field Input")
    def _on_voice_option_changed(self, event: Input.Changed) -> None:
        if not event.value or (event.validation_result and not event.validation_result.is_valid):
            return
        name = next(name for field_id, _, name, *_ in VOICE_FIELDS if field_id == event.input.id)
        self._controller.set_voice_option(name, int(event.value))
        self._sync_preset_select()

    @on(Select.Changed, "#preset-select")
    def _on_preset_changed(self, event: Select.Changed) -> None:
        if not self._controller.select_preset(str(event.value)):
            return
        self._show_advanced_values()

    def _show_advanced_values(self) -> None:
        for field_id, _, name, *_ in VOICE_FIELDS:
            self.query_one(f"#{field_id}", Input).value = str(self._controller.voice_options[name])
        for field_id, _, name, *_ in GATE_FIELDS:
            self.query_one(f"#{field_id}", Input).value = _format_number(
                getattr(self._controller.gate, name)
            )

    def _sync_preset_select(self) -> None:
        if not self.is_mounted:
            return
        select = self.query_one("#preset-select", Select)
        preset = self._controller.preset_key
        if select.value != preset:
            select.value = preset

    @on(Button.Pressed, "#advanced-reset")
    def _on_advanced_reset(self) -> None:
        self._controller.reset_advanced()
        self._show_advanced_values()

    @on(Select.Changed)
    def _on_selection_changed(self, event: Select.Changed) -> None:
        value = event.value if isinstance(event.value, str) else None
        if event.select.id == "input-select":
            self._controller.select_input(value)
        elif event.select.id == "output-select":
            self._controller.select_output(value)
        elif event.select.id == "voice-select":
            self._controller.select_voice(value)

    def _fill_select(self, selector: str, names: Sequence[str], chosen: str | None) -> None:
        select = self.query_one(selector, Select)
        select.set_options((name, name) for name in names)
        if chosen is not None:
            select.value = chosen

    @work(thread=True, exclusive=True, group="download")
    def _download_models(self) -> None:
        self.app.call_from_thread(self._set_download_visible, True)
        self.app.call_from_thread(self._set_status, *DOWNLOADING_STATUS)
        try:
            self._controller.download_models(self._report_download)
        except VoiceCloneError as exc:
            self.app.call_from_thread(self._download_failed, str(exc))
            return
        self.app.call_from_thread(self._download_finished)

    def _report_download(self, message: str, fraction: float) -> None:
        self.app.call_from_thread(self._show_download_progress, message, fraction)

    def _show_download_progress(self, message: str, fraction: float) -> None:
        self.query_one("#download-progress", ProgressBar).update(progress=fraction)
        self._set_status(*self._controller.download_status(message))

    def _download_finished(self) -> None:
        status = self._controller.download_finished()
        self._set_download_visible(False)
        self._set_status(*status)
        self._refresh_controls()

    def _download_failed(self, message: str) -> None:
        status = self._controller.download_failed(message)
        self._set_download_visible(False)
        self._set_status(*status)
        self._refresh_controls()

    def _begin_start(self) -> None:
        if not self._controller.models_ready:
            self._controller.begin_download()
            self._refresh_controls()
            self._download_models()
            return
        request, status = self._controller.begin_start()
        self._set_status(*status)
        if request is None:
            return
        self._refresh_controls()
        self._start_pipeline(request)

    @work(thread=True, exclusive=True, group="pipeline")
    def _start_pipeline(self, request: StartRequest) -> None:
        try:
            pipeline = self._controller.start_pipeline(request)
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

    def _start_succeeded(self, pipeline: ConversionPipeline) -> None:
        self._set_status(*self._controller.start_succeeded(pipeline))
        self._refresh_controls()

    def _start_failed(self, message: str) -> None:
        self._set_status(*self._controller.start_failed(message))
        self._refresh_controls()

    @work(thread=True, exclusive=True, group="stop")
    def _stop_after_error(self, message: str) -> None:
        self._controller.stop_pipeline()
        self.app.call_from_thread(self._start_failed, message)

    def _refresh_live_state(self) -> None:
        state = self._controller.tick()
        self.query_one("#input-meter", LevelMeterWidget).level = state.input_level
        self.query_one("#output-meter", LevelMeterWidget).level = state.output_level
        if state.stop_message is not None:
            self._refresh_controls()
            self._stop_after_error(state.stop_message)
        elif state.status is not None:
            self._set_status(*state.status)

    def _change_pitch(self, value: int) -> None:
        self._controller.change_pitch(value)
        self._refresh_pitch_label()

    def _refresh_pitch_label(self) -> None:
        self.query_one("#pitch-label", Label).update(f"{self._controller.pitch:+d}")

    def _refresh_controls(self) -> None:
        controller = self._controller
        locked = controller.working or controller.converting
        for widget in self.query("#tabs Select, #tabs Input, #tabs Button"):
            widget.disabled = locked
        start = self.query_one("#start-button", Button)
        start.disabled = controller.working
        if controller.converting:
            start.label = "Stop"
            start.variant = "error"
        else:
            start.label = "Start" if controller.models_ready else "Retry download"
            start.variant = "primary"

    def _set_status(self, message: str, kind: str = "") -> None:
        status = self.query_one("#status", Static)
        status.update(message)
        status.set_classes(kind)

    def _set_download_visible(self, visible: bool) -> None:
        self.query_one("#download-progress", ProgressBar).display = visible
        if visible:
            self._controller.begin_download()
            self._refresh_controls()


def _format_number(value: float) -> str:
    return f"{value:g}"
