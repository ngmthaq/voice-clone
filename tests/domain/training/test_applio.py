from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from voice_clone.domain.errors import TrainingError
from voice_clone.domain.training import applio as applio_module
from voice_clone.domain.training import commands as commands_module
from voice_clone.domain.training.applio import APPLIO_COMMIT, READY_MARKER, Applio


class RecordingRunner:
    def __init__(self, applio_ref: list[Applio]) -> None:
        self.calls: list[tuple[list[str], Path | None, Mapping[str, str] | None]] = []
        self._applio_ref = applio_ref

    def __call__(
        self, args: Sequence[str], cwd: Path | None = None, env: Mapping[str, str] | None = None
    ) -> None:
        self.calls.append((list(args), cwd, env))
        applio = self._applio_ref[0]
        if "clone" in args:
            applio.source_dir.mkdir(parents=True)
        if "venv" in args:
            applio.python.parent.mkdir(parents=True)
            applio.python.touch()


@pytest.fixture(autouse=True)
def _tools(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(applio_module, "require_tool", lambda name: f"/bin/{name}")


def _make(tmp_path: Path, platform: str = "darwin", head: str = APPLIO_COMMIT):
    ref: list[Applio] = []
    runner = RecordingRunner(ref)
    applio = Applio(
        tmp_path / ".applio",
        runner=runner,
        head_reader=lambda _: head,
        platform=platform,
        python_finder=lambda version, _: [f"/bin/python{version}"],
    )
    ref.append(applio)
    return applio, runner


def _step(args: list[str]) -> str:
    return next(s for s in ("clone", "venv", "pip", "prerequisites") if s in args)


def test_install_runs_clone_venv_requirements_and_prerequisites(tmp_path: Path) -> None:
    applio, runner = _make(tmp_path)

    applio.ensure_installed()

    steps = [_step(args) for args, _, _ in runner.calls]
    assert steps == ["clone", "venv", "pip", "pip", "prerequisites"]
    assert runner.calls[1][0][:3] == ["/bin/python3.12", "-m", "venv"]
    assert applio.is_installed


def test_install_is_skipped_when_marker_matches(tmp_path: Path) -> None:
    applio, runner = _make(tmp_path)
    applio.source_dir.mkdir(parents=True)
    (applio.source_dir / READY_MARKER).write_text(APPLIO_COMMIT)

    applio.ensure_installed()

    assert runner.calls == []


def test_install_stops_when_commit_does_not_match(tmp_path: Path) -> None:
    applio, _ = _make(tmp_path, head="deadbeef")

    with pytest.raises(TrainingError, match="expected"):
        applio.ensure_installed()
    assert not applio.is_installed


def test_install_on_windows_uses_cuda_index_and_downloads_exe(tmp_path: Path) -> None:
    applio, runner = _make(tmp_path, platform="win32")

    applio.ensure_installed()

    pip_args = next(args for args, _, _ in runner.calls if "-r" in args)
    prereq_args = next(args for args, _, _ in runner.calls if "prerequisites" in args)
    assert "--extra-index-url" in pip_args
    assert "--exe" in prereq_args
    assert applio.python.name == "python.exe"


def test_core_commands_point_applio_to_our_logs_folder(tmp_path: Path) -> None:
    applio, runner = _make(tmp_path)
    applio.ensure_installed()
    (applio.model_dir("me") / "sliced_audios").mkdir(parents=True)

    applio.preprocess("me", tmp_path / "dataset", 40000, 4)

    _, cwd, env = runner.calls[-1]
    assert cwd == applio.source_dir
    assert env is not None
    assert env["APPLIO_LOGS_DIR"] == str(applio.logs_dir.resolve())


def test_preprocess_fails_when_applio_writes_no_output(tmp_path: Path) -> None:
    applio, _ = _make(tmp_path)
    applio.ensure_installed()

    with pytest.raises(TrainingError, match="Preprocessing failed"):
        applio.preprocess("me", tmp_path / "dataset", 40000, 4)


def test_core_command_without_install_raises(tmp_path: Path) -> None:
    applio, _ = _make(tmp_path)

    with pytest.raises(TrainingError, match="not installed"):
        applio.train("me", 2, 40000, 4, 1)


def test_extract_fails_when_no_features_are_written(tmp_path: Path) -> None:
    applio, _ = _make(tmp_path)
    applio.ensure_installed()
    applio.model_dir("me").mkdir(parents=True)
    (applio.model_dir("me") / "config.json").touch()

    with pytest.raises(TrainingError, match="Feature extraction made no files"):
        applio.extract("me", 40000, 4)


@pytest.mark.parametrize(("platform", "device"), [("darwin", "-"), ("win32", "0")])
def test_extract_device_avoids_mps_on_macos(tmp_path: Path, platform: str, device: str) -> None:
    applio, runner = _make(tmp_path, platform=platform)
    applio.ensure_installed()
    extracted = applio.model_dir("me") / "extracted"
    extracted.mkdir(parents=True)
    (extracted / "a.npy").touch()

    applio.extract("me", 40000, 4)

    args = runner.calls[-1][0]
    assert args[args.index("--gpu") + 1] == device


def test_find_python_uses_versioned_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(commands_module.shutil, "which", lambda name: f"/usr/bin/{name}")

    assert commands_module.find_python("3.12", "darwin") == ["/usr/bin/python3.12"]


def test_find_python_uses_windows_launcher(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        commands_module.shutil, "which", lambda name: "C:/py.exe" if name == "py" else None
    )
    monkeypatch.setattr(commands_module, "_starts", lambda args: True)

    assert commands_module.find_python("3.12", "win32") == ["C:/py.exe", "-3.12"]


def test_find_python_missing_explains_how_to_install(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(commands_module.shutil, "which", lambda name: None)

    with pytest.raises(TrainingError, match="Python 3.12 was not found"):
        commands_module.find_python("3.12", "darwin")


def test_install_reports_each_step(tmp_path: Path) -> None:
    applio, _ = _make(tmp_path)
    messages: list[str] = []

    applio.ensure_installed(report=messages.append)

    steps = [m for m in messages if m.startswith("Step ")]
    assert [m.split(":")[0] for m in steps] == ["Step 1/4", "Step 2/4", "Step 3/4", "Step 4/4"]
    assert messages[-1] == "Applio 3.7.1 is installed."


def test_installed_applio_reports_nothing(tmp_path: Path) -> None:
    applio, runner = _make(tmp_path)
    applio.ensure_installed()
    messages: list[str] = []

    applio.ensure_installed(report=messages.append)

    assert messages == []
