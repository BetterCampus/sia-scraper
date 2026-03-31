# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **HTTP Resilience with tenacity**: Automatic retry logic for network failures
  - 3 retry attempts with exponential backoff (2s → 4s → 8s, max 10s)
  - Retries on: `Timeout`, `ReadTimeout`, `ConnectionError`
  - Applied to: `post_request()`, `get_request()`
  - Final failure converts to `SiaSessionException.TimeoutError`
- **Production Logging with loguru**: Structured logging with rotation and retention
  - Log files: `logs/sia_scraper_YYYY-MM-DD.log` (10 MB rotation, 7-day retention)
  - Error logs: `logs/sia_scraper_errors_YYYY-MM-DD.log` (14-day retention)
  - Console output when `SIA_DEBUG=1`
  - New logging functions: `debug_log()`, `info_log()`, `error_log()`
- **lxml 5.x**: Upgraded from lxml 4.9 to 5.2 for improved parsing performance
- **Rust migration completed for parser/request internals**:
  - `get_course_list()` now runs in Rust (direct call path)
  - `get_plain_text()` now runs in Rust (direct call path)
  - `OracleAdfRequestBuilder` now delegates request/event payload generation to Rust
- **Fuzz testing scaffold for Rust parsers**:
  - Added `cargo-fuzz` crate at `fuzz/`
  - Added targets: `fuzz_get_course_list`, `fuzz_get_plain_text`, `fuzz_extract_view_state`
- **Context Manager Support**: `SiaScraper` and `SiaSession` now support `with` statement
- **Session Component Split**: Refactored into isolated components
  - `AdfStateManager`: ViewState synchronization and lifecycle
  - `NavigationController`: ADF workflow orchestration
  - `AdfContext`: Value object for request context
- **Batch Resilience**: `scrape_courses()` supports SKIP/RETRY/ABORT modes

### Refactored

- **Smart Models, Dumb Parser**: Moved data cleaning and transformation logic from `course_parser.py` into Pydantic model validators
  - `Schedule`: Added `classroom` cleaning validator
  - `Group`: Added validators for `group_name`, `teacher`, `faculty`, `duration`, `schedule_type`
  - `CourseInfo`: Added validators for `course_name` and `typology`
  - `CoursePrereqs`: Added code extraction from course_name and typology cleaning
  - Parser now passes raw values, models handle all cleaning/defaults
  - Single Responsibility: Parser extracts HTML, models validate and transform
- **Malformed-row compatibility in Rust course list parser**:
  - Added fallback path to handle edge-case HTML where `<span>` nodes appear directly under `<tr>`
  - Maintains parity with existing Python/XPath behavior for legacy test fixtures

### Performance

- Updated benchmark snapshot (`benchmarks/benchmark_rust_vs_python.py`) shows:
  - `get_plain_text`: ~1.37x faster in Rust baseline
  - `get_course_list`: ~1.62x faster in Rust baseline

## [1.0.0] - 2026-03-30

### Added

- **Pydantic Models**: All data models now use Pydantic BaseModel for runtime validation
  - Models: `Schedule`, `Group`, `CourseInfo`, `Prerequisite`, `PrereqCondition`, `CoursePrereqs`, `SessionState`
  - Immutability: All models are frozen (cannot be modified after creation)
  - Validation: Automatic validation of all fields with clear error messages
- **SessionState Model**: New model for session serialization/deserialization
- **Migration Guide**: Added `docs/MIGRATION_v1.0.md` with detailed upgrade instructions

### Changed

- **Model Instantiation**: All model constructors now require keyword arguments
- **Session Data**: `get_session_data()` returns `SessionState` object instead of dict
- **Dict Access**: Models no longer support dict-style access (`model["key"]`); use attribute access

### Fixed

- **Course code extraction**: Use regex to extract course code from rightmost parentheses in course names with multiple parenthetical expressions (e.g., "ELECTROMAGNETISMO (AVANZADO) (2016489)")
- **Course code misalignment**: Fixed critical bug in `scrape_courses()` where sorting indices without sorting corresponding codes caused mismatched assignments
- **Session resource leak**: Added explicit session cleanup in `init_sia_scraper()` when falling back to a new session

### Refactored

- **PEP 8 compliance**: Replaced double underscore (`__`) private attributes with single underscore (`_`) throughout `scraper.py` and `session.py` to follow Python naming conventions and improve testability
- Removed unnecessary `type: ignore[attr-defined]` comments in tests now that name mangling is no longer used
