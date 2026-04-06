#!/usr/bin/env bash
# Run Python tests with coverage
# Usage: ./test-python-cov.sh [pytest args...]
set -euo pipefail
echo "━━━ Python Tests with Coverage ━━━"
pytest -m "not integration and not network" \
    --cov=src/sia_scraper \
    --cov-report=term \
    --cov-report=html \
    --cov-report=xml \
    "$@"
