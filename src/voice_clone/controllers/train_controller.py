import logging
import shlex
import sys
from collections import deque
from functools import partial
from pathlib import Path

from voice_clone.domain.config import load_settings, save_settings
from voice_clone.domain.errors import TrainingStoppedError, VoiceCloneError
from voice_clone.domain.paths import training_dir, voices_dir
from voice_clone.domain.training import (
    Applio,
    StreamingRunner,
    TrainOptions,
    epochs_done,
    prepare_dataset,
    train_voice,
    validate_options,
    voice_exists,
)

logger = logging.getLogger(__name__)

DEFAULT_OPTIONS = TrainOptions(name="my-voice", inputs=[])
UI_PAUSE_HINT = "Press Stop training to pause; Start training again continues from a checkpoint."
STOPPED_MESSAGE = (
    "Stopped. Press Start training with the same voice name to continue from the last checkpoint."
)


class TrainController:
    def __init__(self) -> None:
        self._events: deque[tuple[str, str]] = deque()
        self._runner: StreamingRunner | None = None
        self._running = False
        self._stopping = False
        self._target_epochs = DEFAULT_OPTIONS.epochs
        self._voice_name = DEFAULT_OPTIONS.name
        self._settings = load_settings()

    @property
    def running(self) -> bool:
        return self._running

    @property
    def busy_message(self) -> str | None:
        return "Training is running." if self._running else None

    @property
    def stopping(self) -> bool:
        return self._stopping

    @property
    def target_epochs(self) -> int:
        return self._target_epochs

    @property
    def default_name(self) -> str:
        return self._settings.train_name

    @property
    def default_epochs(self) -> int:
        return self._settings.train_epochs

    @property
    def default_batch_size(self) -> int:
        return self._settings.train_batch_size

    @property
    def default_save_every(self) -> int:
        return self._settings.train_save_every

    def default_sample_rate(self, allowed: tuple[int, ...]) -> int:
        rate = self._settings.train_sample_rate
        return rate if rate in allowed else DEFAULT_OPTIONS.sample_rate

    def check_options(
        self,
        inputs_text: str,
        name: str,
        epochs_text: str,
        sample_rate: int,
        batch_size_text: str,
        save_every_text: str,
        restart: bool,
        force: bool,
    ) -> TrainOptions:
        inputs = _parse_paths(inputs_text)
        if not inputs:
            raise VoiceCloneError("Add at least one recording (an audio file or a folder).")
        missing = next((path for path in inputs if not path.exists()), None)
        if missing is not None:
            raise VoiceCloneError(f"'{missing}' does not exist.")
        name = name.strip()
        options = TrainOptions(
            name=name,
            inputs=inputs,
            epochs=_read_int(epochs_text, "Epochs"),
            sample_rate=sample_rate,
            batch_size=_read_int(batch_size_text, "Batch size"),
            save_every=_read_int(save_every_text, "Save every"),
            restart=restart,
            force=force,
        )
        validate_options(options)
        self._save_options(options)
        if voice_exists(voices_dir(), name) and not options.force:
            raise VoiceCloneError(
                f"A voice named '{name}' already exists. Tick 'Replace an existing voice' "
                "or pick another name."
            )
        return options

    def start(self, options: TrainOptions) -> None:
        self._running = True
        self._stopping = False
        self._target_epochs = options.epochs
        self._voice_name = options.name
        self._events.clear()
        self._runner = StreamingRunner(
            on_line=lambda line: self._events.append(("line", line)),
            on_transient=lambda line: self._events.append(("transient", line)),
        )

    def train(self, options: TrainOptions) -> None:
        runner = self._runner
        root = training_dir()
        try:
            train_voice(
                options,
                Applio(root / ".applio", runner=runner),
                root,
                voices_dir(),
                report=lambda message: self._events.append(("step", message)),
                prepare=partial(prepare_dataset, runner=runner),
                pause_hint=UI_PAUSE_HINT,
            )
        except TrainingStoppedError:
            self._events.append(("failed", STOPPED_MESSAGE))
        except VoiceCloneError as exc:
            self._events.append(("failed", f"Error: {exc}"))
        except Exception as exc:
            logger.exception("Training failed")
            self._events.append(("failed", f"Error: {exc or type(exc).__name__}"))
        else:
            self._events.append(("done", options.name))

    def train_cli(self, options: TrainOptions) -> None:
        root = training_dir()
        train_voice(options, Applio(root / ".applio"), root, voices_dir())

    def drain_events(self) -> list[tuple[str, str]]:
        drained: list[tuple[str, str]] = []
        while self._events:
            drained.append(self._events.popleft())
        return drained

    def epoch_progress(self, line: str) -> float | None:
        done = epochs_done(line) if self._voice_name in line else None
        if done is None:
            return None
        return min(done, float(self._target_epochs))

    def stop(self) -> bool:
        if self._runner is None or self._stopping:
            return False
        self._stopping = True
        self._runner.stop()
        return True

    def stop_on_unmount(self) -> None:
        if self._runner is not None:
            self._runner.stop()

    def finish(self) -> None:
        self._running = False
        self._stopping = False
        self._runner = None

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


def _read_int(text: str, label: str) -> int:
    try:
        return int(text)
    except ValueError:
        raise VoiceCloneError(f"{label} must be a whole number.") from None
