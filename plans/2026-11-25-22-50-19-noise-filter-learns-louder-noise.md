# Title: Plan — Let the noise filter learn louder background noise again

- Classification: bug
- Description: The noise filter checks for short quiet dips to tell speech from new background noise, so it keeps long speech clear and still learns noise that gets louder.

---

## Approach Summary / Goal

- **Root cause:** the current uncommitted fix treats any frame more than ~6 dB above the learned noise as speech. While a frame counts as speech, the learned noise level rises only ~0.27 dB per second. If the background gets louder (a crowd, a fan), every frame looks like speech, so the filter almost never learns the new noise. In a test with noise that got 20 dB louder, it removed 0.3 dB after 10 s. The old filter removed 10.5 dB.
- **Fix:** the filter keeps the total power of each raw (unsmoothed) frame from the last ~2 s. Speech always has short dips between syllables and words that fall close to the noise level, and steady noise does not. If even the quietest frame in those 2 s is well above the learned noise, the floor has really risen, and the filter learns it fast. Otherwise the current rules stay: slow rise during speech, normal rise in pauses.
- **Goal:** long speech keeps its high frequencies, and background noise that gets 20 dB louder is mostly removed within ~5 s.

## Functional Requirements

- `NoiseReducer` keeps the raw total power of each frame from the last ~2 s (about 125 frames).
- If the quietest of those frames is above `SPEECH_POWER_RATIO × learned noise total`, the learned noise rises at a fast rate. The developer picks the rate so that the next requirement passes.
- After white noise gets 20 dB louder, the filter removes at least 8 dB of it in the 5th–6th second after the change.
- Speech with short word gaps keeps its 3.5–8 kHz band within 3 dB of the clean signal after 9 s.
- Steady white noise drops by at least 8 dB after the filter learns it (unchanged).
- Everything else stays the same: output length equals input length, chunked output equals one-shot output, `reset()` clears the new history, silence stays silent, and the delay is still 512 samples.

## Non-Functional Requirements

- No new dependency. The extra work per frame is small, using a fixed-size numpy ring buffer or a `deque`. Nothing runs in the audio callback.
- Follows `CODING_CONVENTIONS.md` and the no-redundant-comments rule. `pytest` passes, and `ruff check src tests` passes.

## Files in Scope

- Change: `src/voice_clone/domain/audio/noise_reducer.py`
- Change: `tests/domain/audio/test_noise_reducer.py`
- Change: `plans/2026-11-25-20-37-20-better-noise-filter.md` (the "at least 10 dB" line becomes 8 dB)

## Risks & Assumptions

- Assumption: real speech has dips close to the noise level at least once every 2 s. Very connected speech with no gap for more than 2 s will start being learned as noise. It is then learned at the fast rate, so its highs drop again until the next pause.
- The dip check uses raw frame power, not the smoothed power. Smoothed power stays high through short gaps, which would hide the dips.
- The long-speech test signal gets short word gaps (~150 ms about every 1 s) so it acts like real speech. The current signal never dips, so it would count as noise under the new rule.
- After this fix, a sudden loud noise is still let through for ~2 s before the filter starts learning it. That is the window length.

## Open Questions / Blockers

- None

## Status

- [x] Ready to execute
- [ ] Blocked

## Task List

| # | Status | Task | Responsible Role | Dependencies | Acceptance Criteria | Skills |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | DONE | In `noise_reducer.py`, add a ~2 s history of raw frame total power. In `_update_noise`, rise at a new fast rate when the quietest frame in the history is above `SPEECH_POWER_RATIO × noise total`. Otherwise keep the current speech and pause rules. Clear the history in `reset()`. | developer | none | A +20 dB step in white noise loses ≥8 dB in the 5th–6th second after the step. Existing reducer tests pass. `ruff check src` passes. | `.claude/guides/CLEAN_CODE/ENTRY_POINT.md` |
| 2 | DONE | In `plans/2026-11-25-20-37-20-better-noise-filter.md`, change the "at least 10 dB" requirement to 8 dB. | developer | none | The plan text matches the 8 dB test. | `.claude/guides/CLEAN_CODE/ENTRY_POINT.md` |
| 3 | DONE | In `test_noise_reducer.py`, add `test_noise_that_gets_louder_is_learned_within_5_seconds` (a +20 dB step, ≥8 dB drop in the 5th–6th second after it). Add ~150 ms gaps about every 1 s to `_speech_like`. | tester | task 1 | The new test fails on the current uncommitted code and passes after task 1. `test_long_speech_keeps_its_high_frequencies` still passes. Full `pytest` and `ruff check tests` pass. | `.claude/agents/party-mode-tester.md#testing-workflow`, `.claude/guides/AAA_TESTING.md` |

Order: tasks 1 and 2 can run at the same time. Task 3 runs after task 1.
