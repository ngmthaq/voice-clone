import pytest

import voice_clone.audio.devices as devices
from voice_clone.audio.devices import (
    AudioDevice,
    find_device_by_name,
    find_virtual_output,
    list_input_devices,
    list_output_devices,
)


def _info(name, inputs, outputs):
    return {
        "name": name,
        "max_input_channels": inputs,
        "max_output_channels": outputs,
        "default_samplerate": 48000.0,
    }


@pytest.fixture
def fake_query(monkeypatch):
    infos = [_info("Mic", 1, 0), _info("Speakers", 0, 2), _info("BlackHole 2ch", 2, 2)]
    monkeypatch.setattr(devices.sounddevice, "query_devices", lambda: infos)


def test_list_input_devices_keeps_devices_with_input_channels(fake_query):
    assert [d.name for d in list_input_devices()] == ["Mic", "BlackHole 2ch"]


def test_list_output_devices_keeps_devices_with_output_channels(fake_query):
    assert [d.name for d in list_output_devices()] == ["Speakers", "BlackHole 2ch"]


def test_devices_keep_their_portaudio_index(fake_query):
    assert [d.index for d in list_output_devices()] == [1, 2]


def _device(name):
    return AudioDevice(0, name, 2, 2, 48000.0)


def test_find_virtual_output_matches_blackhole():
    found = find_virtual_output([_device("Speakers"), _device("BlackHole 2ch")])

    assert found.name == "BlackHole 2ch"


def test_find_virtual_output_matches_cable_input_case_insensitively():
    found = find_virtual_output([_device("Speakers"), _device("CABLE Input (VB-Audio)")])

    assert found.name.startswith("CABLE Input")


def test_find_virtual_output_returns_none_without_virtual_device():
    assert find_virtual_output([_device("Speakers")]) is None


def test_find_device_by_name_returns_exact_match():
    target = _device("Mic")

    assert find_device_by_name([_device("Other"), target], "Mic") is target


def test_find_device_by_name_returns_none_for_none_or_unknown():
    devs = [_device("Mic")]

    assert find_device_by_name(devs, None) is None
    assert find_device_by_name(devs, "Nope") is None
