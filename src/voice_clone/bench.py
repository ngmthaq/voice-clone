import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

import numpy as np

from voice_clone.audio.devices import AudioDevice
from voice_clone.audio.noise_gate import GateSettings
from voice_clone.audio.pipeline import ConversionPipeline

BENCH_SAMPLE_RATE = 48000
SYLLABLES_PER_SECOND = 4
QUIET_LEVEL = 0.003
LOUD_LEVEL = 0.2
WARM_UP_BLOCKS = 1
TARGET_LOAD = 0.7
HEAVIEST_AUTO_PRESET = "high"
MEASURE_SECONDS = 4.0


@dataclass
class BenchResult:
    block_ms: int
    loads: list[float]
    stage_ms: dict[str, float] = field(default_factory=dict)

    @property
    def mean_load(self) -> float:
        return float(np.mean(self.loads)) if self.loads else 0.0

    @property
    def p95_load(self) -> float:
        return float(np.percentile(self.loads, 95)) if self.loads else 0.0

    @property
    def slow_blocks(self) -> int:
        return sum(load > 1.0 for load in self.loads)


def speech_like(seconds: float, rate: int = BENCH_SAMPLE_RATE, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    t = np.arange(int(seconds * rate)) / rate
    pitch = 160 + 40 * np.sin(2 * np.pi * 0.5 * t)
    phase = 2 * np.pi * np.cumsum(pitch) / rate
    voiced = sum(np.sin(k * phase) / k for k in range(1, 6))
    syllables = np.sin(np.pi * SYLLABLES_PER_SECOND * t) ** 2
    level = QUIET_LEVEL + (LOUD_LEVEL - QUIET_LEVEL) * (syllables > 0.3) * syllables
    noise = rng.standard_normal(len(t)) * QUIET_LEVEL
    return (voiced * level + noise).astype(np.float32)


def apply_engine_options(engine: object, values: Mapping[str, float]) -> None:
    engine.index_rate = values["index_percent"] / 100  # type: ignore[attr-defined]
    engine.protect = values["protect_percent"] / 100  # type: ignore[attr-defined]
    engine.loudness_follow = values["loudness_percent"] / 100  # type: ignore[attr-defined]
    engine.pitch_smoothing_ms = int(values["pitch_smoothing_ms"])  # type: ignore[attr-defined]


def run_bench(engine: object, values: Mapping[str, float], seconds: float) -> BenchResult:
    device = AudioDevice(-1, "bench", 1, 2, BENCH_SAMPLE_RATE)
    block_ms = int(values["block_ms"])
    pipeline = ConversionPipeline(
        engine,  # type: ignore[arg-type]
        device,
        device,
        block_ms=block_ms,
        context_ms=int(values["context_ms"]),
        crossfade_ms=int(values["crossfade_ms"]),
        hum_filter_hz=int(values["hum_filter_hz"]),
        gate_settings=GateSettings(
            hold_ms=int(values["gate_hold_ms"]),
            pre_open_ms=int(values["gate_pre_open_ms"]),
            open_above_floor_db=float(values["gate_open_above_db"]),
        ),
    )
    pipeline.warm_up()
    frames = BENCH_SAMPLE_RATE * block_ms // 1000
    blocks = max(1, int(seconds * 1000 // block_ms)) + WARM_UP_BLOCKS
    audio = speech_like(blocks * frames / BENCH_SAMPLE_RATE)
    timing = hasattr(engine, "time_stages")
    if timing:
        engine.time_stages = True  # type: ignore[attr-defined]
    loads: list[float] = []
    stage_totals: dict[str, float] = {}
    counted = 0
    try:
        for i in range(blocks):
            if timing:
                engine.stage_seconds = {}  # type: ignore[attr-defined]
            started = time.perf_counter()
            pipeline.process_block(audio[i * frames : (i + 1) * frames])
            elapsed = time.perf_counter() - started
            if i < WARM_UP_BLOCKS:
                continue
            loads.append(elapsed / (block_ms / 1000))
            stages = getattr(engine, "stage_seconds", {}) if timing else {}
            if stages:
                counted += 1
                for name, value in stages.items():
                    stage_totals[name] = stage_totals.get(name, 0.0) + value
    finally:
        if timing:
            engine.time_stages = False  # type: ignore[attr-defined]
    stage_ms = {name: total * 1000 / counted for name, total in stage_totals.items()}
    return BenchResult(block_ms, loads, stage_ms)


def auto_presets(
    presets: Mapping[str, tuple[str, Mapping[str, float]]],
) -> dict[str, Mapping[str, float]]:
    chosen: dict[str, Mapping[str, float]] = {}
    for name, (_, values) in presets.items():
        chosen[name] = values
        if name == HEAVIEST_AUTO_PRESET:
            break
    return chosen


def fits(result: BenchResult) -> bool:
    return result.p95_load < TARGET_LOAD


def pick_preset(
    engine: object,
    presets: Mapping[str, Mapping[str, float]],
    seconds: float = MEASURE_SECONDS,
    on_result: Callable[[str, BenchResult], None] | None = None,
) -> tuple[str | None, dict[str, BenchResult]]:
    best: str | None = None
    results: dict[str, BenchResult] = {}
    for name, values in presets.items():
        apply_engine_options(engine, values)
        result = run_bench(engine, values, seconds)
        results[name] = result
        if on_result is not None:
            on_result(name, result)
        if not fits(result):
            break
        best = name
    return best, results


def measure_and_save(
    on_result: Callable[[str, BenchResult], None] | None = None,
) -> tuple[str | None, dict[str, BenchResult]]:
    from voice_clone.config import PERFORMANCE_PRESETS, apply_preset, load_settings, save_settings
    from voice_clone.engine import RvcEngine
    from voice_clone.engine.download import base_model_paths
    from voice_clone.errors import ProfileError
    from voice_clone.paths import models_dir, voices_dir
    from voice_clone.profiles import discover_profiles

    settings = load_settings()
    profiles = discover_profiles(voices_dir())
    profile = next((p for p in profiles if p.name == settings.profile), None)
    if profile is None and profiles:
        profile = profiles[0]
    if profile is None:
        raise ProfileError("Add or train a voice first: the speed test needs one.")
    presets = auto_presets(PERFORMANCE_PRESETS)
    engine = RvcEngine(
        base_model_paths(models_dir()),
        cpu_threads=settings.cpu_threads,
        precision=settings.precision,
    )
    apply_engine_options(engine, next(iter(presets.values())))
    engine.load(profile)
    best, results = pick_preset(engine, presets, on_result=on_result)
    if best is not None:
        save_settings(apply_preset(load_settings(), best))
    return best, results
