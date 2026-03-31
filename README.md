# sia-scraper

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://bettercampus.github.io/sia-scraper)

A Python library for extracting course information from Universidad Nacional de Colombia's SIA
(Sistema de Informacion Academica). It handles Oracle ADF session/state complexity so you can
work with structured, typed course data.

## What is SIA?

SIA is Universidad Nacional de Colombia's academic information system. Its public catalog
contains course metadata such as schedules, groups, prerequisites, and enrollment conditions.

SIA is built on Oracle Application Development Framework (ADF), which requires strict
stateful navigation (ViewState, window/page IDs, event ordering). `sia-scraper` abstracts
that workflow behind a clean Python API.

## Important Notice

This project depends on Oracle ADF component behavior that may change without notice.

- UI/component ID changes in SIA can break request flows.
- Action order must stay exact for dependent dropdown interactions.
- ViewState must be synchronized after each POST request.

For deeper details, see [Oracle ADF Quirks](docs/QUIRKS.md).

## Quick Start

### Installation

Install directly from GitHub:

```bash
pip install git+https://github.com/BetterCampus/sia-scraper.git
```

For local development:

```bash
git clone https://github.com/BetterCampus/sia-scraper.git
cd sia-scraper
pip install -e ".[dev]"
```

### Minimal Example

```python
from sia_scraper import SiaScraper

scraper = SiaScraper()
scraper.set_career("0-2-8-3")

course = scraper.get_course_info(course_code="2016489")
print(f"{course.course_name} ({course.credits} credits)")

scraper.close_session()
```

Career codes use the format `{level}-{campus}-{faculty}-{career}`.

## Common Usage

### Course Details and Groups

```python
from sia_scraper import SiaScraper

scraper = SiaScraper()
scraper.set_career("0-2-8-3")

course = scraper.get_course_info(course_code="2016489")
print(course.course_name)
print(course.typology)
print(course.available_spots)

for group in course.groups:
    print(group.group_name, group.teacher, group.spots)
    for sch in group.schedules:
        print(sch.day, sch.start_time, sch.end_time, sch.classroom)

scraper.close_session()
```

### Prerequisites

```python
prereqs = scraper.get_course_prereqs(course_code="2016489")

for condition in prereqs.conditions:
    print(condition.condition_type)
    for req in condition.prerequisites:
        print(req.code, req.name)
```

### Session Persistence

```python
from sia_scraper import SiaScraper

scraper = SiaScraper()
scraper.set_career("0-2-8-3")
saved = scraper.get_session_data()
scraper.close_session()

scraper = SiaScraper(session_data=saved)
course = scraper.get_course_info(course_code="2016489")
print(course.course_name)
scraper.close_session()
```

### Error Handling

```python
from sia_scraper import SiaScraper, SiaSessionException

scraper = SiaScraper()
try:
    scraper.set_career("0-2-8-3")
    course = scraper.get_course_info(course_code="2016489")
    print(course.course_name)
except SiaSessionException.TimeoutError:
    print("SIA timeout. Retry later.")
except SiaSessionException.CareerNotSet:
    print("Career not set.")
finally:
    scraper.close_session()
```

## Documentation

- API reference: https://bettercampus.github.io/sia-scraper
- Migration guide: [docs/MIGRATION_v2.md](docs/MIGRATION_v2.md)
- Debugging guide: [docs/DEBUGGING.md](docs/DEBUGGING.md)
- Oracle ADF quirks: [docs/QUIRKS.md](docs/QUIRKS.md)

Current version: `0.2.1`.

## Requirements

- Python `>=3.10`
- Runtime dependencies:
  - `requests~=2.32.3`
  - `lxml~=4.9.2`
  - `cssselect~=1.2.0`

## Project Structure

```text
src/sia_scraper/
├── scraper.py              # Main facade with context manager support
├── session.py             # Session management with context manager support
├── core/
│   ├── adf_state.py       # ViewState extraction utilities
│   ├── adf_state_manager.py  # Extracted ADF state manager component
│   ├── enhanced_session.py   # HTTP session wrapper
│   ├── exceptions.py      # Exception hierarchy
│   ├── navigation_controller.py  # Workflow navigation
│   └── oracle_adf_request.py  # Request builder (Rust-backed)
├── utils/
│   ├── date_formatter.py
│   ├── decorators.py
│   └── debug.py
├── constants/
└── parsers/               # HTML/XML parsing (Rust-backed)
```

## Architecture Highlights

### Session Component Split
The session layer has been refactored into isolated components for better maintainability:
- **AdfStateManager**: Handles ViewState synchronization and lifecycle
- **NavigationController**: Orchestrates ADF workflow navigation
- **AdfContext**: Value object carrying request context (ViewState, window IDs, event)

### Batch Resilience
The `scrape_courses()` method includes resilient batch processing:
- **SKIP**: Skip rows that fail to parse
- **RETRY**: Retry failed rows up to 3 times with exponential backoff
- **ABORT**: Abort on first failure (default behavior preserved)

Configure via `scrape_courses(mode="retry")` or `scrape_courses(max_retries=5)`.

## Testing and Quality Checks

```bash
pytest
ruff check .
pyright
cargo clippy --manifest-path Cargo.toml
```

### Rust Fuzzing (Optional)

This repository includes `cargo-fuzz` targets for core Rust parsers:

- `fuzz_get_course_list`
- `fuzz_get_plain_text`
- `fuzz_extract_view_state`

Run them with:

```bash
cargo install cargo-fuzz
cargo fuzz run --manifest-path fuzz/Cargo.toml fuzz_get_course_list
cargo fuzz run --manifest-path fuzz/Cargo.toml fuzz_get_plain_text
cargo fuzz run --manifest-path fuzz/Cargo.toml fuzz_extract_view_state
```

Useful variants:

```bash
pytest --cov=src/sia_scraper
pytest tests/utils/test_date_formatter.py
pytest -m "not integration"
pytest -m "not integration and not network"
pytest tests/fixtures/test_fixtures_validity.py
pytest tests/fixtures/test_contracts.py tests/fixtures/test_regression.py
```

### CI behavior for live tests

- The default CI workflow (`.github/workflows/test.yml`) skips live SIA tests using:
  - `pytest -m "not integration and not network"`
- This keeps pull request checks deterministic and avoids failures caused by temporary
  SIA outages or Oracle ADF response changes.
- Live SIA tests run separately in `.github/workflows/integration-live.yml`
  (manual trigger and nightly schedule).

Run live integration tests locally with:

```bash
pytest -m "integration and network" -v
```

Captured fixture snapshots used by these tests live in `tests/fixtures/` and are refreshed
with `python scripts/capture_sia_fixtures.py`.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, style rules, testing expectations,
and pull request guidelines.

## License

License is currently TBD. A project license file will be added to formalize terms.
