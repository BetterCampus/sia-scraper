# Contributing to sia-scraper

Thanks for contributing to `sia-scraper`.

This document describes how to set up your environment, follow project standards,
and submit high-quality pull requests.

## Development Setup

Prerequisites:

- Python 3.10+
- Git

Clone and set up:

```bash
git clone https://github.com/BetterCampus/sia-scraper.git
cd sia-scraper
make setup
```

This installs Python dependencies, builds the Rust extension, and configures
the `.cargo/config.toml` file if missing.

### Rust Extension Workflow

After modifying Rust code, rebuild the extension:

```bash
make develop
```

Quick validation:

```bash
make check-rust    # lint + test
make check         # full verification (Python + Rust)
```

Why this is required:

- The project uses `setuptools` for editable Python installs and `maturin` for Rust wheels.
- `maturin develop` and `pip install -e .` can overwrite each other in local environments.
- The Makefile handles this correctly by using `maturin develop` under the hood.

## Code Standards

The project enforces:

- Type hints in all function/method signatures and key attributes
- Python 3.10 modern syntax (`X | None`, `list[str]`, etc.)
- Google-style docstrings where applicable
- Import ordering and formatting via Ruff
- Max line length target of 100 characters

Naming conventions:

- `snake_case`: functions, methods, variables
- `PascalCase`: classes
- `UPPER_SNAKE_CASE`: constants
- `_leading_underscore`: private members

## Project Layout

Core source tree:

```text
src/sia_scraper/
├── scraper.py
├── session.py
├── core/
├── utils/
├── constants/
└── parsers/
```

Tests mirror the source structure:

```text
tests/
├── core/
├── utils/
└── ...
```

## Testing Guidelines

- Add/adjust tests for every behavioral change.
- Prefer unit tests with mocking over live network calls.
- Use integration tests only when real SIA interaction is required.

Common commands:

```bash
# All tests
make test

# With coverage (for CI)
make test-python-cov

# Specific file (pass-through)
make test-python ARGS="tests/utils/test_date_formatter.py"

# Pattern
make test-python ARGS="-k format"
```

### Fixture-based Regression Tests

The repository includes sanitized snapshots of live SIA responses under `tests/fixtures/`.
These fixtures back contract and regression tests designed to detect Oracle ADF structure
changes early.

- Fixture validity: `pytest tests/fixtures/test_fixtures_validity.py`
- Structure contracts: `pytest tests/fixtures/test_contracts.py`
- Parser regression baselines: `pytest tests/fixtures/test_regression.py`

Refresh fixtures when SIA markup or parser behavior changes:

```bash
python scripts/capture_sia_fixtures.py
pytest tests/fixtures/test_fixtures_validity.py tests/fixtures/test_contracts.py tests/fixtures/test_regression.py
```

Notes:

- Capture configuration lives in `scripts/capture_config.yaml`.
- The capture script keeps only latest date-stamped fixtures by default.
- Captured data is sanitized before writing files.
- Parser baselines are auto-generated during fixture capture and stored in
  `tests/fixtures/baselines/`; if baseline generation fails, regression tests skip
  with a clear message until a baseline is available for the latest fixture date.

## Linting, Formatting, and Type Checking

Use the Makefile for standard workflows:

```bash
make lint       # Fix + format + check (Python) + clippy (Rust)
make format     # Format Python code only
make typecheck  # Run pyright
make check      # Full pre-commit verification
```

Before opening a PR, run `make check` to ensure everything passes.

## Pull Request Process

Before submitting:

1. Ensure tests, lint, and type checks pass locally.
2. Keep changes scoped and cohesive.
3. Update docs if behavior, APIs, or developer workflows changed.
4. Prefer clear commit history and descriptive messages.

PR description should include:

- What changed
- Why it changed
- How it was validated
- Any migration or compatibility notes

## Commit Message Style

Use concise, purposeful commit messages. Conventional-style prefixes are preferred,
for example:

- `feat: add batch course lookup helper`
- `fix: handle missing ViewState in partial responses`
- `refactor: move ADF infrastructure into core package`
- `docs: clarify debugging workflow for SIA timeouts`
- `test: add edge cases for prerequisite parser`

## Architecture and Behavior Notes

- `session.py` and `scraper.py` are top-level orchestrators.
- `core/` contains Oracle ADF/session internals.
- `utils/` contains reusable helpers and decorators.
- `parsers/` contains extraction logic and typed models.

SIA uses Oracle ADF, so request ordering/state handling is critical. Review
`docs/QUIRKS.md` and `docs/DEBUGGING.md` when changing session flow.

## Documentation References

- API docs: https://bettercampus.github.io/sia-scraper
- Migration notes: `docs/MIGRATION_v2.md`
- Debugging guide: `docs/DEBUGGING.md`
- Oracle ADF quirks: `docs/QUIRKS.md`

## Questions

If anything is unclear, open an issue or discussion in the repository so context
is visible to maintainers and collaborators.
