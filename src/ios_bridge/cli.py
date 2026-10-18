"""Command-line interface: parses arguments, calls the other modules and prints results."""

import argparse
import json
import sys
from importlib.metadata import version
from pathlib import Path

from ios_bridge.config import (
    find_config_path,
    is_readable_by_others,
    load_config,
    write_example_config,
)
from ios_bridge.connection import Device
from ios_bridge.errors import EXIT_USAGE, IOSBridgeError, UsageError

EXIT_OK = 0


def main(argv: list[str] | None = None) -> None:
    """Run the `ios-bridge` command and exit with the command's exit code.

    `argv` defaults to `sys.argv[1:]`. Without a command, prints the help and exits with 2.
    An `IOSBridgeError` is printed as `ios-bridge: error: ...` and exits with its `exit_code`;
    any other exception is a bug and propagates with its traceback.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help(sys.stderr)
        sys.exit(EXIT_USAGE)
    try:
        sys.exit(args.handler(args))
    except IOSBridgeError as error:
        print(f"ios-bridge: error: {error}", file=sys.stderr)
        sys.exit(error.exit_code)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser with one subcommand per command.

    Each subcommand stores its handler in `args.handler`; `--config` is shared by all of them.
    """
    parser = argparse.ArgumentParser(
        prog="ios-bridge",
        description="MCP server that lets an LLM connect to and configure Cisco IOS routers.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {version('ios-bridge')}")

    config_option = argparse.ArgumentParser(add_help=False)
    config_option.add_argument(
        "--config",
        type=Path,
        metavar="PATH",
        help="config file (default: $IOS_BRIDGE_CONFIG, then ./.config/router_config.yaml, "
        "then ~/.config/ios-bridge/router_config.yaml)",
    )

    commands = parser.add_subparsers(dest="command", metavar="<command>")

    init = commands.add_parser(
        "init-config",
        parents=[config_option],
        help="write a commented example config file (mode 600)",
    )
    init.add_argument("--force", action="store_true", help="overwrite an existing file")
    init.set_defaults(handler=init_config)

    check = commands.add_parser(
        "check-config",
        parents=[config_option],
        help="load and validate the config, print a summary",
    )
    check.set_defaults(handler=check_config)

    device_check = commands.add_parser(
        "check-device",
        parents=[config_option],
        help="connect to the device and print what `show version` reports",
    )
    device_check.set_defaults(handler=check_device)

    run = commands.add_parser(
        "run",
        parents=[config_option],
        help="run a `show` command on the device and print its output",
    )
    run.add_argument("words", nargs="+", metavar="COMMAND", help="the command, e.g. `sh ip int br`")
    run.add_argument(
        "-p", "--parse", action="store_true", help="parse the output with TextFSM, print JSON"
    )
    run.set_defaults(handler=run_command)

    return parser


def init_config(args: argparse.Namespace) -> int:
    """`init-config`: write the example config file."""
    path = find_config_path(args.config)
    write_example_config(path, force=args.force)
    print(f"Created {path} (mode 600). Edit it with your device details.")
    return EXIT_OK


def check_config(args: argparse.Namespace) -> int:
    """`check-config`: load the config and print a summary with secrets masked.

    Warns if other users can read the file.
    """
    path = find_config_path(args.config)
    config = load_config(path)
    if is_readable_by_others(path):
        print(
            f"Warning: {path} is readable by other users; run `chmod 600 {path}`.",
            file=sys.stderr,
        )
    print(f"Config: {path}")
    print(f"  host       {config.host}")
    print(f"  username   {config.username}")
    print("  password   ***")
    if config.secret:
        print("  secret     ***")
    print(f"  transport  {config.transport} (port {config.port})")
    print(f"  timeout    {config.timeout} s")
    return EXIT_OK


def check_device(args: argparse.Namespace) -> int:
    """`check-device`: connect, run `show version` and print hostname, version, model, uptime."""
    config = load_config(find_config_path(args.config))
    device = Device(config)
    device.connect()
    try:
        version = device.send_parsed("show version")[0]
    finally:
        device.close()
    print(f"Connected to {device.target} ({config.transport})")
    for label, key in (
        ("hostname", "hostname"),
        ("version", "version"),
        ("model", "hardware"),
        ("uptime", "uptime"),
    ):
        value = version.get(key) or "?"
        print(f"  {label:<9} {value if isinstance(value, str) else ', '.join(value)}")
    return EXIT_OK


def run_command(args: argparse.Namespace) -> int:
    """`run`: run one `show` command and print its raw output, or JSON with `--parse`."""
    command = " ".join(args.words)
    if not is_show_command(command):
        raise UsageError(f"Only `show` commands are allowed, got `{command}`")
    device = Device(load_config(find_config_path(args.config)))
    device.connect()
    try:
        output = device.send_parsed(command) if args.parse else device.send_command(command)
    finally:
        device.close()
    print(json.dumps(output, indent=2) if args.parse else output)
    return EXIT_OK


def is_show_command(command: str) -> bool:
    """True if the first word is `show` or an abbreviation IOS accepts for it (`sh`, `sho`)."""
    first = command.split(maxsplit=1)[0].lower() if command.strip() else ""
    return len(first) >= 2 and "show".startswith(first)
