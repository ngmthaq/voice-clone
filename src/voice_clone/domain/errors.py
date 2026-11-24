class VoiceCloneError(Exception):
    pass


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
    pass
