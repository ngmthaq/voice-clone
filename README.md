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

### Keep your voice in a GitHub Release

Voice files are too big for git (the `.index` file is often near GitHub's 100 MB limit) and `voices/` is in `.gitignore`. To move a voice between computers, upload it once as a release asset. Use a **private** repo: anyone who has your model can sound like you.

```bash
gh repo create your-name/your-voices-repo --private
gh api -X PUT repos/your-name/your-voices-repo/contents/README.md -f message="Initial commit" -f content="$(printf '# Voices\n' | base64)"
gh release create voice-my-voice-v1 voices/my-voice/my-voice.pth voices/my-voice/my-voice.index --repo your-name/your-voices-repo --title "my-voice v1" --notes "RVC voice model"
```

The second command adds a first commit, because GitHub cannot create a release in an empty repo. After you retrain, replace the files with `gh release upload voice-my-voice-v1 <files> --clobber --repo your-name/your-voices-repo`.

To get the voice on another computer, pick one of these. Each one ends with the files in `voices/my-voice/`.

**In the browser.** Open the release page on GitHub while signed in, download `my-voice.pth` and `my-voice.index` from **Assets**, and copy them into `voices/my-voice/`.

**With the GitHub CLI.** Run `gh auth login` once, then:

```bash
gh release download voice-my-voice-v1 --repo your-name/your-voices-repo --dir voices/my-voice
```

**With curl (no GitHub CLI).** Create a [fine-grained personal access token](https://github.com/settings/personal-access-tokens/new) with read-only **Contents** access to the voices repo, then run this in a macOS or Linux terminal (or Git Bash on Windows):

```bash
TOKEN=github_pat_your_token
REPO=your-name/your-voices-repo
TAG=voice-my-voice-v1
mkdir -p voices/my-voice
curl -fsSL -H "Authorization: Bearer $TOKEN" "https://api.github.com/repos/$REPO/releases/tags/$TAG" \
  | python3 -c 'import json, sys; [print(a["id"], a["name"]) for a in json.load(sys.stdin)["assets"]]' \
  | while read -r id name; do
      curl -fL -H "Authorization: Bearer $TOKEN" -H "Accept: application/octet-stream" \
        -o "voices/my-voice/$name" "https://api.github.com/repos/$REPO/releases/assets/$id"
    done
```

The `Accept: application/octet-stream` header makes GitHub send the file itself instead of its details. For a public repo you can skip the token and download each file directly: `curl -fL -o voices/my-voice/my-voice.pth https://github.com/$REPO/releases/download/$TAG/my-voice.pth`.

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

1. On the **Simple** tab, pick your microphone, the output device (BlackHole 2ch or CABLE Input), and a voice.
2. Set the pitch with `-` and `+` (in semitones, -12 to +12).
3. Press Start (or the space bar). Loading the voice can take about 30 seconds the first time.
4. In Zoom, Discord or any other app, choose "BlackHole 2ch" (macOS) or "CABLE Output" (Windows) as the microphone.

Use headphones, so the converted voice does not feed back into your microphone.

While the voice is running, all settings are locked. Press Stop to change them, then Start again.

Keys: `space` start or stop, `q` quit. Your choices are saved and restored on the next start.

### Make the voice match better

"Index voice" is on the **Simple** tab. The other settings are on the **Advanced** tab, with the noise gate. Change one at a time: Stop, change it, Start, and listen.

| Setting | Default | What it does |
| --- | --- | --- |
| Index voice (%) | 50 | How much of the trained voice (the `.index` file) to use. Higher sounds more like the voice but less clear. Needs a `.index` file. |
| Protect consonants (%) | 67 | Keeps consonants (s, t, k, ch) from your live voice, so words stay clear when Index is high. 0 = off. |
| Follow mic volume (%) | 50 | 0 = the model sets the volume. 100 = the output gets louder and quieter the way you speak. |
| Pitch smoothing (ms) | 30 | Removes short pitch jumps that sound like a wobble. 0 = off. |
| Context (ms) | 1000 | How much earlier audio the model hears. More gives clearer words and adds no delay, but needs more CPU/GPU. If the log says blocks were dropped, lower it. |

The defaults are a good place to start. If the voice should sound more like the trained voice, raise Index to 75. On a fast computer, try Context 1500. On the Advanced tab, "Reset voice match to defaults" puts the four advanced settings back (Index voice keeps its value).

## Logs

The app never prints to the terminal. Logs are written to the user log folder:

- macOS: `~/Library/Logs/voice-clone/voice-clone.log`
- Windows: `%LOCALAPPDATA%\voice-clone\Logs\voice-clone.log`

## Responsible use

Only use voices you have the right to use. Do not use this tool to pretend to be someone else without their permission.

## Licenses

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
