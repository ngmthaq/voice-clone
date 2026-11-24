# PROJECT OVERVIEW

---

- **Project Name**: `voice-clone`
- **Project Description**: `A Python terminal (TUI) app that takes live voice from a real microphone, changes it to a chosen voice with a local RVC model, and sends it to a virtual audio device in real time, so other apps (Zoom, Discord, OBS, …) can use it as a microphone. It can also train new voices with Applio.`
- **Programming Languages**: `Python 3.12` (`>=3.12,<3.13`; Applio training uses 3.12 too)
- **Frameworks**: `Textual (TUI), PyTorch 2.5.1 (model inference)`
- **Package Managers**: `pip` + `venv` (no lock file; build backend is hatchling)
- **Key Libraries**: `textual, torch / torchaudio, sounddevice, numpy, soxr (resampling), scipy, librosa, faiss-cpu (RVC index), transformers, huggingface_hub (base model download), pydantic (settings), platformdirs, tomli / tomli-w, soundfile, pytest, ruff`
- **Database**: `None — settings are a TOML file; voices and models are plain files`
- **Doc Directory**: `/plans`
- **Testing Workflow**: `Code-First` <!-- Code-First | Test-First | Skip-Testing -->
- **Playwright Check**: `None` <!-- Always | None | Ask-User -->

> Note: DO NOT change the list format above. Only fill in the values.

## Additional Information

### How to run

| Task | Command |
| --- | --- |
| Install | `python3.12 -m venv .venv`, activate it, then `pip install -e ".[dev]"` |
| Start the app | `python -m voice_clone run` (or `voice-clone run`) |
| Train a voice | `python -m voice_clone train ...` |
| Measure speed | `python -m voice_clone bench ...` |
| Test | `pytest` |
| Lint / format | `ruff check .` / `ruff format .` |

- Windows with NVIDIA: install the CUDA build of torch **before** `pip install -e .` (see `docs/INSTALL.md`).

### Main parts (`src/voice_clone/`)

| Folder / file | Job |
| --- | --- |
| `cli.py`, `__main__.py` | Commands: `run`, `train`, `bench` |
| `views/` | Textual `app.py`, screens (`HomeScreen`, `MainScreen`, `SetupScreen`, `TrainScreen`), widgets, `app.tcss` |
| `controllers/` | Screen logic with no Textual code. `ChangerController` runs the voice changer. `SetupController` runs the setup checks, downloads, Applio install, speed test, and the `bench` command logic. `TrainController` checks the training form, runs training for the Train screen and the `train` command, and saves the last-used training settings. All three have a `busy_message` (the `BusyReporter` protocol), which the app shell asks before it quits or restarts. Views only show their state |
| `domain/audio/` | Device list, `ConversionPipeline`, `NoiseGate`, `RingBuffer` |
| `domain/engine/` | `RvcEngine`, torch device choice, base model download. `domain/engine/vendor/` is copied RVC code (not linted) |
| `domain/profiles/` | Find voices in `voices/` |
| `domain/training/` | Applio setup (pinned to 3.7.1 by commit), dataset prep, training runner |
| `domain/config.py` | `Settings` (pydantic) and performance presets |
| `domain/setup_check.py` | "Check setup": finds missing parts, downloads base models |
| `domain/bench.py` | Speed test ("Measure speed") |

### Target platforms

| OS | GPU backend | Virtual output device |
| --- | --- | --- |
| macOS | PyTorch MPS (Apple Silicon) | BlackHole 2ch |
| Windows | PyTorch CUDA (NVIDIA) | VB-CABLE (`CABLE Input`) |
| Both | CPU fallback (slow) | — |

### Audio pipeline (real time)

1. `sounddevice` reads the mic in blocks.
2. A worker thread runs the RVC engine on each block (with context, crossfade, noise gate, hum filter).
3. `sounddevice` writes the result to the virtual output device.

### Files and folders

- `voices/`, `models/`, `training/` live in the current folder. They are not in git.
- Settings (`settings.toml`) and logs (`voice-clone.log`) live in the user config / log folders (`platformdirs`).
- User guides are in `docs/`. A Kaggle notebook for GPU speed tests is in `tools/`.
- `graphify-out/` holds the code knowledge graph (code only, no docs).
