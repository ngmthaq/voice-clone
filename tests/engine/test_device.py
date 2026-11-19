import torch

from voice_clone.engine.device import select_torch_device


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
