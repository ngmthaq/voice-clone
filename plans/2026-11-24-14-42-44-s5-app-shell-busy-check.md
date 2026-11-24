# Title: Plan — S5 App shell asks controllers about running work

- Classification: feature
- Description: Screens expose their controller, all three controllers have `busy_message`, and `VoiceCloneApp` asks the controllers, not the screens.

---

## Approach Summary / Goal

- Add a small `BusyReporter` Protocol (`runtime_checkable`, one read-only `busy_message: str | None` property) in `controllers/busy_reporter.py`. All three controllers already match it once `TrainController` gets `busy_message`.
- `MainScreen`, `SetupScreen` and `TrainScreen` get a public `controller` property. `TrainScreen` returns the `TrainPanelWidget`'s controller through a new `controller` property on the panel. The screens' own `busy_message` properties are removed.
- `VoiceCloneApp._busy_message` walks `screen_stack` from the top. For each screen whose `controller` is a `BusyReporter`, it returns the first non-empty `busy_message`. `_confirmed` keeps the same logic and texts.
- Goal: the app shell has no screen logic. The busy check can be tested without screens, and behavior stays the same.

## Functional Requirements

- `TrainController.busy_message` returns `"Training is running."` while `running` is true. Otherwise it returns `None`.
- `ChangerController`, `SetupController` and `TrainController` all pass `isinstance(c, BusyReporter)`.
- `VoiceCloneApp._busy_message` reads `controller.busy_message`, never `screen.busy_message`.
- Quit/restart: when busy, the first press shows `"{busy} Press {q|r} again to stop it and {quit|restart}."` and a second press within 3 s goes ahead. When idle, the app quits or restarts on the first press.
- `TrainScreen.action_back` works the same as before.

## Non-Functional Requirements

- No change to texts, key bindings, or timing.
- `controllers/busy_reporter.py` has no Textual import.
- Follows `CODING_CONVENTIONS.md` (type hints, no comments or docstrings in new code). `pytest` and `ruff check .` pass.

## Files in Scope

- Create: `src/voice_clone/controllers/busy_reporter.py`, `tests/views/test_app.py`
- Change: `src/voice_clone/controllers/__init__.py`, `src/voice_clone/controllers/train_controller.py`, `src/voice_clone/views/app.py`, `src/voice_clone/views/main_screen.py`, `src/voice_clone/views/setup_screen.py`, `src/voice_clone/views/train_screen.py`, `src/voice_clone/views/train_panel_widget.py`, `tests/controllers/test_train_controller.py`
- Docs: `plans/2026-11-24-refactor-codebase-to-mvc-overview.md`, `plans/2026-11-24-app-shell-busy-check-story.md`, and the `controllers/` row in `.claude/references/PROJECT_OVERVIEW.md` if it lists the controller files

## Risks & Assumptions

- Assumption: the existing docstring on `_confirmed` stays. Only its wording about "screen is busy" may change to "work is running".
- Risk: `TrainScreen.controller` uses `query_one`, which only works after the screen is composed. Today's `busy_message` has the same limit, so nothing changes.
- Risk: a `runtime_checkable` Protocol only checks that the attribute exists, not its type. That is enough here.

## Open Questions / Blockers

- None

## Status

- [x] Ready to execute
- [ ] Blocked

## Task List

| # | Status | Task | Responsible Role | Dependencies | Acceptance Criteria | Skills |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | DONE | S5.1: create `controllers/busy_reporter.py` with `BusyReporter` Protocol and export it from `controllers/__init__.py`. Add `TrainController.busy_message`. | developer | none | No `textual` import in the new file. `isinstance(TrainController(), BusyReporter)` is true. `ruff check src` passes. | `.claude/guides/CLEAN_CODE/ENTRY_POINT.md` |
| 2 | DONE | S5.2: add a `controller` property to `MainScreen`, `SetupScreen`, `TrainPanelWidget`, `TrainScreen`. Remove the screens' `busy_message`. Change `VoiceCloneApp._busy_message` to ask controllers. | developer | task 1 | `grep -rn busy_message src/voice_clone/views` only finds `app.py`, and there it reads `controller.busy_message`. `python -m voice_clone --help` works. `ruff check src` passes. | `.claude/guides/CLEAN_CODE/ENTRY_POINT.md` |
| 3 | DONE | S5.3: add `TrainController.busy_message` tests (idle → None, running → text). Add `tests/views/test_app.py`: idle `q` quits on first press; busy (fake `BusyReporter` controller on a pushed screen) `q`/`r` first press warns with the exact text and does not exit, second press exits with `None`/`"restart"`; a screen with no controller is skipped. | tester | task 2 | `pytest` and `ruff check .` pass. Every S5 acceptance criterion has a passing test. Existing tests are unchanged and pass. | `.claude/agents/party-mode-tester.md#testing-workflow`, `.claude/guides/AAA_TESTING.md` |
| 4 | DONE | Update docs: overview S5 → ✅ Done with counts (Done 5, Not started 0); tick S5 story criteria. | developer | review passed | Overview and story show S5 done. | — |

After task 3, I review the work against the S5 acceptance criteria and run `graphify update .`.
