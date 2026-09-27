# ios-bridge MCP server: specification

ios-bridge is an MCP server (stdio transport) that lets an LLM run commands on, and configure, a
single Cisco IOS router over SSH. This document describes the target design. Items marked
*(planned)* are not implemented yet.

## Project layout

```text
src/ios_bridge/
├── cli.py                      # `ios-bridge` command: --config, init-config
├── server.py                   # MCP server and tools (planned)
├── config.py                   # finds, creates, loads and validates router_config.yaml
├── router_config.example.yaml  # commented template, shipped in the package
├── errors.py                   # IOSBridgeError, DeviceConnectionError, ConfigError
└── devices/                    # Device interface and unicon-backed IOSDevice
docs/mcp-spec.md                # this document
```

## Dependencies

- `pyyaml`: reads `router_config.yaml` with `yaml.safe_load()`
- `unicon` / `pyats` / `genie`: device sessions (`IOSDevice`)
- `mcp`: MCP server SDK *(planned)*

Configuration does not use `.env` files, `python-dotenv` or a keyring.

## Configuration

The server reads a single YAML file, `router_config.yaml`:

```yaml
device:
  host: "10.0.0.11"
  username: "admin"
  password: "changeme"
  timeout: 30
```

### Location

The config is user data, so it lives outside the package and the repository. The path is chosen
in this order, and the first match wins; later locations are not tried:

1. `--config PATH` on the command line
2. the `IOS_BRIDGE_CONFIG` environment variable
3. `$XDG_CONFIG_HOME/ios-bridge/router_config.yaml`, or `~/.config/ios-bridge/router_config.yaml`
   when `XDG_CONFIG_HOME` is not set

A leading `~` is expanded. A relative path is relative to the working directory, which MCP
clients do not control well, so use absolute paths in client configs. The current directory is
never searched implicitly. For development in the repo, use
`IOS_BRIDGE_CONFIG=./router_config.yaml` (the file name is git-ignored).

`resolve_config_path()` in `config.py` implements this lookup.

### Setup

```bash
ios-bridge init-config                     # default location
ios-bridge --config PATH init-config       # somewhere else (IOS_BRIDGE_CONFIG works too)
```

`init-config` copies the bundled `router_config.example.yaml` (read with `importlib.resources`,
so it works from an installed wheel) to the resolved path. It creates missing parent folders
with mode `700`, creates the file with mode `600`, and refuses to overwrite an existing file.
The example is commented, so it documents the fields where the user edits them.

Running `ios-bridge` with no command loads the config and reports `Config OK` or the error. This
is a placeholder until the MCP server exists.

### Fields

| Field             | Required | Rules                                         |
|-------------------|----------|-----------------------------------------------|
| `device.host`     | yes      | non-empty string: device IP or hostname       |
| `device.username` | yes      | non-empty string                              |
| `device.password` | yes      | non-empty string (quote numeric passwords)    |
| `device.timeout`  | no       | positive integer, seconds; default `30`       |

The top-level object and the `device` section must both be mappings. `device` is the only
allowed top-level key, and `device` accepts only the four keys above, so typos such as `timout`
are reported instead of ignored. `host` and `username` must not have leading or trailing
spaces; the password is taken as written.

### Lifecycle

The config is read once, when the server process starts. Edits to the file take effect only
after the server is restarted.

### Secrets

For this demo the password is stored in plain text in `router_config.yaml`. The file lives
outside the repository and the package, so it cannot be committed or shipped by accident;
`router_config.yaml` is still listed in `.gitignore` as a safety net for development copies.

On POSIX systems, loading a config that other users can read (any group or other permission
bit) logs a warning to stderr that suggests `chmod 600`; the config is still loaded.

The password and the full config are never written to logs or returned by tools. The
`DeviceConfig` repr leaves out the password. Config errors name the file path and field but
never quote file content: YAML syntax errors report only the line number, and unknown keys are
not named (a mistyped line could put the password in a key).

### Errors

A missing file, invalid YAML or an invalid field does not stop the MCP server from starting.
`load_config()` raises `ConfigError`; the server catches it at startup and every tool then
returns the message with an `ERROR:` prefix, for example:

```text
ERROR: /home/you/.config/ios-bridge/router_config.yaml not found; run 'ios-bridge init-config' to create it, or point IOS_BRIDGE_CONFIG at an existing config
ERROR: cannot read /home/you/.config/ios-bridge/router_config.yaml: Permission denied
ERROR: /home/you/.config/ios-bridge/router_config.yaml is not valid UTF-8
ERROR: /home/you/.config/ios-bridge/router_config.yaml is not valid YAML (line 4)
ERROR: /home/you/.config/ios-bridge/router_config.yaml must contain a mapping
ERROR: device section missing in /home/you/.config/ios-bridge/router_config.yaml
ERROR: unknown top-level key in /home/you/.config/ios-bridge/router_config.yaml; only 'device' is allowed
ERROR: device must be a mapping in /home/you/.config/ios-bridge/router_config.yaml
ERROR: unknown key under device in /home/you/.config/ios-bridge/router_config.yaml; allowed keys: host, username, password, timeout
ERROR: device.host missing in /home/you/.config/ios-bridge/router_config.yaml
ERROR: device.password must be a string in /home/you/.config/ios-bridge/router_config.yaml; quote numeric values, e.g. "1234"
ERROR: device.password must be a non-empty string in /home/you/.config/ios-bridge/router_config.yaml
ERROR: device.host has leading or trailing spaces in /home/you/.config/ios-bridge/router_config.yaml
ERROR: device.timeout must be a positive integer in /home/you/.config/ios-bridge/router_config.yaml
```

## Device connection *(planned)*

- The SSH session is opened lazily, on the first tool call that needs the device, not at server
  start. A server with a broken or missing config, or an unreachable device, still starts and
  answers MCP requests.
- The session uses `IOSDevice` with `method="ssh"`, the configured host, username and password,
  and `timeout` as the connection timeout. Later tool calls reuse the open session.
- Connection failures are returned to the LLM as `ERROR: ...` messages without credentials.

## Acceptance criteria

Configuration:

- [x] `router_config.example.yaml` is commented, ships in the wheel and loads as a valid config.
- [x] The config path comes from `--config`, then `IOS_BRIDGE_CONFIG`, then
      `$XDG_CONFIG_HOME/ios-bridge/` or `~/.config/ios-bridge/`; the first match wins.
- [x] The config never lives inside the package or depends on the working directory by default.
- [x] `ios-bridge init-config` copies the example to the resolved path with mode `600`, creates
      parent folders, and never overwrites an existing file.
- [x] Loading a config readable by other users logs a warning; the config still loads.
- [x] YAML is loaded with `yaml.safe_load()`; `python-dotenv` is not a dependency.
- [x] `host`, `username` and `password` must be present and non-empty strings; numeric values get
      a hint to quote them; `host` and `username` must not have surrounding spaces.
- [x] `timeout` is optional, defaults to 30 and must be a positive integer (not a bool or float).
- [x] A non-mapping top-level object or `device` section, or an unknown key, is rejected.
- [x] Every invalid case raises `ConfigError` with a readable message naming the file path and
      field.
- [x] No error message, warning or repr contains the password or quotes file content.
- [x] The README explains `init-config`, the lookup order and the MCP client `env` setting.

Server *(planned)*:

- [ ] The config is loaded once at process start; changes need a restart.
- [ ] The server starts even when the config is missing or invalid.
- [ ] With a bad config, every tool returns a message starting with `ERROR:`.
- [ ] The SSH connection is opened on the first tool call and reused afterwards.
- [ ] Nothing logged or returned by a tool contains the password.
