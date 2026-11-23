import logging
from pathlib import Path

import tomli
import tomli_w
from pydantic import BaseModel, Field, ValidationError

from voice_clone.paths import config_dir

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
    block_ms: int = Field(400, ge=100, le=1000)
    crossfade_ms: int = Field(80, ge=10, le=200)
    hum_filter_hz: int = Field(90, ge=0, le=200)
    train_name: str = "my-voice"
    train_epochs: int = Field(200, ge=1, le=10000)
    train_batch_size: int = Field(8, ge=1, le=50)
    train_sample_rate: int = 40000
    train_save_every: int = Field(10, ge=1, le=100)


def settings_path() -> Path:
    return config_dir() / SETTINGS_FILE_NAME


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
    with target.open("wb") as file:
        tomli_w.dump(data, file)


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
)


def _preset(**values: float) -> dict[str, float]:
    defaults = Settings()
    return {name: getattr(defaults, name) for name in PRESET_FIELDS} | values


PERFORMANCE_PRESETS: dict[str, tuple[str, dict[str, float]]] = {
    "light": (
        "Light: laptop or older GPU, or no GPU (more delay)",
        _preset(
            index_percent=40,
            protect_percent=75,
            loudness_percent=60,
            pitch_smoothing_ms=50,
            context_ms=300,
            block_ms=600,
            crossfade_ms=60,
            gate_hold_ms=300,
            gate_open_above_db=8.0,
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
