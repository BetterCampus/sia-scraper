# sia-scraper

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://bettercampus.github.io/sia-scraper)

A Python library for extracting course information from Universidad Nacional de Colombia's SIA
(Sistema de Informacion Academica). It uses a Rust-backed async HTTP/session layer and returns
structured, typed course data.

## What is SIA?

SIA is Universidad Nacional de Colombia's academic information system. Its public catalog
contains course metadata such as schedules, groups, prerequisites, and enrollment conditions.

SIA is built on Oracle Application Development Framework (ADF), which requires strict
stateful navigation (ViewState, window/page IDs, event ordering). `sia-scraper` abstracts
that workflow behind an async Python API.

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
python scripts/sync_rust_extension.py --build --release --verify
```

If you update Rust code later, run the sync command again to refresh the local extension binary.

### Minimal Example

```python
import asyncio

from sia_scraper import SiaScraper


async def main() -> None:
    scraper = await SiaScraper.create()
    await scraper.set_career("0-2-8-3")

    course = await scraper.get_course_info(course_code="2016489")
    print(f"{course.course_name} ({course.credits} credits)")

    await scraper.close_session()


asyncio.run(main())
```

### Direct Session API

```python
import asyncio

from sia_scraper import SiaSession


async def main() -> None:
    session = await SiaSession.create()
    await session.set_career("0-2-8-3")
    xml = await session.get_course_xml(0)
    print(len(xml))
    await session.close()


asyncio.run(main())
```

See [docs/MIGRATION_v2.md](docs/MIGRATION_v2.md) for complete migration guidance.

Career codes use the format `{level}-{campus}-{faculty}-{career}`.

## Common Usage

### Course Details and Groups

```python
import asyncio

from sia_scraper import SiaScraper


async def main() -> None:
    scraper = await SiaScraper.create()
    await scraper.set_career("0-2-8-3")

    course = await scraper.get_course_info(course_code="2016489")
    print(course.course_name)
    print(course.typology)
    print(course.available_spots)

    for group in course.groups:
        print(group.group_name, group.teacher, group.spots)
        for sch in group.schedules:
            print(sch.day, sch.start_time, sch.end_time, sch.classroom)

    await scraper.close_session()


asyncio.run(main())
```

### Prerequisites

```python
async def check_prerequisites():
    prereqs = await scraper.get_course_prereqs(course_code="2016489")

    for condition in prereqs.conditions:
        print(condition.type)
        for req in condition.prerequisites:
            print(req.course_code, req.course_name)

asyncio.run(check_prerequisites())
```

### Session Persistence

```python
import asyncio

from sia_scraper import SiaScraper, init_sia_scraper


async def main() -> None:
    scraper = await SiaScraper.create()
    await scraper.set_career("0-2-8-3")
    saved = scraper.get_session_data()
    await scraper.close_session()

    restored = await init_sia_scraper("0-2-8-3", False, session_data=saved)
    course = await restored.get_course_info(course_code="2016489")
    print(course.course_name)
    await restored.close_session()


asyncio.run(main())
```

### Error Handling

Sia-scraper provides a typed exception hierarchy with two independent trees:

**Rust exceptions** (from `sia_scraper_rust`, re-exported via `sia_scraper.core.exceptions`):

```text
Exception
  └── SiaScraperException
        ├── NetworkError       -- DNS, connection refused, unreachable
        ├── HttpStatusError    -- HTTP 4xx/5xx responses
        ├── SiaTimeoutError    -- Request timeout
        ├── ParseError         -- Response cannot be parsed
        └── SessionError       -- Session not initialized or expired
```

**Python exceptions** (from `sia_scraper.core.exceptions`):

```text
Exception
  └── SiaSessionException
        ├── SessionNotSet      -- Operation without active session
        ├── CareerNotSet       -- Course operation without career selected
        ├── TimeoutError       -- Legacy timeout (prefer SiaTimeoutError)
        ├── InvalidStatus      -- Incompatible action for current state
        └── ConcurrentAccessError -- Concurrent access detected
```

```python
from sia_scraper.core.exceptions import (
    SiaSessionException,       # Python session errors
    CareerNotSet,              # Career not set
    SiaScraperException,       # Rust base exception
    NetworkError,              # Connection failures
    HttpStatusError,           # HTTP 4xx/5xx
    SiaTimeoutError,           # Request timeouts
    ParseError,                # Parse failures
    SessionError,              # Session state errors
)

try:
    async with await SiaScraper.create() as scraper:
        await scraper.set_career("0-2-8-3")
        course = await scraper.get_course_info(course_code="2016489")
        print(course.course_name)
except NetworkError:
    print("Connection failed. Check network.")
except HttpStatusError as exc:
    print(f"SIA returned HTTP error: {exc}")
except SiaTimeoutError:
    print("SIA timeout. Retry later.")
except CareerNotSet:
    print("Career not set.")
except SiaScraperException as exc:
    print(f"Rust error: {exc}")
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
  - `lxml~=5.2.0`
  - `cssselect~=1.2.0`
  - `pydantic>=2.0,<3.0`
  - `loguru~=0.7.0`

## Project Structure

```text
src/sia_scraper/
├── scraper.py              # Async facade (Rust-backed session)
├── session.py              # Async Rust-backed session wrapper
├── core/
│   ├── adf_state.py        # ViewState extraction utilities
│   └── exceptions.py       # Exception hierarchy
├── utils/
│   ├── date_formatter.py
│   └── debug.py
├── constants/
└── parsers/                # HTML/XML parsing
```

## Architecture Highlights

### Async-Only API
The public API is async-first and Rust-backed. Network/session workflow is handled by Rust
(`reqwest` + `tokio`) through the `sia_scraper_rust` extension.

### Batch Resilience
The `scrape_courses()` method includes resilient batch processing:
- **SKIP**: Skip rows that fail to parse
- **RETRY**: Retry failed rows up to 3 times with configurable delay
- **ABORT**: Abort on first failure

Configure via `scrape_courses(error_mode="retry")`.

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
pytest tests/fixtures/test_fixtures_validity.py
pytest tests/fixtures/test_contracts.py tests/fixtures/test_regression.py
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, style rules, testing expectations,
and pull request guidelines.

## License

License is currently TBD. A project license file will be added to formalize terms.
