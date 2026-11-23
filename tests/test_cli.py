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


def test_restart_runs_the_app_again_and_rescans_devices(monkeypatch: pytest.MonkeyPatch) -> None:
    import voice_clone.app as app_module

    results = iter([app_module.RESTART, app_module.RESTART, None])
    runs = []
    rescans = []

    class FakeApp:
        def run(self):
            runs.append(True)
            return next(results)

    monkeypatch.setattr(app_module, "VoiceCloneApp", FakeApp)
    monkeypatch.setattr("voice_clone.audio.rescan_devices", lambda: rescans.append(True))

    assert cli.main(["run"]) == 0
    assert len(runs) == 3
    assert len(rescans) == 2


def test_r_key_exits_with_restart() -> None:
    import asyncio

    from voice_clone.app import RESTART, VoiceCloneApp

    async def scenario():
        app = VoiceCloneApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("r")
            await pilot.pause()
        return app.return_value

    assert asyncio.run(scenario()) == RESTART
