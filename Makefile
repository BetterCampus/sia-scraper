.PHONY: all help setup develop build lint lint-python lint-rust format typecheck test test-python test-python-cov test-rust check check-python check-rust clean

# Default target
.DEFAULT_GOAL := help

## all - Run the default verification suite
all: check

## help - List all targets with descriptions
help:
	@echo "" && \
	echo "━━━ Available targets ━━━" && \
	grep -E '^## ' Makefile | sed 's/^## //' | while read -r line; do \
		name=$$(echo "$$line" | cut -d' ' -f1); \
		desc=$$(echo "$$line" | cut -d' ' -f2-); \
		printf "  \033[36m%-18s\033[0m %s\n" "$$name" "$$desc"; \
	done && echo ""

## setup - Install dependencies and build extension (checkout → ready)
setup:
	@echo "━━━ Setup ━━━"
	@if [ ! -f .cargo/config.toml ] && [ "$${CI:-false}" != "true" ]; then \
		echo ""; \
		echo "⚠️  No .cargo/config.toml found. Copying from example..."; \
		cp .cargo/config.toml_example .cargo/config.toml; \
		echo "⚠️  Please update .cargo/config.toml with your Python paths."; \
		echo ""; \
		echo "After editing .cargo/config.toml, run 'make setup' again to complete installation."; \
		exit 1; \
	elif [ -f .cargo/config.toml ]; then \
		echo "✓ .cargo/config.toml already exists"; \
	else \
		echo "✓ Running in CI mode, skipping .cargo/config.toml check"; \
	fi && \
	pip install -e ".[dev]" && \
	maturin develop

## develop - Build and install Rust extension (incremental)
develop:
	@echo "━━━ Develop ━━━"
	maturin develop

## build - Build release wheels
build:
	@echo "━━━ Build ━━━"
	maturin build --release

## lint - Run all linting (Python + Rust)
lint: lint-python lint-rust

## lint-python - Lint Python code
lint-python:
	./scripts/lint-python.sh

## lint-rust - Lint Rust code
lint-rust:
	./scripts/lint-rust.sh

## format - Format Python code
format:
	@echo "━━━ Format ━━━"
	ruff format .

## typecheck - Run type checker
typecheck:
	@echo "━━━ Type Check ━━━"
	pyright

## test - Run all tests (Python + Rust)
test: test-python test-rust

## test-python - Run Python tests
test-python:
	./scripts/test-python.sh "$(ARGS)"

## test-python-cov - Run Python tests with coverage
test-python-cov:
	./scripts/test-python-cov.sh "$(ARGS)"

## test-rust - Run Rust tests
test-rust:
	./scripts/test-rust.sh "$(ARGS)"

## check - Run full pre-commit check (stop on first failure)
check:
	./scripts/check.sh

## check-python - Run all Python checks (report all failures)
check-python:
	./scripts/check-python.sh

## check-rust - Run all Rust checks (report all failures)
check-rust:
	./scripts/check-rust.sh

## clean - Remove build artifacts
clean:
	@echo "━━━ Clean ━━━"
	rm -rf target/
	rm -rf dist/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .mypy_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✓ Clean complete"
