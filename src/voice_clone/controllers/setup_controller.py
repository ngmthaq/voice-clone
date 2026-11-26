import logging
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

import torch

from voice_clone.domain.bench import (
    BenchResult,
    apply_engine_options,
    auto_presets,
    fits,
    measure_and_save,
    run_bench,
)
from voice_clone.domain.config import PERFORMANCE_PRESETS, load_settings
from voice_clone.domain.engine import (
    RvcEngine,
    base_models_present,
    ensure_base_models,
    select_torch_device,
)
from voice_clone.domain.engine.download import base_model_paths
from voice_clone.domain.errors import TrainingStoppedError, VoiceCloneError
from voice_clone.domain.paths import models_dir, training_dir, voices_dir
from voice_clone.domain.profiles import VoiceProfile, discover_profiles
from voice_clone.domain.setup_check import (
    APPLIO_KEY,
    MISSING,
    MODELS_KEY,
    TRAINING,
    VOICE_CHANGER,
    Check,
    Facts,
    evaluate,
    gather_facts,
)
from voice_clone.domain.training import Applio, StreamingRunner

logger = logging.getLogger(__name__)

Status = tuple[str, str]

APPLIO_STOPPED_MESSAGE = "Install stopped. Press 'Install Applio' to start again."
MISSING_MODELS_MESSAGE = "Base models are missing. Open the app and choose Check setup first."


@dataclass(frozen=True)
class SetupReport:
    checks: list[Check]
    facts: Facts | None
    error: str | None = None


@dataclass(frozen=True)
class BenchSession:
    engine: RvcEngine
    profile: VoiceProfile
    device: torch.device


class SetupController:
    def __init__(self) -> None:
        self._busy = False
        self._downloading = False
        self._measuring = False
        self._runner: StreamingRunner | None = None
        self._events: deque[tuple[str, str]] = deque()

    @property
    def busy(self) -> bool:
        return self._busy

    @property
    def installing(self) -> bool:
        return self._runner is not None

    @property
    def busy_message(self) -> str | None:
        if self._runner is not None:
            return "Applio is installing."
        if self._downloading:
            return "Base models are downloading."
        if self._measuring:
            return "The speed test is running."
        return None

    def set_busy(self, busy: bool) -> None:
        self._busy = busy

    def check(self) -> SetupReport:
        try:
            facts = gather_facts()
            return SetupReport(evaluate(facts), facts)
        except Exception as exc:
            logger.exception("Setup check failed")
            return SetupReport([], None, str(exc) or type(exc).__name__)

    def summary_status(self, report: SetupReport) -> Status:
        if report.error is not None:
            return (f"Error: could not check the setup: {report.error}", "error")
        changer_problems = _missing(report.checks, VOICE_CHANGER)
        training_problems = _missing(report.checks, TRAINING)
        if changer_problems:
            names = ", ".join(c.name.lower() for c in changer_problems)
            return (f"The voice changer needs: {names}.", "error")
        if training_problems:
            return ("The voice changer is ready. Training needs the items marked ✗.", "warning")
        return ("Everything is ready.", "running")

    def download_mb(self, report: SetupReport) -> int | None:
        models = _models_check(report.checks)
        return None if models is None else models.download_mb

    def shows_applio(self, report: SetupReport) -> bool:
        return any(c.key == APPLIO_KEY for c in report.checks)

    def can_measure(self, report: SetupReport) -> bool:
        return (
            report.facts is not None
            and _models_check(report.checks) is None
            and bool(report.facts.voices)
        )

    def begin_download(self) -> None:
        self._downloading = True

    def end_download(self) -> None:
        self._downloading = False

    def download(self, progress: Callable[[str, float], None]) -> str | None:
        try:
            ensure_base_models(models_dir(), progress)
        except VoiceCloneError as exc:
            return f"Error: {exc}"
        except Exception as exc:
            logger.exception("Base model download failed")
            return f"Error: {exc or type(exc).__name__}"
        return None

    def begin_install(self) -> None:
        self._events.clear()
        self._runner = StreamingRunner(
            on_line=lambda line: self._events.append(("line", line)),
            on_transient=lambda line: self._events.append(("transient", line)),
        )

    def install_applio(self) -> None:
        runner = self._runner
        try:
            Applio(training_dir() / ".applio", runner=runner).ensure_installed(
                report=lambda message: self._events.append(("step", message))
            )
        except TrainingStoppedError:
            self._events.append(("stopped", APPLIO_STOPPED_MESSAGE))
        except VoiceCloneError as exc:
            self._events.append(("failed", f"Error: {exc}"))
        except Exception as exc:
            logger.exception("Applio install failed")
            self._events.append(("failed", f"Error: {exc or type(exc).__name__}"))
        else:
            self._events.append(("done", ""))

    def install_applio_cli(self, report: Callable[[str], None]) -> None:
        Applio(training_dir() / ".applio").ensure_installed(report=report)

    def drain_events(self) -> list[tuple[str, str]]:
        drained: list[tuple[str, str]] = []
        while self._events:
            kind, text = self._events.popleft()
            if kind == "transient" and not (
                text.strip() and self._runner and not self._runner.stopped
            ):
                continue
            drained.append((kind, text))
        return drained

    def stop_install(self) -> None:
        if self._runner is not None:
            self._runner.stop()

    def end_install(self) -> None:
        self._runner = None

    def begin_measure(self) -> None:
        self._measuring = True

    def end_measure(self) -> None:
        self._measuring = False

    def measure_speed(self, on_progress: Callable[[str], None]) -> Status:
        try:
            best, results = measure_and_save(
                on_result=lambda name, result: on_progress(
                    f"Measuring speed: {_preset_title(name)} load {result.p95_load:.2f}…"
                )
            )
        except VoiceCloneError as exc:
            return (f"Error: {exc}", "error")
        except Exception as exc:
            logger.exception("Speed test failed")
            return (f"Error: {exc or type(exc).__name__}", "error")
        return _measure_message(best, results)

    def measure_speed_cli(self, if_needed: bool, report: Callable[[str], None]) -> bool:
        if if_needed and load_settings().speed_measured:
            return True
        if not base_models_present(models_dir()):
            report(f"Speed test skipped: {MISSING_MODELS_MESSAGE}")
            return False
        try:
            best, results = measure_and_save(
                on_result=lambda name, result: report(
                    f"Measuring speed: {_preset_title(name)} load {result.p95_load:.2f}"
                )
            )
        except VoiceCloneError as exc:
            report(f"Error: {exc}")
            return False
        text, _ = _measure_message(best, results)
        report(f"Warning: {text}" if best is None else text)
        return True

    def prepare_bench(
        self, voice: str | None, cpu: bool, threads: int | None, precision: str | None
    ) -> BenchSession | str:
        settings = load_settings()
        if not base_models_present(models_dir()):
            return MISSING_MODELS_MESSAGE
        profiles = discover_profiles(voices_dir())
        wanted = voice or settings.profile
        profile = next((p for p in profiles if p.name == wanted), None)
        if profile is None and voice is None and profiles:
            profile = profiles[0]
        if profile is None:
            return f"Voice not found: {wanted}" if wanted else "No voices found."
        device = torch.device("cpu") if cpu else select_torch_device()
        engine = RvcEngine(
            base_model_paths(models_dir()),
            device,
            cpu_threads=settings.cpu_threads if threads is None else threads,
            precision=precision or settings.precision,
        )
        return BenchSession(engine, profile, device)

    def bench(
        self,
        session: BenchSession,
        presets: list[str],
        seconds: float,
        on_result: Callable[[str, BenchResult], None],
    ) -> str | None:
        fitting: list[str] = []
        for name in presets:
            values = PERFORMANCE_PRESETS[name][1]
            apply_engine_options(session.engine, values)
            if session.engine.output_sample_rate == 0:
                session.engine.load(session.profile)
            result = run_bench(session.engine, values, seconds)
            if (
                fits(result)
                and len(fitting) == presets.index(name)
                and name in auto_presets(PERFORMANCE_PRESETS)
            ):
                fitting.append(name)
            on_result(name, result)
        return fitting[-1] if fitting else None


def _missing(checks: list[Check], group: str) -> list[Check]:
    return [c for c in checks if c.group == group and c.status == MISSING]


def _models_check(checks: list[Check]) -> Check | None:
    return next((c for c in checks if c.key == MODELS_KEY and c.status == MISSING), None)


def _preset_title(name: str) -> str:
    return PERFORMANCE_PRESETS[name][0].split(":")[0]


def _measure_message(best: str | None, results: dict[str, BenchResult]) -> Status:
    if best is None:
        lightest = next(iter(results.values()), None)
        load = f" (load {lightest.p95_load:.2f})" if lightest is not None else ""
        return (
            f"Even Minimal is too slow on this computer{load}. The voice will lag; see "
            "'If the voice lags' in docs/USAGE.md.",
            "error",
        )
    load = results[best].p95_load
    return (
        f"This computer keeps up with {_preset_title(best)} (load {load:.2f}). "
        "Saved: the Voice changer now uses it.",
        "running",
    )
