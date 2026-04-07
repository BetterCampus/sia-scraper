#!/usr/bin/env bash
# Lint Rust code with clippy
set -euo pipefail
cargo clippy --all-targets --all-features -- -D warnings
