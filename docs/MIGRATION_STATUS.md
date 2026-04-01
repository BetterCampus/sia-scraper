# Migration Status Matrix

This document tracks the Rust migration status for `sia-scraper` and reflects
the async-only API cutover completed in Phase 5.6.

## Overview

| Feature | Python Implementation | Rust Implementation | Status | Notes |
|---------|------------------------|--------------------|--------|-------|
| ViewState extraction | `sia_scraper.core.adf_state` | `sia_scraper_rust::parsers::adf` | ✅ Complete | Rust session flow also syncs ViewState internally |
| Course info parsing | `sia_scraper.parsers.course_parser` | `sia_scraper_rust::parsers::course_parser` | ✅ Complete | Python model validation maintained |
| Prereqs parsing | `sia_scraper.parsers.course_parser` | `sia_scraper_rust::parsers::course_parser` | ✅ Complete | Structured conditions + prereqs |
| Course list extraction | `sia_scraper.parsers.html_parser` | `sia_scraper_rust::parsers::table_parser` | ✅ Complete | Direct Rust path for list extraction |
| HTTP/session transport | `sia_scraper.session` (async wrapper) | `sia_scraper_rust::http::sia_session` | ✅ Complete | Rust-first transport and navigation |
| ADF request construction | N/A (sync module removed) | `sia_scraper_rust::parsers::adf_request` | ✅ Complete | Python sync builder removed in Phase 5.6 |

## API Surface

| API | Status | Notes |
|-----|--------|-------|
| `SiaSession` | ✅ Async primary | Rust-backed async session wrapper |
| `SiaScraper` | ✅ Async primary | Async facade for course workflows |
| `init_sia_scraper()` | ✅ Async primary | Async factory helper |
| `create_career_session()` | ✅ Async primary | Async factory helper |
| Sync session/scraper API | ❌ Removed | Removed in Phase 5.6 |

## Phase 5.6 Cutover Summary

Completed:
- Removed sync Python orchestration modules and decorators.
- Promoted async class names to primary API names.
- Removed sync-only dependencies (`requests`, `tenacity`).
- Updated tests to async-first suite.
- Updated scripts and docs for async-only usage.

Deferred:
- PyPI publishing workflow.

## Testing and Quality

Primary verification gates:
- `ruff check .`
- `pyright`
- `pytest`
- `cargo clippy`
- `cargo test --lib --no-default-features`

## Historical Reference

Removed sync modules and their responsibilities are documented in:

- `docs/SYNC_API_REFERENCE.md`
