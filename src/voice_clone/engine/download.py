import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from huggingface_hub import hf_hub_download

from voice_clone.errors import ModelDownloadError

logger = logging.getLogger(__name__)

CONTENTVEC_REPO = "lengyue233/content-vec-best"
CONTENTVEC_FILES = ("config.json", "pytorch_model.bin")
RMVPE_REPO = "lj1995/VoiceConversionWebUI"
RMVPE_FILE = "rmvpe.pt"
CONTENTVEC_DIRNAME = "content-vec-best"
RMVPE_DIRNAME = "rmvpe"

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


def base_models_present(models_dir: Path) -> bool:
    paths = base_model_paths(models_dir)
    contentvec_ok = all((paths.contentvec_dir / name).is_file() for name in CONTENTVEC_FILES)
    return contentvec_ok and paths.rmvpe_path.is_file()


def ensure_base_models(
    models_dir: Path, on_progress: ProgressCallback | None = None
) -> BaseModelPaths:
    paths = base_model_paths(models_dir)
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


def _report(on_progress: ProgressCallback | None, message: str, fraction: float) -> None:
    if on_progress is not None:
        on_progress(message, fraction)
