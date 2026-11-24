from pathlib import Path

import platformdirs

APP_NAME = "voice-clone"


def voices_dir() -> Path:
    return Path.cwd() / "voices"


def models_dir() -> Path:
    return Path.cwd() / "models"


def config_dir() -> Path:
    return platformdirs.user_config_path(APP_NAME)


def log_dir() -> Path:
    return platformdirs.user_log_path(APP_NAME)


def training_dir() -> Path:
    return Path.cwd() / "training"
