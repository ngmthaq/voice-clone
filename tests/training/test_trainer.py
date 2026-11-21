from pathlib import Path

import pytest

from voice_clone.errors import TrainingError
from voice_clone.training import trainer as trainer_module
from voice_clone.training.dataset import DatasetInfo
from voice_clone.training.trainer import (
    TrainOptions,
    epochs_done,
    find_latest_weights,
    import_trained_model,
    train_voice,
)


class FakeApplio:
    def __init__(self, root: Path) -> None:
        self.logs_dir = root / "logs"
        self.steps: list[str] = []

    def model_dir(self, name: str) -> Path:
        return self.logs_dir / name

    def ensure_installed(self) -> None:
        self.steps.append("install")

    def preprocess(self, name: str, *_: object) -> None:
        self.steps.append("preprocess")
        self.model_dir(name).mkdir(parents=True, exist_ok=True)

    def extract(self, name: str, *_: object) -> None:
        self.steps.append("extract")

    def train(self, name: str, *_: object) -> None:
        self.steps.append("train")
        model_dir = self.model_dir(name)
        for file in ("G_1.pth", "D_1.pth", f"{name}_2e_10s.pth", f"{name}.index"):
            (model_dir / file).write_bytes(b"x")


@pytest.fixture(autouse=True)
def _ffmpeg(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(trainer_module, "require_tool", lambda name: name)


def _fake_prepare(inputs, out_dir: Path, ffmpeg: str = "ffmpeg") -> DatasetInfo:
    out_dir.mkdir(parents=True, exist_ok=True)
    return DatasetInfo(directory=out_dir, files=[out_dir / "001.wav"], total_seconds=900.0)


def _run(tmp_path: Path, applio: FakeApplio, **overrides: object) -> Path:
    options = TrainOptions(name="me", inputs=[tmp_path / "rec.m4a"], **overrides)  # type: ignore[arg-type]
    return train_voice(
        options,
        applio,
        tmp_path / "training",
        tmp_path / "voices",
        report=lambda _: None,
        prepare=_fake_prepare,
    )


def test_full_run_installs_the_trained_voice(tmp_path: Path) -> None:
    applio = FakeApplio(tmp_path)

    voice_dir = _run(tmp_path, applio)

    assert applio.steps == ["install", "preprocess", "extract", "train"]
    assert sorted(p.name for p in voice_dir.iterdir()) == ["me.index", "me.pth"]


def test_existing_checkpoint_resumes_without_preprocessing(tmp_path: Path) -> None:
    applio = FakeApplio(tmp_path)
    model_dir = applio.model_dir("me")
    model_dir.mkdir(parents=True)
    (model_dir / "G_5.pth").touch()
    (model_dir / "D_5.pth").touch()

    _run(tmp_path, applio)

    assert applio.steps == ["install", "train"]


def test_restart_throws_away_old_run(tmp_path: Path) -> None:
    applio = FakeApplio(tmp_path)
    model_dir = applio.model_dir("me")
    model_dir.mkdir(parents=True)
    (model_dir / "G_5.pth").touch()
    (model_dir / "D_5.pth").touch()

    _run(tmp_path, applio, restart=True)

    assert "preprocess" in applio.steps
    assert not (model_dir / "G_5.pth").exists()


def test_existing_voice_needs_force(tmp_path: Path) -> None:
    voice_dir = tmp_path / "voices" / "me"
    voice_dir.mkdir(parents=True)
    (voice_dir / "me.pth").touch()

    with pytest.raises(TrainingError, match="--force"):
        _run(tmp_path, FakeApplio(tmp_path))


@pytest.mark.parametrize("name", ["", "../evil", "has space", "a" * 65])
def test_bad_voice_name_is_rejected(tmp_path: Path, name: str) -> None:
    options = TrainOptions(name=name, inputs=[])

    with pytest.raises(TrainingError, match="Voice name"):
        train_voice(options, FakeApplio(tmp_path), tmp_path, tmp_path, report=lambda _: None)


def test_bad_sample_rate_is_rejected(tmp_path: Path) -> None:
    options = TrainOptions(name="me", inputs=[], sample_rate=22050)

    with pytest.raises(TrainingError, match="Sample rate"):
        train_voice(options, FakeApplio(tmp_path), tmp_path, tmp_path, report=lambda _: None)


def test_latest_weights_uses_highest_epoch(tmp_path: Path) -> None:
    for file in ("me_9e_90s.pth", "me_10e_100s.pth", "me_2e_20s.pth", "G_10.pth"):
        (tmp_path / file).touch()

    assert find_latest_weights(tmp_path, "me").name == "me_10e_100s.pth"


def test_missing_weights_raise(tmp_path: Path) -> None:
    with pytest.raises(TrainingError, match="without a model file"):
        find_latest_weights(tmp_path, "me")


def test_import_works_without_index(tmp_path: Path) -> None:
    model_dir = tmp_path / "logs"
    model_dir.mkdir()
    (model_dir / "me_3e_30s.pth").write_bytes(b"x")

    target = import_trained_model(model_dir, "me", tmp_path / "voices" / "me")

    assert target.name == "me.pth"
    assert [p.name for p in target.parent.iterdir()] == ["me.pth"]


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("me | epoch=5 | step=120 | time=10:00:00 | training_speed=0:00:35", 5.0),
        ("me | epoch=5 | step=110 | batch=6/24", 4.25),
        ("me | epoch=1 | step=0 | batch=0/0", 0.0),
        ("Starting training...", None),
        ("Lowest generator loss: 20.1 at epoch 4, step 100", None),
    ],
)
def test_epochs_done_reads_applio_progress(line: str, expected: float | None) -> None:
    assert epochs_done(line) == expected


def test_pause_hint_is_shown_in_the_training_step(tmp_path: Path) -> None:
    messages: list[str] = []
    options = TrainOptions(name="me", inputs=[tmp_path / "rec.m4a"])

    train_voice(
        options,
        FakeApplio(tmp_path),
        tmp_path / "training",
        tmp_path / "voices",
        report=messages.append,
        prepare=_fake_prepare,
        pause_hint="Press Stop.",
    )

    assert any(m.startswith("Step 4/4") and m.endswith("Press Stop.") for m in messages)
