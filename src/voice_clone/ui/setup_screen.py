import logging
from collections import deque

from rich.text import Text
from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, ProgressBar, RichLog, Static

from voice_clone.engine import ensure_base_models
from voice_clone.errors import TrainingStoppedError, VoiceCloneError
from voice_clone.paths import models_dir, training_dir
from voice_clone.setup_check import (
    APPLIO_KEY,
    INFO,
    MISSING,
    MODELS_KEY,
    OK,
    TRAINING,
    VOICE_CHANGER,
    Check,
    evaluate,
    gather_facts,
)
from voice_clone.training import Applio, StreamingRunner

logger = logging.getLogger(__name__)

ICONS = {OK: "✓", MISSING: "✗", INFO: "i"}
BUSY_MESSAGE = "Wait until this is done, then go back."
APPLIO_STOPPED_MESSAGE = "Install stopped. Press 'Install Applio' to start again."
LOG_REFRESH_SECONDS = 0.2
MAX_LOG_LINES = 2000


class SetupScreen(Screen[None]):
    SUB_TITLE = "Check setup"
    BINDINGS = [Binding("escape", "back", "Back")]

    def __init__(self) -> None:
        super().__init__()
        self._busy = False
        self._applio_events: deque[tuple[str, str]] = deque()
        self._applio_runner: StreamingRunner | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="panel"):
            with Vertical(classes="page"):
                yield Static(
                    "What the app needs, and whether this computer has it.", classes="intro"
                )
                yield Vertical(id="checks")
                yield Button("Download base models", id="download-models", variant="primary")
                yield ProgressBar(total=1.0, show_eta=False, id="models-progress")
                yield Button("Install Applio (several GB)", id="install-applio", variant="primary")
                yield Button("Check again", id="check-again")
                yield Static("", id="setup-status")
                yield RichLog(max_lines=MAX_LOG_LINES, min_width=20, wrap=True, id="applio-log")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#models-progress", ProgressBar).display = False
        self.query_one("#download-models", Button).display = False
        self.query_one("#install-applio", Button).display = False
        self.query_one("#applio-log", RichLog).display = False
        self.set_interval(LOG_REFRESH_SECONDS, self._drain_applio_events)
        self._run_checks()

    def on_unmount(self) -> None:
        if self._applio_runner is not None:
            self._applio_runner.stop()

    def action_back(self) -> None:
        if self._busy:
            self.notify(BUSY_MESSAGE, severity="warning")
            return
        self.dismiss()

    @on(Button.Pressed, "#check-again")
    def _on_check_again(self) -> None:
        self._run_checks()

    @on(Button.Pressed, "#download-models")
    def _on_download(self) -> None:
        if self._busy:
            return
        self._set_busy(True)
        progress = self.query_one("#models-progress", ProgressBar)
        progress.update(progress=0)
        progress.display = True
        self._set_status("Downloading…")
        self._download()

    @on(Button.Pressed, "#install-applio")
    def _on_install_applio(self) -> None:
        if self._applio_runner is not None:
            self._applio_runner.stop()
            self.query_one("#install-applio", Button).disabled = True
            self._set_status("Stopping…")
            return
        if self._busy:
            return
        self._set_busy(True)
        button = self.query_one("#install-applio", Button)
        button.disabled = False
        button.label = "Stop install"
        button.variant = "error"
        log = self.query_one("#applio-log", RichLog)
        log.clear()
        log.display = True
        self._set_status("Installing Applio…")
        self._applio_events.clear()
        self._applio_runner = StreamingRunner(
            on_line=lambda line: self._applio_events.append(("line", line)),
            on_transient=lambda line: self._applio_events.append(("transient", line)),
        )
        self._install_applio(self._applio_runner)

    @work(thread=True, exclusive=True, group="applio-install")
    def _install_applio(self, runner: StreamingRunner) -> None:
        try:
            Applio(training_dir() / ".applio", runner=runner).ensure_installed(
                report=lambda message: self._applio_events.append(("step", message))
            )
        except TrainingStoppedError:
            self._applio_events.append(("stopped", APPLIO_STOPPED_MESSAGE))
        except VoiceCloneError as exc:
            self._applio_events.append(("failed", f"Error: {exc}"))
        except Exception as exc:
            logger.exception("Applio install failed")
            self._applio_events.append(("failed", f"Error: {exc or type(exc).__name__}"))
        else:
            self._applio_events.append(("done", ""))

    def _drain_applio_events(self) -> None:
        log = self.query_one("#applio-log", RichLog)
        while self._applio_events:
            kind, text = self._applio_events.popleft()
            if kind == "line":
                log.write(Text.from_ansi(text))
            elif kind == "transient":
                if text.strip() and self._applio_runner and not self._applio_runner.stopped:
                    self._set_status(Text.from_ansi(text.strip()).plain)
            elif kind == "step":
                log.write(Text(text, style="bold"))
                self._set_status(text)
            else:
                self._applio_finished(kind, text)

    def _applio_finished(self, kind: str, message: str) -> None:
        self._applio_runner = None
        button = self.query_one("#install-applio", Button)
        button.label = "Install Applio (several GB)"
        button.variant = "primary"
        self._set_busy(False)
        if kind == "done":
            self._run_checks()
            return
        self._set_status(message, "warning" if kind == "stopped" else "error")

    def _run_checks(self) -> None:
        if self._busy:
            return
        self._set_busy(True)
        self._set_status("Checking…")
        self._check()

    @work(thread=True, exclusive=True, group="setup-check")
    def _check(self) -> None:
        try:
            checks = evaluate(gather_facts())
        except Exception as exc:
            logger.exception("Setup check failed")
            self.app.call_from_thread(self._check_failed, str(exc) or type(exc).__name__)
            return
        self.app.call_from_thread(self._show_checks, checks)

    @work(thread=True, exclusive=True, group="models-download")
    def _download(self) -> None:
        try:
            ensure_base_models(models_dir(), self._report)
        except VoiceCloneError as exc:
            self.app.call_from_thread(self._download_finished, f"Error: {exc}")
        except Exception as exc:
            logger.exception("Base model download failed")
            self.app.call_from_thread(
                self._download_finished, f"Error: {exc or type(exc).__name__}"
            )
        else:
            self.app.call_from_thread(self._download_finished, None)

    def _report(self, message: str, fraction: float) -> None:
        self.app.call_from_thread(self._show_progress, message, fraction)

    def _show_progress(self, message: str, fraction: float) -> None:
        self.query_one("#models-progress", ProgressBar).update(progress=fraction)
        self._set_status(f"Downloading… {message}")

    def _download_finished(self, error: str | None) -> None:
        self.query_one("#models-progress", ProgressBar).display = False
        self._set_busy(False)
        if error is not None:
            self._set_status(error, "error")
            self.query_one("#download-models", Button).label = "Retry download"
            return
        self._run_checks()

    def _check_failed(self, message: str) -> None:
        self._set_busy(False)
        self._set_status(f"Error: could not check the setup: {message}", "error")

    def _show_checks(self, checks: list[Check]) -> None:
        self._set_busy(False)
        container = self.query_one("#checks", Vertical)
        container.remove_children()
        widgets = []
        for group in (VOICE_CHANGER, TRAINING):
            widgets.append(Label(group, classes="section-title"))
            for check in (c for c in checks if c.group == group):
                icon = ICONS.get(check.status, "!")
                parts = [Static(f"{icon} {check.name}: {check.detail}", classes="check-line")]
                if check.fix:
                    parts.append(Static(check.fix, classes="hint check-fix"))
                widgets.append(Vertical(*parts, classes=f"check-row {check.status}"))
        container.mount_all(widgets)

        models = next((c for c in checks if c.key == MODELS_KEY and c.status == MISSING), None)
        download = self.query_one("#download-models", Button)
        download.display = models is not None
        if models is not None:
            download.label = f"Download base models (about {models.download_mb} MB)"
        self.query_one("#install-applio", Button).display = any(c.key == APPLIO_KEY for c in checks)

        changer_problems = [c for c in checks if c.group == VOICE_CHANGER and c.status == MISSING]
        training_problems = [c for c in checks if c.group == TRAINING and c.status == MISSING]
        if changer_problems:
            names = ", ".join(c.name.lower() for c in changer_problems)
            self._set_status(f"The voice changer needs: {names}.", "error")
        elif training_problems:
            self._set_status(
                "The voice changer is ready. Training needs the items marked ✗.", "warning"
            )
        else:
            self._set_status("Everything is ready.", "running")

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.query_one("#download-models", Button).disabled = busy
        self.query_one("#install-applio", Button).disabled = busy
        self.query_one("#check-again", Button).disabled = busy

    def _set_status(self, message: str, kind: str = "") -> None:
        status = self.query_one("#setup-status", Static)
        status.update(message)
        status.set_classes(kind)
