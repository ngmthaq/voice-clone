# Title: Plan — S4 Train controller

- Classification: feature
- Description: Move the form checks, start, stop, the progress and log events, and the last-used settings into a new `TrainController` with no Textual code. `TrainPanelWidget` and `cli.py` `train` both use it.

---

## Approach Summary / Goal

- A new file, `controllers/train_controller.py`, holds the state and rules that `TrainPanelWidget` has today: the training and stopping flags, the target epochs, the voice name, the `StreamingRunner`, the event queue, the option checks (`_read_options`, `_parse_paths`, `_read_int`), and the settings save (`_save_options`).
- `TrainPanelWidget` keeps its `@work(thread=True)` worker and its 0.2 s interval, the same as S2 and S3. The worker calls a blocking controller method. The widget only reads form fields, sends them to the controller, and shows what the controller returns.
- `cli.py` `_run_train` builds `TrainOptions` from the flags and calls a controller method that runs `train_voice` with the plain terminal runner and the CLI pause hint. The CLI keeps its log handler, exception handling, messages, and exit codes.
- Goal: one place for training logic, covered by plain pytest tests with a fake runner. The app works exactly as before.

## Functional Requirements

- `TrainController` does not import Textual. It imports the domain names it uses at module level (`load_settings`, `save_settings`, `training_dir`, `voices_dir`, `Applio`, `StreamingRunner`, `TrainOptions`, `train_voice`, `prepare_dataset`, `validate_options`, `voice_exists`, `epochs_done`). Tests can then patch them on the controller module.
- **Form defaults:** the controller gives the last-used values (name, epochs, batch size, save every, and sample rate, which falls back to the default when the saved rate is not in `SAMPLE_RATES`). The widget uses them in `compose`.
- **Option check:** one method takes the raw form values: the inputs text, name, epochs text, sample rate, batch size text, save-every text, restart, and force. It returns `TrainOptions` or raises `VoiceCloneError`. The order and texts stay the same as today:
  1. Parse the paths.
  2. "Add at least one recording…"
  3. "'…' does not exist."
  4. Read the whole numbers ("… must be a whole number.").
  5. `validate_options`.
  6. Save the last-used settings. A save that fails with `OSError` only writes a log warning.
  7. The "already exists. Tick 'Replace an existing voice'…" check.
- **Start:** a start method sets the training state, clears the events, and makes the `StreamingRunner`. Its `on_line` and `on_transient` callbacks put events on the queue. A blocking `train(options)` method runs `train_voice` with `Applio(training_dir()/".applio", runner=…)`, `partial(prepare_dataset, runner=…)`, and `UI_PAUSE_HINT`. It queues `step`, `failed` (`STOPPED_MESSAGE` or `"Error: …"`), and `done` events, the same as today.
- **Events:** `drain_events()` returns the queued `(kind, text)` events. A helper turns a log line into epoch progress: it checks for the voice name, then calls `epochs_done`, then caps the value at the target epochs.
- **Stop:** `stop()` does nothing if there is no runner or a stop has already started. Otherwise it sets the stopping flag and calls `runner.stop()`. A second method stops the runner when the widget is removed (the same as today's `on_unmount`). A finish method clears the state.
- **Busy:** `running` and `stopping` properties. `TrainScreen.busy_message` and `action_back` work the same as today.
- **CLI:** `_run_train` calls the controller inside the function (lazy import), so `--help` and `run` stay fast. The flags, log lines, `"Error: …"` text, the Ctrl+C message, and the exit codes (`0`, `EXIT_ERROR`, `EXIT_INTERRUPTED`) stay the same.
- `TrainPanelWidget` makes no calls to `domain/training`. It may import domain constants only for the widgets (`NAME_PATTERN`, `MAX_EPOCHS`, `MAX_BATCH_SIZE`, `SAMPLE_RATES`).

## Non-Functional Requirements

- No change in behavior, status texts, widget ids, `train` output, or exit codes. Stop uses the same process kill rules (`StreamingRunner.stop`).
- The UI thread never waits on training.
- `controllers/train_controller.py` has no `textual` import.
- The code follows `CODING_CONVENTIONS.md`: the Controllers section, type hints, file order, and almost no comments.
- `pytest` and `ruff check .` pass.

## Files in Scope

- Create: `src/voice_clone/controllers/train_controller.py`, `tests/controllers/test_train_controller.py`
- Change:
  - `src/voice_clone/controllers/__init__.py`
  - `src/voice_clone/views/train_panel_widget.py`
  - `src/voice_clone/cli.py`
  - `tests/views/test_train_screen.py` (patch targets, private field paths, and imports of moved names only)
  - `tests/test_cli.py` (patch targets only)
  - `.claude/references/PROJECT_OVERVIEW.md` (the `controllers/` row)
  - `plans/2026-11-24-refactor-codebase-to-mvc-overview.md`
  - `plans/2026-11-24-train-controller-story.md`

## Risks & Assumptions

- Assumption: the `train` command still does **not** save last-used settings, the same as today. Only the Train screen saves them.
- Assumption: `_parse_paths`, `_read_int`, `_Event`, `STOPPED_MESSAGE`, `UI_PAUSE_HINT`, and `DEFAULT_OPTIONS` move to the controller. The queue uses `(kind, text)` tuples like `SetupController`, so `_Event` goes away. `REFRESH_SECONDS`, `MAX_LOG_LINES`, and `LOG_MIN_WIDTH` stay in the widget.
- Risk: `test_train_screen.py` imports `_Event` and `_parse_paths`, reads `panel._events`, and patches `train_panel.train_voice`, `voices_dir`, and `training_dir`. The tester changes these to the controller module and does not change any assert or scenario.
- Risk: `test_cli.py` patches `voice_clone.domain.training.train_voice`. That works today only because of the lazy import. The tester changes the patch target to the controller module.
- Risk: today `TrainPanelWidget` loads settings in `__init__`. The controller must load them at the same time (when the widget is built), so test fixtures that patch `settings_path` still work.

## Open Questions / Blockers

- None

## Status

- [x] Ready to execute
- [ ] Blocked

## Task List

| # | Status | Task | Responsible Role | Dependencies | Acceptance Criteria | Skills |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | DONE | S4.1–S4.2: create `controllers/train_controller.py` with `TrainController` (form defaults, option check with settings save, start, blocking `train`, `drain_events`, epoch progress, stop, unmount stop, finish, `running` and `stopping`, and a CLI train method). Export it from `controllers/__init__.py`. | developer | none | `grep -n textual src/voice_clone/controllers/train_controller.py` finds nothing. A small script with a fake `train_voice` and fake paths can check options, start, stop, and drain events with no Textual app. `ruff check src` passes. | `.claude/guides/CLEAN_CODE/ENTRY_POINT.md` |
| 2 | DONE | S4.3: change `views/train_panel_widget.py` to use the controller. Keep the `@work` worker, the 0.2 s interval, widget ids, texts, and `running`. | developer | task 1 | `train_panel_widget.py` has no `domain/training` function calls and no `load_settings` or `save_settings` (only widget constants). `python -m voice_clone --help` works. `ruff check src` passes. | `.claude/guides/CLEAN_CODE/ENTRY_POINT.md` |
| 3 | DONE | S4.4: change `cli.py` `_run_train` to use the controller. Keep the log handler, messages, and exit codes. | developer | task 1 | `_run_train` makes no domain training calls except through the controller. `python -m voice_clone train --help` output is unchanged. `ruff check src` passes. | `.claude/guides/CLEAN_CODE/ENTRY_POINT.md` |
| 4 | DONE | S4.5: add `tests/controllers/test_train_controller.py`. Cover: option errors (no inputs, a missing path, a non-number, a bad name, an existing voice without force), the same `TrainOptions` from form values, the settings saved as the same TOML, start and a fake train queueing `step`/`done`/`failed` events, stop calling `runner.stop()` once, the stopped message, epoch progress (capped, other voice ignored), and the CLI method calling `train_voice` with the CLI pause hint. In `test_train_screen.py` and `test_cli.py`, change only patch targets, field paths, and imports. | tester | tasks 2, 3 | `pytest` and `ruff check .` pass. `git diff tests/views/test_train_screen.py tests/test_cli.py` shows no changed asserts or scenarios. | `.claude/agents/party-mode-tester.md#testing-workflow`, `.claude/guides/AAA_TESTING.md` |
| 5 | DONE | Update docs and plan status. The `controllers/` row in `PROJECT_OVERVIEW.md` names `TrainController`. The overview sets S4 to ✅ Done and changes the counts. The S4 story doc ticks the acceptance criteria. | developer | review passed | The overview shows S4 as Done with correct counts. Every S4 criterion is ticked. | — |

After task 4, I review the work against the S4 acceptance criteria and run `graphify update .`.
