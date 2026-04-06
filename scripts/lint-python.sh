#!/usr/bin/env bash
# Lint Python code: check with --diff, format, then check to verify
set -euo pipefail
echo "━━━ Python Lint ━━━"
ruff check --fix --diff . && ruff format . && ruff check .
