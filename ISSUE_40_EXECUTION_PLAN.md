# Execution Plan - Issue #40: Implement Batch Scraping in Rust

This plan outlines the implementation of Task 9.1 from the v3.0 Migration Roadmap. The goal is to move the batch scraping orchestration from Python to Rust, enabling more efficient execution and providing robust error handling modes.

## Architectural Goals
- **Rust Orchestration:** Move loops and retry logic from Python to Rust to minimize FFI overhead and GIL contention.
- **Thin Wrapper:** Python remains a type-hinted interface delegating to Rust.
- **Zero-Panic:** All Rust code must use `Result` for error propagation.
- **Google-Style Docstrings:** Comprehensive documentation for all public interfaces.

---

## Phased Breakdown

### Phase 1: Models and Core Definitions
**Goal:** Define the data structures for error handling and results in Rust.

- [ ] **Define `ErrorMode` Enum** in `rust/src/http/sia_session.rs` (or a new `rust/src/http/types.rs` if appropriate):
  - [ ] Add `#[derive(Debug, Clone, Copy, PartialEq, Eq)]`.
  - [ ] Variants: `Abort` (fail fast), `Skip` (ignore errors), `Retry` (retry on failure).
  - [ ] Implement `FromStr` or a PyO3-friendly conversion for string-based selection from Python.

- [ ] **Define `ScrapeResult` Struct** (Preliminary Task 9.3) in `rust/src/models/scrape_result.rs`:
  - [ ] Add `#[pyclass(get_all, module = "sia_scraper_rust")]`.
  - [ ] Fields: `successes: Vec<CourseInfoModel>`, `failures: Vec<(usize, String)>` (index and error message).
  - [ ] Implement `#[pymethods]` for `total()`, `success_rate()`, and `__repr__`.

- [ ] **Register `ScrapeResult`** in `rust/src/models/mod.rs` and `rust/src/lib.rs`.

### Phase 2: Sequential Batch Scraping Implementation
**Goal:** Implement the logic for scraping multiple courses sequentially in `SiaSession`.

- [ ] **Update `SiaSession`** in `rust/src/http/sia_session.rs`:
  - [ ] Add `async fn scrape_courses_batch(&self, indices: Vec<i32>, mode: ErrorMode, max_retries: u32, retry_delay_ms: u64) -> Result<ScrapeResult, HttpError>`.
  - [ ] Implement loop over indices:
    - [ ] Perform `scrape_course_info(index)`.
    - [ ] Handle errors based on `ErrorMode`:
      - **`Abort`**: Return `Err` immediately on the first failure.
      - **`Skip`**: Record failure in `ScrapeResult` and continue.
      - **`Retry`**: Use `should_retry()` and `calculate_delay()` (integrating with `RetryConfig`) before failing over to `Skip` or `Abort`.
    - [ ] Add logging for progress (e.g., "Scraping course 5/50...").

### Phase 3: PyO3 Bridge and Python Integration
**Goal:** Expose the new functionality to Python via `PySiaSession`.

- [ ] **Update `PySiaSession`** in `rust/src/http/py_session.rs`:
  - [ ] Add `async fn scrape_courses(&self, indices: Vec<i32>, mode: String, retries: Option<u32>, delay: Option<u64>) -> PyResult<ScrapeResult>`.
  - [ ] Map Python string `mode` to Rust `ErrorMode`.
  - [ ] Call internal `scrape_courses_batch`.

- [ ] **Update Type Stubs** in `stubs/sia_scraper_rust.pyi`:
  - [ ] Add `ScrapeResult` class definition.
  - [ ] Add `scrape_courses` method to `PySiaSession`.

- [ ] **Refactor `SiaScraper`** in `src/sia_scraper/scraper.py`:
  - [ ] Delegate `scrape_courses` to `self._sia_session.scrape_courses()`.
  - [ ] Ensure backward compatibility with the existing Python API if possible, or mark as a breaking change for v3.0.

---

## Verification Gates

### Rust Unit Tests
- [ ] **Test `ErrorMode` Logic**:
  - [ ] Mock server that fails on specific indices.
  - [ ] Verify `Abort` stops immediately.
  - [ ] Verify `Skip` collects all results.
  - [ ] Verify `Retry` attempts the specified number of times.
- [ ] **Command**: `cargo test --lib http::sia_session`

### Python Integration Tests
- [ ] **Verify `ScrapeResult` Access**:
  - [ ] Ensure `successes` and `failures` are accessible from Python.
  - [ ] Check `total()` and `success_rate()` methods.
- [ ] **Benchmark**: Compare sequential batch scraping in Rust vs old Python implementation.
- [ ] **Command**: `pytest tests/rust/test_py_session.py` (New test file)

### Quality Controls
- [ ] **Linter**: `cargo clippy --manifest-path Cargo.toml` (Zero warnings).
- [ ] **Formatter**: `ruff format .` and `cargo fmt`.
- [ ] **Type Check**: `pyright`.

---

## Technical Notes
- **Memory Efficiency:** By returning `CourseInfoModel` as `#[pyclass]`, we avoid expensive JSON serialization and string copies.
- **GIL Management:** Ensure `scrape_courses` is properly `async` in Rust to avoid blocking the Python event loop.
