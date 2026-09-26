"""Connection tests against a real IOS device. All commands are read-only."""

from typing import Any

import pytest

from ios_bridge.devices import IOSDevice
from ios_bridge.errors import DeviceConnectionError

pytestmark = pytest.mark.hardware


def test_connected(device: IOSDevice) -> None:
    assert device.connected


def test_show_version(device: IOSDevice) -> None:
    assert "Cisco IOS" in device.execute("show version")


def test_context_manager_disconnects(device_args: dict[str, Any]) -> None:
    dev = IOSDevice(**device_args)
    with dev:
        assert dev.connected
    assert not dev.connected


def test_wrong_password_raises(device_args: dict[str, Any]) -> None:
    args: dict[str, Any] = {**device_args, "password": "wrong-password"}
    dev = IOSDevice(**args)
    with pytest.raises(DeviceConnectionError):
        dev.connect()
