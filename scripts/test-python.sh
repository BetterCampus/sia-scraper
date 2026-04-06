#!/usr/bin/env bash
# Run Python tests (excludes integration and network tests)
# Usage: ./test-python.sh [pytest args...]
set -euo pipefail
echo "━━━ Python Tests ━━━"
pytest -m "not integration and not network" "$@"
