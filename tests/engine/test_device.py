import pytest
import torch

from voice_clone.engine.device import (
    auto_cpu_threads,
    configure_cpu_threads,
    select_torch_device,
    use_half_precision,
)


def _patch(monkeypatch, cuda, mps):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: cuda)
    monkeypatch.setattr(torch.backends.mps, "is_available", lambda: mps)


def test_prefers_cuda(monkeypatch):
    _patch(monkeypatch, cuda=True, mps=True)

    assert select_torch_device().type == "cuda"


def test_falls_back_to_mps(monkeypatch):
    _patch(monkeypatch, cuda=False, mps=True)

    assert select_torch_device().type == "mps"


def test_falls_back_to_cpu(monkeypatch):
    _patch(monkeypatch, cuda=False, mps=False)

    assert select_torch_device().type == "cpu"


def test_auto_threads_leaves_one_core_free():
    assert auto_cpu_threads(8) == 7


def test_auto_threads_keeps_small_machines_unchanged():
    assert [auto_cpu_threads(n) for n in (0, 1, 2)] == [1, 1, 2]


def test_configure_cpu_threads_uses_explicit_count(monkeypatch):
    seen = []
    monkeypatch.setattr(torch, "set_num_threads", seen.append)
    monkeypatch.setattr(torch, "set_num_interop_threads", lambda n: None)

    assert configure_cpu_threads(3) == 3
    assert seen == [3]


def _capability(monkeypatch, major):
    monkeypatch.setattr(torch.cuda, "get_device_capability", lambda device=None: (major, 5))


@pytest.mark.parametrize(("major", "half"), [(6, False), (7, True), (8, True)])
def test_auto_uses_fp16_only_on_newer_nvidia_cards(monkeypatch, major, half):
    _capability(monkeypatch, major)

    assert use_half_precision(torch.device("cuda"), "auto") is half


def test_forced_fp16_runs_on_older_nvidia_cards(monkeypatch):
    _capability(monkeypatch, 6)

    assert use_half_precision(torch.device("cuda"), "fp16") is True


def test_fp32_is_never_half(monkeypatch):
    _capability(monkeypatch, 8)

    assert use_half_precision(torch.device("cuda"), "fp32") is False


@pytest.mark.parametrize("precision", ["auto", "fp16"])
def test_cpu_never_uses_fp16(precision):
    assert use_half_precision(torch.device("cpu"), precision) is False


def test_apple_gpu_uses_fp16_only_when_asked():
    mps = torch.device("mps")

    assert (use_half_precision(mps, "auto"), use_half_precision(mps, "fp16")) == (False, True)


def test_unknown_precision_is_rejected():
    with pytest.raises(ValueError):
        use_half_precision(torch.device("cpu"), "fp8")
