import numpy as np

from tests.conftest import FakeEngine
from voice_clone.bench import BenchResult, run_bench, speech_like
from voice_clone.config import PERFORMANCE_PRESETS


class TimedFakeEngine(FakeEngine):
    def __init__(self) -> None:
        super().__init__()
        self.time_stages = False
        self.stage_seconds: dict[str, float] = {}

    def convert(self, audio, tail=None):
        if self.time_stages:
            self.stage_seconds = {"encode": 0.002, "synth": 0.004}
        return super().convert(audio, tail)


def test_speech_like_has_loud_and_quiet_parts():
    audio = speech_like(2.0)

    frames = audio[: len(audio) // 960 * 960].reshape(-1, 960)
    levels = np.sqrt(np.mean(frames**2, axis=1))
    assert levels.max() > 10 * levels.min()


def test_run_bench_measures_each_block_and_stage():
    engine = TimedFakeEngine()
    values = PERFORMANCE_PRESETS["balanced"][1]

    result = run_bench(engine, values, seconds=2.0)

    assert result.block_ms == values["block_ms"]
    assert len(result.loads) == 2000 // values["block_ms"]
    assert result.stage_ms == {"encode": 2.0, "synth": 4.0}
    assert engine.time_stages is False
    assert len(engine.convert_lengths) > 1


def test_bench_result_summary():
    result = BenchResult(400, [0.2, 0.4, 1.2, 0.6])

    assert result.slow_blocks == 1
    assert abs(result.mean_load - 0.6) < 1e-9
