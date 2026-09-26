"""IOSDevice unit tests; unicon's Connection is replaced so nothing is spawned."""

from typing import Any
from unittest.mock import MagicMock

import pytest

from ios_bridge.devices import IOSDevice, ios


@pytest.fixture(autouse=True)
def fake_connection(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    conn = MagicMock()
    monkeypatch.setattr(ios, "Connection", MagicMock(return_value=conn))
    return conn


def make_device(**overrides: Any) -> IOSDevice:
    args: dict[str, Any] = {"host": "10.0.0.2", "username": "admin", "password": "pw"}
    return IOSDevice(**{**args, **overrides})


@pytest.mark.parametrize("host", ["", "-oProxyCommand=touch /tmp/pwned"])
def test_rejects_option_like_host(host: str) -> None:
    with pytest.raises(ValueError, match="invalid host"):
        make_device(host=host)


def test_ssh_command_ends_options_before_host() -> None:
    assert make_device()._start_command().endswith("-p 22 -- 10.0.0.2")


def test_telnet_command_ends_options_before_host() -> None:
    assert make_device(method="telnet")._start_command() == "telnet -- 10.0.0.2 23"
