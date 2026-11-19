# Coding Conventions

> Status: proposed at onboarding (2026-11-16), before any code existed. Update when the code shows other patterns.

## Folder Structure (src layout)

```
voice-clone/
├── pyproject.toml          # uv project, ruff + pytest config
├── src/voice_clone/
│   ├── __main__.py         # entry point: `uv run voice-clone`
│   ├── app.py              # Textual App
│   ├── ui/                 # screens, widgets, .tcss styles
│   ├── audio/              # devices, input/output streams, ring buffer
│   ├── engine/             # RVC model loading + inference
│   ├── profiles/           # find and load voice profiles
│   └── config.py           # settings (pydantic)
├── tests/                  # same folders as src/
├── voices/  models/        # not in git
└── plans/
```

## Style

- Use Ruff to lint and format. Line length 100, double quotes, 4 spaces.
- Add type hints to every function signature. Check with mypy or pyright (basic mode).
- Use absolute imports: `from voice_clone.audio import ...`.

## Naming

- `snake_case` for files, modules, functions, and variables.
- `PascalCase` for classes. `UPPER_SNAKE` for constants.
- Textual screens end in `Screen`. Widgets end in `Widget` (e.g. `DeviceSelectScreen`).
- Private helpers start with `_`.

## Code Order in a File

1. Imports (stdlib → third-party → local, sorted by Ruff)
2. Constants
3. Classes and public functions
4. Private helpers (`_name`) last

## Real-Time Audio

- The audio callback must not run the model, write logs, allocate memory, or take locks.
- Run the model in a worker thread. Pass data between threads with queues or ring buffers.
- The Textual UI thread never waits on audio or the model. Send updates with Textual messages or workers.

## Cross-Platform (macOS + Windows)

- Use `pathlib` for every path.
- Keep OS-specific code (device names, torch device choice) in one module per area.
- Never hard-code `cuda` or `mps`. Pick the device at start: `cuda` → `mps` → `cpu`.

## Errors and Logging

- Raise our own exceptions for missing devices, bad profiles, and failed model loads.
- The UI shows these errors in plain words.
- Use the `logging` module and write to a log file. Never print to stdout (it breaks the TUI).

## Settings

- Settings are a pydantic model.
- Save them as TOML in the user config folder (`platformdirs`).

## Testing

- Use pytest. Write tests after the code (Code-First).
- Mock audio devices and the model. Feed fixed numpy buffers. Check shapes, delay, and crossfade.
- Mark real-device tests with `@pytest.mark.hardware`. Skip them in CI.

## Third-Party Libraries

- Add dependencies only with `uv add`.
- Pin `torch` per platform in `pyproject.toml`.
- Do not commit model files (`.pth`, `.index`) or `voices/` / `models/` folders.
