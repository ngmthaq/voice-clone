# Title: Plan — Better noise filter for crowd noise

- Classification: feature
- Description: Add a "smart" gate that opens only near your own voice level, and a spectral filter with an on/off switch that removes steady background murmur before the RVC model.

---

## Approach Summary / Goal

- **Smart gate:** the gate already learns the quiet noise floor. Now it will also learn **your voice level**, which is the loudest recent speech. It decays slowly over time. The gate opens only when a sound is louder than the floor **and** within N dB of your voice. People farther away are quieter, so the gate stays closed for them.
- **Spectral filter** (new `NoiseReducer`): it splits the sound into short frames and frequency bands (an STFT). For each band it learns the steady noise level from the quietest recent frames, then turns that band down. It runs after the hum filter and before the gate. It uses only numpy/scipy. A switch turns it on or off. It has no other controls.
- Goal: less noise between words (from the gate) and less steady murmur while you speak (from the filter), with no new libraries and only a small extra delay.

## Functional Requirements

- `GateSettings` gets `open_below_voice_db: float = 20.0`. 0 = off, which keeps today's behavior.
- The gate learns your voice level only from frames that already pass the floor rule. Before it knows your voice level, it uses the floor rule alone.
- The gate opens only if the level is above `floor + open_above_floor_db` and above `voice_level − open_below_voice_db`. Hold and Open early work as before.
- The voice level falls slowly, a fixed number of dB per frame.
- New setting `gate_open_below_voice_db` (0–40, default 20) in `Settings`, saved, included in presets and reset. It is a new field in the gate panel: "Below my voice (dB)".
- `NoiseReducer.process(audio)` returns the same number of samples it gets. It keeps state between calls, so chunked output = one-shot output.
- On steady white noise, the reducer lowers the level by at least 8 dB once it has learned the noise. A clear tone in that noise keeps most of its energy.
- New setting `noise_reduction: bool = True` in `Settings`, saved in `settings.toml`. It is not part of presets. "Reset Advanced settings" sets it to `True`.
- A "Noise filter" `Switch` in the gate panel shows the setting. `ChangerController.set_noise_reduction(on)` saves it and calls `ConversionPipeline.set_noise_reduction(on)`, which works while the pipeline runs.
- When the switch is off, the pipeline skips the reducer, and the audio is the same as without this feature. When it is turned back on, the reducer starts fresh (its state is reset).
- `ConversionPipeline` runs the reducer after the hum filter and before the gate. `_reset_state` resets it.

## Non-Functional Requirements

- The reducer adds at most ~20 ms of delay. There is no extra delay when it is off.
- CPU cost stays small. Nothing runs in the audio callback.
- No new dependency. No Textual code in `domain/` or `controllers/`. Follows `CODING_CONVENTIONS.md`. `pytest` and `ruff check .` pass.

## Files in Scope

- Create: `src/voice_clone/domain/audio/noise_reducer.py`, `tests/domain/audio/test_noise_reducer.py`
- Change: `src/voice_clone/domain/audio/noise_gate.py`, `src/voice_clone/domain/audio/pipeline.py`, `src/voice_clone/domain/audio/__init__.py`, `src/voice_clone/domain/config.py`, `src/voice_clone/controllers/changer_controller.py`, `src/voice_clone/views/main_screen.py`, `src/voice_clone/views/app.tcss` (only if the switch needs layout), `docs/USAGE.md`
- Tests to change: `tests/domain/audio/test_noise_gate.py`, `tests/domain/audio/test_pipeline.py`, `tests/controllers/test_changer_controller.py`, `tests/views/test_main_screen.py`

## Risks & Assumptions

- Risk: no filter here fully removes nearby voices while you speak.
- Risk: the default of 20 dB is a guess. You need to test it by listening.
- Risk: the spectral filter can add a faint "watery" sound (musical noise). It keeps a gain floor of about −15 dB and smooths the gain to reduce that. If you hear it, you can now turn the filter off.
- Assumption: the switch is on by default, presets don't change it, reset turns it on, and it can be flipped while the pipeline runs.
- Assumption: delay with the filter on vs. off differs by ~16 ms. Flipping it while running may cause one short click.
- Assumption: old `settings.toml` files load with the defaults (20 dB, filter on).

## Open Questions / Blockers

- None

## Status

- [x] Ready to execute
- [ ] Blocked

## Task List

| # | Status | Task | Responsible Role | Dependencies | Acceptance Criteria | Skills |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | DONE | Create `NoiseReducer` in `domain/audio/noise_reducer.py` and export it. Use it in `ConversionPipeline.process_block` after `_remove_hum`, and reset it in `_reset_state`. Add a `noise_reduction` constructor argument and `set_noise_reduction(on)` to `ConversionPipeline`. | developer | none | Output length = input length. Chunked = one-shot. Off = audio unchanged by the reducer. Existing pipeline tests pass. `ruff check src` passes. | `.claude/guides/CLEAN_CODE/ENTRY_POINT.md` |
| 2 | DONE | Smart gate: add `open_below_voice_db` and voice-level tracking to the gate. Add `gate_open_below_voice_db` to `Settings`, presets, `GATE_SETTING_NAMES`, and controller save/apply. Add a new `GATE_FIELDS` row. Add `noise_reduction` to `Settings`, add `ChangerController.set_noise_reduction` (save, pass to the pipeline at start and while running, reset → True), and add a "Noise filter" `Switch` in the gate panel. Update `docs/USAGE.md`. | developer | task 1 (uses `ConversionPipeline.set_noise_reduction`) | Gate value 0 = today's output. The new field and the switch show and are saved. Presets don't change the switch. Reset turns it on. Existing tests pass. `ruff check src` passes. | `.claude/guides/CLEAN_CODE/ENTRY_POINT.md` |
| 3 | DONE | Tests for task 1: `test_noise_reducer.py` (length, chunked = one-shot, ≥8 dB drop on white noise, tone kept, silence stays silent). Pipeline tests: the reducer runs when on, is skipped when off, and can be flipped while running. | tester | task 1 | `pytest` passes. Each task 1 criterion has a passing test. | `.claude/agents/party-mode-tester.md#testing-workflow`, `.claude/guides/AAA_TESTING.md` |
| 4 | DONE | Tests for task 2: neighbour voice stays closed, a soft user word opens, 0 = old behavior, voice level decays, controller save/preset/reset of the new gate setting. Controller: the switch setting is saved, sent to a running pipeline, not changed by presets, and set to True by reset. Main screen: the switch shows the setting and flipping it calls the controller. | tester | task 2 | `pytest` and `ruff check .` pass. Each task 2 criterion has a passing test. | `.claude/agents/party-mode-tester.md#testing-workflow`, `.claude/guides/AAA_TESTING.md` |

Order: task 2 uses the new pipeline method, so tasks 1 and 2 run one after the other. Task 3 can run while task 2 is in progress.
