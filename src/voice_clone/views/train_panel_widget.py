import logging
import shlex
import sys
from collections import deque
from dataclasses import dataclass
from functools import partial
from pathlib import Path

from rich.text import Text
from textual import on, work
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.validation import Number, Regex
from textual.widgets import Button, Checkbox, Input, ProgressBar, RichLog, Select, Static

from voice_clone.domain.config import load_settings, save_settings
from voice_clone.domain.errors import TrainingStoppedError, VoiceCloneError
from voice_clone.domain.paths import training_dir, voices_dir
from voice_clone.domain.training import (
    MAX_BATCH_SIZE,
    MAX_EPOCHS,
    NAME_PATTERN,
    SAMPLE_RATES,
    Applio,
    StreamingRunner,
    TrainOptions,
    epochs_done,
    prepare_dataset,
    train_voice,
    validate_options,
    voice_exists,
)
from voice_clone.views.fields import labeled_field

logger = logging.getLogger(__name__)

REFRESH_SECONDS = 0.2
MAX_LOG_LINES = 2000
LOG_MIN_WIDTH = 20
DEFAULT_OPTIONS = TrainOptions(name="my-voice", inputs=[])
UI_PAUSE_HINT = "Press Stop training to pause; Start training again continues from a checkpoint."
STOPPED_MESSAGE = (
    "Stopped. Press Start training with the same voice name to continue from the last checkpoint."
)


@dataclass(frozen=True)
class _Event:
    kind: str
    text: str


class TrainPanelWidget(Vertical):
    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._events: deque[_Event] = deque()
        self._runner: StreamingRunner | None = None
        self._is_training = False
        self._stopping = False
        self._target_epochs = DEFAULT_OPTIONS.epochs
        self._voice_name = DEFAULT_OPTIONS.name
        self._settings = load_settings()

    @property
    def running(self) -> bool:
        return self._is_training

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
                self._settings.train_name,
                validators=[Regex(NAME_PATTERN.pattern)],
                id="train-name",
            ),
            "Letters, numbers, - and _. Use the same name to continue a paused run.",
        )
        yield from labeled_field(
            "Epochs",
            Input(
                str(self._settings.train_epochs),
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
                str(self._settings.train_batch_size),
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
                str(self._settings.train_save_every),
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
                value=(
                    self._settings.train_sample_rate
                    if self._settings.train_sample_rate in SAMPLE_RATES
                    else DEFAULT_OPTIONS.sample_rate
                ),
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
        if self._runner is not None:
            self._runner.stop()

    @on(Button.Pressed, "#train-button")
    def _on_button(self) -> None:
        if self._is_training:
            self._stop()
        else:
            self._start()

    def _start(self) -> None:
        try:
            options = self._read_options()
        except VoiceCloneError as exc:
            self._set_status(f"Error: {exc}", "error")
            return
        self._is_training = True
        self._stopping = False
        self._target_epochs = options.epochs
        self._voice_name = options.name
        self._events.clear()
        log = self.query_one("#train-log", RichLog)
        log.clear()
        log.display = True
        progress = self.query_one("#train-progress", ProgressBar)
        progress.update(total=None, progress=0)
        progress.display = True
        self._set_status("Starting…")
        self._refresh_controls()
        self._runner = StreamingRunner(
            on_line=lambda line: self._events.append(_Event("line", line)),
            on_transient=lambda line: self._events.append(_Event("transient", line)),
        )
        self._train(options, self._runner)

    def _stop(self) -> None:
        if self._runner is None or self._stopping:
            return
        self._stopping = True
        self._set_status("Stopping…")
        self._refresh_controls()
        self._runner.stop()

    def _read_options(self) -> TrainOptions:
        inputs = _parse_paths(self.query_one("#train-inputs", Input).value)
        if not inputs:
            raise VoiceCloneError("Add at least one recording (an audio file or a folder).")
        missing = next((path for path in inputs if not path.exists()), None)
        if missing is not None:
            raise VoiceCloneError(f"'{missing}' does not exist.")
        name = self.query_one("#train-name", Input).value.strip()
        options = TrainOptions(
            name=name,
            inputs=inputs,
            epochs=_read_int(self.query_one("#train-epochs", Input), "Epochs"),
            sample_rate=int(self.query_one("#train-sample-rate", Select).value),  # type: ignore[arg-type]
            batch_size=_read_int(self.query_one("#train-batch-size", Input), "Batch size"),
            save_every=_read_int(self.query_one("#train-save-every", Input), "Save every"),
            restart=self.query_one("#train-restart", Checkbox).value,
            force=self.query_one("#train-force", Checkbox).value,
        )
        validate_options(options)
        self._save_options(options)
        if voice_exists(voices_dir(), name) and not options.force:
            raise VoiceCloneError(
                f"A voice named '{name}' already exists. Tick 'Replace an existing voice' "
                "or pick another name."
            )
        return options

    def _save_options(self, options: TrainOptions) -> None:
        settings = load_settings().model_copy(
            update=dict(
                train_name=options.name,
                train_epochs=options.epochs,
                train_batch_size=options.batch_size,
                train_sample_rate=options.sample_rate,
                train_save_every=options.save_every,
            )
        )
        try:
            save_settings(settings)
        except OSError:
            logger.warning("Could not save training settings", exc_info=True)

    @work(thread=True, exclusive=True, group="train")
    def _train(self, options: TrainOptions, runner: StreamingRunner) -> None:
        root = training_dir()
        try:
            train_voice(
                options,
                Applio(root / ".applio", runner=runner),
                root,
                voices_dir(),
                report=lambda message: self._events.append(_Event("step", message)),
                prepare=partial(prepare_dataset, runner=runner),
                pause_hint=UI_PAUSE_HINT,
            )
        except TrainingStoppedError:
            self._events.append(_Event("failed", STOPPED_MESSAGE))
        except VoiceCloneError as exc:
            self._events.append(_Event("failed", f"Error: {exc}"))
        except Exception as exc:
            logger.exception("Training failed")
            self._events.append(_Event("failed", f"Error: {exc or type(exc).__name__}"))
        else:
            self._events.append(_Event("done", options.name))

    def _drain_events(self) -> None:
        log = self.query_one("#train-log", RichLog)
        while self._events:
            event = self._events.popleft()
            if event.kind == "line":
                log.write(Text.from_ansi(event.text))
                self._show_epoch_progress(event.text)
            elif event.kind == "transient":
                if event.text.strip() and not self._stopping:
                    self._set_status(Text.from_ansi(event.text.strip()).plain)
            elif event.kind == "step":
                log.write(Text(event.text, style="bold"))
                if not self._stopping:
                    self._set_status(event.text.strip())
            elif event.kind == "done":
                self._finish(
                    f"Done. Voice '{event.text}' is ready. Pick it in the Voice changer.",
                    "running",
                    event.text,
                )
            else:
                self._finish(event.text, "warning" if event.text == STOPPED_MESSAGE else "error")

    def _show_epoch_progress(self, line: str) -> None:
        done = epochs_done(line) if self._voice_name in line else None
        if done is None:
            return
        done = min(done, float(self._target_epochs))
        self.query_one("#train-progress", ProgressBar).update(
            total=self._target_epochs, progress=done
        )
        if not self._stopping:
            self._set_status(f"Training: epoch {int(done)} of {self._target_epochs}")

    def _finish(self, message: str, kind: str, voice_name: str | None = None) -> None:
        self._is_training = False
        self._stopping = False
        self._runner = None
        progress = self.query_one("#train-progress", ProgressBar)
        if voice_name is not None:
            progress.update(total=self._target_epochs, progress=self._target_epochs)
        else:
            progress.display = False
        self._set_status(message, kind)
        self._refresh_controls()

    def _refresh_controls(self) -> None:
        for widget in self.query("Input, Select, Checkbox"):
            widget.disabled = self._is_training
        button = self.query_one("#train-button", Button)
        button.disabled = self._stopping
        if self._is_training:
            button.label = "Stop training"
            button.variant = "error"
        else:
            button.label = "Start training"
            button.variant = "primary"

    def _set_status(self, message: str, kind: str = "") -> None:
        status = self.query_one("#train-status", Static)
        status.update(message)
        status.set_classes(kind)


def _parse_paths(text: str, platform: str = sys.platform) -> list[Path]:
    """Paths typed, pasted or dragged in. A dragged path is quoted or uses '\\ ' for spaces."""
    text = text.strip()
    if not text:
        return []
    whole = Path(text.strip("'\"")).expanduser()
    if whole.exists():
        return [whole]
    try:
        parts = shlex.split(text, posix=platform != "win32")
    except ValueError as exc:
        raise VoiceCloneError(f"Could not read the recording paths: {exc}.") from exc
    return [Path(part.strip("'\"")).expanduser() for part in parts if part.strip("'\"")]


def _read_int(field: Input, label: str) -> int:
    try:
        return int(field.value)
    except ValueError:
        raise VoiceCloneError(f"{label} must be a whole number.") from None
