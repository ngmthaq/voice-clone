import logging
from collections.abc import Sequence

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, ProgressBar, Select, Static

from voice_clone.audio import (
    AudioDevice,
    ConversionPipeline,
    find_device_by_name,
    find_virtual_output,
    list_input_devices,
    list_output_devices,
)
from voice_clone.config import Settings, load_settings, save_settings
from voice_clone.engine import RvcEngine, base_models_present, ensure_base_models
from voice_clone.engine.download import base_model_paths
from voice_clone.errors import VoiceCloneError
from voice_clone.paths import models_dir, voices_dir
from voice_clone.profiles import VoiceProfile, discover_profiles
from voice_clone.ui.level_meter_widget import LevelMeterWidget

logger = logging.getLogger(__name__)

MIN_PITCH = -12
MAX_PITCH = 12
METER_REFRESH_SECONDS = 0.1
NO_VIRTUAL_DEVICE_MESSAGE = (
    "No virtual audio device found. Install BlackHole 2ch (macOS) or VB-CABLE (Windows)."
)
NO_VOICES_MESSAGE = "No voices found. Put a voice in voices/<name>/model.pth"


class MainScreen(Screen[None]):
    def __init__(self) -> None:
        super().__init__()
        self._settings = load_settings()
        self._inputs: list[AudioDevice] = []
        self._outputs: list[AudioDevice] = []
        self._profiles: list[VoiceProfile] = []
        self._engine: RvcEngine | None = None
        self._loaded_profile: str | None = None
        self._pipeline: ConversionPipeline | None = None
        self._pitch = self._settings.pitch
        self._models_ready = False
        self._working = False
        self._converting = False
        self._initialised = False
        self._input_level = 0.0
        self._output_level = 0.0
        self._pipeline_error: Exception | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="panel"):
            yield Label("Input microphone", classes="field-label")
            yield Select[str]([], id="input-select", prompt="Select a microphone")
            yield Label("Output device", classes="field-label")
            yield Select[str]([], id="output-select", prompt="Select an output device")
            yield Label("Voice", classes="field-label")
            yield Select[str]([], id="voice-select", prompt="Select a voice")
            with Horizontal(id="pitch-row"):
                yield Button("-", id="pitch-down")
                yield Label("", id="pitch-label")
                yield Button("+", id="pitch-up")
            yield Button("Start", id="start-button", variant="primary")
            yield LevelMeterWidget("Input", id="input-meter")
            yield LevelMeterWidget("Output", id="output-meter")
            yield ProgressBar(total=1.0, show_eta=False, id="download-progress")
            yield Static("", id="status")
        yield Footer()

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

    def toggle(self) -> None:
        if self._working:
            return
        if self._converting:
            self._stop_pipeline()
            self._set_status("Ready")
            self._refresh_controls()
        else:
            self._begin_start()

    @on(Button.Pressed, "#start-button")
    def _on_start_pressed(self) -> None:
        self.toggle()

    @on(Button.Pressed, "#pitch-down")
    def _on_pitch_down(self) -> None:
        self._change_pitch(self._pitch - 1)

    @on(Button.Pressed, "#pitch-up")
    def _on_pitch_up(self) -> None:
        self._change_pitch(self._pitch + 1)

    @on(Select.Changed)
    def _on_selection_changed(self) -> None:
        self._save_current_settings()

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
            if self._loaded_profile != profile.name:
                engine.load(profile)
                self._loaded_profile = profile.name
            engine.set_pitch(pitch)
            pipeline = ConversionPipeline(
                engine,
                input_device,
                output_device,
                on_levels=self._store_levels,
                on_error=self._store_error,
            )
            pipeline.warm_up()
            pipeline.start()
        except VoiceCloneError as exc:
            self.app.call_from_thread(self._start_failed, str(exc))
        except Exception as exc:
            logger.exception("Could not start voice conversion")
            self.app.call_from_thread(self._start_failed, str(exc) or type(exc).__name__)
        else:
            self.app.call_from_thread(self._start_succeeded, pipeline)

    def _get_engine(self) -> RvcEngine:
        if self._engine is None:
            self._engine = RvcEngine(base_model_paths(models_dir()))
        return self._engine

    def _start_succeeded(self, pipeline: ConversionPipeline) -> None:
        self._pipeline = pipeline
        self._working = False
        self._converting = True
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
        self._input_level = 0.0
        self._output_level = 0.0
        if pipeline is not None:
            pipeline.stop()

    @work(thread=True, exclusive=True, group="stop")
    def _stop_after_error(self, message: str) -> None:
        self._stop_pipeline()
        self.app.call_from_thread(self._start_failed, message)

    def _store_levels(self, input_rms: float, output_rms: float) -> None:
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

    def _change_pitch(self, value: int) -> None:
        self._pitch = max(MIN_PITCH, min(MAX_PITCH, value))
        self._refresh_pitch_label()
        if self._engine is not None and self._converting:
            self._engine.set_pitch(self._pitch)
        self._save_current_settings()

    def _refresh_pitch_label(self) -> None:
        self.query_one("#pitch-label", Label).update(f"Pitch: {self._pitch:+d}")

    def _refresh_controls(self) -> None:
        locked = self._working or self._converting
        for selector in ("#input-select", "#output-select", "#voice-select"):
            self.query_one(selector, Select).disabled = locked
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

    def _save_current_settings(self) -> None:
        if not self._initialised:
            return
        settings = Settings(
            input_device=self._selected_name("#input-select"),
            output_device=self._selected_name("#output-select"),
            profile=self._selected_name("#voice-select"),
            pitch=self._pitch,
        )
        try:
            save_settings(settings)
        except OSError:
            logger.warning("Could not save settings", exc_info=True)
