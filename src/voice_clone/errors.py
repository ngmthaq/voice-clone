class VoiceCloneError(Exception):
    """Base class for all expected voice-clone errors."""


class DeviceNotFoundError(VoiceCloneError):
    pass


class ProfileError(VoiceCloneError):
    pass


class ModelDownloadError(VoiceCloneError):
    pass


class ModelLoadError(VoiceCloneError):
    pass


class TrainingError(VoiceCloneError):
    pass


class TrainingStoppedError(TrainingError):
    """The user stopped training. The last checkpoint is kept, so it can continue later."""
