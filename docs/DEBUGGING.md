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
    print(scraper.sia_session.status)
    await scraper.set_career("0-2-8-3")
    print(scraper.sia_session.status)


asyncio.run(main())
```

## 2) Wrong course details for a selected index

Cause: stale ADF state (usually ViewState drift).

Checks:

- Verify each course-related POST is going through `post_request()`.
- Confirm no custom code bypasses session methods and sends raw POSTs.

Example anti-pattern:

```python
# Bad: missing await on async API
session.get_course_xml(0)
```

Preferred pattern:

```python
# Good: await async session methods
await session.get_course_xml(0)
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

## 5) Understanding Rust exception types

The scraper raises granular exceptions from the Rust layer. Here's how to interpret them:

### `NetworkError`

**Cause:** DNS resolution failure, connection refused, or network unreachable.

**What to check:**

- Verify SIA server is reachable: `curl -I https://sia.unal.edu.co`
- Check your network connection and firewall rules
- If behind a proxy, ensure proxy settings are configured

```python
from sia_scraper.core.exceptions import NetworkError

try:
    await scraper.create_session()
except NetworkError as exc:
    print(f"Network issue: {exc}")
    # Check connectivity before retrying
```

### `HttpStatusError`

**Cause:** SIA returned an HTTP 4xx or 5xx response.

**What to check:**

- The error message contains the HTTP status code (e.g., "500 Internal Server Error")
- 4xx errors usually indicate invalid requests (check career code format)
- 5xx errors indicate SIA server issues (retry later)

```python
from sia_scraper.core.exceptions import HttpStatusError

try:
    await scraper.set_career("0-2-8-3")
except HttpStatusError as exc:
    status_code = str(exc)
    if "404" in status_code:
        print("Career not found - verify the code")
    elif "500" in status_code:
        print("SIA server error - retry later")
```

### `SiaTimeoutError`

**Cause:** Request exceeded the configured timeout.

**What to check:**

- SIA may be slow during peak hours
- Increase timeout in `SiaScraper.create(timeout=60)`
- Check for network latency issues

### `ParseError`

**Cause:** SIA response could not be parsed (HTML structure changed).

**What to check:**

- SIA may have updated their UI
- Run with `SIA_DEBUG=1` to see raw responses
- Check if the issue affects all courses or specific ones

### `SessionError`

**Cause:** Session not initialized or has expired.

**What to check:**

- Ensure `create_session()` or `init_session()` was called first
- Session may have timed out - recreate it
- The Python wrapper translates this to `SessionNotSet` or `CareerNotSet`

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
