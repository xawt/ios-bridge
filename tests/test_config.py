"""router_config.yaml lookup, creation, loading and validation."""

import logging
import stat
from pathlib import Path

import pytest

from ios_bridge.config import (
    DEFAULT_TIMEOUT,
    ENV_VAR,
    DeviceConfig,
    default_config_path,
    example_config,
    init_config,
    load_config,
    resolve_config_path,
)
from ios_bridge.errors import ConfigError

SECRET = "s3cr3t-pw"

VALID = f"""\
device:
  host: "10.0.0.11"
  username: "admin"
  password: "{SECRET}"
  timeout: 45
"""


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv(ENV_VAR, raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))


def write(tmp_path: Path, text: str, mode: int = 0o600) -> Path:
    path = tmp_path / "router_config.yaml"
    path.write_text(text, encoding="utf-8")
    path.chmod(mode)
    return path


def device_yaml(**fields: str) -> str:
    lines = {"host": '"10.0.0.11"', "username": '"admin"', "password": f'"{SECRET}"', **fields}
    body = "".join(f"  {key}: {value}\n" for key, value in lines.items() if value != "<omit>")
    return f"device:\n{body}"


def config_error(path: Path) -> str:
    with pytest.raises(ConfigError) as exc_info:
        load_config(path)
    message = str(exc_info.value)
    assert SECRET not in message
    return message


# Lookup


def test_default_path_is_under_home_config(tmp_path: Path) -> None:
    expected = tmp_path / "home" / ".config" / "ios-bridge" / "router_config.yaml"
    assert default_config_path() == expected


def test_default_path_honours_xdg_config_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    assert default_config_path() == tmp_path / "xdg" / "ios-bridge" / "router_config.yaml"


def test_resolve_uses_default_without_overrides() -> None:
    assert resolve_config_path() == default_config_path()


def test_resolve_env_var_beats_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_VAR, str(tmp_path / "env.yaml"))
    assert resolve_config_path() == tmp_path / "env.yaml"


def test_resolve_cli_path_beats_env_var(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_VAR, str(tmp_path / "env.yaml"))
    assert resolve_config_path(tmp_path / "cli.yaml") == tmp_path / "cli.yaml"


def test_resolve_expands_tilde(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_VAR, "~/env.yaml")
    assert resolve_config_path() == tmp_path / "home" / "env.yaml"
    assert resolve_config_path(Path("~/cli.yaml")) == tmp_path / "home" / "cli.yaml"


# init_config


def test_init_config_copies_example_owner_only(tmp_path: Path) -> None:
    path = tmp_path / "a" / "b" / "router_config.yaml"
    init_config(path)
    assert path.read_bytes() == example_config()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_init_config_does_not_overwrite(tmp_path: Path) -> None:
    path = write(tmp_path, VALID)
    with pytest.raises(ConfigError, match="already exists"):
        init_config(path)
    assert path.read_text(encoding="utf-8") == VALID


def test_example_file_is_valid(tmp_path: Path) -> None:
    path = tmp_path / "router_config.yaml"
    init_config(path)
    assert load_config(path) == DeviceConfig(
        host="10.0.0.11", username="admin", password="changeme", timeout=30
    )


# Loading


def test_loads_valid_config(tmp_path: Path) -> None:
    assert load_config(write(tmp_path, VALID)) == DeviceConfig(
        host="10.0.0.11", username="admin", password=SECRET, timeout=45
    )


def test_timeout_defaults_to_30(tmp_path: Path) -> None:
    assert load_config(write(tmp_path, device_yaml())).timeout == DEFAULT_TIMEOUT == 30


def test_repr_hides_password(tmp_path: Path) -> None:
    assert SECRET not in repr(load_config(write(tmp_path, VALID)))


def test_warns_when_readable_by_others(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    path = write(tmp_path, VALID, mode=0o644)
    with caplog.at_level(logging.WARNING):
        load_config(path)
    assert "chmod 600" in caplog.text
    assert SECRET not in caplog.text


def test_no_warning_when_owner_only(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        load_config(write(tmp_path, VALID))
    assert caplog.text == ""


# Errors


def test_missing_file(tmp_path: Path) -> None:
    path = tmp_path / "router_config.yaml"
    message = config_error(path)
    assert message.startswith(f"{path} not found")
    assert "ios-bridge init-config" in message
    assert ENV_VAR in message


def test_unreadable_file_reports_reason(tmp_path: Path) -> None:
    assert config_error(tmp_path) == f"cannot read {tmp_path}: Is a directory"


def test_non_utf8_file(tmp_path: Path) -> None:
    path = tmp_path / "router_config.yaml"
    path.write_bytes(b"device:\n  host: \xff\n")
    assert config_error(path) == f"{path} is not valid UTF-8"


def test_invalid_yaml_reports_line_without_content(tmp_path: Path) -> None:
    path = write(tmp_path, f'device:\n  host: "10.0.0.11"\n  password: "{SECRET}\n  x: [\n')
    assert config_error(path).startswith(f"{path} is not valid YAML (line ")


@pytest.mark.parametrize("text", ["", "- device\n", "just a string\n"])
def test_top_level_must_be_mapping(tmp_path: Path, text: str) -> None:
    path = write(tmp_path, text)
    assert config_error(path) == f"{path} must contain a mapping"


def test_device_section_missing(tmp_path: Path) -> None:
    path = write(tmp_path, "other: 1\n")
    assert config_error(path) == f"device section missing in {path}"


def test_unknown_top_level_key(tmp_path: Path) -> None:
    path = write(tmp_path, VALID + f"{SECRET}: 1\n")
    assert config_error(path) == f"unknown top-level key in {path}; only 'device' is allowed"


@pytest.mark.parametrize("text", ["device:\n", "device: [1, 2]\n", "device: host\n"])
def test_device_must_be_mapping(tmp_path: Path, text: str) -> None:
    path = write(tmp_path, text)
    assert config_error(path) == f"device must be a mapping in {path}"


@pytest.mark.parametrize("key", ["timout", SECRET])
def test_unknown_device_key_is_not_quoted(tmp_path: Path, key: str) -> None:
    path = write(tmp_path, device_yaml(**{key: "1"}))
    message = config_error(path)
    assert message == (
        f"unknown key under device in {path}; allowed keys: host, username, password, timeout"
    )
    assert key not in message


@pytest.mark.parametrize("key", ["host", "username", "password"])
def test_required_field_missing(tmp_path: Path, key: str) -> None:
    path = write(tmp_path, device_yaml(**{key: "<omit>"}))
    assert config_error(path) == f"device.{key} missing in {path}"


@pytest.mark.parametrize("key", ["host", "username", "password"])
@pytest.mark.parametrize("value", ['""', '"   "', "null", "[a]", "true"])
def test_required_field_must_be_non_empty_string(tmp_path: Path, key: str, value: str) -> None:
    path = write(tmp_path, device_yaml(**{key: value}))
    assert config_error(path) == f"device.{key} must be a non-empty string in {path}"


@pytest.mark.parametrize("key", ["host", "username", "password"])
@pytest.mark.parametrize("value", ["1234", "12.5"])
def test_numeric_field_suggests_quoting(tmp_path: Path, key: str, value: str) -> None:
    path = write(tmp_path, device_yaml(**{key: value}))
    message = config_error(path)
    assert message == f'device.{key} must be a string in {path}; quote numeric values, e.g. "1234"'


@pytest.mark.parametrize("key", ["host", "username"])
@pytest.mark.parametrize("value", ['" admin"', '"admin "'])
def test_padded_field_is_rejected(tmp_path: Path, key: str, value: str) -> None:
    path = write(tmp_path, device_yaml(**{key: value}))
    assert config_error(path) == f"device.{key} has leading or trailing spaces in {path}"


def test_padded_password_is_kept(tmp_path: Path) -> None:
    path = write(tmp_path, device_yaml(password='" pw "'))
    assert load_config(path).password == " pw "


@pytest.mark.parametrize("value", ["0", "-5", '"30"', "true", "1.5", "null"])
def test_timeout_must_be_positive_integer(tmp_path: Path, value: str) -> None:
    path = write(tmp_path, device_yaml(timeout=value))
    assert config_error(path) == f"device.timeout must be a positive integer in {path}"
