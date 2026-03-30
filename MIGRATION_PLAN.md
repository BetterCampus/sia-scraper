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
- `get_course_list()` direct Rust call path (no Python fallback)
- `get_plain_text()` direct Rust call path (no Python fallback)
- Malformed row compatibility for `<tr><span ...>` test fixture shape
- Fuzzing infrastructure (`fuzz/` + cargo-fuzz targets)

### Phase 4: HTTP Client & Session 🔮 FUTURE
**Status:** Deferred

**Planned:**
- Replace `requests` with `reqwest` (async-enabled)
- Port retry logic from `tenacity` to Rust
- Convert `SiaSession` to `#[pyclass]`
- Connection pooling & cookie management in Rust

**Note:** Designed async-ready for future `tokio` integration.

### Phase 5: Async & Production Polish 🔮 FUTURE
**Status:** Planned

- Full async support with `tokio` + `reqwest`
- Fuzz testing integration (`cargo fuzz`)
- GitHub Actions with maturin wheel building
- PyPI publishing

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

### Phase 4 (HTTP Client - Future)
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
| Phase 4 | HTTP client (async) | 🔮 Future |
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
