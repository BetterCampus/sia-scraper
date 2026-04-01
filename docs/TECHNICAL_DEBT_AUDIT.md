# Technical Debt Audit (Rust + Python)

Date: 2026-03-31

This audit identifies technical debt that is both real and actionable before opening a dedicated "Technical Debt" PR.

## Scope and method

- Reviewed Rust session/HTTP/parser modules, Python wrappers/constants/parsers, and fixture contracts.
- Verified claims using direct code evidence and fixture-based tests.
- Focused on debt with operational impact (correctness, observability, maintainability), not style-only preferences.

## Executive conclusions

- The most important debt is in Rust session transport/state handling, not parser algorithm redesign.
- Some reviewer concerns are valid and high-value to fix now:
  - silent fallbacks (`unwrap_or_default`) in critical request/state paths,
  - duplicated SIA URL/header/action constants across Rust and Python,
  - stringly-typed `course_list_json` stored in a generic params map.
- Parser index fragility is real in both languages, but a full selector-strategy rewrite is medium/high risk and should be incremental.
- Python currently has no explicit concurrency guard in `SiaSession`; this is acceptable for current sequential scraper flow but should be documented or guarded to prevent misuse.

## Evidence-backed findings

### 1) Critical-path silent fallbacks in Rust (high priority)

**What we observed**

- Query encoding errors are silently ignored by returning an empty query string:
  - `rust/src/http/sia_session.rs:138`
- Course list serialization/deserialization can silently drop data:
  - `rust/src/http/sia_session.rs:265`
  - `rust/src/http/sia_session.rs:283`
  - `rust/src/lib.rs:431`
  - `rust/src/lib.rs:433`

**Why this is debt**

- These are correctness-sensitive flows in session navigation and course selection.
- Silent defaults hide root causes and make flaky scraping harder to diagnose.

**Recommendation**

- Replace critical `unwrap_or_default` with explicit error propagation (`HttpError::InvalidInput` / `ParseError`) or at minimum structured logging and a hard failure for impossible states.

### 2) Stringly-typed session state (`course_list_json`) in params map (high priority)

**What we observed**

- Rust stores parsed course list as JSON string inside `SessionState.params`:
  - `rust/src/http/sia_session.rs:263`
  - `rust/src/http/sia_session.rs:264`
- Later code rehydrates from this string:
  - `rust/src/http/sia_session.rs:277`
  - `rust/src/http/sia_session.rs:283`
  - `rust/src/lib.rs:427`
  - `rust/src/lib.rs:433`

**Why this is debt**

- Data shape is erased into a generic map, then re-parsed repeatedly.
- Increases failure surface and couples unrelated parts via magic key names.

**Recommendation**

- Introduce typed field(s) on Rust `SessionState` for course list metadata/data instead of `params["course_list_json"]`.

### 3) Constant duplication and drift risk between Python and Rust (high priority)

**What we observed**

- Python centralizes HTTP constants:
  - `src/sia_scraper/constants/http.py:10`
  - `src/sia_scraper/constants/http.py:14`
- Rust hardcodes same values in multiple places:
  - base URL in `rust/src/http/sia_session.rs:446`
  - base URL in PyO3 entrypoints `rust/src/lib.rs:369`, `rust/src/lib.rs:413`, `rust/src/lib.rs:473`
  - headers in `rust/src/http/client.rs:59`, `rust/src/http/client.rs:61`
  - taskflow query in `rust/src/http/sia_session.rs:95`

**Why this is debt**

- Multiple sources of truth raise maintenance cost and break parity over time.

**Recommendation**

- Centralize Rust-side SIA constants (URL, taskflow id, required headers, ADF IDs/actions) in dedicated modules and ensure Python-facing wrappers consume those single sources.

### 4) Parser field extraction is index-order dependent in both languages (medium priority)

**What we observed**

- Python group extraction uses positional indexes from constants:
  - `src/sia_scraper/constants/business.py:17`
  - `src/sia_scraper/parsers/course_parser.py:187`
  - `src/sia_scraper/parsers/course_parser.py:201`
- Rust parser mirrors index-based extraction:
  - `rust/src/parsers/course_parser.rs:242`
  - `rust/src/parsers/course_parser.rs:254`
  - `rust/src/parsers/course_parser.rs:272`

**Fixture support**

- Fixtures confirm current Oracle ADF table structure is consistent and parseable:
  - `tests/fixtures/test_contracts.py:26`
  - `tests/fixtures/test_contracts.py:56`
  - `tests/fixtures/test_fixtures_validity.py:116`

**Why this is debt**

- Works today, but brittle to DOM order changes.

**Recommendation**

- Do incremental hardening first (guard checks, better missing-field diagnostics, fixture variance tests), then selectively move highest-risk fields to label/selector-driven extraction.

### 5) Python session wrapper lacks explicit concurrency guard (medium priority)

**What we observed**

- `SiaSession` mutates internal runtime state across async methods with no lock:
  - `src/sia_scraper/session.py:20`
  - `src/sia_scraper/session.py:75`
  - `src/sia_scraper/session.py:95`
- Status model explicitly describes sequential flow:
  - `src/sia_scraper/constants/status.py:13`
- Current high-level scraper loops sequentially:
  - `src/sia_scraper/scraper.py:134`

**Why this is debt**

- Internal usage is sequential, but API does not prevent unsafe concurrent calls by consumers.

**Recommendation**

- Either add an internal `asyncio.Lock` around mutating operations or document non-concurrency guarantees in API docs and raise a clear runtime error for overlapping operations.

## Findings to defer (or keep as-is for now)

### Manual PyO3 dict construction

- Repetitive `PyDict::set_item` patterns exist (for example `rust/src/lib.rs:381`), but this is mostly ergonomics unless coupled with measurable bottlenecks or bug patterns.
- Defer broad refactor unless touched by nearby functional changes.

### Full parser strategy rewrite

- A full migration from index-based extraction to semantic selectors across all parser paths is large and risky.
- Prefer targeted hardening + fixture expansion first.

## Proposed Technical Debt PR scope

### Phase 1 (recommended first PR)

1. Eliminate critical silent fallbacks in Rust session request/state flows.
2. Remove `course_list_json` string roundtrip from `params`; add typed session field(s).
3. Centralize Rust SIA constants (URL/taskflow/headers/action IDs where feasible).
4. Add/adjust tests for failure transparency (encoding/serialization errors should fail explicitly).

### Phase 2 (follow-up PR)

1. Add Python session concurrency guard or explicit non-concurrent contract enforcement.
2. Add parser hardening tests against slight fixture structure variation.
3. Improve parser diagnostics for missing/shifted fields.

### Phase 3 (deferred)

1. Selective parser refactor away from index assumptions for highest-risk fields.
2. Optional PyO3 response-construction cleanup if evidence shows maintainability gains.

## Suggested acceptance criteria for the Technical Debt PR

- No critical `unwrap_or_default` in request encoding / session state serialization paths.
- Rust constants used from centralized modules (no duplicated SIA base URL strings in wrappers/session/client).
- Typed session state replaces `params["course_list_json"]` flow.
- Tests verify explicit failures on malformed encode/decode paths.
- Existing parity/fixture tests continue passing.
