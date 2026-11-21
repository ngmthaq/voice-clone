import logging
import os
import re
import shutil
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from voice_clone.errors import TrainingError
from voice_clone.training.applio import Applio
from voice_clone.training.commands import require_tool
from voice_clone.training.dataset import DatasetInfo, prepare_dataset

logger = logging.getLogger(__name__)

NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
SAMPLE_RATES = (32000, 40000, 48000)
MAX_EPOCHS = 10000
MAX_BATCH_SIZE = 50
WEIGHTS_PATTERN = re.compile(r"_(\d+)e_(\d+)s\.pth$")
# Applio prints "<name> | epoch=5 | step=120 | batch=3/24" during an epoch,
# and "<name> | epoch=5 | step=144 | time=…" when it ends.
EPOCH_PATTERN = re.compile(r"\| epoch=(\d+) \| step=\d+(?: \| batch=(\d+)/(\d+))?")
CLI_PAUSE_HINT = "Press Ctrl+C to pause; run the same command again to continue."

Reporter = Callable[[str], None]


@dataclass(frozen=True)
class TrainOptions:
    name: str
    inputs: Sequence[Path]
    epochs: int = 200
    sample_rate: int = 40000
    batch_size: int = 8
    save_every: int = 10
    restart: bool = False
    force: bool = False


def train_voice(
    options: TrainOptions,
    applio: Applio,
    training_root: Path,
    voices_root: Path,
    report: Reporter = logger.info,
    prepare: Callable[..., DatasetInfo] = prepare_dataset,
    pause_hint: str = CLI_PAUSE_HINT,
) -> Path:
    """Prepare recordings, train with Applio, and install the result as a voice profile."""
    validate_options(options)
    voice_dir = voices_root / options.name
    if voice_exists(voices_root, options.name) and not options.force:
        raise TrainingError(
            f"A voice named '{options.name}' already exists. Use --force to replace it, "
            "or pick another --name."
        )

    report("Step 1/4: Preparing your recordings…")
    dataset = prepare(
        options.inputs, training_root / options.name / "dataset", ffmpeg=require_tool("ffmpeg")
    )
    report(f"  {len(dataset.files)} file(s), {dataset.total_seconds / 60:.1f} minutes of audio.")
    if dataset.is_short:
        report("  Note: less than 10 minutes of audio. The voice will sound better with more.")

    report("Step 2/4: Setting up Applio (only slow the first time)…")
    applio.ensure_installed()

    model_dir = applio.model_dir(options.name)
    if options.restart and model_dir.exists():
        report("  --restart: removing the previous training run.")
        shutil.rmtree(model_dir)
    cpu_cores = max(1, (os.cpu_count() or 2) - 1)
    if _has_checkpoint(model_dir):
        report("Step 3/4: Found an earlier run. Continuing from its last checkpoint.")
    else:
        if model_dir.exists():
            shutil.rmtree(model_dir)
        report("Step 3/4: Slicing audio and extracting voice features…")
        applio.preprocess(options.name, dataset.directory, options.sample_rate, cpu_cores)
        applio.extract(options.name, options.sample_rate, cpu_cores)

    report(f"Step 4/4: Training for {options.epochs} epochs. This can take hours. {pause_hint}")
    applio.train(
        options.name, options.epochs, options.sample_rate, options.batch_size, options.save_every
    )

    installed = import_trained_model(model_dir, options.name, voice_dir)
    report(f"Done. Voice '{options.name}' is ready in {voice_dir} ({installed.name}).")
    return voice_dir


def epochs_done(line: str) -> float | None:
    """How many epochs are finished, read from one line of Applio output (None if not known)."""
    match = EPOCH_PATTERN.search(line)
    if match is None:
        return None
    epoch = int(match.group(1))
    if match.group(2) is None:
        return float(epoch)
    batch, batches = int(match.group(2)), int(match.group(3))
    return epoch - 1 + batch / batches if batches else float(epoch - 1)


def validate_options(options: TrainOptions) -> None:
    if not NAME_PATTERN.match(options.name):
        raise TrainingError(
            "Voice name may only use letters, numbers, '-' and '_' (max 64 characters)."
        )
    if options.sample_rate not in SAMPLE_RATES:
        raise TrainingError(f"Sample rate must be one of {', '.join(map(str, SAMPLE_RATES))}.")
    if not 1 <= options.epochs <= MAX_EPOCHS:
        raise TrainingError(f"Epochs must be between 1 and {MAX_EPOCHS}.")
    if not 1 <= options.batch_size <= MAX_BATCH_SIZE:
        raise TrainingError(f"Batch size must be between 1 and {MAX_BATCH_SIZE}.")
    if not 1 <= options.save_every <= 100:
        raise TrainingError("--save-every must be between 1 and 100.")


def voice_exists(voices_root: Path, name: str) -> bool:
    return any((voices_root / name).glob("*.pth"))


def find_latest_weights(model_dir: Path, name: str) -> Path:
    candidates: list[tuple[int, int, Path]] = []
    for path in model_dir.glob(f"{name}_*e_*s.pth"):
        match = WEIGHTS_PATTERN.search(path.name)
        if match:
            candidates.append((int(match.group(1)), int(match.group(2)), path))
    if not candidates:
        raise TrainingError(
            "Training finished without a model file. See the Applio output above for the reason."
        )
    return max(candidates)[2]


def import_trained_model(model_dir: Path, name: str, voice_dir: Path) -> Path:
    weights = find_latest_weights(model_dir, name)
    if voice_dir.exists():
        shutil.rmtree(voice_dir)
    voice_dir.mkdir(parents=True)
    target = voice_dir / f"{name}.pth"
    shutil.copy2(weights, target)
    index = model_dir / f"{name}.index"
    if index.is_file():
        shutil.copy2(index, voice_dir / index.name)
    else:
        logger.warning("No index file found in %s; the voice will work without it", model_dir)
    return target


def _has_checkpoint(model_dir: Path) -> bool:
    return any(model_dir.glob("G_*.pth")) and any(model_dir.glob("D_*.pth"))
