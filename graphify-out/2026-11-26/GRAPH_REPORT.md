# Graph Report - voice-clone  (2026-11-26)

## Corpus Check
- 185 files · ~100,755 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: (none) 5, .tcss 1, .ipynb 1)

## Summary
- 2422 nodes · 5575 edges · 166 communities (139 shown, 27 thin omitted)
- Extraction: 81% EXTRACTED · 19% INFERRED · 0% AMBIGUOUS · INFERRED: 1033 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f1ad143b`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_app.py
- ConversionPipeline
- test_pipeline.py
- MainScreen
- rmvpe.py
- test_main_screen.py
- SetupScreen
- test_setup_screen.py
- test_train_screen.py
- test_rvc_engine.py
- test_trainer.py
- download.py
- numpy
- StreamingRunner
- ndarray
- changer_controller.py
- TrainingError
- cli.py
- test_applio.py
- SetupController
- env
- setup_check.py
- torch
- test_changer_controller.py
- agile-planning/SKILL.md
- test_cli.py
- TrainPanelWidget
- .start
- RingBuffer
- RMVPE
- LayerNorm
- rvc_engine.py
- pull-request/SKILL.md
- Tester
- SynthesizerTrnMs256NSFsid
- Applio
- evaluate
- .schedule_save
- party-mode/SKILL.md
- Settings
- VoiceCloneApp
- Secret Scanning Script
- SineGen
- Claude Hook Settings
- WN
- .begin_install
- setup_controller.py
- Project Root
- DiscriminatorP
- transforms.py
- VoiceProfile
- Developer
- AAA — Arrange, Act, Assert
- Execution Workflow
- Coding Conventions
- web-test/SKILL.md
- Vulnerability Categories
- Step 1 — Project Overview
- pull-request-template.md
- Pull Request
- Title: Plan — voice-clone MVP
- Title: Plan — S1 Move code into `domain/` and `views/`
- Atomic Design
- Language & Framework Patterns
- Vulnerable Package Watchlist
- MonkeyPatch
- Code Review Checklist
- Install the app
- Voice Recording Script (about 12–15 minutes)
- Title: Plan — Add install and run scripts
- AGENT_RULES.md
- Researcher
- SOLID
- SECURITY_SCANNER/ENTRY_POINT.md
- SetupReport
- test_setup_controller.py
- onboarding/SKILL.md
- Step 1 — Brainstorming (Root Agent)
- Step 6 — Reply to and Resolve Threads
- Train a New Voice
- Use the voice changer
- Data Handling
- Functional Requirements
- Step 6 — Review (Root Agent)
- Step 1 — Choose the Access Method
- S1 — Move code into `domain/` and `views/`
- AI / LLM Security
- Report Format
- Authentication & Access Control
- Phase 6 — Create Tickets
- Step 2 — Planning (Root Agent)
- Party-Mode
- Step 4 — Triage and Group Comments
- Step 5 — Run Tests in the Browser
- Third-Party Notices
- Step 3 — Train
- Clean Code
- Security Scanner
- Secret Patterns
- Title: Plan — S2 Voice changer controller
- Step 4 — Delegation to Sub-Agents
- Step 6 — Create the PR
- Step 3 — Fetch Reviewer Comments
- Step 5 — Resolve via Party-Mode
- Step 10 — Offer to Post Review (File + Line Comments)
- Step 3 — Fetch the Code Diff
- Step 2 — Find the Target PR
- TrainScreen
- Step 2 — Brainstorming
- voice-clone
- FakePipeline
- Step 3 — User Approval Gate
- Step 7 — Summary Report to User
- test_device.py
- test_train_controller.py
- Title: Plan — Install scripts ask questions; download models and Applio
- Graphify Setup
- errors.py
- Phase 3 — Break Down Work
- Voice files
- S4 — Train controller (Train screen + `train` command)
- RTK Setup
- ChangerController
- FakeTimer
- Phase 5 — Generate Docs
- Additional Information
- train_voice
- step-6-test-report.md
- .__init__
- .bench
- Step 1 — Check Browser Permission
- Step 3 — Test Plan
- Step 4 — Approval Gate
- S2 — Voice changer controller
- TrainController
- Title: Plan — Better noise filter for crowd noise
- Install
- KISS.md
- models.py
- RvcEngine
- run.sh script
- ._busy_message
- test_commands.py
- MultiHeadAttention
- .load
- bench.py
- .__init__
- LevelMeterWidget
- Title: Plan — One automatic run script
- pipeline.py
- FakeRunner
- HomeScreen
- run.ps1
- saved_toml
- _Stoppable
- ElementwiseAffine

## God Nodes (most connected - your core abstractions)
1. `SetupController` - 117 edges
2. `ChangerController` - 81 edges
3. `TrainController` - 73 edges
4. `MainScreen` - 57 edges
5. `Settings` - 46 edges
6. `NoiseGate` - 45 edges
7. `ConversionPipeline` - 45 edges
8. `TrainingError` - 45 edges
9. `load_settings()` - 43 edges
10. `VoiceCloneError` - 42 edges

## Surprising Connections (you probably didn't know these)
- `Files in Scope` --references--> `ChangerController`  [INFERRED]
  plans/2026-11-24-09-07-30-s2-voice-changer-controller.md → src/voice_clone/controllers/changer_controller.py
- `Approach Summary / Goal` --references--> `NoiseReducer`  [INFERRED]
  plans/2026-11-25-20-37-20-better-noise-filter.md → src/voice_clone/domain/audio/noise_reducer.py
- `Files in Scope` --references--> `measure_and_save()`  [INFERRED]
  plans/2026-11-26-21-36-24-one-automatic-run-script.md → src/voice_clone/domain/bench.py
- `Settings` --references--> `Settings`  [INFERRED]
  .claude/references/CODING_CONVENTIONS.md → src/voice_clone/domain/config.py
- `Task List` --references--> `VoiceCloneError`  [INFERRED]
  plans/2026-11-26-21-15-55-install-questions-and-model-download.md → src/voice_clone/domain/errors.py

## Import Cycles
- None detected.

## Communities (166 total, 27 thin omitted)

### Community 0 - "test_app.py"
Cohesion: 0.15
Nodes (25): FakeController, FakeScreen, _push(), _run(), scenario(), ScreenWithoutController, test_a_different_key_does_not_confirm(), body() (+17 more)

### Community 1 - "ConversionPipeline"
Cohesion: 0.17
Nodes (6): Main parts (`src/voice_clone/`), Functional Requirements, Task List, ConversionPipeline, _fit_history(), _tail_or_pad()

### Community 2 - "test_pipeline.py"
Cohesion: 0.05
Nodes (51): fake_engine(), FakeEngine, input_device(), output_device(), _block(), fake_sd(), FakeInputStream, FakeOutputStream (+43 more)

### Community 3 - "MainScreen"
Cohesion: 0.18
Nodes (3): Functional Requirements, Tasks, MainScreen

### Community 4 - "rmvpe.py"
Cohesion: 0.06
Nodes (11): BiGRU, ConvBlockRes, Decoder, DeepUnet, E2E, Encoder, Intermediate, MelSpectrogram (+3 more)

### Community 5 - "test_main_screen.py"
Cohesion: 0.05
Nodes (35): empty_environment(), _run(), test_advanced_reset_restores_all_advanced_defaults(), test_advanced_reset_turns_bump_filter_switch_back_on(), test_advanced_reset_turns_noise_filter_switch_back_on(), test_advanced_tab_holds_voice_match_and_gate(), test_all_settings_are_disabled_while_running(), test_below_voice_input_shows_default() (+27 more)

### Community 6 - "SetupScreen"
Cohesion: 0.20
Nodes (3): Functional Requirements, Tasks, SetupScreen

### Community 7 - "test_setup_screen.py"
Cohesion: 0.10
Nodes (31): _applio_line(), environment(), facts(), fake_applio(), FakeApplio, _fill_models(), _lines(), _run() (+23 more)

### Community 8 - "test_train_screen.py"
Cohesion: 0.12
Nodes (29): environment(), _press_start(), _run(), scenario(), _start_blocking_training(), _status(), test_a_different_key_does_not_confirm(), body() (+21 more)

### Community 9 - "test_rvc_engine.py"
Cohesion: 0.08
Nodes (19): _cpu_rmvpe_init(), _engine(), FakeEncoder, FakePitch, index_loads(), test_convert_before_load_raises_model_load_error(), test_convert_length_matches_target_rate(), test_convert_tail_decodes_only_the_last_frames() (+11 more)

### Community 10 - "test_trainer.py"
Cohesion: 0.17
Nodes (15): _fake_prepare(), FakeApplio, _ffmpeg(), _run(), test_bad_sample_rate_is_rejected(), test_bad_voice_name_is_rejected(), test_epochs_done_reads_applio_progress(), test_existing_checkpoint_resumes_without_preprocessing() (+7 more)

### Community 11 - "download.py"
Cohesion: 0.12
Nodes (18): base_model_files(), base_model_paths(), BaseModelFile, BaseModelPaths, ensure_base_models(), _quiet_progress_bars(), _report(), _verify() (+10 more)

### Community 12 - "numpy"
Cohesion: 0.05
Nodes (93): Approach Summary / Goal, Files in Scope, Functional Requirements, Non-Functional Requirements, Open Questions / Blockers, Risks & Assumptions, Status, Task List (+85 more)

### Community 14 - "ndarray"
Cohesion: 0.17
Nodes (10): _coarse_pitch(), _fit_length(), _follow_loudness(), _loudness_envelope(), _pad_tail(), _smooth_pitch(), test_follow_loudness_full_matches_source_level(), test_follow_loudness_zero_returns_output_unchanged() (+2 more)

### Community 15 - "changer_controller.py"
Cohesion: 0.19
Nodes (19): Task List, AudioDevice, find_device_by_name(), find_virtual_output(), list_input_devices(), list_output_devices(), _query_devices(), rescan_devices() (+11 more)

### Community 16 - "TrainingError"
Cohesion: 0.24
Nodes (17): TrainingError, collect_audio_files(), _duration_seconds(), prepare_dataset(), _refuse_inputs_inside(), _safe_stem(), test_missing_program_raises(), _fake_ffmpeg() (+9 more)

### Community 17 - "cli.py"
Cohesion: 0.20
Nodes (10): _build_parser(), main(), _rescan_audio_devices(), _run_bench_command(), _run_download_models(), _run_install_applio(), _run_measure_speed(), _run_train() (+2 more)

### Community 18 - "test_applio.py"
Cohesion: 0.17
Nodes (18): _make(), RecordingRunner, _step(), test_core_command_without_install_raises(), test_core_commands_point_applio_to_our_logs_folder(), test_extract_device_avoids_mps_on_macos(), test_extract_fails_when_no_features_are_written(), test_find_python_missing_explains_how_to_install() (+10 more)

### Community 19 - "SetupController"
Cohesion: 0.11
Nodes (19): BenchSession, SetupController, test_busy_follows_set_busy(), test_busy_message_clears_after_end_calls(), test_busy_message_prefers_install_then_download_then_measure(), test_busy_message_while_downloading(), test_busy_message_while_measuring(), test_installing_follows_begin_and_end_install() (+11 more)

### Community 22 - "setup_check.py"
Cohesion: 0.37
Nodes (13): _applio(), _audio(), Check, _compute(), Facts, _is_virtual_device(), _is_virtual_output(), _models() (+5 more)

### Community 23 - "torch"
Cohesion: 0.20
Nodes (15): add_timing_signal_1d(), cat_timing_signal_1d(), convert_pad_shape(), fused_add_tanh_sigmoid_multiply(), generate_path(), get_timing_signal_1d(), kl_divergence(), rand_gumbel() (+7 more)

### Community 24 - "test_changer_controller.py"
Cohesion: 0.05
Nodes (18): EngineStub, start_running(), test_begin_start_returns_request_and_loading_status(), test_change_pitch_does_not_touch_engine_when_not_converting(), test_change_pitch_updates_running_engine(), test_levels_are_zero_after_stop_even_if_pipeline_reports_while_stopping(), test_pipeline_receives_store_callbacks(), test_reset_advanced_restores_default_options() (+10 more)

### Community 25 - "agile-planning/SKILL.md"
Cohesion: 0.11
Nodes (15): 1a. Find the input source, 1b. Find the input type, 1c. Show what you got, Phase 1 — Take Input, 2a. Ask clarifying questions first, 2b. Look at the codebase (read-only), 2c. Write the analysis, Phase 2 — Brainstorm (+7 more)

### Community 26 - "test_cli.py"
Cohesion: 0.09
Nodes (27): _by_values(), _no_log_file(), patch_bench_fakes(), test_bench_ctrl_c_returns_exit_code_130(), test_bench_prints_the_error_when_the_bench_fails(), test_bench_prints_the_table_and_the_recommended_preset(), test_bench_says_when_no_preset_keeps_up(), test_bench_with_an_unknown_voice_prints_a_message_and_returns_error() (+19 more)

### Community 27 - "TrainPanelWidget"
Cohesion: 0.18
Nodes (3): Functional Requirements, Tasks, TrainPanelWidget

### Community 28 - ".start"
Cohesion: 0.16
Nodes (16): options(), test_busy_message_is_none_after_finish(), test_busy_message_reports_training_while_running(), test_drain_events_empties_the_queue(), test_epoch_progress_ignores_another_voice(), test_epoch_progress_ignores_lines_without_an_epoch(), test_epoch_progress_is_capped_at_target_epochs(), test_epoch_progress_returns_epochs_done_for_the_voice() (+8 more)

### Community 29 - "RingBuffer"
Cohesion: 0.26
Nodes (10): RingBuffer, test_clear_empties_buffer(), test_non_positive_capacity_is_rejected(), test_overflow_overwrites_oldest_samples(), test_read_returns_written_samples_in_order(), test_trim_below_limit_keeps_everything(), test_trim_drops_oldest_samples_beyond_limit(), test_underrun_zero_pads_the_read() (+2 more)

### Community 30 - "RMVPE"
Cohesion: 0.27
Nodes (5): _rmvpe_hidden(), _RmvpePitchExtractor, RMVPE, test_rmvpe_split_matches_the_original_network(), test_rmvpe_with_recurrent_on_cpu_gives_same_pitch()

### Community 31 - "LayerNorm"
Cohesion: 0.14
Nodes (5): Decoder, Encoder, FFN, ConvReluNorm, LayerNorm

### Community 32 - "rvc_engine.py"
Cohesion: 0.24
Nodes (9): _adapt_weight_norm_keys(), _ensure_index(), _load_index(), _load_voice(), _LoadedVoice, _single_thread_faiss(), _synthesizer_class(), ModelLoadError (+1 more)

### Community 33 - "pull-request/SKILL.md"
Cohesion: 0.13
Nodes (7): Step 3 — Choose the Target Branch, Step 4 — Collect Context, Step 5 — Fill the Template, Step 7 — Summary Report, Suggested format, Step 4 — Check That the Code Matches the Requirements, Step 9 — Write the Review Report

### Community 34 - "Tester"
Cohesion: 0.11
Nodes (21): Additional Skill References, Code-First, Constraints, Delegation Prompt Template, Failure Modes, Inputs, Note for Code-First and Test-First, Outputs (+13 more)

### Community 35 - "SynthesizerTrnMs256NSFsid"
Cohesion: 0.09
Nodes (8): Generator, GeneratorNSF, PosteriorEncoder, ResidualCouplingBlock, SynthesizerTrnMs256NSFsid, SynthesizerTrnMs256NSFsid_nono, SynthesizerTrnMs768NSFsid, SynthesizerTrnMs768NSFsid_nono

### Community 37 - "evaluate"
Cohesion: 0.29
Nodes (20): evaluate(), _by_name(), _facts(), _ready_models(), test_applio_can_be_installed_when_git_and_python_are_there(), test_applio_install_needs_git_and_python_first(), test_cuda_shows_the_card_name(), test_cuda_shows_whether_fp16_is_used() (+12 more)

### Community 39 - "party-mode/SKILL.md"
Cohesion: 0.22
Nodes (4): DRY — Don't Repeat Yourself, DRY Rules, Separation of Concerns, SoC Rules

### Community 40 - "Settings"
Cohesion: 0.14
Nodes (23): Functional Requirements, _first_start_settings(), apply_preset(), load_settings(), _preset(), save_settings(), Settings, settings_path() (+15 more)

### Community 41 - "VoiceCloneApp"
Cohesion: 0.14
Nodes (13): VoiceCloneApp, test_r_key_exits_with_restart(), scenario(), open_voice_changer(), scenario(), test_no_voices_shows_status_message(), scenario(), test_pipeline_started_after_the_screen_closed_is_stopped() (+5 more)

### Community 42 - "Secret Scanning Script"
Cohesion: 0.50
Nodes (7): main(), report(), scan_diff(), scan_files(), scan_line(), severity_color(), scan-secrets.sh script

### Community 44 - "Claude Hook Settings"
Cohesion: 0.50
Nodes (3): hooks, PreToolUse, $schema

### Community 45 - "WN"
Cohesion: 0.18
Nodes (3): ResBlock1, ResidualCouplingLayer, WN

### Community 46 - ".begin_install"
Cohesion: 0.17
Nodes (18): FakeApplio, test_begin_install_clears_old_events(), test_drain_events_drops_a_blank_transient(), test_drain_events_drops_a_transient_after_stop(), test_drain_events_drops_a_transient_when_there_is_no_runner(), test_drain_events_empties_the_queue(), test_drain_events_keeps_a_non_blank_transient_while_running(), test_install_applio_cli_installs_into_the_dot_applio_folder() (+10 more)

### Community 47 - "setup_controller.py"
Cohesion: 0.15
Nodes (20): _missing(), apply_engine_options(), auto_presets(), BenchResult, fits(), measure_and_save(), pick_preset(), _fake_loads() (+12 more)

### Community 49 - "DiscriminatorP"
Cohesion: 0.18
Nodes (4): DiscriminatorP, DiscriminatorS, MultiPeriodDiscriminator, MultiPeriodDiscriminatorV2

### Community 50 - "transforms.py"
Cohesion: 0.23
Nodes (6): ConvFlow, DDSConv, piecewise_rational_quadratic_transform(), rational_quadratic_spline(), searchsorted(), unconstrained_rational_quadratic_spline()

### Community 52 - "VoiceProfile"
Cohesion: 0.16
Nodes (10): VoiceEngine, _build_profile(), discover_profiles(), VoiceProfile, _make_voice(), test_discovers_profiles_sorted_by_name_with_index(), test_folder_without_pth_is_skipped(), test_loose_files_in_voices_folder_are_ignored() (+2 more)

### Community 53 - "Developer"
Cohesion: 0.18
Nodes (11): Additional Skill References, Constraints, Delegation Prompt Template, Developer, Failure Modes, Inputs, Outputs, Position in the Workflow (+3 more)

### Community 54 - "AAA — Arrange, Act, Assert"
Cohesion: 0.18
Nodes (8): AAA — Arrange, Act, Assert, Common Violations, Rules, Shared Arrange, Test Naming, The Pattern, Step 5 — Load Guides, Step 8 — Apply AAA Testing Review

### Community 55 - "Execution Workflow"
Cohesion: 0.18
Nodes (11): Execution Workflow, Step 10 — Propose Patches, Step 1 — Find the Scope and Look Around, Step 2 — Dependency Audit (SCA), Step 3 — Secrets & Exposure Scan, Step 4 — Static Analysis (SAST), Step 5 — Vulnerability Deep Scan, Step 6 — AI / LLM Security (+3 more)

### Community 56 - "Coding Conventions"
Cohesion: 0.17
Nodes (12): Code Order in a File, Coding Conventions, Comments, Controllers, Cross-Platform (macOS + Windows), Errors and Logging, Folder Structure (src layout), Real-Time Audio (+4 more)

### Community 57 - "web-test/SKILL.md"
Cohesion: 0.36
Nodes (3): Constraints, Step-by-Step Instructions, Web Test

### Community 58 - "Vulnerability Categories"
Cohesion: 0.20
Nodes (9): Business Logic, Command Injection (CWE-78), Cross-Site Scripting — XSS (CWE-79), Cryptography, Injection, Input Validation, Other Injection Sinks, SQL Injection (CWE-89) (+1 more)

### Community 59 - "Step 1 — Project Overview"
Cohesion: 0.20
Nodes (10): 1.1 — Project Name and Description, 1.2 — Programming Languages and Frameworks, 1.3 — Package Manager, 1.4 — Key Libraries, 1.5 — Database, 1.6 — Doc Directory, 1.7 — Testing Workflow, 1.8 — Playwright Check (+2 more)

### Community 60 - "pull-request-template.md"
Cohesion: 0.20
Nodes (8): Changes Made, Checklist, Description, How to Test, Related Issues, Screenshots, Type of Change, Step 2 — Find the PR Template

### Community 61 - "Pull Request"
Cohesion: 0.20
Nodes (10): `create`, Pull Request, `resolve`, `review`, Rules for All Modes, Rules for `create`, Rules for `resolve`, Rules for `review` (+2 more)

### Community 62 - "Title: Plan — voice-clone MVP"
Cohesion: 0.20
Nodes (9): Approach Summary / Goal, Files in Scope, Functional Requirements, Non-Functional Requirements, Open Questions / Blockers, Outcome (2026-11-18), Risks & Assumptions, Status (+1 more)

### Community 63 - "Title: Plan — S1 Move code into `domain/` and `views/`"
Cohesion: 0.20
Nodes (9): Approach Summary / Goal, Files in Scope, Functional Requirements, Non-Functional Requirements, Open Questions / Blockers, Risks & Assumptions, Status, Task List (+1 more)

### Community 64 - "Atomic Design"
Cohesion: 0.22
Nodes (8): Atomic Design, Atomic Design Rules, Atoms, Folder Structure, Molecules, Organisms, Pages, Templates

### Community 65 - "Language & Framework Patterns"
Cohesion: 0.22
Nodes (9): Go, Java, JavaScript / TypeScript, Language & Framework Patterns, .NET / C#, PHP, Python, Ruby (+1 more)

### Community 66 - "Vulnerable Package Watchlist"
Cohesion: 0.22
Nodes (9): Cargo, Go Modules, Maven / Gradle, npm, pip, Reporting Format, RubyGems, Triage Rules (+1 more)

### Community 67 - "MonkeyPatch"
Cohesion: 0.14
Nodes (12): test_check_reports_the_error_when_gathering_facts_fails(), boom(), test_check_uses_the_exception_name_when_it_has_no_message(), test_download_passes_progress_to_ensure_base_models_and_returns_none(), test_download_returns_an_error_for_a_plain_exception(), test_download_returns_the_voice_clone_error_text(), failing(), test_measure_speed_reports_progress_and_the_saved_preset() (+4 more)

### Community 68 - "Code Review Checklist"
Cohesion: 0.22
Nodes (7): Atomic Design _(UI only)_, Code Review Checklist, DRY _(All)_, KISS _(All)_, Separation of Concerns _(All)_, SOLID _(OOP)_, Step 6 — Apply Clean Code Review

### Community 69 - "Install the app"
Cohesion: 0.40
Nodes (5): Install the app, macOS (Apple Silicon or Intel), Windows: do I have an NVIDIA card?, Windows with an NVIDIA card (PowerShell), Windows without an NVIDIA card (PowerShell)

### Community 70 - "Voice Recording Script (about 12–15 minutes)"
Cohesion: 0.22
Nodes (9): Part 1 — Normal speech, Part 2 — Questions and answers, Part 3 — Feelings, Part 4 — Range, Part 5 — Short story, Part 6 — Work and technology, Part 7 — Mixed sentences, Part 8 — Free talk (2–3 minutes) (+1 more)

### Community 71 - "Title: Plan — Add install and run scripts"
Cohesion: 0.20
Nodes (9): Approach Summary / Goal, Files in Scope, Functional Requirements, Non-Functional Requirements, Open Questions / Blockers, Risks & Assumptions, Status, Task List (+1 more)

### Community 72 - "AGENT_RULES.md"
Cohesion: 0.17
Nodes (9): AGENT RULES, CLAUDE, CODING CONVENTIONS, graphify, GRAPHIFY KNOWLEDGE GRAPH, PROJECT OVERVIEW, AGENT RULES, DO (+1 more)

### Community 73 - "Researcher"
Cohesion: 0.25
Nodes (8): Constraints, Failure Modes, Inputs, Outputs, Position in the Workflow, Purpose, Researcher, Workflow Steps

### Community 74 - "SOLID"
Cohesion: 0.25
Nodes (7): D — Dependency Inversion Principle, I — Interface Segregation Principle, L — Liskov Substitution Principle, O — Open/Closed Principle, S — Single Responsibility Principle, SOLID, SOLID Rules

### Community 76 - "SetupReport"
Cohesion: 0.25
Nodes (16): _models_check(), SetupReport, check(), make_facts(), test_can_measure_when_models_are_present_and_a_voice_exists(), test_cannot_measure_when_models_are_missing(), test_cannot_measure_when_the_check_failed(), test_cannot_measure_without_voices() (+8 more)

### Community 77 - "test_setup_controller.py"
Cohesion: 0.12
Nodes (18): applio(), bench_env(), __init__(), bench_run(), fake_run(), controller(), run_bench(), test_bench_does_not_reload_an_engine_that_is_loaded() (+10 more)

### Community 78 - "onboarding/SKILL.md"
Cohesion: 0.18
Nodes (7): Step 2 — Coding Conventions, Step 3 — Finish, How to Use This Skill, Onboarding Workflow, Override Notice, Project Onboarding, Purpose

### Community 79 - "Step 1 — Brainstorming (Root Agent)"
Cohesion: 0.25
Nodes (8): Brainstorming Dialogue, Bug, Check Task Complexity, Classify the Intent, Feature, Step 1 — Brainstorming (Root Agent), Unclear Cases, Usage Notes

### Community 80 - "Step 6 — Reply to and Resolve Threads"
Cohesion: 0.25
Nodes (7): Do not resolve when, Push the changes first, Reply, then resolve — per accepted thread, Step 6 — Reply to and Resolve Threads, Using MCP, Using the browser, Using the CLI

### Community 81 - "Train a New Voice"
Cohesion: 0.25
Nodes (8): Before you start, Options, Step 1 — Record, Step 2 — Copy the recordings into the project, Step 4 — Use the voice, Train a New Voice, Troubleshooting, Where files go

### Community 82 - "Use the voice changer"
Cohesion: 0.22
Nodes (9): Change your voice, If the voice lags, drops or comes late, Logs, Make the voice match better, Measure the speed, Noise gate and noise filter, Performance presets, Speed and delay (+1 more)

### Community 83 - "Data Handling"
Cohesion: 0.29
Nodes (7): Data Handling, Insecure Deserialization (CWE-502), Path Traversal (CWE-22), Sensitive Data Exposure (CWE-200, CWE-312, CWE-798), SSRF (CWE-918), Transport & Storage, XXE (CWE-611)

### Community 84 - "Functional Requirements"
Cohesion: 0.17
Nodes (14): Functional Requirements, Risks & Assumptions, Risks & Assumptions, _measure_message(), _preset_title(), base_models_present(), config_dir(), log_dir() (+6 more)

### Community 85 - "Step 6 — Review (Root Agent)"
Cohesion: 0.29
Nodes (7): Checklist, Minimum Skill References, Review Feedback (when not qualified), Review Workflow, Routing, Rules, Step 6 — Review (Root Agent)

### Community 86 - "Step 1 — Choose the Access Method"
Cohesion: 0.29
Nodes (7): Find the platform, None available, Step 1 — Choose the Access Method, Tier 1 — Platform MCP (best), Tier 2 — Platform CLI (backup), Tier 3 — Claude browser control, What each mode needs

### Community 87 - "S1 — Move code into `domain/` and `views/`"
Cohesion: 0.12
Nodes (16): Acceptance Criteria, Estimate, Functional Requirements, Goal, Non-Functional Requirements, Out of Scope, Requirements, S1 — Move code into `domain/` and `views/` (+8 more)

### Community 88 - "AI / LLM Security"
Cohesion: 0.33
Nodes (6): AI / LLM Security, Data Leakage via Prompts, Indirect Prompt Injection (RAG / Agentic), Insecure Tool Use, Model & Infrastructure Basics, Prompt Injection (CWE-1336)

### Community 89 - "Report Format"
Cohesion: 0.33
Nodes (6): 1. Scan Summary, 2. Finding Cards, 3. Dependency Audit, 4. Secrets Scan, 5. Proposed Patches, Report Format

### Community 90 - "Authentication & Access Control"
Cohesion: 0.33
Nodes (6): Authentication & Access Control, Broken Authorization / IDOR / BOLA (CWE-284, CWE-639), CSRF (CWE-352), JWT Weaknesses, Mass Assignment (CWE-915), Session & Privilege

### Community 91 - "Phase 6 — Create Tickets"
Cohesion: 0.22
Nodes (8): 6a. Choose where to create the tickets, 6b. Create story tickets, 6c. Create task tickets, 6d. Update the overview, 6e. Show a summary, MCP Reference, No MCP — use the browser, Phase 6 — Create Tickets

### Community 92 - "Step 2 — Planning (Root Agent)"
Cohesion: 0.33
Nodes (6): Additional rules for `bug` plans, Minimum Skill References, Plan Template, Planning Rules, Step 2 — Planning (Root Agent), Usage Notes

### Community 93 - "Party-Mode"
Cohesion: 0.33
Nodes (6): Common Rules, Constraints, Loop Guard, Party-Mode, Step-by-Step Instructions, Sub-Agent Roles

### Community 94 - "Step 4 — Triage and Group Comments"
Cohesion: 0.33
Nodes (5): Classify each comment that needs work, Group related comments, Remove comments that need no work, Step 4 — Triage and Group Comments, Write the triage table

### Community 95 - "Step 5 — Run Tests in the Browser"
Cohesion: 0.33
Nodes (5): 1. Start the browser, 2. Run each test case, 3. Browser safety rules, 4. Finish, Step 5 — Run Tests in the Browser

### Community 97 - "Third-Party Notices"
Cohesion: 0.33
Nodes (5): ContentVec, Python dependencies, RMVPE, RVC-Project (Retrieval-based Voice Conversion WebUI), Third-Party Notices

### Community 98 - "Step 3 — Train"
Cohesion: 0.33
Nodes (6): How long does it take?, In the app, Pause and continue, Step 3 — Train, What training does, With a command

### Community 99 - "Clean Code"
Cohesion: 0.40
Nodes (5): Clean Code, Four contexts and their load order, How to Use This Guide, Reference Index, Universal Rules

### Community 100 - "Security Scanner"
Cohesion: 0.40
Nodes (5): Reference Files, Rules, Security Scanner, Severity Guide, When to Use

### Community 101 - "Secret Patterns"
Cohesion: 0.40
Nodes (5): Detected Patterns, How to Fix, Running the Scanner, Secret Patterns, What the Script Cannot Find — Check by Hand

### Community 102 - "Title: Plan — S2 Voice changer controller"
Cohesion: 0.22
Nodes (8): Approach Summary / Goal, Files in Scope, Non-Functional Requirements, Open Questions / Blockers, Risks & Assumptions, Status, Task List, Title: Plan — S2 Voice changer controller

### Community 103 - "Step 4 — Delegation to Sub-Agents"
Cohesion: 0.40
Nodes (5): Re-delegation, Running in parallel, Start the developer sub-agent, Start the tester sub-agent, Step 4 — Delegation to Sub-Agents

### Community 104 - "Step 6 — Create the PR"
Cohesion: 0.40
Nodes (5): Copy-paste, Step 6 — Create the PR, Using MCP, Using the browser, Using the CLI

### Community 105 - "Step 3 — Fetch Reviewer Comments"
Cohesion: 0.40
Nodes (4): Step 3 — Fetch Reviewer Comments, Using MCP, Using the browser, Using the CLI

### Community 106 - "Step 5 — Resolve via Party-Mode"
Cohesion: 0.40
Nodes (4): Check out the PR branch first, Hand the triage list to party-mode, Pass-through rules, Step 5 — Resolve via Party-Mode

### Community 107 - "Step 10 — Offer to Post Review (File + Line Comments)"
Cohesion: 0.40
Nodes (4): Posting via browser, Posting via CLI, Posting via MCP, Step 10 — Offer to Post Review (File + Line Comments)

### Community 108 - "Step 3 — Fetch the Code Diff"
Cohesion: 0.40
Nodes (4): Step 3 — Fetch the Code Diff, Using MCP, Using the browser, Using the CLI

### Community 109 - "Step 2 — Find the Target PR"
Cohesion: 0.40
Nodes (5): Step 2 — Find the Target PR, Using MCP, Using the browser, Using the CLI, What to get from the PR

### Community 110 - "TrainScreen"
Cohesion: 0.14
Nodes (11): Approach Summary / Goal, Files in Scope, Functional Requirements, Non-Functional Requirements, Open Questions / Blockers, Risks & Assumptions, Status, Task List (+3 more)

### Community 111 - "Step 2 — Brainstorming"
Cohesion: 0.40
Nodes (5): Brainstorming Dialogue, Check the Test Scope, Classify the Intent, Step 2 — Brainstorming, Usage Notes

### Community 112 - "voice-clone"
Cohesion: 0.40
Nodes (5): Documentation, Licenses, Quick start, Responsible use, voice-clone

### Community 114 - "Step 3 — User Approval Gate"
Cohesion: 0.50
Nodes (4): Approved, Cancels / Aborts, Requests Changes, Step 3 — User Approval Gate

### Community 115 - "Step 7 — Summary Report to User"
Cohesion: 0.50
Nodes (3): Step 7 — Summary Report to User, Summary Report Template, Usage Notes

### Community 116 - "test_device.py"
Cohesion: 0.18
Nodes (18): auto_cpu_threads(), configure_cpu_threads(), select_torch_device(), use_half_precision(), _capability(), _patch(), test_apple_gpu_uses_fp16_only_when_asked(), test_auto_threads_keeps_small_machines_unchanged() (+10 more)

### Community 117 - "test_train_controller.py"
Cohesion: 0.12
Nodes (22): VoiceCloneError, failing(), check(), FakeApplio, test_busy_message_is_none_when_idle(), test_check_options_accepts_existing_voice_with_force(), test_check_options_builds_train_options(), test_check_options_rejects_bad_name() (+14 more)

### Community 118 - "Title: Plan — Install scripts ask questions; download models and Applio"
Cohesion: 0.22
Nodes (8): Approach Summary / Goal, Files in Scope, Non-Functional Requirements, Open Questions / Blockers, Risks & Assumptions, Status, Task List, Title: Plan — Install scripts ask questions; download models and Applio

### Community 119 - "Graphify Setup"
Cohesion: 0.25
Nodes (7): Add to Claude Code, Build the graph, Graphify Setup, Install, Keep it up to date (optional), Search the graph, What you need

### Community 120 - "errors.py"
Cohesion: 0.17
Nodes (7): _parse_paths(), TrainingStoppedError, git_head(), find_python(), run_command(), _starts(), test_parse_paths_keeps_an_existing_path_with_spaces_whole()

### Community 121 - "Phase 3 — Break Down Work"
Cohesion: 0.25
Nodes (8): 3a. Epic → User Stories, 3b. User Story → Tasks, Dependencies, How to split a big story, Output format, Phase 3 — Break Down Work, What counts as a user story, What is NOT a user story

### Community 122 - "Voice files"
Cohesion: 0.67
Nodes (3): Add a voice you already have, Keep your voice in a GitHub Release, Voice files

### Community 123 - "S4 — Train controller (Train screen + `train` command)"
Cohesion: 0.25
Nodes (8): Acceptance Criteria, Estimate, Goal, Non-Functional Requirements, Out of Scope, Requirements, S4 — Train controller (Train screen + `train` command), User Story

### Community 124 - "RTK Setup"
Cohesion: 0.29
Nodes (6): Add to Claude Code, Check savings, Common commands, Install, Notes, RTK Setup

### Community 125 - "ChangerController"
Cohesion: 0.07
Nodes (4): ChangerController, LiveState, matching_preset(), test_initial_status_without_virtual_device_is_warning()

### Community 132 - "FakeTimer"
Cohesion: 0.29
Nodes (3): FakeTimer, TimerLog, timers()

### Community 133 - "Phase 5 — Generate Docs"
Cohesion: 0.25
Nodes (7): After writing, File path, Overview file, Overview template, Phase 5 — Generate Docs, Rules, Story doc template

### Community 134 - "Additional Information"
Cohesion: 0.33
Nodes (6): Additional Information, Audio pipeline (real time), Files and folders, How to run, PROJECT OVERVIEW, Target platforms

### Community 135 - "train_voice"
Cohesion: 0.21
Nodes (13): Approach Summary / Goal, Functional Requirements, _read_int(), require_tool(), DatasetInfo, epochs_done(), find_latest_weights(), _has_checkpoint() (+5 more)

### Community 136 - "step-6-test-report.md"
Cohesion: 0.50
Nodes (3): Step 6 — Test Report, Test Report Template, Usage Notes

### Community 138 - ".bench"
Cohesion: 0.14
Nodes (16): Approach Summary / Goal, Files in Scope, Non-Functional Requirements, Open Questions / Blockers, Status, Task List, Title: Plan — S3 Setup controller, Acceptance Criteria (+8 more)

### Community 139 - "Step 1 — Check Browser Permission"
Cohesion: 0.50
Nodes (4): 1. Check that the user allows the browser, 2. Check that a browser tool is available, 3. Get the target, Step 1 — Check Browser Permission

### Community 140 - "Step 3 — Test Plan"
Cohesion: 0.50
Nodes (4): Planning Rules, Step 3 — Test Plan, Test Plan Template, Usage Notes

### Community 141 - "Step 4 — Approval Gate"
Cohesion: 0.50
Nodes (4): Approved, Cancels, Requests Changes, Step 4 — Approval Gate

### Community 143 - "S2 — Voice changer controller"
Cohesion: 0.25
Nodes (8): Acceptance Criteria, Estimate, Goal, Non-Functional Requirements, Out of Scope, Requirements, S2 — Voice changer controller, User Story

### Community 144 - "TrainController"
Cohesion: 0.11
Nodes (8): Files in Scope, Open Questions / Blockers, Status, Task List, Title: Plan — S4 Train controller, TrainController, test_form_defaults_come_from_saved_settings(), test_stop_on_unmount_stops_an_existing_runner()

### Community 145 - "Title: Plan — Better noise filter for crowd noise"
Cohesion: 0.25
Nodes (7): Approach Summary / Goal, Files in Scope, Non-Functional Requirements, Open Questions / Blockers, Risks & Assumptions, Status, Title: Plan — Better noise filter for crowd noise

### Community 146 - "Install"
Cohesion: 0.22
Nodes (9): Check the setup, First start, Install, Install and start with one script, macOS, Other commands, Prerequisites, What the script does (+1 more)

### Community 148 - "models.py"
Cohesion: 0.17
Nodes (6): get_padding(), init_weights(), TextEncoder, Flip, Log, ResBlock2

### Community 149 - "RvcEngine"
Cohesion: 0.13
Nodes (6): _HubertContentEncoder, RvcEngine, _upsample_frames(), test_half_content_encoder_returns_half(), test_v1_encoder_skips_layers_but_matches_layer_nine(), test_v2_encoder_returns_last_hidden_state()

### Community 150 - "run.sh script"
Cohesion: 0.83
Nodes (3): hash_file(), run.sh script, usage()

### Community 151 - "._busy_message"
Cohesion: 0.18
Nodes (10): Acceptance Criteria, Estimate, Functional Requirements, Goal, Non-Functional Requirements, Out of Scope, Requirements, S5 — App shell asks controllers about running work (+2 more)

### Community 152 - "test_commands.py"
Cohesion: 0.32
Nodes (9): Collected, _python(), test_failed_command_raises(), test_lines_and_progress_redraws_are_split(), test_no_command_runs_after_stop(), test_stop_ends_the_command_and_its_children(), run(), test_stop_kills_a_command_that_ignores_sigterm() (+1 more)

### Community 154 - ".load"
Cohesion: 0.18
Nodes (12): env(), loaded(), make_voice(), test_begin_start_without_voice_warns_no_voices(), test_first_start_on_cpu_without_saved_settings_uses_minimal_preset(), test_initial_status_without_voices_is_no_voices_warning(), test_load_prefers_saved_device_and_voice_names(), test_load_without_voices_leaves_voice_unset() (+4 more)

### Community 155 - "bench.py"
Cohesion: 0.20
Nodes (4): StartRequest, _open_early(), run_bench(), speech_like()

### Community 156 - ".__init__"
Cohesion: 0.22
Nodes (4): ContentEncoder, _default_device(), PitchExtractor, _StageClock

### Community 158 - "Title: Plan — One automatic run script"
Cohesion: 0.20
Nodes (9): Approach Summary / Goal, Files in Scope, Functional Requirements, Non-Functional Requirements, Open Questions / Blockers, Risks & Assumptions, Status, Task List (+1 more)

### Community 159 - "pipeline.py"
Cohesion: 0.27
Nodes (3): _close_stream(), _rms(), DeviceNotFoundError

### Community 163 - "saved_toml"
Cohesion: 0.33
Nodes (6): saved_toml(), test_flush_writes_new_value_and_keeps_other_saved_keys(), test_set_bump_filter_updates_property_and_is_saved(), test_set_gate_value_open_below_voice_db_is_float_and_saved(), test_set_noise_reduction_updates_property_and_is_saved(), test_timer_callback_flushes_the_save()

## Knowledge Gaps
- **1 isolated node(s):** `voice-clone`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 809 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **27 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Main parts (`src/voice_clone/`)` connect `ConversionPipeline` to `HomeScreen`, `MainScreen`, `Additional Information`, `SetupScreen`, `Settings`, `.bench`, `numpy`, `TrainScreen`, `TrainController`, `RingBuffer`, `SetupController`, `RvcEngine`, `ChangerController`?**
  _High betweenness centrality (0.142) - this node is a cross-community bridge._
- **Are the 82 inferred relationships involving `SetupController` (e.g. with `Main parts (`src/voice_clone/`)` and `Functional Requirements`) actually correct?**
  _`SetupController` has 82 INFERRED edges - model-reasoned connections that need verification._
- **What connects `voice-clone` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_pipeline.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05341614906832298 - nodes in this community are weakly interconnected._
- **Why does `Additional Information` connect `Additional Information` to `ConversionPipeline`?**
  _High betweenness centrality (0.109) - this node is a cross-community bridge._
- **Are the 25 inferred relationships involving `ChangerController` (e.g. with `Main parts (`src/voice_clone/`)` and `Files in Scope`) actually correct?**
  _`ChangerController` has 25 INFERRED edges - model-reasoned connections that need verification._
- **Should `rmvpe.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05858585858585859 - nodes in this community are weakly interconnected._