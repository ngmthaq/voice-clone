# PROJECT OVERVIEW

---

- **Project Name**: `voice-clone`
- **Project Description**: `A Python TUI app that takes live voice from a real microphone, changes it to a selected voice profile with a local AI model (RVC), and sends it to a virtual audio device in real time, so other apps (Zoom, Discord, OBS, …) can use it as a microphone.`
- **Programming Languages**: `Python 3.10+`
- **Frameworks**: `Textual (TUI), PyTorch (model inference)`
- **Package Managers**: `uv`
- **Key Libraries**: `textual, torch, sounddevice, numpy, librosa / torchaudio (resampling), faiss-cpu (RVC index), pydantic (settings), pytest`
- **Database**: `None — voice profiles and settings are plain files`
- **Doc Directory**: `/plans`
- **Testing Workflow**: `Code-First` <!-- Code-First | Test-First | Skip-Testing -->
- **Playwright Check**: `None` <!-- Always | None | Ask-User -->

> Note: DO NOT change the list format above. Only fill in the values.

## Additional Information

### Status

- New project. The repo was empty at onboarding (2026-11-16). No code yet.

### Target platforms

| OS      | GPU backend                 | Virtual output device         |
| ------- | --------------------------- | ----------------------------- |
| macOS   | PyTorch MPS (Apple Silicon) | BlackHole 2ch                 |
| Windows | PyTorch CUDA (NVIDIA)       | VB-Audio Virtual Cable        |
| Both    | CPU fallback (slow)         | —                             |

- The user installs the virtual audio driver once. The app finds it by device name.
- Pick the torch device at start: `cuda` → `mps` → `cpu`.

### Audio pipeline (real time)

1. **Input**: `sounddevice` reads the real microphone in small blocks.
2. **Convert**: the RVC engine changes each block to the selected voice profile (pitch shift is a setting).
3. **Output**: `sounddevice` writes the result to the virtual output device.
4. Other apps select the virtual device as their microphone.

- Keep the audio callback fast. Run model inference in a worker thread, not in the callback and not in the Textual UI thread.
- Use a ring buffer (a fixed-size queue that overwrites old data) with crossfade between blocks to avoid clicks.
- Target end-to-end delay: under ~300 ms.

### Voice profiles

- RVC profile = one trained `.pth` model file + an optional `.index` file.
- Profiles live in a `voices/` folder (one sub-folder per profile). Do not commit model files to git.
- Shared base models (e.g. HuBERT / ContentVec, RMVPE pitch model) are downloaded once to a `models/` folder.

### TUI features (planned)

- Select input mic, output device, and voice profile.
- Start / stop conversion. Live input/output level meters and delay readout.
- Settings: pitch shift, block size, index rate, noise gate.
