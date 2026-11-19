import shutil
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import soundfile as sf

from voice_clone.errors import TrainingError
from voice_clone.training.commands import CommandRunner, run_command

AUDIO_SUFFIXES = frozenset(
    {".m4a", ".wav", ".mp3", ".aac", ".caf", ".flac", ".ogg", ".aiff", ".aif", ".mp4"}
)
DATASET_SAMPLE_RATE = 48000
MIN_SECONDS = 60.0
RECOMMENDED_SECONDS = 600.0
# Cut low hum (e.g. 50/60 Hz mains) and even out loudness before Applio slices the audio.
AUDIO_FILTER = "highpass=f=70,loudnorm=I=-20:TP=-2:LRA=11"


@dataclass(frozen=True)
class DatasetInfo:
    directory: Path
    files: list[Path]
    total_seconds: float

    @property
    def is_short(self) -> bool:
        return self.total_seconds < RECOMMENDED_SECONDS


def collect_audio_files(inputs: Sequence[Path]) -> list[Path]:
    files: list[Path] = []
    for path in inputs:
        if path.is_dir():
            files.extend(sorted(p for p in path.rglob("*") if p.suffix.lower() in AUDIO_SUFFIXES))
        elif path.is_file():
            if path.suffix.lower() not in AUDIO_SUFFIXES:
                raise TrainingError(f"'{path.name}' is not a supported audio file.")
            files.append(path)
        else:
            raise TrainingError(f"'{path}' does not exist.")
    if not files:
        raise TrainingError("No audio files found in the given input.")
    return files


def prepare_dataset(
    inputs: Sequence[Path],
    out_dir: Path,
    ffmpeg: str = "ffmpeg",
    runner: CommandRunner = run_command,
) -> DatasetInfo:
    """Convert recordings to clean 48 kHz mono WAV files in out_dir (old files are removed)."""
    sources = collect_audio_files(inputs)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    outputs: list[Path] = []
    for number, source in enumerate(sources, start=1):
        target = out_dir / f"{number:03d}_{_safe_stem(source)}.wav"
        runner(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(source),
                "-vn",
                "-ac",
                "1",
                "-ar",
                str(DATASET_SAMPLE_RATE),
                "-af",
                AUDIO_FILTER,
                "-c:a",
                "pcm_s16le",
                str(target),
            ]
        )
        outputs.append(target)

    total = sum(_duration_seconds(path) for path in outputs)
    if total < MIN_SECONDS:
        raise TrainingError(
            f"Only {total:.0f} s of audio found. Record at least 1 minute (10+ minutes is best)."
        )
    return DatasetInfo(directory=out_dir, files=outputs, total_seconds=total)


def _duration_seconds(path: Path) -> float:
    try:
        info = sf.info(str(path))
    except RuntimeError as exc:
        raise TrainingError(f"Could not read converted audio '{path.name}': {exc}") from exc
    return info.frames / info.samplerate


def _safe_stem(path: Path) -> str:
    stem = "".join(c if c.isalnum() or c in "-_" else "_" for c in path.stem)
    return stem[:40] or "audio"
