# S1 — Move code into `domain/` and `views/`

- **Epic:** [Refactor codebase to MVC — Overview](./2026-11-24-refactor-codebase-to-mvc-overview.md)
- **Story Points:** 5
- **Depends On:** —

## User Story

As a `developer`, I want to `have the code moved into domain/ and views/ folders` so that I can `see the layers at a glance`.

This is an **enabler** story. It makes S2, S3, S4 and S5 possible.

## Goal

**Problem:** Today the model code (`config.py`, `audio/`, `engine/`, `training/`, …) and the UI code (`ui/`, `app.py`) sit side by side at the top of `src/voice_clone/`. Nothing in the layout shows which code is data and logic, and which code is UI. New developers must read the code to learn the layers.

**Solution:** Move the files into two new packages, `domain/` (model layer) and `views/` (UI layer), and add an empty `controllers/` package. Only paths and imports change. No logic changes.

**Impact:** The folder layout shows the MVC layers. Later stories can add controllers without also moving files, so their reviews stay small.

## Requirements

### Functional Requirements

- `src/voice_clone/domain/` holds: `config.py`, `errors.py`, `paths.py`, `setup_check.py`, `bench.py`, `profiles/`, `audio/`, `engine/` (with `vendor/`), `training/`.
- `src/voice_clone/views/` holds: `app.py` and everything in today's `ui/` (screens, widgets, `fields.py`, `app.tcss`).
- `src/voice_clone/controllers/` exists as an empty package.
- `cli.py`, `__main__.py` and `logging_setup.py` stay at the top of `src/voice_clone/`.
- All imports use the new absolute paths (`from voice_clone.domain.audio import ...`). The old paths are removed. There are no shims.
- `tests/` mirrors the new `src/` folders.

### Non-Functional Requirements

- No change in app behavior: screens, key bindings, settings file, and CLI commands stay the same.
- `domain/engine/vendor/` code is not edited or restyled. Only its path changes.
- `pytest` and `ruff check .` pass.
- Works on macOS and Windows (use `pathlib` for the `app.tcss` path).

## Acceptance Criteria

- [x] Given the new layout, when I list `src/voice_clone/`, then I see `domain/`, `views/`, `controllers/` (empty package), plus `cli.py`, `__main__.py`, `logging_setup.py`.
- [x] Given the move, when I search for `voice_clone.ui`, `voice_clone.audio`, `voice_clone.engine`, `voice_clone.training`, `voice_clone.profiles`, `voice_clone.config`, then nothing is found outside `domain/` paths.
- [x] Given the move, when I run `pytest` and `ruff check .`, then both pass with no test logic changed.
- [x] Given the move, when I run `python -m voice_clone run`, `train --help` and `bench --help`, then they work as before.
- [x] Given `domain/engine/vendor/`, when I diff it, then only the path changed, no code.

## Tasks

| # | Task | Done when | Depends On |
| --- | --- | --- | --- |
| S1.1 | [BE] Move `config.py`, `errors.py`, `paths.py`, `setup_check.py`, `bench.py`, `profiles/`, `audio/`, `engine/` (with `vendor/`), `training/` into `src/voice_clone/domain/`; fix all imports | App imports work from the new paths | — |
| S1.2 | [FE] Move `ui/` (screens, widgets, `fields.py`, `app.tcss`) and `app.py` into `src/voice_clone/views/`; fix `CSS_PATH` and imports | The app starts and loads its styles | S1.1 |
| S1.3 | [BE] Add an empty `src/voice_clone/controllers/` package | Package imports with no error | — |
| S1.4 | [DevOps] Update `pyproject.toml` ruff `extend-exclude` to `src/voice_clone/domain/engine/vendor` | `ruff check .` skips vendor code | S1.1 |
| S1.5 | [QA] Move `tests/` folders to mirror `domain/` and `views/`; fix imports and patch targets | `pytest` passes with no test logic changed | S1.1, S1.2 |
| S1.6 | [Docs] Update `CODING_CONVENTIONS.md`, `PROJECT_OVERVIEW.md`, and any old paths in `docs/` (for example `THIRD_PARTY_NOTICES.md`) | No doc names an old path | S1.1, S1.2 |
| S1.7 | [QA] Check S1 acceptance criteria and run `graphify update .` | Every criterion above is checked | S1.5, S1.6 |

## Estimate

- **Points:** 5
- **Reason:** High effort (many files, every test import). Low complexity (no logic change). Medium uncertainty: `mock.patch` targets and `CSS_PATH` can break in hidden ways.

## Out of Scope

- Any logic change, bug fix, or new feature.
- Moving logic out of screens into controllers (S2, S3, S4).
- Editing or restyling `domain/engine/vendor/` code.
- Renaming the root `models/` data folder.
