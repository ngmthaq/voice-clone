# Title: Plan — Add install and run scripts

- Classification: feature
- Description: Add `scripts/` with install and run scripts for macOS (bash) and Windows (PowerShell), and add them to the docs.

---

## Approach Summary / Goal

- The scripts do the same steps as `docs/INSTALL.md`, so users run one command instead of copying blocks by hand.
- `install.*` finds Python 3.12, makes `.venv` in the project root, installs torch (CUDA on Windows when an NVIDIA card is found), then runs `pip install -e .`, and warns about missing prerequisites.
- `run.*` uses `.venv`'s Python, so the user does not have to activate the venv first.
- Goal: a fresh clone works with `scripts/install.sh && scripts/run.sh` (or the `.ps1` scripts).

## Functional Requirements

- All scripts work from any current folder. They `cd` to the project root (the parent of `scripts/`).
- **install.sh** (macOS; Linux works on a best-effort basis):
  - Finds `python3.12`. If it is missing, it stops with a message that says how to install it (`brew install python@3.12`).
  - If `.venv` exists and its Python is not 3.12: stops with a message, unless `--force` is given, which deletes `.venv` and makes it again. If `.venv` exists with 3.12, it uses it.
  - Runs `pip install --upgrade pip`, then `pip install -e .`, or `pip install -e ".[dev]"` with `--dev`.
  - Warns (does not install) when BlackHole 2ch (`/Library/Audio/Plug-Ins/HAL/BlackHole2ch.driver`), `ffmpeg`, or `git` is missing.
  - `--help` prints the usage. An unknown flag prints the usage and exits with a non-zero code.
  - Ends with "Done. Start the app with scripts/run.sh".
- **install.ps1** (Windows PowerShell 5.1+):
  - Finds Python 3.12 with `py -3.12` first, then `python3.12`. If neither works, it stops with a message (python.org link).
  - `.venv` rules are the same as install.sh, with a `-Force` switch.
  - Torch: `-Cuda` or `-Cpu` overrides. Without either, it runs `nvidia-smi`. If that works, it installs `torch==2.5.1 torchaudio==2.5.1` from `https://download.pytorch.org/whl/cu124` **before** `pip install -e .`. After install, it prints whether `torch.cuda.is_available()` is `True`.
  - `-Dev` installs `.[dev]`.
  - Warns when VB-CABLE (no audio device with "CABLE" in its name), `ffmpeg`, or `git` is missing.
  - Stops on the first failed command, with a non-zero exit code.
- **run.sh / run.ps1**:
  - If `.venv` is missing, they stop with "Run scripts/install.sh first" (or `install.ps1`).
  - No arguments → `.venv` Python runs `-m voice_clone run`. With arguments → `-m voice_clone <args>`. Example: `run.sh train --help`.
  - The exit code is the app's exit code.
- **Docs**: `docs/INSTALL.md` gets a "Quick install with scripts" section before the manual blocks, with the flags listed. The manual blocks stay. `README.md` quick start steps 1–2 mention the scripts.

## Non-Functional Requirements

- bash scripts: `#!/usr/bin/env bash`, `set -euo pipefail`, executable bit set (`chmod +x`), quoted paths (the project lives under `/Volumes/...`, and paths may have spaces).
- PowerShell: `$ErrorActionPreference = 'Stop'`. Check `$LASTEXITCODE` after each native command. Use `param()` for switches.
- Messages use plain, short English. No comments beyond the ones the code needs.
- The `.ps1` files use CRLF-safe content. Add a `.gitattributes` rule (`*.sh text eol=lf`, `*.ps1 text eol=crlf`) so line endings stay correct on both systems.

## Files in Scope

- `scripts/install.sh` (new)
- `scripts/install.ps1` (new)
- `scripts/run.sh` (new)
- `scripts/run.ps1` (new)
- `.gitattributes` (new, or changed if it exists)
- `docs/INSTALL.md` (changed)
- `README.md` (changed)

## Risks & Assumptions

- I cannot run the `.ps1` scripts on this Mac unless `pwsh` is installed. If it is not, the Windows scripts are only checked by reading them. You will need to try them on Windows.
- The VB-CABLE check uses `Get-PnpDevice` / `Get-CimInstance Win32_SoundDevice`. On some systems it may give a false warning. It is a warning only, so it never stops the install.
- install.sh never installs CUDA torch (macOS has no NVIDIA). On Linux it installs the default torch from PyPI.
- No pytest tests: these are shell scripts and the project tests are Python only. The check is manual: `bash -n`, `shellcheck` if present, and a real run of `install.sh --help`, `run.sh --help`, and the `.venv` error paths.

## Open Questions / Blockers

- None.

## Status

- [x] Ready to execute
- [ ] Blocked — requires user input on: —

## Task List

| #   | Status | Task | Responsible Role | Dependencies | Acceptance Criteria | Skills |
| --- | ------ | ---- | ---------------- | ------------ | ------------------- | ------ |
| 1 | TODO | Write `scripts/install.sh` and `scripts/run.sh` (+ `chmod +x`) | developer | none | Meets the bash requirements above. `bash -n` passes. `--help` works. `run.sh` with no `.venv` prints the install hint and exits non-zero | `guides/CLEAN_CODE/ENTRY_POINT.md` |
| 2 | TODO | Write `scripts/install.ps1` and `scripts/run.ps1` | developer | none | Meets the PowerShell requirements above. Parses with no errors (`pwsh` parser check if `pwsh` is present) | `guides/CLEAN_CODE/ENTRY_POINT.md` |
| 3 | TODO | Add `.gitattributes` line-ending rules; update `docs/INSTALL.md` and `README.md` | developer | tasks 1, 2 | Docs list each script, each flag, and the run pass-through. The manual steps stay | `references/AGENT_RULES.md` (writing style) |
