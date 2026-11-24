# S2 — Voice changer controller

- **Epic:** [Refactor codebase to MVC — Overview](./2026-11-24-refactor-codebase-to-mvc-overview.md)
- **Story Points:** 8
- **Depends On:** S1 — [Move code into domain/ and views/](./2026-11-24-move-code-into-domain-views-story.md)

## User Story

As a `developer`, I want to `have the voice changer logic in a controller` so that I can `test start/stop, settings and voice choice without the UI`.

## Goal

**Problem:** `views/main_screen.py` (745 lines) builds widgets, but it also loads and saves settings, finds voices, lists audio devices, and starts and stops the audio pipeline. This logic can only be tested through a running Textual app. The file is hard to read and hard to change safely.

**Solution:** Add `controllers/changer_controller.py` with a `ChangerController`. It holds the voice changer state and actions. `MainScreen` only builds widgets, sends user actions to the controller, and shows controller state.

**Impact:** Plain pytest tests can cover the voice changer logic. `main_screen.py` gets much smaller. The controller rules are written down for the next stories.

## Requirements

### Functional Requirements

- `ChangerController` loads input and output devices, voice profiles, and settings (today in `on_mount` and `_populate_selects`).
- It starts, stops and toggles the pipeline (today in `toggle`, `_begin_start`, `_start_pipeline`).
- It takes setting changes and saves them with the same debounce as today (`_schedule_save`).
- It reports status and level changes to the view. The view gets them through Textual messages or workers.
- `MainScreen` has no direct calls to `domain/`. It may import `domain/` types for type hints only.

### Non-Functional Requirements

- Real-time audio rules: the controller adds no model calls, logs, memory allocation, or locks to the audio callback.
- The Textual UI thread never waits on audio or the model.
- No change in app behavior. The settings TOML file is the same as today.
- The controller does not import Textual.

## Acceptance Criteria

- [ ] Given `controllers/changer_controller.py`, when a test creates it with a `FakeEngine` and fake devices, then it can start and stop the pipeline with no Textual app.
- [ ] Given a setting change, when the controller saves it, then it uses the same debounced save as today and the TOML file is the same.
- [ ] Given voices in `voices/`, when the controller loads them, then the voice list matches today's list.
- [ ] Given `MainScreen`, when I read it, then it only builds widgets, sends user actions to the controller, and shows controller state. It has no direct calls to `domain/`.
- [ ] Given the audio callback, when the pipeline runs, then the controller adds no model calls, logs, or locks to it.
- [ ] Given the app, when I use the voice changer screen, then it works exactly as before.

## Tasks

| # | Task | Done when | Depends On |
| --- | --- | --- | --- |
| S2.1 | [BE] Create `ChangerController` with state for devices, voices, settings, and pipeline status (from `_populate_selects`, `on_mount` loading) | Controller loads devices, voices and settings in a test | — |
| S2.2 | [BE] Move pipeline start/stop/toggle (`toggle`, `_begin_start`, `_start_pipeline`) into the controller | Start/stop works from a test with `FakeEngine` | S2.1 |
| S2.3 | [BE] Move settings change and debounced save (`_schedule_save`) into the controller | Settings save from a test, same TOML output | S2.1 |
| S2.4 | [FE] Change `views/main_screen.py` to use the controller; status and level updates come from the controller via Textual messages or workers | `MainScreen` has no `domain/` imports except types | S2.2, S2.3 |
| S2.5 | [Docs] Add controller rules to `CODING_CONVENTIONS.md` (what goes in a controller, how views talk to it) | Rules are in the doc | S2.4 |
| S2.6 | [QA] Add `tests/controllers/test_changer_controller.py`; keep `tests/views/test_main_screen.py` passing | Every criterion above has a passing test | S2.4 |

## Estimate

- **Points:** 8
- **Reason:** High effort (the biggest file). High complexity: audio thread, debounced saves, timers. Medium uncertainty: the real-time rules must hold after the split.

## Out of Scope

- Any change in app behavior or the settings format.
- Changes to `domain/audio/pipeline.py` or `domain/engine/rvc_engine.py` logic.
- The Setup screen (S3), the Train screen (S4), and the app quit check (S5).
