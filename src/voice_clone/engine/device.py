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
    """Leave one core for the audio callbacks and the UI when there are cores to spare."""
    return default - 1 if default >= 3 else max(1, default)


def configure_cpu_threads(threads: int = 0) -> int:
    """Set how many threads torch uses on the CPU. 0 picks a number automatically."""
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
