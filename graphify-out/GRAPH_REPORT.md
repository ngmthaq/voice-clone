# Graph Report - voice-clone  (2026-11-24)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1195 nodes · 3051 edges · 55 communities (38 shown, 17 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 282 edges (avg confidence: 0.9)
- Token cost: 33,537 input · 727 output

## Graph Freshness
- Built from commit: `e83eef5d`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Voice Training Runner
- Audio Pipeline & Noise Gate
- Pipeline Test Fakes
- Voice Changer Main Screen
- RMVPE Pitch Model
- Setup Screen Tests
- Setup Environment Check
- Main Screen Tests
- App Shell & UI Widgets
- RVC Engine Tests
- Train Screen Tests
- Base Model Download
- Setup Screen UI
- Streaming Process Runner
- Settings & Presets Config
- Audio Device Discovery
- Performance Benchmark
- CLI Entry Point
- Applio Integration Tests
- Voice Model Loading
- Torch Device Selection
- NSF Generator Models
- VITS Vendor Modules
- VITS Common Utilities
- App Lifecycle & Quit
- Transformer Encoder Decoder
- CLI Tests
- Voice Conversion Inference
- Training Panel Widget
- RVC Engine Core
- RMVPE Pitch Extractor
- Relative Multi-Head Attention
- Home & Train Screens
- GAN Discriminators
- Flow Spline Transforms
- Residual Coupling Blocks
- Voice Profile Discovery
- Encoder & Pitch Protocols
- Sine Source Generator
- Settings Form Fields
- Voice Engine Interface
- Advanced Settings Tests
- Secret Scanning Script
- Pipeline Lifecycle Test
- Claude Hook Settings
- Level Meter Reset Test
- Elementwise Affine Flow
- Slow Conversion Warning Test
- Project Root

## God Nodes (most connected - your core abstractions)
1. `MainScreen` - 58 edges
2. `TrainingError` - 45 edges
3. `ConversionPipeline` - 36 edges
4. `SetupScreen` - 35 edges
5. `load_settings()` - 34 edges
6. `_make()` - 31 edges
7. `train_voice()` - 29 edges
8. `evaluate()` - 29 edges
9. `RvcEngine` - 27 edges
10. `_run()` - 27 edges

## Surprising Connections (you probably didn't know these)
- `test_train_error_returns_exit_code_1()` --uses--> `TrainingError`  [INFERRED]
  tests/test_cli.py → src/voice_clone/errors.py
- `fake_train()` --calls--> `TrainingError`  [EXTRACTED]
  tests/test_cli.py → src/voice_clone/errors.py
- `test_core_command_without_install_raises()` --uses--> `TrainingError`  [INFERRED]
  tests/training/test_applio.py → src/voice_clone/errors.py
- `test_extract_fails_when_no_features_are_written()` --uses--> `TrainingError`  [INFERRED]
  tests/training/test_applio.py → src/voice_clone/errors.py
- `test_find_python_missing_explains_how_to_install()` --uses--> `TrainingError`  [INFERRED]
  tests/training/test_applio.py → src/voice_clone/errors.py

## Import Cycles
- None detected.

## Communities (55 total, 17 thin omitted)

### Community 0 - "Voice Training Runner"
Cohesion: 0.06
Nodes (47): TrainingError, Applio, git_head(), CommandRunner, find_python(), require_tool(), run_command(), _starts() (+39 more)

### Community 1 - "Audio Pipeline & Noise Gate"
Cohesion: 0.07
Nodes (31): _db(), GateSettings, NoiseGate, _open_early(), _close_stream(), ConversionPipeline, _Engine, _fit_history() (+23 more)

### Community 2 - "Pipeline Test Fakes"
Cohesion: 0.06
Nodes (46): _block(), fake_sd(), FakeInputStream, FakeOutputStream, FakeStream, _make(), _settled_rms(), test_constant_engine_output_has_no_jumps_between_blocks() (+38 more)

### Community 4 - "RMVPE Pitch Model"
Cohesion: 0.06
Nodes (11): BiGRU, ConvBlockRes, Decoder, DeepUnet, E2E, Encoder, Intermediate, MelSpectrogram (+3 more)

### Community 5 - "Setup Screen Tests"
Cohesion: 0.09
Nodes (32): _applio_line(), environment(), facts(), fake_applio(), FakeApplio, _fill_models(), _lines(), _run() (+24 more)

### Community 6 - "Setup Environment Check"
Cohesion: 0.16
Nodes (35): _applio(), _audio(), Check, _compute(), _compute_device(), evaluate(), Facts, gather_facts() (+27 more)

### Community 7 - "Main Screen Tests"
Cohesion: 0.10
Nodes (21): empty_environment(), _run(), test_advanced_reset_restores_all_advanced_defaults(), test_advanced_tab_holds_voice_match_and_gate(), test_all_settings_are_disabled_while_running(), test_changing_a_gate_value_is_saved(), test_choosing_a_preset_sets_every_advanced_value_and_saves(), test_disabled_button_does_not_change_on_hover() (+13 more)

### Community 8 - "App Shell & UI Widgets"
Cohesion: 0.12
Nodes (5): VoiceCloneError, LevelMeterWidget, _parse_paths(), _read_int(), test_parse_paths_keeps_an_existing_path_with_spaces_whole()

### Community 9 - "RVC Engine Tests"
Cohesion: 0.08
Nodes (20): VoiceProfile, _cpu_rmvpe_init(), _engine(), FakeEncoder, FakePitch, index_loads(), test_convert_before_load_raises_model_load_error(), test_convert_length_matches_target_rate() (+12 more)

### Community 10 - "Train Screen Tests"
Cohesion: 0.13
Nodes (28): environment(), _press_start(), _run(), scenario(), _start_blocking_training(), _status(), test_a_different_key_does_not_confirm(), body() (+20 more)

### Community 11 - "Base Model Download"
Cohesion: 0.12
Nodes (19): base_model_files(), base_model_paths(), base_models_present(), BaseModelFile, BaseModelPaths, ensure_base_models(), _quiet_progress_bars(), _report() (+11 more)

### Community 12 - "Setup Screen UI"
Cohesion: 0.14
Nodes (3): _measure_message(), _preset_title(), SetupScreen

### Community 13 - "Streaming Process Runner"
Cohesion: 0.14
Nodes (13): TrainingStoppedError, StreamingRunner, Collected, _python(), test_failed_command_raises(), test_lines_and_progress_redraws_are_split(), test_missing_program_raises(), test_no_command_runs_after_stop() (+5 more)

### Community 14 - "Settings & Presets Config"
Cohesion: 0.15
Nodes (18): apply_preset(), load_settings(), _preset(), save_settings(), Settings, settings_path(), settings_saved(), _first_start_settings() (+10 more)

### Community 15 - "Audio Device Discovery"
Cohesion: 0.17
Nodes (18): AudioDevice, find_device_by_name(), find_virtual_output(), list_input_devices(), list_output_devices(), _query_devices(), rescan_devices(), _device() (+10 more)

### Community 16 - "Performance Benchmark"
Cohesion: 0.16
Nodes (21): apply_engine_options(), auto_presets(), BenchResult, fits(), measure_and_save(), pick_preset(), run_bench(), speech_like() (+13 more)

### Community 17 - "CLI Entry Point"
Cohesion: 0.18
Nodes (12): _build_parser(), main(), _rescan_audio_devices(), _run_bench_command(), _run_train(), setup_logging(), main(), config_dir() (+4 more)

### Community 18 - "Applio Integration Tests"
Cohesion: 0.17
Nodes (18): _make(), RecordingRunner, _step(), test_core_command_without_install_raises(), test_core_commands_point_applio_to_our_logs_folder(), test_extract_device_avoids_mps_on_macos(), test_extract_fails_when_no_features_are_written(), test_find_python_missing_explains_how_to_install() (+10 more)

### Community 19 - "Voice Model Loading"
Cohesion: 0.16
Nodes (12): _adapt_weight_norm_keys(), _ensure_index(), _load_index(), _load_voice(), _LoadedVoice, _single_thread_faiss(), _synthesizer_class(), SynthesizerTrnMs256NSFsid (+4 more)

### Community 20 - "Torch Device Selection"
Cohesion: 0.18
Nodes (18): auto_cpu_threads(), configure_cpu_threads(), select_torch_device(), use_half_precision(), _capability(), _patch(), test_apple_gpu_uses_fp16_only_when_asked(), test_auto_threads_keeps_small_machines_unchanged() (+10 more)

### Community 21 - "NSF Generator Models"
Cohesion: 0.12
Nodes (4): Generator, GeneratorNSF, PosteriorEncoder, ResidualCouplingBlock

### Community 22 - "VITS Vendor Modules"
Cohesion: 0.17
Nodes (6): get_padding(), init_weights(), TextEncoder, Flip, Log, ResBlock2

### Community 23 - "VITS Common Utilities"
Cohesion: 0.20
Nodes (15): add_timing_signal_1d(), cat_timing_signal_1d(), convert_pad_shape(), fused_add_tanh_sigmoid_multiply(), generate_path(), get_timing_signal_1d(), kl_divergence(), rand_gumbel() (+7 more)

### Community 24 - "App Lifecycle & Quit"
Cohesion: 0.16
Nodes (12): VoiceCloneApp, test_r_key_exits_with_restart(), scenario(), open_voice_changer(), scenario(), test_no_voices_shows_status_message(), scenario(), scenario() (+4 more)

### Community 25 - "Transformer Encoder Decoder"
Cohesion: 0.14
Nodes (5): Decoder, Encoder, FFN, ConvReluNorm, LayerNorm

### Community 26 - "CLI Tests"
Cohesion: 0.15
Nodes (9): _no_log_file(), test_bench_without_base_models_returns_error(), test_restart_runs_the_app_again_and_rescans_devices(), test_run_and_no_command_open_the_app(), test_train_ctrl_c_returns_exit_code_130(), test_train_error_returns_exit_code_1(), fake_train(), test_train_passes_options() (+1 more)

### Community 27 - "Voice Conversion Inference"
Cohesion: 0.17
Nodes (10): _coarse_pitch(), _fit_length(), _follow_loudness(), _loudness_envelope(), _pad_tail(), _smooth_pitch(), test_follow_loudness_full_matches_source_level(), test_follow_loudness_zero_returns_output_unchanged() (+2 more)

### Community 29 - "RVC Engine Core"
Cohesion: 0.14
Nodes (6): _HubertContentEncoder, RvcEngine, _upsample_frames(), test_half_content_encoder_returns_half(), test_v1_encoder_skips_layers_but_matches_layer_nine(), test_v2_encoder_returns_last_hidden_state()

### Community 30 - "RMVPE Pitch Extractor"
Cohesion: 0.25
Nodes (6): _rmvpe_hidden(), _RmvpePitchExtractor, RMVPE, ModelLoadError, test_rmvpe_split_matches_the_original_network(), test_rmvpe_with_recurrent_on_cpu_gives_same_pitch()

### Community 33 - "GAN Discriminators"
Cohesion: 0.18
Nodes (4): DiscriminatorP, DiscriminatorS, MultiPeriodDiscriminator, MultiPeriodDiscriminatorV2

### Community 34 - "Flow Spline Transforms"
Cohesion: 0.23
Nodes (6): ConvFlow, DDSConv, piecewise_rational_quadratic_transform(), rational_quadratic_spline(), searchsorted(), unconstrained_rational_quadratic_spline()

### Community 35 - "Residual Coupling Blocks"
Cohesion: 0.18
Nodes (3): ResBlock1, ResidualCouplingLayer, WN

### Community 36 - "Voice Profile Discovery"
Cohesion: 0.33
Nodes (8): _build_profile(), discover_profiles(), _make_voice(), test_discovers_profiles_sorted_by_name_with_index(), test_folder_without_pth_is_skipped(), test_loose_files_in_voices_folder_are_ignored(), test_missing_voices_folder_returns_empty_list(), test_several_pth_files_use_first_by_name_and_warn()

### Community 37 - "Encoder & Pitch Protocols"
Cohesion: 0.22
Nodes (4): ContentEncoder, _default_device(), PitchExtractor, _StageClock

### Community 39 - "Settings Form Fields"
Cohesion: 0.24
Nodes (3): matching_preset(), labeled_field(), _format_number()

### Community 41 - "Advanced Settings Tests"
Cohesion: 0.22
Nodes (4): test_editing_any_advanced_value_switches_preset_to_custom(), test_performance_preset_matches_saved_settings(), test_speed_value_is_saved(), test_voice_match_value_is_saved()

### Community 42 - "Secret Scanning Script"
Cohesion: 0.50
Nodes (7): main(), report(), scan_diff(), scan_files(), scan_line(), severity_color(), scan-secrets.sh script

### Community 44 - "Claude Hook Settings"
Cohesion: 0.50
Nodes (3): hooks, PreToolUse, $schema

## Knowledge Gaps
- **1 isolated node(s):** `voice-clone`
  These have ≤1 connection - possible missing edges. (Counts symbols only; 256 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **17 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `MainScreen` connect `Voice Changer Main Screen` to `Home & Train Screens`, `Settings Form Fields`, `App Shell & UI Widgets`, `Settings & Presets Config`, `Audio Device Discovery`?**
  _High betweenness centrality (0.054) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `MainScreen` (e.g. with `HomeScreen` and `VoiceCloneError`) actually correct?**
  _`MainScreen` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `voice-clone` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Voice Training Runner` be split into smaller, more focused modules?**
  _Cohesion score 0.06400343642611683 - nodes in this community are weakly interconnected._
- **Why does `VoiceCloneApp` connect `App Lifecycle & Quit` to `Setup Screen Tests`, `Main Screen Tests`, `App Shell & UI Widgets`, `Train Screen Tests`, `Pipeline Lifecycle Test`, `CLI Entry Point`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Are the 20 inferred relationships involving `TrainingError` (e.g. with `Applio` and `StreamingRunner`) actually correct?**
  _`TrainingError` has 20 INFERRED edges - model-reasoned connections that need verification._
- **Should `Audio Pipeline & Noise Gate` be split into smaller, more focused modules?**
  _Cohesion score 0.06594399277326106 - nodes in this community are weakly interconnected._