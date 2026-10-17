# CLAUDE.md

## Git conventions

- **Branch names** use Conventional Commits types as a prefix: `<type>/<short-description>`,
  e.g. `feat/device-pairing`, `fix/usb-reconnect`, `docs/readme`, `chore/ci-setup`.
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

- **Title**: a plain sentence in the imperative that says what the PR achieves, no type prefix
  (e.g. "Load a fetch-pr directory into a typed structure", "Ignore macOS .DS_Store files").
- **Small, single-purpose PRs** (a one-line config change, a `.gitignore` entry): the description
  is one short paragraph that says what changed and why. No headings.
- **Larger PRs** use this structure:

  ```markdown
  ## Summary
  - One bullet per meaningful change: what was added or changed, naming the modules, functions,
    files and CLI flags in backticks, and how they behave.
  - Mention small side fixes as their own bullet.

  Optional plain paragraphs after the list: naming or design decisions worth knowing, what is
  deliberately not included yet, what comes next, or which PR this one supersedes.

  ## Test plan
  - [x] `uv run ruff check`, `uv run ruff format --check`, `uv run ty check` pass
  - [x] A concrete manual check that was run, with its observed result
  ```

- The test plan lists only checks that were actually run, each with its result. A check that
  wasn't run stays unchecked (`- [ ]`) and says why.
- Write for a reviewer who hasn't seen the work: full sentences, concrete names, no filler.
- **Before opening a PR**, review the changed code and suggest test cases for it (what to test,
  with which inputs, and the expected outcome). Do not write any tests without explicit approval
  or a direct instruction.

## Python tooling: uv only

Always use `uv`. Never call `pip`, `pip install`, bare `python`, or activate `.venv` by hand.

| Task | Command |
|---|---|
| Run as module | `uv run python -m <package>` |
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
`uv run pre-commit install`.

## Typing

- Every function in `src/` must have full annotations: all arguments and the return type (`-> None` included). One exception: `__init__` may omit `-> None` when at least one argument is annotated (`mypy-init-return`). Ruff's `ANN` rules enforce this.
- Don't use `Any` (`ANN401`) — use a concrete type, a `Protocol`, or `object`.
- Use modern syntax: `list[str]`, `X | None`, not `List` / `Optional`.
- ty warnings fail the check (`error-on-warning`). Don't silence a diagnostic with `# ty: ignore` without a comment explaining why.

## Secrets

Credentials and keys go in `.env`, which is gitignored. Never commit `.env` or hardcode secrets.
