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

See [Phase 4 Detailed Breakdown](#phase-4-detailed-breakdown) for implementation details.

### Phase 5: Async & Production Polish 🔮 FUTURE
**Status:** Planned

- Full async support with `tokio` + `reqwest`
- Fuzz testing integration (`cargo fuzz`)
- GitHub Actions with maturin wheel building
- PyPI publishing

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

**Status:** Deferred to Phase 4

### Planned Wheel Building
```yaml
- uses: PyO3/maturin-action@v1
  with:
    args: --release --out dist
    manylinux: auto
```

### Supported Platforms (Future)
- ✅ Linux: x86_64, aarch64
- ✅ macOS: x86_64, arm64 (M1/M2)
- ✅ Windows: x86_64

### Distribution (Future)
- **PyPI:** Precompiled wheels
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
- [ ] `reqwest` integration (async)
- [ ] Retry logic port
- [ ] `SiaSession` as `#[pyclass]`
- [ ] CI/CD with maturin-action
- [ ] PyPI publishing

## Timeline

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 0 | Build infrastructure | ✅ Complete |
| Phase 1 | HTML parsers | ✅ Complete |
| Phase 2 | Oracle ADF logic | ✅ Complete |
| Phase 3 | Parser completion + fuzzing | ✅ Complete |
| Phase 4 | HTTP client (async) | 🚀 Planned |
| Phase 5 | Async + production polish | 🔮 Future |

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
