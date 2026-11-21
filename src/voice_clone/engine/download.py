import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import tqdm
from huggingface_hub import hf_hub_download
from huggingface_hub.utils import disable_progress_bars

from voice_clone.errors import ModelDownloadError

logger = logging.getLogger(__name__)

CONTENTVEC_REPO = "lengyue233/content-vec-best"
CONTENTVEC_FILES = ("config.json", "pytorch_model.bin")
RMVPE_REPO = "lj1995/VoiceConversionWebUI"
RMVPE_FILE = "rmvpe.pt"
CONTENTVEC_DIRNAME = "content-vec-best"
RMVPE_DIRNAME = "rmvpe"
# Rough download sizes, shown before the download starts.
CONTENTVEC_APPROX_MB = {"config.json": 1, "pytorch_model.bin": 378}
RMVPE_APPROX_MB = 181

ProgressCallback = Callable[[str, float], None]


@dataclass(frozen=True)
class BaseModelPaths:
    contentvec_dir: Path
    rmvpe_path: Path


def base_model_paths(models_dir: Path) -> BaseModelPaths:
    return BaseModelPaths(
        contentvec_dir=models_dir / CONTENTVEC_DIRNAME,
        rmvpe_path=models_dir / RMVPE_DIRNAME / RMVPE_FILE,
    )


@dataclass(frozen=True)
class BaseModelFile:
    """One file the voice changer needs, for showing what is downloaded."""

    name: str
    purpose: str
    path: Path
    approx_mb: int

    @property
    def present(self) -> bool:
        return self.path.is_file()


def base_model_files(models_dir: Path) -> list[BaseModelFile]:
    paths = base_model_paths(models_dir)
    return [
        BaseModelFile(
            f"{CONTENTVEC_DIRNAME}/{name}",
            "ContentVec: reads the words and sounds of your voice",
            paths.contentvec_dir / name,
            CONTENTVEC_APPROX_MB[name],
        )
        for name in CONTENTVEC_FILES
    ] + [
        BaseModelFile(
            f"{RMVPE_DIRNAME}/{RMVPE_FILE}",
            "RMVPE: finds the pitch of your voice",
            paths.rmvpe_path,
            RMVPE_APPROX_MB,
        )
    ]


def base_models_present(models_dir: Path) -> bool:
    return all(file.present for file in base_model_files(models_dir))


def ensure_base_models(
    models_dir: Path, on_progress: ProgressCallback | None = None
) -> BaseModelPaths:
    paths = base_model_paths(models_dir)
    _quiet_progress_bars()
    downloads = [
        (CONTENTVEC_REPO, name, paths.contentvec_dir, paths.contentvec_dir / name)
        for name in CONTENTVEC_FILES
    ]
    downloads.append((RMVPE_REPO, RMVPE_FILE, paths.rmvpe_path.parent, paths.rmvpe_path))
    total = len(downloads)
    for index, (repo, filename, target_dir, target) in enumerate(downloads):
        if target.is_file():
            _report(on_progress, f"{filename} already downloaded", (index + 1) / total)
            continue
        _report(on_progress, f"Downloading {filename}", index / total)
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            hf_hub_download(repo_id=repo, filename=filename, local_dir=target_dir)
        except Exception as error:
            logger.exception("Download of %s from %s failed", filename, repo)
            raise ModelDownloadError(
                f"Could not download {filename}. Check your internet connection and try again."
            ) from error
        _report(on_progress, f"Downloaded {filename}", (index + 1) / total)
    return paths


def _quiet_progress_bars() -> None:
    """Make huggingface_hub downloads safe to run inside the TUI.

    The app shows its own progress, so hub progress bars are turned off. tqdm still
    creates a multiprocessing lock, which on Python 3.12 starts a helper process that
    needs a real stderr. While Textual owns the terminal, stderr has no file number and
    the download fails with "bad value(s) in fds_to_keep". A thread lock avoids that.
    """
    disable_progress_bars()
    tqdm.tqdm.set_lock(threading.RLock())


def _report(on_progress: ProgressCallback | None, message: str, fraction: float) -> None:
    if on_progress is not None:
        on_progress(message, fraction)
