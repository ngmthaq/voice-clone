# voice-clone

Change your voice in real time. voice-clone listens to your microphone, converts your voice with an RVC voice model, and sends the result to a virtual audio device. Apps like Zoom or Discord can then use that device as a microphone.

It runs in the terminal (a Textual TUI).

## Quick start

1. **Install** the prerequisites (Python, and BlackHole on macOS or VB-CABLE on Windows) and the app: follow [docs/INSTALL.md](docs/INSTALL.md) for your computer.

2. **Run** the app and pick **Voice changer** or **Train a voice**:

   ```bash
   python -m voice_clone run
   ```

3. **Get a voice:** train one from 10–30 minutes of your recordings ([docs/TRAINING.md](docs/TRAINING.md)), or add RVC voice files you already have ([docs/VOICES.md](docs/VOICES.md)).

4. **Change your voice:** pick your microphone, the output device (BlackHole 2ch on macOS, CABLE Input on Windows) and the voice, then press Start. In Zoom or Discord, choose BlackHole 2ch (macOS) or CABLE Output (Windows) as the microphone ([docs/USAGE.md](docs/USAGE.md)).

## Documentation

| Guide | What is in it |
| --- | --- |
| [INSTALL.md](docs/INSTALL.md) | Prerequisites, install on macOS and Windows (with or without an NVIDIA card), first start |
| [USAGE.md](docs/USAGE.md) | Change your voice, keys, settings that make the voice match better, logs |
| [TRAINING.md](docs/TRAINING.md) | Record and train your own voice, in the app or with a command; options and troubleshooting |
| [READING_SCRIPT.md](docs/READING_SCRIPT.md) | A text to read aloud while you record (about 12–15 minutes) |
| [VOICES.md](docs/VOICES.md) | Voice files, adding a voice you already have, moving voices between computers with a GitHub Release |

## Responsible use

Only use voices you have the right to use. Do not use this tool to pretend to be someone else without their permission.

## Licenses

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
