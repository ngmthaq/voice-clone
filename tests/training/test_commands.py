import sys
import threading
import time

import pytest

from voice_clone.errors import TrainingError, TrainingStoppedError
from voice_clone.training.commands import StreamingRunner


def _python(code: str) -> list[str]:
    return [sys.executable, "-c", code]


class Collected:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.transient: list[str] = []

    def runner(self) -> StreamingRunner:
        return StreamingRunner(on_line=self.lines.append, on_transient=self.transient.append)


def test_lines_and_progress_redraws_are_split() -> None:
    out = Collected()
    code = (
        "import sys, time\n"
        "w = sys.stdout.buffer.write\n"
        "w(b'first\\nsecond\\r')\n"
        "sys.stdout.flush(); time.sleep(0.05)\n"
        "w(b'\\nbar 1\\rbar 2\\r\\n')\n"
        "sys.stdout.flush()\n"
        "sys.stderr.write('from stderr\\n'); sys.stderr.flush()\n"
        "w('h\\u00e9llo'.encode())\n"
    )

    out.runner()(_python(code))

    assert out.lines == ["first", "second", "bar 2", "from stderr", "héllo"]
    assert out.transient == ["bar 1"]


def test_failed_command_raises() -> None:
    with pytest.raises(TrainingError, match="exit code 3"):
        Collected().runner()(_python("raise SystemExit(3)"))


def test_missing_program_raises() -> None:
    with pytest.raises(TrainingError, match="Could not run"):
        Collected().runner()(["voice-clone-no-such-program"])


def test_stop_ends_the_command_and_its_children() -> None:
    out = Collected()
    runner = out.runner()
    code = (
        "import subprocess, sys, time\n"
        "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])\n"
        "print('ready', flush=True)\n"
        "time.sleep(30)\n"
    )
    errors: list[Exception] = []

    def run() -> None:
        try:
            runner(_python(code))
        except Exception as exc:
            errors.append(exc)

    thread = threading.Thread(target=run)
    thread.start()
    deadline = time.monotonic() + 10
    while "ready" not in out.lines and time.monotonic() < deadline:
        time.sleep(0.02)
    runner.stop()
    thread.join(timeout=10)

    assert not thread.is_alive()
    assert len(errors) == 1 and isinstance(errors[0], TrainingStoppedError)


def test_no_command_runs_after_stop() -> None:
    out = Collected()
    runner = out.runner()
    runner.stop()

    with pytest.raises(TrainingStoppedError):
        runner(_python("print('should not run')"))
    assert out.lines == []
