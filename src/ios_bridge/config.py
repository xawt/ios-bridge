"""Device settings loaded from router_config.yaml.

The file is looked up, first match wins, at the --config path, at $IOS_BRIDGE_CONFIG, and at
~/.config/ios-bridge/router_config.yaml (honouring $XDG_CONFIG_HOME).

Error messages name the file and field but never quote the file content, which holds the
device password.
"""

import logging
import os
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any

import yaml

from ios_bridge.errors import ConfigError

log = logging.getLogger(__name__)

CONFIG_NAME = "router_config.yaml"
EXAMPLE_NAME = "router_config.example.yaml"
ENV_VAR = "IOS_BRIDGE_CONFIG"
DEFAULT_TIMEOUT = 30

_REQUIRED_FIELDS = ("host", "username", "password")
_DEVICE_FIELDS = (*_REQUIRED_FIELDS, "timeout")
# Leading or trailing spaces here are always a typo and would reach ssh as-is.
_UNPADDED_FIELDS = ("host", "username")


@dataclass(frozen=True)
class DeviceConfig:
    """Connection details for the device the server manages."""

    host: str
    username: str
    password: str = field(repr=False)
    timeout: int = DEFAULT_TIMEOUT


def default_config_path() -> Path:
    """~/.config/ios-bridge/router_config.yaml, or under $XDG_CONFIG_HOME when it is set."""
    base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(base) / "ios-bridge" / CONFIG_NAME


def resolve_config_path(cli_path: Path | None = None) -> Path:
    """The config path from --config, then $IOS_BRIDGE_CONFIG, then the default location."""
    if cli_path is not None:
        return cli_path.expanduser()
    if env_path := os.environ.get(ENV_VAR):
        return Path(env_path).expanduser()
    return default_config_path()


def example_config() -> bytes:
    """The bundled router_config.example.yaml."""
    return resources.files("ios_bridge").joinpath(EXAMPLE_NAME).read_bytes()


def init_config(path: Path) -> None:
    """Create the config at path from the example, readable only by the owner."""
    try:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        # O_EXCL: never overwrite an existing config, even one created a moment ago.
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise ConfigError(f"{path} already exists; not overwriting it") from None
    except OSError as e:
        raise ConfigError(f"cannot create {path}: {e.strerror}") from None
    with os.fdopen(fd, "wb") as f:
        f.write(example_config())


def load_config(path: Path) -> DeviceConfig:
    """Read and validate the config file; raise ConfigError if it is missing or invalid."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ConfigError(
            f"{path} not found; run 'ios-bridge init-config' to create it, "
            f"or point {ENV_VAR} at an existing config"
        ) from None
    except UnicodeDecodeError:
        raise ConfigError(f"{path} is not valid UTF-8") from None
    except OSError as e:
        raise ConfigError(f"cannot read {path}: {e.strerror}") from None

    _warn_if_exposed(path)

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        # The YAML error message quotes the offending line, so only report its number.
        mark = getattr(e, "problem_mark", None)
        where = f" (line {mark.line + 1})" if mark is not None else ""
        raise ConfigError(f"{path} is not valid YAML{where}") from None

    if not isinstance(data, dict):
        raise ConfigError(f"{path} must contain a mapping")
    if "device" not in data:
        raise ConfigError(f"device section missing in {path}")
    # Unknown keys are not named: a mistyped line could put the password in a key.
    if len(data) > 1:
        raise ConfigError(f"unknown top-level key in {path}; only 'device' is allowed")
    device = data["device"]
    if not isinstance(device, dict):
        raise ConfigError(f"device must be a mapping in {path}")
    if set(device) - set(_DEVICE_FIELDS):
        allowed = ", ".join(_DEVICE_FIELDS)
        raise ConfigError(f"unknown key under device in {path}; allowed keys: {allowed}")

    values = {key: _required_string(device, key, path) for key in _REQUIRED_FIELDS}
    return DeviceConfig(**values, timeout=_timeout(device, path))


def _warn_if_exposed(path: Path) -> None:
    if os.name != "posix":
        return
    mode = path.stat().st_mode & 0o777
    if mode & 0o077:
        log.warning(
            "%s holds the device password but is readable by other users (mode %03o); "
            "run: chmod 600 %s",
            path,
            mode,
            path,
        )


def _required_string(device: dict[Any, Any], key: str, path: Path) -> str:
    if key not in device:
        raise ConfigError(f"device.{key} missing in {path}")
    value = device[key]
    if isinstance(value, int | float) and not isinstance(value, bool):
        raise ConfigError(
            f'device.{key} must be a string in {path}; quote numeric values, e.g. "1234"'
        )
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"device.{key} must be a non-empty string in {path}")
    if key in _UNPADDED_FIELDS and value != value.strip():
        raise ConfigError(f"device.{key} has leading or trailing spaces in {path}")
    return value


def _timeout(device: dict[Any, Any], path: Path) -> int:
    value = device.get("timeout", DEFAULT_TIMEOUT)
    # bool is an int subclass, so `timeout: true` must be rejected explicitly.
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ConfigError(f"device.timeout must be a positive integer in {path}")
    return value
