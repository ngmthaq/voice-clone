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
    gate_hold_ms: int = Field(500, ge=0, le=2000)
    gate_pre_open_ms: int = Field(100, ge=0, le=400)
    gate_open_above_db: float = Field(6.0, ge=0, le=30)


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
