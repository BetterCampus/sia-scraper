#!/usr/bin/env bash
# Run Rust library tests
# Usage: ./test-rust.sh [cargo test args...]
set -euo pipefail
echo "━━━ Rust Tests ━━━"
cargo test --no-default-features --lib "$@"
