# Title: Plan — Friendlier prerequisite messages

- Classification: feature
- Description: The run scripts show one status line per prerequisite (already installed / missing / installed / could not be installed), with friendlier wording.

## Example output (macOS, git already there)

```text
Checking what voice-clone needs...
  ✓ git is already installed
  ✗ Python 3.12 is missing
  ✗ ffmpeg is missing
  ✗ BlackHole 2ch is missing

Some things are missing. Install them now? [Y/n]

Installing Python 3.12...
  ✓ Python 3.12 installed
Installing ffmpeg...
  ✓ ffmpeg installed
Installing BlackHole 2ch (your Mac may ask for your password)...
  ✓ BlackHole 2ch installed
  Tip: if BlackHole 2ch does not show up in your apps, restart your Mac.

✓ Everything voice-clone needs is ready.
```

If an install fails: `✗ ffmpeg could not be installed. You can try later with: brew install ffmpeg`.

When nothing is missing, it prints a single line: `✓ Everything voice-clone needs is ready.`

## Functional Requirements

- The check prints one line for each item (Python 3.12, git, ffmpeg, BlackHole 2ch or VB-CABLE): `✓ <name> is already installed` or `✗ <name> is missing`.
- The question becomes `Some things are missing. Install them now? [Y/n]`.
- Each install prints `Installing <name>...`, then `✓ <name> installed` or `✗ <name> could not be installed. You can try later with: <command>`.
- The password and admin hints sit on the "Installing" line: "your Mac may ask for your password" or "Windows will ask for permission".
- The restart note becomes a `Tip:` line.
- At the end of the check: `✓ Everything voice-clone needs is ready.` If an item is still missing, the script prints a short list of what is still missing instead.
- With No, or with no terminal, the behaviour is the same as now. Only the wording changes.
- Symbols: `run.sh` uses ✓ and ✗. `run.ps1` must stay ASCII (PowerShell 5.1 can read a non-ASCII file wrongly), so it uses `[OK]` and `[X]` and shows them in green and red.

## Files in Scope

- `scripts/run.sh`, `scripts/run.ps1`. Also `docs/INSTALL.md`, only if it quotes the old message text.

## Risks & Assumptions

- In `run.sh`, ✓ and ✗ need a UTF-8 terminal. The macOS Terminal is UTF-8 by default.
- No behaviour change, and no Python change.

## Task List

| # | Status | Task | Responsible Role | Dependencies | Acceptance Criteria | Skills |
| - | ------ | ---- | ---------------- | ------------ | ------------------- | ------ |
| 1 | TODO | Change the messages in `run.sh` as above | developer | none | `shellcheck` clean. A stub test shows the per-item lines, the install success and failure lines, and the final line | `guides/CLEAN_CODE/ENTRY_POINT.md` |
| 2 | TODO | Same change in `run.ps1` with `[OK]` and `[X]` | developer | none | ASCII + CRLF, checked by reading | `guides/CLEAN_CODE/ENTRY_POINT.md` |
