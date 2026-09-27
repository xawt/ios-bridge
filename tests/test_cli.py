"""The `ios-bridge` command."""

from pathlib import Path

import pytest

from ios_bridge.cli import main
from ios_bridge.config import ENV_VAR, example_config


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv(ENV_VAR, raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))


def test_init_config_creates_default_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["init-config"]) == 0
    path = tmp_path / "xdg" / "ios-bridge" / "router_config.yaml"
    assert path.read_bytes() == example_config()
    assert f"Created {path}" in capsys.readouterr().err


def test_init_config_honours_config_option(tmp_path: Path) -> None:
    path = tmp_path / "custom.yaml"
    assert main(["--config", str(path), "init-config"]) == 0
    assert path.read_bytes() == example_config()


def test_init_config_refuses_to_overwrite(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["init-config"]) == 0
    assert main(["init-config"]) == 1
    assert "already exists" in capsys.readouterr().err


def test_reports_loaded_config(capsys: pytest.CaptureFixture[str]) -> None:
    main(["init-config"])
    assert main([]) == 0
    captured = capsys.readouterr()
    assert "Config OK: admin@10.0.0.11" in captured.err
    assert captured.out == ""


def test_reports_config_error_on_stderr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv(ENV_VAR, str(tmp_path / "missing.yaml"))
    assert main([]) == 1
    captured = capsys.readouterr()
    assert captured.err.startswith(f"ERROR: {tmp_path / 'missing.yaml'} not found")
    assert captured.out == ""
