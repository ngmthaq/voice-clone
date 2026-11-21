"""Checks that everything the app needs is in place, with a plain-words fix for each problem.

gather_facts() looks at the computer (slow: it loads torch and asks the audio system).
evaluate() turns those facts into checks, without side effects, so it is easy to test.
"""

import logging
import platform as platform_module
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

from voice_clone.engine.download import BaseModelFile, base_model_files
from voice_clone.errors import VoiceCloneError

logger = logging.getLogger(__name__)

VOICE_CHANGER = "Voice changer"
TRAINING = "Training"
OK = "ok"
WARNING = "warning"
MISSING = "missing"
INFO = "info"
MODELS_KEY = "models"
APPLIO_KEY = "applio"  # Applio can be installed now from the Check setup page
SUPPORTED_PYTHON = (3, 12)
CUDA_TORCH_INSTALL = (
    "pip install --force-reinstall torch==2.5.1 torchaudio==2.5.1 "
    "--index-url https://download.pytorch.org/whl/cu124"
)


@dataclass(frozen=True)
class Check:
    group: str
    name: str
    status: str
    detail: str
    fix: str = ""
    key: str = ""
    download_mb: int = 0  # for the models check: size of what is missing


@dataclass
class Facts:
    platform: str
    machine: str
    python_version: tuple[int, int, int]
    models_dir: Path
    model_files: list[BaseModelFile]
    input_devices: list[str] | None  # None: the audio system could not be read
    output_devices: list[str] | None
    audio_error: str = ""
    compute: str = "cpu"  # cuda, mps or cpu
    gpu_name: str = ""
    nvidia_driver: bool = False
    voices: list[str] = field(default_factory=list)
    ffmpeg: str | None = None
    git: str | None = None
    python312: str | None = None
    applio_installed: bool = False


def gather_facts() -> Facts:
    from voice_clone.paths import models_dir, training_dir, voices_dir
    from voice_clone.profiles import discover_profiles
    from voice_clone.training.applio import APPLIO_PYTHON, Applio
    from voice_clone.training.commands import find_python

    facts = Facts(
        platform=sys.platform,
        machine=platform_module.machine(),
        python_version=sys.version_info[:3],
        models_dir=models_dir(),
        model_files=base_model_files(models_dir()),
        input_devices=None,
        output_devices=None,
    )
    try:
        from voice_clone.audio import list_input_devices, list_output_devices

        facts.input_devices = [device.name for device in list_input_devices()]
        facts.output_devices = [device.name for device in list_output_devices()]
    except Exception as exc:
        logger.exception("Could not list audio devices")
        facts.audio_error = str(exc) or type(exc).__name__
    facts.compute, facts.gpu_name = _compute_device()
    facts.nvidia_driver = shutil.which("nvidia-smi") is not None
    try:
        facts.voices = [profile.name for profile in discover_profiles(voices_dir())]
    except Exception:
        logger.exception("Could not read the voices folder")
    facts.ffmpeg = shutil.which("ffmpeg")
    facts.git = shutil.which("git")
    try:
        facts.python312 = " ".join(find_python(APPLIO_PYTHON, sys.platform))
    except VoiceCloneError:
        facts.python312 = None
    facts.applio_installed = Applio(training_dir() / ".applio").is_installed
    return facts


def evaluate(facts: Facts) -> list[Check]:
    return [
        _python(facts),
        _models(facts),
        *_audio(facts),
        _compute(facts),
        _voices(facts),
        _tool(facts, "ffmpeg", facts.ffmpeg),
        _tool(facts, "git", facts.git),
        _python312(facts),
        _applio(facts),
    ]


def _python(facts: Facts) -> Check:
    major, minor, micro = facts.python_version
    version = f"{major}.{minor}.{micro}"
    if (major, minor) == SUPPORTED_PYTHON:
        return Check(VOICE_CHANGER, "Python", OK, version)
    return Check(
        VOICE_CHANGER,
        "Python",
        WARNING,
        f"{version} is not supported. The app and training use Python 3.12.",
        "Make the virtual environment again with Python 3.12 (see docs/INSTALL.md).",
    )


def _models(facts: Facts) -> Check:
    missing = [file for file in facts.model_files if not file.present]
    if not missing:
        return Check(VOICE_CHANGER, "Base models", OK, f"Downloaded in {facts.models_dir}")
    size = sum(file.approx_mb for file in missing)
    names = ", ".join(file.name for file in missing)
    return Check(
        VOICE_CHANGER,
        "Base models",
        MISSING,
        f"Missing: {names} (about {size} MB)",
        "Press 'Download base models' below.",
        MODELS_KEY,
        size,
    )


def _audio(facts: Facts) -> list[Check]:
    if facts.input_devices is None or facts.output_devices is None:
        return [
            Check(
                VOICE_CHANGER,
                "Audio devices",
                MISSING,
                f"Could not read the audio devices: {facts.audio_error}",
                "Check that the computer has sound devices, then press 'Check again'.",
            )
        ]
    # BlackHole also shows up as an input; it is not a real microphone.
    microphones = [name for name in facts.input_devices if not _is_virtual_device(name)]
    if microphones:
        mic = Check(VOICE_CHANGER, "Microphone", OK, ", ".join(microphones))
    else:
        mic = Check(
            VOICE_CHANGER,
            "Microphone",
            MISSING,
            "No microphone found.",
            "Plug in a microphone or headset, then press 'Check again'.",
        )
        if facts.platform == "darwin":
            mic = _with_fix(
                mic,
                mic.fix + " If one is plugged in, allow the terminal app in System Settings "
                "→ Privacy & Security → Microphone.",
            )
    virtual = [name for name in facts.output_devices if _is_virtual_output(name)]
    if virtual:
        cable = Check(VOICE_CHANGER, "Virtual audio device", OK, ", ".join(virtual))
    elif facts.platform == "win32":
        cable = Check(
            VOICE_CHANGER,
            "Virtual audio device",
            MISSING,
            "VB-CABLE was not found.",
            "Install VB-Audio Virtual Cable from https://vb-audio.com/Cable/ and restart "
            "the computer.",
        )
    else:
        cable = Check(
            VOICE_CHANGER,
            "Virtual audio device",
            MISSING,
            "BlackHole 2ch was not found.",
            "Run 'brew install blackhole-2ch', then restart the app.",
        )
    return [mic, cable]


def _compute(facts: Facts) -> Check:
    if facts.compute == "cuda":
        return Check(VOICE_CHANGER, "GPU", OK, f"NVIDIA GPU (CUDA): {facts.gpu_name}".rstrip(": "))
    if facts.compute == "mps":
        return Check(VOICE_CHANGER, "GPU", OK, "Apple GPU (Metal)")
    if facts.nvidia_driver:
        return Check(
            VOICE_CHANGER,
            "GPU",
            WARNING,
            "An NVIDIA card is installed, but this PyTorch cannot use it. Conversion runs "
            "on the CPU.",
            f"Install the CUDA build of PyTorch: {CUDA_TORCH_INSTALL}",
        )
    if facts.platform == "darwin" and facts.machine == "arm64":
        return Check(
            VOICE_CHANGER,
            "GPU",
            WARNING,
            "The Apple GPU is not available to PyTorch. Conversion runs on the CPU.",
            "Reinstall the app in a fresh virtual environment (see docs/INSTALL.md).",
        )
    return Check(
        VOICE_CHANGER,
        "GPU",
        WARNING,
        "No GPU found. Conversion runs on the CPU and may be slow or drop audio.",
        "If audio drops, lower 'Context (ms)' on the Advanced tab.",
    )


def _voices(facts: Facts) -> Check:
    if facts.voices:
        return Check(VOICE_CHANGER, "Voices", OK, ", ".join(facts.voices))
    return Check(
        VOICE_CHANGER,
        "Voices",
        MISSING,
        "No voices found in voices/.",
        "Train one with 'Train a voice' on the start screen, or add one (docs/VOICES.md).",
    )


def _tool(facts: Facts, name: str, path: str | None) -> Check:
    from voice_clone.training.commands import INSTALL_HINTS

    if path is not None:
        return Check(TRAINING, name, OK, path)
    return Check(TRAINING, name, MISSING, f"'{name}' was not found.", INSTALL_HINTS[name])


def _python312(facts: Facts) -> Check:
    from voice_clone.training.commands import PYTHON_HINT

    if facts.python312 is not None:
        return Check(TRAINING, "Python 3.12 (for Applio)", OK, facts.python312)
    return Check(
        TRAINING,
        "Python 3.12 (for Applio)",
        MISSING,
        "Python 3.12 was not found on the PATH. Applio builds its own environment from it.",
        PYTHON_HINT.format(version="3.12"),
    )


def _applio(facts: Facts) -> Check:
    if facts.applio_installed:
        return Check(TRAINING, "Applio", OK, "Installed in training/.applio/")
    detail = "Not installed yet (several GB). The first training run installs it by itself."
    if facts.git is None or facts.python312 is None:
        return Check(
            TRAINING,
            "Applio",
            INFO,
            detail,
            "To install it now, first install git and Python 3.12.",
        )
    return Check(
        TRAINING,
        "Applio",
        INFO,
        detail,
        "Or press 'Install Applio' below to install it now.",
        APPLIO_KEY,
    )


def _is_virtual_output(name: str) -> bool:
    from voice_clone.audio.devices import VIRTUAL_OUTPUT_KEYWORDS

    lowered = name.lower()
    return any(keyword in lowered for keyword in VIRTUAL_OUTPUT_KEYWORDS)


def _is_virtual_device(name: str) -> bool:
    lowered = name.lower()
    return "blackhole" in lowered or "cable output" in lowered or _is_virtual_output(name)


def _compute_device() -> tuple[str, str]:
    try:
        import torch

        from voice_clone.engine.device import select_torch_device

        device = select_torch_device().type
        name = torch.cuda.get_device_name(0) if device == "cuda" else ""
        return device, name
    except Exception:
        logger.exception("Could not check the PyTorch device")
        return "cpu", ""


def _with_fix(check: Check, fix: str) -> Check:
    return Check(
        check.group, check.name, check.status, check.detail, fix, check.key, check.download_mb
    )
