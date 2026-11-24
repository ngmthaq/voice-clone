# S3 — Setup controller (Setup screen + `bench` command)

- **Epic:** [Refactor codebase to MVC — Overview](./2026-11-24-refactor-codebase-to-mvc-overview.md)
- **Story Points:** 5
- **Depends On:** S1 — [Move code into domain/ and views/](./2026-11-24-move-code-into-domain-views-story.md)

## User Story

As a `developer`, I want to `have the setup check and speed test logic in a controller` so that I can `have the Setup screen and the bench command use the same code`.

## Goal

**Problem:** `views/setup_screen.py` runs the setup checks, downloads base models, installs Applio, and measures speed. It calls `domain/` code directly and keeps busy state in widgets. `cli.py` `_run_bench_command` repeats part of the speed test flow. The logic is only testable through the Textual app, and the two paths can drift apart.

**Solution:** Add `controllers/setup_controller.py` with a `SetupController`. It wraps `domain/setup_check.py`, `domain/bench.py`, base model download, and Applio install. `SetupScreen` and the `bench` command both use it.

**Impact:** One place for setup logic. Plain pytest tests can cover it. The Setup screen file gets smaller.

## Requirements

### Functional Requirements

- `SetupController` runs checks, downloads base models, installs Applio, measures speed, and stops running work (today in `_run_checks`, `_on_download`, and busy state in `SetupScreen`).
- It reports progress and log lines through a callback, not through widgets.
- `SetupScreen` has no direct calls to `domain/`.
- `cli.py` `_run_bench_command` uses the controller.

### Non-Functional Requirements

- No change in app behavior. The `bench` command prints the same output and returns the same exit codes.
- The controller does not import Textual.
- The UI thread never waits on downloads, installs, or speed tests.

## Acceptance Criteria

- [ ] Given `controllers/setup_controller.py`, when a test runs checks with fake facts, then it returns the same check list as today.
- [ ] Given the controller, when it downloads base models, installs Applio, or measures speed, then it reports progress through a callback, not widgets.
- [ ] Given `python -m voice_clone bench`, when it runs, then it uses the setup controller and prints the same output as before.
- [ ] Given `SetupScreen`, when I read it, then it has no direct calls to `domain/`.
- [ ] Given the app, when I use the Setup screen, then it works exactly as before.

## Tasks

| # | Task | Done when | Depends On |
| --- | --- | --- | --- |
| S3.1 | [BE] Create `SetupController` for run checks, download base models, install Applio, and stop (from `_run_checks`, `_on_download`, busy state) | Each action works from a test with fakes | — |
| S3.2 | [BE] Add measure-speed to the controller (wraps `domain/bench.py` `measure_and_save`) | Measure speed works from a test with `FakeEngine` | S3.1 |
| S3.3 | [FE] Change `views/setup_screen.py` to use the controller | `SetupScreen` has no `domain/` calls | S3.2 |
| S3.4 | [BE] Change `cli.py` `_run_bench_command` to use the controller | `bench` output is the same as before | S3.2 |
| S3.5 | [QA] Add `tests/controllers/test_setup_controller.py`; keep `test_setup_screen.py` and `test_cli.py` passing | Every criterion above has a passing test | S3.3, S3.4 |

## Estimate

- **Points:** 5
- **Reason:** Medium effort (several actions plus CLI wiring). Medium complexity. Low uncertainty: the logic already lives in `setup_check.py` and `bench.py`.

## Out of Scope

- Any change to the check rules in `domain/setup_check.py` or the speed math in `domain/bench.py`.
- Any change to `bench` command flags or output.
- The voice changer screen (S2), the Train screen (S4), and the app quit check (S5).
