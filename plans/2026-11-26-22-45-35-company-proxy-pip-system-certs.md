# Title: Plan — Support a company network proxy with pip-system-certs

- Classification: feature
- Description: Install `pip-system-certs` in the app's `.venv` and in Applio's `.venv`, before their other downloads, so all Python downloads trust the system's certificates.

---

## Approach Summary / Goal

- `pip-system-certs` makes Python's HTTPS use the operating system's trusted certificates. That includes the company proxy certificate that IT installs.
- It must be in place **before** the large downloads, so the run scripts install it right after making `.venv`. Applio's installer does the same for its own environment.
- Goal: the run script, the model downloads, and the Applio install work behind a company proxy that inspects HTTPS.

## Functional Requirements

- **`pyproject.toml`:** add `"pip-system-certs"` to `dependencies`. Pin it to a major version range after checking the current version on PyPI (for example `>=4,<6`). The install stamp sees this change, so existing installs pick it up on their next run.
- **`run.sh` / `run.ps1`:** in the install step, right after the `.venv` is made or checked and before the pip upgrade, run `"$venv_python" -m pip install pip-system-certs`. This also runs before CUDA torch on Windows and before `pip install -e .`. If it fails, the script stops with exit 1 and a proxy hint, because nothing after it can download either: "Could not install pip-system-certs. If you are behind a company proxy, check that HTTPS_PROXY is set and the company certificate is installed in the system."
- **Applio (`applio.py` `ensure_installed`):** after Applio's `.venv` is made at step 2, and before `pip install --upgrade pip`, run `[*pip, "pip-system-certs"]`. Step numbers and messages stay the same.
- **Docs, `docs/INSTALL.md`:** add a short "Behind a company proxy" note:
  - The app uses the system's trusted certificates through `pip-system-certs`.
  - The company certificate must be installed in the system. IT usually does this.
  - If the proxy needs it, set `HTTPS_PROXY` (and `HTTP_PROXY`) before running the script.
  - Add a manual-steps line: run `pip install pip-system-certs` first.

## Non-Functional Requirements

- No verification is turned off. There is no `--trusted-host` and no `verify=False`.
- Same script rules as before: shellcheck clean, PowerShell ASCII + CRLF. Python follows ruff.

## Files in Scope

- `pyproject.toml`, `scripts/run.sh`, `scripts/run.ps1`, `src/voice_clone/domain/training/applio.py`, `tests/domain/training/test_applio.py`, `docs/INSTALL.md`

## Risks & Assumptions

- **The very first pip download** (`pip-system-certs` itself) runs before the certificate fix is active. Recent pip versions (24.2 and later, which come with current Python 3.12 releases) already use the system certificates, so this usually works. If the Python 3.12 install is older and the proxy blocks it, the script stops with the proxy hint.
- **Applio installs that already exist** are skipped (Applio's ready marker), so they will not get the package. Only new Applio installs get it. To redo one, delete `training/.applio`. The docs will say so.
- **`git clone` of Applio** uses git's own certificate settings, not Python's. Behind some proxies, git may need `git config --global http.sslBackend schannel` on Windows. The docs note mentions this in one line. The script does not change git settings.
- I cannot test behind your proxy here. Please try it on the company network.

## Open Questions / Blockers

- None.

## Status

- [x] Ready to execute

## Task List

| # | Status | Task | Responsible Role | Dependencies | Acceptance Criteria | Skills |
| - | ------ | ---- | ---------------- | ------------ | ------------------- | ------ |
| 1 | TODO | Add `pip-system-certs` to `pyproject.toml`. Install it first in `run.sh` / `run.ps1` | developer | none | `shellcheck` clean. A stub test shows `pip install pip-system-certs` runs before the pip upgrade, CUDA torch, and `pip install -e .`. A failure stops with exit 1 and the hint | `guides/CLEAN_CODE/ENTRY_POINT.md` |
| 2 | TODO | Applio: install `pip-system-certs` right after its `.venv` is made | developer | none | `ruff` passes. Existing `pytest` passes | `guides/CLEAN_CODE/ENTRY_POINT.md` |
| 3 | TODO | Docs: the "Behind a company proxy" note in `INSTALL.md` | developer | 1, 2 | The note covers the system certificate, `HTTPS_PROXY`, git on Windows, and redoing Applio | `references/AGENT_RULES.md` |
| 4 | TODO | Test: Applio's install commands include `pip-system-certs` right after venv creation and before the pip upgrade | tester | 2 | The test fails without the change and passes with it. Full `pytest` passes | `guides/AAA_TESTING.md` |
