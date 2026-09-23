# CLAUDE.md

## Git conventions

- **Branch names** use Conventional Commits types as a prefix: `<type>/<short-description>`,
  e.g. `feat/device-pairing`, `fix/usb-reconnect`, `docs/readme`, `chore/ci-setup`.
  Types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `ci`, `build`, `perf`, `style`.
- **Commit messages** do not follow Conventional Commits — write plain, descriptive messages
  (e.g. "Add README with setup instructions").

## Dependencies

- Always add packages with `uv add <package-name>` (`uv add --dev <package-name>` for dev tools).
  Never edit dependency lists in `pyproject.toml` or `uv.lock` by hand.
- Remove packages with `uv remove <package-name>`.

## Development commands

- Lint: `uv run ruff check`
- Format: `uv run ruff format`
- Type check: `uv run ty check`
- Test: `uv run pytest`

Git hooks (pre-commit) run ruff on commit and ty + pytest on push; enable with
`uv run pre-commit install`.
