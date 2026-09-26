"""Cisco IOS device over SSH or Telnet, backed by unicon (no testbed file)."""

import shlex
from contextlib import suppress
from typing import Literal

from unicon import Connection
from unicon.core import errors as unicon_errors

from ios_bridge.devices.base import Device
from ios_bridge.errors import DeviceConnectionError

Method = Literal["ssh", "telnet"]

DEFAULT_PORTS: dict[str, int] = {"ssh": 22, "telnet": 23}

# Modern OpenSSH no longer offers the algorithms that IOS 15.x uses by default.
LEGACY_SSH_OPTIONS: tuple[str, ...] = (
    "-o KexAlgorithms=+diffie-hellman-group14-sha1",
    "-o HostKeyAlgorithms=+ssh-rsa",
    "-o PubkeyAcceptedAlgorithms=+ssh-rsa",
    "-o StrictHostKeyChecking=no",
    "-o UserKnownHostsFile=/dev/null",
)

_CONNECT_ERRORS = (
    unicon_errors.ConnectionError,
    unicon_errors.TimeoutError,
    unicon_errors.CredentialsExhaustedError,
    unicon_errors.UniconAuthenticationError,
    unicon_errors.SpawnInitError,
    unicon_errors.StateMachineError,
    unicon_errors.EOF,
)


class IOSDevice(Device):
    """A Cisco IOS switch or router reached over SSH or Telnet.

    The transport only changes the command unicon spawns; login, enable mode, prompts and
    command handling are the same for both.
    """

    def __init__(
        self,
        host: str,
        port: int | None = None,
        method: Method = "ssh",
        *,
        username: str,
        password: str,
        enable_password: str | None = None,
        ssh_options: tuple[str, ...] = LEGACY_SSH_OPTIONS,
        timeout: int = 60,
    ) -> None:
        if method not in DEFAULT_PORTS:
            raise ValueError(f"method must be 'ssh' or 'telnet', got {method!r}")
        # A leading dash would make ssh/telnet parse the host as an option (e.g. ProxyCommand).
        if not host or host.startswith("-"):
            raise ValueError(f"invalid host: {host!r}")
        self.host = host
        self.port = port if port is not None else DEFAULT_PORTS[method]
        self.method = method
        self.username = username
        self.ssh_options = ssh_options

        credentials: dict[str, dict[str, str]] = {
            "default": {"username": username, "password": password},
        }
        if enable_password is not None:
            credentials["enable"] = {"password": enable_password}

        self._conn = Connection(
            hostname=host,
            start=[self._start_command()],
            os="ios",
            credentials=credentials,
            # The device hostname does not need to be known in advance.
            learn_hostname=True,
            # Don't change the device config on connect (unicon's default does).
            init_config_commands=[],
            # Keep stdout clean for the MCP stdio transport.
            log_stdout=False,
            connection_timeout=timeout,
        )

    def _start_command(self) -> str:
        host = shlex.quote(self.host)
        if self.method == "telnet":
            return f"telnet -- {host} {self.port}"
        options = " ".join(self.ssh_options)
        return f"ssh {options} -l {shlex.quote(self.username)} -p {self.port} -- {host}"

    def connect(self) -> None:
        try:
            self._conn.connect()
        except _CONNECT_ERRORS as e:
            self._close_quietly()
            raise DeviceConnectionError(
                f"Failed to connect to {self.host}:{self.port} over {self.method}: {e}"
            ) from e

    def disconnect(self) -> None:
        self._close_quietly()

    def _close_quietly(self) -> None:
        # unicon raises if nothing was ever spawned, but a half-open session must still be closed.
        with suppress(Exception):
            self._conn.disconnect()

    @property
    def connected(self) -> bool:
        return bool(self._conn.connected)

    def execute(self, command: str) -> str:
        return self._conn.execute(command)

    def configure(self, lines: str | list[str]) -> str:
        return self._conn.configure(lines)
