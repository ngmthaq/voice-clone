from pathlib import Path

import pytest

from voice_clone import cli
from voice_clone.errors import TrainingError


@pytest.fixture(autouse=True)
def _no_log_file(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "setup_logging", lambda: Path("unused.log"))


def test_train_passes_options(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def fake_train(options, applio, training_root, voices_root):
        seen["options"] = options

    monkeypatch.setattr("voice_clone.training.train_voice", fake_train)

    code = cli.main(["train", "a.m4a", "b.m4a", "--name", "me", "--epochs", "50"])

    assert code == 0
    assert seen["options"].name == "me"
    assert seen["options"].epochs == 50
    assert [p.name for p in seen["options"].inputs] == ["a.m4a", "b.m4a"]


def test_train_error_returns_exit_code_1(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_train(*_: object) -> None:
        raise TrainingError("boom")

    monkeypatch.setattr("voice_clone.training.train_voice", fake_train)

    assert cli.main(["train", "a.m4a"]) == cli.EXIT_ERROR


def test_train_ctrl_c_returns_exit_code_130(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_train(*_: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr("voice_clone.training.train_voice", fake_train)

    assert cli.main(["train", "a.m4a"]) == cli.EXIT_INTERRUPTED


def test_train_rejects_unknown_sample_rate() -> None:
    with pytest.raises(SystemExit):
        cli.main(["train", "a.m4a", "--sample-rate", "22050"])


@pytest.mark.parametrize("argv", [[], ["run"]])
def test_run_and_no_command_open_the_app(monkeypatch: pytest.MonkeyPatch, argv) -> None:
    opened = []

    class FakeApp:
        def run(self) -> None:
            opened.append(True)

    monkeypatch.setattr("voice_clone.app.VoiceCloneApp", FakeApp)

    assert cli.main(argv) == 0
    assert opened == [True]
