import argparse
import sys
from importlib.metadata import version
from pathlib import Path

from ios_bridge.config import (
    ConfigError,
    find_config_path,
    is_readable_by_others,
    load_config,
    write_example_config,
)

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help(sys.stderr)
        sys.exit(EXIT_USAGE)
    sys.exit(args.handler(args))


def build_parser() -> argparse.ArgumentParser:
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
        help="config file (default: $IOS_BRIDGE_CONFIG, then "
        "~/.config/ios-bridge/router_config.yaml)",
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

    return parser


def init_config(args: argparse.Namespace) -> int:
    path = find_config_path(args.config)
    try:
        write_example_config(path, force=args.force)
    except FileExistsError:
        print(f"{path} already exists; use --force to overwrite it.", file=sys.stderr)
        return EXIT_ERROR
    except OSError as error:
        print(f"Cannot write {path}: {error.strerror}", file=sys.stderr)
        return EXIT_ERROR
    print(f"Created {path} (mode 600). Edit it with your device details.")
    return EXIT_OK


def check_config(args: argparse.Namespace) -> int:
    path = find_config_path(args.config)
    try:
        config = load_config(path)
    except ConfigError as error:
        print(error, file=sys.stderr)
        return EXIT_USAGE
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
