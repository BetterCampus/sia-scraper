"""SIA Session Management Module.

This module provides the core session management layer for interacting with
Universidad Nacional de Colombia's SIA (Sistema de Información Académica) system,
which is built on Oracle Application Development Framework (ADF).

The SiaSession class handles:
- HTTP session lifecycle with Oracle ADF backend
- State management (ViewState, Window-Id, Page-Id) required by Oracle ADF
- Navigation through SIA's multi-page workflow (search → career → course details)
- Request body generation for Oracle RichClient AJAX interactions

Oracle ADF requires maintaining stateful session tokens and sequential navigation
through its component model. This class encapsulates that complexity.

## ViewState Auto-Sync

Oracle ADF's JSF ViewState token changes with each server interaction. This module
keeps the client in sync with the server by automatically extracting and updating
the ViewState from every POST response (via `post_request`). This eliminates the
need for explicit `update_view_state()` GET requests and prevents ViewState drift
that can cause Oracle ADF to mistrack component state.

## Debug Logging

Set environment variable `SIA_DEBUG=1` to enable debug logging for Oracle ADF state
investigation. This logs ViewState, DELTAS, and state transitions.
"""

from typing import Any

from requests import Response

from .constants import actions, adf_events, adf_ids, business, data_map, http, status
from .core import (
    EnhancedSession,
    OracleAdfRequestBuilder,
    SiaSessionException,
    extract_view_state,
    extract_view_state_from_response,
)
from .parsers.html_parser import HtmlParser, get_course_list
from .parsers.models import SessionState
from .utils import (
    check_session,
    check_status,
    debug_log,
    handle_timeout_with_retry,
)


class SiaSession:
    """Manages HTTP sessions and state for Oracle ADF-based SIA system.

    This class handles the complexities of interacting with SIA's Oracle ADF backend:
    - Initializing and maintaining HTTP sessions with proper cookies/headers
    - Tracking Oracle ADF state tokens (ViewState, Window-Id, Page-Id)
    - Navigating through SIA's sequential workflow (career selection → course list → course details)
    - Generating Oracle RichClient XML request bodies for AJAX interactions

    Typical workflow:
        1. init_session() - Establish HTTP session with SIA
        2. set_career(search_code) - Navigate to academic program and load course list
        3. get_course_xml(index) - Retrieve detailed course information
        4. close_session() - Clean up resources

    ## Attributes
        timeout (int): HTTP request timeout in seconds
        career_name (str): Name of currently selected academic program
        career_code (str): Hyphen-delimited code (level-campus-faculty-career)
        is_electives (bool): Whether current career view shows elective courses
        course_list (list): List of {course_code: course_name} dicts for current career
        STATUS (SiaSessionStatus): Current navigation state in SIA workflow
    """

    def __init__(
        self,
        timeout: int = http.DEFAULT_TIMEOUT,
        session_data: dict[str, Any] | SessionState | None = None,
        init_session: bool = False,
    ) -> None:
        """Initialize a SiaSession instance.

        ## Args
            timeout: HTTP request timeout in seconds (default: 15)
            session_data: Previously serialized session state to restore (optional)
            init_session: If True, immediately call init_session() (default: False)

        ## Note
            Either session_data OR init_session should be provided, not both.
        """
        self._url: str = http.SIA_BASE_URL
        self.timeout: int = timeout

        self._career_name: str = "N/A"
        self._career_code: str = ""

        self._is_electives: bool = False
        self.__tipology_index: str = ""  # "7" for electives, "" for regular courses
        self.career_indices: list[str] = []

        # Oracle ADF state tokens - Required for all POST requests
        self._javax_faces_ViewState: str | None = None  # JSF ViewState (changes per request)
        self._Adf_Window_Id: str | None = None  # Oracle ADF Window identifier
        self._Adf_Page_Id: str | None = None  # Oracle ADF Page identifier
        self._params: dict[str, str] = {}  # URL params (Window-Id, Page-Id)

        self._session: EnhancedSession | None = None
        self._course_list: list[dict[str, str]] = []

        self._STATUS: status.SiaSessionStatus = status.SiaSessionStatus.NO_SESSION
        self.main_page_html: bytes | None = None  # Cached initial page HTML

        if session_data:
            self.load_session(session_data)
            self._init_request_dict()
        elif init_session:
            self.init_session()
            self._init_request_dict()

    @property
    def url(self) -> str:
        """SIA base URL for course catalog service."""
        return self._url

    @property
    def career_name(self) -> str:
        """Human-readable name of currently selected academic program."""
        return self._career_name

    @property
    def career_code(self) -> str:
        """Hyphen-delimited career code (format: level-campus-faculty-career)."""
        return self._career_code

    @property
    def is_electives(self) -> bool:
        """Whether the current view shows elective courses (vs. regular courses)."""
        return self._is_electives

    @property
    def course_list(self) -> list[dict[str, str]]:
        """List of courses for current career as [{course_code: course_name}, ...]."""
        return self._course_list

    @property
    def STATUS(self) -> status.SiaSessionStatus:
        """Current navigation state in the SIA workflow."""
        return self._STATUS

    @property
    def _has_session(self) -> bool:
        """Whether an HTTP session is currently initialized."""
        return self._session is not None

    @property
    def _tipology_index(self) -> str:
        """Current selected tipology index used by request builder."""
        return self.__tipology_index

    @property
    def _window_id(self) -> str | None:
        """Current Oracle ADF Window-Id."""
        return self._Adf_Window_Id

    @property
    def _page_id(self) -> str | None:
        """Current Oracle ADF Page-Id."""
        return self._Adf_Page_Id

    @property
    def _view_state(self) -> str | None:
        """Current Oracle ADF ViewState token."""
        return self._javax_faces_ViewState

    ##################### METHODS #####################

    @check_session
    def valid_session(self) -> bool:
        """Check if the current session is still valid (not timed out).

        ## Returns
            True if session is active, False if SIA reports session timeout

        ## Note
            This makes a lightweight POST request and checks for Oracle ADF timeout message.
            Not the most elegant approach, but works reliably for timeout detection.

        ## Raises
            SiaSessionException.SessionNotSet: If no session exists
        """
        if adf_events.SESSION_TIMEOUT_ALERT in self.post_request(data={}).text:
            return False
        return True

    def init_session(self) -> None:
        """Create a new HTTP session with SIA and extract Oracle ADF state tokens.

        This method:
        1. Creates an EnhancedSession (persistent HTTP session)
        2. Performs initial GET request to SIA catalog page
        3. Parses HTML to extract Oracle ADF tokens (ViewState, Window-Id)
        4. Initializes session parameters for subsequent requests
        5. Sets STATUS to CAREER_NOT_SET

        ## Raises
            SiaSessionException.SessionNotSet: If Oracle ADF tokens not found in response.
            SiaSessionException.TimeoutError: If request times out or connection fails.

        ## Note
            Oracle ADF requires javax.faces.ViewState (JSF state token).
            Adf-Window-Id uniquely identifies browser window/tab.
            Adf-Page-Id is set to '0' (seems to accept [0,1,2] without impact).
        """
        self._session = EnhancedSession(timeout=self.timeout)

        r = self.get_request(f"{self._url}?taskflowId=task-flow-AC_CatalogoAsignaturas")
        self.main_page_html = r.content

        html_content = r.content.decode("utf-8", errors="ignore")
        parser = HtmlParser(html_content)

        # Target: Oracle ADF JSF page → <input type="hidden" name="javax.faces.ViewState">
        view_state_input = parser.find("input", type="hidden", name="javax.faces.ViewState")
        if view_state_input is None:
            raise SiaSessionException.SessionNotSet from ValueError(
                "ViewState not found in initial page"
            )
        self._javax_faces_ViewState = str(view_state_input.get("value"))

        # Target: Oracle ADF page → <input type="hidden" name="Adf-Window-Id">
        adf_window_input = parser.find("input", type="hidden", name="Adf-Window-Id")
        if adf_window_input is None:
            raise SiaSessionException.SessionNotSet from ValueError(
                "Adf-Window-Id not found in initial page"
            )
        self._Adf_Window_Id = str(adf_window_input.get("value"))

        # self._Adf_Page_Id = soup.find("input", {"type": "hidden", "name":"Adf-Page-Id"})['value']
        self._Adf_Page_Id = "0"  # Hardcoded - Oracle ADF accepts [0,1,2], no observable difference

        self._params = {
            "Adf-Window-Id": self._Adf_Window_Id,
            "Adf-Page-Id": self._Adf_Page_Id,
        }
        self._STATUS = status.SiaSessionStatus.CAREER_NOT_SET

    @check_session
    def get_session_data(self) -> SessionState:
        """Serialize current session state for persistence/restoration.

        ## Returns
            SessionState model containing all session state (cookies, tokens, career info, STATUS)

        ## Raises
            SiaSessionException.SessionNotSet: If no session exists

        ## Note
            This allows sessions to be saved (e.g., in Flask session) and restored later
            to avoid repeated authentication and career navigation.
        """
        session = self._session
        return SessionState(
            session_headers=dict(session.headers),  # type: ignore[OptionalMemberAccess]
            session_cookies=session.cookies.get_dict(),  # type: ignore[OptionalMemberAccess]
            params=self._params,
            javax_faces_ViewState=self._javax_faces_ViewState,
            career_code=self._career_code,
            career_name=self._career_name,
            is_electives=self._is_electives,
            STATUS=self._STATUS.name,
        )

    def load_session(self, session_data: SessionState | dict[str, Any]) -> "SiaSession":
        """Restore a previously serialized session state.

        ## Args
            session_data: SessionState model or dict from get_session_data() containing session state

        ## Returns
            self (for method chaining)

        ## Note
            1. Create new EnhancedSession with restored headers/cookies
            2. Restore Oracle ADF tokens (ViewState, Window-Id, Page-Id)
            3. Restore career context (code, name, course list)
            4. Re-fetch course list from SIA to ensure data freshness
        """
        if isinstance(session_data, dict):
            session_data = SessionState.model_validate(session_data)

        self._session = EnhancedSession(timeout=self.timeout)  # requests.session()

        self._session.headers = session_data.session_headers  # type: ignore[assignment]
        self._session.cookies.update(session_data.session_cookies)

        self._params = session_data.params
        self._Adf_Page_Id = str(self._params["Adf-Page-Id"])
        self._Adf_Window_Id = str(self._params["Adf-Window-Id"])

        self._javax_faces_ViewState = session_data.javax_faces_ViewState

        self._career_code = session_data.career_code
        self._career_name = session_data.career_name
        self.career_indices = self._career_code.split(
            "-"
        )  # Split into [level, campus, faculty, career]

        self._is_electives = session_data.is_electives
        self._STATUS = status.SiaSessionStatus[session_data.STATUS]

        # Re-fetch current page to get updated course list and fresh ViewState
        r = self.get_request(f"{self._url}?taskflowId=task-flow-AC_CatalogoAsignaturas")

        html = r.content
        # Target: Oracle ADF table with class 'af_table_data-row' containing course rows
        self._course_list = get_course_list(html)

        # Refresh ViewState from the GET response instead of relying on stored data
        try:
            self._javax_faces_ViewState = extract_view_state(html)
        except SiaSessionException.SessionNotSet:
            pass  # Keep stored ViewState if extraction fails

        return self

    @check_session
    def close_session(self) -> None:
        """Close HTTP session and reset all state to initial values.

        ## Raises
            SiaSessionException.SessionNotSet: If no session exists

        ## Note
            After calling this, the instance returns to NO_SESSION state.
            Call init_session() to start a new session.
        """
        self._session.close()  # type: ignore[OptionalMemberAccess]
        self._session = None
        self._career_code = ""
        self._career_name = "N/A"
        self._course_list = []
        self._is_electives = False
        self._init_request_dict()
        self._STATUS = status.SiaSessionStatus.NO_SESSION

    def __enter__(self) -> "SiaSession":
        """Enter context manager for deterministic cleanup."""
        return self

    def __exit__(self, exc_type: type, exc_val: Exception, exc_tb: object) -> None:
        """Exit context manager and ensure session cleanup."""
        self.close_session()

    @check_session
    def keep_alive(self) -> Response:
        """Reset SIA session timeout by making a lightweight request.

        ## Returns
            Response object from the keep-alive POST request

        ## Raises
            SiaSessionException.SessionNotSet: If no session exists

        ## Note
            SIA sessions timeout after inactivity. Call this periodically
            for long-running operations to maintain session validity.
        """
        return self.post_request(data={})

    @check_session
    @handle_timeout_with_retry
    def post_request(self, data: dict[str, str]) -> Response:
        """Make a POST request to SIA with Oracle ADF headers and parameters.

        After each POST, the ViewState is automatically synced from the response
        to keep the client in sync with Oracle ADF's server-side state.

        ## Args
            data: Request body dictionary (usually generated by _generate_request_body)

        ## Returns
            requests.Response object from the POST request

        ## Raises
            SiaSessionException.SessionNotSet: If no session exists
            SiaSessionException.TimeoutError: If request times out
        """
        response = self._session.post(  # type: ignore[OptionalMemberAccess]
            self._url, params=self._params, headers=http.SIA_HEADERS, data=data
        )
        self.sync_view_state_from_response(response)
        return response

    @handle_timeout_with_retry
    def get_request(self, url: str, params: dict[str, str] | None = None) -> Response:
        """Make a GET request to SIA (or any URL).

        ## Args
            url: Full URL to request
            params: Optional URL query parameters

        ## Returns
            requests.Response object from the GET request

        ## Raises
            SiaSessionException.TimeoutError: If request times out

        ## Note
            Does not require @check_session - used for initial session creation.
        """
        session = self._session
        if session is None:
            raise SiaSessionException.SessionNotSet from None
        return session.get(url, params=params or {})

    def _init_request_dict(self) -> None:
        """Initialize the request body boilerplate dictionary.

        This dictionary serves as a template for all Oracle ADF POST requests.
        It contains Oracle ADF form fields and state tokens that must be present
        in every request to maintain session state.

        Specific requests augment this with additional fields via _generate_request_body.
        """
        builder = OracleAdfRequestBuilder(self)
        self.request_dict = builder.init_request_dict()

    @check_session
    def update_view_state(self) -> None:
        """Refresh the javax.faces.ViewState token by fetching current page.

        Oracle ADF's ViewState token changes with each server interaction.
        This method fetches the latest ViewState and updates the request_dict.

        ## Raises
            SiaSessionException.SessionNotSet: If ViewState not found in response.
            SiaSessionException.TimeoutError: If request times out.

        ## Note
            Makes GET request to current SIA page.
            Uses regex to extract ViewState from HTML.
            Updates both _javax_faces_ViewState and request_dict.
        """
        debug_log("UPDATE_VIEW_STATE: Fetching current page for ViewState")

        r = self.get_request(self._url, params=self._params)
        self._javax_faces_ViewState = extract_view_state(r.content)
        self.request_dict["javax.faces.ViewState"] = self._javax_faces_ViewState  # type: ignore[arg-type]

        debug_log(
            f"UPDATE_VIEW_STATE: ViewState updated, length={len(self._javax_faces_ViewState)}"
        )

    def extract_view_state_from_response(self, response: Any) -> str:
        """Extract ViewState from a partial POST response.

        This method parses an Oracle ADF partial page response to extract the new
        ViewState token. This is useful when we want to sync our ViewState with
        the server's state after making a request.

        ## Args
            response: Response object from a POST request.

        ## Returns
            Extracted ViewState string.

        ## Raises
            SiaSessionException.SessionNotSet: If ViewState not found in response.
        """
        return extract_view_state_from_response(response)

    def sync_view_state_from_response(self, response: Any) -> None:
        """Sync ViewState from a partial POST response.

        Extracts ViewState from the response and updates internal state.
        If ViewState is not found in the response, the current ViewState is preserved.

        ## Args
            response: Response object from a POST request.

        ## Note
            This is a convenience method that combines extract_view_state_from_response
            with state update. Use this when you want to ensure our ViewState matches
            the server's state after making a request.
        """
        try:
            self._javax_faces_ViewState = extract_view_state_from_response(response)
            self.request_dict["javax.faces.ViewState"] = self._javax_faces_ViewState  # type: ignore[arg-type]
            debug_log(
                f"SYNC_VIEW_STATE: ViewState synced from response, length={len(self._javax_faces_ViewState)}"
            )
        except SiaSessionException.SessionNotSet:
            debug_log("SYNC_VIEW_STATE: ViewState not found in response, keeping current")

    @check_session
    def set_career(self, search_code: str, electives: bool = False) -> "SiaSession":
        """Navigate to a specific academic career and load its course list.

        This method orchestrates a sequence of Oracle ADF interactions to navigate
        through SIA's dropdown-based search form and load the course catalog.

        ## Args
            search_code: Hyphen-delimited code (format: "level-campus-faculty-career").
                Example: "1-3-5-2345" where indices correspond to dropdown positions.
            electives: If True, load elective courses instead of regular courses (default: False).

        ## Returns
            self (for method chaining)

        ## Raises
            SiaSessionException.CareerNotSet: If career dropdown not found or no response.
            SiaSessionException.TimeoutError: If request times out.

        ## Note
            Regular courses (6 requests):
            1. Select study level dropdown → Triggers faculty dropdown population
            2. Select campus dropdown → Filter faculties by campus
            3. Select faculty dropdown → Triggers career dropdown population
            4. Select career dropdown → Enable "Mostrar" button
            5. Select typology dropdown → Filter course types (optional)
            6. Click "Mostrar" button → Load course list

            Electives (8 requests):
            Steps 1-5 same as regular, then:
            6. Select faculty/plan dropdown → Enable electives campus selector
            7. Select electives campus → Apply campus offset (+40)
            8. Click "Mostrar" button → Load elective course list
        """

        if electives:
            self.__tipology_index = business.ELECTIVES_TYPOLOGY_INDEX
        else:
            self.__tipology_index = ""

        self._career_code = search_code
        self.career_indices = search_code.split("-")  # [level, campus, faculty, career]

        # Build the action sequence for Oracle ADF workflow
        action_sequence = [
            actions.STUDY_LEVEL_DD,
            actions.CAMPUS_DD,
            actions.FACULTY_DD,
            actions.CAREER_DD,
            actions.TIPOLOGY_DD,
        ]

        if not electives:
            # Regular courses: Just click "Mostrar"
            action_sequence.append(actions.SHOW_COURSES_BTTN)
        else:
            # Electives: Two extra dropdown selections before "Mostrar"
            action_sequence.extend(
                [
                    actions.FACULTY_CAREER_DD,
                    actions.CAMPUS_ELECTIVES_DD,
                    actions.SHOW_COURSES_BTTN,
                ]
            )

        # Execute request sequence in order (ORDER IS CRITICAL - Oracle ADF enforces workflow)
        # Each body is generated just before sending so it gets the freshly synced ViewState
        # from the previous response (auto-synced by post_request).
        response = None
        for action in action_sequence:
            self._init_request_dict()

            # Populate request_dict with selected dropdown indices
            self.request_dict[adf_ids.STUDY_LEVEL_DD_ID] = self.career_indices[0]
            self.request_dict[adf_ids.CAMPUS_DD_ID] = self.career_indices[1]
            self.request_dict[adf_ids.FACULTY_DD_ID] = self.career_indices[2]
            self.request_dict[adf_ids.CAREER_DD_ID] = self.career_indices[3]

            data = self._generate_request_body(action)
            response = self.post_request(data=data)
            # ViewState auto-synced by post_request after each POST

            # Extract career name from FACULTY dropdown response XML
            # Target: Oracle ADF dropdown XML → <option> element at career index
            if action == actions.FACULTY_DD:
                xml = response.text
                parser = HtmlParser(xml)
                # Dropdown first option is "Select..." placeholder, offset by 1
                dropdown_elements = parser.findall(f'//*[@id="{data_map.DROPDOWNS[3]}"]/option')
                if not dropdown_elements:
                    raise SiaSessionException.CareerNotSet from ValueError(
                        "Career dropdown not found"
                    )
                option_index = int(self.career_indices[3]) + business.DROPDOWN_FIRST_OPTION_OFFSET
                self._career_name = dropdown_elements[option_index].text

        # Reset request_dict to clean state
        self._init_request_dict()

        if response is None:
            raise SiaSessionException.CareerNotSet from ValueError(
                "No response while setting career"
            )
        xml = response.text

        # Target: Final response XML contains Oracle ADF table with course list
        self._course_list = get_course_list(xml)
        self._is_electives = electives

        self._STATUS = status.SiaSessionStatus.ON_CAREER_PAGE

        debug_log(f"SET_CAREER: Course list loaded, {len(self._course_list)} courses")

        return self

    @check_status(status.SiaSessionStatus.ON_CAREER_PAGE)
    def _select_course_row(self, course_index: int) -> None:
        """Select (highlight) a course row in the Oracle ADF table.

        ## Args
            course_index: Index of course in course_list (0-based).

        ## Raises
            SiaSessionException.InvalidStatus: If not on career page.
            SiaSessionException.TimeoutError: If request times out.

        ## Note
            This ONLY highlights the row, does not navigate to course details.
            Oracle ADF requires this before clicking COURSE_PAGE_LINK.
            ViewState is automatically synced by post_request after the POST.
        """
        debug_log(f"SELECT_ROW: Index={course_index}")

        self._init_request_dict()
        request_body = self._generate_request_body(actions.SELECT_ROW, course_index)

        debug_log(f"SELECT_ROW: Sending request for index {course_index}")
        self.post_request(request_body)
        # ViewState auto-synced by post_request

    @check_status(status.SiaSessionStatus.ON_CAREER_PAGE)
    def enter_course_page(self, course_index: int) -> Response:
        """Navigate to course detail page for a specific course.

        ## Args
            course_index: Index of course in course_list (0-based).

        ## Returns
            Response object containing course detail XML.

        ## Raises
            SiaSessionException.InvalidStatus: If not on career page.
            SiaSessionException.TimeoutError: If request times out.

        ## Note
            1. Select course row (required by Oracle ADF before navigation)
            2. Reset request_dict (picks up ViewState synced from select_course_row response)
            3. Click course link to navigate
            4. Update STATUS to ON_COURSE_PAGE

            ViewState is automatically kept in sync by post_request after each POST,
            so no explicit update_view_state() GET call is needed.
        """
        debug_log(f"ENTER_COURSE_PAGE: Index={course_index}, Status={self._STATUS.value}")

        if course_index < len(self._course_list):
            course_at_idx = self._course_list[course_index]
            debug_log(f"Index {course_index} target", {"course": str(course_at_idx)})

        self._select_course_row(course_index)
        self._init_request_dict()

        request_body = self._generate_request_body(actions.COURSE_PAGE_LINK, course_index)
        debug_log(
            f"COURSE_PAGE_LINK request for index {course_index}",
            {"PROCESS": request_body.get("oracle.adf.view.rich.PROCESS", "N/A")},
        )

        response = self.post_request(request_body)
        # ViewState auto-synced by post_request

        self._STATUS = status.SiaSessionStatus.ON_COURSE_PAGE

        debug_log(f"ENTER_COURSE_PAGE: Success, Status={self._STATUS.value}")
        return response

    @check_status(status.SiaSessionStatus.ON_COURSE_PAGE)
    def exit_course_page(self) -> None:
        """Return to course list from course detail page.

        Clicks the "Volver" (Back) button in Oracle ADF interface.
        ViewState is automatically synced by post_request after the POST.

        ## Raises
            SiaSessionException.InvalidStatus: If not on course page.
            SiaSessionException.TimeoutError: If request times out.
        """
        debug_log(f"EXIT_COURSE_PAGE: Current Status={self._STATUS.value}")

        data = {
            "org.apache.myfaces.trinidad.faces.FORM": "f1",
            "Adf-Window-Id": self._Adf_Window_Id,
            "Adf-Page-Id": self._Adf_Page_Id,
            "javax.faces.ViewState": self._javax_faces_ViewState,
            "event": adf_ids.BACK_BTTN_ID,
            f"event.{adf_ids.BACK_BTTN_ID}": adf_events.BTTN_EVENT_VALUE,
            "oracle.adf.view.rich.PROCESS": f"{adf_ids.ORACLE_ADF_REGION_ID},{adf_ids.BACK_BTTN_ID}4",
        }
        self.post_request(data)
        # ViewState auto-synced by post_request
        self._STATUS = status.SiaSessionStatus.ON_CAREER_PAGE

        debug_log(f"EXIT_COURSE_PAGE: Complete, Status={self._STATUS.value}")

    @check_status(status.SiaSessionStatus.ON_CAREER_PAGE)
    def get_course_xml(self, course_index: int) -> str:
        """Retrieve course detail XML for a specific course.

        This is a convenience method that:
        1. Enters course detail page
        2. Captures the XML response
        3. Exits back to course list

        ## Args
            course_index: Index of course in course_list (0-based).

        ## Returns
            Oracle ADF XML containing course details (groups, schedules, prerequisites, etc.).

        ## Raises
            SiaSessionException.InvalidStatus: If not on career page.
            SiaSessionException.TimeoutError: If request times out.

        ## Note
            ViewState is automatically kept in sync by post_request after each POST,
            ensuring Oracle ADF's server-side state matches the client's expectations.
        """
        debug_log(f"=== GET_COURSE_XML START: Index={course_index} ===")
        debug_log(f"Current course list size: {len(self._course_list)}")

        if course_index < len(self._course_list):
            course_info = self._course_list[course_index]
            debug_log(f"Course at index {course_index}", {"course": str(course_info)})
        else:
            debug_log(f"WARNING: Index {course_index} out of bounds!")

        xml = self.enter_course_page(course_index).text
        debug_log(f"ENTER_COURSE_PAGE returned, XML length: {len(xml)}")

        self.exit_course_page()
        debug_log(f"=== GET_COURSE_XML END: Index={course_index} ===")

        return xml

    @check_session
    def get_current_xml(self) -> str:
        """Retrieve Oracle ADF XML for the current page (based on STATUS).

        ## Returns
            Raw XML response from SIA for current page state

        ## Raises
            SiaSessionException.SessionNotSet: If no session exists

        ## Note
            Useful for debugging Oracle ADF responses or extracting data from current view.
        """
        return self.get_request(self._url, params=self._params).text

    def _generate_request_body(self, data_name: str, idx: int = -1) -> dict[str, str]:
        """Generate complete Oracle ADF request body for a named action.

        ## Args
            data_name: Logical action name from DATA_MAP (e.g., STUDY_LEVEL_DD, SHOW_COURSES_BTTN).
            idx: Optional table row index for row-based actions (default: -1).

        ## Returns
            Complete request body dictionary ready for POST to SIA.

        ## Raises
            KeyError: If data_name not found in DATA_MAP.
        """
        builder = OracleAdfRequestBuilder(self, self.request_dict)
        return builder.build_request_body(data_name, idx)
