import logging
from pathlib import Path

import pytest

import voice_clone.controllers.setup_controller as sc
from tests.conftest import FakeEngine
from voice_clone.controllers.setup_controller import (
    APPLIO_STOPPED_MESSAGE,
    MISSING_MODELS_MESSAGE,
    BenchSession,
    SetupController,
    SetupReport,
)
from voice_clone.domain.bench import BenchResult
from voice_clone.domain.config import PERFORMANCE_PRESETS, Settings
from voice_clone.domain.errors import ModelDownloadError, TrainingStoppedError, VoiceCloneError
from voice_clone.domain.profiles import VoiceProfile
from voice_clone.domain.setup_check import (
    APPLIO_KEY,
    MISSING,
    MODELS_KEY,
    OK,
    TRAINING,
    VOICE_CHANGER,
    Check,
    Facts,
)

PROFILE = VoiceProfile("me", Path("me.pth"), None)
FAST = BenchResult(300, [0.3, 0.3])
SLOW = BenchResult(300, [0.9, 0.9])


def make_facts(voices: list[str] | None = None) -> Facts:
    return Facts(
        platform="darwin",
        machine="arm64",
        python_version=(3, 12, 8),
        models_dir=Path("models"),
        model_files=[],
        input_devices=["Mic"],
        output_devices=["Out"],
        voices=["me"] if voices is None else voices,
    )


def check(group=VOICE_CHANGER, status=OK, key="", name="Item", download_mb=0) -> Check:
    return Check(group, name, status, "", key=key, download_mb=download_mb)


@pytest.fixture
def controller() -> SetupController:
    return SetupController()


def test_check_returns_the_evaluated_checks_and_facts(
    controller: SetupController, monkeypatch: pytest.MonkeyPatch
) -> None:
    facts = make_facts()
    checks = [check()]
    monkeypatch.setattr(sc, "gather_facts", lambda: facts)
    monkeypatch.setattr(sc, "evaluate", lambda given: checks if given is facts else [])

    report = controller.check()

    assert report == SetupReport(checks, facts)


def test_check_reports_the_error_when_gathering_facts_fails(
    controller: SetupController, monkeypatch: pytest.MonkeyPatch, caplog
) -> None:
    def boom() -> Facts:
        raise RuntimeError("no disk")

    monkeypatch.setattr(sc, "gather_facts", boom)

    with caplog.at_level(logging.ERROR):
        report = controller.check()

    assert report == SetupReport([], None, "no disk")
    assert "Setup check failed" in caplog.text


def test_check_uses_the_exception_name_when_it_has_no_message(
    controller: SetupController, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom() -> Facts:
        raise ValueError

    monkeypatch.setattr(sc, "gather_facts", boom)

    assert controller.check().error == "ValueError"


def test_summary_status_for_a_check_error(controller: SetupController) -> None:
    report = SetupReport([], None, "no disk")

    assert controller.summary_status(report) == (
        "Error: could not check the setup: no disk",
        "error",
    )


def test_summary_status_lists_missing_voice_changer_items(controller: SetupController) -> None:
    report = SetupReport(
        [
            check(VOICE_CHANGER, MISSING, name="Base Models"),
            check(VOICE_CHANGER, MISSING, name="Virtual Cable"),
            check(VOICE_CHANGER, OK, name="Python"),
            check(TRAINING, MISSING, name="FFmpeg"),
        ],
        make_facts(),
    )

    assert controller.summary_status(report) == (
        "The voice changer needs: base models, virtual cable.",
        "error",
    )


def test_summary_status_warns_when_only_training_is_missing(controller: SetupController) -> None:
    report = SetupReport([check(VOICE_CHANGER, OK), check(TRAINING, MISSING)], make_facts())

    assert controller.summary_status(report) == (
        "The voice changer is ready. Training needs the items marked ✗.",
        "warning",
    )


def test_summary_status_when_everything_is_ready(controller: SetupController) -> None:
    report = SetupReport([check(VOICE_CHANGER, OK), check(TRAINING, OK)], make_facts())

    assert controller.summary_status(report) == ("Everything is ready.", "running")


def test_download_mb_comes_from_the_missing_models_check(controller: SetupController) -> None:
    report = SetupReport([check(key=MODELS_KEY, status=MISSING, download_mb=180)], make_facts())

    assert controller.download_mb(report) == 180


def test_download_mb_is_none_when_models_are_present(controller: SetupController) -> None:
    report = SetupReport([check(key=MODELS_KEY, status=OK, download_mb=180)], make_facts())

    assert controller.download_mb(report) is None


def test_shows_applio_when_the_applio_check_exists(controller: SetupController) -> None:
    with_check = SetupReport([check(key=APPLIO_KEY)], make_facts())
    without_check = SetupReport([check(key="other")], make_facts())

    assert controller.shows_applio(with_check) is True
    assert controller.shows_applio(without_check) is False


def test_can_measure_when_models_are_present_and_a_voice_exists(
    controller: SetupController,
) -> None:
    report = SetupReport([check(key=MODELS_KEY, status=OK)], make_facts(["me"]))

    assert controller.can_measure(report) is True


def test_cannot_measure_when_models_are_missing(controller: SetupController) -> None:
    report = SetupReport([check(key=MODELS_KEY, status=MISSING)], make_facts(["me"]))

    assert controller.can_measure(report) is False


def test_cannot_measure_without_voices(controller: SetupController) -> None:
    report = SetupReport([], make_facts([]))

    assert controller.can_measure(report) is False


def test_cannot_measure_when_the_check_failed(controller: SetupController) -> None:
    assert controller.can_measure(SetupReport([], None, "boom")) is False


def test_download_passes_progress_to_ensure_base_models_and_returns_none(
    controller: SetupController, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    calls = []

    def fake_ensure(path, progress):
        calls.append(path)
        progress("rmvpe.pt", 0.5)

    monkeypatch.setattr(sc, "models_dir", lambda: tmp_path)
    monkeypatch.setattr(sc, "ensure_base_models", fake_ensure)
    seen = []

    result = controller.download(lambda name, fraction: seen.append((name, fraction)))

    assert result is None
    assert calls == [tmp_path]
    assert seen == [("rmvpe.pt", 0.5)]


def test_download_returns_the_voice_clone_error_text(
    controller: SetupController, monkeypatch: pytest.MonkeyPatch
) -> None:
    def failing(path, progress):
        raise ModelDownloadError("Could not download rmvpe.pt.")

    monkeypatch.setattr(sc, "ensure_base_models", failing)

    assert controller.download(lambda *_: None) == "Error: Could not download rmvpe.pt."


def test_download_returns_an_error_for_a_plain_exception(
    controller: SetupController, monkeypatch: pytest.MonkeyPatch
) -> None:
    def failing(path, progress):
        raise OSError("disk full")

    monkeypatch.setattr(sc, "ensure_base_models", failing)

    assert controller.download(lambda *_: None) == "Error: disk full"


class FakeApplio:
    outcome: BaseException | None = None

    def __init__(self, root, runner=None) -> None:
        self.root = root
        self.runner = runner

    def ensure_installed(self, report) -> None:
        report("Step 1/2: Downloading Applio…")
        if FakeApplio.outcome is not None:
            raise FakeApplio.outcome


@pytest.fixture
def applio(monkeypatch: pytest.MonkeyPatch, tmp_path) -> type[FakeApplio]:
    FakeApplio.outcome = None
    monkeypatch.setattr(sc, "Applio", FakeApplio)
    monkeypatch.setattr(sc, "training_dir", lambda: tmp_path)
    return FakeApplio


def test_install_applio_reports_a_step_then_done(
    controller: SetupController, applio: type[FakeApplio]
) -> None:
    controller.begin_install()

    controller.install_applio()

    assert controller.drain_events() == [("step", "Step 1/2: Downloading Applio…"), ("done", "")]


def test_drain_events_empties_the_queue(
    controller: SetupController, applio: type[FakeApplio]
) -> None:
    controller.begin_install()
    controller.install_applio()
    controller.drain_events()

    assert controller.drain_events() == []


def test_install_applio_reports_the_stop_message_when_stopped(
    controller: SetupController, applio: type[FakeApplio]
) -> None:
    applio.outcome = TrainingStoppedError("stopped")
    controller.begin_install()

    controller.install_applio()

    assert controller.drain_events()[-1] == ("stopped", APPLIO_STOPPED_MESSAGE)


def test_install_applio_reports_a_voice_clone_error_as_failed(
    controller: SetupController, applio: type[FakeApplio]
) -> None:
    applio.outcome = VoiceCloneError("git is missing")
    controller.begin_install()

    controller.install_applio()

    assert controller.drain_events()[-1] == ("failed", "Error: git is missing")


def test_install_applio_reports_a_plain_exception_as_failed(
    controller: SetupController, applio: type[FakeApplio]
) -> None:
    applio.outcome = RuntimeError("network down")
    controller.begin_install()

    controller.install_applio()

    assert controller.drain_events()[-1] == ("failed", "Error: network down")


def test_install_applio_gives_the_runner_to_applio(
    controller: SetupController, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    created = []

    class Recording(FakeApplio):
        def __init__(self, root, runner=None) -> None:
            super().__init__(root, runner)
            created.append(self)

    monkeypatch.setattr(sc, "Applio", Recording)
    monkeypatch.setattr(sc, "training_dir", lambda: tmp_path)
    controller.begin_install()

    controller.install_applio()

    assert created[0].root == tmp_path / ".applio"
    assert created[0].runner is controller._runner


def test_runner_output_becomes_line_events(controller: SetupController) -> None:
    controller.begin_install()

    controller._runner._on_line("cloning")

    assert controller.drain_events() == [("line", "cloning")]


def test_drain_events_keeps_a_non_blank_transient_while_running(
    controller: SetupController,
) -> None:
    controller.begin_install()

    controller._runner._on_transient("50%")

    assert controller.drain_events() == [("transient", "50%")]


def test_drain_events_drops_a_blank_transient(controller: SetupController) -> None:
    controller.begin_install()

    controller._runner._on_transient("   ")

    assert controller.drain_events() == []


def test_drain_events_drops_a_transient_after_stop(controller: SetupController) -> None:
    controller.begin_install()
    controller._runner._on_transient("50%")
    controller._runner._stopped = True

    assert controller.drain_events() == []


def test_drain_events_drops_a_transient_when_there_is_no_runner(
    controller: SetupController,
) -> None:
    controller.begin_install()
    controller._runner._on_transient("50%")
    controller.end_install()

    assert controller.drain_events() == []


def test_begin_install_clears_old_events(controller: SetupController) -> None:
    controller.begin_install()
    controller._runner._on_line("old")

    controller.begin_install()

    assert controller.drain_events() == []


def test_stop_install_stops_the_runner(controller: SetupController) -> None:
    controller.begin_install()

    controller.stop_install()

    assert controller._runner.stopped is True


def test_stop_install_without_a_runner_does_nothing(controller: SetupController) -> None:
    controller.stop_install()

    assert controller.installing is False


def test_installing_follows_begin_and_end_install(controller: SetupController) -> None:
    controller.begin_install()
    during = controller.installing
    controller.end_install()

    assert during is True
    assert controller.installing is False


def test_busy_follows_set_busy(controller: SetupController) -> None:
    controller.set_busy(True)

    assert controller.busy is True


def test_busy_message_is_none_when_idle(controller: SetupController) -> None:
    assert controller.busy_message is None


def test_busy_message_while_downloading(controller: SetupController) -> None:
    controller.begin_download()

    assert controller.busy_message == "Base models are downloading."


def test_busy_message_while_measuring(controller: SetupController) -> None:
    controller.begin_measure()

    assert controller.busy_message == "The speed test is running."


def test_busy_message_while_installing(controller: SetupController) -> None:
    controller.begin_install()

    assert controller.busy_message == "Applio is installing."


def test_busy_message_prefers_install_then_download_then_measure(
    controller: SetupController,
) -> None:
    controller.begin_measure()
    controller.begin_download()
    download_first = controller.busy_message
    controller.begin_install()

    assert download_first == "Base models are downloading."
    assert controller.busy_message == "Applio is installing."


def test_busy_message_clears_after_end_calls(controller: SetupController) -> None:
    controller.begin_download()
    controller.begin_measure()
    controller.begin_install()
    controller.end_download()
    controller.end_measure()
    controller.end_install()

    assert controller.busy_message is None


def test_measure_speed_reports_progress_and_the_saved_preset(
    controller: SetupController, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = BenchResult(300, [0.5, 0.5])

    def fake_measure(on_result=None):
        on_result("balanced", result)
        return "balanced", {"balanced": result}

    monkeypatch.setattr(sc, "measure_and_save", fake_measure)
    progress = []

    status = controller.measure_speed(progress.append)

    assert progress == ["Measuring speed: Balanced load 0.50…"]
    assert status == (
        "This computer keeps up with Balanced (load 0.50). Saved: the Voice changer now uses it.",
        "running",
    )


def test_measure_speed_reports_when_even_minimal_is_too_slow(
    controller: SetupController, monkeypatch: pytest.MonkeyPatch
) -> None:
    slow = BenchResult(1000, [1.3])
    monkeypatch.setattr(sc, "measure_and_save", lambda on_result=None: (None, {"minimal": slow}))

    message, kind = controller.measure_speed(lambda _: None)

    assert kind == "error"
    assert message.startswith("Even Minimal is too slow on this computer (load 1.30).")
    assert "'If the voice lags' in docs/USAGE.md." in message


def test_measure_speed_too_slow_without_results_omits_the_load(
    controller: SetupController, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sc, "measure_and_save", lambda on_result=None: (None, {}))

    message, _ = controller.measure_speed(lambda _: None)

    assert message.startswith("Even Minimal is too slow on this computer. ")


def test_measure_speed_returns_a_voice_clone_error_as_an_error_status(
    controller: SetupController, monkeypatch: pytest.MonkeyPatch
) -> None:
    def failing(on_result=None):
        raise VoiceCloneError("Add or train a voice first.")

    monkeypatch.setattr(sc, "measure_and_save", failing)

    assert controller.measure_speed(lambda _: None) == (
        "Error: Add or train a voice first.",
        "error",
    )


def test_measure_speed_returns_a_plain_exception_as_an_error_status(
    controller: SetupController, monkeypatch: pytest.MonkeyPatch
) -> None:
    def failing(on_result=None):
        raise RuntimeError("out of memory")

    monkeypatch.setattr(sc, "measure_and_save", failing)

    assert controller.measure_speed(lambda _: None) == ("Error: out of memory", "error")


@pytest.fixture
def bench_env(monkeypatch: pytest.MonkeyPatch, tmp_path):
    state = {"settings": Settings(), "present": True, "profiles": [PROFILE], "engines": []}

    class RecordingEngine(FakeEngine):
        precision = "fp32"

        def __init__(self, paths, device, cpu_threads, precision) -> None:
            super().__init__()
            self.args = (paths, device, cpu_threads, precision)
            state["engines"].append(self)

    monkeypatch.setattr(sc, "load_settings", lambda: state["settings"])
    monkeypatch.setattr(sc, "base_models_present", lambda path: state["present"])
    monkeypatch.setattr(sc, "models_dir", lambda: tmp_path / "models")
    monkeypatch.setattr(sc, "voices_dir", lambda: tmp_path / "voices")
    monkeypatch.setattr(sc, "discover_profiles", lambda path: state["profiles"])
    monkeypatch.setattr(sc, "base_model_paths", lambda path: "paths")
    monkeypatch.setattr(sc, "select_torch_device", lambda: "selected")
    monkeypatch.setattr(sc, "RvcEngine", RecordingEngine)
    return state


def test_prepare_bench_returns_a_session_for_the_named_voice(
    controller: SetupController, bench_env
) -> None:
    other = VoiceProfile("other", Path("o.pth"), None)
    bench_env["profiles"] = [other, PROFILE]

    session = controller.prepare_bench("me", True, None, None)

    assert isinstance(session, BenchSession)
    assert session.profile is PROFILE


def test_prepare_bench_reports_missing_models(controller: SetupController, bench_env) -> None:
    bench_env["present"] = False

    assert controller.prepare_bench(None, True, None, None) == MISSING_MODELS_MESSAGE
    assert MISSING_MODELS_MESSAGE == (
        "Base models are missing. Open the app and choose Check setup first."
    )


def test_prepare_bench_reports_a_voice_that_was_not_found(
    controller: SetupController, bench_env
) -> None:
    assert controller.prepare_bench("ghost", True, None, None) == "Voice not found: ghost"


def test_prepare_bench_does_not_fall_back_when_a_voice_was_asked_for(
    controller: SetupController, bench_env
) -> None:
    bench_env["settings"] = Settings(profile="me")

    assert controller.prepare_bench("ghost", True, None, None) == "Voice not found: ghost"


def test_prepare_bench_reports_no_voices_found(controller: SetupController, bench_env) -> None:
    bench_env["profiles"] = []

    assert controller.prepare_bench(None, True, None, None) == "No voices found."


def test_prepare_bench_falls_back_to_the_first_voice_without_a_wanted_name(
    controller: SetupController, bench_env
) -> None:
    other = VoiceProfile("other", Path("o.pth"), None)
    bench_env["profiles"] = [other, PROFILE]

    session = controller.prepare_bench(None, True, None, None)

    assert session.profile is other


def test_prepare_bench_uses_the_saved_profile_setting(
    controller: SetupController, bench_env
) -> None:
    other = VoiceProfile("other", Path("o.pth"), None)
    bench_env["profiles"] = [other, PROFILE]
    bench_env["settings"] = Settings(profile="me")

    session = controller.prepare_bench(None, True, None, None)

    assert session.profile is PROFILE


def test_prepare_bench_uses_the_cpu_when_asked(controller: SetupController, bench_env) -> None:
    session = controller.prepare_bench(None, True, None, None)

    assert session.device.type == "cpu"


def test_prepare_bench_selects_a_device_without_cpu(controller: SetupController, bench_env) -> None:
    session = controller.prepare_bench(None, False, None, None)

    assert session.device == "selected"


def test_prepare_bench_takes_threads_and_precision_from_settings(
    controller: SetupController, bench_env
) -> None:
    bench_env["settings"] = Settings(cpu_threads=4, precision="fp16")

    session = controller.prepare_bench(None, True, None, None)

    assert session.engine.args[2:] == (4, "fp16")


def test_prepare_bench_arguments_override_settings(controller: SetupController, bench_env) -> None:
    bench_env["settings"] = Settings(cpu_threads=4, precision="fp16")

    session = controller.prepare_bench(None, True, 0, "fp32")

    assert session.engine.args[2:] == (0, "fp32")


@pytest.fixture
def bench_run(monkeypatch: pytest.MonkeyPatch):
    results: dict[str, BenchResult] = {}
    order: list[str] = []

    def fake_run(engine, values, seconds):
        name = next(n for n, (_, v) in PERFORMANCE_PRESETS.items() if v is values)
        order.append(name)
        return results[name]

    monkeypatch.setattr(sc, "run_bench", fake_run)
    monkeypatch.setattr(sc, "apply_engine_options", lambda engine, values: None)
    return results, order


def run_bench(controller, presets, results, seconds=1.0, engine=None):
    session = BenchSession(engine or FakeEngine(), PROFILE, "cpu")
    reported = []
    recommended = controller.bench(
        session, presets, seconds, lambda name, result: reported.append((name, result))
    )
    return recommended, reported


def test_bench_reports_each_preset_in_order_and_recommends_the_heaviest_fitting(
    controller: SetupController, bench_run
) -> None:
    results, order = bench_run
    results.update(minimal=FAST, light=FAST, balanced=FAST, high=SLOW)
    presets = ["minimal", "light", "balanced", "high"]

    recommended, reported = run_bench(controller, presets, results)

    assert recommended == "balanced"
    assert [name for name, _ in reported] == presets
    assert order == presets


def test_bench_never_recommends_a_preset_above_balanced(
    controller: SetupController, bench_run
) -> None:
    results, _ = bench_run
    results.update(minimal=FAST, light=FAST, balanced=FAST, high=FAST, ultra=FAST)

    recommended, _ = run_bench(controller, list(PERFORMANCE_PRESETS), results)

    assert recommended == "balanced"


def test_bench_stops_recommending_after_a_preset_that_does_not_fit(
    controller: SetupController, bench_run
) -> None:
    results, _ = bench_run
    results.update(minimal=FAST, light=SLOW, balanced=FAST)

    recommended, _ = run_bench(controller, ["minimal", "light", "balanced"], results)

    assert recommended == "minimal"


def test_bench_recommends_nothing_when_the_first_preset_is_too_slow(
    controller: SetupController, bench_run
) -> None:
    results, _ = bench_run
    results.update(minimal=SLOW, light=FAST)

    recommended, _ = run_bench(controller, ["minimal", "light"], results)

    assert recommended is None


def test_bench_loads_the_profile_when_the_engine_is_not_loaded(
    controller: SetupController, bench_run
) -> None:
    results, _ = bench_run
    results.update(minimal=FAST)
    loaded = []

    class Unloaded(FakeEngine):
        def load(self, profile) -> None:
            loaded.append(profile)

    run_bench(controller, ["minimal"], results, engine=Unloaded(output_sample_rate=0))

    assert loaded == [PROFILE]


def test_bench_does_not_reload_an_engine_that_is_loaded(
    controller: SetupController, bench_run
) -> None:
    results, _ = bench_run
    results.update(minimal=FAST)
    loaded = []

    class Loaded(FakeEngine):
        def load(self, profile) -> None:
            loaded.append(profile)

    run_bench(controller, ["minimal"], results, engine=Loaded(output_sample_rate=40000))

    assert loaded == []


def test_bench_passes_the_seconds_to_run_bench(
    controller: SetupController, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen = []
    monkeypatch.setattr(sc, "apply_engine_options", lambda engine, values: None)

    def fake_run(engine, values, seconds):
        seen.append(seconds)
        return FAST

    monkeypatch.setattr(sc, "run_bench", fake_run)

    run_bench(controller, ["minimal"], {}, seconds=2.5)

    assert seen == [2.5]
