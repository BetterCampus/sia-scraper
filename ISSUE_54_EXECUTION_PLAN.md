# Issue #54 Execution Plan: Align get_course_list Return Shape

This document outlines the strategy for aligning the `get_course_list` return shape with an intuitive `code`/`name` contract, as requested in Issue #54. This change is part of **Phase 6: Zero-Copy Models** and aims to improve API consistency and type safety.

## Architectural Goal
Align the internal Rust representation and the public Python API for course lists. We will transition from unstructured `HashMap<String, String>` to the typed `CourseListEntryModel`, ensuring consistency across the "Thin Wrapper" boundary while fulfilling the explicit requirement for an intuitive dictionary contract in Python.

---

## Technical Standards
- **Zero Panics:** All parsing operations use `Result<T, SiaScraperError>`.
- **Type Safety:** 100% type coverage in `sia_scraper_rust.pyi` and clean `pyright` checks.
- **Documentation:** Google-Style docstrings for all updated Rust and Python methods.
- **Zero-Copy Alignment:** Internal Rust state will use `CourseListEntryModel` directly to minimize transformations.

---

## Phase 1: Rust Core Internal Refactor
**Goal:** Transition internal state from `HashMap` to typed models.

- [ ] **Task 1.1:** Update `SessionState` in `rust/src/http/session.rs`.
  - Change `course_list: Vec<HashMap<String, String>>` to `course_list: Vec<CourseListEntryModel>`.
- [ ] **Task 1.2:** Update `get_course_list` in `rust/src/parsers/table_parser.rs`.
  - Change return type to `Result<Vec<CourseListEntryModel>, SiaScraperError>`.
  - Update implementation to construct `CourseListEntryModel` instances directly during parsing.
- [ ] **Task 1.3:** Refactor `rust/src/models/session.rs`.
  - Simplify `SessionStateModel::from_session_state` and `into_session_state` by removing `flatten_course_list` and manual `HashMap` conversions.
  - Update `SessionStateModel::to_dict` and `from_dict` to use the keys `code` and `name` for the `course_list` items to maintain consistency with the new contract.

**Verification Gate:**
```bash
cargo check --manifest-path Cargo.toml
cargo test --manifest-path Cargo.toml --lib parsers::table_parser
```

---

## Phase 2: PyO3 Bridge & API Alignment
**Goal:** Implement the new Python contract and maintain backward compatibility strategy.

- [ ] **Task 2.1:** Update `get_course_list` in `rust/src/lib.rs`.
  - Modify the `#[pyfunction]` to return `list[dict[str, str]]` with keys `"code"` and `"name"`.
  - Implementation: Iterate over `Vec<CourseListEntryModel>` and construct `PyDict` with the new keys.
- [ ] **Task 2.2:** Update `CourseListEntryModel` fields (Optional but Recommended).
  - Consider renaming fields to `code` and `name` to match the dictionary keys, OR maintain `course_code`/`course_name` for internal clarity but ensure the dictionary mapping uses the new contract.
  - *Decision:* Renaming to `code`/`name` in the model as well for 100% consistency across Phase 6 models.

**Verification Gate:**
```bash
maturin develop
pytest tests/rust/test_py_session.py
```

---

## Phase 3: Documentation & Type Stubs
**Goal:** Update public-facing contracts and migration guides.

- [ ] **Task 3.1:** Update `stubs/sia_scraper_rust.pyi`.
  - Update `get_course_list` return type hint: `list[dict[str, str]]`.
  - Update example in docstring to show `[{"code": "...", "name": "..."}]`.
- [ ] **Task 3.2:** Update `CHANGELOG.md`.
  - Document the breaking change in `get_course_list` return shape.
  - Provide the "Backward Compatibility Strategy": Explain that the change is part of the 3.0.0 migration and consumers should update to the new keys.

**Verification Gate:**
```bash
pyright
ruff check .
```

---

## Phase 4: Validation & Cleanup
**Goal:** Ensure 100% compliance and no regressions.

- [ ] **Task 4.1:** Update Python Integration Tests.
  - Audit `tests/` for any usage of `get_course_list` and update assertions to the new shape.
  - Update `tests/rust/test_py_session.py`.
- [ ] **Task 4.2:** Final Quality sweep.
  - `cargo clippy` (zero warnings).
  - `ruff format .`.

**Final Verification Gate:**
```bash
cargo clippy --manifest-path Cargo.toml
cargo test --manifest-path Cargo.toml
pytest
pyright
```

---

## Summary of Changes
- **Modified Files:**
  - `rust/src/http/session.rs`: Internal state type change.
  - `rust/src/parsers/table_parser.rs`: Parser return type change.
  - `rust/src/models/session.rs`: Model simplification and key alignment.
  - `rust/src/lib.rs`: Bridge API update.
  - `stubs/sia_scraper_rust.pyi`: Type hint update.
  - `CHANGELOG.md`: Migration documentation.
