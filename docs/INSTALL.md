# Install

How to set up voice-clone on macOS or Windows. When you are done, go to [USAGE.md](USAGE.md).

## Prerequisites

To use the voice changer:

- **Python 3.12**, for the app and for training: from https://www.python.org/downloads/, or `brew install python@3.12` on macOS. Check it with `python3.12 --version` (macOS) or `py -3.12 --version` (Windows).

  **Windows:** `py` comes only with the installer from python.org. If you installed Python from the Microsoft Store, `py` is "not recognized": type `python3.12` wherever these docs say `py -3.12` (for example `python3.12 --version` and `python3.12 -m venv .venv`).
- A virtual audio device:
  - macOS: BlackHole 2ch. Install with `brew install blackhole-2ch`.
  - Windows: VB-Audio Virtual Cable (VB-CABLE), from https://vb-audio.com/Cable/
- Windows: an NVIDIA graphics card makes conversion much faster. Without one, the app uses the CPU and may be slow.
- Headphones, so the converted voice does not feed back into your microphone.

To train your own voice, also install (details in [TRAINING.md](TRAINING.md#before-you-start)):

- `ffmpeg`: `brew install ffmpeg` (macOS) or `winget install ffmpeg` (Windows)
- `git`: `xcode-select --install` (macOS) or `winget install Git.Git` (Windows)

## Install the app

Create a virtual environment with Python 3.12 and install the app (once). Pick the block for your computer.

If you already have a `.venv` folder made with another Python version, delete the folder first, then run the block again.

### macOS (Apple Silicon or Intel)

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Macs have no NVIDIA card. On Apple Silicon (M1 and later) the app uses the Apple GPU by itself.

### Windows: do I have an NVIDIA card?

In PowerShell, run:

```powershell
nvidia-smi
```

- It prints a table with your card's name (for example "NVIDIA GeForce RTX 3060"): you have one. Use **Windows with an NVIDIA card**.
- It says the command is not recognized: you have no NVIDIA card, or its driver is missing. Use **Windows without an NVIDIA card**. (To be sure, open Task Manager → Performance and look for "GPU … NVIDIA". If it is there, install the latest driver from https://www.nvidia.com/drivers and run `nvidia-smi` again.)

### Windows with an NVIDIA card (PowerShell)

```powershell
py -3.12 -m venv .venv    # Microsoft Store Python: python3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install torch==2.5.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu124
pip install -e .
```

The third line installs the NVIDIA (CUDA) build of PyTorch, about 2.5 GB. It must come **before** `pip install -e .`.

Check that the card is used:

```powershell
python -c "import torch; print(torch.cuda.is_available())"
```

It must print `True`. If it prints `False`, update the NVIDIA driver and check again.

### Windows without an NVIDIA card (PowerShell)

```powershell
py -3.12 -m venv .venv    # Microsoft Store Python: python3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
```

This installs the normal (CPU) build of PyTorch.

If you add an NVIDIA card later, or ran this block by mistake on a computer that has one, switch to the CUDA build:

```powershell
pip install --force-reinstall torch==2.5.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu124
```

## First start

```bash
python -m voice_clone run
```

The app opens on a start screen with three choices: **Voice changer**, **Train a voice** and **Check setup**. Press `esc` to come back to it.

In a new terminal, activate the environment again first (`source .venv/bin/activate`, or `.venv\Scripts\Activate.ps1` on Windows). After `pip install -e .`, the short command `voice-clone` works too.

## Check the setup

Choose **Check setup** on the start screen. It checks everything the app needs and says how to fix what is missing:

| Group | What it checks |
| --- | --- |
| Voice changer | Python version, base models, microphone, virtual audio device (BlackHole or VB-CABLE), GPU, voices |
| Training | `ffmpeg`, `git`, Python 3.12, and whether Applio is installed yet |

Each line shows ✓ (ready), ✗ (missing, with how to fix it), ! (works, but could be better) or i (for your information). If the base models are missing, press **Download base models** (about 560 MB, into `models/`). After you install something, press **Check again**.

To get training ready ahead of time, press **Install Applio**. It downloads Applio, creates its Python 3.12 environment, installs its packages and downloads its pretrained models (several GB in all). The page shows each step and Applio's output; **Stop install** stops it, and pressing **Install Applio** again starts over. The button appears only when `git` and Python 3.12 are installed. If you skip this, the first training run installs Applio by itself.

Once the base models and at least one voice are there, press **Measure speed**. It tests each Performance preset on this computer (up to a minute) and saves the best one the computer keeps up with, so the voice changer is ready to use.

The voice changer also downloads the base models by itself the first time you open it, if they are missing. If a download fails, check your connection and press "Retry download".

If the GPU line says an NVIDIA card is installed but PyTorch cannot use it, install the CUDA build as shown in [Windows with an NVIDIA card](#windows-with-an-nvidia-card-powershell).

Next: [USAGE.md](USAGE.md) to change your voice, or [TRAINING.md](TRAINING.md) to make your own voice.
