import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("hardware", "real device used by tests marked 'hardware'")
    group.addoption("--device-host", help="device IP or hostname")
    group.addoption("--device-user", help="login username")
    group.addoption("--device-password", help="login password")
    group.addoption("--device-enable-password", help="enable password, if the device needs one")
    group.addoption("--device-port", type=int, help="port (default: 23 for telnet)")
