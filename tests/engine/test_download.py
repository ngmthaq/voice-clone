import pytest

import voice_clone.engine.download as download
from voice_clone.engine.download import base_model_paths, base_models_present, ensure_base_models
from voice_clone.errors import ModelDownloadError


@pytest.fixture
def fake_hub(monkeypatch):
    calls = []

    def fake_download(repo_id, filename, local_dir):
        calls.append(filename)
        (local_dir / filename).write_bytes(b"x")

    monkeypatch.setattr(download, "hf_hub_download", fake_download)
    return calls


def test_downloads_all_files_when_missing(tmp_path, fake_hub):
    paths = ensure_base_models(tmp_path)

    assert sorted(fake_hub) == ["config.json", "pytorch_model.bin", "rmvpe.pt"]
    assert base_models_present(tmp_path)
    assert paths == base_model_paths(tmp_path)


def test_skips_files_already_present(tmp_path, fake_hub):
    paths = base_model_paths(tmp_path)
    paths.contentvec_dir.mkdir(parents=True)
    (paths.contentvec_dir / "config.json").write_bytes(b"x")
    (paths.contentvec_dir / "pytorch_model.bin").write_bytes(b"x")

    ensure_base_models(tmp_path)

    assert fake_hub == ["rmvpe.pt"]


def test_progress_callback_is_called_and_reaches_one(tmp_path, fake_hub):
    events = []

    ensure_base_models(tmp_path, lambda message, fraction: events.append((message, fraction)))

    assert events and events[-1][1] == 1.0


def test_hub_failure_raises_model_download_error(tmp_path, monkeypatch):
    def failing(**kwargs):
        raise OSError("offline")

    monkeypatch.setattr(download, "hf_hub_download", failing)

    with pytest.raises(ModelDownloadError):
        ensure_base_models(tmp_path)


def test_base_models_present_is_false_for_empty_folder(tmp_path):
    assert not base_models_present(tmp_path)


def test_progress_bars_use_a_thread_lock_inside_the_tui(tmp_path, fake_hub):
    # A multiprocessing lock needs a real stderr, which the TUI does not have (Python 3.12).
    import threading

    import tqdm

    ensure_base_models(tmp_path)

    assert isinstance(tqdm.tqdm.get_lock(), type(threading.RLock()))
