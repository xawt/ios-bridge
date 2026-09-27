from collections.abc import Iterator
from typing import Any

import pytest

from ios_bridge.config import load_config, resolve_config_path
from ios_bridge.devices import IOSDevice
from ios_bridge.errors import ConfigError


@pytest.fixture(scope="module")
def device_args(request: pytest.FixtureRequest) -> dict[str, Any]:
    """IOSDevice keyword arguments built from the --device-* options.

    Without --device-host, --device-user and --device-password, the device comes from the
    ios-bridge config file ($IOS_BRIDGE_CONFIG or ~/.config/ios-bridge/router_config.yaml).
    """
    option = request.config.getoption
    host = option("--device-host")
    username = option("--device-user")
    password = option("--device-password")
    timeout = 30
    if not (host and username and password):
        try:
            config = load_config(resolve_config_path())
        except ConfigError as e:
            pytest.skip(f"pass --device-host, --device-user and --device-password, or fix: {e}")
        host, username, password = config.host, config.username, config.password
        timeout = config.timeout
    return {
        "host": host,
        "port": option("--device-port"),
        "method": "telnet",
        "username": username,
        "password": password,
        "enable_password": option("--device-enable-password"),
        "timeout": timeout,
    }


@pytest.fixture(scope="module")
def device(device_args: dict[str, Any]) -> Iterator[IOSDevice]:
    """One connected session shared by the tests in a module."""
    with IOSDevice(**device_args) as dev:
        yield dev
