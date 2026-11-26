# Title: Plan — One automatic run script

- Classification: feature
- Description: `scripts/run.sh` and `scripts/run.ps1` install the app, download all models, measure speed the first time, and start the app, with no questions. The install scripts are removed.

---

## Approach Summary / Goal

- Each run script does four steps in order: install if needed, download the models, measure speed the first time only, start the app. The steps already done are fast no-ops: the install stamp, files already downloaded, Applio's own ready marker, and the `speed_measured` flag.
- The speed test logic stays in Python. A new `measure-speed` CLI command uses the same code as the **Measure speed** button. A new `speed_measured` setting records that it ran.
- Goal: a user runs one command on a fresh clone and ends up in the app with the models ready and the Performance dropdown set for this computer.

## Functional Requirements

**Python**
- `Settings.speed_measured: bool = False`, a new field in `src/voice_clone/domain/config.py`. Old `settings.toml` files without it load as `False`.
- `measure_and_save()` in `src/voice_clone/domain/bench.py`:
  - If a preset fits: save it (as today) and set `speed_measured = True`.
  - If no preset fits: save the **lightest** preset, set `speed_measured = True`, and return `best = None` so the caller can warn.
  - If it raises (no voice, missing models): save nothing, and the flag stays `False`.
  - The **Measure speed** button uses the same function, so it also sets the flag and saves the lightest preset when nothing fits. Its message text stays the same.
- New CLI command `voice-clone measure-speed`, through a `SetupController` method:
  - It prints one line per preset tested and then the result message.
  - Exit 0 on success, including the "too slow" case, which prints a warning.
  - Exit 1 on error (`Error: ...`), and 130 on Ctrl+C.
  - The `--if-needed` option exits 0 at once, printing nothing, when `speed_measured` is already `True`.
  - When base models or voices are missing, it prints "Speed test skipped: …" and exits 1. The run script shows the note and goes on.
- `download-models` and `install-applio` stay as they are. Applio already skips when it is installed.

**`scripts/run.sh` and `scripts/run.ps1`, no arguments**
1. `cd` (bash) or `Push-Location` (PowerShell) to the project root. Any argument → usage message and exit 2. `--help` → usage and exit 0.
2. Find Python 3.12, as today. If it is missing, stop with an install hint and exit 1.
3. `.venv`:
   - If it is missing, make it.
   - If it is not Python 3.12, print a note, delete it, and make it again.
4. Install when the stamp `.venv/.voice-clone-install` is missing, or holds a different SHA-256 hash of `pyproject.toml`:
   - Upgrade pip.
   - Windows only: install CUDA torch (cu124) first when `nvidia-smi` works, then print `torch.cuda.is_available()`.
   - Run `pip install -e .`.
   - Write the stamp only after all of this works. Any failure stops the script with exit 1.
5. `python -m voice_clone download-models`. On failure: warn and go on.
6. `python -m voice_clone install-applio`. If `git` is missing, skip with a warning. On failure: warn and go on.
7. `python -m voice_clone measure-speed --if-needed`. On a non-zero exit: print "Speed test skipped, it will try again next time" and go on.
8. Prerequisite warnings (BlackHole or VB-CABLE, `ffmpeg`, `git`), only on a run that installed.
9. Start the app with `python -m voice_clone run`. The script exits with the app's exit code.
- Delete `scripts/install.sh` and `scripts/install.ps1`.

**Docs**
- `docs/INSTALL.md`: replace the "Quick install with scripts" section with "Install and start with one script". Describe the four steps, the first run (large downloads plus the speed test of up to a minute), and how to install again (delete `.venv/.voice-clone-install`, or the whole `.venv`). Remove the questions table. The manual blocks stay.
- `README.md` quick start: step 1 is the prerequisites, step 2 is `scripts/run.sh` / `scripts\run.ps1`.
- `docs/TRAINING.md`: change the `run.sh install-applio` mention. Applio is now installed by the run script, and by hand with `python -m voice_clone install-applio` after you activate `.venv`.
- `docs/USAGE.md` "Measure the speed": the run script does this the first time, `python -m voice_clone measure-speed` runs it again, and `speed_measured` is in the settings file.

## Non-Functional Requirements

- Same script rules as before: bash 3.2, `set -euo pipefail`, quoted paths, shellcheck clean. PowerShell 5.1, ASCII + CRLF, `try/finally` around `Pop-Location`, `$LASTEXITCODE` checks.
- Python follows the project style, uses lazy imports in `cli.py`, and keeps the logic in the controller.
- A second run with nothing to do starts the app within a few seconds, with no pip, no downloads, and no speed test.

## Files in Scope

- `src/voice_clone/domain/config.py`, `src/voice_clone/domain/bench.py`, `src/voice_clone/controllers/setup_controller.py`, `src/voice_clone/cli.py` (changed)
- `scripts/run.sh`, `scripts/run.ps1` (rewritten)
- `scripts/install.sh`, `scripts/install.ps1` (deleted)
- `tests/test_cli.py`, `tests/controllers/test_setup_controller.py`, plus the existing bench/config test files that cover `measure_and_save` (changed)
- `docs/INSTALL.md`, `docs/USAGE.md`, `docs/TRAINING.md`, `README.md` (changed)

## Risks & Assumptions

- **The first run is long and big:** about 2.5 GB of CUDA torch on Windows, 560 MB of base models, and several GB of Applio. The user chose this ("install all models").
- When no preset fits, the Measure speed button now also saves the lightest preset. Today it saves nothing. I assume the user wants the button and the script to behave the same.
- The script takes no arguments now, so `run.sh train ...` no longer works. The CLI commands still work after `source .venv/bin/activate`. The docs will say so.
- The `.ps1` script still cannot be run here. Please test it on Windows.
- If the user stops the script (Ctrl+C) during the speed test, the app does not start. The script exits 130.

## Open Questions / Blockers

- None.

## Status

- [x] Ready to execute
- [ ] Blocked — requires user input on: —

## Task List

| # | Status | Task | Responsible Role | Dependencies | Acceptance Criteria | Skills |
| - | ------ | ---- | ---------------- | ------------ | ------------------- | ------ |
| 1 | TODO | Add `speed_measured` to `Settings`. Change `measure_and_save` (flag, lightest-on-fail). Add the `measure-speed [--if-needed]` CLI command and its controller method | developer | none | Behaviour as above. `ruff` passes. Existing `pytest` passes, or existing tests are changed only where the planned behaviour changed (reported) | `guides/CLEAN_CODE/ENTRY_POINT.md` |
| 2 | TODO | Rewrite `run.sh` / `run.ps1` (steps 1–9). Delete `install.sh` / `install.ps1` | developer | task 1 | `shellcheck` is clean. Stubbed test: the first run does every step in order. The second run skips the install, and the speed test is skipped through `--if-needed`. A failed download or speed test still starts the app. An argument gives exit 2 | `guides/CLEAN_CODE/ENTRY_POINT.md` |
| 3 | TODO | Update `INSTALL.md`, `README.md`, `TRAINING.md`, `USAGE.md` | developer | tasks 1, 2 | No mention of `install.sh`, `install.ps1`, the questions, or `run.sh <args>` is left. The steps and the re-install hint are documented | `references/AGENT_RULES.md` |
| 4 | TODO | Tests: `measure_and_save` (sets the flag; lightest when none fits; no save on error), the `speed_measured` default and old-file load, `measure-speed` CLI (0, 0 with warning, 1, 130, `--if-needed` skip) | tester | task 1 | New tests pass, follow AAA, and use mocks. The full `pytest` passes | `guides/AAA_TESTING.md` |
