#!/usr/bin/env bash
# PostToolUse hook: format and lint a Python file after Claude edits it.
# Exit 2 sends remaining ruff errors back to Claude.
if ! command -v jq >/dev/null; then
  echo "ruff hook skipped: jq is not installed" >&2
  exit 1
fi
f=$(jq -r '.tool_input.file_path // .tool_response.filePath // empty')
[[ "$f" == *.py ]] || exit 0
project=$(realpath "${CLAUDE_PROJECT_DIR:-.}") || exit 0
# Only lint files inside this project, and skip files that no longer exist.
[[ "$(realpath -m "$f")" == "$project"/* && -f "$f" ]] || exit 0
cd "$project" || exit 0
if ! command -v uv >/dev/null; then
  echo "ruff hook skipped: uv is not installed" >&2
  exit 1
fi

uv run --quiet ruff format --quiet "$f" >/dev/null 2>&1
if ! out=$(uv run --quiet ruff check --fix --quiet "$f" 2>&1); then
  echo "$out" >&2
  exit 2
fi
