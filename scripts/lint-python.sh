#!/usr/bin/env bash
# Lint Python code: check --fix, format, then check again to verify
set -euo pipefail
echo "━━━ Python Lint ━━━"
ruff check --fix . && ruff format . && ruff check .
