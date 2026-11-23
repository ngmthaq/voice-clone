import torch

from voice_clone.engine.device import auto_cpu_threads, configure_cpu_threads, select_torch_device


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
