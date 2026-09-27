"""Exceptions raised by ios-bridge."""


class IOSBridgeError(Exception):
    """Base class for all ios-bridge errors."""


class DeviceConnectionError(IOSBridgeError):
    """Connecting or logging in to a device failed."""


class ConfigError(IOSBridgeError):
    """The config file is missing, invalid or cannot be created."""
