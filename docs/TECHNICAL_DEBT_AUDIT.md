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

### Phase 3 (approved implementation plan)

Goal: migrate from dictionary-shaped cross-language payloads and index-based parsing to typed models and selector-driven extraction, with strict correctness and graceful diagnostics.

#### Phase 3 engineering policy (mandatory)

- No `unwrap`, no `expect`, no panic-driven control flow in production code.
- Tests follow strict handling too: return `Result` and use `?` where possible; no `unwrap`/`expect` in tests.
- Strict parsing semantics for correctness:
  - Required fields missing/invalid -> fail parse.
  - Any group parse failure -> fail entire course parse.
  - Optional fields are represented as `None`/`Option`, not silently defaulted.
- Graceful diagnostics for operability:
  - Aggregate errors (do not stop at first error in default mode).
  - Include both HTML snippet context and propagation stack context in error output.
- Runtime mode toggle for performance/diagnostics:
  - Default: `full-error-collection` (collect all errors, rich diagnostics).
  - Optional: `fail-fast` feature (first error returns immediately).

#### Phase 3A - typed course parser + selector engine

Scope: migrate `parse_course_info`/`scrape_info` to typed contracts and selector-based extraction.

1. Typed models and contracts
   - Rust:
     - Add `rust/src/models/course.rs` with `CourseInfo`, `CourseGroup`, `Schedule`.
     - Add `rust/src/models/errors.rs` with parser error taxonomy and context metadata.
     - Ensure serde derives for cross-language serialization.
   - Python:
     - Add `src/sia_scraper/models/course.py` Pydantic models in strict mode.
     - Add validation for course code format, credits bounds, schedule fields.
     - Provide temporary `.to_dict()` compatibility helper with deprecation warning (remove after transition window).

2. Selector infrastructure with compile-time validation discipline
   - Add selector registry module (single source of selector strings).
   - Add `build.rs` validation step for selector syntax to fail build early on invalid selectors.
   - At runtime, selector creation/parsing must still use explicit `Result` handling (no panic path).
   - Add cached selector access pattern that returns `Result` (no `unwrap`/`expect`).

3. Selector-based extraction (remove index assumptions)
   - Replace positional extraction in Rust course parser with label/selector extraction utilities.
   - Implement label fallback lists for resilient matching (for example `Profesor:` and alternate labels).
   - Keep optional fields optional (`Option`/`None`) instead of defaulting to placeholders.
   - For malformed/missing required group fields: fail the whole course parse with contextual errors.

4. Error handling implementation
   - Add rich error context struct containing:
     - `html_snippet` (trimmed safe snippet around failure point),
     - `stack_context` (hierarchical propagation path).
   - Implement aggregate error type (`Multiple`/collection) for default mode.
   - Ensure all parser helpers return `Result<T, ParseError>` or `Option<T>` explicitly.
   - Remove all silent fallback calls in parser paths (`unwrap_or_default`, hidden defaults).

5. Python bridge migration
   - Update PyO3 boundary for course parse output to typed/serialized model flow.
   - Update `src/sia_scraper/parsers/course_parser.py` to return typed `CourseInfo` model.
   - Update call sites to attribute access instead of dictionary key access.

6. Testing (both strategies)
   - Property-based tests (Hypothesis): model round-trips, boundary validation, invalid payload rejection.
   - Fixture-based tests: all existing fixtures + edge fixtures parse with expected strict behavior.
   - Error diagnostics tests: verify message contains field, selector/label attempted, HTML snippet, and stack context.
   - Rust tests: use `Result` + `?`; no unwrap/expect.

7. Tooling gates
   - Add/enforce clippy policy denying unwrap/expect usage in crate code.
   - Keep `cargo clippy`, `cargo check`, `pyright`, `ruff`, `pytest` green throughout migration.

#### Phase 3B - typed prerequisite parser

Scope: apply the same typed and strict approach to `parse_prereqs`/`scrape_prereqs`.

1. Models
   - Rust: add prerequisite models (`PrerequisiteInfo`, `Condition`, related entities).
   - Python: matching strict Pydantic models in `src/sia_scraper/models/prerequisite.py`.

2. Parser refactor
   - Replace index-dependent prerequisite extraction with selector/label extraction.
   - Required prerequisite structure failures -> strict parser error.
   - Optional branches -> explicit `Option`/`None`.

3. Diagnostics parity
   - Reuse the same rich error context strategy (HTML snippet + stack context).
   - Maintain aggregate errors in default mode.

4. Tests
   - Property tests for condition combinations and invalid states.
   - Fixture tests for known prerequisite structures and edge variants.
   - Contract tests for Rust/Python parity of serialized typed outputs.

#### Phase 3C - typed session/state and boundary cleanup

Scope: remove remaining stringly/dict boundary patterns and standardize typed transport.

1. Session models
   - Rust: typed session state models for course list/session metadata.
   - Python: strict models in `src/sia_scraper/models/session.py`.

2. Bridge alignment
   - Ensure Rust->Python session payloads are typed/validated end-to-end.
   - Remove ad hoc dictionary assumptions from wrapper/scraper call sites.

3. Strict handling
   - Session/state decode or schema mismatch -> explicit error, never silent default.
   - Optional state remains explicit and typed.

4. Tests
   - Serialization/deserialization contract tests for session payloads.
   - Regression tests for previously stringly paths.

#### Phase 3D - transition hardening and cleanup

Scope: complete migration ergonomics and remove temporary compatibility scaffolding.

1. Backward-compat transition plan
   - Keep `.to_dict()` helper temporarily in typed Python models with clear deprecation warnings.
   - Document cutoff version for removal.

2. Cleanup after transition window
   - Remove deprecated dictionary compatibility paths.
   - Remove outdated docs/examples referencing dict-key parser responses.

3. Performance and mode tuning
   - Benchmark `full-error-collection` vs `fail-fast` mode.
   - Document recommended mode by environment (CI/debug/prod scraping).

4. Release readiness
   - Update migration docs with before/after examples.
   - Add changelog entries for breaking API changes and strict handling guarantees.

#### Phase 3 acceptance criteria

- Zero `unwrap` and zero `expect` in production Rust code paths.
- No unwrap/expect in tests; tests use `Result` + `?` and explicit pattern handling.
- No panic-based error handling in parser/session boundary logic.
- Course and prerequisite parsers return typed models, not ad hoc dict payloads.
- Selector-based extraction fully replaces index-order dependency in targeted Phase 3 parser paths.
- Default mode aggregates errors and includes both HTML snippet and stack context.
- Optional fail-fast mode exists and is validated by tests.
- Existing fixture/regression parity remains green.

#### Phase 3 execution tracker (living checklist)

Status legend: `not_started` | `in_progress` | `blocked` | `done`

| Workstream | Status | Branch | PR | Dependencies | Notes |
|---|---|---|---|---|---|
| 3A Typed course parser + selector engine | not_started | `phase-3a-typed-course-parser` | TBD | Phase 2 merged | First migration slice, highest impact |
| 3B Typed prerequisite parser | not_started | `phase-3b-typed-prereq-parser` | TBD | 3A merged | Reuse extractor and error infra |
| 3C Typed session/state cleanup | not_started | `phase-3c-typed-session-state` | TBD | 3B merged | Remove remaining stringly/dict boundaries |
| 3D Transition hardening and cleanup | not_started | `phase-3d-transition-cleanup` | TBD | 3C merged | Remove deprecations after transition window |

##### 3A checklist

- [ ] Create Rust typed models for course payloads (`CourseInfo`, `CourseGroup`, `Schedule`).
- [ ] Create Python strict Pydantic course models and validators.
- [ ] Add temporary `.to_dict()` compatibility helper with deprecation warning.
- [ ] Add selector registry module and `build.rs` selector validation.
- [ ] Implement cached selector access with explicit `Result` handling only.
- [ ] Replace index-based course extraction with selector/label extraction.
- [ ] Add label fallback lists for resilient matching.
- [ ] Keep optional fields as `Option`/`None`; remove hidden defaults.
- [ ] Add rich parser error context (`html_snippet`, `stack_context`).
- [ ] Add aggregate error type for default mode (`full-error-collection`).
- [ ] Add optional `fail-fast` feature path and wire mode selection.
- [ ] Update PyO3 boundary and Python parser wrappers to typed return models.
- [ ] Update all affected call sites from dict-key to attribute access.
- [ ] Add property-based tests (Hypothesis) for typed models and boundaries.
- [ ] Add fixture-based strict parsing and diagnostics assertions.
- [ ] Add clippy gates denying unwrap/expect and panic-driven handling.
- [ ] Verify `cargo check`, `cargo clippy`, `pyright`, `ruff`, `pytest` pass.

##### 3B checklist

- [ ] Create Rust typed prerequisite models (`PrerequisiteInfo`, `Condition`, related types).
- [ ] Create Python strict Pydantic prerequisite models.
- [ ] Refactor prerequisite parser to selector/label-driven extraction.
- [ ] Enforce strict failures on required prerequisite structure mismatches.
- [ ] Represent optional branches explicitly as `Option`/`None`.
- [ ] Reuse rich error diagnostics (HTML snippet + stack context).
- [ ] Keep aggregate errors in default mode and support fail-fast mode.
- [ ] Add property tests for condition combinations and invalid states.
- [ ] Add fixture and parity contract tests for Rust/Python output consistency.
- [ ] Verify quality gates (`cargo check`, `cargo clippy`, `pyright`, `ruff`, `pytest`).

##### 3C checklist

- [ ] Introduce typed Rust session state models for session metadata and course list.
- [ ] Introduce strict Python session models (`src/sia_scraper/models/session.py`).
- [ ] Align Rust->Python bridge to typed payloads end-to-end.
- [ ] Remove ad hoc dict assumptions in wrappers and scraper call sites.
- [ ] Enforce strict decode/schema mismatch handling (no silent defaults).
- [ ] Keep optional state explicit and typed.
- [ ] Add session serialization/deserialization contract tests.
- [ ] Add regressions for formerly stringly state paths.
- [ ] Verify quality gates (`cargo check`, `cargo clippy`, `pyright`, `ruff`, `pytest`).

##### 3D checklist

- [ ] Keep `.to_dict()` compatibility only for transition window with deprecation warning.
- [ ] Publish and maintain migration docs with before/after usage examples.
- [ ] Define and document deprecation cutoff version.
- [ ] Remove deprecated dict compatibility paths after cutoff.
- [ ] Remove outdated docs/examples referencing dict-key parser responses.
- [ ] Benchmark and document `full-error-collection` vs `fail-fast` trade-offs.
- [ ] Document recommended mode per environment (CI/debug/prod scraping).
- [ ] Final release notes/changelog for breaking changes and strict handling guarantees.

##### Tracking cadence

- [ ] Update this tracker at least once per PR (status, branch, PR link, blockers).
- [ ] Keep one active phase branch at a time to reduce merge complexity.
- [ ] Do not open next phase PR until current phase CI is green and reviewed.
- [ ] Record any scope change directly in this document before implementation.

## Suggested acceptance criteria for the Technical Debt PR

- No critical `unwrap_or_default` in request encoding / session state serialization paths.
- Rust constants used from centralized modules (no duplicated SIA base URL strings in wrappers/session/client).
- Typed session state replaces `params["course_list_json"]` flow.
- Tests verify explicit failures on malformed encode/decode paths.
- Existing parity/fixture tests continue passing.
