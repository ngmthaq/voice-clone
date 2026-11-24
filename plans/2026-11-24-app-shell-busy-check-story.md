# S5 — App shell asks controllers about running work

- **Epic:** [Refactor codebase to MVC — Overview](./2026-11-24-refactor-codebase-to-mvc-overview.md)
- **Story Points:** 2
- **Depends On:**
  - S2 — [Voice changer controller](./2026-11-24-voice-changer-controller-story.md)
  - S3 — [Setup controller](./2026-11-24-setup-controller-story.md)
  - S4 — [Train controller](./2026-11-24-train-controller-story.md)

## User Story

As a `developer`, I want to `have the app's quit/restart check ask controllers if work is running` so that I can `keep screen logic out of the app shell`.

## Goal

**Problem:** `views/app.py` `VoiceCloneApp._busy_message` asks each screen if work is running before it quits or restarts. So the app shell depends on screen details, not on the logic layer.

**Solution:** Give each controller the same "busy message" method. The app shell asks the controllers instead of the screens.

**Impact:** The app shell has no screen logic. The busy check can be tested without screens.

## Requirements

### Functional Requirements

- `ChangerController`, `SetupController` and `TrainController` each have the same method that returns a busy message, or nothing when idle.
- `VoiceCloneApp._busy_message` and `_confirmed` use these controller methods.

### Non-Functional Requirements

- No change in app behavior. The confirmation messages are the same as today.

## Acceptance Criteria

- [x] Given work is running in any controller, when the user quits or restarts, then the app asks for confirmation with the same message as today.
- [x] Given no work is running, when the user quits, then the app quits with no question.
- [x] Given `views/app.py`, when I read it, then `_busy_message` asks controllers, not screens.

## Tasks

| # | Task | Done when | Depends On |
| --- | --- | --- | --- |
| S5.1 | [BE] Add a common "busy message" method to the three controllers | Each controller returns its busy message in a test | — |
| S5.2 | [FE] Change `VoiceCloneApp._busy_message` and `_confirmed` to use the controllers | Quit/restart prompts are the same as before | S5.1 |
| S5.3 | [QA] Add tests for quit and restart with and without running work | Every criterion above has a passing test | S5.2 |

## Estimate

- **Points:** 2
- **Reason:** Low effort (one method per controller and a small change in `app.py`). Low complexity. Low uncertainty.

## Out of Scope

- A controller for `HomeScreen`.
- Any change to the confirmation text or key bindings.
