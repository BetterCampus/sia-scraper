#!/usr/bin/env bash
# Run Python tests with coverage
# Usage: ./test-python-cov.sh [pytest args...]
set -euo pipefail
cd "$(dirname "$0")/.."
pytest -m "not integration and not network" \
    --cov=src/sia_scraper \
    --cov-report=term \
    --cov-report=html \
    --cov-report=xml \
    "$@"
