# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Concurrent Session State Safety (Issue #94)**: Generation-based race condition prevention
  - Added `generation: u64` counter to `SessionState` and `SessionStateModel`
  - Generation increments on each `update_state()` call
  - `scrape_courses()` now checks generation before updating session state
  - Stale state updates are skipped with debug-level logging when generation mismatch detected
  - Prevents concurrent `scrape_courses()` calls from overwriting each other's state changes
  - Comprehensive test suite covering generation field, edge cases, and concurrency scenarios

- **Typed Error Hierarchy (Phase 8)**: Complete Rust-to-Python exception mapping
  - 5 granular Rust exception types: `NetworkError`, `HttpStatusError`, `SiaTimeoutError`, `ParseError`, `SessionError`
  - All inherit from `SiaScraperException` base class
  - HTTP-facing Rust endpoints map `HttpError` variants to specific Python exceptions
  - Python `SiaSession` wrapper translates Rust exceptions to Python-native exceptions
  - Comprehensive test suite (32 tests) covering exception raising, inheritance, and translation
  - Zero-Panic Policy: No `.unwrap()` or `.expect()` in production Rust code

### Changed

- **Breaking change in batch progress callback behavior**:
  - `SiaScraper.scrape_courses(...)` now calls `progress_callback` exactly once after the full batch completes.
  - Incremental per-course callback updates during scraping are no longer emitted.
  - **Migration**: If you rely on per-item progress logic, iterate through the
    returned `ScrapeResult.successes` and `ScrapeResult.failures` after the
    batch call completes in skip/retry modes. In abort mode, `scrape_courses(...)`
    returns `list[CourseInfoModel]` directly.

- **Session Serialization Breaking Change**: Standardized course list entry format (Issue #54)
  - **BREAKING**: `get_course_list()` now returns `[{"code": "1000001", "name": "Calculo"}]` instead of `[{"1000001": "Calculo"}]`
    - Old format: `[{"1000001": "Calculo I"}, {"1000002": "Algebra"}]` (single-key dict per course)
    - New format: `[{"code": "1000001", "name": "Calculo I"}, {"code": "1000002", "name": "Algebra"}]` (explicit keys)
  - **BREAKING**: `CourseListEntryModel` fields renamed:
    - `course_code` → `code`
    - `course_name` → `name`
  - **Backward compatibility**:
    - Deserialization supports all legacy formats with deprecation warnings:
      1. Single-key dict: `{"1000001": "Calculo"}` (emits `DeprecationWarning`)
      2. Legacy named keys: `{"course_code": "...", "course_name": "..."}` (emits `DeprecationWarning`)
      3. Current format: `{"code": "...", "name": "..."}` (no warning)
    - Legacy support will be removed in version 4.0.0
  - **Migration for integrators**:
    - **If consuming `get_course_list()` output**: Update code to access `course["code"]` and `course["name"]` instead of extracting the single key/value
    - **If creating `CourseListEntryModel` instances**: Use `code=` and `name=` kwargs instead of `course_code=` and `course_name=`
    - **If loading saved sessions**: No action needed - backward deserialization is automatic (with deprecation warnings)
  - **New features**:
    - `CourseListEntryModel.to_dict()` method serializes to `{"code": ..., "name": ...}`
    - `CourseListEntryModel.from_dict()` classmethod deserializes from dict (supports all formats)
    - `SessionStateModel` pickle support with automatic legacy format migration

- **Async HTTP Client (Rust reqwest + tokio)**: Phase 4 complete - async HTTP transport layer
  - New async `SiaSession` class for session management
  - Connection pooling enabled by default
  - Automatic ViewState synchronization after each request
  - SIA-optimized retry with exponential backoff and jitter
  - TLS: rustls with dual backend (native-certs + webpki-roots)
- **Session persistence via Rust**: Implemented proper session save/restore
  - `PySiaSession.get_session_data()` returns complete session state (headers, cookies, ViewState, career info, course list)
  - `PySiaSession.reset()` clears Rust session for clean re-initialization
  - `PySiaSession.from_state()` class method restores session from saved state
  - `SiaSession.from_state()` Python wrapper for session restoration
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

---

## [3.0.0-alpha.1] - 2026-04-02

### Phase 6 Complete: Rust PyClass Models

This alpha release marks the completion of Phase 6 of the Rust migration plan, introducing Rust PyClass models as the primary data interchange format.

### Breaking Changes

- **Pydantic models deprecated**: All Pydantic models in `sia_scraper.models` are now deprecated in favor of Rust `#[pyclass]` models
  - `sia_scraper.models.course.CourseInfoTyped` → use `sia_scraper_rust.CourseInfoModel`
  - `sia_scraper.models.course.GroupTyped` → use `sia_scraper_rust.GroupModel`
  - `sia_scraper.models.course.ScheduleTyped` → use `sia_scraper_rust.ScheduleModel`
  - `sia_scraper.models.prerequisite.PrereqConditionTyped` → use `sia_scraper_rust.PrereqConditionModel`
  - `sia_scraper.models.prerequisite.CoursePrereqsTyped` → use `sia_scraper_rust.CoursePrereqsModel`
  - `sia_scraper.models.session.SessionStateTyped` → use `sia_scraper_rust.SessionStateModel`
  - `sia_scraper.models.session.CourseListEntryTyped` → use `sia_scraper_rust.CourseListEntryModel`
- **Return types changed**: Parser functions now return Rust PyClass models directly instead of Pydantic models
- **Pickle support**: `SessionStateModel` implements `__getstate__`/`__setstate__` for pickle serialization

### Added

- **Rust PyClass models** (8 models):
  - `ScheduleModel` with `__repr__`, `__str__`, pickle support
  - `GroupModel` with `__repr__`, `__str__`, pickle support  
  - `CourseInfoModel` with `__repr__`, `__str__`, mutable `code` field, pickle support
  - `PrerequisiteModel` with `__repr__`, `__str__`, pickle support
  - `PrereqConditionModel` with `__repr__`, `__str__`, pickle support
  - `CoursePrereqsModel` with `__repr__`, `__str__`, pickle support
  - `CourseListEntryModel` with `__repr__`, `__str__`, pickle support
  - `SessionStateModel` with `__repr__`, `__str__`, `is_ready()`, pickle support
- **Type stubs**: Complete `sia_scraper_rust.pyi` with all model definitions and method signatures
- **Model integration tests**: Comprehensive test coverage for Rust models including:
  - Creation with positional and keyword arguments
  - `__repr__` and `__str__` output verification
  - Nested model traversal (groups → schedules, conditions → prerequisites)
  - Pickle serialization/deserialization roundtrips
  - Edge cases (None values, empty lists, special characters, large numbers)

### Performance

- **Direct Rust model return path**: Rust structs exposed directly to Python via `#[pyclass]`, reducing FFI overhead

### Phase 7 Complete: Unified HTTP + Parse Pipeline

- **Zero-copy scraping**: `scrape_course_info()` and `scrape_course_prereqs()` perform HTTP fetch + parsing entirely in Rust
- **No XML crossing FFI**: Raw HTML/XML never copied to Python heap - stays in Rust throughout
- **Unified pipeline**: Single async call for complete HTTP+parse workflow (was fetch→parse before)
- **Session persistence**: Full save/restore via `get_session_data()` and `from_state()`
- **Integration tests**: Added `tests/integration/test_phase7_workflow.py` with real SIA server tests
- **Phase 7 benchmark**: Added `benchmarks/benchmark_phase7.py` documenting unified pipeline performance

### Deprecated

- `sia_scraper.models` module - will be removed in v3.1.0 final release
- Use `sia_scraper_rust` for all model needs

### Code Quality

- `cargo clippy`: Zero warnings
- `ruff check && ruff format`: Clean
- `pyright`: Zero errors
- Python test coverage: Maintained at >90%

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
