# Rust Migration Plan: sia-scraper

## Executive Summary

Progressive migration from pure Python to Rust-accelerated parsing using PyO3 + Maturin.
Goal: 2-5x performance improvement while maintaining idiomatic Python API.

## Architecture: Bottom-Up Migration

### Current State
- **Facade**: `scraper.py` (public entry point)
- **Network & State**: `session.py` (HTTP, ViewState sync)
- **Parsers**: `parsers/` (lxml + Pydantic validation)

### Target State
- **Rust Core**: HTML/XML parsing, ADF logic, HTTP client (async)
- **Python Wrapper**: Type hints, Pydantic validation, public API
- **Build**: Maturin wheels for cross-platform distribution

## Migration Phases

### Phase 0: Build Infrastructure ✅ COMPLETE
**Completed:** 2026-03-XX
- Maturin build backend in `pyproject.toml`
- `Cargo.toml` with PyO3 dependencies
- `rust/src/lib.rs` exposing Python module
- Build pipeline validated

### Phase 1: HTML Parsers (The Bottleneck) ✅ COMPLETE
**Status:** 100% complete

**Completed:**
- ✅ `parse_course_info()` → **2.45x speedup**
- ✅ `parse_prereqs()` → **2.03x speedup**
- ✅ `extract_view_state()` → Rust implementation
- ✅ `SiaScraperException` → Python exception

**Remaining:**
- None

**Technology:**
- Rust crate: `scraper` (CSS selectors)
- Replaced: `beautifulsoup4` / `lxml`
- Interop: Rust returns `PyDict` / `PyList` → Pydantic validates

### Phase 2: Business Logic & Oracle ADF ✅ COMPLETE
**Completed:** 2026-03-30

**Completed:**
- Rust-backed request dict initialization for `OracleAdfRequestBuilder`
- Rust-backed request body generation for DATA_MAP actions
- Rust-backed event dict generation (`event`, `event.*`, `PROCESS`)

**Benefits:**
- Immutable request building (no accidental mutations)
- Compile-time type checking for ADF payloads
- Faster JSON serialization

### Phase 3: Parser Completion + Fuzzing ✅ COMPLETE
**Completed:** 2026-03-30

**Completed:**
- ✅ `get_course_list()` direct Rust call path (no Python fallback)
- ✅ `get_plain_text()` direct Rust call path (no Python fallback)
- ✅ Malformed row compatibility for `<tr><span ...>` test fixture shape
- ✅ Fuzzing infrastructure (`fuzz/` + cargo-fuzz targets)
- ⏳ **IN PROGRESS:** 100% Rust test coverage (currently ~90%)

**Post-Migration Cleanup:**
See [Phase 3/4 Execution Plan](#phase-34-execution-plan) below for detailed execution steps.

### Phase 4: HTTP Client & Session Migration 🚀 HIGH PRIORITY
**Status:** Planned (execute after Phase 3 cleanup)

**Design Decisions:**
- ✅ **API Style:** Expose async methods (`async def`, requires `asyncio`)
- ✅ **Fallback Strategy:** Full Rust commitment (remove Python `requests` fallback)
- ✅ **Priority:** High (start after Phase 3 execution steps complete)
- ✅ **TLS Backend:** `rustls` (pure Rust, cross-platform)

**Goals:**
- Replace `requests` with `reqwest` (async HTTP/1.1 + HTTP/2)
- Port retry logic from `tenacity` to Rust backoff
- Convert `SiaSession` to Rust `#[pyclass]`
- Connection pooling & cookie management in Rust
- ViewState auto-synchronization in Rust
- Async Python API for high-throughput concurrent scraping

**Estimated Effort:** 19-31 hours (6 sub-phases)

**Sub-Phases:**
- **Phase 4.1:** Research & Proof of Concept (2-4 hours)
- **Phase 4.2:** Core HTTP Module Structure (4-6 hours)
- **Phase 4.3:** Session & Cookie Management (3-4 hours)
- **Phase 4.4:** Retry Logic & Error Handling (2-3 hours)
- **Phase 4.5:** Python API Integration (3-5 hours)
- **Phase 4.6:** Testing, Benchmarking & Documentation (5-9 hours)
- **Phase 4.7:** SiaScraper Async Migration ✅ COMPLETE

See [Phase 4 Detailed Breakdown](#phase-4-detailed-breakdown) for implementation details.

### Phase 5: Async & Production Polish 🚧 IN PROGRESS
**Status:** Substantially complete (PyPI publishing intentionally deferred)

**Phase 5.6 Async Cutover:** ✅ Complete

**Completed in this phase:**
- ✅ Full async support with `tokio` + `reqwest`
- ✅ Rust quality workflow in GitHub Actions (`.github/workflows/rust.yml`)
- ✅ Cross-platform wheel + sdist CI builds via maturin (`.github/workflows/build-wheels.yml`)
- ✅ Fuzz smoke CI workflow (`.github/workflows/fuzz.yml`)
- ✅ Rust extension build integration in test workflows
- ✅ Async session behavior stabilized with non-network unit tests
- ✅ Removed sync Python API remnants and promoted async API names as primary

**Deferred by scope:**
- ⏸️ PyPI publishing

---

## Phase 3/4 Execution Plan

**Purpose:** Post-migration cleanup, commit hygiene, and a concrete execution path for Phase 4.

**Last Updated:** 2026-03-30

### Step 1: Review and Commit Unstaged Changes

#### Commit 1: Documentation Enhancement
**Files:** `AGENTS.md`  
**Type:** `docs`  
**Message:** `docs: add comprehensive Rust extension development guidelines to AGENTS.md`

**Changes:**
- Added PyO3 + Maturin build commands
- Added Rust code quality standards (clippy, testing, rustdoc)
- Added error handling patterns and PyO3 best practices
- Added performance optimization guidelines and project Rust patterns

**Verification:**
```bash
ruff check .
pyright
```

#### Commit 2: Benchmark Cleanup
**Files:** `benchmarks/benchmark_parsing.py`, `benchmarks/profile_scraper.py`  
**Type:** `refactor`  
**Message:** `refactor: clean up benchmark script imports and unused variables`

**Changes:**
- Use `collections.abc.Callable` instead of `typing.Callable`
- Remove unused `result` variable in `time_function()`
- Remove unused imports (`io`, `scrape_prereqs`)
- Keep import ordering compliant with ruff/isort

**Verification:**
```bash
ruff check .
ruff format .
```

#### Commit 3: Rust Error Enhancement
**Files:** `rust/src/error.rs`  
**Type:** `feat`  
**Message:** `feat: enhance Rust error types with detailed variants and documentation`

**Changes:**
- Add module-level rustdoc documentation
- Add `MissingElement { element, selector }`
- Add `ParseFieldError { field, value }`
- Add rustdoc comments to `SiaScraperError` variants
- Remove unused `pyo3::prelude::*` import

**Verification:**
```bash
cargo clippy --manifest-path Cargo.toml
```

#### Commit 4: Pyright Configuration
**Files:** `pyrightconfig.json`  
**Type:** `config`  
**Message:** `config: exclude benchmarks and Rust parity tests from pyright checking`

**Changes:**
- Add `"exclude": ["benchmarks", "tests/test_rust_parity.py"]`
- Keeps strict typing focused on production modules

**Verification:**
```bash
pyright
```

#### Step 1 Exit Criteria
- Four logical commits created with clean commit messages
- All relevant checks pass (`ruff`, `pyright`, `clippy`, `pytest`, `cargo test`)

### Step 2: Push to Remote Repository

**Pre-Push Checklist:**
- Clean working tree (`git status`)
- All checks passing
- Branch is `feat/rust-migration`

**Command:**
```bash
git push origin feat/rust-migration
```

**Expected Result:**
- Branch updates are available on `origin/feat/rust-migration`
- Pull request creation is deferred until all requested work is complete

### Step 3: Achieve 100% Rust Coverage (Deferred)

**Status:** Deferred by request. Execute later.

**Current Baseline:**
- ~89.68% regions (excluding FFI glue in `rust/src/lib.rs` and `rust/src/error.rs`)

**Future Goal:**
- 100% line/region/function coverage on Rust parser modules

**Performance Guardrail:**
- Acceptable regression threshold: <=5%
- Preferred regression threshold: <=2% where possible

### Step 4: Code Quality Improvements (Next Execution Steps)

**Status:** Planned (execute in order below)

**Objective:** Implement every improvement identified in the code quality review before major Phase 4 transport-layer changes.

**Execution Rule:** Complete all high-priority items first, then medium-priority items, then low-priority cleanup.

**Estimated Effort:** 49-64 hours total

#### Step 4.0: Program-Level Exit Criteria
- No `.unwrap()`/`.expect()` in non-test Rust code paths
- `session.py` reduced in responsibility (coordinator role only)
- Batch scraping supports `skip`/`retry`/`abort` error strategies
- Type-checking remains clean (`pyright`)
- Linting remains clean (`ruff`, `clippy`)
- Test suite expanded for edge cases and failure-recovery scenarios

---

#### High Priority Improvements (Execute First)

##### CQ-H1: Refactor `SiaSession` into focused components
**Category:** Refactoring  
**Severity:** High  
**Estimate:** 6-8 hours

**Goal:** Decompose `src/sia_scraper/session.py` (large multi-responsibility class) into small cohesive units.

**Implementation Plan:**
1. Create `src/sia_scraper/core/adf_state_manager.py` to own ViewState/Window-Id/Page-Id synchronization and validation.
2. Create `src/sia_scraper/core/navigation_controller.py` to own workflow transitions (career selection, course page navigation, list navigation).
3. Keep `SiaSession` as orchestration/coordinator class that delegates to state manager + navigator.
4. Update `src/sia_scraper/scraper.py` and request-builder integration points to use delegation, not direct state mutation.
5. Preserve backward compatibility by keeping stable public methods and forwarding internally.

**Verification:**
- `pytest tests/test_session.py -v`
- `pytest tests/core -v`
- `pyright`

**Exit Criteria:**
- `SiaSession` handles orchestration only.
- New components have dedicated tests.

##### CQ-H2: Add resilient batch scraping error handling
**Category:** Robustness  
**Severity:** High  
**Estimate:** 3-4 hours

**Goal:** Prevent one course failure from aborting full batch operations.

**Implementation Plan:**
1. Refactor `scrape_courses()` to support `on_error` modes: `skip`, `retry`, `abort`.
2. Add `ScrapeResult` return model with `successes`, `failures`, `total`, `success_rate`.
3. Add retry controls (`max_retries`, `retry_delay`) for transient errors.
4. Add optional progress callback for long-running batch jobs.
5. Keep compatibility path for consumers expecting previous behavior.

**Verification:**
- `pytest tests/test_scraper.py -k "scrape_courses" -v`
- Failure scenario integration tests for partial-success behavior.

**Exit Criteria:**
- Partial results are returned for `skip` and `retry` modes.
- `abort` mode preserves strict fail-fast behavior.

##### CQ-H3: Eliminate Rust panics in production paths
**Category:** Rust Safety  
**Severity:** High  
**Estimate:** 4-5 hours

**Goal:** Replace panic-prone `.unwrap()`/`.expect()` usage in production Rust with typed error propagation.

**Implementation Plan:**
1. Audit all non-test `.unwrap()`/`.expect()` uses in `rust/src/**`.
2. Replace with `ok_or_else(...)`/`map_err(...)` and `?` propagation.
3. Ensure parser helper functions return `Result<T, SiaScraperError>` where fallible.
4. Improve selector/data-access errors with structured variants (`MissingElement`, `ParseFieldError`, etc.).
5. Add tests for invalid selectors, missing nodes, and malformed numeric fields.

**Verification:**
- `cargo test --manifest-path Cargo.toml`
- `cargo clippy --manifest-path Cargo.toml`
- `rg "\.unwrap\(\)|\.expect\(" rust/src --type rust` (non-test review)

**Exit Criteria:**
- No panic-based extraction in production Rust modules.
- All failures are explicit `Result` errors.

---

#### Medium Priority Improvements (Execute After High)

##### CQ-M1: Replace imprecise `Any` return types with concrete types
**Category:** Type Safety  
**Severity:** Medium  
**Estimate:** 2-3 hours

**Implementation Plan:**
1. Audit `-> Any` signatures in `src/sia_scraper/session.py`, `src/sia_scraper/scraper.py`, and `src/sia_scraper/core/*.py`.
2. Replace with concrete types (`requests.Response`, `CourseInfo`, `list[CourseInfo]`, etc.).
3. Where dynamic return is unavoidable, add inline justification comments.

**Verification:**
- `pyright`
- `rg "-> Any" src/sia_scraper --type py`

##### CQ-M2: Remove unnecessary Rust cloning in request builder hot paths
**Category:** Performance  
**Severity:** Medium  
**Estimate:** 2-3 hours

**Implementation Plan:**
1. Refactor `rust/src/parsers/adf_request.rs` to mutate builder state in place.
2. Return references where possible (`&HashMap`) and clone only at FFI boundaries when required.
3. Re-run request payload parity tests to guarantee no behavioral change.

**Verification:**
- `cargo test --manifest-path Cargo.toml`
- `pytest tests/test_rust_parity.py -v`

##### CQ-M3: Add property-based tests to prevent parser panic regressions
**Category:** Testing  
**Severity:** Medium  
**Estimate:** 3-4 hours

**Implementation Plan:**
1. Add `proptest` to Rust dev dependencies.
2. Create property tests for `parse_course_info`, `parse_prereqs`, `get_course_list`, `extract_view_state`, and ADF body builders.
3. Assert behavior is always `Ok` or structured `Err`, never panic.
4. Add CI-friendly case count defaults + optional high-case stress profile.

**Verification:**
- `cargo test --manifest-path Cargo.toml property`
- `PROPTEST_CASES=10000 cargo test --manifest-path Cargo.toml`

##### CQ-M4: Introduce `AdfContext` value object to reduce coupling
**Category:** Architecture  
**Severity:** Medium  
**Estimate:** 2-3 hours

**Implementation Plan:**
1. Add immutable `AdfContext` dataclass in `src/sia_scraper/core/adf_context.py`.
2. Update `OracleAdfRequestBuilder` to consume context object rather than session internals.
3. Add conversion helper (`AdfContext.from_session(...)`) and validation method.

**Verification:**
- `pytest tests/core -k adf_context -v`
- `pyright`

##### CQ-M5: Standardize error handling patterns across Python and Rust
**Category:** Error Handling  
**Severity:** Medium  
**Estimate:** 2-3 hours

**Implementation Plan:**
1. Replace broad Python `except Exception` usage with specific exception classes.
2. Align Rust fallible helpers to `Result<T, SiaScraperError>` where failures are meaningful.
3. Document error taxonomy and propagation policy in module docstrings.

**Verification:**
- `rg "except Exception" src tests --type py`
- `cargo clippy --manifest-path Cargo.toml`

##### CQ-M6: Expand integration tests for failure and recovery flows
**Category:** Testing  
**Severity:** Medium  
**Estimate:** 3-4 hours

**Implementation Plan:**
1. Add tests for session timeout recovery, intermittent network failure, and ADF state drift.
2. Add assertions for ViewState synchronization after partial failures.
3. Add long-batch scenarios validating resilience behavior and metrics.

**Verification:**
- `pytest tests/test_integration.py -v`
- `pytest tests -k "timeout or retry or viewstate" -v`

##### CQ-M7: Cache Rust CSS selectors for repeated parser queries
**Category:** Performance  
**Severity:** Medium  
**Estimate:** 1-2 hours

**Implementation Plan:**
1. Introduce static selector cache (`once_cell`/`LazyLock`) for hot selectors.
2. Replace repeated `Selector::parse(...)` in parser loops.
3. Benchmark parser throughput before/after.

**Verification:**
- `cargo test --manifest-path Cargo.toml`
- `python benchmarks/benchmark_parsing.py`

---

#### Low Priority Improvements (Execute After Medium)

##### CQ-L1: Centralize default literals (e.g., `"Unknown"`)
**Category:** Code Quality  
**Severity:** Low  
**Estimate:** 1 hour

**Implementation Plan:**
1. Create `src/sia_scraper/constants/defaults.py`.
2. Replace repeated literals with shared constants.
3. Update parsers/models to import constants.

**Verification:**
- `rg '"Unknown"' src/sia_scraper --type py`

##### CQ-L2: Align Python/Rust index constants to avoid divergence
**Category:** Consistency  
**Severity:** Low  
**Estimate:** 1 hour

**Implementation Plan:**
1. Document source-of-truth for group/index constants.
2. Add parity test that validates Rust and Python constant values match.

**Verification:**
- New parity test in `tests/test_rust_parity.py`

##### CQ-L3: Remove duplicated text-extraction helpers in Rust
**Category:** Refactoring  
**Severity:** Low  
**Estimate:** 1 hour

**Implementation Plan:**
1. Create shared helper module under `rust/src/parsers/utils.rs` (or equivalent).
2. Replace duplicate `extract_text_from_elem` implementations.

**Verification:**
- `cargo test --manifest-path Cargo.toml`

##### CQ-L4: Decompose deeply nested `extract_group` logic
**Category:** Refactoring  
**Severity:** Low  
**Estimate:** 2 hours

**Implementation Plan:**
1. Split group-name extraction, field extraction, and output construction into separate functions.
2. Keep each function focused and independently testable.

**Verification:**
- `cargo test --manifest-path Cargo.toml test_course_parser`

##### CQ-L5: Replace long parameter lists with context structs
**Category:** Refactoring  
**Severity:** Low  
**Estimate:** 1.5 hours

**Implementation Plan:**
1. Introduce request context structs in Rust and Python where 4+ correlated parameters repeat.
2. Update call sites and tests.

**Verification:**
- `cargo test --manifest-path Cargo.toml`
- `pyright`

##### CQ-L6: Add `#[inline]` to tiny hot-path Rust helpers
**Category:** Performance  
**Severity:** Low  
**Estimate:** 1 hour

**Implementation Plan:**
1. Identify short, frequently called parser helpers.
2. Add `#[inline]` where beneficial and non-noisy.

**Verification:**
- `cargo clippy --manifest-path Cargo.toml`

##### CQ-L7: Introduce safe helper for repetitive `PyDict` construction
**Category:** Rust Interop  
**Severity:** Low  
**Estimate:** 1.5 hours

**Implementation Plan:**
1. Add helper function/macro that inserts keys with checked `set_item` calls.
2. Replace ad hoc patterns ignoring insertion results.

**Verification:**
- `cargo test --manifest-path Cargo.toml`

##### CQ-L8: Preserve source error context in Rust conversions
**Category:** Error Handling  
**Severity:** Low  
**Estimate:** 1 hour

**Implementation Plan:**
1. Prefer `#[from]` variants where appropriate in `SiaScraperError`.
2. Keep root-cause context instead of flattening to string-only messages.

**Verification:**
- `cargo test --manifest-path Cargo.toml`
- Error mapping tests pass

##### CQ-L9: Simplify explicit lifetimes where elision is clearer
**Category:** Readability  
**Severity:** Low  
**Estimate:** 30 minutes

**Implementation Plan:**
1. Review parser helpers for redundant explicit lifetimes.
2. Apply elision where readability improves without ambiguity.

**Verification:**
- `cargo clippy --manifest-path Cargo.toml`

##### CQ-L10: Evaluate `const fn` opportunities in Rust initialization paths
**Category:** Performance  
**Severity:** Low  
**Estimate:** 1 hour

**Implementation Plan:**
1. Audit constant initialization in parser/request modules.
2. Convert applicable runtime-initialized helpers to compile-time where practical.

**Verification:**
- `cargo test --manifest-path Cargo.toml`

##### CQ-L11: Reduce redundant string allocations in Rust text extraction
**Category:** Performance  
**Severity:** Low  
**Estimate:** 1 hour

**Implementation Plan:**
1. Review trim/collect/to_string chains in parser helpers.
2. Use allocation-minimizing extraction patterns while preserving output parity.

**Verification:**
- `cargo test --manifest-path Cargo.toml`
- benchmark comparison in `benchmarks/benchmark_parsing.py`

##### CQ-L12: Precompile and standardize ViewState regex usage
**Category:** Performance  
**Severity:** Low  
**Estimate:** 30 minutes

**Implementation Plan:**
1. Ensure regex is compiled once and reused in all Python extraction paths.
2. Keep fallback behavior unchanged.

**Verification:**
- `pytest tests -k view_state -v`

##### CQ-L13: Apply `frozen=True`/`slots=True` selectively to dataclasses
**Category:** Python Quality  
**Severity:** Low  
**Estimate:** 1 hour

**Implementation Plan:**
1. Review data-holder dataclasses for immutability suitability.
2. Add `frozen=True` and `slots=True` where mutation is not required.

**Verification:**
- `pyright`
- dataclass-focused unit tests

##### CQ-L14: Add context-manager support for scraper/session lifecycle
**Category:** API Ergonomics  
**Severity:** Low  
**Estimate:** 1 hour

**Implementation Plan:**
1. Implement `__enter__`/`__exit__` on high-level scraper/session objects.
2. Guarantee deterministic `close_session()` behavior.

**Verification:**
- new tests validating cleanup on success and exception

##### CQ-L15: Convert simple list-building loops to comprehensions
**Category:** Python Readability  
**Severity:** Low  
**Estimate:** 30 minutes

**Implementation Plan:**
1. Refactor straightforward accumulation loops in `scraper.py` and parsers.
2. Keep side-effect-heavy loops unchanged.

**Verification:**
- `ruff check .`
- `pytest tests/test_scraper.py -v`

##### CQ-L16: Reduce brittle index-based test assumptions
**Category:** Testing  
**Severity:** Low  
**Estimate:** 1 hour

**Implementation Plan:**
1. Replace hard-coded index assumptions with fixture-driven lookups by course code/name where possible.
2. Keep index tests only where index semantics are the explicit subject.

**Verification:**
- `pytest tests/test_scraper.py tests/test_session.py -v`

##### CQ-L17: Add reusable fixture factories
**Category:** Testing  
**Severity:** Low  
**Estimate:** 2 hours

**Implementation Plan:**
1. Add `tests/fixtures/factories.py` for session/course payload builders.
2. Migrate repetitive fixture setup from individual tests.

**Verification:**
- `pytest tests -v`

##### CQ-L18: Add additional malformed-input edge-case tests
**Category:** Testing  
**Severity:** Low  
**Estimate:** 1.5 hours

**Implementation Plan:**
1. Add malformed schedule, missing-attribute, empty-node, and unicode-heavy parser tests.
2. Cover both Rust and Python wrappers for parity.

**Verification:**
- `cargo test --manifest-path Cargo.toml`
- `pytest tests/test_rust_parity.py -v`

##### CQ-L19: Improve ViewState synchronization observability
**Category:** Debuggability  
**Severity:** Low  
**Estimate:** 30 minutes

**Implementation Plan:**
1. Add explicit debug events for ViewState updated/unchanged states.
2. Ensure logs are gated by debug mode to avoid noise.

**Verification:**
- debug log tests or manual debug run

##### CQ-L20: Add Rust module-level examples in rustdoc
**Category:** Documentation  
**Severity:** Low  
**Estimate:** 2 hours

**Implementation Plan:**
1. Add `//!` module examples for parser modules.
2. Keep examples concise and aligned with exposed API.

**Verification:**
- `cargo test --manifest-path Cargo.toml --doc`

##### CQ-L21: Add migration status matrix document
**Category:** Documentation  
**Severity:** Low  
**Estimate:** 1 hour

**Implementation Plan:**
1. Create `docs/migration_status.md` with Python vs Rust coverage table.
2. Include parity status and performance notes.

**Verification:**
- markdown lint/manual review

##### CQ-L22: Replace residual generic exception catches in tests where meaningful
**Category:** Testing Hygiene  
**Severity:** Low  
**Estimate:** 45 minutes

**Implementation Plan:**
1. Replace broad catches with targeted exceptions where test intent allows.
2. Keep broad catches only where explicitly validating unknown failure boundaries.

**Verification:**
- `rg "except Exception" tests --type py`

##### CQ-L23: Formalize mutable-default-argument guardrail
**Category:** Preventive Quality  
**Severity:** Low  
**Estimate:** 30 minutes

**Implementation Plan:**
1. Add guideline in `AGENTS.md` and test-style docs to keep using `default_factory`/`None` patterns.
2. Add review checklist item in migration execution notes.

**Verification:**
- doc review

##### CQ-L24: Automate hygiene checks for imports/dead code
**Category:** Tooling  
**Severity:** Low  
**Estimate:** 30 minutes

**Implementation Plan:**
1. Ensure `ruff check --fix . && ruff format . && ruff check .` is documented and used in pre-merge flow.
2. Add local verification block in migration plan and PR template if applicable.

**Verification:**
- `ruff check .`

##### CQ-L25: Update release-facing docs after structural changes
**Category:** Documentation  
**Severity:** Low  
**Estimate:** 1 hour

**Implementation Plan:**
1. Update `README.md`, `CHANGELOG.md`, and `AGENTS.md` to reflect architecture/refactor outcomes.
2. Reference new batch-resilience behavior and session component split.

**Verification:**
- manual docs consistency pass

---

#### Step 4 Suggested Execution Batches

##### Batch A (High Priority, blocking)
- CQ-H1, CQ-H2, CQ-H3

##### Batch B (Medium Priority, strongly recommended before Phase 4)
- CQ-M1, CQ-M2, CQ-M3, CQ-M4, CQ-M5, CQ-M6, CQ-M7

##### Batch C (Low Priority, cleanup and hardening)
- CQ-L1 through CQ-L25

#### Step 4 Global Verification Gate
Run after each batch and before starting Phase 4:

```bash
ruff check . && ruff format . && ruff check .
pyright
pytest
cargo test --manifest-path Cargo.toml
cargo clippy --manifest-path Cargo.toml
```

#### Step 4 Completion Criteria
- All CQ-H and CQ-M items completed
- At least 80% of CQ-L items completed (or explicitly deferred with rationale)
- No critical regressions in parser correctness or performance
- Migration plan and status docs updated to reflect completion

## Phase 4 Detailed Breakdown

### Phase 4.1: Research & Proof of Concept
**Duration:** 2-4 hours

**Tasks:**
- Validate `pyo3-asyncio` integration patterns
- Build async `reqwest` PoC callable from Python
- Verify Rust async error propagation to Python exceptions

**Deliverable:**
- Working async PoC with documented learnings and constraints

### Phase 4.2: Core HTTP Module Structure
**Duration:** 4-6 hours

**Tasks:**
- Create `rust/src/http/` module skeleton (`mod.rs`, `client.rs`, `errors.rs`, `types.rs`)
- Add `reqwest`, `tokio`, and `pyo3-asyncio` dependencies
- Implement `HttpClient` wrapper for async GET/POST

**Deliverable:**
- Compilable core async HTTP layer with unit tests

### Phase 4.3: Session & Cookie Management
**Duration:** 3-4 hours

**Tasks:**
- Implement `SiaSession` as Rust `#[pyclass]`
- Add cookie jar persistence and request state handling
- Integrate ViewState extraction and synchronization

**Deliverable:**
- Rust-backed stateful session object exposed to Python

### Phase 4.4: Retry Logic & Error Handling
**Duration:** 2-3 hours

**Tasks:**
- Port retry behavior from `tenacity` to Rust backoff strategy
- Map `reqwest` failures to project-specific errors
- Ensure retry rules distinguish transient vs non-transient failures

**Deliverable:**
- Deterministic retry and robust error mapping for async requests

### Phase 4.5: Python API Integration
**Duration:** 3-5 hours

**Tasks:**
- Update `src/sia_scraper/session.py` and `src/sia_scraper/scraper.py` to async usage
- Expose async public methods with maintained type hints
- Keep parser orchestration stable while swapping transport layer

**Deliverable:**
- Async-first Python API backed by Rust HTTP/session internals

### Phase 4.6: Testing, Benchmarking & Documentation
**Duration:** 5-9 hours

**Tasks:**
- Add async integration tests (Rust + Python)
- Add HTTP throughput benchmarks against prior sync baseline
- Keep performance regressions <=5% (target <=2%)
- Update docs and publish migration guide

**Deliverables:**
- Updated `README.md`, `CHANGELOG.md`, and `AGENTS.md`
- New migration guide: `docs/MIGRATION_v2.md`

### Phase 4.7: SiaScraper Async Migration
**Status:** ✅ Complete

**Purpose:** Migrate the high-level `SiaScraper` facade to async API.

**Completed:**
- Added async facade in `src/sia_scraper/scraper.py`
- Added async public methods for course info, prereqs, career setup, and batch scraping
- Added async factory helpers: `init_sia_scraper()` and `create_career_session()`
- Added dedicated async scraper tests in `tests/test_scraper.py`
- Removed sync API remnants in Phase 5.6

**Deliverables:**
- Full async public API via `SiaScraper`
- Async factory helpers exported from package root
- Updated async test coverage for scraper facade

### Pull Request Timing
- PR creation happens after Step 1 and Step 2 are complete, and after deferred items are either completed or explicitly scoped out.

## Development Guidelines

### Rust Code Standards
1. **Unit Tests Required:** Every function has `#[test]` block
2. **No Panics:** Use `Result<T, SiaScraperError>`, map to `PyErr`
3. **100% Coverage:** Measured with `cargo tarpaulin`
4. **Clippy Clean:** Zero warnings (`cargo clippy`)
5. **Documentation:** Rustdoc comments for all public functions

### Error Handling
```rust
// ✅ Correct: Return Result
pub fn parse(html: &str) -> Result<Data, SiaScraperError> { }

// ❌ Wrong: Panic crashes Python
pub fn parse(html: &str) -> Data {
    html.parse().unwrap()  // NO!
}
```

### Python Integration
- **Option A:** Direct Rust calls (fail on error, no fallback)
- Keep Python wrappers for type hints and IDE support
- Pydantic validation at Python boundary

## Performance Benchmarks

### Current Results
| Function | Python | Rust | Speedup | Status |
|----------|--------|------|---------|--------|
| `parse_course_info` | 8.34ms | 3.40ms | **2.45x** | ✅ |
| `parse_prereqs` | 0.97ms | 0.48ms | **2.03x** | ✅ |
| `extract_view_state` | 0.091ms | 4.196ms | **0.02x** | ✅ |
| `get_course_list` | 8.004ms | 4.954ms | **1.62x** | ✅ |
| `get_plain_text` | 2.820ms | 2.060ms | **1.37x** | ✅ |

### Overall Impact
- **Session time reduction:** 30-50% (estimated)
- **Scalability:** Better performance with large course catalogs (100+ courses)

## CI/CD: GitHub Actions + Maturin

**Status:** Implemented in Phase 5 (PyPI publishing deferred)

### Planned Wheel Building
```yaml
- uses: PyO3/maturin-action@v1
  with:
    args: --release --out dist
    manylinux: auto
```

### Supported Platforms
- ✅ Linux: x86_64, aarch64
- ✅ macOS: x86_64, arm64 (M1/M2)
- ✅ Windows: x86_64

### Distribution
- **CI artifacts:** Precompiled wheels + source distribution generated on GitHub Actions
- **PyPI:** Deferred
- **Fallback:** Source distribution (requires Rust toolchain)

## Testing Strategy

### Rust Tests
```bash
cargo test                          # Run unit tests
cargo tarpaulin --out Html          # Coverage report
cargo clippy                        # Linter
cargo fuzz run --manifest-path fuzz/Cargo.toml fuzz_get_course_list
cargo fuzz run --manifest-path fuzz/Cargo.toml fuzz_get_plain_text
cargo fuzz run --manifest-path fuzz/Cargo.toml fuzz_extract_view_state
```

### Python Tests
```bash
pytest --cov=src/sia_scraper       # Integration tests
pyright                             # Type checking
ruff check .                        # Linting
```

### Parity Tests
- `tests/test_rust_parity.py` compares Rust vs Python outputs
- Ensures exact match on real fixtures
- Catches regressions during migration

## Migration Checklist

### Phase 1 (HTML Parsers)
- [x] `parse_course_info()`
- [x] `parse_prereqs()`
- [x] `extract_view_state()`
- [x] `get_course_list()`
- [x] `get_plain_text()`

### Phase 2 (Oracle ADF)
- [x] Rust-backed `OracleAdfRequestBuilder` payload generation
- [x] Rust-backed event dict generation
- [x] ViewState extraction optimization

### Phase 3 (HTML Parsers Complete)
- [x] `get_course_list()` implementation
- [x] `get_plain_text()` implementation
- [x] Fuzz testing setup
- [ ] 100% Rust test coverage
- [x] Documentation updates

### Phase 4 (HTTP Client Migration)
- [x] `reqwest` integration (async)
- [x] Retry logic port
- [x] `SiaSession` async Python integration
- [x] CI/CD with maturin-action
- [ ] PyPI publishing

### Phase 5 (Async & Production Polish)
- [x] Rust CI quality workflow (`cargo clippy` + Rust lib tests)
- [x] Cross-platform wheel and sdist builds in CI
- [x] Fuzz smoke CI workflow (`cargo fuzz` quick runs)
- [x] Async workflow hardening + test stabilization
- [x] Phase 5.6 async-only API cutover (remove sync remnants)
- [ ] PyPI publishing

## Timeline

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 0 | Build infrastructure | ✅ Complete |
| Phase 1 | HTML parsers | ✅ Complete |
| Phase 2 | Oracle ADF logic | ✅ Complete |
| Phase 3 | Parser completion + fuzzing | ✅ Complete |
| Phase 4 | HTTP client (async) | ✅ Complete |
| Phase 5 | Async + production polish | 🚧 In Progress (PyPI deferred) |

## Breaking Changes

Version 1.1.0 will include breaking changes:

- **Option A (strict):** Direct Rust calls, no Python fallback
- **API Changes:** Possible minor changes when `SiaSession` migrates to Rust
- **Deprecation:** Python-only implementations will be deprecated but remain functional

## References
- [PyO3 User Guide](https://pyo3.rs/)
- [Maturin Documentation](https://www.maturin.rs/)
- [scraper crate](https://docs.rs/scraper/)
- [AGENTS.md](./AGENTS.md) - Rust code standards
