from pathlib import Path

import pytest
import torch

from tests.conftest import FakeEngine
from voice_clone import cli
from voice_clone.domain.bench import BenchResult
from voice_clone.domain.config import PERFORMANCE_PRESETS, Settings
from voice_clone.domain.errors import TrainingError, VoiceCloneError
from voice_clone.domain.profiles import VoiceProfile


@pytest.fixture(autouse=True)
def _no_log_file(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "setup_logging", lambda: Path("unused.log"))


def test_train_passes_options(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def fake_train(options, applio, training_root, voices_root):
        seen["options"] = options

    monkeypatch.setattr("voice_clone.domain.training.train_voice", fake_train)

    code = cli.main(["train", "a.m4a", "b.m4a", "--name", "me", "--epochs", "50"])

    assert code == 0
    assert seen["options"].name == "me"
    assert seen["options"].epochs == 50
    assert [p.name for p in seen["options"].inputs] == ["a.m4a", "b.m4a"]


def test_train_error_returns_exit_code_1(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_train(*_: object) -> None:
        raise TrainingError("boom")

    monkeypatch.setattr("voice_clone.domain.training.train_voice", fake_train)

    assert cli.main(["train", "a.m4a"]) == cli.EXIT_ERROR


def test_train_ctrl_c_returns_exit_code_130(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_train(*_: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr("voice_clone.domain.training.train_voice", fake_train)

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

    monkeypatch.setattr("voice_clone.views.app.VoiceCloneApp", FakeApp)

    assert cli.main(argv) == 0
    assert opened == [True]


def test_restart_runs_the_app_again_and_rescans_devices(monkeypatch: pytest.MonkeyPatch) -> None:
    import voice_clone.views.app as app_module

    results = iter([app_module.RESTART, app_module.RESTART, None])
    runs = []
    rescans = []

    class FakeApp:
        def run(self):
            runs.append(True)
            return next(results)

    monkeypatch.setattr(app_module, "VoiceCloneApp", FakeApp)
    monkeypatch.setattr("voice_clone.domain.audio.rescan_devices", lambda: rescans.append(True))

    assert cli.main(["run"]) == 0
    assert len(runs) == 3
    assert len(rescans) == 2


def test_r_key_exits_with_restart() -> None:
    import asyncio

    from voice_clone.views.app import RESTART, VoiceCloneApp

    async def scenario():
        app = VoiceCloneApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("r")
            await pilot.pause()
        return app.return_value

    assert asyncio.run(scenario()) == RESTART


CONTROLLER = "voice_clone.controllers.setup_controller"


class BenchEngine(FakeEngine):
    precision = "fp32"

    def __init__(self, paths=None, device=None, cpu_threads=0, precision="auto") -> None:
        super().__init__()

    def load(self, profile) -> None:
        self.output_sample_rate = 40000


def patch_bench_fakes(monkeypatch, results, profiles=None, models_present=True):
    fakes = {
        "load_settings": lambda: Settings(),
        "base_models_present": lambda path: models_present,
        "select_torch_device": lambda: torch.device("cpu"),
        "RvcEngine": BenchEngine,
        "base_model_paths": lambda path: {},
        "models_dir": lambda: Path("models"),
        "discover_profiles": lambda path: [PROFILE] if profiles is None else profiles,
        "apply_engine_options": lambda engine, values: None,
        "run_bench": lambda engine, values, seconds: results[next(iter(_by_values(values)))],
        "voices_dir": lambda: Path("voices"),
    }
    for name, fake in fakes.items():
        monkeypatch.setattr(f"{CONTROLLER}.{name}", fake)


def _by_values(values):
    return [name for name, (_, preset) in PERFORMANCE_PRESETS.items() if preset is values]


PROFILE = VoiceProfile("me", Path("me.pth"), None)
BENCH_RESULTS = {
    "minimal": BenchResult(1000, [0.30], {"hubert": 40.0, "rvc": 80.4}),
    "light": BenchResult(600, [0.50], {"hubert": 30.0, "rvc": 70.0}),
    "balanced": BenchResult(400, [0.60], {"hubert": 20.0, "rvc": 60.0}),
    "high": BenchResult(300, [1.10], {"hubert": 10.0, "rvc": 50.0}),
    "ultra": BenchResult(200, [1.30], {"hubert": 5.0, "rvc": 40.0}),
}


def test_bench_without_base_models_prints_a_message_and_returns_error(
    monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    patch_bench_fakes(monkeypatch, BENCH_RESULTS, models_present=False)

    code = cli.main(["bench", "--cpu"])

    assert code == cli.EXIT_ERROR
    assert capsys.readouterr().out == (
        "Base models are missing. Open the app and choose Check setup first.\n"
    )


def test_bench_with_an_unknown_voice_prints_a_message_and_returns_error(
    monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    patch_bench_fakes(monkeypatch, BENCH_RESULTS)

    code = cli.main(["bench", "--cpu", "--voice", "ghost"])

    assert code == cli.EXIT_ERROR
    assert capsys.readouterr().out == "Voice not found: ghost\n"


def test_bench_without_any_voice_prints_no_voices_found(
    monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    patch_bench_fakes(monkeypatch, BENCH_RESULTS, profiles=[])

    code = cli.main(["bench", "--cpu"])

    assert code == cli.EXIT_ERROR
    assert capsys.readouterr().out == "No voices found.\n"


def test_bench_prints_the_table_and_the_recommended_preset(
    monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    patch_bench_fakes(monkeypatch, BENCH_RESULTS)
    monkeypatch.setattr(torch, "get_num_threads", lambda: 8)

    code = cli.main(["bench", "--cpu"])

    assert code == 0
    assert capsys.readouterr().out.splitlines() == [
        "Voice: me   Device: cpu (fp32)   CPU threads: 8",
        "Preset      Block   Load    p95  Slow   Stage ms per hop",
        "minimal    1000ms   0.30   0.30     0   hubert 40  rvc 80",
        "light       600ms   0.50   0.50     0   hubert 30  rvc 70",
        "balanced    400ms   0.60   0.60     0   hubert 20  rvc 60",
        "high        300ms   1.10   1.10     1   hubert 10  rvc 50",
        "ultra       200ms   1.30   1.30     1   hubert 5  rvc 40",
        "Recommended: balanced (heaviest preset up to Balanced with p95 under 0.7)",
    ]


def test_bench_with_selected_presets_prints_only_those_rows(
    monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    patch_bench_fakes(monkeypatch, BENCH_RESULTS)

    code = cli.main(["bench", "--cpu", "--preset", "minimal", "--preset", "light"])

    rows = capsys.readouterr().out.splitlines()[2:]
    assert code == 0
    assert [row.split()[0] for row in rows] == ["minimal", "light", "Recommended:"]
    assert rows[-1] == "Recommended: light (heaviest preset up to Balanced with p95 under 0.7)"


def test_bench_says_when_no_preset_keeps_up(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    patch_bench_fakes(monkeypatch, {name: BenchResult(500, [0.9]) for name in BENCH_RESULTS})

    code = cli.main(["bench", "--cpu", "--preset", "minimal"])

    assert code == 0
    assert capsys.readouterr().out.splitlines()[-1] == (
        "None of these presets keeps up comfortably (p95 under 0.7)."
    )


def test_bench_prints_the_error_when_the_bench_fails(
    monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    patch_bench_fakes(monkeypatch, BENCH_RESULTS)

    def failing(engine, values, seconds):
        raise VoiceCloneError("model broke")

    monkeypatch.setattr(f"{CONTROLLER}.run_bench", failing)

    code = cli.main(["bench", "--cpu", "--preset", "minimal"])

    assert code == cli.EXIT_ERROR
    assert capsys.readouterr().out.splitlines()[-1] == "Error: model broke"


def test_bench_ctrl_c_returns_exit_code_130(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_bench_fakes(monkeypatch, BENCH_RESULTS)

    def interrupted(engine, values, seconds):
        raise KeyboardInterrupt

    monkeypatch.setattr(f"{CONTROLLER}.run_bench", interrupted)

    assert cli.main(["bench", "--cpu", "--preset", "minimal"]) == cli.EXIT_INTERRUPTED


def test_bench_rejects_unknown_preset() -> None:
    with pytest.raises(SystemExit):
        cli.main(["bench", "--preset", "turbo"])
