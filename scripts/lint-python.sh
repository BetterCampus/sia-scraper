#!/usr/bin/env bash
# Lint Python code: CI mode uses --check/--diff, local mode auto-fixes
# Usage: ./lint-python.sh [--check]  (default: auto-fix mode)
set -euo pipefail
echo "━━━ Python Lint ━━━"

if [[ "${1:-}" == "--check" ]] || [[ "${CI:-}" == "true" ]]; then
    ruff check --diff . && ruff format --check .
else
    ruff check --fix . && ruff format .
fi
