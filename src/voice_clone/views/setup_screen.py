from rich.text import Text
from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, ProgressBar, RichLog, Rule, Static

from voice_clone.controllers import SetupController
from voice_clone.controllers.setup_controller import SetupReport
from voice_clone.domain.setup_check import INFO, MISSING, OK, TRAINING, VOICE_CHANGER

ICONS = {OK: "✓", MISSING: "✗", INFO: "i"}
BUSY_MESSAGE = "Wait until this is done, then go back."
LOG_REFRESH_SECONDS = 0.2
MAX_LOG_LINES = 2000
MEASURE_HINT = (
    "Converts made-up speech with each Performance preset and picks the best one this "
    "computer keeps up with, up to Balanced. Takes up to a minute."
)


class SetupScreen(Screen[None]):
    SUB_TITLE = "Check setup"
    BINDINGS = [Binding("escape", "back", "Back")]

    def __init__(self) -> None:
        super().__init__()
        self._controller = SetupController()

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
                with Vertical(id="performance-section"):
                    yield Rule()
                    yield Label("Performance", classes="section-title")
                    yield Static(MEASURE_HINT, classes="hint")
                    yield Button("Measure speed", id="measure-speed")
                yield Static("", id="setup-status")
                yield RichLog(max_lines=MAX_LOG_LINES, min_width=20, wrap=True, id="applio-log")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#models-progress", ProgressBar).display = False
        self.query_one("#download-models", Button).display = False
        self.query_one("#install-applio", Button).display = False
        self.query_one("#performance-section", Vertical).display = False
        self.query_one("#applio-log", RichLog).display = False
        self.set_interval(LOG_REFRESH_SECONDS, self._drain_applio_events)
        self._run_checks()

    def on_unmount(self) -> None:
        self._controller.stop_install()

    @property
    def busy_message(self) -> str | None:
        return self._controller.busy_message

    def action_back(self) -> None:
        if self._controller.busy:
            self.notify(BUSY_MESSAGE, severity="warning")
            return
        self.dismiss()

    @on(Button.Pressed, "#check-again")
    def _on_check_again(self) -> None:
        self._run_checks()

    @on(Button.Pressed, "#download-models")
    def _on_download(self) -> None:
        if self._controller.busy:
            return
        self._set_busy(True)
        self._controller.begin_download()
        progress = self.query_one("#models-progress", ProgressBar)
        progress.update(progress=0)
        progress.display = True
        self._set_status("Downloading…")
        self._download()

    @on(Button.Pressed, "#measure-speed")
    def _on_measure_speed(self) -> None:
        if self._controller.busy:
            return
        self._set_busy(True)
        self._controller.begin_measure()
        self._set_status("Measuring speed: loading the voice…")
        self._measure_speed()

    @work(thread=True, exclusive=True, group="measure-speed")
    def _measure_speed(self) -> None:
        message, kind = self._controller.measure_speed(
            lambda text: self.app.call_from_thread(self._set_status, text)
        )
        self.app.call_from_thread(self._measure_finished, message, kind)

    def _measure_finished(self, message: str, kind: str) -> None:
        self._controller.end_measure()
        self._set_busy(False)
        self._set_status(message, kind)

    @on(Button.Pressed, "#install-applio")
    def _on_install_applio(self) -> None:
        if self._controller.installing:
            self._controller.stop_install()
            self.query_one("#install-applio", Button).disabled = True
            self._set_status("Stopping…")
            return
        if self._controller.busy:
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
        self._controller.begin_install()
        self._install_applio()

    @work(thread=True, exclusive=True, group="applio-install")
    def _install_applio(self) -> None:
        self._controller.install_applio()

    def _drain_applio_events(self) -> None:
        log = self.query_one("#applio-log", RichLog)
        for kind, text in self._controller.drain_events():
            if kind == "line":
                log.write(Text.from_ansi(text))
            elif kind == "transient":
                self._set_status(Text.from_ansi(text.strip()).plain)
            elif kind == "step":
                log.write(Text(text, style="bold"))
                self._set_status(text)
            else:
                self._applio_finished(kind, text)

    def _applio_finished(self, kind: str, message: str) -> None:
        self._controller.end_install()
        button = self.query_one("#install-applio", Button)
        button.label = "Install Applio (several GB)"
        button.variant = "primary"
        self._set_busy(False)
        if kind == "done":
            self._run_checks()
            return
        self._set_status(message, "warning" if kind == "stopped" else "error")

    def _run_checks(self) -> None:
        if self._controller.busy:
            return
        self._set_busy(True)
        self._set_status("Checking…")
        self._check()

    @work(thread=True, exclusive=True, group="setup-check")
    def _check(self) -> None:
        report = self._controller.check()
        self.app.call_from_thread(self._show_checks, report)

    @work(thread=True, exclusive=True, group="models-download")
    def _download(self) -> None:
        error = self._controller.download(
            lambda message, fraction: self.app.call_from_thread(
                self._show_progress, message, fraction
            )
        )
        self.app.call_from_thread(self._download_finished, error)

    def _show_progress(self, message: str, fraction: float) -> None:
        self.query_one("#models-progress", ProgressBar).update(progress=fraction)
        self._set_status(f"Downloading… {message}")

    def _download_finished(self, error: str | None) -> None:
        self.query_one("#models-progress", ProgressBar).display = False
        self._controller.end_download()
        self._set_busy(False)
        if error is not None:
            self._set_status(error, "error")
            self.query_one("#download-models", Button).label = "Retry download"
            return
        self._run_checks()

    def _show_checks(self, report: SetupReport) -> None:
        self._set_busy(False)
        if report.error is not None:
            self._set_status(*self._controller.summary_status(report))
            return
        container = self.query_one("#checks", Vertical)
        container.remove_children()
        widgets = []
        for group in (VOICE_CHANGER, TRAINING):
            widgets.append(Label(group, classes="section-title"))
            for check in (c for c in report.checks if c.group == group):
                icon = ICONS.get(check.status, "!")
                parts = [Static(f"{icon} {check.name}: {check.detail}", classes="check-line")]
                if check.fix:
                    parts.append(Static(check.fix, classes="hint check-fix"))
                widgets.append(Vertical(*parts, classes=f"check-row {check.status}"))
        container.mount_all(widgets)

        download_mb = self._controller.download_mb(report)
        download = self.query_one("#download-models", Button)
        download.display = download_mb is not None
        if download_mb is not None:
            download.label = f"Download base models (about {download_mb} MB)"
        self.query_one("#install-applio", Button).display = self._controller.shows_applio(report)
        self.query_one("#performance-section", Vertical).display = self._controller.can_measure(
            report
        )
        self._set_status(*self._controller.summary_status(report))

    def _set_busy(self, busy: bool) -> None:
        self._controller.set_busy(busy)
        self.query_one("#download-models", Button).disabled = busy
        self.query_one("#install-applio", Button).disabled = busy
        self.query_one("#check-again", Button).disabled = busy
        self.query_one("#measure-speed", Button).disabled = busy

    def _set_status(self, message: str, kind: str = "") -> None:
        status = self.query_one("#setup-status", Static)
        status.update(message)
        status.set_classes(kind)
