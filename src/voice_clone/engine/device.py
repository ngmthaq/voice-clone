import logging

import torch

logger = logging.getLogger(__name__)

_threads_configured = False
_TORCH_DEFAULT_THREADS = torch.get_num_threads()


def select_torch_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    mps = getattr(torch.backends, "mps", None)
    if mps is not None and mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def auto_cpu_threads(default: int) -> int:
    return default - 1 if default >= 3 else max(1, default)


def configure_cpu_threads(threads: int = 0) -> int:
    global _threads_configured
    count = int(threads) if threads > 0 else auto_cpu_threads(_TORCH_DEFAULT_THREADS)
    torch.set_num_threads(count)
    if not _threads_configured:
        try:
            torch.set_num_interop_threads(1)
        except RuntimeError:
            logger.debug("torch inter-op threads were already set", exc_info=True)
        _threads_configured = True
    logger.info("Using %d CPU thread(s) for the voice model", count)
    return count


PRECISIONS = ("auto", "fp32", "fp16")
HALF_MIN_CUDA_MAJOR = 7


def use_half_precision(device: torch.device, precision: str = "auto") -> bool:
    if precision not in PRECISIONS:
        raise ValueError(f"precision must be one of {PRECISIONS}")
    if precision == "fp32" or device.type == "cpu":
        if precision == "fp16":
            logger.warning("fp16 is not used on the CPU; using fp32")
        return False
    if precision == "fp16":
        return device.type in ("cuda", "mps")
    if device.type != "cuda":
        return False
    major, _ = torch.cuda.get_device_capability(device)
    return major >= HALF_MIN_CUDA_MAJOR
