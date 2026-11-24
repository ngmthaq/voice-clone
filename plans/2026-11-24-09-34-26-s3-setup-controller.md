# Title: Plan — S3 Setup controller

- Classification: feature
- Description: Move the setup checks, base model download, Applio install, speed test, and bench logic into a new `SetupController` with no Textual code. `SetupScreen` and `cli.py` `bench` both use it.

---

## Approach Summary / Goal

- A new `controllers/setup_controller.py` holds the state and rules that `SetupScreen` has today: busy state, the check summary status, the download, the Applio runner and its event queue, the speed test, the stop action, and the busy message.
- `SetupScreen` keeps its `@work(thread=True)` workers and its 0.2 s interval, the same as S2. Workers call blocking controller methods. The view only builds widgets and shows the controller's state.
- The controller also gets a bench method for the CLI. It checks the base models, picks the voice, builds the engine, runs each preset, and picks the recommended preset. `cli.py` keeps every `print`, the table format, and the exit codes.
- Goal: one place for setup logic, covered by plain pytest tests. The app and `bench` work exactly as before.

## Functional Requirements

- `SetupController` does not import Textual. It imports the domain names it uses at module level (`gather_facts`, `evaluate`, `ensure_base_models`, `models_dir`, `training_dir`, `voices_dir`, `Applio`, `StreamingRunner`, `measure_and_save`, `RvcEngine`, `select_torch_device`, `base_models_present`, `discover_profiles`, `load_settings`, …), so tests can patch them on the controller module.
- **Checks:** a blocking method returns the check list and facts from `gather_facts()` + `evaluate()`. The controller gives the summary status as a `(message, kind)` pair, with today's texts ("The voice changer needs: …", "The voice changer is ready. Training needs …", "Everything is ready.", "Error: could not check the setup: …"). It also says if the download button shows (and its MB size), if the Applio button shows, and if Measure speed shows.
- **Download:** a blocking method calls `ensure_base_models(models_dir(), progress)` and reports progress through a callback. It returns `None` or the error text (`"Error: …"`), the same as today.
- **Applio install:** the controller owns the `StreamingRunner` and the event queue. `drain_events()` returns the queued `(kind, text)` events. A stop method stops the runner. The texts stay the same (`APPLIO_STOPPED_MESSAGE`, `"Error: …"`).
- **Measure speed:** a blocking method wraps `measure_and_save(on_result=...)`. It reports each result through a callback and returns the final `(message, kind)` from today's `_measure_message`.
- **Busy state and message:** the controller holds `busy`, `downloading`, `measuring`, and the runner. `SetupScreen.busy_message` returns `controller.busy_message`, with the same texts. `BUSY_MESSAGE` on Esc stays the same.
- **Bench (CLI):** a controller method takes voice, presets, seconds, cpu, threads, and precision. It reports a clear error for missing base models and a missing voice, reports the header facts (voice, device, precision, threads), reports each result through a callback, and returns the recommended preset (or `None`). `cli.py` prints the same lines and returns the same exit codes (`0`, `EXIT_ERROR`, `EXIT_INTERRUPTED`).
- `SetupScreen` has no direct calls to `domain/`. It may import `domain/` names only for type hints and widget constants (`OK`, `MISSING`, `INFO`, `VOICE_CHANGER`, `TRAINING`, `Check`).
- `cli.py` imports the controller inside `_run_bench_command` (lazy), so `--help` and `run` stay fast.

## Non-Functional Requirements

- No change in behavior, status texts, widget ids, key bindings, or `bench` output and exit codes.
- The UI thread never waits on checks, downloads, installs, or speed tests.
- `controllers/setup_controller.py` has no `textual` import.
- Follow `CODING_CONVENTIONS.md` (Controllers section, type hints, file order, almost no comments).
- `pytest` and `ruff check .` pass.

## Files in Scope

- Create: `src/voice_clone/controllers/setup_controller.py`, `tests/controllers/test_setup_controller.py`
- Change: `src/voice_clone/controllers/__init__.py`, `src/voice_clone/views/setup_screen.py`, `src/voice_clone/cli.py`, `tests/views/test_setup_screen.py` (patch targets and private field paths only), `tests/test_cli.py` (patch targets only, plus new bench output tests), `.claude/references/PROJECT_OVERVIEW.md` (the `controllers/` row), `plans/2026-11-24-refactor-codebase-to-mvc-overview.md`, `plans/2026-11-24-setup-controller-story.md`

## Risks & Assumptions

- Risk: `test_cli.py` patches `voice_clone.domain.paths.models_dir` and `voice_clone.domain.engine.base_models_present`. These work today only because `cli.py` imports them lazily. After the move, the tester changes them to the controller module.
- Risk: today no test checks the full `bench` output. The tester adds one with `FakeEngine` and `capsys` (pytest's output capture). It must pass before and after the change to `cli.py`, so the tester writes it against the current output text.
- Risk: state changes after a worker ends must still run on the UI thread (`call_from_thread`), the same as S2.
- Assumption: `_preset_title` and `_measure_message` move to the controller. `ICONS` stays in the view.
- Assumption: S2 is still not committed. S3 is built on top. Nothing is committed. You commit when you are ready.

## Open Questions / Blockers

- None

## Status

- [x] Ready to execute
- [ ] Blocked

## Task List

| # | Status | Task | Responsible Role | Dependencies | Acceptance Criteria | Skills |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | DONE | S3.1–S3.2: create `controllers/setup_controller.py` with `SetupController` (checks + summary status, download, Applio install with its own runner and event queue, stop, measure speed, busy state and message, bench for the CLI). Export it from `controllers/__init__.py`. | developer | none | `grep -n textual src/voice_clone/controllers/setup_controller.py` finds nothing. A small script with fake facts, a fake download, a fake Applio, and `FakeEngine` can run each action with no Textual app. `ruff check src` passes. | `.claude/guides/CLEAN_CODE/ENTRY_POINT.md` |
| 2 | DONE | S3.3: change `views/setup_screen.py` to use the controller. Keep the `@work` workers, the 0.2 s interval, widget ids, bindings, and `busy_message`. | developer | task 1 | `setup_screen.py` has no domain function calls (only type and widget-constant imports). `python -m voice_clone --help` works. `ruff check src` passes. | `.claude/guides/CLEAN_CODE/ENTRY_POINT.md` |
| 3 | DONE | S3.4: change `cli.py` `_run_bench_command` to use the controller. Keep every print line and exit code. | developer | task 1 | `cli.py` bench has no domain calls except through the controller. `python -m voice_clone bench --help` works. `ruff check src` passes. | `.claude/guides/CLEAN_CODE/ENTRY_POINT.md` |
| 4 | DONE | S3.5: add `tests/controllers/test_setup_controller.py`, covering every S3 criterion (check list with fake facts, summary statuses, download progress and error via callback, Applio events and stop, measure speed via callback with `FakeEngine`, busy message, bench results and recommended preset). In `tests/test_cli.py` add bench output tests (missing models, missing voice, full table with a fake engine). Change only patch targets and private field paths in `tests/views/test_setup_screen.py` and the old `test_cli.py` bench tests. | tester | tasks 2, 3 | `pytest` and `ruff check .` pass. `git diff tests/views/test_setup_screen.py` shows no changed asserts or scenarios. | `.claude/agents/party-mode-tester.md#testing-workflow`, `.claude/guides/AAA_TESTING.md` |
| 5 | DONE | Update docs and plan status: the `controllers/` row in `PROJECT_OVERVIEW.md` names `SetupController`. In the overview, set S3 to ✅ Done and change the counts. In the S3 story doc, tick the acceptance criteria. | developer | review passed | The overview shows S3 as Done with correct counts. Every S3 criterion is ticked. | — |

After task 4, I review the work against the S3 acceptance criteria and run `graphify update .`.
