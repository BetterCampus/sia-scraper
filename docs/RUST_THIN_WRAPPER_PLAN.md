# Ultimate Rust Migration Plan: Python as Thin Wrapper

**Version:** 3.0 Migration Roadmap  
**Target:** Complete Rust ownership of computation with Python as friendly async interface  
**Status:** Ready for execution  
**Created:** 2026-04-01  
**Python Version:** 3.10+

---

## Executive Summary

This plan completes the transformation of `sia-scraper` into a **Rust-first library with a Python skin**. Building on the excellent foundation already in place (Phases 0-5 complete: parsing, HTTP, async support), this plan eliminates the remaining Python computational overhead.

### Current State (After Phase 5)

✅ **Complete:**
- HTML/XML parsing in Rust (2-5x faster than Python)
- Oracle ADF request building in Rust
- Async HTTP with `reqwest` + `tokio`
- Basic `SiaSession` async integration
- CI/CD with wheels for all platforms

⚠️ **Remaining Bottlenecks:**
- **String copying:** 2-3MB HTML passed Python → Rust → Python
- **GIL contention:** Python orchestrates each HTTP request
- **Duplicate models:** Pydantic validation on Rust-parsed data
- **Python loops:** Retry logic, batch scraping in Python
- **No concurrency:** Session doesn't support parallel course scraping

### Target State (v3.0)

🎯 **Goals:**
- **Zero-copy data:** Rust structs exposed directly to Python via `#[pyclass]`
- **Rust orchestration:** HTTP + parse in single Rust call, no string crossing FFI
- **Parallel scraping:** Tokio enables concurrent course scraping
- **Typed errors:** NetworkError, ParseError, ValidationError from Rust
- **Session persistence:** Pickle support for session state
- **Python < 1000 lines:** Down from ~3000 (70% reduction)

### Performance Targets

| Operation | Current (v2.x) | Target (v3.0) | Gain |
|-----------|---------------|---------------|------|
| Parse course | 8.3ms | 3.4ms | 2.5x ✅ |
| Batch 50 courses (sequential) | 80s | 25s | **3.2x** |
| Batch 50 courses (parallel) | N/A | 8s | **10x** |
| Peak memory | 500MB | 150MB | **70% reduction** |

---

## Architecture Overview

### Before (Current)

```
Python SiaScraper
  ↓ (orchestrates)
Python SiaSession.get_course_xml() → returns 2MB XML string
  ↓ (calls Rust FFI)
Rust get_course_xml() → returns string
  ↓ (string copied to Python heap)
Python scrape_info(xml) → validates with Pydantic
  ↓ (calls Rust FFI again)
Rust parse_course_info() → returns dict
  ↓ (converted to Pydantic)
Python CourseInfo (Pydantic model)
```

**Cost:** 2 FFI crossings, 2-3MB string copy, Pydantic overhead, GIL per request

### After (Target)

```
Python SiaScraper.scrape_course_info(index)
  ↓ (single async call)
Rust PySiaSession.scrape_course_info(index)
  → HTTP fetch (reqwest)
  → Parse HTML (scraper crate)
  → Build CourseInfoModel struct
  ↓ (zero-copy return)
Python receives native Rust CourseInfoModel (#[pyclass])
```

**Cost:** 1 FFI crossing, zero string copy, zero validation, Rust parallelism

---

## Phase 6: Zero-Copy Models with `#[pyclass]`

**Duration:** 2-3 weeks  
**Priority:** CRITICAL (foundation for all other improvements)  
**Goal:** Replace Pydantic models with Rust structs exposed to Python

### Task 6.1: Convert Course Models to PyClasses

**Estimated Time:** 3-4 days

#### Todo List

- [x] Update `rust/src/models/course.rs`
  - [x] Add `#[pyclass(get_all, module = "sia_scraper_rust")]` to `ScheduleModel`
  - [x] Implement `#[pymethods]` with `__new__`, `__repr__`, `__str__` for `ScheduleModel`
  - [x] Add `#[pyclass(get_all, module = "sia_scraper_rust")]` to `GroupModel`
  - [x] Implement `#[pymethods]` with `__repr__`, `__str__`, `total_hours()` for `GroupModel`
  - [x] Add `#[pyclass(get_all, module = "sia_scraper_rust")]` to `CourseInfoModel`
  - [x] Implement `#[pymethods]` with `__repr__`, `__str__`, `total_groups()`, `has_availability()` for `CourseInfoModel`
  - [x] Ensure all fields are public and derive `Serialize`, `Deserialize`, `PartialEq`, `Eq`
  - [x] Add rustdoc comments to all public methods

- [x] Update `rust/src/models/prerequisite.rs`
  - [x] Add `#[pyclass(get_all, module = "sia_scraper_rust")]` to `PrerequisiteModel`
  - [x] Implement `#[pymethods]` with `__new__`, `__repr__` for `PrerequisiteModel`
  - [x] Add `#[pyclass(get_all, module = "sia_scraper_rust")]` to `PrereqConditionModel`
  - [x] Implement `#[pymethods]` with `__repr__`, `courses_required()` for `PrereqConditionModel`
  - [x] Note: Use `type_` instead of `type` (Rust keyword)
  - [x] Add `#[pyclass(get_all, module = "sia_scraper_rust")]` to `CoursePrereqsModel`
  - [x] Implement `#[pymethods]` with `__repr__`, `has_prerequisites()` for `CoursePrereqsModel`

- [x] Update `rust/src/models/session.rs`
  - [x] Add `#[pyclass(get_all, module = "sia_scraper_rust")]` to `CourseListEntryModel`
  - [x] Implement `#[pymethods]` with `__new__`, `__repr__` for `CourseListEntryModel`
  - [x] Add `#[pyclass(get_all, module = "sia_scraper_rust")]` to `SessionStateModel`
  - [x] Implement `__getstate__(&self, py: Python) -> PyResult<PyObject>` for pickle support
  - [x] Implement `__setstate__(&mut self, state: &PyAny) -> PyResult<()>` for unpickling
  - [x] Implement `__repr__` and `is_ready()` helper methods
  - [x] Add `use std::collections::HashMap` if not present

- [x] Register classes in `rust/src/lib.rs`
  - [x] Add `m.add_class::<models::course::ScheduleModel>()?;`
  - [x] Add `m.add_class::<models::course::GroupModel>()?;`
  - [x] Add `m.add_class::<models::course::CourseInfoModel>()?;`
  - [x] Add `m.add_class::<models::prerequisite::PrerequisiteModel>()?;`
  - [x] Add `m.add_class::<models::prerequisite::PrereqConditionModel>()?;`
  - [x] Add `m.add_class::<models::prerequisite::CoursePrereqsModel>()?;`
  - [x] Add `m.add_class::<models::session::CourseListEntryModel>()?;`
  - [x] Add `m.add_class::<models::session::SessionStateModel>()?;`

- [x] Build and test
  - [x] Run `maturin develop --release`
  - [x] Test model creation in Python REPL
  - [x] Verify `__repr__` output
  - [x] Test pickle serialization
  - [x] Run `cargo clippy --manifest-path Cargo.toml`
  - [x] Run `cargo test --manifest-path Cargo.toml`

### Task 6.2: Update Type Stubs ✅ COMPLETE (PR #53)

**Completed:** April 2, 2026

**Verification Results:**
- All 8 PyClass models added to type stubs with full type hints (PR #52)
- Parser functions (`parse_course_info`, `parse_prereqs`) return model types
- Comprehensive docstrings added with usage examples (PR #53)
- Pyright verification: 0 errors (47 files analyzed)
- Verification script created: `scripts/verify_type_stubs.py` (PR #53)

#### Todo List

- [x] Update `stubs/sia_scraper_rust.pyi`
  - [x] Add `ScheduleModel` class with full type hints
  - [x] Add `GroupModel` class with full type hints
  - [x] Add `CourseInfoModel` class with full type hints
  - [x] Add `PrerequisiteModel` class with full type hints
  - [x] Add `PrereqConditionModel` class with full type hints
  - [x] Add `CoursePrereqsModel` class with full type hints
  - [x] Add `CourseListEntryModel` class with full type hints
  - [x] Add `SessionStateModel` class with pickle methods
  - [x] Update `parse_course_info()` to return `CourseInfoModel`
  - [x] Update `parse_prereqs()` to return `CoursePrereqsModel`
  - [x] Add docstrings to all classes and methods

- [x] Verify type stubs
  - [x] Run `pyright` on test files
  - [x] Check IDE autocomplete works
  - [x] Verify no type errors in existing code

### Task 6.3: Update Parser Functions

**Estimated Time:** 1-2 days

#### Todo List

- [x] Update `rust/src/parsers/course_parser.rs`
  - [x] Promote `parse_course_model()` as public typed parser returning `CourseInfoModel`
  - [x] Promote `parse_prereqs_model()` as public typed parser returning `CoursePrereqsModel`
  - [x] Remove parser-layer JSON helper variants (`parse_*_model_json`)
  - [x] Return structs directly from parser layer
  - [x] Keep parser errors on `SiaScraperError`

- [x] Update `rust/src/lib.rs`
  - [x] Route `parse_course_info()` through `parse_course_model()` typed path
  - [x] Route `parse_prereqs()` through `parse_prereqs_model()` typed path
  - [x] Keep `_json` variants for compatibility, but deprecate with `DeprecationWarning`
  - [x] Keep JSON serialization only at FFI boundary for deprecated endpoints

- [x] Update Python typed bridge to consume PyClass models directly
  - [x] Switch `scrape_info_typed()` from `parse_course_info_json()` to `parse_course_info()`
  - [x] Switch `scrape_prereqs_typed()` from `parse_prereqs_json()` to `parse_prereqs()`
  - [x] Add PyClass-to-Pydantic payload conversion helpers

- [x] Test parser changes
  - [x] Run targeted parser/parity pytest suites
  - [x] Verify typed output parity from direct PyClass models
  - [x] Add tests for deprecated JSON endpoints and warning behavior

### Task 6.4: Deprecate Python Pydantic Models

**Estimated Time:** 1 day

#### Todo List

- [ ] Mark Python models as deprecated
  - [ ] Add deprecation warning to `src/sia_scraper/models/course.py`
  - [ ] Add deprecation warning to `src/sia_scraper/models/prerequisite.py`
  - [ ] Add deprecation warning to `src/sia_scraper/models/session.py`
  - [ ] Update module docstrings with migration instructions

- [ ] Update `src/sia_scraper/__init__.py`
  - [ ] Import Rust models: `import sia_scraper_rust`
  - [ ] Create type aliases: `CourseInfo = sia_scraper_rust.CourseInfoModel`
  - [ ] Create type aliases: `CoursePrereqs = sia_scraper_rust.CoursePrereqsModel`
  - [ ] Create type aliases: `SessionState = sia_scraper_rust.SessionStateModel`
  - [ ] Export Rust models in `__all__`
  - [ ] Update version to `3.0.0-beta.1`

- [ ] Update imports in existing code
  - [ ] Update `src/sia_scraper/scraper.py` to use Rust models
  - [ ] Update `src/sia_scraper/session.py` to use Rust models
  - [ ] Search for old imports and update

### Task 6.5: Migrate Model Tests

**Estimated Time:** 2-3 days

#### Todo List

- [ ] Update `tests/models/test_course_typed_models.py`
  - [ ] Import `sia_scraper_rust` models
  - [ ] Test `ScheduleModel` creation and fields
  - [ ] Test `GroupModel` creation and methods
  - [ ] Test `CourseInfoModel` creation and methods
  - [ ] Test `__repr__` and `__str__` output
  - [ ] Test helper methods (`total_groups()`, `has_availability()`, etc.)

- [ ] Update `tests/models/test_prerequisite_typed_models.py`
  - [ ] Import `sia_scraper_rust` models
  - [ ] Test `PrerequisiteModel` creation
  - [ ] Test `PrereqConditionModel` creation and methods
  - [ ] Test `CoursePrereqsModel` creation and methods

- [ ] Update `tests/models/test_session_typed_models.py`
  - [ ] Import `sia_scraper_rust` models
  - [ ] Test `CourseListEntryModel` creation
  - [ ] Test `SessionStateModel` creation
  - [ ] Test pickle serialization/deserialization
  - [ ] Test `is_ready()` method

- [ ] Add integration tests
  - [ ] Test parser returns correct model types
  - [ ] Test model field access from Python
  - [ ] Test nested models (groups, schedules, prerequisites)
  - [ ] Test edge cases (None values, empty lists)

- [ ] Run full test suite
  - [ ] `pytest tests/models/ -v`
  - [ ] `pytest tests/parsers/ -v`
  - [ ] Ensure all tests pass
  - [ ] Check test coverage

### Task 6.6: Phase 6 Validation

**Estimated Time:** 1 day

#### Todo List

- [ ] Code quality checks
  - [ ] Run `cargo clippy --manifest-path Cargo.toml` (zero warnings)
  - [ ] Run `cargo test --manifest-path Cargo.toml` (all pass)
  - [ ] Run `ruff check . && ruff format .` (clean)
  - [ ] Run `pyright` (zero errors)
  - [ ] Run `pytest --cov=src/sia_scraper` (maintain coverage)

- [ ] Performance validation
  - [ ] Run `python benchmarks/benchmark_parsing.py`
  - [ ] Verify no regression in parse times
  - [ ] Measure memory usage with Rust models vs Pydantic
  - [ ] Document performance gains

- [ ] Documentation
  - [ ] Update CHANGELOG.md with Phase 6 completion
  - [ ] Document breaking changes
  - [ ] Update MIGRATION_PLAN.md status
  - [ ] Add inline code examples

- [ ] Git workflow
  - [ ] Commit Phase 6 changes with descriptive message
  - [ ] Tag as `v3.0.0-alpha.1`
  - [ ] Push to remote branch

---

## Phase 7: Unified HTTP + Parse Pipeline

**Duration:** 2-3 weeks  
**Priority:** HIGH (eliminates string copying bottleneck)  
**Goal:** Combine HTTP fetch + parsing in single Rust function

### Task 7.1: Extend SiaSession with Direct Scraping

**Estimated Time:** 3-4 days

#### Todo List

- [ ] Update `rust/src/http/sia_session.rs`
  - [ ] Rename `get_course_xml()` to `get_course_xml_internal()` (private)
  - [ ] Add `async fn scrape_course_info(&self, course_index: i32) -> Result<CourseInfoModel, HttpError>`
  - [ ] Implement: fetch XML internally → parse → return struct
  - [ ] Add `async fn scrape_course_prereqs(&self, course_index: i32) -> Result<CoursePrereqsModel, HttpError>`
  - [ ] Add error handling and logging
  - [ ] Add rustdoc comments
  - [ ] Ensure XML never crosses FFI boundary

- [ ] Add unit tests in `rust/src/http/sia_session.rs`
  - [ ] Test `scrape_course_info()` with mock server
  - [ ] Test `scrape_course_prereqs()` with mock server
  - [ ] Test error cases (network failure, parse error)
  - [ ] Test that XML is not exposed externally

- [ ] Build and verify
  - [ ] Run `cargo test --manifest-path Cargo.toml`
  - [ ] Run `cargo clippy --manifest-path Cargo.toml`
  - [ ] Verify no panics in error paths

### Task 7.2: Create Stateful PySiaSession

**Estimated Time:** 4-5 days

#### Todo List

- [ ] Create `rust/src/http/py_session.rs`
  - [ ] Add `use` statements (pyo3, tokio, Arc, RwLock, models, etc.)
  - [ ] Define `#[pyclass(module = "sia_scraper_rust")] pub struct PySiaSession`
  - [ ] Add `inner: Arc<RwLock<SiaSession>>` field
  - [ ] Implement `#[new] fn new(timeout: Option<u64>) -> PyResult<Self>`
  - [ ] Add async `init_session()` method with `future_into_py`
  - [ ] Add async `set_career()` method
  - [ ] Add async `scrape_course_info()` method (returns `CourseInfoModel`)
  - [ ] Add async `scrape_course_prereqs()` method (returns `CoursePrereqsModel`)
  - [ ] Add async `get_state()` method (returns `SessionStateModel`)
  - [ ] Add proper error handling with `PyErr` conversion

- [ ] Update `rust/src/http/mod.rs`
  - [ ] Add `pub mod py_session;`
  - [ ] Export `PySiaSession`

- [ ] Register in `rust/src/lib.rs`
  - [ ] Add `use crate::http::py_session::PySiaSession;`
  - [ ] Add `m.add_class::<PySiaSession>()?;` in pymodule

- [ ] Update type stubs `stubs/sia_scraper_rust.pyi`
  - [ ] Add `PySiaSession` class definition
  - [ ] Add all method signatures with type hints
  - [ ] Add docstrings

- [ ] Test PySiaSession
  - [ ] Create integration test in `tests/rust/test_py_session.py`
  - [ ] Test session creation
  - [ ] Test init_session()
  - [ ] Test set_career()
  - [ ] Test scrape_course_info()
  - [ ] Test error handling

### Task 7.3: Update Python Session Wrapper

**Estimated Time:** 2 days

#### Todo List

- [ ] Simplify `src/sia_scraper/session.py`
  - [ ] Remove all HTTP logic (delegate to Rust)
  - [ ] Remove ViewState tracking (Rust handles it)
  - [ ] Keep only thin wrapper methods
  - [ ] Add `self._rust_session = sia_scraper_rust.PySiaSession(timeout)` in `__init__`
  - [ ] Update `init_session()` to call `self._rust_session.init_session()`
  - [ ] Update `set_career()` to call `self._rust_session.set_career()`
  - [ ] Add `scrape_course_info()` delegating to Rust
  - [ ] Add `scrape_course_prereqs()` delegating to Rust
  - [ ] Update `get_state()` to call Rust
  - [ ] Remove old `get_course_xml()` method (no longer needed)
  - [ ] Keep `@classmethod async def create()` factory

- [ ] Update class docstrings
  - [ ] Document that all computation happens in Rust
  - [ ] Update examples in docstrings
  - [ ] Remove references to obsolete methods

- [ ] Clean up imports
  - [ ] Remove unused imports
  - [ ] Add `import sia_scraper_rust`
  - [ ] Run `ruff check . && ruff format .`

### Task 7.4: Update Scraper Facade

**Estimated Time:** 2 days

#### Todo List

- [ ] Update `src/sia_scraper/scraper.py`
  - [ ] Update `get_course_info()` to use `session.scrape_course_info()`
  - [ ] Update `get_course_prereqs()` to use `session.scrape_course_prereqs()`
  - [ ] Remove old parsing logic (now in Rust)
  - [ ] Update return type hints to use Rust models
  - [ ] Update docstrings with new behavior

- [ ] Update scraper tests in `tests/test_scraper.py`
  - [ ] Update expected return types
  - [ ] Test that Rust models are returned
  - [ ] Test error handling
  - [ ] Test async workflow

### Task 7.5: Phase 7 Validation

**Estimated Time:** 2 days

#### Todo List

- [ ] Integration testing
  - [ ] Test full workflow: create → set_career → scrape courses
  - [ ] Test with real SIA (optional, can mock)
  - [ ] Test error scenarios
  - [ ] Test session state persistence

- [ ] Performance benchmarking
  - [ ] Create `benchmarks/benchmark_phase7.py`
  - [ ] Measure time for 10 course scrapes (old vs new)
  - [ ] Measure memory usage (old vs new)
  - [ ] Document string copy elimination
  - [ ] Target: 2-3x improvement

- [ ] Code quality
  - [ ] Run full test suite
  - [ ] Run `cargo clippy && cargo test`
  - [ ] Run `ruff check . && pyright`
  - [ ] Verify zero warnings/errors

- [ ] Git workflow
  - [ ] Commit Phase 7 changes
  - [ ] Tag as `v3.0.0-alpha.2`
  - [ ] Update MIGRATION_PLAN.md

---

## Phase 8: Typed Error Hierarchy

**Duration:** 1 week  
**Priority:** MEDIUM (improves error handling)  
**Goal:** Granular error types from Rust mapped to Python exceptions

### Task 8.1: Expand Rust Error Types

**Estimated Time:** 2 days

#### Todo List

- [ ] Update `rust/src/http/errors.rs`
  - [ ] Add `#[derive(Error, Debug, Clone)]` to `HttpError`
  - [ ] Add `NetworkError(String)` variant
  - [ ] Add `HttpStatusError { status: u16, message: String }` variant
  - [ ] Add `TimeoutError { timeout: u64, operation: String }` variant
  - [ ] Add `ParseError(String)` variant
  - [ ] Add `InvalidInput(String)` variant
  - [ ] Add `SessionError(String)` variant
  - [ ] Implement `is_retryable(&self) -> bool` method
  - [ ] Add rustdoc comments for each variant

- [ ] Update error conversions
  - [ ] Implement `From<reqwest::Error> for HttpError`
  - [ ] Implement `From<SiaScraperError> for HttpError`
  - [ ] Update all error usage in `sia_session.rs`

- [ ] Test error types
  - [ ] Add unit tests for each error variant
  - [ ] Test `is_retryable()` logic
  - [ ] Test error message formatting

### Task 8.2: Create Python Exception Types

**Estimated Time:** 2 days

#### Todo List

- [ ] Update `rust/src/lib.rs`
  - [ ] Add `create_exception!(sia_scraper_rust, NetworkError, PyException);`
  - [ ] Add `create_exception!(sia_scraper_rust, HttpStatusError, PyException);`
  - [ ] Add `create_exception!(sia_scraper_rust, TimeoutError, PyException);`
  - [ ] Add `create_exception!(sia_scraper_rust, ParseError, PyException);`
  - [ ] Add `create_exception!(sia_scraper_rust, SessionError, PyException);`
  - [ ] Implement `From<HttpError> for PyErr` with proper mapping
  - [ ] Register exceptions in pymodule: `m.add("NetworkError", py.get_type::<NetworkError>())?;`

- [ ] Update type stubs `stubs/sia_scraper_rust.pyi`
  - [ ] Add `class NetworkError(Exception): ...`
  - [ ] Add `class HttpStatusError(Exception): ...`
  - [ ] Add `class TimeoutError(Exception): ...`
  - [ ] Add `class ParseError(Exception): ...`
  - [ ] Add `class SessionError(Exception): ...`

- [ ] Test exception raising
  - [ ] Test each exception type can be caught in Python
  - [ ] Test exception messages are preserved
  - [ ] Test exception inheritance

### Task 8.3: Update Python Exception Handling

**Estimated Time:** 1 day

#### Todo List

- [ ] Update `src/sia_scraper/core/exceptions.py`
  - [ ] Import Rust exceptions: `from sia_scraper_rust import NetworkError, HttpStatusError, ...`
  - [ ] Re-export for convenience
  - [ ] Keep backward-compatible wrappers
  - [ ] Update module docstrings

- [ ] Update error handling in `src/sia_scraper/session.py`
  - [ ] Catch specific Rust exceptions where appropriate
  - [ ] Add try/except blocks with specific exception types
  - [ ] Update error messages

- [ ] Update error handling in `src/sia_scraper/scraper.py`
  - [ ] Catch and handle specific error types
  - [ ] Provide helpful error context

### Task 8.4: Phase 8 Validation

**Estimated Time:** 1 day

#### Todo List

- [ ] Test error handling
  - [ ] Create `tests/test_error_handling.py`
  - [ ] Test each exception type is raised correctly
  - [ ] Test exception inheritance
  - [ ] Test error messages

- [ ] Code quality
  - [ ] Run `cargo clippy && cargo test`
  - [ ] Run `ruff check . && pyright`
  - [ ] Run `pytest tests/`

- [ ] Documentation
  - [ ] Document error types in README
  - [ ] Add error handling examples
  - [ ] Update CHANGELOG.md

- [ ] Git workflow
  - [ ] Commit Phase 8 changes
  - [ ] Tag as `v3.0.0-alpha.3`

---

## Phase 9: Rust Orchestration (Batch Scraping & Parallelism)

**Duration:** 2 weeks  
**Priority:** HIGH (enables parallel scraping, major performance gain)  
**Goal:** Move control flow and retry logic to Rust

### Task 9.1: Implement Batch Scraping in Rust

**Estimated Time:** 4-5 days

#### Todo List

- [ ] Define error modes in `rust/src/http/sia_session.rs`
  - [ ] Add `#[derive(Debug, Clone, Copy)] pub enum ErrorMode { Abort, Skip, Retry }`
  - [ ] Add conversion from string for PyO3

- [ ] Implement sequential batch scraping
  - [ ] Add `async fn scrape_courses_batch()` to `SiaSession`
  - [ ] Implement abort mode (fail on first error)
  - [ ] Implement skip mode (record failures, continue)
  - [ ] Implement retry mode (retry with backoff)
  - [ ] Add logging for batch progress
  - [ ] Use `is_retryable()` to decide retry eligibility
  - [ ] Add `tokio::time::sleep()` for retry delay

- [ ] Add unit tests
  - [ ] Test abort mode stops on first error
  - [ ] Test skip mode continues after errors
  - [ ] Test retry mode retries failures
  - [ ] Test with mock server returning failures

### Task 9.2: Implement Parallel Scraping

**Estimated Time:** 3-4 days

#### Todo List

- [ ] Add concurrent scraping to `rust/src/http/sia_session.rs`
  - [ ] Add `futures` crate to Cargo.toml dependencies
  - [ ] Implement `async fn scrape_courses_concurrent()`
  - [ ] Use `futures::stream::StreamExt` for concurrent execution
  - [ ] Use `buffer_unordered(max_concurrent)` for parallelism
  - [ ] Handle Arc/RwLock for shared session state
  - [ ] Collect results into `ScrapeResult`

- [ ] Add concurrency tests
  - [ ] Test parallel execution with mock server
  - [ ] Test concurrency limit is respected
  - [ ] Test error handling in concurrent mode
  - [ ] Benchmark parallel vs sequential

### Task 9.3: Create ScrapeResult Model

**Estimated Time:** 1 day

#### Todo List

- [ ] Create `rust/src/models/scrape_result.rs`
  - [ ] Define `#[pyclass] pub struct ScrapeResult`
  - [ ] Add `successes: Vec<CourseInfoModel>` field
  - [ ] Add `failures: Vec<(usize, String)>` field
  - [ ] Implement `#[pymethods]` with `total()`, `success_rate()`, `__repr__()`

- [ ] Register in `rust/src/models/mod.rs`
  - [ ] Add `pub mod scrape_result;`
  - [ ] Export `ScrapeResult`

- [ ] Register in `rust/src/lib.rs`
  - [ ] Add `m.add_class::<models::scrape_result::ScrapeResult>()?;`

- [ ] Update type stubs
  - [ ] Add `ScrapeResult` class to `stubs/sia_scraper_rust.pyi`

### Task 9.4: Expose Batch Scraping to Python

**Estimated Time:** 2 days

#### Todo List

- [ ] Update `rust/src/http/py_session.rs`
  - [ ] Add `scrape_courses()` method taking indices, error_mode, retries, delay
  - [ ] Convert error_mode string to `ErrorMode` enum
  - [ ] Call Rust `scrape_courses_batch()`
  - [ ] Return `ScrapeResult`
  - [ ] Add `scrape_courses_parallel()` method
  - [ ] Call Rust `scrape_courses_concurrent()`

- [ ] Update type stubs
  - [ ] Add method signatures to `PySiaSession`
  - [ ] Document parameters and return types

### Task 9.5: Update Python Scraper Facade

**Estimated Time:** 2 days

#### Todo List

- [ ] Simplify `src/sia_scraper/scraper.py`
  - [ ] Remove Python retry logic (now in Rust)
  - [ ] Remove Python batch loop (now in Rust)
  - [ ] Add `scrape_courses()` delegating to Rust
  - [ ] Add `scrape_courses_parallel()` delegating to Rust
  - [ ] Keep simple API with good defaults
  - [ ] Update docstrings with examples

- [ ] Update scraper tests
  - [ ] Test `scrape_courses()` with different error modes
  - [ ] Test `scrape_courses_parallel()`
  - [ ] Test `ScrapeResult` properties
  - [ ] Test error handling

### Task 9.6: Phase 9 Validation

**Estimated Time:** 3 days

#### Todo List

- [ ] Comprehensive testing
  - [ ] Test batch scraping with 50+ courses
  - [ ] Test error recovery
  - [ ] Test parallel vs sequential performance
  - [ ] Test memory usage during batch operations

- [ ] Performance benchmarking
  - [ ] Create `benchmarks/benchmark_batch_scraping.py`
  - [ ] Measure sequential batch (old vs new)
  - [ ] Measure parallel batch (new only)
  - [ ] Document speedups (target: 3-10x)
  - [ ] Measure memory usage

- [ ] Code quality
  - [ ] Run full test suite
  - [ ] Run `cargo clippy && cargo test`
  - [ ] Run `ruff check . && pyright`
  - [ ] Zero warnings/errors

- [ ] Documentation
  - [ ] Add batch scraping examples to README
  - [ ] Document error modes
  - [ ] Document parallel scraping
  - [ ] Update CHANGELOG.md

- [ ] Git workflow
  - [ ] Commit Phase 9 changes
  - [ ] Tag as `v3.0.0-beta.1`

---

## Phase 10: Python Cleanup & Documentation

**Duration:** 1 week  
**Priority:** LOW (polish)  
**Goal:** Remove obsolete code, finalize documentation

### Task 10.1: Delete Obsolete Python Code

**Estimated Time:** 1 day

#### Todo List

- [ ] Delete obsolete files
  - [ ] Delete `src/sia_scraper/parsers/html_parser.py`
  - [ ] Delete `src/sia_scraper/parsers/course_parser.py`
  - [ ] Delete `src/sia_scraper/models/course.py`
  - [ ] Delete `src/sia_scraper/models/prerequisite.py`
  - [ ] Delete `src/sia_scraper/core/adf_state.py` (if not needed)
  - [ ] Delete `src/sia_scraper/utils/date_formatter.py` (move to Rust if needed)

- [ ] Delete obsolete tests
  - [ ] Delete `tests/parsers/test_html_parser.py`
  - [ ] Delete `tests/parsers/test_course_parser.py` (keep integration tests)
  - [ ] Review and clean up other parser tests

- [ ] Update `src/sia_scraper/__init__.py`
  - [ ] Remove imports for deleted modules
  - [ ] Clean up exports
  - [ ] Verify version is `3.0.0`

- [ ] Clean up imports across codebase
  - [ ] Search for imports from deleted modules
  - [ ] Update to use Rust models
  - [ ] Run `ruff check --fix .`

### Task 10.2: Simplify Remaining Python Code

**Estimated Time:** 1 day

#### Todo List

- [ ] Review `src/sia_scraper/session.py`
  - [ ] Ensure < 100 lines
  - [ ] Remove any remaining computational logic
  - [ ] Keep only delegation and convenience methods
  - [ ] Improve docstrings

- [ ] Review `src/sia_scraper/scraper.py`
  - [ ] Ensure < 150 lines
  - [ ] Remove any remaining computational logic
  - [ ] Keep only high-level API
  - [ ] Improve docstrings

- [ ] Review `src/sia_scraper/core/exceptions.py`
  - [ ] Ensure < 100 lines
  - [ ] Keep only re-exports and wrappers
  - [ ] Add migration notes

- [ ] Verify Python codebase size
  - [ ] Run `find src/sia_scraper -name "*.py" -exec wc -l {} + | tail -1`
  - [ ] Target: < 1000 lines total

### Task 10.3: Update Documentation

**Estimated Time:** 2 days

#### Todo List

- [ ] Update README.md
  - [ ] Add performance comparison table
  - [ ] Add architecture diagram
  - [ ] Add quick start examples
  - [ ] Add parallel scraping examples
  - [ ] Document batch scraping error modes
  - [ ] Add installation instructions
  - [ ] Update feature list

- [ ] Create migration guide `docs/MIGRATION_v3.md`
  - [ ] Document breaking changes
  - [ ] Provide before/after code examples
  - [ ] List deprecated features
  - [ ] Provide migration checklist
  - [ ] Add FAQ section

- [ ] Update CHANGELOG.md
  - [ ] Add v3.0.0 section
  - [ ] List all breaking changes
  - [ ] List all new features
  - [ ] List performance improvements
  - [ ] Credit contributors

- [ ] Update AGENTS.md
  - [ ] Update architecture section
  - [ ] Update build commands
  - [ ] Update testing guidelines
  - [ ] Add v3.0 notes

### Task 10.4: Performance Documentation

**Estimated Time:** 1 day

#### Todo List

- [ ] Create comprehensive benchmarks
  - [ ] Run all benchmarks in `benchmarks/`
  - [ ] Collect performance data
  - [ ] Create comparison tables
  - [ ] Document methodology

- [ ] Create `docs/PERFORMANCE.md`
  - [ ] Document parsing performance
  - [ ] Document batch scraping performance
  - [ ] Document parallel scraping performance
  - [ ] Document memory usage
  - [ ] Add benchmark reproduction steps

- [ ] Add performance tests to CI
  - [ ] Create benchmark workflow
  - [ ] Set performance regression thresholds
  - [ ] Document in README

### Task 10.5: Final Testing & Release Preparation

**Estimated Time:** 2 days

#### Todo List

- [ ] Comprehensive testing
  - [ ] Run full test suite: `pytest tests/ -v`
  - [ ] Run Rust tests: `cargo test --manifest-path Cargo.toml`
  - [ ] Run benchmarks: `python benchmarks/benchmark_full_pipeline.py`
  - [ ] Test on all supported Python versions (3.10, 3.11, 3.12)
  - [ ] Test installation from source
  - [ ] Test wheel installation

- [ ] Code quality final check
  - [ ] Run `cargo clippy --manifest-path Cargo.toml` (zero warnings)
  - [ ] Run `cargo test --manifest-path Cargo.toml` (all pass)
  - [ ] Run `ruff check . && ruff format .` (clean)
  - [ ] Run `pyright` (zero errors)
  - [ ] Check code coverage: `pytest --cov=src/sia_scraper`

- [ ] Build release artifacts
  - [ ] Build wheels: `maturin build --release`
  - [ ] Build source distribution: `maturin sdist`
  - [ ] Verify wheel contents
  - [ ] Test wheel installation

- [ ] Update version numbers
  - [ ] Update `Cargo.toml` version to `3.0.0`
  - [ ] Update `pyproject.toml` version to `3.0.0`
  - [ ] Update `src/sia_scraper/__init__.py` version to `3.0.0`
  - [ ] Verify all version strings match

### Task 10.6: Release

**Estimated Time:** 1 day

#### Todo List

- [ ] Pre-release checklist
  - [ ] All tests passing
  - [ ] Documentation complete
  - [ ] CHANGELOG.md updated
  - [ ] Migration guide complete
  - [ ] Performance benchmarks documented

- [ ] Git workflow
  - [ ] Merge feature branch to main
  - [ ] Tag release: `git tag -a v3.0.0 -m "Release v3.0.0"`
  - [ ] Push tags: `git push origin v3.0.0`

- [ ] GitHub release
  - [ ] Create GitHub release from tag
  - [ ] Upload wheel artifacts
  - [ ] Add release notes (from CHANGELOG)
  - [ ] Highlight breaking changes
  - [ ] Link to migration guide

- [ ] PyPI release (optional, can defer)
  - [ ] Test upload to TestPyPI
  - [ ] Verify installation from TestPyPI
  - [ ] Upload to production PyPI
  - [ ] Verify installation from PyPI

- [ ] Post-release
  - [ ] Announce release (if applicable)
  - [ ] Update documentation website (if applicable)
  - [ ] Monitor for issues

---

## Timeline Summary

| Phase | Duration | Start | End |
|-------|----------|-------|-----|
| Phase 6: Zero-Copy Models | 2-3 weeks | Week 1 | Week 3 |
| Phase 7: Unified Pipeline | 2-3 weeks | Week 4 | Week 6 |
| Phase 8: Typed Errors | 1 week | Week 7 | Week 8 |
| Phase 9: Batch Orchestration | 2 weeks | Week 9 | Week 11 |
| Phase 10: Cleanup & Release | 1 week | Week 12 | Week 12 |

**Total Duration:** 12 weeks (3 months)

---

## Success Criteria

### Performance Metrics

- [ ] Parse course: maintain 2.5x speedup vs Python
- [ ] Batch 50 courses sequential: achieve 3x+ speedup
- [ ] Batch 50 courses parallel: achieve 10x+ speedup
- [ ] Memory usage: reduce by 60%+ vs current

### Code Quality Metrics

- [ ] Python codebase: < 1000 lines (70% reduction)
- [ ] Rust test coverage: 100% for core modules
- [ ] Python test coverage: maintain 90%+
- [ ] Zero clippy warnings
- [ ] Zero pyright errors

### Feature Completeness

- [ ] All models as `#[pyclass]`
- [ ] Session state picklable
- [ ] Typed error hierarchy
- [ ] Batch scraping with error modes
- [ ] Parallel scraping support
- [ ] Complete documentation

---

## Risk Management

### Risk 1: Breaking Changes Impact
**Probability:** HIGH  
**Impact:** HIGH  
**Mitigation:**
- [ ] Clear migration guide with examples
- [ ] Deprecation warnings in v2.9.0
- [ ] 6-month support for v2.x
- [ ] Active monitoring of user feedback

### Risk 2: Performance Regression
**Probability:** LOW  
**Impact:** HIGH  
**Mitigation:**
- [ ] Benchmark after each phase
- [ ] Performance tests in CI
- [ ] Accept only < 2% regression
- [ ] Rollback plan ready

### Risk 3: Session State Compatibility
**Probability:** MEDIUM  
**Impact:** MEDIUM  
**Mitigation:**
- [ ] Extensive pickle testing
- [ ] Migration script for session files
- [ ] Versioned session schema
- [ ] Backward compatibility layer

### Risk 4: Concurrency Bugs
**Probability:** MEDIUM  
**Impact:** HIGH  
**Mitigation:**
- [ ] Rust ownership prevents data races
- [ ] Comprehensive async tests
- [ ] Stress testing (100+ concurrent)
- [ ] Tokio's proven runtime

### Risk 5: PyO3 Compatibility Issues
**Probability:** LOW  
**Impact:** MEDIUM  
**Mitigation:**
- [ ] Pin PyO3 version
- [ ] Test on all target platforms
- [ ] Monitor PyO3 release notes
- [ ] Maintain compatibility layer

---

## Dependencies & Prerequisites

### Rust Dependencies (Cargo.toml)

```toml
[dependencies]
pyo3 = { version = "0.20", features = ["extension-module", "abi3-py310"] }
pyo3-asyncio = { version = "0.20", features = ["tokio-runtime"] }
tokio = { version = "1", features = ["full"] }
reqwest = { version = "0.11", features = ["json"] }
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
thiserror = "1.0"
scraper = "0.17"
futures = "0.3"
```

### Python Dependencies (pyproject.toml)

```toml
[project]
name = "sia-scraper"
version = "3.0.0"
requires-python = ">=3.10"
dependencies = []  # All heavy deps removed!

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "pytest-cov>=4.0",
    "pyright>=1.1",
    "ruff>=0.1",
]
```

---

## Communication & Documentation Plan

### Internal Documentation

- [ ] Update MIGRATION_PLAN.md with progress
- [ ] Document architecture decisions
- [ ] Keep CHANGELOG.md current
- [ ] Maintain inline code documentation

### External Communication

- [ ] Release announcement (blog post / GitHub Discussions)
- [ ] Migration guide for users
- [ ] Performance comparison charts
- [ ] Breaking changes clearly documented

### Support Plan

- [ ] Monitor GitHub issues for migration problems
- [ ] Provide migration assistance
- [ ] Maintain v2.x with critical fixes for 6 months
- [ ] FAQ document for common issues

---

## Post-Release Roadmap (v3.1+)

### Future Enhancements

- [ ] **v3.1**: Add caching layer for repeated queries
- [ ] **v3.1**: Add rate limiting support
- [ ] **v3.2**: WebAssembly compilation for browser usage
- [ ] **v3.2**: GraphQL API wrapper
- [ ] **v3.3**: Real-time session monitoring
- [ ] **v4.0**: Remove all deprecated APIs

### Maintenance Plan

- [ ] Monthly dependency updates
- [ ] Security audit every 6 months
- [ ] Performance regression monitoring
- [ ] User feedback incorporation

---

## Appendix: Key Code Examples

### Example 1: Using Zero-Copy Models

```python
import asyncio
from sia_scraper import SiaScraper

async def main():
    async with SiaScraper.create() as scraper:
        await scraper.set_career("0-2-8-3")
        
        # Returns native Rust object (zero-copy)
        course = await scraper.scrape_course_info(0)
        
        # Direct field access (no dict, no validation)
        print(f"{course.course_name}: {course.credits} credits")
        print(f"Groups: {course.total_groups()}")
        print(f"Available: {course.has_availability()}")
        
        # Access nested models
        for group in course.groups:
            print(f"  {group.group_name}: {group.teacher}")
            for schedule in group.schedules:
                print(f"    {schedule.day} {schedule.start_time}-{schedule.end_time}")

asyncio.run(main())
```

### Example 2: Batch Scraping with Error Handling

```python
import asyncio
from sia_scraper import SiaScraper

async def main():
    async with SiaScraper.create() as scraper:
        await scraper.set_career("0-2-8-3")
        
        # Batch scrape with retry
        result = await scraper.scrape_courses(
            indices=list(range(50)),
            error_mode="retry",  # "abort", "skip", or "retry"
            max_retries=3,
            retry_delay=1.0,
        )
        
        print(f"Scraped {len(result.successes)}/{result.total()} courses")
        print(f"Success rate: {result.success_rate():.1%}")
        
        # Access results
        for course in result.successes:
            print(course.course_name)
        
        # Handle failures
        for index, error in result.failures:
            print(f"Failed index {index}: {error}")

asyncio.run(main())
```

### Example 3: Parallel Scraping

```python
import asyncio
from sia_scraper import SiaScraper

async def main():
    async with SiaScraper.create() as scraper:
        await scraper.set_career("0-2-8-3")
        
        # Parallel scraping (10x faster!)
        result = await scraper.scrape_courses_parallel(
            indices=list(range(100)),
            max_concurrent=10,  # 10 concurrent requests
        )
        
        print(f"Scraped {len(result.successes)} courses in parallel")
        print(f"Success rate: {result.success_rate():.1%}")

asyncio.run(main())
```

### Example 4: Session Persistence

```python
import asyncio
import pickle
from sia_scraper import SiaScraper

async def save_session():
    async with SiaScraper.create() as scraper:
        await scraper.set_career("0-2-8-3")
        
        # Get session state
        state = await scraper.get_state()
        
        # Pickle it
        with open("session.pkl", "wb") as f:
            pickle.dump(state, f)

async def restore_session():
    # Load session state
    with open("session.pkl", "rb") as f:
        state = pickle.load(f)
    
    # Restore session (implementation depends on API)
    scraper = await SiaScraper.create()
    # ... restore logic ...

asyncio.run(save_session())
```

---

## Conclusion

This plan transforms `sia-scraper` into a true Rust-first library with Python providing only a friendly interface. The systematic approach ensures:

- **Zero computational overhead in Python**
- **3-10x performance improvement**
- **70% code reduction**
- **Type-safe, maintainable codebase**
- **True async parallelism**

Each phase is self-contained, testable, and measurable. The detailed todo lists provide clear actionable steps for execution.

**Ready to begin? Start with Phase 6, Task 6.1! 🚀**
