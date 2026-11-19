# Train a New Voice

This guide shows how to turn your own recordings into a voice for the app. Training runs on your computer with [Applio](https://github.com/IAHispano/Applio) 3.7.1. The `voice-clone train` command does the whole job.

> Use only your own voice, or the voice of someone who clearly agreed to it. Do not use a cloned voice to trick or hurt other people.

---

## Before you start

You need:

| Tool | Check | Install |
| --- | --- | --- |
| Python 3.12 | macOS: `python3.12 --version` · Windows: `py -3.12 --version` | https://www.python.org/downloads/ (macOS: or `brew install python@3.12`) |
| `git` | `git --version` | macOS: `xcode-select --install` · Windows: `winget install Git.Git` |
| `ffmpeg` | `ffmpeg -version` | macOS: `brew install ffmpeg` · Windows: `winget install ffmpeg` |

The first training run also:

- installs Applio in `training/.applio/`, in its own Python 3.12 virtual environment,
- downloads Applio's pretrained models (several GB).

Later runs skip this setup.

The app itself must already be installed (see the README), and its virtual environment must be active (`source .venv/bin/activate`, or `.venv\Scripts\Activate.ps1` on Windows).

---

## Step 1 — Record

| Rule | Why |
| --- | --- |
| **One person only.** No other voices, no music, no TV. | Every sound in the file ends up in the model. |
| **10–30 minutes** of speech. At least 1 minute. | More clean audio gives a closer match. |
| **Quiet room**, with no echo or fan noise. | Noise makes the voice rough. |
| Keep the **same mic and distance** the whole time (about 20–30 cm). | Changes in distance change the tone. |
| Talk **naturally**, with some louder, softer, higher and lower parts. | The model learns your whole range. |

To help, read the script in [`docs/READING_SCRIPT.md`](READING_SCRIPT.md). It takes about 12–15 minutes.

**On iPhone:** set **Settings → Apps → Voice Memos → Audio Quality → Lossless**, record in Voice Memos, then AirDrop the file to the computer.

**On the computer:** a USB mic or USB headset works best. Cheap jack mics often add a low electrical hum.

Supported files: `.m4a`, `.wav`, `.mp3`, `.aac`, `.caf`, `.flac`, `.ogg`, `.aiff`, `.mp4`.

---

## Step 2 — Copy the recordings into the project

Make one folder per voice, and copy the recordings into it. Use a **plain file name** with no accents or special letters.

```bash
mkdir -p training/voice-2/raw
```

```bash
cp ~/Downloads/YourFile.m4a training/voice-2/raw/recording.m4a
```

You can put several files in the `raw/` folder. The command uses all of them.

`training/` is in `.gitignore`, so your recordings never go into git.

---

## Step 3 — Train

```bash
caffeinate -i python -m voice_clone train training/voice-2/raw --name voice-2 --epochs 100
```

- `--name` is the voice name shown in the app. Use only letters, numbers, `-` and `_`.
- `caffeinate -i` (macOS only) keeps the Mac awake while training runs. On Windows, leave it out.

The command runs 4 steps:

1. **Prepare.** It changes the recordings to mono 48 kHz WAV, removes low hum, and evens out the volume. The result goes to `training/<name>/dataset/`.
2. **Set up Applio.** This happens only on the first run.
3. **Slice and extract.** It cuts the audio into short pieces and extracts the pitch (RMVPE) and the voice features (ContentVec).
4. **Train.** It trains an RVC v2 model and copies the result to `voices/<name>/`.

### How long does it take?

| Computer | About 11 minutes of audio, 100 epochs |
| --- | --- |
| Apple M1 (16 GB) | about 3 minutes per epoch, so about 5 hours |
| Windows + NVIDIA GPU | much faster |
| CPU only | very slow, so not recommended |

### Pause and continue

- Press **Ctrl+C** to pause.
- Run **the same command** again. It continues from the last checkpoint, which is saved every 10 epochs.
- The voice is copied to `voices/<name>/` only when all epochs are done.

> Run **one training at a time**. All runs share the same Applio install and the same GPU.

---

## Step 4 — Use the voice

1. Run the app:

   ```bash
   python -m voice_clone run
   ```

2. Pick the new voice in the **Voice** list and press **Start**.
3. If the voice sounds too high or too low, change **Pitch**.

The trained files are in `voices/<name>/`:

| File | What it is |
| --- | --- |
| `<name>.pth` | The voice model (about 50 MB) |
| `<name>.index` | Helps the voice sound closer to the original. This file is optional. |

---

## Options

| Option | Default | Use |
| --- | --- | --- |
| `--name NAME` | `my-voice` | The voice name and folder name |
| `--epochs N` | 200 | More epochs give a closer match. Too many can sound robotic. 100 is a good start for 10+ minutes of audio. |
| `--batch-size N` | 8 | Lower it to 4 if training runs out of memory |
| `--sample-rate` | 40000 | 32000, 40000 or 48000 |
| `--save-every N` | 10 | Save a checkpoint every N epochs |
| `--restart` | off | Delete the earlier run with this name and start over. Use it after you change the recordings. |
| `--force` | off | Replace an existing voice in `voices/<name>/` |

See all options with:

```bash
python -m voice_clone train --help
```

---

## Troubleshooting

| Problem | What to do |
| --- | --- |
| `A voice named '…' already exists` | Add `--force`, or choose another `--name`. |
| `Only N s of audio found` | Record at least 1 minute. 10+ minutes is best. |
| `'ffmpeg' was not found` (or `git`, `Python 3.12`) | Install the tool. See [Before you start](#before-you-start). |
| Out of memory during training | Add `--batch-size 4`. |
| You changed the recordings, but the old ones are still used | Add `--restart`. |
| The voice sounds robotic or metallic | Train again with fewer epochs, for example `--epochs 60 --restart --force`. |
| The voice is noisy or has other people in it | Record again, alone, in a quieter room. Then use `--restart --force`. |
| Training stopped early and you want the result now | Run the same command again so it finishes. Or ask a developer to copy the newest `training/.applio/logs/<name>/<name>_*e_*s.pth` to `voices/<name>/` by hand. |

For the full output of a run, look at the terminal where it ran. App logs are in `~/Library/Logs/voice-clone/` (macOS) or `%LOCALAPPDATA%\voice-clone\Logs\` (Windows).

---

## Where files go

```
training/                  (not in git)
  <name>/raw/              your recordings
  <name>/dataset/          cleaned WAV files
  .applio/Applio-3.7.1/    Applio and its Python environment
  .applio/logs/<name>/     training checkpoints, features and index
voices/<name>/             the finished voice used by the app
```
