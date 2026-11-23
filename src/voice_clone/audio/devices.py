from dataclasses import dataclass

import sounddevice

VIRTUAL_OUTPUT_KEYWORDS = ("blackhole", "cable input")


@dataclass(frozen=True)
class AudioDevice:
    index: int
    name: str
    max_input_channels: int
    max_output_channels: int
    default_samplerate: float


def list_input_devices() -> list[AudioDevice]:
    return [device for device in _query_devices() if device.max_input_channels > 0]


def list_output_devices() -> list[AudioDevice]:
    return [device for device in _query_devices() if device.max_output_channels > 0]


def find_virtual_output(devices: list[AudioDevice]) -> AudioDevice | None:
    for device in devices:
        lowered = device.name.lower()
        if any(keyword in lowered for keyword in VIRTUAL_OUTPUT_KEYWORDS):
            return device
    return None


def find_device_by_name(devices: list[AudioDevice], name: str | None) -> AudioDevice | None:
    if name is None:
        return None
    return next((device for device in devices if device.name == name), None)


def rescan_devices() -> None:
    sounddevice._terminate()
    sounddevice._initialize()


def _query_devices() -> list[AudioDevice]:
    return [
        AudioDevice(
            index=index,
            name=str(info["name"]),
            max_input_channels=int(info["max_input_channels"]),
            max_output_channels=int(info["max_output_channels"]),
            default_samplerate=float(info["default_samplerate"]),
        )
        for index, info in enumerate(sounddevice.query_devices())
    ]
