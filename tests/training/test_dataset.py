from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from voice_clone.errors import TrainingError
from voice_clone.training.dataset import (
    DATASET_SAMPLE_RATE,
    collect_audio_files,
    prepare_dataset,
)


def _fake_ffmpeg(seconds: float):
    calls: list[list[str]] = []

    def runner(args: Sequence[str], cwd: Path | None = None, env=None) -> None:
        calls.append(list(args))
        samples = np.zeros(int(seconds * DATASET_SAMPLE_RATE), dtype=np.float32)
        sf.write(args[-1], samples, DATASET_SAMPLE_RATE)

    return runner, calls


def test_collect_finds_audio_in_folder_recursively(tmp_path: Path) -> None:
    (tmp_path / "sub").mkdir()
    (tmp_path / "a.m4a").touch()
    (tmp_path / "sub" / "b.WAV").touch()
    (tmp_path / "notes.txt").touch()

    files = collect_audio_files([tmp_path])

    assert [f.name for f in files] == ["a.m4a", "b.WAV"]


def test_collect_rejects_unsupported_file(tmp_path: Path) -> None:
    text = tmp_path / "notes.txt"
    text.touch()

    with pytest.raises(TrainingError, match="not a supported audio file"):
        collect_audio_files([text])


def test_collect_rejects_missing_path(tmp_path: Path) -> None:
    with pytest.raises(TrainingError, match="does not exist"):
        collect_audio_files([tmp_path / "missing.m4a"])


def test_collect_rejects_folder_without_audio(tmp_path: Path) -> None:
    with pytest.raises(TrainingError, match="No audio files"):
        collect_audio_files([tmp_path])


def test_prepare_converts_each_file_to_mono_48k_wav(tmp_path: Path) -> None:
    source = tmp_path / "Voice Memo 1.m4a"
    source.touch()
    runner, calls = _fake_ffmpeg(seconds=90)

    info = prepare_dataset([source], tmp_path / "dataset", runner=runner)

    assert [f.name for f in info.files] == ["001_Voice_Memo_1.wav"]
    assert calls[0][calls[0].index("-ac") + 1] == "1"
    assert calls[0][calls[0].index("-ar") + 1] == "48000"


def test_prepare_measures_total_duration(tmp_path: Path) -> None:
    for name in ("a.wav", "b.wav"):
        (tmp_path / name).touch()
    runner, _ = _fake_ffmpeg(seconds=45)

    info = prepare_dataset(
        [tmp_path / "a.wav", tmp_path / "b.wav"], tmp_path / "out", runner=runner
    )

    assert info.total_seconds == pytest.approx(90.0)
    assert info.is_short


def test_prepare_removes_old_dataset_files(tmp_path: Path) -> None:
    out = tmp_path / "dataset"
    out.mkdir()
    (out / "old.wav").touch()
    source = tmp_path / "a.wav"
    source.touch()
    runner, _ = _fake_ffmpeg(seconds=90)

    prepare_dataset([source], out, runner=runner)

    assert not (out / "old.wav").exists()


def test_prepare_rejects_less_than_one_minute(tmp_path: Path) -> None:
    source = tmp_path / "a.wav"
    source.touch()
    runner, _ = _fake_ffmpeg(seconds=20)

    with pytest.raises(TrainingError, match="at least 1 minute"):
        prepare_dataset([source], tmp_path / "out", runner=runner)
