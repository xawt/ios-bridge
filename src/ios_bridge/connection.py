"""Open and use a netmiko session to the configured device."""

from contextlib import suppress

from netmiko import BaseConnection, ConnectHandler
from netmiko.exceptions import (
    NetmikoAuthenticationException,
    NetmikoTimeoutException,
    ReadException,
)

from ios_bridge.config import DeviceConfig
from ios_bridge.errors import IOSBridgeError


class DeviceError(IOSBridgeError):
    """Connecting to the device, entering enable mode or running a command failed."""


class Device:
    """A netmiko session to one device, in privileged EXEC (enable) mode once connected.

    Call `connect()` before sending commands and `close()` when done.
    """

    def __init__(self, config: DeviceConfig) -> None:
        self.config = config
        self._session: BaseConnection | None = None

    @property
    def target(self) -> str:
        """`username@host:port`, for messages. Never includes the password."""
        return f"{self.config.username}@{self.config.host}:{self.config.port}"

    @property
    def is_connected(self) -> bool:
        """True between a successful `connect()` and `close()`."""
        return self._session is not None

    def connect(self) -> None:
        """Log in and enter enable mode with `secret`. Does nothing if already connected.

        Raises `DeviceError` if the device can't be reached, rejects the login or the secret.
        """
        if self._session is not None:
            return
        try:
            session = ConnectHandler(**self.config.connection_params())
        except NetmikoAuthenticationException:
            raise DeviceError(
                f"Login to {self.target} failed: check username and password"
            ) from None
        except NetmikoTimeoutException:
            raise DeviceError(
                f"Cannot connect to {self.target}: timed out after {self.config.timeout} s"
            ) from None
        except ReadException as error:
            raise DeviceError(f"Cannot connect to {self.target}: {error}") from None
        except EOFError:
            raise DeviceError(f"Cannot connect to {self.target}: connection closed") from None
        except OSError as error:
            reason = error.strerror or type(error).__name__
            raise DeviceError(f"Cannot connect to {self.target}: {reason}") from None

        try:
            self._enable(session)
        except BaseException:
            session.disconnect()
            raise
        self._session = session

    def _enable(self, session: BaseConnection) -> None:
        """Enter enable mode with `secret`, unless the login already landed there."""
        if session.check_enable_mode():
            return
        if not self.config.secret:
            raise DeviceError(
                f"Login to {self.target} landed in user mode: set device.secret in the config"
            )
        try:
            session.enable()
        except ValueError:
            raise DeviceError(
                f"Cannot enter enable mode on {self.target}: check device.secret"
            ) from None

    def send_command(self, command: str) -> str:
        """Run one exec command and return its raw output.

        Raises `DeviceError` if not connected or the device doesn't answer in time.
        """
        session = self._require_session()
        try:
            output = session.send_command(command)
        except ReadException as error:
            raise DeviceError(f"`{command}` on {self.target} failed: {error}") from None
        except OSError, EOFError:
            raise DeviceError(f"`{command}` on {self.target} failed: connection lost") from None
        if not isinstance(output, str):  # only parsed output (use_textfsm=True) isn't a str
            raise TypeError(f"netmiko returned {type(output).__name__} for raw output")
        return output

    def close(self) -> None:
        """Log out and drop the session. Safe to call when not connected."""
        session, self._session = self._session, None
        if session is not None:
            with suppress(OSError, EOFError):  # the session is gone either way
                session.disconnect()

    def _require_session(self) -> BaseConnection:
        """Return the open session, or raise `DeviceError` if `connect()` wasn't called."""
        if self._session is None:
            raise DeviceError(f"Not connected to {self.target}: call connect() first")
        return self._session
