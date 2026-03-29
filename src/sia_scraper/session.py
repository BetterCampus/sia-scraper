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

## Debug Logging

Set environment variable `SIA_DEBUG=1` to enable debug logging for Oracle ADF state
investigation. This logs ViewState, DELTAS, and state transitions.

## Known Issues

### Oracle ADF Index 0/1 Swap Bug (2026-03-28)

Oracle ADF has a client-side bug that causes indices 0 and 1 to swap data when
requesting course details. This bug:

- Affects ONLY indices 0 and 1 in the course list
- Indices 2+ work correctly
- Is in Oracle ADF's JavaScript/client-side code (not in our request format)
- Cannot be fixed without Oracle patching ADF

**Workaround:** None available. When requesting index 1, the response will contain
index 0's data instead of index 1's data. Users should be aware of this limitation
when processing courses at indices 0 and 1.
"""

from typing import Any

from .adf_state import extract_view_state, extract_view_state_from_response
from .constants import (
    BACK_BTTN_ID,
    BTTN_EVENT_VALUE,
    CAMPUS_DD,
    CAMPUS_DD_ID,
    CAMPUS_ELECTIVES_DD,
    CAREER_DD,
    CAREER_DD_ID,
    COURSE_PAGE_LINK,
    DEFAULT_TIMEOUT,
    DROPDOWN_FIRST_OPTION_OFFSET,
    DROPDOWNS,
    ELECTIVES_TYPOLOGY_INDEX,
    FACULTY_CAREER_DD,
    FACULTY_DD,
    FACULTY_DD_ID,
    ORACLE_ADF_REGION_ID,
    SELECT_ROW,
    SESSION_TIMEOUT_ALERT,
    SHOW_COURSES_BTTN,
    SIA_BASE_URL,
    SIA_HEADERS,
    STUDY_LEVEL_DD,
    STUDY_LEVEL_DD_ID,
    TIPOLOGY_DD,
    SiaSessionStatus,
)
from .decorators import check_session, check_status, handle_timeout_error
from .enhanced_session import EnhancedSession
from .exceptions import SiaSessionException
from .oracle_adf_request import OracleAdfRequestBuilder
from .parsers import HtmlParser, get_course_list
from .utils import debug_log


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
        timeout: int = DEFAULT_TIMEOUT,
        session_data: dict[str, Any] | None = None,
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
        self.__url: str = SIA_BASE_URL
        self.timeout: int = timeout

        self.__career_name: str = "N/A"
        self.__career_code: str = ""

        self.__is_electives: bool = False
        self.__tipology_index: str = ""  # "7" for electives, "" for regular courses

        # Oracle ADF state tokens - Required for all POST requests
        self.__javax_faces_ViewState: str | None = None  # JSF ViewState (changes per request)
        self.__Adf_Window_Id: str | None = None  # Oracle ADF Window identifier
        self.__Adf_Page_Id: str | None = None  # Oracle ADF Page identifier
        self.__params: dict[str, str] = {}  # URL params (Window-Id, Page-Id)

        self.__session: EnhancedSession | None = None
        self.__course_list: list[dict[str, str]] = []

        self.__STATUS: SiaSessionStatus = SiaSessionStatus.NO_SESSION
        self.main_page_html: bytes | None = None  # Cached initial page HTML

        if session_data:
            self.load_session(session_data)
            self.__init_request_dict()
        elif init_session:
            self.init_session()
            self.__init_request_dict()

    @property
    def url(self) -> str:
        """SIA base URL for course catalog service."""
        return self.__url

    @property
    def career_name(self) -> str:
        """Human-readable name of currently selected academic program."""
        return self.__career_name

    @property
    def career_code(self) -> str:
        """Hyphen-delimited career code (format: level-campus-faculty-career)."""
        return self.__career_code

    @property
    def is_electives(self) -> bool:
        """Whether the current view shows elective courses (vs. regular courses)."""
        return self.__is_electives

    @property
    def course_list(self) -> list[dict[str, str]]:
        """List of courses for current career as [{course_code: course_name}, ...]."""
        return self.__course_list

    @property
    def STATUS(self) -> SiaSessionStatus:
        """Current navigation state in the SIA workflow."""
        return self.__STATUS

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
        if SESSION_TIMEOUT_ALERT in self.post_request(data={}).text:
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
        self.__session = EnhancedSession(timeout=self.timeout)

        r = self.get_request(f"{self.__url}?taskflowId=task-flow-AC_CatalogoAsignaturas")
        self.main_page_html = r.content

        html_content = r.content.decode("utf-8", errors="ignore")
        parser = HtmlParser(html_content)

        # Target: Oracle ADF JSF page → <input type="hidden" name="javax.faces.ViewState">
        view_state_input = parser.find("input", type="hidden", name="javax.faces.ViewState")
        if view_state_input is None:
            raise SiaSessionException.SessionNotSet from ValueError(
                "ViewState not found in initial page"
            )
        self.__javax_faces_ViewState = str(view_state_input.get("value"))

        # Target: Oracle ADF page → <input type="hidden" name="Adf-Window-Id">
        adf_window_input = parser.find("input", type="hidden", name="Adf-Window-Id")
        if adf_window_input is None:
            raise SiaSessionException.SessionNotSet from ValueError(
                "Adf-Window-Id not found in initial page"
            )
        self.__Adf_Window_Id = str(adf_window_input.get("value"))

        # self.__Adf_Page_Id = soup.find("input", {"type": "hidden", "name":"Adf-Page-Id"})['value']
        self.__Adf_Page_Id = "0"  # Hardcoded - Oracle ADF accepts [0,1,2], no observable difference

        self.__params = {
            "Adf-Window-Id": self.__Adf_Window_Id,
            "Adf-Page-Id": self.__Adf_Page_Id,
        }
        self.__STATUS = SiaSessionStatus.CAREER_NOT_SET

    @check_session
    def get_session_data(self) -> dict[str, Any]:
        """Serialize current session state for persistence/restoration.

        ## Returns
            Dictionary containing all session state (cookies, tokens, career info, STATUS)

        ## Raises
            SiaSessionException.SessionNotSet: If no session exists

        ## Note
            This allows sessions to be saved (e.g., in Flask session) and restored later
            to avoid repeated authentication and career navigation.
        """
        session = self.__session
        return {
            "session_headers": dict(session.headers),  # type: ignore[OptionalMemberAccess]
            "session_cookies": session.cookies.get_dict(),  # type: ignore[OptionalMemberAccess]
            "params": self.__params,
            "javax_faces_ViewState": self.__javax_faces_ViewState,
            "career_code": self.__career_code,
            "career_name": self.__career_name,
            "is_electives": self.__is_electives,
            "STATUS": self.__STATUS.name,
        }

    def load_session(self, session_data: dict[str, Any]) -> "SiaSession":
        """Restore a previously serialized session state.

        ## Args
            session_data: Dictionary from get_session_data() containing session state

        ## Returns
            self (for method chaining)

        ## Note
            1. Create new EnhancedSession with restored headers/cookies
            2. Restore Oracle ADF tokens (ViewState, Window-Id, Page-Id)
            3. Restore career context (code, name, course list)
            4. Re-fetch course list from SIA to ensure data freshness
        """
        self.__session = EnhancedSession(timeout=self.timeout)  # requests.session()

        self.__session.headers = session_data["session_headers"]
        self.__session.cookies.update(session_data["session_cookies"])

        self.__params = session_data["params"]
        self.__Adf_Page_Id = str(self.__params["Adf-Page-Id"])
        self.__Adf_Window_Id = str(self.__params["Adf-Window-Id"])

        self.__javax_faces_ViewState = session_data["javax_faces_ViewState"]

        self.__career_code = session_data["career_code"]
        self.__career_name = session_data["career_name"]
        self.career_indexs = self.__career_code.split(
            "-"
        )  # Split into [level, campus, faculty, career]

        self.__is_electives = session_data["is_electives"]
        self.__STATUS = SiaSessionStatus[session_data["STATUS"]]

        # Re-fetch current page to get updated course list
        r = self.get_request(f"{self.__url}?taskflowId=task-flow-AC_CatalogoAsignaturas")

        html = r.content
        # Target: Oracle ADF table with class 'af_table_data-row' containing course rows
        self.__course_list = get_course_list(html)

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
        self.__session.close()  # type: ignore[OptionalMemberAccess]
        self.__session = None
        self.__career_code = ""
        self.__career_name = "N/A"
        self.__course_list = []
        self.__is_electives = False
        self.__init_request_dict()
        self.__STATUS = SiaSessionStatus.NO_SESSION

    @check_session
    def keep_alive(self) -> Any:
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
    @handle_timeout_error
    def post_request(self, data: dict[str, str]) -> Any:
        """Make a POST request to SIA with Oracle ADF headers and parameters.

        ## Args
            data: Request body dictionary (usually generated by _generate_request_body)

        ## Returns
            requests.Response object from the POST request

        ## Raises
            SiaSessionException.SessionNotSet: If no session exists
            SiaSessionException.TimeoutError: If request times out
        """
        return self.__session.post(self.__url, params=self.__params, headers=SIA_HEADERS, data=data)  # type: ignore[OptionalMemberAccess]

    @handle_timeout_error
    def get_request(self, url: str, params: dict[str, str] | None = None) -> Any:
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
        session = self.__session
        if session is None:
            raise SiaSessionException.SessionNotSet from SiaSessionException
        return session.get(url, params=params or {})

    def __init_request_dict(self) -> None:
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
            Updates both __javax_faces_ViewState and request_dict.
        """
        debug_log("UPDATE_VIEW_STATE: Fetching current page for ViewState")

        r = self.get_request(self.__url, params=self.__params)
        self.__javax_faces_ViewState = extract_view_state(r.content)
        self.request_dict["javax.faces.ViewState"] = self.__javax_faces_ViewState  # type: ignore[arg-type]

        debug_log(
            f"UPDATE_VIEW_STATE: ViewState updated, length={len(self.__javax_faces_ViewState)}"
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
            self.__javax_faces_ViewState = extract_view_state_from_response(response)
            self.request_dict["javax.faces.ViewState"] = self.__javax_faces_ViewState  # type: ignore[arg-type]
            debug_log(
                f"SYNC_VIEW_STATE: ViewState synced from response, length={len(self.__javax_faces_ViewState)}"
            )
        except SiaSessionException.SessionNotSet:
            debug_log("SYNC_VIEW_STATE: ViewState not found in response, keeping current")

    @check_status(SiaSessionStatus.ON_CAREER_PAGE)
    def reset_row_selection_state(self) -> None:
        """Reset Oracle ADF's table row selection state.

        This method sends a preliminary request to reset Oracle ADF's internal
        row selection state. This can help avoid the index 0/1 swap bug
        that occurs on the first request after set_career().

        ## Raises
            SiaSessionException.InvalidStatus: If not on career page.
            SiaSessionException.TimeoutError: If request times out.

        ## Note
            This sends a SELECT_ROW request with a non-existent index (-1)
            which appears to reset ADF's internal selection state without
            actually selecting any row. This can be called before get_course_xml()
            to ensure a clean state.
        """
        debug_log("RESET_ROW_SELECTION: Sending preliminary request to reset state")

        # Make a preliminary request with index -1 to reset selection state
        self.__init_request_dict()
        request_body = self._generate_request_body(SELECT_ROW, -1)

        # Override DELTAS to indicate no row selected
        request_body["oracle.adf.view.rich.DELTAS"] = (
            f"{{pt1:r1:0:t4={{viewportSize={len(self.__course_list) + 1},"
            f"rows={len(self.__course_list)},selectedRowKeys=}}}}"
        )

        response = self.post_request(request_body)
        self.sync_view_state_from_response(response)

        debug_log("RESET_ROW_SELECTION: State reset complete")

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
            self.__tipology_index = ELECTIVES_TYPOLOGY_INDEX
        else:
            self.__tipology_index = ""

        self.__career_code = search_code
        self.career_indexs = search_code.split("-")  # [level, campus, faculty, career]

        self.__init_request_dict()

        # Populate request_dict with selected dropdown indices
        self.request_dict[STUDY_LEVEL_DD_ID] = self.career_indexs[0]
        self.request_dict[CAMPUS_DD_ID] = self.career_indexs[1]
        self.request_dict[FACULTY_DD_ID] = self.career_indexs[2]
        self.request_dict[CAREER_DD_ID] = self.career_indexs[3]

        # Generate Oracle ADF request bodies for each sequential interaction
        STUDY_LEVEL_DD_data = self._generate_request_body(STUDY_LEVEL_DD)
        CAMPUS_DD_data = self._generate_request_body(CAMPUS_DD)
        FACULTY_DD_data = self._generate_request_body(FACULTY_DD)
        CAREER_DD_data = self._generate_request_body(CAREER_DD)
        TIPOLOGY_DD_data = self._generate_request_body(TIPOLOGY_DD)

        data_list = [
            STUDY_LEVEL_DD_data,
            CAMPUS_DD_data,
            FACULTY_DD_data,
            CAREER_DD_data,
            TIPOLOGY_DD_data,
        ]

        if not electives:
            # Regular courses: Just click "Mostrar"
            SHOW_CURSES_BTTN_data = self._generate_request_body(SHOW_COURSES_BTTN)
            data_list.append(SHOW_CURSES_BTTN_data)

        else:
            # Electives: Two extra dropdown selections before "Mostrar"
            FACULTY_CAREER_DD_data = self._generate_request_body(FACULTY_CAREER_DD)
            CAMPUS_ELECTIVES_DD_data = self._generate_request_body(CAMPUS_ELECTIVES_DD)
            SHOW_CURSES_BTTN_data = self._generate_request_body(SHOW_COURSES_BTTN)

            data_list.append(FACULTY_CAREER_DD_data)
            data_list.append(CAMPUS_ELECTIVES_DD_data)
            data_list.append(SHOW_CURSES_BTTN_data)

        # Refresh ViewState before starting request sequence
        self.update_view_state()
        self.request_dict["javax.faces.ViewState"] = self.__javax_faces_ViewState  # type: ignore[arg-type]

        # Execute request sequence in order (ORDER IS CRITICAL - Oracle ADF enforces workflow)
        response = None
        for data in data_list:
            response = self.post_request(data=data)

            # Extract career name from FACULTY dropdown response XML
            # Target: Oracle ADF dropdown XML → <option> element at career index
            if data == FACULTY_DD_data:
                xml = response.text
                parser = HtmlParser(xml)
                # Dropdown first option is "Select..." placeholder, offset by 1
                dropdown_elements = parser.find_by_xpath(f'//*[@id="{DROPDOWNS[3]}"]/option')
                if not dropdown_elements:
                    raise SiaSessionException.CareerNotSet from ValueError(
                        "Career dropdown not found"
                    )
                option_index = int(self.career_indexs[3]) + DROPDOWN_FIRST_OPTION_OFFSET
                self.__career_name = dropdown_elements[option_index].text

        # Reset request_dict to clean state
        self.__init_request_dict()

        if response is None:
            raise SiaSessionException.CareerNotSet from ValueError(
                "No response while setting career"
            )
        xml = response.text

        # Target: Final response XML contains Oracle ADF table with course list
        self.__course_list = get_course_list(xml)
        self.__is_electives = electives

        self.__STATUS = SiaSessionStatus.ON_CAREER_PAGE

        debug_log(f"SET_CAREER: Course list loaded, {len(self.__course_list)} courses")

        return self

    @check_status(SiaSessionStatus.ON_CAREER_PAGE)
    def __select_course_row(self, course_index: int, prime: bool = False) -> None:
        """Select (highlight) a course row in the Oracle ADF table.

        ## Args
            course_index: Index of course in course_list (0-based).
            prime: If True, this is a priming request sent before the actual selection.
                   Used to work around Oracle ADF's index 0/1 bug.

        ## Raises
            SiaSessionException.InvalidStatus: If not on career page.
            SiaSessionException.TimeoutError: If request times out.

        ## Note
            This ONLY highlights the row, does not navigate to course details.
            Oracle ADF requires this before clicking COURSE_PAGE_LINK.
        """
        # Mark index 0 vs index 1 for comparison
        index_marker = (
            "FIRST"
            if course_index == 0
            else ("SECOND" if course_index == 1 else f"OTHER({course_index})")
        )
        marker = "PRIME" if prime else index_marker
        debug_log(f"SELECT_ROW: [{marker}] Index={course_index}")

        # Log ViewState before request
        viewstate_value = self.__javax_faces_ViewState or ""
        viewstate_preview = (
            viewstate_value[:50] + "..." if len(viewstate_value) > 50 else viewstate_value
        )
        debug_log(f"ViewState before SELECT_ROW [{marker}]", {"ViewState": viewstate_preview})

        self.__init_request_dict()
        request_body = self._generate_request_body(SELECT_ROW, course_index)

        # Log DELTAS being sent
        if "oracle.adf.view.rich.DELTAS" in request_body:
            deltas = request_body["oracle.adf.view.rich.DELTAS"]
            debug_log(f"DELTAS [{marker}]", {"DELTAS": deltas})
            # Highlight the selectedRowKeys value
            if "selectedRowKeys=" in deltas:
                for part in deltas.split(","):
                    if "selectedRowKeys" in part:
                        debug_log(f"selectedRowKeys [{marker}]", {"selectedRowKeys": part})

        response = self.post_request(request_body)

        # Sync ViewState after the request
        if not prime:
            self.sync_view_state_from_response(response)

    @check_status(SiaSessionStatus.ON_CAREER_PAGE)
    def enter_course_page(self, course_index: int) -> Any:
        """Navigate to course detail page for a specific course.

        ## Args
            course_index: Index of course in course_list (0-based).

        ## Returns
            Response object containing course detail XML.

        ## Raises
            SiaSessionException.InvalidStatus: If not on career page.
            SiaSessionException.TimeoutError: If request times out.

        ## Note
            1. Refresh ViewState (ensures fresh Oracle ADF state)
            2. Select course row (required by Oracle ADF before navigation)
            3. Reset request_dict
            4. Click course link to navigate
            5. Update STATUS to ON_COURSE_PAGE
        """
        debug_log(f"ENTER_COURSE_PAGE: Index={course_index}, Status={self.__STATUS.value}")

        # Log course being accessed for index comparison
        if course_index < len(self.__course_list):
            course_at_idx = self.__course_list[course_index]
            debug_log(f"Index {course_index} target", {"course": str(course_at_idx)})

        self.update_view_state()
        self.__select_course_row(course_index)
        self.__init_request_dict()

        request_body = self._generate_request_body(COURSE_PAGE_LINK, course_index)
        debug_log(
            f"COURSE_PAGE_LINK request for index {course_index}",
            {"PROCESS": request_body.get("oracle.adf.view.rich.PROCESS", "N/A")},
        )

        response = self.post_request(request_body)

        # Log response info for debugging
        response_text = response.text
        debug_log(
            f"ENTER_COURSE_PAGE response for index {course_index}",
            {"response_length": len(response_text), "status_code": response.status_code},
        )

        self.__STATUS = SiaSessionStatus.ON_COURSE_PAGE

        debug_log(f"ENTER_COURSE_PAGE: Success, Status={self.__STATUS.value}")
        return response

    @check_status(SiaSessionStatus.ON_COURSE_PAGE)
    def exit_course_page(self) -> None:
        """Return to course list from course detail page.

        Clicks the "Volver" (Back) button in Oracle ADF interface.

        ## Raises
            SiaSessionException.InvalidStatus: If not on course page.
            SiaSessionException.TimeoutError: If request times out.
        """
        debug_log(f"EXIT_COURSE_PAGE: Current Status={self.__STATUS.value}")

        # Log ViewState before exit
        viewstate_value = self.__javax_faces_ViewState or ""
        viewstate_preview = (
            viewstate_value[:50] + "..." if len(viewstate_value) > 50 else viewstate_value
        )
        debug_log("ViewState before BACK_BTTN", {"ViewState": viewstate_preview})

        data = {
            "org.apache.myfaces.trinidad.faces.FORM": "f1",
            "Adf-Window-Id": self.__Adf_Window_Id,
            "Adf-Page-Id": self.__Adf_Page_Id,
            "javax.faces.ViewState": self.__javax_faces_ViewState,
            "event": BACK_BTTN_ID,
            f"event.{BACK_BTTN_ID}": BTTN_EVENT_VALUE,
            "oracle.adf.view.rich.PROCESS": f"{ORACLE_ADF_REGION_ID},{BACK_BTTN_ID}4",
        }
        self.post_request(data)
        self.__STATUS = SiaSessionStatus.ON_CAREER_PAGE

        debug_log(f"EXIT_COURSE_PAGE: Back button posted, Status={self.__STATUS.value}")

        debug_log("EXIT_COURSE_PAGE: Complete")

    @check_status(SiaSessionStatus.ON_CAREER_PAGE)
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

        ## Oracle ADF Bug Mitigation
            Investigation (2026-03-28) confirmed Oracle ADF has an off-by-one bug
            affecting ONLY indices 0 and 1. These indices swap data depending on ADF's
            current row state. Higher indices (2+) work correctly.

            See module docstring for full details on the bug and its limitations.
        """
        debug_log(f"=== GET_COURSE_XML START: Index={course_index} ===")
        debug_log(f"Current course list size: {len(self.__course_list)}")

        if course_index < len(self.__course_list):
            course_info = self.__course_list[course_index]
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
        return self.get_request(self.__url, params=self.__params).text

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
