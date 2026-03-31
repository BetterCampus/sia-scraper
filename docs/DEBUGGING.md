# Debugging Guide

This guide explains how to debug common runtime issues when scraping SIA.

## Enable debug logging

Set `SIA_DEBUG=1` before running your script:

```bash
export SIA_DEBUG=1
python your_script.py
```

When enabled, the scraper logs Oracle ADF state transitions and selected request
metadata through the project logger.

## Recommended logger setup

```python
import logging

logging.basicConfig(level=logging.DEBUG)
```

If logging is not configured, debug messages may not be visible even with
`SIA_DEBUG=1`.

## What to inspect first

1. Session status transitions
2. ViewState evolution across POST requests
3. Dropdown action order for career selection
4. Course list size before row selection
5. DELTAS payload for selected row

## Dependency issues

### `ImportError: cssselect does not seem to be installed`

Cause: `lxml.cssselect` requires the separate `cssselect` package.

Checks:

- Confirm `cssselect` is installed in the active environment.
- Reinstall project dependencies after pulling latest changes.

Fix:

```bash
pip install -e ".[dev]"
```

If you only need the runtime dependency:

```bash
pip install cssselect~=1.2.0
```

## Common issues and checks

## 1) `InvalidStatus` exceptions

Cause: calling an action from the wrong state.

Checks:

- Confirm current status before operation.
- Ensure workflow order is respected: create session -> set career -> get course info.

Example:

```python
import asyncio

from sia_scraper import SiaScraper


async def main() -> None:
    scraper = SiaScraper(init_session=False)
    await scraper.create_session()
    print(scraper.sia_session.STATUS)
    await scraper.set_career("0-2-8-3")
    print(scraper.sia_session.STATUS)


asyncio.run(main())
```

## 2) Wrong course details for a selected index

Cause: stale ADF state (usually ViewState drift).

Checks:

- Verify each course-related POST is going through `post_request()`.
- Confirm no custom code bypasses session methods and sends raw POSTs.

Example anti-pattern:

```python
# Bad: bypasses state sync logic
session._SiaSession__session.post(session_url, data=payload)
```

Preferred pattern:

```python
# Good: keeps ViewState synchronized
session.post_request(payload)
```

## 3) `ValueError` in course parsing

Cause: live SIA payload differences for a specific row.

Checks:

- Retry another nearby course index.
- Validate page content contains expected `detass-creditos` and course title elements.

Example fallback pattern:

```python
import asyncio


async def main() -> None:
    course_info = None
    for idx in range(min(5, len(scraper.course_list))):
        try:
            course_info = await scraper.get_course_info(course_index=idx)
            break
        except ValueError:
            continue


asyncio.run(main())
```

## 4) Career loads but course list is empty

Cause: incomplete ADF action chain or changed component behavior.

Checks:

- Verify action sequence in `set_career()` completes.
- Confirm `search_code` format is `level-campus-faculty-career`.
- Test another known career code.

## Debug command checklist

Run these checks locally after changes:

```bash
pytest
ruff check --fix . && ruff format . && ruff check .
pyright
```

## Useful files for troubleshooting

- `src/sia_scraper/session.py`
- `src/sia_scraper/scraper.py`
- `src/sia_scraper/core/adf_state.py`
- `src/sia_scraper/core/exceptions.py`
- `src/sia_scraper/parsers/course_parser.py`
- `docs/SYNC_API_REFERENCE.md` (historical sync implementation reference)

## Project structure (v2.0+)

```text
src/sia_scraper/
├── scraper.py
├── session.py
├── core/
│   ├── adf_state.py
│   └── exceptions.py
├── utils/
│   ├── date_formatter.py
│   └── debug.py
├── constants/
└── parsers/
```
