import logging
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Protocol

from voice_clone.domain.audio import (
    AudioDevice,
    ConversionPipeline,
    GateSettings,
    find_device_by_name,
    find_virtual_output,
    list_input_devices,
    list_output_devices,
)
from voice_clone.domain.config import (
    PERFORMANCE_PRESETS,
    Settings,
    apply_preset,
    load_settings,
    matching_preset,
    save_settings,
    settings_saved,
)
from voice_clone.domain.engine import (
    RvcEngine,
    base_models_present,
    ensure_base_models,
    select_torch_device,
)
from voice_clone.domain.engine.download import base_model_paths
from voice_clone.domain.paths import models_dir, voices_dir
from voice_clone.domain.profiles import VoiceProfile, discover_profiles

logger = logging.getLogger(__name__)

Status = tuple[str, str]

MIN_PITCH = -12
MAX_PITCH = 12
SAVE_DELAY_SECONDS = 0.3
SLOW_LOAD = 0.9
FIRST_START_CPU_PRESET = "minimal"
NO_VIRTUAL_DEVICE_MESSAGE = (
    "No virtual audio device found. Install BlackHole 2ch (macOS) or VB-CABLE (Windows)."
)
NO_VOICES_MESSAGE = (
    "No voices found. Go back (Esc) and choose 'Train a voice', "
    "or put a voice in voices/<name>/model.pth"
)
SLOW_MESSAGE = (
    "Too slow for this computer: converting takes {percent}% of real time{dropped}, so the "
    "voice lags and drops. Stop, pick a lighter Performance preset on the Simple tab "
    "(try Light), then Start again."
)
READY_STATUS: Status = ("Ready", "")
RUNNING_STATUS: Status = ("Running", "running")
LOADING_STATUS: Status = ("Loading voice…", "")
DOWNLOADING_STATUS: Status = ("Downloading…", "")
WAIT_STATUS: Status = ("Please wait until loading or the download is done.", "warning")
GATE_SETTING_NAMES = {
    "hold_ms": "gate_hold_ms",
    "pre_open_ms": "gate_pre_open_ms",
    "open_above_floor_db": "gate_open_above_db",
    "open_below_voice_db": "gate_open_below_voice_db",
}
VOICE_OPTION_NAMES = (
    "index_percent",
    "protect_percent",
    "loudness_percent",
    "pitch_smoothing_ms",
    "context_ms",
    "block_ms",
    "crossfade_ms",
    "hum_filter_hz",
)


class _Stoppable(Protocol):
    def stop(self) -> object: ...


SetTimer = Callable[[float, Callable[[], None]], _Stoppable]


@dataclass(frozen=True)
class StartRequest:
    input_device: AudioDevice
    output_device: AudioDevice
    profile: VoiceProfile
    pitch: int


@dataclass(frozen=True)
class LiveState:
    input_level: float
    output_level: float
    stop_message: str | None = None
    status: Status | None = None


class ChangerController:
    def __init__(self, set_timer: SetTimer) -> None:
        self._set_timer = set_timer
        self._settings = _first_start_settings() or load_settings()
        self._inputs: list[AudioDevice] = []
        self._outputs: list[AudioDevice] = []
        self._profiles: list[VoiceProfile] = []
        self._input_name: str | None = None
        self._output_name: str | None = None
        self._voice_name: str | None = None
        self._engine: RvcEngine | None = None
        self._loaded_profile: str | None = None
        self._pipeline: ConversionPipeline | None = None
        self._pitch = self._settings.pitch
        self._voice_options = {
            name: int(getattr(self._settings, name)) for name in VOICE_OPTION_NAMES
        }
        self._gate = GateSettings(
            hold_ms=self._settings.gate_hold_ms,
            pre_open_ms=self._settings.gate_pre_open_ms,
            open_above_floor_db=self._settings.gate_open_above_db,
            open_below_voice_db=self._settings.gate_open_below_voice_db,
            block_bumps=self._settings.bump_filter,
        )
        self._noise_reduction = self._settings.noise_reduction
        self._models_ready = False
        self._working = False
        self._converting = False
        self._initialised = False
        self._input_level = 0.0
        self._output_level = 0.0
        self._pipeline_error: Exception | None = None
        self._slow_warned = False
        self._save_timer: _Stoppable | None = None
        self._pending_save: dict[str, object] | None = None

    @property
    def input_names(self) -> list[str]:
        return [device.name for device in self._inputs]

    @property
    def output_names(self) -> list[str]:
        return [device.name for device in self._outputs]

    @property
    def voice_names(self) -> list[str]:
        return [profile.name for profile in self._profiles]

    @property
    def input_name(self) -> str | None:
        return self._input_name

    @property
    def output_name(self) -> str | None:
        return self._output_name

    @property
    def voice_name(self) -> str | None:
        return self._voice_name

    @property
    def pitch(self) -> int:
        return self._pitch

    @property
    def voice_options(self) -> dict[str, int]:
        return self._voice_options

    @property
    def gate(self) -> GateSettings:
        return self._gate

    @property
    def preset_key(self) -> str:
        return matching_preset(self._preset_values())

    @property
    def models_ready(self) -> bool:
        return self._models_ready

    @property
    def working(self) -> bool:
        return self._working

    @property
    def converting(self) -> bool:
        return self._converting

    @property
    def busy_message(self) -> str | None:
        if not self._working:
            return None
        return "The voice is loading." if self._models_ready else "Base models are downloading."

    def load(self) -> None:
        self._inputs = list_input_devices()
        self._outputs = list_output_devices()
        self._profiles = discover_profiles(voices_dir())

        saved_input = find_device_by_name(self._inputs, self._settings.input_device) or (
            self._inputs[0] if self._inputs else None
        )
        saved_output = find_device_by_name(self._outputs, self._settings.output_device)
        output = saved_output or find_virtual_output(self._outputs)
        saved_profile = next((p for p in self._profiles if p.name == self._settings.profile), None)
        profile = saved_profile or (self._profiles[0] if self._profiles else None)

        self._input_name = saved_input.name if saved_input else None
        self._output_name = output.name if output else None
        self._voice_name = profile.name if profile else None
        self._initialised = True
        self._models_ready = base_models_present(models_dir())

    def initial_status(self) -> Status:
        if not self._profiles:
            return NO_VOICES_MESSAGE, "warning"
        if find_virtual_output(self._outputs) is None:
            return NO_VIRTUAL_DEVICE_MESSAGE, "warning"
        return READY_STATUS

    def back_status(self) -> Status | None:
        return WAIT_STATUS if self._working else None

    def select_input(self, name: str | None) -> None:
        self._input_name = name
        self.schedule_save()

    def select_output(self, name: str | None) -> None:
        self._output_name = name
        self.schedule_save()

    def select_voice(self, name: str | None) -> None:
        self._voice_name = name
        self.schedule_save()

    def change_pitch(self, value: int) -> None:
        self._pitch = max(MIN_PITCH, min(MAX_PITCH, value))
        if self._engine is not None and self._converting:
            self._engine.set_pitch(self._pitch)
        self.schedule_save()

    def set_voice_option(self, name: str, value: int) -> None:
        self._voice_options[name] = value
        self._apply_voice_options()
        self.schedule_save()

    def set_gate_value(self, name: str, text: str) -> None:
        value = float(text) if name.endswith("_db") else int(text)
        self._apply_gate(replace(self._gate, **{name: value}))

    @property
    def noise_reduction(self) -> bool:
        return self._noise_reduction

    def set_noise_reduction(self, on: bool) -> None:
        self._noise_reduction = on
        if self._pipeline is not None:
            self._pipeline.set_noise_reduction(on)
        self.schedule_save()

    @property
    def bump_filter(self) -> bool:
        return self._gate.block_bumps

    def set_bump_filter(self, on: bool) -> None:
        self._apply_gate(replace(self._gate, block_bumps=on))

    def select_preset(self, key: str) -> bool:
        self.schedule_save()
        preset = PERFORMANCE_PRESETS.get(key)
        if preset is None:
            return False
        _, values = preset
        self._voice_options.update({name: int(values[name]) for name in self._voice_options})
        self._gate = GateSettings(
            block_bumps=self._gate.block_bumps,
            **{name: values[setting] for name, setting in GATE_SETTING_NAMES.items()},
        )
        return True

    def reset_advanced(self) -> None:
        defaults = Settings()
        self._voice_options.update(
            {name: int(getattr(defaults, name)) for name in self._voice_options}
        )
        self._apply_gate(GateSettings(block_bumps=True))
        self.set_noise_reduction(True)

    def begin_download(self) -> None:
        self._working = True

    def download_models(self, progress: Callable[[str, float], None]) -> None:
        ensure_base_models(models_dir(), progress)

    def download_status(self, message: str) -> Status:
        return f"Downloading… {message}", ""

    def download_finished(self) -> Status:
        self._models_ready = True
        self._working = False
        return self.initial_status()

    def download_failed(self, message: str) -> Status:
        self._working = False
        return f"Error: {message}", "error"

    def begin_start(self) -> tuple[StartRequest | None, Status]:
        input_device = find_device_by_name(self._inputs, self._input_name)
        output_device = find_device_by_name(self._outputs, self._output_name)
        profile = next((p for p in self._profiles if p.name == self._voice_name), None)
        if profile is None:
            return None, (NO_VOICES_MESSAGE, "warning")
        if output_device is None:
            return None, (NO_VIRTUAL_DEVICE_MESSAGE, "warning")
        if input_device is None:
            return None, ("Error: Select a microphone first.", "error")
        self._working = True
        self._pipeline_error = None
        return StartRequest(input_device, output_device, profile, self._pitch), LOADING_STATUS

    def start_pipeline(self, request: StartRequest) -> ConversionPipeline:
        engine = self._get_engine()
        engine.set_pitch(request.pitch)
        self._apply_voice_options(engine=engine)
        if self._loaded_profile != request.profile.name:
            engine.load(request.profile)
            self._loaded_profile = request.profile.name
        pipeline = ConversionPipeline(
            engine,
            request.input_device,
            request.output_device,
            on_levels=self._store_levels,
            on_error=self._store_error,
            block_ms=self._voice_options["block_ms"],
            context_ms=self._voice_options["context_ms"],
            crossfade_ms=self._voice_options["crossfade_ms"],
            hum_filter_hz=self._voice_options["hum_filter_hz"],
            gate_settings=self._gate,
            noise_reduction=self._noise_reduction,
        )
        pipeline.warm_up()
        pipeline.start()
        return pipeline

    def start_succeeded(self, pipeline: ConversionPipeline) -> Status:
        self._pipeline = pipeline
        self._working = False
        self._converting = True
        self._slow_warned = False
        return RUNNING_STATUS

    def start_failed(self, message: str) -> Status:
        self._working = False
        self._converting = False
        return f"Error: {message}", "error"

    def stop(self) -> Status:
        self.stop_pipeline()
        return READY_STATUS

    def stop_pipeline(self) -> None:
        pipeline, self._pipeline = self._pipeline, None
        self._converting = False
        if pipeline is not None:
            pipeline.stop()
        # Zero after stop(): the worker may still report the block it was converting.
        self._input_level = 0.0
        self._output_level = 0.0

    def tick(self) -> LiveState:
        input_level, output_level = self._input_level, self._output_level
        error, self._pipeline_error = self._pipeline_error, None
        if error is not None and self._converting:
            self._converting = False
            self._working = True
            message = str(error) or type(error).__name__
            return LiveState(input_level, output_level, stop_message=message)
        return LiveState(input_level, output_level, status=self._slow_status())

    def schedule_save(self) -> None:
        if not self._initialised:
            return
        self._pending_save = dict(
            input_device=self._input_name,
            output_device=self._output_name,
            profile=self._voice_name,
            pitch=self._pitch,
            **self._voice_options,
            gate_hold_ms=self._gate.hold_ms,
            gate_pre_open_ms=self._gate.pre_open_ms,
            gate_open_above_db=self._gate.open_above_floor_db,
            gate_open_below_voice_db=self._gate.open_below_voice_db,
            noise_reduction=self._noise_reduction,
            bump_filter=self._gate.block_bumps,
        )
        if self._save_timer is not None:
            self._save_timer.stop()
        self._save_timer = self._set_timer(SAVE_DELAY_SECONDS, self.flush_save)

    def flush_save(self) -> None:
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

    def _preset_values(self) -> dict[str, float]:
        gate = {setting: getattr(self._gate, name) for name, setting in GATE_SETTING_NAMES.items()}
        return {**self._voice_options, **gate}

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
        self.schedule_save()

    def _get_engine(self) -> RvcEngine:
        if self._engine is None:
            self._engine = RvcEngine(
                base_model_paths(models_dir()),
                cpu_threads=self._settings.cpu_threads,
                precision=self._settings.precision,
            )
        return self._engine

    def _store_levels(self, input_rms: float, output_rms: float) -> None:
        if not self._converting:
            return
        self._input_level = input_rms
        self._output_level = output_rms

    def _store_error(self, error: Exception) -> None:
        self._pipeline_error = error

    def _slow_status(self) -> Status | None:
        pipeline = self._pipeline
        if pipeline is None or not self._converting or self._slow_warned:
            return None
        dropped = pipeline.dropped_blocks
        if pipeline.load < SLOW_LOAD and not dropped:
            return None
        self._slow_warned = True
        logger.warning("Conversion too slow: load %.2f, dropped %d", pipeline.load, dropped)
        message = SLOW_MESSAGE.format(
            percent=round(pipeline.load * 100),
            dropped=f", {dropped} block(s) dropped" if dropped else "",
        )
        return message, "warning"


def _first_start_settings() -> Settings | None:
    if settings_saved() or select_torch_device().type != "cpu":
        return None
    logger.info("No GPU found: starting with the %s preset", FIRST_START_CPU_PRESET)
    return apply_preset(Settings(), FIRST_START_CPU_PRESET)
