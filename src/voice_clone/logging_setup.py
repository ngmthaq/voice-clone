import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from voice_clone.paths import log_dir

LOG_FILE_NAME = "voice-clone.log"
MAX_LOG_BYTES = 1_000_000
LOG_BACKUP_COUNT = 3
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def setup_logging(level: int = logging.INFO) -> Path:
    directory = log_dir()
    directory.mkdir(parents=True, exist_ok=True)
    log_file = directory / LOG_FILE_NAME

    handler = RotatingFileHandler(
        log_file, maxBytes=MAX_LOG_BYTES, backupCount=LOG_BACKUP_COUNT, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter(LOG_FORMAT))

    root = logging.getLogger()
    for existing in list(root.handlers):
        root.removeHandler(existing)
        existing.close()
    root.addHandler(handler)
    root.setLevel(level)
    return log_file
