# Title: Plan — S2 Voice changer controller

- Classification: feature
- Description: Move the voice changer logic from `views/main_screen.py` into a new `ChangerController` that does not import Textual. `MainScreen` keeps its Textual workers and timer, and sends work to the controller.

---

## Approach Summary / Goal

- A new `controllers/changer_controller.py` holds all state and rules: devices, voices, settings, pitch, voice options, gate, presets, the start/stop flow, levels, pipeline errors, the "too slow" check, the busy message, status texts, and the debounced save.
- `MainScreen` keeps its `@work(thread=True)` workers. Inside them it calls blocking controller methods. It also passes its own `self.set_timer` to the controller for the 0.3 s save. Threading and save timing stay the same as today.
- The controller gives the view a status as a `(message, kind)` pair. The view only builds widgets, sends user actions to the controller, and shows controller state.
- Goal: plain pytest tests can cover the voice changer logic, and the app works exactly as before.

## Functional Requirements

- `ChangerController` takes `set_timer: Callable[[float, Callable[[], None]], <object with stop()>]` in its constructor. It does not import Textual.
- The controller module imports the domain names it uses at module level (`list_input_devices`, `list_output_devices`, `discover_profiles`, `voices_dir`, `models_dir`, `ConversionPipeline`, `RvcEngine`, `select_torch_device`, `base_models_present`, `ensure_base_models`, `load_settings`, `save_settings`, `settings_saved`). Tests can then patch them on the controller module.
- **Loading:** a load method fills inputs, outputs, and profiles. It picks the default input, output, and voice with today's rules (saved name → first input / virtual output / first voice). It also sets `models_ready`. First-start CPU settings (`_first_start_settings`, the `minimal` preset) move to the controller.
- **Selections:** the controller holds the chosen input, output, and voice names. The view tells it when a `Select` changes.
- **Settings:** pitch (clamped to −12…+12), voice options, gate values, choosing a preset, the Advanced reset, and the matching-preset key are controller methods. A change applies to a running engine or pipeline the same way as today (`_apply_voice_options`, `set_gate_settings`, `set_pitch`).
- **Debounced save:** `schedule_save` reads the values right away. It stops the old timer and sets a new 0.3 s timer with `set_timer`. `flush_save` writes `load_settings().model_copy(update=values)` and logs `OSError` as a warning. The TOML file is the same as today.
- **Start/stop:** the controller checks the start conditions (models ready, voice, output, input) and returns the same status texts as today. A blocking start method builds or reuses the engine, loads the profile only if it changed, builds `ConversionPipeline`, then calls `warm_up()` and `start()`. Success and failure handlers set `working` and `converting`. Stopping sets the levels to 0 **after** `pipeline.stop()`. If the screen is gone when the start finishes, the pipeline is still stopped.
- **Download:** a blocking method calls `ensure_base_models(models_dir(), progress)`. Finish and fail handlers set the state.
- **Live tick:** a method called every 0.1 s by the view returns the levels and any status change. A stored pipeline error leads to a stop. The "too slow" warning (`SLOW_LOAD`, `SLOW_MESSAGE`) shows once per run.
- **Busy message:** `MainScreen.busy_message` returns `controller.busy_message`, with the same texts as today (`app.py` still reads it from the screen).
- `MainScreen` has no direct calls to `domain/`. It may import `domain/` names only for type hints and for constants used to build widgets (`PERFORMANCE_PRESETS`, `CUSTOM_PRESET`, `GateSettings` defaults, `Settings` defaults for placeholders).

## Non-Functional Requirements

- Real-time audio rules: `on_levels` and `on_error` on the controller only store values. They add no model calls, logs, locks, or memory allocation.
- The Textual UI thread never waits on audio or the model.
- No change in behavior, status texts, key bindings, or the settings TOML.
- `controllers/changer_controller.py` has no `textual` import.
- Follow `CODING_CONVENTIONS.md`: type hints, file order, and almost no comments (see your memory rule).
- `pytest` and `ruff check .` pass.

## Files in Scope

- Create: `src/voice_clone/controllers/changer_controller.py`, `tests/controllers/__init__.py`, `tests/controllers/test_changer_controller.py`
- Change: `src/voice_clone/controllers/__init__.py` (export `ChangerController`), `src/voice_clone/views/main_screen.py`, `tests/views/test_main_screen.py` (patch targets and private field paths only), `.claude/references/CODING_CONVENTIONS.md`, `.claude/references/PROJECT_OVERVIEW.md` (the `controllers/` row says "empty for now"), `plans/2026-11-24-refactor-codebase-to-mvc-overview.md`, `plans/2026-11-24-voice-changer-controller-story.md`

## Risks & Assumptions

- Risk: the controller's state changes from a worker thread (blocking start), as today's screen does. The developer must keep the same split: the worker does only the blocking work, and the state changes run on the UI thread through `call_from_thread`.
- Risk: some view tests set private fields such as `screen._engine` or `screen._converting`. After the move they become `screen._controller.<field>`. The tester changes only these paths, not the scenarios or the asserts.
- Assumption: widget-building constants (field tables, `MIN_PITCH`/`MAX_PITCH` labels) may stay in the view. Logic constants (`SAVE_DELAY_SECONDS`, `SLOW_LOAD`, the messages) move to the controller. `main_screen.NO_VOICES_MESSAGE` is read by a view test, so the tester changes that reference to the controller module.
- Assumption: nothing is committed. You commit when you are ready.

## Open Questions / Blockers

- None

## Status

- [x] Ready to execute
- [ ] Blocked

## Task List

| # | Status | Task | Responsible Role | Dependencies | Acceptance Criteria | Skills |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | DONE | S2.1–S2.3: create `controllers/changer_controller.py` with `ChangerController` (loading, selections, settings and presets, debounced save with an injected `set_timer`, start/stop/download, live tick, status pairs, busy message). Export it from `controllers/__init__.py`. | developer | none | `grep -n textual src/voice_clone/controllers/changer_controller.py` finds nothing. A small Python script with fake devices, a fake engine, a fake pipeline class, and a fake timer can load, start, stop, and save with no Textual app. `ruff check src` passes. | `.claude/guides/CLEAN_CODE/ENTRY_POINT.md` |
| 2 | DONE | S2.4: rewrite `views/main_screen.py` to use the controller. Keep the `@work` workers, the 0.1 s interval, and `set_timer`. Keep the widget ids, bindings, and `busy_message`. | developer | task 1 | `main_screen.py` has no domain function calls (only type and widget-constant imports). `python -m voice_clone --help` works. `ruff check src` passes. | `.claude/guides/CLEAN_CODE/ENTRY_POINT.md` |
| 3 | DONE | S2.5: add a "Controllers" section to `CODING_CONVENTIONS.md` (what goes in a controller, no Textual import, the view owns threads and timers, status as `(message, kind)`). Change the `controllers/` row in `PROJECT_OVERVIEW.md`. | developer | task 2 | Both docs describe the new rules in plain English. | — |
| 4 | DONE | S2.6: add `tests/controllers/__init__.py` and `tests/controllers/test_changer_controller.py`, covering every S2 acceptance criterion (start/stop with `FakeEngine`, same TOML after a debounced save, voice list, status texts, slow warning, levels set to 0 after stop, `on_levels` only stores values). Change only patch targets and private field paths in `tests/views/test_main_screen.py`. | tester | task 2 | `pytest` and `ruff check .` pass. `git diff tests/views/test_main_screen.py` shows no changed asserts or scenarios. | `.claude/agents/party-mode-tester.md#testing-workflow`, `.claude/guides/AAA_TESTING.md` |
| 5 | DONE | Update the plan status: in the overview, set S2 to ✅ Done and change the counts. In the S2 story doc, tick the acceptance criteria. | developer | review passed | The overview shows S2 as Done with correct counts. Every S2 criterion is ticked. | — |

After task 4, the Root Agent reviews the work against the S2 acceptance criteria and runs `graphify update .`.
