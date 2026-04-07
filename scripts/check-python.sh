#!/usr/bin/env bash
# Run all Python checks, collect failures, report summary
# Usage: ./check-python.sh
set -uo pipefail

# Enable colors unless NO_COLOR is set or terminal doesn't support it
if [ "${NO_COLOR+set}" = "set" ] || [ ! -t 1 ]; then
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
    ((total++))
    echo -e "${RESET}━━━ $name ━━━"
    if "$@"; then
        echo -e "${GREEN}✓ $name passed${RESET}"
    else
        echo -e "${RED}✗ $name failed${RESET}"
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
