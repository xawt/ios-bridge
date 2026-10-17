#!/usr/bin/env bash
# PostToolUse hook: format and lint a Python file after Claude edits it.
# Exit 2 sends remaining ruff errors back to Claude.
f=$(jq -r '.tool_input.file_path // .tool_response.filePath // empty')
[[ "$f" == *.py ]] || exit 0
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0

uv run --quiet ruff format --quiet "$f" >/dev/null 2>&1
if ! out=$(uv run --quiet ruff check --fix --quiet "$f" 2>&1); then
  echo "$out" >&2
  exit 2
fi
