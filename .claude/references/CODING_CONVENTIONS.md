# Coding Conventions

## Folder Structure (src layout)

```
voice-clone/
├── pyproject.toml          # hatchling build, ruff + pytest config
├── src/voice_clone/
│   ├── __main__.py, cli.py # commands: run, train, bench
│   ├── app.py              # Textual App
│   ├── config.py           # Settings (pydantic) + presets
│   ├── errors.py, paths.py, logging_setup.py, setup_check.py, bench.py
│   ├── ui/                 # screens, widgets, app.tcss
│   ├── audio/              # devices, pipeline, noise gate, ring buffer
│   ├── engine/             # RVC engine, torch device, downloads; vendor/ = copied RVC code
│   ├── profiles/           # find voices
│   └── training/           # Applio setup, dataset, trainer
├── tests/                  # same folders as src/, conftest.py has shared fakes
├── docs/                   # user guides
├── plans/                  # plan files
└── voices/ models/ training/   # not in git
```

## Style

- Use Ruff to lint (`E, F, I, UP, B`) and format. Line length 100, double quotes, 4 spaces, target Python 3.12.
- `src/voice_clone/engine/vendor/` and `training/` are not linted. Do not restyle vendor code.
- Add type hints to every function signature. Use modern syntax: `str | None`, `list[int]`, `collections.abc.Callable`.
- Use absolute imports: `from voice_clone.audio import ...`. Sub-packages export their public names in `__init__.py`.

## Naming

- `snake_case` for files, modules, functions, and variables.
- `PascalCase` for classes. `UPPER_SNAKE` for constants.
- Textual screens end in `Screen`. Widgets end in `Widget`. The file name matches (`level_meter_widget.py` → `LevelMeterWidget`).
- Private names start with `_` (functions, attributes, and internal types like `_Engine`).

## Code Order in a File

1. Imports (stdlib → third-party → local, sorted by Ruff)
2. `logger = logging.getLogger(__name__)`
3. Constants and type aliases
4. Classes and public functions
5. Private helpers (`_name`) last

## Comments

- Write almost no comments. Use clear names instead.
- Add a short docstring only when the reason for the code is not clear from the code.

## Real-Time Audio

- The audio callback must not run the model, write logs, allocate memory, or take locks.
- Run the model in a worker thread. Pass data between threads with queues or ring buffers.
- The Textual UI thread never waits on audio or the model. Send updates with Textual messages or workers.

## Cross-Platform (macOS + Windows)

- Use `pathlib` for every path.
- Keep OS-specific code (device names, torch device choice) in one module per area.
- Never hard-code `cuda` or `mps`. Pick the device at start: `cuda` → `mps` → `cpu`.

## Errors and Logging

- Raise our own exceptions from `errors.py`. All of them come from `VoiceCloneError`.
- The UI shows these errors in plain words.
- Use the `logging` module. Logs go to a rotating file (`logging_setup.py`).
- Never `print` in the app (it breaks the TUI). Only CLI commands like `bench` print.

## Settings

- All settings are fields on one pydantic `Settings` model. Use `Field(ge=..., le=...)` for limits.
- Save them as TOML in the user config folder (`platformdirs`). A broken or missing file gives defaults.

## Testing

- Use pytest. Write tests after the code (Code-First).
- Test files mirror `src/` folders. Name tests by behavior: `test_load_missing_file_returns_defaults`.
- Arrange / act / assert, split by blank lines.
- Use fakes (e.g. `FakeEngine` in `conftest.py`) for audio devices and the model. Feed fixed numpy buffers.
- Mark real-device tests with `@pytest.mark.hardware`.

## Third-Party Libraries

- Add dependencies to `pyproject.toml`, then run `pip install -e ".[dev]"`.
- Keep `torch` and `torchaudio` pinned to the same version.
- Do not commit model files (`.pth`, `.index`) or the `voices/`, `models/`, `training/` folders.
