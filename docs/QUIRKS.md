# Oracle ADF Quirks

This document captures Oracle ADF behavior we have observed while scraping SIA,
plus how the library currently handles each case.

## 1) ViewState changes after POST (critical)

Oracle ADF rotates `javax.faces.ViewState` after state-changing requests. Reusing
an older token can make the server apply actions against stale component state.

### Symptom

- wrong course detail payload for a selected row
- inconsistent table behavior after multiple POST calls

### How we manage it

- ViewState is extracted from every POST response and immediately stored.
- Request body generation happens per-step so each POST uses the latest ViewState.

### Implementation note

In v2.0+, ViewState synchronization is handled in Rust HTTP/session code. The
Python layer no longer performs manual request posting for this workflow.

## 2) Strict action order in dependent dropdowns

SIA's Oracle ADF flow requires selecting filters in sequence. Sending only the
final target value (career or typology) is not enough.

### Required sequence

`STUDY_LEVEL_DD -> CAMPUS_DD -> FACULTY_DD -> CAREER_DD -> TIPOLOGY_DD -> SHOW_COURSES_BTTN`

Electives include additional steps before show.

### How we manage it

- We execute a full action sequence in `set_career()`.
- Each step sends its own event payload and receives fresh state.

### Implementation note

The action sequence is executed by the Rust-backed session implementation,
maintaining parity with the observed Oracle ADF workflow.

## 3) Token trio required in every POST

Most ADF interactions require:

- `Adf-Window-Id`
- `Adf-Page-Id`
- `javax.faces.ViewState`

### How we manage it

- Tokens are captured on session initialization.
- The request builder injects them into each request body.

### Implementation note

Token propagation is now centralized in Rust session/request code.

## 4) Table row selection needs DELTAS metadata

Selecting a course row is not only about event name; ADF expects a matching
`oracle.adf.view.rich.DELTAS` payload describing table viewport and row state.

### How we manage it

- DELTAS is built dynamically from current course list size.
- `selectedRowKeys` is set to the requested course index.

### Implementation note

DELTAS construction is handled in Rust request-building logic used by the async flow.

## 5) Component IDs are brittle

ADF IDs are tied to rendered component structure (for example `pt1:r1:0:soc2`).
Changes in SIA frontend structure can break scraping flows.

### How we manage it

- IDs are centralized in constants modules.
- Integration tests exercise real requests against SIA.

## Historical note: index 0/1 swap observation

We previously documented apparent index `0/1` swapping during course detail
navigation. After implementing ViewState auto-sync, that behavior stopped
reproducing consistently and is currently treated as state-drift related.

## Operational guidance

- Keep `post_request()` as the only place where ViewState sync is guaranteed.
- Avoid precomputing long request chains with a single stale request dictionary.
- If scraping starts returning mismatched rows, verify ViewState and DELTAS first.

## Module locations (v2.0+)

Current implementation modules:

- `src/sia_scraper/core/adf_state.py`
- `src/sia_scraper/core/exceptions.py`
- `rust/src/http/sia_session.rs`
- `rust/src/parsers/adf_request.rs`

Historical sync implementation details are archived in
`docs/SYNC_API_REFERENCE.md`.
