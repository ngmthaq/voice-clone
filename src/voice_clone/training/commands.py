import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol

from voice_clone.errors import TrainingError

INSTALL_HINTS = {
    "ffmpeg": "Install: 'brew install ffmpeg' (macOS) or 'winget install ffmpeg' (Windows).",
    "git": "Install: 'xcode-select --install' (macOS) or 'winget install Git.Git' (Windows).",
}
PYTHON_HINT = (
    "Install Python {version} from https://www.python.org/downloads/ "
    "(macOS: or 'brew install python@{version}')."
)


class CommandRunner(Protocol):
    def __call__(
        self,
        args: Sequence[str],
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
    ) -> None: ...


def run_command(
    args: Sequence[str],
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> None:
    """Run a command and stream its output to the console. Non-zero exit raises."""
    try:
        result = subprocess.run(list(args), cwd=cwd, env=dict(env) if env else None, check=False)
    except OSError as exc:
        raise TrainingError(f"Could not run '{args[0]}': {exc}") from exc
    if result.returncode != 0:
        raise TrainingError(f"Command failed (exit code {result.returncode}): {' '.join(args)}")


def require_tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        hint = INSTALL_HINTS.get(name, "")
        raise TrainingError(f"'{name}' was not found. {hint}".strip())
    return path


def find_python(version: str, platform: str = sys.platform) -> list[str]:
    """Return the command that starts Python <version>, e.g. ['/usr/bin/python3.12']."""
    path = shutil.which(f"python{version}")
    if path is not None:
        return [path]
    if platform == "win32":
        launcher = shutil.which("py")
        if launcher is not None and _starts([launcher, f"-{version}", "-c", "pass"]):
            return [launcher, f"-{version}"]
    raise TrainingError(
        f"Python {version} was not found. It is needed to train voices. "
        + PYTHON_HINT.format(version=version)
    )


def _starts(args: Sequence[str]) -> bool:
    try:
        return subprocess.run(list(args), capture_output=True, check=False).returncode == 0
    except OSError:
        return False
