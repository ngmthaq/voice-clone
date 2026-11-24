from rich.text import Text
from textual import on, work
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.validation import Number, Regex
from textual.widgets import Button, Checkbox, Input, ProgressBar, RichLog, Select, Static

from voice_clone.controllers.train_controller import (
    DEFAULT_OPTIONS,
    STOPPED_MESSAGE,
    TrainController,
)
from voice_clone.domain.errors import VoiceCloneError
from voice_clone.domain.training import (
    MAX_BATCH_SIZE,
    MAX_EPOCHS,
    NAME_PATTERN,
    SAMPLE_RATES,
    TrainOptions,
)
from voice_clone.views.fields import labeled_field

REFRESH_SECONDS = 0.2
MAX_LOG_LINES = 2000
LOG_MIN_WIDTH = 20


class TrainPanelWidget(Vertical):
    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._controller = TrainController()

    @property
    def running(self) -> bool:
        return self._controller.running

    def compose(self) -> ComposeResult:
        yield from labeled_field(
            "Recordings",
            Input(placeholder="Drag audio files or a folder here", id="train-inputs"),
            "m4a, wav, mp3, … 10–30 minutes in total is best. Separate several paths with "
            "spaces; put quotes around a path that has spaces in it.",
        )
        yield from labeled_field(
            "Voice name",
            Input(
                self._controller.default_name,
                validators=[Regex(NAME_PATTERN.pattern)],
                id="train-name",
            ),
            "Letters, numbers, - and _. Use the same name to continue a paused run.",
        )
        yield from labeled_field(
            "Epochs",
            Input(
                str(self._controller.default_epochs),
                placeholder=f"default {DEFAULT_OPTIONS.epochs}",
                type="integer",
                validators=[Number(minimum=1, maximum=MAX_EPOCHS)],
                id="train-epochs",
            ),
            "More = closer match, but too many can sound robotic",
        )
        yield from labeled_field(
            "Batch size",
            Input(
                str(self._controller.default_batch_size),
                placeholder=f"default {DEFAULT_OPTIONS.batch_size}",
                type="integer",
                validators=[Number(minimum=1, maximum=MAX_BATCH_SIZE)],
                id="train-batch-size",
            ),
            "Lower it to 4 if training runs out of memory",
        )
        yield from labeled_field(
            "Save every (epochs)",
            Input(
                str(self._controller.default_save_every),
                placeholder=f"default {DEFAULT_OPTIONS.save_every}",
                type="integer",
                validators=[Number(minimum=1, maximum=100)],
                id="train-save-every",
            ),
            "How often a checkpoint is saved. A stopped run continues from the last one",
        )
        yield from labeled_field(
            "Sample rate",
            Select[int](
                [(f"{rate} Hz", rate) for rate in SAMPLE_RATES],
                value=self._controller.default_sample_rate(SAMPLE_RATES),
                allow_blank=False,
                id="train-sample-rate",
            ),
        )
        yield Checkbox("Start over (throw away an earlier run with this name)", id="train-restart")
        yield Checkbox("Replace an existing voice with this name", id="train-force")
        yield Button("Start training", id="train-button", variant="primary")
        yield ProgressBar(total=None, show_eta=False, id="train-progress")
        yield Static("", id="train-status")
        yield RichLog(
            max_lines=MAX_LOG_LINES,
            min_width=LOG_MIN_WIDTH,
            wrap=True,
            id="train-log",
        )

    def on_mount(self) -> None:
        self.query_one("#train-progress", ProgressBar).display = False
        self.query_one("#train-log", RichLog).display = False
        self.set_interval(REFRESH_SECONDS, self._drain_events)
        self._refresh_controls()

    def on_unmount(self) -> None:
        self._controller.stop_on_unmount()

    @on(Button.Pressed, "#train-button")
    def _on_button(self) -> None:
        if self._controller.running:
            self._stop()
        else:
            self._start()

    def _start(self) -> None:
        try:
            options = self._read_options()
        except VoiceCloneError as exc:
            self._set_status(f"Error: {exc}", "error")
            return
        self._controller.start(options)
        log = self.query_one("#train-log", RichLog)
        log.clear()
        log.display = True
        progress = self.query_one("#train-progress", ProgressBar)
        progress.update(total=None, progress=0)
        progress.display = True
        self._set_status("Starting…")
        self._refresh_controls()
        self._train(options)

    def _stop(self) -> None:
        if not self._controller.stop():
            return
        self._set_status("Stopping…")
        self._refresh_controls()

    def _read_options(self) -> TrainOptions:
        return self._controller.check_options(
            self.query_one("#train-inputs", Input).value,
            self.query_one("#train-name", Input).value,
            self.query_one("#train-epochs", Input).value,
            int(self.query_one("#train-sample-rate", Select).value),  # type: ignore[arg-type]
            self.query_one("#train-batch-size", Input).value,
            self.query_one("#train-save-every", Input).value,
            self.query_one("#train-restart", Checkbox).value,
            self.query_one("#train-force", Checkbox).value,
        )

    @work(thread=True, exclusive=True, group="train")
    def _train(self, options: TrainOptions) -> None:
        self._controller.train(options)

    def _drain_events(self) -> None:
        log = self.query_one("#train-log", RichLog)
        for kind, text in self._controller.drain_events():
            if kind == "line":
                log.write(Text.from_ansi(text))
                self._show_epoch_progress(text)
            elif kind == "transient":
                if text.strip() and not self._controller.stopping:
                    self._set_status(Text.from_ansi(text.strip()).plain)
            elif kind == "step":
                log.write(Text(text, style="bold"))
                if not self._controller.stopping:
                    self._set_status(text.strip())
            elif kind == "done":
                self._finish(
                    f"Done. Voice '{text}' is ready. Pick it in the Voice changer.",
                    "running",
                    text,
                )
            else:
                self._finish(text, "warning" if text == STOPPED_MESSAGE else "error")

    def _show_epoch_progress(self, line: str) -> None:
        done = self._controller.epoch_progress(line)
        if done is None:
            return
        target = self._controller.target_epochs
        self.query_one("#train-progress", ProgressBar).update(total=target, progress=done)
        if not self._controller.stopping:
            self._set_status(f"Training: epoch {int(done)} of {target}")

    def _finish(self, message: str, kind: str, voice_name: str | None = None) -> None:
        self._controller.finish()
        progress = self.query_one("#train-progress", ProgressBar)
        if voice_name is not None:
            target = self._controller.target_epochs
            progress.update(total=target, progress=target)
        else:
            progress.display = False
        self._set_status(message, kind)
        self._refresh_controls()

    def _refresh_controls(self) -> None:
        for widget in self.query("Input, Select, Checkbox"):
            widget.disabled = self._controller.running
        button = self.query_one("#train-button", Button)
        button.disabled = self._controller.stopping
        if self._controller.running:
            button.label = "Stop training"
            button.variant = "error"
        else:
            button.label = "Start training"
            button.variant = "primary"

    def _set_status(self, message: str, kind: str = "") -> None:
        status = self.query_one("#train-status", Static)
        status.update(message)
        status.set_classes(kind)
