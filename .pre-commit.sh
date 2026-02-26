#!/usr/bin/env bash
set -euo pipefail

mapfile -t PYTHON_FILES < <(git diff --cached --name-only --diff-filter=ACMR | grep --color=never -E '\.py$' || true)

# Do nothing if no staged python file.
if [[ ${#PYTHON_FILES[@]} -eq 0 ]]; then
  exit 0
fi

if command -v uv >/dev/null 2>&1; then
  RUN=(uv run)
else
  RUN=()
fi

echo "Running ruff check --fix..."
"${RUN[@]}" ruff check --fix "${PYTHON_FILES[@]}"

echo "Running ruff format..."
"${RUN[@]}" ruff format "${PYTHON_FILES[@]}"

git add "${PYTHON_FILES[@]}"

echo "Running ruff check..."
"${RUN[@]}" ruff check "${PYTHON_FILES[@]}"
