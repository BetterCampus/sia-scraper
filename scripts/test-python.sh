#!/usr/bin/env bash
# Run Python tests (excludes integration and network tests)
# Usage: ./test-python.sh [pytest args...]
set -euo pipefail
cd "$(dirname "$0")/.."
pytest -m "not integration and not network" "$@"
