# CLAUDE.md

## Project

ios-bridge — an MCP server that lets an LLM connect to and configure Cisco IOS routers.
See `README.md`.

- Package sources: `src/ios_bridge/` (src-layout)
- Entry point: `ios_bridge.cli:main` (`src/ios_bridge/cli.py`); also runs as `uv run python -m ios_bridge`
- `cli.py` is a thin layer: it parses arguments, calls other modules and prints results.
  Functionality lives in separate modules in `src/ios_bridge/`, not in `cli.py`.
- Device connections go through netmiko. Parse `show` output with TextFSM (ntc-templates)
  rather than hand-written regex.

## Git conventions

- **Branch names** use Conventional Commits types as a prefix: `<type>/<short-description>`,
  e.g. `feat/show-commands`, `fix/ssh-reconnect`, `docs/readme`, `chore/ci-setup`.
  Types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `ci`, `build`, `perf`, `style`.
- **Commit messages** do not follow Conventional Commits — write plain, descriptive messages
  (e.g. "Add README with setup instructions").
- **Atomic commits**: each commit covers one logical change (a single feature, fix, or
  refactor). Split unrelated changes into separate commits rather than bundling them.
- **No AI attribution**: never add `Co-Authored-By: Claude` (or any other AI co-author) trailers
  to commits, and no "Generated with Claude Code" footer in PR descriptions.
- **Merging PRs** uses a merge commit (no squash). The subject is the PR title followed by the PR
  number, with an empty body: `gh pr merge <N> --merge --subject "<PR title> (#<N>)" --body ""`.

## Pull requests

- **Title**: brief, a few words in the imperative that name the purpose of the PR, not a list of
  what changed; the details go in the description. No type prefix.
  E.g. "Bootstrap the project", "Add show command tool", "Fix SSH reconnect".
- **Description** uses this template, with all four sections in this order:

  ```markdown
  ## 📌 What
  One or two sentences: what this PR does and where it fits in the project.

  ## 🤔 Why
  The need behind the change, as a short lead-in followed by a list:
  - the problem it solves or what it enables
  - ...

  ## 🛠️ Changes
  - Added/Changed/Removed `path/or/name` – what it is or does
  - ...

  ## 🧪 How to test
  1. A step the reviewer runs, e.g. `uv sync`
  2. The command that shows the change working, and what to expect, e.g. `uv run ios-bridge`
  ```

- **Changes** has one bullet per file or component, starting with Added / Changed / Removed,
  then an en dash and a short description. Group closely related files in one bullet
  (e.g. `uv.lock` and `.python-version`).
- **How to test** lists concrete steps a reviewer can run, in order, with the expected result.
- Keep it short and scannable: no long paragraphs, concrete names in backticks.
- **Before opening a PR**, review the changed code and suggest test cases for it (what to test,
  with which inputs, and the expected outcome). Do not write any tests without explicit approval
  or a direct instruction.

## Python tooling: uv only

Always use `uv`. Never call `pip`, `pip install`, bare `python`, or activate `.venv` by hand.

| Task | Command |
|---|---|
| Run the CLI | `uv run ios-bridge` |
| Run as module | `uv run python -m ios_bridge` |
| Run any script/command in the env | `uv run <cmd>` |
| Add dependency | `uv add <pkg>` |
| Add dev dependency | `uv add --dev <pkg>` |
| Remove dependency | `uv remove <pkg>` |
| Install / sync env from lockfile | `uv sync` |
| One-off tool (not a dependency) | `uvx <tool>` |
| Lint (with autofix) | `uv run ruff check --fix` |
| Format | `uv run ruff format` |
| Type check | `uv run ty check` |

Never edit dependency lists in `pyproject.toml` or `uv.lock` by hand — always go through
`uv add` / `uv remove`.

After editing Python code, run all three before committing:

```sh
uv run ruff check --fix && uv run ruff format && uv run ty check
```

Git hooks (pre-commit) run ruff check and ruff format on commit and ty check on push; enable with
`uv run pre-commit install`. A Claude Code hook (`.claude/hooks/ruff.sh`) also runs ruff format
and ruff check after every Python edit and reports any remaining errors back to Claude.

## Typing

- Every function in `src/` must have full annotations: all arguments and the return type (`-> None` included). One exception: `__init__` may omit `-> None` when at least one argument is annotated (`mypy-init-return`). Ruff's `ANN` rules enforce this.
- Don't use `Any` (`ANN401`) — use a concrete type, a `Protocol`, or `object`.
- Use modern syntax: `list[str]`, `X | None`, not `List` / `Optional`.
- ty warnings fail the check (`error-on-warning`). Don't silence a diagnostic with `# ty: ignore` without a comment explaining why.

## Secrets

Credentials and keys go in `.env`, which is gitignored. Never commit `.env` or hardcode secrets.
