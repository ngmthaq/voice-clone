import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from voice_clone.errors import VoiceCloneError
from voice_clone.logging_setup import setup_logging
from voice_clone.paths import training_dir, voices_dir

logger = logging.getLogger(__name__)

EXIT_ERROR = 1
EXIT_INTERRUPTED = 130


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    setup_logging()
    if args.command == "train":
        return _run_train(args)
    from voice_clone.app import VoiceCloneApp

    VoiceCloneApp().run()
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="voice-clone",
        description="Real-time voice conversion. Run with no command for the TUI.",
    )
    commands = parser.add_subparsers(dest="command")
    train = commands.add_parser(
        "train",
        help="Train a voice model from your recordings (runs locally with Applio).",
        description="Train an RVC v2 voice from your recordings and add it to voices/<name>/.",
    )
    train.add_argument(
        "inputs", nargs="+", type=Path, help="Audio files or folders (m4a, wav, mp3, …)."
    )
    train.add_argument("--name", default="my-voice", help="Voice name (default: my-voice).")
    train.add_argument("--epochs", type=int, default=200, help="Training epochs (default: 200).")
    train.add_argument(
        "--sample-rate",
        type=int,
        default=40000,
        choices=(32000, 40000, 48000),
        help="Model sample rate (default: 40000).",
    )
    train.add_argument(
        "--batch-size",
        type=int,
        default=8,
        help="Lower it (e.g. 4) if training runs out of memory (default: 8).",
    )
    train.add_argument(
        "--save-every", type=int, default=10, help="Save a checkpoint every N epochs (default: 10)."
    )
    train.add_argument(
        "--restart",
        action="store_true",
        help="Throw away an earlier run with this name and start over.",
    )
    train.add_argument(
        "--force", action="store_true", help="Replace an existing voice with the same name."
    )
    return parser


def _run_train(args: argparse.Namespace) -> int:
    from voice_clone.training import Applio, TrainOptions, train_voice

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter("%(message)s"))
    console.setLevel(logging.INFO)
    logging.getLogger().addHandler(console)

    options = TrainOptions(
        name=args.name,
        inputs=args.inputs,
        epochs=args.epochs,
        sample_rate=args.sample_rate,
        batch_size=args.batch_size,
        save_every=args.save_every,
        restart=args.restart,
        force=args.force,
    )
    root = training_dir()
    try:
        train_voice(options, Applio(root / ".applio"), root, voices_dir())
    except VoiceCloneError as exc:
        logger.error("Error: %s", exc)
        return EXIT_ERROR
    except KeyboardInterrupt:
        logger.info("Stopped. Run the same command again to continue from the last checkpoint.")
        return EXIT_INTERRUPTED
    return 0
