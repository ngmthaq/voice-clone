# Title: Plan — Run scripts install the prerequisites

- Classification: feature
- Description: Before the app install, `run.sh` / `run.ps1` find any missing prerequisites. They list them, ask one yes/no question, and install them with Homebrew (macOS) or winget plus the VB-CABLE setup (Windows).

---

## Approach Summary / Goal

- A new first step runs before the steps we have today. It checks for Python 3.12, git, ffmpeg, and the virtual audio device.
- If anything is missing, the script lists it and asks one question: `Install these now? [Y/n]`. The default is Yes, and with no terminal the answer is Yes. When nothing is missing, it asks nothing.
- macOS uses Homebrew, and installs it first if it is missing. Windows uses winget, plus the official VB-CABLE zip.
- Goal: a new computer with nothing installed gets to a working app with one script.

## Functional Requirements

**Find what is missing (both scripts)**
- **Python 3.12:** the same check as today (`python3.12`, or on Windows `py -3.12` and then `python3.12`).
- **git:** `git --version` must succeed. On macOS, `/usr/bin/git` can be a stand-in that only exists to offer the Xcode tools install, so the script runs `git --version` instead of only checking that the command exists.
- **ffmpeg:** found on `PATH`.
- **Audio device:** on macOS, `/Library/Audio/Plug-Ins/HAL/BlackHole2ch.driver` exists. On Windows, a `Win32_SoundDevice` has a name like `*CABLE*`.
- **The question:** the script prints the missing list and asks `Install these now? [Y/n]`. If the answer is No, the script keeps today's behaviour (it stops when Python is missing and warns for the rest).

**macOS (`run.sh`)**
- **Homebrew missing:**
  - Run the official installer: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`.
  - Then load brew into this shell with `eval "$(/opt/homebrew/bin/brew shellenv)"`, or the `/usr/local/bin/brew` path on Intel Macs.
  - If the Homebrew install fails, stop with a hint, because nothing else can be installed.
- **Installs:**
  - `brew install python@3.12`, plus `git` and `ffmpeg` as needed.
  - `brew install --cask blackhole-2ch`, which asks for the Mac password.
  - After BlackHole: `sudo killall coreaudiod`, so the audio system picks up the new device. Then print: "If BlackHole 2ch does not show up, restart the Mac."
- **Failures:** if Python fails, the script stops (exit 1). If git, ffmpeg or BlackHole fails, it prints a warning and goes on.

**Windows (`run.ps1`)**
- **winget missing:** if anything is missing and `winget` is not there, print how to get "App Installer" from the Microsoft Store. Then go on with today's behaviour.
- **Installs:**
  - `winget install --id <id> -e --silent --accept-source-agreements --accept-package-agreements`, with the ids `Python.Python.3.12`, `Git.Git` and `Gyan.FFmpeg`.
  - After each install, reload `$env:Path` from the Machine and User values, so the new tools work right away.
- **VB-CABLE:**
  1. Download `https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack46.zip` to a new temp folder.
  2. Unzip it with `Expand-Archive`.
  3. Find `VBCABLE_Setup_x64.exe` on 64-bit Windows, or `VBCABLE_Setup.exe` on 32-bit.
  4. Run it with `Start-Process -Verb RunAs -Wait`. Windows shows the admin prompt, and the user clicks Install in the driver setup.
  5. Print: "Restart Windows if CABLE Input does not show up."
  6. If the download or the setup fails, or the exe is not found: warn, open `https://vb-audio.com/Cable/`, and go on.
- **Failures:** same rules as macOS. Python stops the script, and the rest only warn.

**Remove the old warnings**
- The "X is not installed" warnings after install now appear only for items that are still missing (the user said No, or the install failed).

**Docs**
- `docs/INSTALL.md`: the prerequisites section says the run script can install them. It describes the one question, the password and admin prompts, the BlackHole and VB-CABLE restart note, and that Homebrew or winget is used. The manual instructions stay.
- `README.md` quick start step 1: the script installs the prerequisites too.

## Non-Functional Requirements

- Same script rules as before: bash 3.2, shellcheck clean, PowerShell 5.1, ASCII and CRLF.
- Keep the prerequisite code in its own functions (for example `find_missing`, `install_missing`), so the main flow stays easy to read.
- Never install anything without the yes answer (the default is Yes).

## Files in Scope

- `scripts/run.sh`, `scripts/run.ps1` (changed)
- `docs/INSTALL.md`, `README.md` (changed)

## Risks & Assumptions

- **The VB-CABLE URL is pinned to Pack46.** When VB-Audio releases a new version, the link may break. The script then opens the web page instead. The site publishes no checksum, so the download cannot be verified.
- The setup file names inside the zip (`VBCABLE_Setup_x64.exe`, `VBCABLE_Setup.exe`) are from my knowledge. The page does not list them. If they are different, the script falls back to the web page. Please check this on Windows.
- **Password and admin prompts cannot be skipped:** Homebrew, the BlackHole cask, `sudo killall coreaudiod`, the winget installers, and the VB-CABLE setup each ask. In CI (no terminal) these may fail. The script then warns and goes on, except for Python.
- The script accepts the winget source and package agreements for you through flags, after you answer Yes.
- Ruff and pytest are not affected. There is no Python change, so there are no new Python tests.
- Nothing here can be tested for real on this Mac without really installing things. The developer will test with fake `brew`, `git`, `ffmpeg` and `curl` commands. `run.ps1` is read only, so please test it on Windows.

## Open Questions / Blockers

- None.

## Status

- [x] Ready to execute

## Task List

| # | Status | Task | Responsible Role | Dependencies | Acceptance Criteria | Skills |
| - | ------ | ---- | ---------------- | ------------ | ------------------- | ------ |
| 1 | TODO | `run.sh`: find what is missing, ask one question, install Homebrew and the brew packages and cask, restart `coreaudiod` | developer | none | `shellcheck` clean. A stub test with fake `brew`, `curl`, `sudo`, `git` and `ffmpeg` shows: nothing missing → no question. Missing items → the list and the question. No → today's behaviour. Yes → the right brew commands in order. A Python install failure → exit 1 | `guides/CLEAN_CODE/ENTRY_POINT.md` |
| 2 | TODO | `run.ps1`: the same with winget, the PATH reload and the VB-CABLE download and setup | developer | none | ASCII and CRLF. Location restored. Every failure path warns, except Python. Checked by reading | `guides/CLEAN_CODE/ENTRY_POINT.md` |
| 3 | TODO | Update `docs/INSTALL.md` and `README.md` | developer | 1, 2 | The prerequisite install, the question, the prompts and the restart note are documented | `references/AGENT_RULES.md` |
