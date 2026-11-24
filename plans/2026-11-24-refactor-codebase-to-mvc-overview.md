# Refactor Codebase to MVC — Overview

- **Source:** Pasted text
- **Type:** epic
- **Created:** 2026-11-24
- **Stories:** 5 · **Total Points:** 25 · **Done:** 4 · **In progress:** 0 · **Not started:** 1

## Summary

This epic moves `src/voice_clone/` into three layers: `domain/` (model: settings, voices, audio, engine, training), `views/` (Textual screens and widgets), and `controllers/` (screen logic shared by the TUI and the CLI). Developers can then test logic without the UI, find code faster, and keep screen files small. The app works exactly as before.

## Stories

| # | User Story | Doc | Points | Depends On | Ticket | Status |
| --- | --- | --- | --- | --- | --- | --- |
| S1 | Move code into `domain/` and `views/` | [Doc](./2026-11-24-move-code-into-domain-views-story.md) | 5 | — | — | ✅ Done |
| S2 | Voice changer controller | [Doc](./2026-11-24-voice-changer-controller-story.md) | 8 | S1 | — | ✅ Done |
| S3 | Setup controller (Setup screen + `bench`) | [Doc](./2026-11-24-setup-controller-story.md) | 5 | S1 | — | ✅ Done |
| S4 | Train controller (Train screen + `train`) | [Doc](./2026-11-24-train-controller-story.md) | 5 | S1 | — | ✅ Done |
| S5 | App shell asks controllers about running work | [Doc](./2026-11-24-app-shell-busy-check-story.md) | 2 | S2, S3, S4 | — | ⬜ Not started |

**Status legend:** ⬜ Not started · 🚧 In progress · ✅ Done

## Delivery Order

1. S1 Move code into `domain/` and `views/`
2. S2 Voice changer controller, S3 Setup controller, S4 Train controller _(blocked by S1; these three can be built at the same time)_
3. S5 App shell asks controllers about running work _(blocked by S2, S3, S4)_

## Deferred to Later

- A controller for `HomeScreen`. It only opens other screens, so it has no logic to move.
- Splitting `domain/engine/rvc_engine.py` (522 lines) into smaller files. It is not part of MVC.

## Open Questions

- None
