# Install

How to set up voice-clone on macOS or Windows. When you are done, go to [USAGE.md](USAGE.md).

## Prerequisites

To use the voice changer:

- Python 3.10, 3.11 or 3.12
- A virtual audio device:
  - macOS: BlackHole 2ch. Install with `brew install blackhole-2ch`.
  - Windows: VB-Audio Virtual Cable (VB-CABLE), from https://vb-audio.com/Cable/
- Windows: an NVIDIA graphics card makes conversion much faster. Without one, the app uses the CPU and may be slow.
- Headphones, so the converted voice does not feed back into your microphone.

To train your own voice, also (details in [TRAINING.md](TRAINING.md#before-you-start)):

- `ffmpeg`: `brew install ffmpeg` (macOS) or `winget install ffmpeg` (Windows)
- `git`: `xcode-select --install` (macOS) or `winget install Git.Git` (Windows)
- **Python 3.12** (Applio needs it, even if the app runs on 3.10): from https://www.python.org/downloads/, or `brew install python@3.12` on macOS

## Install the app

Create a virtual environment and install the app (once). Pick the block for your computer.

### macOS (Apple Silicon or Intel)

```bash
python3.10 -m venv .venv
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
py -3.10 -m venv .venv
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
py -3.10 -m venv .venv
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

The app opens on a start screen with two choices: **Voice changer** and **Train a voice**. Press `esc` to come back to it.

In a new terminal, activate the environment again first (`source .venv/bin/activate`, or `.venv\Scripts\Activate.ps1` on Windows). After `pip install -e .`, the short command `voice-clone` works too.

The first time you open the voice changer, the app downloads about 550 MB of base models into `models/`. A progress bar shows the download. If it fails, check your connection and press "Retry download".

Next: [USAGE.md](USAGE.md) to change your voice, or [TRAINING.md](TRAINING.md) to make your own voice.
