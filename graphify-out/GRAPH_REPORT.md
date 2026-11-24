# Graph Report - voice-clone  (2026-11-24)

## Corpus Check
- 162 files · ~78,933 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 6 file(s) not represented in the graph (top: (none) 4, .tcss 1, .ipynb 1)

## Summary
- 1801 nodes · 3778 edges · 132 communities (110 shown, 22 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 359 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0a92c070`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- train_voice
- ConversionPipeline
- test_pipeline.py
- MainScreen
- rmvpe.py
- test_main_screen.py
- SetupScreen
- test_setup_screen.py
- main_screen.py
- test_rvc_engine.py
- test_trainer.py
- setup_check.py
- numpy
- errors.py
- load_settings
- AudioDevice
- TrainingError
- train_panel_widget.py
- test_applio.py
- rvc_engine.py
- test_device.py
- S1 — Move code into `domain/` and `views/`
- models.py
- torch
- VoiceCloneApp
- agile-planning/SKILL.md
- CLI Tests
- RingBuffer
- TrainPanelWidget
- _HubertContentEncoder
- ModelLoadError
- LayerNorm
- ndarray
- pull-request/SKILL.md
- Tester
- PosteriorEncoder
- Applio
- S5 — App shell asks controllers about running work
- MultiHeadAttention
- party-mode/SKILL.md
- VoiceEngine
- onboarding/SKILL.md
- Secret Scanning Script
- SineGen
- Claude Hook Settings
- WN
- RvcEngine
- BaseModelPaths
- Project Root
- DiscriminatorP
- transforms.py
- discover_profiles
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
- Phase 6 — Create Tickets
- Code Review Checklist
- Install
- Voice Recording Script (about 12–15 minutes)
- test_speed_value_is_saved
- CLAUDE.md
- Researcher
- SOLID
- SECURITY_SCANNER/ENTRY_POINT.md
- Phase 3 — Break Down Work
- Phase 5 — Generate Docs
- Graphify Setup
- Step 1 — Brainstorming (Root Agent)
- Step 6 — Reply to and Resolve Threads
- Train a New Voice
- Use the voice changer
- Data Handling
- RTK Setup
- Step 6 — Review (Root Agent)
- Step 1 — Choose the Access Method
- test_pipeline_started_after_the_screen_closed_is_stopped
- AI / LLM Security
- Report Format
- Authentication & Access Control
- Main parts (`src/voice_clone/`)
- Step 2 — Planning (Root Agent)
- Party-Mode
- Step 4 — Triage and Group Comments
- Step 5 — Run Tests in the Browser
- Third-Party Notices
- Step 3 — Train
- Clean Code
- Security Scanner
- Secret Patterns
- Phase 1 — Take Input
- Step 4 — Delegation to Sub-Agents
- Step 6 — Create the PR
- Step 3 — Fetch Reviewer Comments
- Step 5 — Resolve via Party-Mode
- Step 10 — Offer to Post Review (File + Line Comments)
- Step 3 — Fetch the Code Diff
- Step 2 — Find the Target PR
- Step 1 — Check Browser Permission
- Step 2 — Brainstorming
- voice-clone
- test_voice_match_changes_apply_to_running_engine_and_pipeline
- Step 3 — User Approval Gate
- Step 7 — Summary Report to User
- Step 3 — Test Plan
- Step 4 — Approval Gate
- test_stop_resets_the_level_meters
- KISS.md
- SEPARATION_OF_CONCERNS.md
- Step 5 — Sub-Agent Result Return
- Voice files
- TextEncoder
- ElementwiseAffine

## God Nodes (most connected - your core abstractions)
1. `MainScreen` - 63 edges
2. `TrainingError` - 45 edges
3. `SetupScreen` - 40 edges
4. `ConversionPipeline` - 38 edges
5. `load_settings()` - 34 edges
6. `_make()` - 31 edges
7. `RvcEngine` - 29 edges
8. `evaluate()` - 29 edges
9. `train_voice()` - 29 edges
10. `_run()` - 27 edges

## Surprising Connections (you probably didn't know these)
- `Settings` --references--> `Settings`  [INFERRED]
  .claude/references/CODING_CONVENTIONS.md → src/voice_clone/domain/config.py
- `Errors and Logging` --references--> `VoiceCloneError`  [INFERRED]
  .claude/references/CODING_CONVENTIONS.md → src/voice_clone/domain/errors.py
- `Out of Scope` --references--> `HomeScreen`  [INFERRED]
  plans/2026-11-24-app-shell-busy-check-story.md → src/voice_clone/views/home_screen.py
- `Deferred to Later` --references--> `HomeScreen`  [INFERRED]
  plans/2026-11-24-refactor-codebase-to-mvc-overview.md → src/voice_clone/views/home_screen.py
- `Functional Requirements` --references--> `_run_bench_command()`  [INFERRED]
  plans/2026-11-24-setup-controller-story.md → src/voice_clone/cli.py

## Import Cycles
- None detected.

## Communities (132 total, 22 thin omitted)

### Community 0 - "train_voice"
Cohesion: 0.18
Nodes (13): git_head(), find_python(), require_tool(), run_command(), _starts(), DatasetInfo, epochs_done(), find_latest_weights() (+5 more)

### Community 1 - "ConversionPipeline"
Cohesion: 0.10
Nodes (8): Naming, _close_stream(), ConversionPipeline, _Engine, _fit_history(), _rms(), _tail_or_pad(), DeviceNotFoundError

### Community 2 - "test_pipeline.py"
Cohesion: 0.07
Nodes (42): fake_engine(), FakeEngine, input_device(), output_device(), _block(), fake_sd(), FakeInputStream, FakeOutputStream (+34 more)

### Community 3 - "MainScreen"
Cohesion: 0.06
Nodes (14): Acceptance Criteria, Estimate, Functional Requirements, Goal, Non-Functional Requirements, Out of Scope, Requirements, S2 — Voice changer controller (+6 more)

### Community 4 - "rmvpe.py"
Cohesion: 0.06
Nodes (11): BiGRU, ConvBlockRes, Decoder, DeepUnet, E2E, Encoder, Intermediate, MelSpectrogram (+3 more)

### Community 5 - "test_main_screen.py"
Cohesion: 0.09
Nodes (21): _run(), test_advanced_reset_restores_all_advanced_defaults(), test_advanced_tab_holds_voice_match_and_gate(), test_all_settings_are_disabled_while_running(), test_changing_a_gate_value_is_saved(), test_choosing_a_preset_sets_every_advanced_value_and_saves(), test_disabled_button_does_not_change_on_hover(), test_editing_a_speed_field_switches_preset_to_custom() (+13 more)

### Community 6 - "SetupScreen"
Cohesion: 0.10
Nodes (13): Acceptance Criteria, Estimate, Functional Requirements, Goal, Non-Functional Requirements, Out of Scope, Requirements, S3 — Setup controller (Setup screen + `bench` command) (+5 more)

### Community 7 - "test_setup_screen.py"
Cohesion: 0.12
Nodes (29): _applio_line(), FakeApplio, _fill_models(), _lines(), _run(), scenario(), _settle(), _status() (+21 more)

### Community 8 - "main_screen.py"
Cohesion: 0.06
Nodes (32): HomeScreen, LevelMeterWidget, TrainScreen, environment(), _press_start(), _run(), scenario(), _start_blocking_training() (+24 more)

### Community 9 - "test_rvc_engine.py"
Cohesion: 0.09
Nodes (16): VoiceProfile, _cpu_rmvpe_init(), _engine(), index_loads(), test_convert_before_load_raises_model_load_error(), test_convert_length_matches_target_rate(), test_convert_tail_decodes_only_the_last_frames(), test_convert_tail_returns_only_the_end() (+8 more)

### Community 10 - "test_trainer.py"
Cohesion: 0.17
Nodes (16): TrainOptions, _fake_prepare(), FakeApplio, _ffmpeg(), _run(), test_bad_sample_rate_is_rejected(), test_bad_voice_name_is_rejected(), test_epochs_done_reads_applio_progress() (+8 more)

### Community 11 - "setup_check.py"
Cohesion: 0.07
Nodes (54): base_model_files(), base_model_paths(), base_models_present(), BaseModelFile, ensure_base_models(), _quiet_progress_bars(), _report(), _verify() (+46 more)

### Community 12 - "numpy"
Cohesion: 0.23
Nodes (14): _db(), GateSettings, NoiseGate, _open_early(), _noise(), _speech(), test_background_hiss_is_silenced(), test_digital_silence_does_not_lower_the_noise_floor() (+6 more)

### Community 13 - "errors.py"
Cohesion: 0.13
Nodes (12): TrainingStoppedError, StreamingRunner, Collected, _python(), test_failed_command_raises(), test_lines_and_progress_redraws_are_split(), test_missing_program_raises(), test_no_command_runs_after_stop() (+4 more)

### Community 14 - "load_settings"
Cohesion: 0.07
Nodes (43): _run_bench_command(), apply_engine_options(), auto_presets(), BenchResult, fits(), measure_and_save(), pick_preset(), run_bench() (+35 more)

### Community 15 - "AudioDevice"
Cohesion: 0.17
Nodes (19): Task List, AudioDevice, find_device_by_name(), find_virtual_output(), list_input_devices(), list_output_devices(), _query_devices(), rescan_devices() (+11 more)

### Community 16 - "TrainingError"
Cohesion: 0.24
Nodes (16): TrainingError, collect_audio_files(), _duration_seconds(), prepare_dataset(), _refuse_inputs_inside(), _safe_stem(), _fake_ffmpeg(), test_collect_finds_audio_in_folder_recursively() (+8 more)

### Community 17 - "train_panel_widget.py"
Cohesion: 0.12
Nodes (15): _build_parser(), main(), _rescan_audio_devices(), _run_train(), VoiceCloneError, config_dir(), log_dir(), training_dir() (+7 more)

### Community 18 - "test_applio.py"
Cohesion: 0.17
Nodes (18): _make(), RecordingRunner, _step(), test_core_command_without_install_raises(), test_core_commands_point_applio_to_our_logs_folder(), test_extract_device_avoids_mps_on_macos(), test_extract_fails_when_no_features_are_written(), test_find_python_missing_explains_how_to_install() (+10 more)

### Community 19 - "rvc_engine.py"
Cohesion: 0.16
Nodes (12): _adapt_weight_norm_keys(), _ensure_index(), _load_index(), _load_voice(), _LoadedVoice, _single_thread_faiss(), _synthesizer_class(), SynthesizerTrnMs256NSFsid (+4 more)

### Community 20 - "test_device.py"
Cohesion: 0.17
Nodes (19): auto_cpu_threads(), configure_cpu_threads(), select_torch_device(), use_half_precision(), _compute_device(), _capability(), _patch(), test_apple_gpu_uses_fp16_only_when_asked() (+11 more)

### Community 21 - "S1 — Move code into `domain/` and `views/`"
Cohesion: 0.12
Nodes (16): Acceptance Criteria, Estimate, Functional Requirements, Goal, Non-Functional Requirements, Out of Scope, Requirements, S1 — Move code into `domain/` and `views/` (+8 more)

### Community 22 - "models.py"
Cohesion: 0.20
Nodes (5): get_padding(), init_weights(), Generator, Flip, Log

### Community 23 - "torch"
Cohesion: 0.20
Nodes (15): add_timing_signal_1d(), cat_timing_signal_1d(), convert_pad_shape(), fused_add_tanh_sigmoid_multiply(), generate_path(), get_timing_signal_1d(), kl_divergence(), rand_gumbel() (+7 more)

### Community 24 - "VoiceCloneApp"
Cohesion: 0.23
Nodes (12): VoiceCloneApp, test_r_key_exits_with_restart(), scenario(), open_voice_changer(), scenario(), test_no_voices_shows_status_message(), scenario(), scenario() (+4 more)

### Community 25 - "agile-planning/SKILL.md"
Cohesion: 0.11
Nodes (14): AGENT RULES, DO, DO NOT, 2a. Ask clarifying questions first, 2b. Look at the codebase (read-only), 2c. Write the analysis, Phase 2 — Brainstorm, 4a. Find a reference story (+6 more)

### Community 26 - "CLI Tests"
Cohesion: 0.15
Nodes (9): _no_log_file(), test_bench_without_base_models_returns_error(), test_restart_runs_the_app_again_and_rescans_devices(), test_run_and_no_command_open_the_app(), test_train_ctrl_c_returns_exit_code_130(), test_train_error_returns_exit_code_1(), fake_train(), test_train_passes_options() (+1 more)

### Community 27 - "RingBuffer"
Cohesion: 0.26
Nodes (10): RingBuffer, test_clear_empties_buffer(), test_non_positive_capacity_is_rejected(), test_overflow_overwrites_oldest_samples(), test_read_returns_written_samples_in_order(), test_trim_below_limit_keeps_everything(), test_trim_drops_oldest_samples_beyond_limit(), test_underrun_zero_pads_the_read() (+2 more)

### Community 28 - "TrainPanelWidget"
Cohesion: 0.11
Nodes (12): Acceptance Criteria, Estimate, Functional Requirements, Goal, Non-Functional Requirements, Out of Scope, Requirements, S4 — Train controller (Train screen + `train` command) (+4 more)

### Community 29 - "_HubertContentEncoder"
Cohesion: 0.22
Nodes (5): _HubertContentEncoder, _upsample_frames(), test_half_content_encoder_returns_half(), test_v1_encoder_skips_layers_but_matches_layer_nine(), test_v2_encoder_returns_last_hidden_state()

### Community 30 - "ModelLoadError"
Cohesion: 0.25
Nodes (6): _rmvpe_hidden(), _RmvpePitchExtractor, RMVPE, ModelLoadError, test_rmvpe_split_matches_the_original_network(), test_rmvpe_with_recurrent_on_cpu_gives_same_pitch()

### Community 31 - "LayerNorm"
Cohesion: 0.14
Nodes (5): Decoder, Encoder, FFN, ConvReluNorm, LayerNorm

### Community 32 - "ndarray"
Cohesion: 0.17
Nodes (10): _coarse_pitch(), _fit_length(), _follow_loudness(), _loudness_envelope(), _pad_tail(), _smooth_pitch(), test_follow_loudness_full_matches_source_level(), test_follow_loudness_zero_returns_output_unchanged() (+2 more)

### Community 33 - "pull-request/SKILL.md"
Cohesion: 0.13
Nodes (7): Step 3 — Choose the Target Branch, Step 4 — Collect Context, Step 5 — Fill the Template, Step 7 — Summary Report, Suggested format, Step 4 — Check That the Code Matches the Requirements, Step 9 — Write the Review Report

### Community 34 - "Tester"
Cohesion: 0.12
Nodes (16): Additional Skill References, Code-First, Constraints, Delegation Prompt Template, Failure Modes, Inputs, Note for Code-First and Test-First, Outputs (+8 more)

### Community 37 - "S5 — App shell asks controllers about running work"
Cohesion: 0.18
Nodes (10): Acceptance Criteria, Estimate, Functional Requirements, Goal, Non-Functional Requirements, Out of Scope, Requirements, S5 — App shell asks controllers about running work (+2 more)

### Community 41 - "onboarding/SKILL.md"
Cohesion: 0.16
Nodes (8): PROJECT OVERVIEW, Step 2 — Coding Conventions, Step 3 — Finish, How to Use This Skill, Onboarding Workflow, Override Notice, Project Onboarding, Purpose

### Community 42 - "Secret Scanning Script"
Cohesion: 0.50
Nodes (7): main(), report(), scan_diff(), scan_files(), scan_line(), severity_color(), scan-secrets.sh script

### Community 43 - "SineGen"
Cohesion: 0.16
Nodes (3): GeneratorNSF, SineGen, SourceModuleHnNSF

### Community 44 - "Claude Hook Settings"
Cohesion: 0.50
Nodes (3): hooks, PreToolUse, $schema

### Community 45 - "WN"
Cohesion: 0.15
Nodes (4): ResBlock1, ResBlock2, ResidualCouplingLayer, WN

### Community 46 - "RvcEngine"
Cohesion: 0.21
Nodes (5): RvcEngine, FakeEncoder, FakePitch, test_cpu_engine_stays_fp32_when_fp16_is_asked(), test_half_voice_converts_to_float32()

### Community 47 - "BaseModelPaths"
Cohesion: 0.20
Nodes (5): BaseModelPaths, ContentEncoder, _default_device(), PitchExtractor, _StageClock

### Community 49 - "DiscriminatorP"
Cohesion: 0.18
Nodes (4): DiscriminatorP, DiscriminatorS, MultiPeriodDiscriminator, MultiPeriodDiscriminatorV2

### Community 50 - "transforms.py"
Cohesion: 0.23
Nodes (6): ConvFlow, DDSConv, piecewise_rational_quadratic_transform(), rational_quadratic_spline(), searchsorted(), unconstrained_rational_quadratic_spline()

### Community 52 - "discover_profiles"
Cohesion: 0.33
Nodes (8): _build_profile(), discover_profiles(), _make_voice(), test_discovers_profiles_sorted_by_name_with_index(), test_folder_without_pth_is_skipped(), test_loose_files_in_voices_folder_are_ignored(), test_missing_voices_folder_returns_empty_list(), test_several_pth_files_use_first_by_name_and_warn()

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
Cohesion: 0.18
Nodes (11): Code Order in a File, Coding Conventions, Comments, Cross-Platform (macOS + Windows), Errors and Logging, Folder Structure (src layout), Real-Time Audio, Settings (+3 more)

### Community 57 - "web-test/SKILL.md"
Cohesion: 0.24
Nodes (6): Step 6 — Test Report, Test Report Template, Usage Notes, Constraints, Step-by-Step Instructions, Web Test

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

### Community 67 - "Phase 6 — Create Tickets"
Cohesion: 0.22
Nodes (8): 6a. Choose where to create the tickets, 6b. Create story tickets, 6c. Create task tickets, 6d. Update the overview, 6e. Show a summary, MCP Reference, No MCP — use the browser, Phase 6 — Create Tickets

### Community 68 - "Code Review Checklist"
Cohesion: 0.22
Nodes (7): Atomic Design _(UI only)_, Code Review Checklist, DRY _(All)_, KISS _(All)_, Separation of Concerns _(All)_, SOLID _(OOP)_, Step 6 — Apply Clean Code Review

### Community 69 - "Install"
Cohesion: 0.22
Nodes (9): Check the setup, First start, Install, Install the app, macOS (Apple Silicon or Intel), Prerequisites, Windows: do I have an NVIDIA card?, Windows with an NVIDIA card (PowerShell) (+1 more)

### Community 70 - "Voice Recording Script (about 12–15 minutes)"
Cohesion: 0.22
Nodes (9): Part 1 — Normal speech, Part 2 — Questions and answers, Part 3 — Feelings, Part 4 — Range, Part 5 — Short story, Part 6 — Work and technology, Part 7 — Mixed sentences, Part 8 — Free talk (2–3 minutes) (+1 more)

### Community 71 - "test_speed_value_is_saved"
Cohesion: 0.22
Nodes (4): test_editing_any_advanced_value_switches_preset_to_custom(), test_performance_preset_matches_saved_settings(), test_speed_value_is_saved(), test_voice_match_value_is_saved()

### Community 72 - "CLAUDE.md"
Cohesion: 0.25
Nodes (6): AGENT RULES, CLAUDE, CODING CONVENTIONS, graphify, GRAPHIFY KNOWLEDGE GRAPH, PROJECT OVERVIEW

### Community 73 - "Researcher"
Cohesion: 0.25
Nodes (8): Constraints, Failure Modes, Inputs, Outputs, Position in the Workflow, Purpose, Researcher, Workflow Steps

### Community 74 - "SOLID"
Cohesion: 0.25
Nodes (7): D — Dependency Inversion Principle, I — Interface Segregation Principle, L — Liskov Substitution Principle, O — Open/Closed Principle, S — Single Responsibility Principle, SOLID, SOLID Rules

### Community 76 - "Phase 3 — Break Down Work"
Cohesion: 0.25
Nodes (8): 3a. Epic → User Stories, 3b. User Story → Tasks, Dependencies, How to split a big story, Output format, Phase 3 — Break Down Work, What counts as a user story, What is NOT a user story

### Community 77 - "Phase 5 — Generate Docs"
Cohesion: 0.25
Nodes (7): After writing, File path, Overview file, Overview template, Phase 5 — Generate Docs, Rules, Story doc template

### Community 78 - "Graphify Setup"
Cohesion: 0.25
Nodes (7): Add to Claude Code, Build the graph, Graphify Setup, Install, Keep it up to date (optional), Search the graph, What you need

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
Cohesion: 0.25
Nodes (8): Change your voice, If the voice lags, drops or comes late, Logs, Make the voice match better, Measure the speed, Performance presets, Speed and delay, Use the voice changer

### Community 83 - "Data Handling"
Cohesion: 0.29
Nodes (7): Data Handling, Insecure Deserialization (CWE-502), Path Traversal (CWE-22), Sensitive Data Exposure (CWE-200, CWE-312, CWE-798), SSRF (CWE-918), Transport & Storage, XXE (CWE-611)

### Community 84 - "RTK Setup"
Cohesion: 0.29
Nodes (6): Add to Claude Code, Check savings, Common commands, Install, Notes, RTK Setup

### Community 85 - "Step 6 — Review (Root Agent)"
Cohesion: 0.29
Nodes (7): Checklist, Minimum Skill References, Review Feedback (when not qualified), Review Workflow, Routing, Rules, Step 6 — Review (Root Agent)

### Community 86 - "Step 1 — Choose the Access Method"
Cohesion: 0.29
Nodes (7): Find the platform, None available, Step 1 — Choose the Access Method, Tier 1 — Platform MCP (best), Tier 2 — Platform CLI (backup), Tier 3 — Claude browser control, What each mode needs

### Community 88 - "AI / LLM Security"
Cohesion: 0.33
Nodes (6): AI / LLM Security, Data Leakage via Prompts, Indirect Prompt Injection (RAG / Agentic), Insecure Tool Use, Model & Infrastructure Basics, Prompt Injection (CWE-1336)

### Community 89 - "Report Format"
Cohesion: 0.33
Nodes (6): 1. Scan Summary, 2. Finding Cards, 3. Dependency Audit, 4. Secrets Scan, 5. Proposed Patches, Report Format

### Community 90 - "Authentication & Access Control"
Cohesion: 0.33
Nodes (6): Authentication & Access Control, Broken Authorization / IDOR / BOLA (CWE-284, CWE-639), CSRF (CWE-352), JWT Weaknesses, Mass Assignment (CWE-915), Session & Privilege

### Community 91 - "Main parts (`src/voice_clone/`)"
Cohesion: 0.33
Nodes (6): Additional Information, Audio pipeline (real time), Files and folders, How to run, Main parts (`src/voice_clone/`), Target platforms

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

### Community 102 - "Phase 1 — Take Input"
Cohesion: 0.40
Nodes (4): 1a. Find the input source, 1b. Find the input type, 1c. Show what you got, Phase 1 — Take Input

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

### Community 110 - "Step 1 — Check Browser Permission"
Cohesion: 0.40
Nodes (4): 1. Check that the user allows the browser, 2. Check that a browser tool is available, 3. Get the target, Step 1 — Check Browser Permission

### Community 111 - "Step 2 — Brainstorming"
Cohesion: 0.40
Nodes (5): Brainstorming Dialogue, Check the Test Scope, Classify the Intent, Step 2 — Brainstorming, Usage Notes

### Community 112 - "voice-clone"
Cohesion: 0.40
Nodes (5): Documentation, Licenses, Quick start, Responsible use, voice-clone

### Community 113 - "test_voice_match_changes_apply_to_running_engine_and_pipeline"
Cohesion: 0.30
Nodes (3): empty_environment(), test_voice_match_changes_apply_to_running_engine_and_pipeline(), body()

### Community 114 - "Step 3 — User Approval Gate"
Cohesion: 0.50
Nodes (4): Approved, Cancels / Aborts, Requests Changes, Step 3 — User Approval Gate

### Community 115 - "Step 7 — Summary Report to User"
Cohesion: 0.50
Nodes (3): Step 7 — Summary Report to User, Summary Report Template, Usage Notes

### Community 116 - "Step 3 — Test Plan"
Cohesion: 0.50
Nodes (4): Planning Rules, Step 3 — Test Plan, Test Plan Template, Usage Notes

### Community 117 - "Step 4 — Approval Gate"
Cohesion: 0.50
Nodes (4): Approved, Cancels, Requests Changes, Step 4 — Approval Gate

### Community 121 - "Step 5 — Sub-Agent Result Return"
Cohesion: 0.67
Nodes (3): Step 5 — Sub-Agent Result Return, Sub-Agent Result Template, Usage Notes

### Community 122 - "Voice files"
Cohesion: 0.67
Nodes (3): Add a voice you already have, Keep your voice in a GitHub Release, Voice files

## Knowledge Gaps
- **1 isolated node(s):** `voice-clone`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 657 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **22 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Main parts (`src/voice_clone/`)` connect `Main parts (`src/voice_clone/`)` to `ConversionPipeline`, `MainScreen`, `SetupScreen`, `main_screen.py`, `numpy`, `RvcEngine`, `load_settings`, `RingBuffer`?**
  _High betweenness centrality (0.237) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `MainScreen` (e.g. with `Main parts (`src/voice_clone/`)` and `Acceptance Criteria`) actually correct?**
  _`MainScreen` has 8 INFERRED edges - model-reasoned connections that need verification._
- **What connects `voice-clone` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `ConversionPipeline` be split into smaller, more focused modules?**
  _Cohesion score 0.09957325746799431 - nodes in this community are weakly interconnected._
- **Why does `Additional Information` connect `Main parts (`src/voice_clone/`)` to `onboarding/SKILL.md`?**
  _High betweenness centrality (0.227) - this node is a cross-community bridge._
- **Are the 20 inferred relationships involving `TrainingError` (e.g. with `Applio` and `StreamingRunner`) actually correct?**
  _`TrainingError` has 20 INFERRED edges - model-reasoned connections that need verification._
- **Should `test_pipeline.py` be split into smaller, more focused modules?**
  _Cohesion score 0.0726764500349406 - nodes in this community are weakly interconnected._