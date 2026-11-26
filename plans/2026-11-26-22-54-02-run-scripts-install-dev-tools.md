# Title: Plan — run scripts install the dev tools

- Classification: feature
- Description: `run.sh` and `run.ps1` install `.[dev]` (the app plus pytest and ruff) instead of `.`.

## What changes

- **`run.sh` / `run.ps1`:** in the install step, `pip install -e .` becomes `pip install -e ".[dev]"`. In PowerShell it is `'.[dev]'`. The order stays the same: pip-system-certs, the pip upgrade, CUDA torch (Windows), then the app.
- **Stamp:** the stamp file `.venv/.voice-clone-install` gets the text `dev:` in front of the `pyproject.toml` hash. Without this, an existing `.venv` would look "already installed" and the dev tools would never be added. With the new stamp text, the next run reinstalls once and adds pytest and ruff.
- **Docs (`docs/INSTALL.md`):** step 1 of "What the script does" says it also installs the development tools (pytest, ruff).

## Acceptance

- `shellcheck` is clean.
- Test with a fake Python: the old stamp, which has no `dev:`, triggers one reinstall with `-e .[dev]`. A second run skips the install.
- `run.ps1` stays ASCII with CRLF line endings.

## Risk

- Every install now also downloads pytest and ruff. They add only a few MB.

## Task List

| # | Status | Task | Responsible Role | Dependencies | Acceptance Criteria | Skills |
| - | ------ | ---- | ---------------- | ------------ | ------------------- | ------ |
| 1 | TODO | `run.sh` / `run.ps1`: install `.[dev]`; stamp text `dev:<hash>` | developer | none | As in Acceptance above | `guides/CLEAN_CODE/ENTRY_POINT.md` |
| 2 | TODO | `docs/INSTALL.md`: mention the dev tools in step 1 | developer | 1 | Docs say the script installs pytest and ruff | `references/AGENT_RULES.md` |
