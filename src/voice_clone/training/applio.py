import logging
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from voice_clone.errors import TrainingError
from voice_clone.training.commands import CommandRunner, find_python, require_tool, run_command

logger = logging.getLogger(__name__)

APPLIO_REPO = "https://github.com/IAHispano/Applio.git"
APPLIO_VERSION = "3.7.1"
APPLIO_COMMIT = "6f69726b140c615c8cc6831a7db8b7c5e48ba8af"
APPLIO_PYTHON = "3.12"
WINDOWS_TORCH_INDEX = "https://download.pytorch.org/whl/cu128"
READY_MARKER = ".voice-clone-ready"
# "0" lets Applio pick CUDA, then Apple MPS, then CPU. "-" forces CPU.
GPU_ID = "0"
CPU_ID = "-"


def git_head(repo_dir: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo_dir), "rev-parse", "HEAD"], text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise TrainingError(f"Could not read the Applio version: {exc}") from exc


class Applio:
    """Runs a pinned Applio release in its own virtual environment."""

    def __init__(
        self,
        root: Path,
        runner: CommandRunner = run_command,
        head_reader: Callable[[Path], str] = git_head,
        platform: str = sys.platform,
        python_finder: Callable[[str, str], list[str]] = find_python,
    ) -> None:
        self.root = root
        self.source_dir = root / f"Applio-{APPLIO_VERSION}"
        self.logs_dir = root / "logs"
        self.config_dir = root / "config"
        self._runner = runner
        self._head_reader = head_reader
        self._platform = platform
        self._python_finder = python_finder

    @property
    def python(self) -> Path:
        if self._platform == "win32":
            return self.source_dir / ".venv" / "Scripts" / "python.exe"
        return self.source_dir / ".venv" / "bin" / "python"

    @property
    def is_installed(self) -> bool:
        marker = self.source_dir / READY_MARKER
        return marker.is_file() and marker.read_text().strip() == APPLIO_COMMIT

    def model_dir(self, name: str) -> Path:
        return self.logs_dir / name

    def ensure_installed(self) -> None:
        if self.is_installed:
            return
        git = require_tool("git")
        base_python = self._python_finder(APPLIO_PYTHON, self._platform)
        if self.source_dir.exists():
            shutil.rmtree(self.source_dir)
        self.root.mkdir(parents=True, exist_ok=True)

        self._runner(
            [
                git,
                "clone",
                "--depth",
                "1",
                "--branch",
                APPLIO_VERSION,
                APPLIO_REPO,
                str(self.source_dir),
            ]
        )
        head = self._head_reader(self.source_dir)
        if head != APPLIO_COMMIT:
            raise TrainingError(
                f"Applio {APPLIO_VERSION} has commit {head}, expected {APPLIO_COMMIT}. "
                "The release may have changed; stopping for safety."
            )

        self._runner([*base_python, "-m", "venv", ".venv"], cwd=self.source_dir)
        pip = [str(self.python), "-m", "pip", "install"]
        self._runner([*pip, "--upgrade", "pip"], cwd=self.source_dir)
        install = [*pip, "-r", "requirements-engine.txt"]
        if self._platform == "win32":
            # CUDA wheels carry a "+cu128" tag, which pip ranks above the plain CPU wheels.
            install += ["--extra-index-url", WINDOWS_TORCH_INDEX]
        self._runner(install, cwd=self.source_dir)

        prerequisites = ["prerequisites", "--pretraineds-hifigan", "--models"]
        prerequisites.append("--exe" if self._platform == "win32" else "--no-exe")
        self._core(prerequisites)
        (self.source_dir / READY_MARKER).write_text(APPLIO_COMMIT)

    def preprocess(self, name: str, dataset_dir: Path, sample_rate: int, cpu_cores: int) -> None:
        self._core(
            [
                "preprocess",
                "--model-name",
                name,
                "--dataset-path",
                str(dataset_dir.resolve()),
                "--sample-rate",
                str(sample_rate),
                "--cpu-cores",
                str(cpu_cores),
                "--cut-preprocess",
                "Automatic",
            ]
        )
        self._require_output(self.model_dir(name) / "sliced_audios", "Preprocessing")

    def extract(self, name: str, sample_rate: int, cpu_cores: int) -> None:
        self._core(
            [
                "extract",
                "--model-name",
                name,
                "--f0-method",
                "rmvpe",
                "--gpu",
                self._extract_device,
                "--sample-rate",
                str(sample_rate),
                "--cpu-cores",
                str(cpu_cores),
                "--embedder-model",
                "contentvec",
            ]
        )
        extracted = self.model_dir(name) / "extracted"
        if not extracted.is_dir() or not any(extracted.iterdir()):
            raise TrainingError(
                "Feature extraction made no files. See the Applio output above for the reason."
            )

    @property
    def _extract_device(self) -> str:
        # Applio 3.7.1 embedding extraction fails on Apple MPS (float64 tensors), so use CPU.
        return CPU_ID if self._platform == "darwin" else GPU_ID

    def train(
        self, name: str, epochs: int, sample_rate: int, batch_size: int, save_every: int
    ) -> None:
        self._core(
            [
                "train",
                "--model-name",
                name,
                "--total-epoch",
                str(epochs),
                "--sample-rate",
                str(sample_rate),
                "--batch-size",
                str(batch_size),
                "--save-every-epoch",
                str(save_every),
                "--save-only-latest",
                "--gpu",
                GPU_ID,
                "--vocoder",
                "HiFi-GAN",
                "--index-algorithm",
                "Auto",
            ]
        )

    def _core(self, args: list[str]) -> None:
        if not self.python.is_file():
            raise TrainingError("Applio is not installed. Run the train command again.")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self._runner([str(self.python), "core.py", *args], cwd=self.source_dir, env=self._env())

    def _env(self) -> dict[str, str]:
        env = dict(os.environ)
        env["APPLIO_LOGS_DIR"] = str(self.logs_dir.resolve())
        env["APPLIO_CONFIG_DIR"] = str(self.config_dir.resolve())
        env["PYTHONUNBUFFERED"] = "1"
        env.pop("VIRTUAL_ENV", None)
        return env

    @staticmethod
    def _require_output(path: Path, step: str) -> None:
        # Applio's core.py prints errors but still exits 0, so check its output files.
        if not path.exists():
            raise TrainingError(f"{step} failed. See the Applio output above for the reason.")
