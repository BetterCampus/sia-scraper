# Scripts

This directory contains development and maintenance scripts for the project.

## Development Scripts

| Script | Description |
|--------|-------------|
| `lint-python.sh` | Run ruff check --fix, format, and verify |
| `lint-rust.sh` | Run cargo clippy with all features and warnings as errors |
| `test-python.sh` | Run Python tests (excludes integration/network) |
| `test-python-cov.sh` | Run Python tests with coverage reports |
| `test-rust.sh` | Run Rust library tests |
| `check.sh` | Full pre-commit check (stops on first failure) |
| `check-python.sh` | Run all Python checks, report all failures |
| `check-rust.sh` | Run all Rust checks, report all failures |

Most scripts accept additional arguments via `$@` for flexibility.

## Makefile Integration

These scripts are invoked by the project Makefile. For most development workflows,
use `make` targets directly:

```bash
make lint          # Runs lint-python.sh + lint-rust.sh
make check         # Runs check.sh
make check-python  # Runs check-python.sh
make check-rust    # Runs check-rust.sh
```

Run `make help` to see all available targets.

## Maintenance Scripts

### Fixture Capture

Capture real SIA responses for regression tests:

```bash
PYTHONPATH=src python3 scripts/capture_sia_fixtures.py
```

The script reads `scripts/capture_config.yaml` and writes fixtures under:

- `tests/fixtures/html/`
- `tests/fixtures/xml/`
- `tests/fixtures/json/`

Behavior configured for this project:

- Captures CS career (`0-2-8-3`)
- Captures 5 regular courses
- Captures 2 electives
- Captures timeout error fixture
- Sanitizes tokens/cookies
- Keeps only latest fixture set for each logical file

### Rust Extension Sync

Build and sync the Rust extension into the editable src tree:

```bash
python scripts/sync_rust_extension.py --build --release --verify
```

This script keeps local editable installs stable by placing the compiled extension
at `src/sia_scraper_rust/sia_scraper_rust<EXT_SUFFIX>`, so `pytest` and regular
imports work without `PYTHONPATH` hacks. The Makefile handles this automatically
via `make develop`.

### Constants Sync Check

Verify Python and Rust constants are synchronized:

```bash
python scripts/check_constants_sync.py --verbose
```