#!/usr/bin/env bash
# Run all Python checks, collect failures, report summary
# Usage: ./check-python.sh
set -uo pipefail

IS_CI="${CI:-false}"
if [ "$IS_CI" = "true" ]; then
    RESET=""
    GREEN=""
    RED=""
else
    RESET="\033[0m"
    GREEN="\033[0;32m"
    RED="\033[0;31m"
fi

failures=0
total=0

run_check() {
    local name="$1"; shift
    local cmd="$*"
    local output
    ((total++))
    echo -e "${RESET}━━━ $name ━━━"
    if output=$(eval "$cmd" 2>&1); then
        echo -e "${GREEN}✓ $name passed${RESET}"
    else
        echo -e "${RED}✗ $name failed${RESET}"
        echo "$output"
        ((failures++))
    fi
    echo
}

echo "━━━ Python Checks ━━━"
echo

run_check "Python lint" ./scripts/lint-python.sh
run_check "Type check" pyright
run_check "Python tests" ./scripts/test-python.sh

echo "━━━ Summary ━━━"
if [ "$failures" -gt 0 ]; then
    echo -e "${RED}✗ $failures/$total check(s) failed${RESET}"
    exit 1
fi
echo -e "${GREEN}✓ All Python checks passed ($total/$total)${RESET}"
