import pytest

import voice_clone.config as config
from voice_clone.config import Settings, load_settings, save_settings


def test_save_then_load_returns_same_settings(tmp_path):
    path = tmp_path / "settings.toml"
    settings = Settings(input_device="Mic", output_device="BlackHole 2ch", profile="a", pitch=-3)

    save_settings(settings, path)

    assert load_settings(path) == settings


def test_save_creates_missing_parent_folder(tmp_path):
    path = tmp_path / "nested" / "settings.toml"

    save_settings(Settings(), path)

    assert path.is_file()


def test_load_missing_file_returns_defaults(tmp_path):
    assert load_settings(tmp_path / "missing.toml") == Settings()


def test_load_broken_toml_returns_defaults(tmp_path):
    path = tmp_path / "settings.toml"
    path.write_text("this is = = not toml [")

    assert load_settings(path) == Settings()


def test_load_out_of_range_pitch_returns_defaults(tmp_path):
    path = tmp_path / "settings.toml"
    path.write_text("pitch = 99\n")

    assert load_settings(path) == Settings()


def test_advanced_voice_defaults():
    settings = Settings()

    assert (
        settings.protect_percent,
        settings.loudness_percent,
        settings.pitch_smoothing_ms,
        settings.context_ms,
    ) == (67, 50, 30, 1000)


def test_failed_save_keeps_the_old_file(tmp_path, monkeypatch):
    path = tmp_path / "settings.toml"
    save_settings(Settings(pitch=3), path)

    def broken_dump(data, file):
        file.write(b"pitch = ")
        raise OSError("disk full")

    monkeypatch.setattr(config.tomli_w, "dump", broken_dump)

    with pytest.raises(OSError):
        save_settings(Settings(pitch=5), path)

    assert load_settings(path).pitch == 3
    assert [p.name for p in tmp_path.iterdir()] == ["settings.toml"]
