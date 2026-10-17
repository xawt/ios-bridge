```text
██╗ ██████╗ ███████╗      ██████╗ ██████╗ ██╗██████╗  ██████╗ ███████╗
██║██╔═══██╗██╔════╝      ██╔══██╗██╔══██╗██║██╔══██╗██╔════╝ ██╔════╝
██║██║   ██║███████╗█████╗██████╔╝██████╔╝██║██║  ██║██║  ███╗█████╗
██║██║   ██║╚════██║╚════╝██╔══██╗██╔══██╗██║██║  ██║██║   ██║██╔══╝
██║╚██████╔╝███████║      ██████╔╝██║  ██║██║██████╔╝╚██████╔╝███████╗
╚═╝ ╚═════╝ ╚══════╝      ╚═════╝ ╚═╝  ╚═╝╚═╝╚═════╝  ╚═════╝ ╚══════╝

  ┌─────────┐     MCP      ┌────────────┐   netmiko    ┌───────────┐
  │   LLM   │ <──────────> │ ios-bridge │ <──────────> │ Cisco IOS │
  └─────────┘    stdio     └────────────┘  ssh/telnet  └───────────┘

  R1(config)# talk to your routers in plain English_
```

<div align="center">

**An [MCP](https://modelcontextprotocol.io) server that lets an LLM connect to and configure Cisco IOS routers.**

[![Python](https://img.shields.io/badge/python-3.15%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org)
[![MCP](https://img.shields.io/badge/MCP-server-8A2BE2?style=for-the-badge)](https://modelcontextprotocol.io)
[![netmiko](https://img.shields.io/badge/powered%20by-netmiko-049FD9?style=for-the-badge)](https://github.com/ktbyers/netmiko)
[![TextFSM](https://img.shields.io/badge/parsed%20with-TextFSM-2E8B57?style=for-the-badge)](https://github.com/google/textfsm)
[![uv](https://img.shields.io/badge/managed%20with-uv-DE5FE9?style=for-the-badge)](https://docs.astral.sh/uv/)
[![Status](https://img.shields.io/badge/status-early%20development-orange?style=for-the-badge)](#-what-is-it)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue?style=for-the-badge)](LICENSE)

</div>

---

> [!WARNING]
> **ios-bridge is in early development.** The features described below show where the project is
> going and may change before the first release.

## ✨ What is it?

**ios-bridge** sits between an AI assistant and your network gear. It exposes Cisco IOS devices as
[Model Context Protocol](https://modelcontextprotocol.io) tools, so any MCP client (Claude Desktop,
Claude Code, and others) can:

- 🔌 **Connect** to routers over SSH or Telnet (console servers included)
- 🔍 **Inspect** them: `show` commands, running config, interfaces, routing tables
- 🛠️ **Configure** them: push config blocks from a plain-English request
- 🛡️ **Stay safe**: config changes are shown to you before anything is applied

Under the hood it uses [**netmiko**](https://github.com/ktbyers/netmiko), a widely used library for
managing network devices over SSH and Telnet. netmiko handles prompts, enable mode, config mode,
pagination and all the other quirks of the IOS CLI. `show` output is parsed with
[**TextFSM**](https://github.com/google/textfsm) templates from
[ntc-templates](https://github.com/networktocode/ntc-templates), so the LLM gets structured data
instead of raw CLI text.

## 🧭 How it works

```mermaid
flowchart LR
    U([👤 You]) -->|"Add a loopback 10 on R1<br/>with 10.10.10.1/32"| L[🧠 LLM / MCP client]
    L <-->|MCP · stdio| B[⚡ ios-bridge]
    B <-->|netmiko · SSH / Telnet| R1[🛜 R1 · IOS]
```

1. You ask your assistant for something in plain language.
2. The LLM calls ios-bridge tools over MCP.
3. ios-bridge opens (or reuses) a netmiko session to the device, runs the commands and returns
   structured output to the LLM.

## 🛠️ Development

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync                        # create .venv and install the package + dev tools
uv run pre-commit install      # enable git hooks (once per clone)
uv run ios-bridge              # run the CLI (the MCP server is planned)
```

| Task       | Command               |
|------------|-----------------------|
| Lint       | `uv run ruff check`   |
| Format     | `uv run ruff format`  |
| Type check | `uv run ty check`     |

Git hooks run ruff check and ruff format on every commit, and ty check on every push.

## ⚠️ Disclaimer

> [!CAUTION]
> **Do not use ios-bridge in production.** This is an early-development, experimental project.
> It lets an LLM change device configuration, and it can get things wrong. Use it only in a lab
> or other disposable environment, at your own risk.

## 📄 License

Licensed under the [Apache License 2.0](LICENSE).
