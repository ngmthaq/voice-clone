# voice-clone

Change your voice in real time. voice-clone listens to your microphone, converts your voice with an RVC voice model, and sends the result to a virtual audio device. Apps like Zoom or Discord can then use that device as a microphone.

It runs in the terminal (a Textual TUI).

## Requirements

- Python 3.10, 3.11 or 3.12
- A virtual audio device:
  - macOS: BlackHole 2ch. Install with `brew install blackhole-2ch`.
  - Windows: VB-Audio Virtual Cable (VB-CABLE), from https://vb-audio.com/Cable/
- Windows with an NVIDIA GPU: install the CUDA build of PyTorch first (see below). Without a GPU, conversion runs on the CPU and may be slow.

## Install and run

Create a virtual environment and install the app (once):

macOS:

```bash
python3.10 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Windows (PowerShell):

```powershell
py -3.10 -m venv .venv
.venv\Scripts\Activate.ps1
pip install torch==2.5.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu124
pip install -e .
```

The first `pip install` line on Windows gets the NVIDIA (CUDA) build of PyTorch. Skip it if you have no NVIDIA GPU.

Then run the app:

```bash
python -m voice_clone run
```

In a new terminal, activate the environment again first (`source .venv/bin/activate`, or `.venv\Scripts\Activate.ps1` on Windows). After `pip install -e .`, the short command `voice-clone` works too.

On the first start the app downloads about 550 MB of base models into `models/`. A progress bar shows the download. If it fails, check your connection and press "Retry download".

## Add a voice

Put each RVC voice in its own folder under `voices/`:

```
voices/
  my-voice/
    model.pth      required
    model.index    optional, improves voice match
```

The folder name is the voice name shown in the app. Use any file names you like; the first `.pth` and the first `.index` in the folder are used.

## Train your own voice

Full step-by-step guide: [docs/TRAINING.md](docs/TRAINING.md).

Record 10–30 minutes of your own voice (for example with iPhone Voice Memos set to **Lossless**), copy the file(s) to this computer, then run:

```bash
python -m voice_clone train path/to/recording.m4a --name my-voice
```

The command:

1. Cleans the recordings (mono, 48 kHz, removes low hum, evens out loudness) into `training/<name>/dataset/`.
2. The first time only: installs [Applio](https://github.com/IAHispano/Applio) 3.7.1 in `training/.applio/` in its own Python 3.12 virtual environment, and downloads its pretrained models (several GB).
3. Slices the audio and extracts voice features (RMVPE pitch, ContentVec).
4. Trains an RVC v2 model and copies the result to `voices/<name>/`.

Needs `ffmpeg`, `git` and **Python 3.12** (for Applio) installed. Training uses an NVIDIA GPU (Windows), the Apple GPU (Apple Silicon), or the CPU. On an M1 Mac, 200 epochs take several hours.

Useful options:

| Option | Default | Use |
| --- | --- | --- |
| `--epochs N` | 200 | More epochs = closer match, but too many can sound robotic |
| `--batch-size N` | 8 | Lower to 4 if training runs out of memory |
| `--sample-rate` | 40000 | 32000, 40000 or 48000 |
| `--restart` | off | Throw away an earlier run with the same name |
| `--force` | off | Replace an existing voice in `voices/<name>/` |

Press **Ctrl+C** to pause. Run the same command again to continue from the last checkpoint (saved every 10 epochs by default).

## Use it

1. Pick your microphone, the output device (BlackHole 2ch or CABLE Input), and a voice.
2. Set the pitch with `-` and `+` (in semitones, -12 to +12).
3. Press Start (or the space bar). Loading the voice can take about 30 seconds the first time.
4. In Zoom, Discord or any other app, choose "BlackHole 2ch" (macOS) or "CABLE Output" (Windows) as the microphone.

Use headphones, so the converted voice does not feed back into your microphone.

Keys: `space` start or stop, `q` quit. Your choices are saved and restored on the next start.

## Logs

The app never prints to the terminal. Logs are written to the user log folder:

- macOS: `~/Library/Logs/voice-clone/voice-clone.log`
- Windows: `%LOCALAPPDATA%\voice-clone\Logs\voice-clone.log`

## Responsible use

Only use voices you have the right to use. Do not use this tool to pretend to be someone else without their permission.

## Licenses

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
