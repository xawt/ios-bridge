"""Locate, load and validate the device config file."""

import os
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml

type Transport = Literal["telnet", "ssh"]

ENV_VAR = "IOS_BRIDGE_CONFIG"
CONFIG_FILENAME = "router_config.yaml"

DEFAULT_TRANSPORT: Transport = "telnet"
DEFAULT_TIMEOUT = 30
DEFAULT_PORTS: dict[Transport, int] = {"telnet": 23, "ssh": 22}
DEVICE_TYPES: dict[Transport, str] = {"telnet": "cisco_ios_telnet", "ssh": "cisco_ios"}

REQUIRED_KEYS = ("host", "username", "password")
OPTIONAL_KEYS = ("transport", "port", "secret", "timeout")


class ConfigError(Exception):
    """The config file is missing, unreadable or invalid. Lists every problem found."""

    def __init__(self, path: Path, problems: list[str]) -> None:
        self.path = path
        self.problems = problems
        lines = "\n".join(f"  - {problem}" for problem in problems)
        super().__init__(f"Invalid config {path}:\n{lines}")


@dataclass(frozen=True)
class DeviceConfig:
    """Connection details for the one device ios-bridge talks to."""

    host: str
    username: str
    password: str = field(repr=False)
    transport: Transport
    port: int
    secret: str = field(repr=False)
    timeout: int

    def netmiko_params(self) -> dict[str, str | int]:
        """Keyword arguments for `netmiko.ConnectHandler`."""
        return {
            "device_type": DEVICE_TYPES[self.transport],
            "host": self.host,
            "username": self.username,
            "password": self.password,
            "secret": self.secret,
            "port": self.port,
            "conn_timeout": self.timeout,
        }


def default_config_path() -> Path:
    """`$XDG_CONFIG_HOME/ios-bridge/router_config.yaml`, falling back to `~/.config`."""
    config_home = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(config_home) / "ios-bridge" / CONFIG_FILENAME


def find_config_path(cli_path: Path | None) -> Path:
    """Pick the config file: `--config`, then `$IOS_BRIDGE_CONFIG`, then the default path."""
    if cli_path is not None:
        return cli_path
    if env_path := os.environ.get(ENV_VAR):
        return Path(env_path)
    return default_config_path()


def is_readable_by_others(path: Path) -> bool:
    """True if users other than the owner can read the file."""
    return bool(path.stat().st_mode & (stat.S_IRGRP | stat.S_IROTH))


def load_config(path: Path) -> DeviceConfig:
    """Read and validate the config file, raising `ConfigError` with every problem found."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ConfigError(
            path, ["file not found (create it with `ios-bridge init-config`)"]
        ) from None
    except OSError as error:
        raise ConfigError(path, [f"cannot read file: {error.strerror}"]) from None

    try:
        data: object = yaml.safe_load(text)
    except yaml.MarkedYAMLError as error:
        where = f" at line {error.problem_mark.line + 1}" if error.problem_mark else ""
        raise ConfigError(path, [f"not valid YAML{where}: {error.problem}"]) from None
    except yaml.YAMLError as error:
        raise ConfigError(path, [f"not valid YAML: {error}"]) from None

    if not isinstance(data, dict):
        raise ConfigError(path, ["expected a `device:` section at the top level"])
    problems = [f"unknown top-level key `{key}`" for key in data if key != "device"]
    device = data.get("device")
    if not isinstance(device, dict):
        raise ConfigError(path, [*problems, "`device` must be a mapping of connection settings"])

    problems += [
        f"device.{key}: unknown key"
        for key in device
        if key not in REQUIRED_KEYS and key not in OPTIONAL_KEYS
    ]
    host = _required_str(device, "host", problems)
    username = _required_str(device, "username", problems)
    password = _required_str(device, "password", problems)
    transport = _transport(device, problems)
    port = _int_in_range(device, "port", DEFAULT_PORTS[transport], 1, 65535, problems)
    secret = _optional_str(device, "secret", problems)
    timeout = _int_in_range(device, "timeout", DEFAULT_TIMEOUT, 1, 3600, problems)

    if problems:
        raise ConfigError(path, problems)
    return DeviceConfig(
        host=host,
        username=username,
        password=password,
        transport=transport,
        port=port,
        secret=secret,
        timeout=timeout,
    )


def _required_str(device: dict, key: str, problems: list[str]) -> str:
    value = device.get(key)
    if value is None:
        problems.append(f"device.{key}: required")
        return ""
    if isinstance(value, bool | int | float):
        problems.append(f'device.{key}: must be a string; quote it, e.g. "{value}"')
        return ""
    if not isinstance(value, str) or not value.strip():
        problems.append(f"device.{key}: must be a non-empty string")
        return ""
    return value


def _optional_str(device: dict, key: str, problems: list[str]) -> str:
    value = device.get(key)
    if value is None:
        return ""
    if isinstance(value, bool | int | float):
        problems.append(f'device.{key}: must be a string; quote it, e.g. "{value}"')
        return ""
    if not isinstance(value, str):
        problems.append(f"device.{key}: must be a string")
        return ""
    return value


def _transport(device: dict, problems: list[str]) -> Transport:
    value = device.get("transport", DEFAULT_TRANSPORT)
    if value == "telnet" or value == "ssh":
        return value
    problems.append(f"device.transport: must be `telnet` or `ssh`, got `{value}`")
    return DEFAULT_TRANSPORT


def _int_in_range(
    device: dict, key: str, default: int, low: int, high: int, problems: list[str]
) -> int:
    value = device.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        problems.append(f"device.{key}: must be a whole number from {low} to {high}")
        return default
    return value
