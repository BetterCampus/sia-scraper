#!/usr/bin/env bash
# Lint Rust code with clippy
set -euo pipefail
echo "━━━ Rust Lint ━━━"
cargo clippy --all-targets --all-features -- -D warnings
