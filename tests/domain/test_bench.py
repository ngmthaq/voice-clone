import numpy as np
import pytest

from tests.conftest import FakeEngine
from voice_clone.domain import bench
from voice_clone.domain.bench import BenchResult, pick_preset, run_bench, speech_like
from voice_clone.domain.config import PERFORMANCE_PRESETS


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


def _fake_loads(monkeypatch, loads):
    measured = []

    def fake_run(engine, values, seconds):
        name = next(k for k, (_, v) in PERFORMANCE_PRESETS.items() if v is values)
        measured.append(name)
        return BenchResult(int(values["block_ms"]), [loads[name]])

    monkeypatch.setattr(bench, "run_bench", fake_run)
    return measured


PRESETS = {name: values for name, (_, values) in PERFORMANCE_PRESETS.items()}


def test_pick_preset_returns_heaviest_that_fits_and_stops(monkeypatch):
    measured = _fake_loads(
        monkeypatch, {"minimal": 0.2, "light": 0.3, "balanced": 0.5, "high": 0.8, "ultra": 0.1}
    )

    best, results = pick_preset(TimedFakeEngine(), PRESETS)

    assert best == "balanced"
    assert measured == ["minimal", "light", "balanced", "high"]
    assert set(results) == set(measured)


def test_pick_preset_none_when_lightest_is_too_slow(monkeypatch):
    _fake_loads(monkeypatch, {"minimal": 0.9})

    assert pick_preset(TimedFakeEngine(), PRESETS)[0] is None


@pytest.fixture
def measure_environment(tmp_path, monkeypatch):
    from voice_clone.domain import config

    voices = tmp_path / "voices"
    (voices / "me").mkdir(parents=True)
    (voices / "me" / "me.pth").write_bytes(b"x")
    monkeypatch.setattr(config, "settings_path", lambda: tmp_path / "settings.toml")
    monkeypatch.setattr("voice_clone.domain.paths.voices_dir", lambda: voices)
    monkeypatch.setattr("voice_clone.domain.paths.models_dir", lambda: tmp_path / "models")
    loaded = []

    class FakeRvcEngine(TimedFakeEngine):
        def __init__(self, *args, **kwargs):
            super().__init__()

        def load(self, profile):
            loaded.append(profile.name)

    monkeypatch.setattr("voice_clone.domain.engine.RvcEngine", FakeRvcEngine)
    return loaded


def test_measure_and_save_saves_the_best_preset(measure_environment, monkeypatch):
    from voice_clone.domain.config import load_settings

    _fake_loads(monkeypatch, {"minimal": 0.2, "light": 0.3, "balanced": 0.5, "high": 0.9})

    best, _ = bench.measure_and_save()

    settings = load_settings()
    assert best == "balanced" and measure_environment == ["me"]
    assert (settings.block_ms, settings.context_ms) == (400, 1000)


def test_measure_and_save_leaves_settings_when_nothing_fits(measure_environment, monkeypatch):
    from voice_clone.domain.config import settings_saved

    _fake_loads(monkeypatch, {"minimal": 0.9})

    assert bench.measure_and_save()[0] is None
    assert not settings_saved()


def test_measure_and_save_needs_a_voice(measure_environment, monkeypatch, tmp_path):
    from voice_clone.domain.errors import ProfileError

    monkeypatch.setattr("voice_clone.domain.paths.voices_dir", lambda: tmp_path / "none")

    with pytest.raises(ProfileError):
        bench.measure_and_save()


def test_auto_presets_stop_at_balanced():
    assert list(bench.auto_presets(PERFORMANCE_PRESETS)) == ["minimal", "light", "balanced"]


def test_measure_and_save_never_picks_above_balanced(measure_environment, monkeypatch):
    from voice_clone.domain.config import load_settings

    measured = _fake_loads(
        monkeypatch,
        {"minimal": 0.1, "light": 0.1, "balanced": 0.1, "high": 0.1, "ultra": 0.1},
    )

    best, _ = bench.measure_and_save()

    assert best == "balanced"
    assert measured == ["minimal", "light", "balanced"]
    assert load_settings().block_ms == 400
