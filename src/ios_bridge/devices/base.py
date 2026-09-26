"""Abstract device interface shared by real and mock devices."""

from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self


class Device(ABC):
    """A network device that runs CLI commands and returns their output."""

    @abstractmethod
    def connect(self) -> None:
        """Open the session to the device."""

    @abstractmethod
    def disconnect(self) -> None:
        """Close the session to the device."""

    @property
    @abstractmethod
    def connected(self) -> bool:
        """Whether the session is open."""

    @abstractmethod
    def execute(self, command: str) -> str:
        """Run an exec-mode command and return its output."""

    @abstractmethod
    def configure(self, lines: str | list[str]) -> str:
        """Apply configuration lines in config mode and return the output."""

    def __enter__(self) -> Self:
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.disconnect()
