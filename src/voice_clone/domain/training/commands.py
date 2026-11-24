import codecs
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Protocol

from voice_clone.domain.errors import TrainingError, TrainingStoppedError

INSTALL_HINTS = {
    "ffmpeg": "Install: 'brew install ffmpeg' (macOS) or 'winget install ffmpeg' (Windows).",
    "git": "Install: 'xcode-select --install' (macOS) or 'winget install Git.Git' (Windows).",
}
READ_CHUNK_BYTES = 4096
KILL_GRACE_SECONDS = 10.0
LINE_END = re.compile(r"\r\n|\n|\r")
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
    try:
        result = subprocess.run(list(args), cwd=cwd, env=dict(env) if env else None, check=False)
    except OSError as exc:
        raise TrainingError(f"Could not run '{args[0]}': {exc}") from exc
    if result.returncode != 0:
        raise TrainingError(f"Command failed (exit code {result.returncode}): {' '.join(args)}")


class StreamingRunner:
    """Runs commands and passes their output (stdout and stderr) to callbacks, line by line.

    on_line gets each finished line. on_transient gets progress-bar redraws (text ending in a
    lone carriage return), which should replace each other instead of piling up.
    stop() ends the running command with all its child processes, from any thread.
    """

    def __init__(
        self,
        on_line: Callable[[str], None],
        on_transient: Callable[[str], None] = lambda _: None,
        platform: str = sys.platform,
        kill_grace_seconds: float = KILL_GRACE_SECONDS,
    ) -> None:
        self._on_line = on_line
        self._kill_grace_seconds = kill_grace_seconds
        self._on_transient = on_transient
        self._platform = platform
        self._lock = threading.Lock()
        self._process: subprocess.Popen[bytes] | None = None
        self._stopped = False

    @property
    def stopped(self) -> bool:
        return self._stopped

    def __call__(
        self,
        args: Sequence[str],
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
    ) -> None:
        with self._lock:
            if self._stopped:
                raise TrainingStoppedError("Training was stopped.")
            try:
                process = subprocess.Popen(
                    list(args),
                    cwd=cwd,
                    env=dict(env) if env else None,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    bufsize=0,
                    **self._group_options(),
                )
            except OSError as exc:
                raise TrainingError(f"Could not run '{args[0]}': {exc}") from exc
            self._process = process
        try:
            assert process.stdout is not None
            self._pump(process.stdout)
            returncode = process.wait()
        finally:
            with self._lock:
                self._process = None
        if self._stopped:
            raise TrainingStoppedError("Training was stopped.")
        if returncode != 0:
            raise TrainingError(f"Command failed (exit code {returncode}): {' '.join(args)}")

    def stop(self) -> None:
        with self._lock:
            self._stopped = True
            process = self._process
        if process is not None and process.poll() is None:
            self._kill_tree(process)
            if self._platform != "win32":
                threading.Thread(
                    target=self._force_kill_later, args=(process,), daemon=True
                ).start()

    def _pump(self, stream: object) -> None:
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        pending = ""
        while True:
            chunk = stream.read(READ_CHUNK_BYTES)  # type: ignore[attr-defined]
            pending += decoder.decode(chunk or b"", final=not chunk)
            pending = self._emit(pending, final=not chunk)
            if not chunk:
                return

    def _emit(self, text: str, final: bool) -> str:
        start = 0
        for match in LINE_END.finditer(text):
            if match.group() == "\r" and match.end() == len(text) and not final:
                break
            line = text[start : match.start()]
            if match.group() == "\r":
                self._on_transient(line)
            else:
                self._on_line(line)
            start = match.end()
        rest = text[start:]
        if final and rest:
            self._on_line(rest)
            return ""
        return rest

    def _group_options(self) -> dict[str, object]:
        if self._platform == "win32":
            return {"creationflags": getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)}
        return {"start_new_session": True}

    def _force_kill_later(self, process: subprocess.Popen[bytes]) -> None:
        """SIGKILL the group if it ignored SIGTERM, so stop() never hangs."""
        try:
            process.wait(timeout=self._kill_grace_seconds)
        except subprocess.TimeoutExpired:
            self._kill_tree(process, sig=signal.SIGKILL)

    def _kill_tree(
        self, process: subprocess.Popen[bytes], sig: int = signal.SIGTERM
    ) -> None:
        try:
            if self._platform == "win32":
                subprocess.run(
                    ["taskkill", "/T", "/F", "/PID", str(process.pid)],
                    capture_output=True,
                    check=False,
                )
            else:
                os.killpg(process.pid, sig)
        except OSError:
            process.kill()


def require_tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        hint = INSTALL_HINTS.get(name, "")
        raise TrainingError(f"'{name}' was not found. {hint}".strip())
    return path


def find_python(version: str, platform: str = sys.platform) -> list[str]:
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
