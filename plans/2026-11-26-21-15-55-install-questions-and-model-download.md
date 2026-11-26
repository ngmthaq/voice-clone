# Title: Plan — Install scripts ask questions; download models and Applio

- Classification: feature
- Description: The install scripts ask questions with default answers (no flags). Two new CLI commands let the scripts download the base models and install Applio.

---

## Approach Summary / Goal

- The download and install logic stays in Python, where it already lives. I add two small CLI commands, `download-models` and `install-applio`, which use the same code as the "Check setup" screen. The scripts call them through the `.venv` Python. Users can also run them later, for example `scripts/run.sh download-models`.
- `install.sh` / `install.ps1` drop all flags. They ask up to five questions. Each question shows its default, and pressing Enter keeps the default.
- When input is not a terminal (CI, piped input), the scripts use every default and print the answers they chose.
- Goal: a new user runs one script, presses Enter a few times, and gets a working app with base models.

## Functional Requirements

**CLI (Python)**
- `voice-clone download-models`: calls `ensure_base_models(models_dir(), progress)` through `SetupController.download`. It prints each progress message on its own line. It exits 0 on success, 1 on error (with `Error: ...`), and 130 on Ctrl+C. Files already there are skipped, which the existing code already does.
- `voice-clone install-applio`: installs Applio into `training/.applio` with `Applio(...).ensure_installed(report=print)`. It uses the default (non-streaming) runner, so Applio's output goes straight to the terminal. Exit codes are the same as above. The logic goes in `SetupController` (for example `install_applio_cli(report)`), so `cli.py` only handles parsing and printing, like `bench` and `train`.

**Questions in both install scripts, in this order**

| # | Question | Default | When asked |
| - | -------- | ------- | ---------- |
| 1 | `.venv` is not Python 3.12 (found X). Delete it and make it again? [y/N] | No → stop with a message, exit 1 | Only when `.venv` exists and is not 3.12 |
| 2 | Install the NVIDIA (CUDA) build of PyTorch? | `[Y/n]` if `nvidia-smi` works, otherwise `[y/N]` | `install.ps1` only |
| 3 | Install development tools (pytest, ruff)? [y/N] | No | Always |
| 4 | Download the base models now (about 560 MB)? [Y/n] | Yes | Always |
| 5 | Install Applio for voice training now (several GB)? [y/N] | No | Always |

- All questions are asked **before** any install work starts, so the user can walk away after answering.
- Answers accept `y`, `yes`, `n` and `no`, in any case. Empty means the default. Any other answer asks again.
- No terminal: bash checks `[ -t 0 ]`. PowerShell checks `[Console]::IsInputRedirected` or `-not [Environment]::UserInteractive`. Each default is then printed as `Question ... -> default`.
- Step order: venv → pip upgrade → torch (CUDA, Windows) → `pip install -e .` / `.[dev]` → `download-models` → `install-applio` → prerequisite warnings → done.
- If the model download or the Applio install fails, the script prints a warning with the command to retry (`scripts/run.sh download-models` or `install-applio`, or the Check setup screen). It still finishes with exit code 0.
- If the user says yes to Applio but `git` is missing, the script skips Applio with a warning instead of failing.
- `install.sh --help` and any other argument: print a short usage ("This script asks questions, it takes no options") and exit (0 for `--help`, 2 for anything else). `install.ps1` takes no parameters.
- `run.sh` / `run.ps1` stay as they are.

**Docs**
- `docs/INSTALL.md`: replace the flags tables with the list of questions and their defaults. Explain that piped or CI runs use the defaults. Add `download-models` and `install-applio` to the run examples.
- `docs/TRAINING.md`: mention `install-applio` next to the "Install Applio" button, if the doc talks about it.
- `README.md`: no change unless it names flags.

## Non-Functional Requirements

- Same rules as before: bash 3.2 safe, `set -euo pipefail`, quoted paths, shellcheck clean. PowerShell 5.1, `Push-Location`/`Pop-Location` in `try/finally`, ASCII with CRLF.
- One small `ask_yes_no` helper per script. No repeated prompt code.
- Python follows the project style (ruff, no comments that repeat the code). Lazy imports in `cli.py`, like the other commands.

## Files in Scope

- `src/voice_clone/cli.py` (changed)
- `src/voice_clone/controllers/setup_controller.py` (changed)
- `tests/test_cli.py`, `tests/controllers/test_setup_controller.py` (changed; the second file is created if it does not exist)
- `scripts/install.sh`, `scripts/install.ps1` (changed)
- `docs/INSTALL.md`, `docs/TRAINING.md`, `README.md` (changed if needed)

## Risks & Assumptions

- Removing the flags means you can no longer pick an answer without typing. Piped or CI runs always get the defaults, so they never install CUDA torch unless `nvidia-smi` works, never install dev tools, and never install Applio. You chose this.
- `.ps1` still cannot be run here (no `pwsh`), so it is checked by reading only. Please test on Windows.
- Applio's `ensure_installed` needs `git` and Python 3.12. The CLI reports its own error if something is missing. The script also checks `git` first.
- A real download and a real Applio install are not run in checks. Tests mock `ensure_base_models` and `Applio`.

## Open Questions / Blockers

- None.

## Status

- [x] Ready to execute
- [ ] Blocked — requires user input on: —

## Task List

| # | Status | Task | Responsible Role | Dependencies | Acceptance Criteria | Skills |
| - | ------ | ---- | ---------------- | ------------ | ------------------- | ------ |
| 1 | TODO | Add `download-models` and `install-applio` to `cli.py`, with the controller method in `setup_controller.py` | developer | none | `voice-clone --help` lists both commands. Exit codes are 0, 1 and 130 as specified. `ruff check` and `ruff format --check` pass. Existing `pytest` passes | `guides/CLEAN_CODE/ENTRY_POINT.md` |
| 2 | TODO | Rewrite `install.sh` and `install.ps1` to ask questions 1–5 with defaults, with no flags, the no-terminal fallback, and the step order and failure rules above | developer | task 1 | `shellcheck` is clean. Piped input (`</dev/null`) uses the defaults and prints them. `--help` exits 0, an unknown argument exits 2. `.ps1` is ASCII with CRLF, and the location is restored | `guides/CLEAN_CODE/ENTRY_POINT.md` |
| 3 | TODO | Update `docs/INSTALL.md` (and `TRAINING.md`/`README.md` if needed) | developer | tasks 1, 2 | No old flags are named anywhere. The questions and defaults are listed. The new commands are documented | `references/AGENT_RULES.md` |
| 4 | TODO | Tests for the two CLI commands: success, `VoiceCloneError` → 1, `KeyboardInterrupt` → 130, progress printed; controller method test | tester | task 1 | New tests pass, follow the AAA pattern, and use mocks (no network). The full `pytest` run passes | `guides/AAA_TESTING.md` |
