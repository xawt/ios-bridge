"""The `ios-bridge` command."""

import argparse
import logging
import sys
from pathlib import Path

from ios_bridge.config import ENV_VAR, init_config, load_config, resolve_config_path
from ios_bridge.errors import ConfigError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ios-bridge", description="MCP server for Cisco IOS routers."
    )
    parser.add_argument(
        "--config",
        type=Path,
        metavar="PATH",
        help=f"config file (default: ${ENV_VAR}, else ~/.config/ios-bridge/router_config.yaml)",
    )
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("init-config", help="create the config file from the bundled example")
    args = parser.parse_args(argv)

    # stdout is reserved for the MCP protocol; diagnostics go to stderr.
    logging.basicConfig(stream=sys.stderr, format="%(levelname)s: %(message)s")
    path = resolve_config_path(args.config)

    if args.command == "init-config":
        try:
            init_config(path)
        except ConfigError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 1
        print(f"Created {path}; fill in the device details.", file=sys.stderr)
        return 0

    # The MCP server is not implemented yet, so only report whether the config loads.
    try:
        config = load_config(path)
    except ConfigError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    print(f"Config OK: {config.username}@{config.host} (from {path})", file=sys.stderr)
    return 0
