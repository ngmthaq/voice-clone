# Install

How to set up voice-clone on macOS or Windows. When you are done, go to [USAGE.md](USAGE.md).

## Prerequisites

The run script (next section) can install all of these for you. It checks for Python 3.12, git, ffmpeg and the virtual audio device. If something is missing, it shows a line for each item (installed or missing) and asks one question: `Some things are missing. Install them now? [Y/n]`. Press Enter or type `y` to install. If there is no terminal to answer, the answer is Yes. Type `n` to skip, and install them by hand as shown below. When nothing is missing, it only says that everything is ready.

- **macOS:** it uses Homebrew (it installs Homebrew first if needed). Homebrew and BlackHole ask for your Mac password. After BlackHole, the script restarts the audio system. If BlackHole 2ch does not show up, restart the Mac.
- **Windows:** it uses `winget` (from "App Installer" in the Microsoft Store). It downloads VB-CABLE from vb-audio.com and starts its setup. Windows asks for administrator rights, and you click **Install** in the driver setup. If CABLE Input does not show up, restart Windows.
- If git, ffmpeg or the audio device fails to install, the script warns and goes on. If Python 3.12 fails to install, it stops.

To install by hand, or to check what you have, use the list below.

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

## Install and start with one script

One script does everything. It takes no options. The only question it asks is whether to install missing prerequisites (see [Prerequisites](#prerequisites)). Run it from any folder.

### macOS

```bash
scripts/run.sh
```

### Windows (PowerShell)

```powershell
scripts\run.ps1
```

If PowerShell says running scripts is disabled, run this once in the same window, then try again:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

Or run the script like this: `powershell -ExecutionPolicy Bypass -File scripts\run.ps1`

### What the script does

1. **Installs the prerequisites** that are missing, after you say yes (see [Prerequisites](#prerequisites)).
2. **Installs the app.** It finds Python 3.12 (if not, it stops and says how to install it), makes the `.venv` (it makes it again when the `.venv` was made with another Python version), and installs the app and the development tools (pytest and ruff). On Windows with an NVIDIA card, it installs the CUDA build of PyTorch first (about 2.5 GB) and prints whether PyTorch can use the card. This step is skipped when `pyproject.toml` has not changed since the last install.
3. **Downloads the models.** The base models (about 560 MB) and Applio for voice training (several GB). Files that are already there are skipped.
4. **Measures the speed** of this computer, the first time only (up to a minute). It saves the Performance preset that fits. This needs a voice in `voices/`. Without one, the script skips it and tries again next time.
5. **Starts the app.**

The first run is large and slow because of the downloads. Later runs skip every finished step and start the app within a few seconds.

If the model download, the Applio install or the speed test fails, the script prints a warning and still starts the app. The failed step is tried again on the next run. You can also use the **Check setup** screen. If the install itself fails, the script stops.

After the check, the script says `Still missing: ...` when something is not installed, for example when you answered No or the install failed.

To install again, delete the file `.venv/.voice-clone-install`, or the whole `.venv` folder, and run the script.

## Behind a company proxy

The app installs `pip-system-certs`, so Python downloads (pip, the models, Applio) use the certificates your system trusts. The scripts install it first, before the other downloads.

- The company certificate must be installed in the system. IT usually does this.
- If the proxy needs it, set `HTTPS_PROXY` (and `HTTP_PROXY`) before you run the script, for example `export HTTPS_PROXY=http://proxy.example.com:8080` (macOS) or `$env:HTTPS_PROXY = 'http://proxy.example.com:8080'` (PowerShell).
- Applio is downloaded with `git`, which has its own certificate settings. On Windows, you may need `git config --global http.sslBackend schannel`.
- An Applio install that already exists does not get `pip-system-certs`. To redo it, delete the folder `training/.applio` and run the script again.
- If you install by hand, run `pip install pip-system-certs` first (see the blocks below).

### Other commands

The script starts only the app. To use another command, activate the `.venv` first (`source .venv/bin/activate`, or `.venv\Scripts\Activate.ps1` on Windows), then run:

```bash
python -m voice_clone train --help      # train a voice
python -m voice_clone download-models   # download the base models (about 560 MB)
python -m voice_clone install-applio    # install Applio for training (several GB)
python -m voice_clone measure-speed     # measure the speed again
```

`download-models` skips files that are already there. These commands print their progress, exit with 0 when they work and 1 on an error, and can be stopped with Ctrl+C.

If you prefer to do the steps by hand, use the blocks below.

## Install the app

Create a virtual environment with Python 3.12 and install the app (once). Pick the block for your computer.

If you already have a `.venv` folder made with another Python version, delete the folder first, then run the block again.

### macOS (Apple Silicon or Intel)

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install pip-system-certs
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
pip install pip-system-certs
pip install torch==2.5.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu124
pip install -e .
```

The fourth line installs the NVIDIA (CUDA) build of PyTorch, about 2.5 GB. It must come **before** `pip install -e .`.

Check that the card is used:

```powershell
python -c "import torch; print(torch.cuda.is_available())"
```

It must print `True`. If it prints `False`, update the NVIDIA driver and check again.

### Windows without an NVIDIA card (PowerShell)

```powershell
py -3.12 -m venv .venv    # Microsoft Store Python: python3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install pip-system-certs
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

To get training ready ahead of time, press **Install Applio** (or run `python -m voice_clone install-applio`). It downloads Applio, creates its Python 3.12 environment, installs its packages and downloads its pretrained models (several GB in all). The page shows each step and Applio's output; **Stop install** stops it, and pressing **Install Applio** again starts over. The button appears only when `git` and Python 3.12 are installed. If you skip this, the first training run installs Applio by itself.

Once the base models and at least one voice are there, press **Measure speed**. It tests each Performance preset on this computer (up to a minute) and saves the heaviest one up to Balanced that the computer keeps up with, so the voice changer is ready to use.

The voice changer also downloads the base models by itself the first time you open it, if they are missing. If a download fails, check your connection and press "Retry download".

If the GPU line says an NVIDIA card is installed but PyTorch cannot use it, install the CUDA build as shown in [Windows with an NVIDIA card](#windows-with-an-nvidia-card-powershell).

Next: [USAGE.md](USAGE.md) to change your voice, or [TRAINING.md](TRAINING.md) to make your own voice.
