# Title: Plan — S1 Move code into `domain/` and `views/`

- Classification: feature
- Description: Move files with `git mv` into `domain/` and `views/`, add an empty `controllers/` package, and change only imports and paths.

## Approach Summary / Goal

- The developer moves the files with `git mv`, so git keeps the file history. Then the developer changes every import to the new absolute path.
- The tester moves the test folders to match and fixes imports and patch target strings. Test logic does not change.
- Goal: the folders show the MVC layers. The app works exactly as before.

## Functional Requirements

- `src/voice_clone/domain/` holds `config.py`, `errors.py`, `paths.py`, `setup_check.py`, `bench.py`, `profiles/`, `audio/`, `engine/` (with `vendor/`), `training/`, and a new empty `__init__.py`.
- `src/voice_clone/views/` holds `app.py` and all of today's `ui/`: `__init__.py` (same exports), `fields.py`, the screens, the widgets, and `app.tcss`.
- `src/voice_clone/controllers/__init__.py` exists and is empty.
- `cli.py`, `__main__.py`, `logging_setup.py`, and `__init__.py` stay at the top level.
- `CSS_PATH = Path(__file__).parent / "app.tcss"` in `views/app.py`.
- No old import paths remain, and there are no shims (old modules that point to new ones).
- Tests mirror the new layout:
  - `tests/{audio,engine,profiles,training}` → `tests/domain/...`
  - `test_bench.py`, `test_config.py`, `test_setup_check.py` → `tests/domain/`
  - `tests/ui/` → `tests/views/`
  - `test_cli.py` and `conftest.py` stay at the top.
- `tools/kaggle_bench.ipynb`: only the import lines change.
- After review passes, the plan files show S1 as Done.

## Non-Functional Requirements

- No logic change. Screens, key bindings, the settings file, and CLI commands stay the same.
- `domain/engine/vendor/` keeps the same bytes. Only its path changes.
- `pytest` and `ruff check .` pass.
- Paths use `pathlib`, so they work on macOS and Windows.

## Files in Scope

- Move: all files listed above in `src/voice_clone/` and `tests/`
- Create: `src/voice_clone/domain/__init__.py`, `src/voice_clone/views/__init__.py` (moved from `ui/__init__.py`), `src/voice_clone/controllers/__init__.py`, `tests/domain/__init__.py`, `tests/views/__init__.py`
- Change: `src/voice_clone/cli.py`, `src/voice_clone/__main__.py` (if it imports moved code), `pyproject.toml`, `tools/kaggle_bench.ipynb`, `docs/THIRD_PARTY_NOTICES.md`, `.claude/references/CODING_CONVENTIONS.md`, `.claude/references/PROJECT_OVERVIEW.md`, `plans/2026-11-24-refactor-codebase-to-mvc-overview.md`, `plans/2026-11-24-move-code-into-domain-views-story.md`
- Delete: the empty old `src/voice_clone/ui/` and `tests/ui/` folders, plus the other old folders after the move

## Risks & Assumptions

- Risk: string patch targets (`monkeypatch.setattr("voice_clone.paths.voices_dir", ...)`) do not fail at import time. They fail only when the test runs. A full `pytest` run catches them.
- Risk: between task 1 and task 3, tests fail because tests still use the old paths. This is expected.
- Assumption: Ruff's `"training"` exclude stays as it is. It matches any folder named `training`, so the moved folder is still excluded.
- Assumption: nothing is committed. You commit when you are ready.

## Open Questions / Blockers

- None

## Status

- [x] Ready to execute
- [ ] Blocked

## Task List

| # | Status | Task | Responsible Role | Dependencies | Acceptance Criteria | Skills |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | TODO | S1.1–S1.4: `git mv` the model code into `domain/` and the UI code into `views/`. Add an empty `domain/__init__.py` and `controllers/__init__.py`. Fix all imports in `src/` and `CSS_PATH`. Change the Ruff vendor exclude to `src/voice_clone/domain/engine/vendor`. | developer | none | `grep -rn "voice_clone\.\(ui\|audio\|engine\|training\|profiles\|config\|errors\|paths\|setup_check\|bench\|app\)\b" src` finds nothing outside the `voice_clone.domain.`/`voice_clone.views.` forms. `python -m voice_clone --help`, `train --help`, and `bench --help` work. `python -c "import voice_clone.views.app, voice_clone.controllers"` works. `git diff -M --stat` shows the vendor files as pure renames. `ruff check src` passes. | `guides/CLEAN_CODE/ENTRY_POINT.md` |
| 2 | TODO | S1.6 + notebook: change old paths in `docs/THIRD_PARTY_NOTICES.md`, `.claude/references/CODING_CONVENTIONS.md` (folder tree, vendor/lint note, import example), and `.claude/references/PROJECT_OVERVIEW.md` (Main parts table). Change only the import lines in `tools/kaggle_bench.ipynb`. | developer | task 1 | No doc or notebook names an old module path. The notebook stays valid JSON, and only the import lines change. | `guides/CLEAN_CODE/ENTRY_POINT.md` |
| 3 | TODO | S1.5: `git mv` the test folders to mirror `src/`. Add the `__init__.py` files. Fix imports and every string patch target. | tester | task 1 | `pytest` and `ruff check .` pass. `git diff -M` shows only import and patch-string changes in tests. No old module path remains in `tests/`. | `agents/party-mode-tester.md#testing-workflow`, `guides/AAA_TESTING.md` |
| 4 | TODO | Update the plan status: in the overview, set S1 to ✅ Done and change the counts. In the S1 story doc, tick the acceptance criteria. | developer | review passed | The overview shows S1 as Done with correct counts. Every S1 criterion is ticked. | — |

After this, the Root Agent reviews the work against the S1 acceptance criteria and runs `graphify update .` (S1.7).
