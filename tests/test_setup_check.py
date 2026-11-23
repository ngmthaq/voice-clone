from pathlib import Path

import pytest

from voice_clone.engine.download import base_model_files
from voice_clone.setup_check import (
    APPLIO_KEY,
    INFO,
    MISSING,
    MODELS_KEY,
    OK,
    TRAINING,
    VOICE_CHANGER,
    WARNING,
    Facts,
    evaluate,
)


def _ready_models(models_dir: Path) -> None:
    for file in base_model_files(models_dir):
        file.path.parent.mkdir(parents=True, exist_ok=True)
        file.path.write_bytes(b"x")


def _facts(tmp_path: Path, **overrides) -> Facts:
    values = dict(
        platform="darwin",
        machine="arm64",
        python_version=(3, 12, 8),
        models_dir=tmp_path,
        model_files=base_model_files(tmp_path),
        input_devices=["MacBook Mic"],
        output_devices=["Speakers", "BlackHole 2ch"],
        compute="mps",
        voices=["me"],
        ffmpeg="/bin/ffmpeg",
        git="/bin/git",
        python312="/bin/python3.12",
        applio_installed=True,
    )
    values.update(overrides)
    return Facts(**values)


def _by_name(checks):
    return {check.name: check for check in checks}


def test_everything_ready(tmp_path):
    _ready_models(tmp_path)

    checks = evaluate(_facts(tmp_path))

    assert {check.status for check in checks} == {OK}
    assert {check.group for check in checks} == {VOICE_CHANGER, TRAINING}


def test_missing_models_are_listed_with_size_and_the_download_key(tmp_path):
    check = _by_name(evaluate(_facts(tmp_path)))["Base models"]

    assert check.status == MISSING
    assert check.key == MODELS_KEY
    assert "rmvpe/rmvpe.pt" in check.detail
    assert "about 560 MB" in check.detail


def test_only_missing_models_count(tmp_path):
    _ready_models(tmp_path)
    base_model_files(tmp_path)[2].path.unlink()

    check = _by_name(evaluate(_facts(tmp_path)))["Base models"]

    assert check.detail == "Missing: rmvpe/rmvpe.pt (about 181 MB)"


@pytest.mark.parametrize(
    ("platform", "fix_part"),
    [("darwin", "brew install blackhole-2ch"), ("win32", "vb-audio.com/Cable")],
)
def test_missing_virtual_device_has_a_fix_for_each_system(tmp_path, platform, fix_part):
    facts = _facts(tmp_path, platform=platform, output_devices=["Speakers"])

    check = _by_name(evaluate(facts))["Virtual audio device"]

    assert check.status == MISSING
    assert fix_part in check.fix


def test_no_microphone_on_mac_mentions_the_privacy_setting(tmp_path):
    check = _by_name(evaluate(_facts(tmp_path, input_devices=[])))["Microphone"]

    assert check.status == MISSING
    assert "Privacy & Security" in check.fix


def test_unreadable_audio_system_is_one_problem(tmp_path):
    facts = _facts(tmp_path, input_devices=None, output_devices=None, audio_error="PortAudio")

    checks = _by_name(evaluate(facts))

    assert checks["Audio devices"].status == MISSING
    assert "Microphone" not in checks


def test_nvidia_card_with_cpu_torch_suggests_the_cuda_build(tmp_path):
    facts = _facts(tmp_path, platform="win32", machine="AMD64", compute="cpu", nvidia_driver=True)

    check = _by_name(evaluate(facts))["GPU"]

    assert check.status == WARNING
    assert "download.pytorch.org/whl/cu124" in check.fix


def test_cuda_shows_the_card_name(tmp_path):
    facts = _facts(tmp_path, platform="win32", compute="cuda", gpu_name="RTX 3060")

    check = _by_name(evaluate(facts))["GPU"]

    assert (check.status, check.detail) == (OK, "NVIDIA GPU (CUDA): RTX 3060")


@pytest.mark.parametrize(
    ("fp16", "suffix"), [(True, ", fast fp16"), (False, ", fp32 (older card, fp16 is slow)")]
)
def test_cuda_shows_whether_fp16_is_used(tmp_path, fp16, suffix):
    facts = _facts(tmp_path, platform="win32", compute="cuda", gpu_name="GTX 1060", gpu_fp16=fp16)

    check = _by_name(evaluate(facts))["GPU"]

    assert check.detail == "NVIDIA GPU (CUDA): GTX 1060" + suffix


def test_no_voices_points_to_training(tmp_path):
    check = _by_name(evaluate(_facts(tmp_path, voices=[])))["Voices"]

    assert check.status == MISSING
    assert "Train a voice" in check.fix


def test_missing_training_tools(tmp_path):
    facts = _facts(tmp_path, ffmpeg=None, git=None, python312=None, applio_installed=False)

    checks = _by_name(evaluate(facts))

    assert checks["ffmpeg"].status == MISSING and "brew install ffmpeg" in checks["ffmpeg"].fix
    assert checks["git"].status == MISSING
    assert checks["Python 3.12 (for Applio)"].status == MISSING
    assert checks["Applio"].status == INFO


@pytest.mark.parametrize("version", [(3, 10, 14), (3, 11, 9), (3, 13, 0)])
def test_python_other_than_3_12_is_a_warning(tmp_path, version):
    check = _by_name(evaluate(_facts(tmp_path, python_version=version)))["Python"]

    assert check.status == WARNING
    assert "3.12" in check.fix


def test_virtual_devices_are_not_counted_as_microphones(tmp_path):
    facts = _facts(
        tmp_path,
        input_devices=["BlackHole 2ch", "MacBook Mic"],
        output_devices=["BlackHole 16ch", "BlackHole 2ch"],
    )

    checks = _by_name(evaluate(facts))

    assert checks["Microphone"].detail == "MacBook Mic"
    assert checks["Virtual audio device"].detail == "BlackHole 16ch, BlackHole 2ch"


def test_only_virtual_inputs_means_no_microphone(tmp_path):
    facts = _facts(tmp_path, platform="win32", input_devices=["CABLE Output (VB-Audio)"])

    assert _by_name(evaluate(facts))["Microphone"].status == MISSING


def test_applio_can_be_installed_when_git_and_python_are_there(tmp_path):
    check = _by_name(evaluate(_facts(tmp_path, applio_installed=False)))["Applio"]

    assert (check.status, check.key) == (INFO, APPLIO_KEY)


def test_applio_install_needs_git_and_python_first(tmp_path):
    facts = _facts(tmp_path, applio_installed=False, git=None)

    check = _by_name(evaluate(facts))["Applio"]

    assert check.key == ""
    assert "install git and Python 3.12" in check.fix
