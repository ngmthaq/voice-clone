# S4 — Train controller (Train screen + `train` command)

- **Epic:** [Refactor codebase to MVC — Overview](./2026-11-24-refactor-codebase-to-mvc-overview.md)
- **Story Points:** 5
- **Depends On:** S1 — [Move code into domain/ and views/](./2026-11-24-move-code-into-domain-views-story.md)

## User Story

As a `developer`, I want to `have the training logic in a controller` so that I can `have the Train screen and the train command use the same code`.

## Goal

**Problem:** `views/train_panel_widget.py` (340 lines) reads form fields, but it also builds `TrainOptions`, starts and stops the training runner, parses progress, and saves last-used settings. `cli.py` `_run_train` repeats part of this flow. The logic is only testable through the Textual app, and the two paths can drift apart.

**Solution:** Add `controllers/train_controller.py` with a `TrainController`. It checks options, starts and stops training, and sends progress events. `TrainPanelWidget` and the `train` command both use it.

**Impact:** One place for training logic. Plain pytest tests can cover it with a fake runner. The widget file gets smaller.

## Requirements

### Functional Requirements

- `TrainController` checks options, starts training, stops training, and sends progress and log events (today in `_read_options`, `_start`, `_train`, `_Event`).
- It loads and saves last-used training settings.
- `TrainPanelWidget` only reads form fields and shows controller state.
- `cli.py` `_run_train` uses the controller.

### Non-Functional Requirements

- No change in app behavior. Stop works the same way as today (same process kill rules from `domain/training/commands.py`).
- The `train` command keeps the same flags, output, and exit codes.
- The controller does not import Textual.
- The UI thread never waits on the training process.

## Acceptance Criteria

- [x] Given `controllers/train_controller.py`, when a test starts training with a fake runner, then it builds the same `TrainOptions` and runs the same steps as today.
- [x] Given a running training, when the user stops it, then the controller stops the runner the same way as today.
- [x] Given training output, when lines arrive, then the controller sends progress and log lines through a callback.
- [x] Given `python -m voice_clone train ...`, when it runs, then it uses the train controller with the same flags and output.
- [x] Given `TrainPanelWidget`, when I read it, then it only reads form fields and shows controller state.

## Tasks

| # | Task | Done when | Depends On |
| --- | --- | --- | --- |
| S4.1 | [BE] Create `TrainController` with options check, start, stop, and progress events (from `_read_options`, `_start`, `_train`, `_Event`) | Start/stop works from a test with a fake runner | — |
| S4.2 | [BE] Move last-used training settings load/save into the controller | Settings save from a test, same TOML output | S4.1 |
| S4.3 | [FE] Change `views/train_panel_widget.py` to use the controller | Widget has no `domain/training` calls | S4.1, S4.2 |
| S4.4 | [BE] Change `cli.py` `_run_train` to use the controller | `train` output and exit codes are the same | S4.1 |
| S4.5 | [QA] Add `tests/controllers/test_train_controller.py`; keep `test_train_screen.py` and `test_cli.py` passing | Every criterion above has a passing test | S4.3, S4.4 |

## Estimate

- **Points:** 5
- **Reason:** Medium effort (controller plus CLI wiring). Medium complexity: child process with streamed output. Medium uncertainty: stop behavior must stay the same.

## Out of Scope

- Any change to `domain/training/` logic (Applio setup, dataset prep, process runner).
- Any change to `train` command flags or output.
- The voice changer screen (S2), the Setup screen (S3), and the app quit check (S5).
