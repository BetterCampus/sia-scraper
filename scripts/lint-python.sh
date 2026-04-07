#!/usr/bin/env bash
# Lint Python code: CI mode uses --check/--diff, local mode auto-fixes
# Usage: ./lint-python.sh [--check]  (default: auto-fix mode)
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ "${1:-}" == "--check" ]] || [[ "${CI:-}" == "true" ]]; then
    exit_code=0
    ruff check --diff . || exit_code=1
    ruff format --check . || exit_code=1
    exit $exit_code
else
    ruff check --fix . && ruff format .
fi
