#!/usr/bin/env bash
# Full pre-commit check: stop on first failure
# Usage: ./check.sh
set -euo pipefail
echo "━━━ Full Check (stop on first failure) ━━━"
./scripts/lint-python.sh
./scripts/lint-rust.sh
echo "━━━ Type Check ━━━"
pyright
echo "━━━ Tests ━━━"
./scripts/test-python.sh
./scripts/test-rust.sh
echo "━━━ All checks passed ━━━"
