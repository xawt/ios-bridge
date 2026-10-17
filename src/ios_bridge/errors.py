"""Exceptions raised by ios-bridge. All of them derive from `IOSBridgeError`."""

EXIT_ERROR = 1
EXIT_USAGE = 2


class IOSBridgeError(Exception):
    """Base class for errors ios-bridge raises on purpose.

    Anything else reaching the CLI (netmiko, paramiko, Python itself) is unexpected.
    `exit_code` is the CLI exit code for this kind of error.
    """

    exit_code: int = EXIT_ERROR
