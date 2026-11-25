import pytest

import voice_clone.domain.config as config
from voice_clone.domain.config import (
    PERFORMANCE_PRESETS,
    Settings,
    apply_preset,
    load_settings,
    save_settings,
)


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


def test_unknown_precision_falls_back_to_defaults(tmp_path):
    path = tmp_path / "settings.toml"
    path.write_text('precision = "fp8"\n')

    assert load_settings(path).precision == "auto"


def test_precision_round_trips(tmp_path):
    path = tmp_path / "settings.toml"
    save_settings(Settings(precision="fp16"), path)

    assert load_settings(path).precision == "fp16"


def test_apply_preset_sets_preset_values_and_keeps_the_rest():
    settings = apply_preset(Settings(profile="me", pitch=3), "light")

    assert (settings.block_ms, settings.context_ms, settings.gate_open_above_db) == (600, 300, 6.0)
    assert (settings.profile, settings.pitch) == ("me", 3)
    assert isinstance(settings.block_ms, int)


def test_light_and_minimal_use_the_balanced_noise_gate():
    gate = ("gate_hold_ms", "gate_pre_open_ms", "gate_open_above_db")
    balanced = {name: PERFORMANCE_PRESETS["balanced"][1][name] for name in gate}

    for preset in ("minimal", "light"):
        assert {name: PERFORMANCE_PRESETS[preset][1][name] for name in gate} == balanced


def test_new_noise_settings_defaults_and_presets():
    assert Settings().gate_open_below_voice_db == 20.0
    assert Settings().noise_reduction is True
    assert all(
        values["gate_open_below_voice_db"] == 20.0 for _, values in PERFORMANCE_PRESETS.values()
    )
    assert "noise_reduction" not in config.PRESET_FIELDS


def test_bump_filter_defaults_on_and_is_not_a_preset_field():
    assert Settings().bump_filter is True
    assert "bump_filter" not in config.PRESET_FIELDS
    assert all("bump_filter" not in values for _, values in PERFORMANCE_PRESETS.values())


def test_bump_filter_false_round_trips_and_old_file_defaults_true(tmp_path, monkeypatch):
    settings_file = tmp_path / "settings.toml"
    monkeypatch.setattr(config, "settings_path", lambda: settings_file)
    settings_file.write_text("gate_hold_ms = 700\n")
    assert config.load_settings().bump_filter is True

    config.save_settings(Settings(bump_filter=False))

    assert config.load_settings().bump_filter is False
