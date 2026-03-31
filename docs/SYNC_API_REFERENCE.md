# Sync API Reference (Archived)

This document preserves the Python sync-layer architecture that was removed during
the async-first Rust migration.

It is intended as historical reference for maintainers who need to understand
legacy behavior, request flow assumptions, and previous public interfaces.

## Removed Modules

### `src/sia_scraper/session.py`

Legacy sync `SiaSession` implementation backed by `requests`.

Responsibilities:
- Initialize and hold HTTP session state.
- Manage Oracle ADF tokens (`ViewState`, `Adf-Window-Id`, `Adf-Page-Id`).
- Build request payloads for ADF interactions.
- Navigate career/course pages and retrieve course XML.
- Serialize/restore session data.

Main public methods:
- `init_session()`
- `set_career(search_code: str, electives: bool = False)`
- `get_course_xml(course_index: int)`
- `enter_course_page(course_index: int)`
- `exit_course_page()`
- `get_current_xml()`
- `get_session_data()`
- `load_session(session_data)`
- `close_session()`

### `src/sia_scraper/core/enhanced_session.py`

`EnhancedSession(requests.Session)` wrapper.

Responsibilities:
- Provide a default timeout for all HTTP requests.
- Expose a familiar `requests.Session` interface with timeout injection.

### `src/sia_scraper/core/navigation_controller.py`

Legacy sync navigation orchestrator.

Responsibilities:
- Execute dependent dropdown action sequence for career selection.
- Select row, enter/exit course page, and fetch course XML.
- Track `career_code`, `career_name`, `is_electives`, and `course_list`.

Main public methods:
- `set_career(search_code: str, electives: bool, session)`
- `select_course_row(course_index: int, session)`
- `enter_course_page(course_index: int, session)`
- `exit_course_page(session)`
- `get_course_xml(course_index: int, session)`
- `update_course_list_from_xml(xml: str)`
- `restore_from_session_data(session_data: dict[str, Any])`

### `src/sia_scraper/core/adf_state_manager.py`

Legacy Oracle ADF token lifecycle helper.

Responsibilities:
- Initialize/sync ViewState and ADF window/page IDs.
- Build request dict fragments from internal token state.
- Snapshot and restore state from serialized session data.

Main public APIs:
- `AdfState` frozen dataclass (`view_state`, `window_id`, `page_id`)
- `AdfStateManager.initialize_from_html(...)`
- `AdfStateManager.sync_from_response(...)`
- `AdfStateManager.sync_from_html(...)`
- `AdfStateManager.get_state_snapshot()`
- `AdfStateManager.restore_from_session_data(...)`
- `AdfStateManager.build_request_dict()`

### `src/sia_scraper/core/adf_context.py`

Legacy immutable request context value object.

Responsibilities:
- Carry state required by request-building routines.
- Provide validated accessors for `window_id`, `page_id`, `view_state`, and
  `career_indices`.

Main public APIs:
- `AdfContext` frozen dataclass
- `AdfContext.from_session(...)`
- `AdfContext.with_updated_view_state(...)`
- `AdfContext.validate()` and validated getters

### `src/sia_scraper/core/oracle_adf_request.py`

Legacy Python request-body builder used by sync workflow.

Responsibilities:
- Build Oracle ADF request dict and event dict payloads.
- Handle special dropdown index rules for faculty/electives flows.
- Bridge to Rust helper functions for payload construction in later migration stages.

Main public APIs:
- `OracleAdfRequestBuilder.init_request_dict()`
- `OracleAdfRequestBuilder.build_request_body(data_name: str, idx: int = -1)`

### `src/sia_scraper/utils/decorators.py`

Legacy sync decorators and retry wrappers.

Responsibilities:
- Guard method execution on active session/status.
- Wrap network operations with timeout mapping and retry behavior.

Main public APIs:
- `check_session`
- `check_status`
- `handle_timeout_error`
- `handle_timeout_with_retry`

## Why These Were Removed

The async-first Rust stack (`reqwest` + `tokio`, exposed via PyO3) now owns:
- HTTP transport
- retry logic
- Oracle ADF state synchronization
- career and course-page navigation workflow

Keeping duplicate sync Python orchestration increased maintenance cost and
invited behavior drift between Python and Rust flows.

The current primary API is async and Rust-backed.
