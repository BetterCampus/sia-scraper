# Migration Guide: v1.x -> v2.0 (Async API)

## Overview

Version `2.0` introduces a fully async API for session and scraping operations.
The transport layer is now Rust-first (`reqwest` + `tokio`) and Python-facing
methods use `async def`.

This guide focuses on practical migration steps with concise examples.

## Breaking Changes

### 1) Strict parsing for course and prerequisite data

All parsing endpoints now enforce strict validation. Previously, malformed groups and prerequisite conditions were silently skipped.

**Behavioral changes:**
- Empty group panels now cause parse errors instead of being skipped
- Prerequisite conditions with insufficient headers now fail parsing
- Malformed group data is no longer silently ignored

**Impact:**
- If your SIA HTML responses contain malformed data, parsing will now fail with descriptive errors
- This catches data quality issues early rather than producing incomplete results
- No code changes needed, but be prepared to handle parsing errors

**Rationale:**
- Ensures data completeness and consistency
- Prevents silent data loss from malformed HTML
- Aligns with typed JSON endpoint expectations

### 2) Session and scraper workflows are async

Most public operations that touch SIA now return awaitables.

Before (`v1.x`):

```python
from sia_scraper import SiaScraper

scraper = SiaScraper(init_session=False)
scraper.create_session()
scraper.set_career("0-2-8-3")
course = scraper.get_course_info(course_index=0)
print(course)
```

After (`v2.0`):

```python
import asyncio

from sia_scraper import SiaScraper


async def main() -> None:
    scraper = await SiaScraper.create()
    await scraper.set_career("0-2-8-3")
    history = await scraper.get_course_info(course_index=0)
    print(history)


if __name__ == "__main__":
    asyncio.run(main())
```

### 3) Rust-first HTTP stack (no Python fallback)

The `requests` transport fallback is removed. HTTP/session behavior is handled by
Rust code exposed through PyO3 bindings.

### 4) Python version and runtime expectations

- Python `3.10+` remains required.
- Async-aware execution context is required (`asyncio.run`, framework event loop,
  or notebook-aware loop usage).

## Migration Steps

### Step 1: Upgrade dependencies

```bash
pip install -e ".[dev]"
```

If you install from wheel in CI or deployment:

```bash
pip install target/wheels/sia_scraper-*.whl --force-reinstall
```

### Step 2: Convert call sites to async/await

Wrap top-level scripts in `asyncio.run(...)` and add `await` for session/scraper
methods.

Before:

```python
def run() -> None:
    scraper = SiaScraper(init_session=False)
    scraper.create_session()
    scraper.set_career("0-2-8-3")
    data = scraper.get_course_info(course_index=0)
    print(data)


run()
```

After:

```python
import asyncio


async def run() -> None:
    scraper = await SiaScraper.create()
    await scraper.set_career("0-2-8-3")
    data = await scraper.get_course_info(course_index=0)
    print(data)


asyncio.run(run())
```

### Step 3: Update tests for async behavior

Use `pytest.mark.asyncio` for test functions calling async methods.

```python
import pytest


@pytest.mark.asyncio
async def test_get_course_info_returns_data() -> None:
    scraper = await SiaScraper.create()
    await scraper.set_career("0-2-8-3")
    data = await scraper.get_course_info(course_index=0)
    assert data is not None
```

### Step 4: Validate and benchmark

Run the standard quality gates:

```bash
ruff check .
pyright
cargo clippy --manifest-path Cargo.toml
pytest
```

For performance checks:

```bash
python benchmarks/benchmark_rust_vs_python.py
```

## Common Migration Patterns

### Pattern A: Batch scraping concurrently

Before (`v1.x`, sequential):

```python
results = []
for creds in users:
    scraper = SiaScraper(init_session=False)
    scraper.create_session()
    scraper.set_career("0-2-8-3")
    results.append(scraper.get_course_info(course_index=0))
```

After (`v2.0`, concurrent):

```python
import asyncio


async def scrape_one(creds: dict[str, str]):
    scraper = await SiaScraper.create()
    await scraper.set_career("0-2-8-3")
    return await scraper.get_course_info(course_index=0)


async def scrape_many(users: list[dict[str, str]]):
    tasks = [scrape_one(creds) for creds in users]
    return await asyncio.gather(*tasks)
```

### Pattern B: Framework integration

If you are already in an async framework (FastAPI/Quart/etc.), do not call
`asyncio.run(...)` inside handlers. Call `await` directly.

## Troubleshooting

### `RuntimeError: asyncio.run() cannot be called from a running event loop`

You are already inside an active loop (often notebooks or async frameworks).
Use `await` directly instead of `asyncio.run(...)`.

### `TypeError` from missing `await`

If a method now returns a coroutine, calling it without `await` will fail.
Update the call site and containing function to async.

### Build/install issues around Rust extension

Use project-standard build commands:

```bash
maturin build --release
pip install target/wheels/sia_scraper-*.whl --force-reinstall
```

## Compatibility and Rollout Guidance

- Prefer migrating entry points first (CLI/script/jobs).
- Migrate tests next (`pytest.mark.asyncio`).
- Migrate service/framework handlers last.
- Keep rollout incremental by module to reduce risk.

## Quick Checklist

- [ ] Convert synchronous scraper/session calls to `await`
- [ ] Add `asyncio.run(...)` in synchronous entry scripts
- [ ] Add/update async pytest tests
- [ ] Run `ruff`, `pyright`, `clippy`, and `pytest`
- [ ] Run benchmark comparison and capture baseline

## API Naming Note

During Phase 5.6, async classes and factories were promoted to primary names:

- `SiaSessionAsync` -> `SiaSession`
- `SiaScraperAsync` -> `SiaScraper`
- `init_sia_scraper_async()` -> `init_sia_scraper()`
- `create_career_session_async()` -> `create_career_session()`

All examples in this guide use the current primary names.

## Additional Resources

- Python asyncio docs: <https://docs.python.org/3/library/asyncio.html>
- PyO3 guide: <https://pyo3.rs/>
- Maturin docs: <https://www.maturin.rs/>
