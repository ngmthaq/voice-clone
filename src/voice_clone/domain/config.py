import logging
import os
from pathlib import Path
from typing import Literal

import tomli
import tomli_w
from pydantic import BaseModel, Field, ValidationError

from voice_clone.domain.paths import config_dir

logger = logging.getLogger(__name__)

SETTINGS_FILE_NAME = "settings.toml"


class Settings(BaseModel):
    input_device: str | None = None
    output_device: str | None = None
    profile: str | None = None
    pitch: int = Field(0, ge=-12, le=12)
    index_percent: int = Field(50, ge=0, le=100)
    protect_percent: int = Field(67, ge=0, le=100)
    loudness_percent: int = Field(50, ge=0, le=100)
    pitch_smoothing_ms: int = Field(30, ge=0, le=200)
    context_ms: int = Field(1000, ge=200, le=2000)
    gate_hold_ms: int = Field(500, ge=0, le=2000)
    gate_pre_open_ms: int = Field(100, ge=0, le=400)
    gate_open_above_db: float = Field(6.0, ge=0, le=30)
    gate_open_below_voice_db: float = Field(20.0, ge=0, le=40)
    noise_reduction: bool = True
    bump_filter: bool = True
    block_ms: int = Field(400, ge=100, le=1000)
    crossfade_ms: int = Field(80, ge=10, le=200)
    hum_filter_hz: int = Field(90, ge=0, le=200)
    cpu_threads: int = Field(0, ge=0, le=256)
    precision: Literal["auto", "fp32", "fp16"] = "auto"
    train_name: str = "my-voice"
    train_epochs: int = Field(200, ge=1, le=10000)
    train_batch_size: int = Field(8, ge=1, le=50)
    train_sample_rate: int = 40000
    train_save_every: int = Field(10, ge=1, le=100)


def settings_path() -> Path:
    return config_dir() / SETTINGS_FILE_NAME


def settings_saved() -> bool:
    return settings_path().is_file()


def load_settings(path: Path | None = None) -> Settings:
    target = path or settings_path()
    if not target.is_file():
        return Settings()
    try:
        with target.open("rb") as file:
            return Settings.model_validate(tomli.load(file))
    except (OSError, tomli.TOMLDecodeError, ValidationError) as error:
        logger.warning("Ignoring unreadable settings file %s: %s", target, error)
        return Settings()


def save_settings(settings: Settings, path: Path | None = None) -> None:
    target = path or settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    data = settings.model_dump(exclude_none=True)
    # Write a temp file and swap it in, so a crash never leaves a half-written settings file.
    temp = target.with_name(f"{target.name}.tmp")
    try:
        with temp.open("wb") as file:
            tomli_w.dump(data, file)
        os.replace(temp, target)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise


CUSTOM_PRESET = "custom"
PRESET_FIELDS = (
    "index_percent",
    "protect_percent",
    "loudness_percent",
    "pitch_smoothing_ms",
    "context_ms",
    "block_ms",
    "crossfade_ms",
    "hum_filter_hz",
    "gate_hold_ms",
    "gate_pre_open_ms",
    "gate_open_above_db",
    "gate_open_below_voice_db",
)


def _preset(**values: float) -> dict[str, float]:
    defaults = Settings()
    return {name: getattr(defaults, name) for name in PRESET_FIELDS} | values


PERFORMANCE_PRESETS: dict[str, tuple[str, dict[str, float]]] = {
    "minimal": (
        "Minimal: no GPU, or Light is still too slow (most delay)",
        _preset(
            index_percent=0,
            protect_percent=80,
            loudness_percent=60,
            pitch_smoothing_ms=60,
            context_ms=200,
            block_ms=1000,
            crossfade_ms=40,
        ),
    ),
    "light": (
        "Light: laptop or older GPU (more delay)",
        _preset(
            index_percent=40,
            protect_percent=75,
            loudness_percent=60,
            pitch_smoothing_ms=50,
            context_ms=300,
            block_ms=600,
            crossfade_ms=60,
        ),
    ),
    "balanced": (
        "Balanced: mid-range GPU or Apple M-series",
        _preset(),
    ),
    "high": (
        "High: fast GPU (less delay, clearer words)",
        _preset(
            index_percent=55,
            protect_percent=60,
            loudness_percent=45,
            pitch_smoothing_ms=25,
            context_ms=1500,
            block_ms=300,
            crossfade_ms=80,
            gate_hold_ms=500,
            gate_open_above_db=6.0,
        ),
    ),
    "ultra": (
        "Ultra: high-end GPU (least delay, clearest words)",
        _preset(
            index_percent=60,
            protect_percent=50,
            loudness_percent=40,
            pitch_smoothing_ms=20,
            context_ms=2000,
            block_ms=200,
            crossfade_ms=60,
            gate_hold_ms=600,
            gate_open_above_db=5.0,
        ),
    ),
}


def matching_preset(values: dict[str, float]) -> str:
    for key, (_, preset) in PERFORMANCE_PRESETS.items():
        if all(values.get(name) == value for name, value in preset.items()):
            return key
    return CUSTOM_PRESET


def apply_preset(settings: Settings, key: str) -> Settings:
    _, values = PERFORMANCE_PRESETS[key]
    return Settings.model_validate({**settings.model_dump(), **values})
