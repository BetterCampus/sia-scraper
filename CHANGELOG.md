# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Breaking Changes

- **Async-only API**: Removed sync Python API entirely; Rust-backed async is now the sole interface
- **Session status property**: Renamed `SiaSession.STATUS` to `SiaSession.status`
- **Session state serialization**: Renamed `SessionState.STATUS` field to `SessionState.status`
- **Electives parameter**: Renamed `electives` parameter to `is_electives` in `set_career()` (Python + Rust bindings)
- Removed sync modules: `adf_context`, `adf_state_manager`, `enhanced_session`, `navigation_controller`, `oracle_adf_request`, `decorators`
- Removed Python dependencies: `requests`, `tenacity`
- **Strict parsing for all endpoints**: Both legacy dict endpoints (`parse_course_info`, `parse_prereqs`) and typed JSON endpoints (`parse_course_info_json`, `parse_prereqs_json`) now enforce strict validation. Malformed groups, empty panels, and invalid prerequisite conditions that were previously skipped now cause parsing errors. This ensures data quality and early error detection at the cost of backward compatibility.

### Added

- **Async HTTP Client (Rust reqwest + tokio)**: Phase 4 complete - async HTTP transport layer
  - New async `SiaSession` class for session management
  - Connection pooling enabled by default
  - Automatic ViewState synchronization after each request
  - SIA-optimized retry with exponential backoff and jitter
  - TLS: rustls with dual backend (native-certs + webpki-roots)
- **pytest-asyncio**: Async test infrastructure added
  - Async session tests consolidated in `tests/test_session.py`
  - All tests passing
- **HTTP Benchmarks**: `benchmarks/benchmark_http_async.py`
  - Session creation: ~240ms (p50), ~272ms (p95)
  - Set career: ~213ms (p50), ~287ms (p95)
  - Concurrent sessions: 35+ sessions/second
  - No baseline comparison (sync API metrics not collected)
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
- **Context Manager Support**: `SiaScraper` and `SiaSession` support `async with`
- **Batch Resilience**: `scrape_courses()` supports SKIP/RETRY/ABORT modes
- **Async scraper facade (Phase 4.7)**:
  - Async `SiaScraper` in `src/sia_scraper/scraper.py`
  - Async factory helpers: `init_sia_scraper()` and `create_career_session()`
  - Async scraper unit tests in `tests/test_scraper.py`
  - `sia_scraper.__init__` exports async API as the primary interface
- **Rust quality CI workflow**:
  - Added `.github/workflows/rust.yml`
  - Runs `cargo clippy` and `cargo test --lib --no-default-features`
  - Added `rust-toolchain.toml` for consistent Rust toolchain pinning
- **Cross-platform wheel CI builds**:
  - Added `.github/workflows/build-wheels.yml`
  - Builds maturin wheels for Linux/macOS/Windows and produces sdist artifacts
  - Includes wheel smoke-import verification job
- **Fuzz smoke CI workflow**:
  - Added `.github/workflows/fuzz.yml`
  - Runs short `cargo fuzz` smoke executions on schedule and manual dispatch

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
- **Rust-backed async career navigation + XML retrieval**:
  - Implemented Rust-side `set_career` workflow returning course list + updated ViewState data
  - Implemented Rust-side `get_course_xml` retrieval workflow
  - Updated Python async wrapper integration to use Rust results and electives input
- **Async session test stabilization**:
  - Reworked `tests/test_session.py` to avoid live-network dependence
  - Converted to deterministic mocked unit tests for CI reliability
- **Async-only API cutover (Phase 5.6)**:
  - Removed sync Python session/scraper implementations and sync helper modules
  - Promoted Rust-backed async classes to primary API names (`SiaSession`, `SiaScraper`)
  - Updated tests and tooling to async-first workflow

### Removed

- Sync Python infrastructure modules:
  - `src/sia_scraper/core/adf_context.py`
  - `src/sia_scraper/core/adf_state_manager.py`
  - `src/sia_scraper/core/enhanced_session.py`
  - `src/sia_scraper/core/navigation_controller.py`
  - `src/sia_scraper/core/oracle_adf_request.py`
  - `src/sia_scraper/utils/decorators.py`
- Legacy sync entry modules:
  - `src/sia_scraper/session_async.py` (merged into `src/sia_scraper/session.py`)
  - `src/sia_scraper/scraper_async.py` (merged into `src/sia_scraper/scraper.py`)
- Sync-only runtime dependencies:
  - `requests`
  - `tenacity`
- **Typed prerequisite condition fields (breaking)**:
  - `PrereqCondition.condition`: `str` -> `int`
  - `PrereqCondition.type`: `str` -> `PrereqType` enum (`M`, `O`, `E`, `A`, `UNKNOWN`)
  - `PrereqCondition.all_required`: `str` -> `bool`
  - `PrereqCondition.number_of_courses`: `str` -> `int`
  - Added model validators that normalize bracketed values (e.g., `[N]`, `[1]`) into typed fields
  - Added robust Rust extraction support for both nested and sibling prerequisite header value layouts

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
