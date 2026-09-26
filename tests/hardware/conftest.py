from collections.abc import Iterator
from typing import Any

import pytest

from ios_bridge.devices import IOSDevice


@pytest.fixture(scope="module")
def device_args(request: pytest.FixtureRequest) -> dict[str, Any]:
    """IOSDevice keyword arguments built from the --device-* options."""
    option = request.config.getoption
    host = option("--device-host")
    username = option("--device-user")
    password = option("--device-password")
    if not (host and username and password):
        pytest.skip("pass --device-host, --device-user and --device-password")
    return {
        "ip": host,
        "port": option("--device-port"),
        "method": "telnet",
        "username": username,
        "password": password,
        "enable_password": option("--device-enable-password"),
        "timeout": 30,
    }


@pytest.fixture(scope="module")
def device(device_args: dict[str, Any]) -> Iterator[IOSDevice]:
    """One connected session shared by the tests in a module."""
    with IOSDevice(**device_args) as dev:
        yield dev
