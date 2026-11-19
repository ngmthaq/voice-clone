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
