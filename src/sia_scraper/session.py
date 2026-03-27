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
through its component model. This class encapsulates that complexity."""

import re
from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar, cast

from bs4 import BeautifulSoup
from requests.exceptions import ConnectionError, ReadTimeout, Timeout

from .constants import (
    BACK_BTTN_ID,
    BTTN_EVENT_VALUE,
    CAMPUS_DD,
    CAMPUS_DD_ID,
    CAMPUS_ELECTIVES_DD,
    CAMPUS_ELECTIVES_DD_ID,
    CAREER_DD,
    CAREER_DD_ID,
    COURSE_PAGE_LINK,
    DATA_MAP,
    DEFAULT_TIMEOUT,
    DROPDOWN_EVENT_VALUE,
    DROPDOWNS,
    ELECTIVES_CAMPUS_INCREMENT,
    FACULTY_CAREER_DD,
    FACULTY_CAREER_DD_ID,
    FACULTY_DD,
    FACULTY_DD_ID,
    SELECT_ROW,
    SELECT_ROW_EVENT_VALUE,
    SHOW_COURSES_BTTN,
    SHOW_CURSES_BTTN_ID,
    SIA_BASE_URL,
    SIA_HEADERS,
    STUDY_LEVEL_DD,
    STUDY_LEVEL_DD_ID,
    TIPOLOGY_DD,
    TIPOLOGY_DD_ID,
    SiaSessionStatus,
)
from .enhanced_session import EnhancedSession

P = ParamSpec("P")
R = TypeVar("R")


class SiaSessionException(Exception):
    """Base exception for SIA session-related errors."""

    class SessionNotSet(Exception):
        """Raised when attempting session operations without an active session.

        Resolution: Call init_session() or load_session(session_data) first.
        """

        def __init__(self) -> None:
            """Initialize with instruction to start session."""
            super().__init__("Must set session by create_session() or load_session(session_data)")

    class CareerNotSet(Exception):
        """Raised when attempting course operations without selecting a career.

        Resolution: Call set_career(search_code) to navigate to a career page.
        """

        def __init__(self) -> None:
            """Initialize with instruction to set career."""
            super().__init__("Must set career by set_career(__career_code)")

    class TimeoutError(Exception):
        """Raised when SIA HTTP requests exceed the configured timeout.

        This typically indicates SIA server overload or network issues.
        """

        def __init__(self) -> None:
            """Initialize with timeout message."""
            super().__init__("Request to SIA take to long")

    class InvalidStatus(Exception):
        """Raised when attempting an action incompatible with current session state.

        ### Example
        Trying to exit_course_page() when STATUS != ON_COURSE_PAGE.
        """

        def __init__(self) -> None:
            """Initialize with invalid status message."""
            super().__init__("Invalid action to current SIA status")


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

    ##################### DECORATORS #####################

    @staticmethod
    def check_session(func: Callable[P, R]) -> Callable[P, R]:
        """Decorator: Ensures an active HTTP session exists before executing method.

        ## Raises
            SiaSessionException.SessionNotSet: If session is None
        """

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            """Execute method after checking session exists.

            Raises SessionNotSet if __session is None.
            """
            self = cast("SiaSession", args[0])
            if self.__session is None:
                raise SiaSessionException.SessionNotSet from SiaSessionException
            return func(*args, **kwargs)

        return wrapper

    @staticmethod
    def check_career(func: Callable[P, R]) -> Callable[P, R]:
        """Decorator: Ensures a career has been selected before executing method.

        ## Raises
            SiaSessionException.CareerNotSet: If career_code is empty
        """

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            """Execute method after checking career is set.

            Raises CareerNotSet if __career_code is empty.
            """
            self = cast("SiaSession", args[0])
            if self.__career_code == "":
                raise SiaSessionException.CareerNotSet from SiaSessionException
            return func(*args, **kwargs)

        return wrapper

    @staticmethod
    def check_status(status: SiaSessionStatus) -> Callable[[Callable[P, R]], Callable[P, R]]:
        """Decorator factory: Ensures session is in required status before executing.

        ## Args
            status: Required SiaSessionStatus for method execution

        ## Returns
            Decorator function that validates STATUS matches required value

        ## Raises
            SiaSessionException.InvalidStatus: If current STATUS != required status
        """

        def decorator(func: Callable[P, R]) -> Callable[P, R]:
            """Apply status check to a function."""

            @wraps(func)
            def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                """Execute method after validating session STATUS."""
                self = cast("SiaSession", args[0])
                if self.__STATUS != status:
                    raise SiaSessionException.InvalidStatus from SiaSessionException
                return func(*args, **kwargs)

            return wrapper

        return decorator

    @staticmethod
    def handle_timeout_error(func: Callable[P, R]) -> Callable[P, R]:
        """Decorator: Wraps HTTP operations and converts timeout exceptions.

        ## Raises
            SiaSessionException.TimeoutError: When requests timeout or connection fails
        """

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            """Execute method with timeout error handling.

            Converts requests timeout/connection errors to SiaSessionException.TimeoutError.
            """
            try:
                return func(*args, **kwargs)
            except (Timeout, ReadTimeout, ConnectionError) as e:
                raise SiaSessionException.TimeoutError from e

        return wrapper

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
        # TODO: Refactor - Brittle check based on alert message string
        if (
            "AdfPage.PAGE.__getSessionTimeoutHelper().__alertTimeout()"
            in self.post_request(data={}).text
        ):
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
            Various network exceptions from requests library

        ## Note
            ### Logic
            - Oracle ADF requires javax.faces.ViewState (JSF state token)
            - Adf-Window-Id uniquely identifies browser window/tab
            - Adf-Page-Id is set to '0' (seems to accept [0,1,2] without impact)
        """
        self.__session = EnhancedSession(timeout=self.timeout)

        r = self.get_request(f"{self.__url}?taskflowId=task-flow-AC_CatalogoAsignaturas")
        self.main_page_html = r.content

        html_content = r.content.decode("utf-8", errors="ignore")
        soup = BeautifulSoup(html_content, "html.parser")

        # Target: Oracle ADF JSF page → <input type="hidden" name="javax.faces.ViewState">
        view_state_input = soup.find("input", {"type": "hidden", "name": "javax.faces.ViewState"})
        if view_state_input is None:
            raise SiaSessionException.SessionNotSet from ValueError(
                "ViewState not found in initial page"
            )
        self.__javax_faces_ViewState = str(view_state_input["value"])

        # Target: Oracle ADF page → <input type="hidden" name="Adf-Window-Id">
        adf_window_input = soup.find("input", {"type": "hidden", "name": "Adf-Window-Id"})
        if adf_window_input is None:
            raise SiaSessionException.SessionNotSet from ValueError(
                "Adf-Window-Id not found in initial page"
            )
        self.__Adf_Window_Id = str(adf_window_input["value"])

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
        if session is None:
            raise SiaSessionException.SessionNotSet from SiaSessionException
        return {
            "session_headers": dict(session.headers),
            "session_cookies": session.cookies.get_dict(),
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
            ### Logic
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
        self.__course_list = get_course_list(html, "html.parser")

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
        session = self.__session
        if session is None:
            raise SiaSessionException.SessionNotSet from SiaSessionException
        session.close()
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
        session = self.__session
        if session is None:
            raise SiaSessionException.SessionNotSet from SiaSessionException
        return session.post(self.__url, params=self.__params, headers=SIA_HEADERS, data=data)

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

        ## Note
            # TODO: Refactor - Document the purpose of unknown fields:
            - pt1:r1:0:soc10, pt1:r1:0:it10, pt1:r1:0:it11 (unknown Oracle ADF components)
            - org.apache.myfaces.trinidad.faces.FORM = "f1" (Trinidad form identifier)
        """
        self.request_dict = {
            STUDY_LEVEL_DD_ID: "",
            CAMPUS_DD_ID: "",
            FACULTY_DD_ID: "",
            CAREER_DD_ID: "",
            TIPOLOGY_DD_ID: self.__tipology_index,
            SHOW_CURSES_BTTN_ID: "",
            "pt1:r1:0:soc5": "",  # TODO: Document - Unknown Oracle ADF component
            "pt1:r1:0:soc10": "",  # TODO: Document - Unknown Oracle ADF component
            "pt1:r1:0:it10": "",  # TODO: Document - Unknown Oracle ADF component
            "pt1:r1:0:it11": "",  # TODO: Document - Unknown Oracle ADF component
            "org.apache.myfaces.trinidad.faces.FORM": "f1",  # Trinidad JSF form ID
            "Adf-Window-Id": self.__Adf_Window_Id,
            "Adf-Page-Id": self.__Adf_Page_Id,
            "javax.faces.ViewState": self.__javax_faces_ViewState,
        }

    @check_session
    def update_view_state(self) -> None:
        """Refresh the javax.faces.ViewState token by fetching current page.

        Oracle ADF's ViewState token changes with each server interaction.
        This method fetches the latest ViewState and updates the request_dict.

        ## Raises
            SiaSessionException.SessionNotSet: If no session exists

        ## Note
            ### Logic
            - Makes GET request to current SIA page
            - Uses regex to extract ViewState from HTML (faster than BeautifulSoup for single value)
            - Updates both __javax_faces_ViewState and request_dict
        """
        r = self.get_request(self.__url, params=self.__params)

        # Target: Oracle ADF JSF → <input type="hidden" name="javax.faces.ViewState" value="...">
        view_state_regex = re.compile(
            b'<input type="hidden" name="javax.faces.ViewState" value="(.*?)">'
        )
        match = view_state_regex.search(r.content)
        if match is None:
            raise SiaSessionException.SessionNotSet from ValueError("ViewState regex did not match")
        view_state = match.group(1)

        self.__javax_faces_ViewState = view_state.decode("utf-8")
        self.request_dict["javax.faces.ViewState"] = self.__javax_faces_ViewState

    @check_session
    def set_career(self, search_code: str, electives: bool = False) -> "SiaSession":
        """Navigate to a specific academic career and load its course list.

        This method orchestrates a sequence of Oracle ADF interactions to navigate
        through SIA's dropdown-based search form and load the course catalog.

        ## Args
            search_code: Hyphen-delimited code (format: "level-campus-faculty-career")
                        ### Example
                        "1-3-5-2345" where indices correspond to dropdown positions
            electives: If True, load elective courses instead of regular courses (default: False)

        ## Returns
            self (for method chaining)

        ## Raises
            SiaSessionException.SessionNotSet: If no session exists

        ## Note
            # Logic (Regular courses - 6 requests):
            1. Select study level dropdown → Triggers faculty dropdown population
            2. Select campus dropdown → Filter faculties by campus
            3. Select faculty dropdown → Triggers career dropdown population
            4. Select career dropdown → Enable "Mostrar" button
            5. Select typology dropdown → Filter course types (optional)
            6. Click "Mostrar" button → Load course list

            # Logic (Electives - 8 requests):
            Steps 1-5 same as regular, then:
            6. Select faculty/plan dropdown → Enable electives campus selector
            7. Select electives campus → Apply campus offset (+40)
            8. Click "Mostrar" button → Load elective course list

            # TODO: Refactor - Investigate why get_course_xml(0) is needed at end
            Without that call, subsequent set_career() calls fail (Oracle ADF state issue?)
        """

        if electives:
            self.__tipology_index = "7"  # TODO: Extract to constant - "7" = electives typology
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
        self.request_dict["javax.faces.ViewState"] = self.__javax_faces_ViewState

        # Execute request sequence in order (ORDER IS CRITICAL - Oracle ADF enforces workflow)
        response = None
        for data in data_list:
            response = self.post_request(data=data)

            # Extract career name from FACULTY dropdown response XML
            # Target: Oracle ADF dropdown XML → <option> element at career index
            if data == FACULTY_DD_data:
                xml = response.text
                soup = BeautifulSoup(xml, "lxml")
                # TODO: Refactor - Magic index +1 offset to skip first "Select..." option
                career_dropdown = soup.find(id=DROPDOWNS[3])
                if career_dropdown is None:
                    raise SiaSessionException.CareerNotSet from ValueError(
                        "Career dropdown not found"
                    )
                options = career_dropdown.find_all("option")
                option_index = int(self.career_indexs[3]) + 1
                self.__career_name = options[option_index].text

        # Reset request_dict to clean state
        self.__init_request_dict()

        if response is None:
            raise SiaSessionException.CareerNotSet from ValueError(
                "No response while setting career"
            )
        xml = response.text

        # Target: Final response XML contains Oracle ADF table with course list
        self.__course_list = get_course_list(xml, "lxml")
        self.__is_electives = electives

        self.__STATUS = SiaSessionStatus.ON_CAREER_PAGE

        # TODO: Refactor - Workaround for Oracle ADF state issue
        # Without this, subsequent set_career() calls fail. Investigate root cause.
        self.get_course_xml(0)

        return self

    @check_status(SiaSessionStatus.ON_CAREER_PAGE)
    def __select_course_row(self, course_index: int) -> None:
        """Select (highlight) a course row in the Oracle ADF table.

        ## Args
            course_index: Index of course in course_list (0-based)

        ## Raises
            SiaSessionException.InvalidStatus: If not on career page

        ## Note
            This ONLY highlights the row, does not navigate to course details.
            Oracle ADF requires this before clicking COURSE_PAGE_LINK.
        """
        self.__init_request_dict()
        self.post_request(self._generate_request_body(SELECT_ROW, course_index))

    @check_status(SiaSessionStatus.ON_CAREER_PAGE)
    def enter_course_page(self, course_index: int) -> Any:
        """Navigate to course detail page for a specific course.

        ## Args
            course_index: Index of course in course_list (0-based)

        ## Returns
            Response object containing course detail XML

        ## Raises
            SiaSessionException.InvalidStatus: If not on career page

        ## Note
            ### Logic
            1. Refresh ViewState (ensures fresh Oracle ADF state)
            2. Select course row (required by Oracle ADF before navigation)
            3. Reset request_dict
            4. Click course link to navigate
            5. Update STATUS to ON_COURSE_PAGE
        """
        self.update_view_state()
        self.__select_course_row(course_index)
        self.__init_request_dict()
        response = self.post_request(self._generate_request_body(COURSE_PAGE_LINK, course_index))
        self.__STATUS = SiaSessionStatus.ON_COURSE_PAGE
        return response

    @check_status(SiaSessionStatus.ON_COURSE_PAGE)
    def exit_course_page(self) -> None:
        """Return to course list from course detail page.

        Clicks the "Volver" (Back) button in Oracle ADF interface.

        ## Raises
            SiaSessionException.InvalidStatus: If not on course page

        ## Note
            # TODO: Refactor - Use _generate_request_body instead of manual dict
            After exiting, selects row index 1 (workaround for Oracle ADF navigation quirk)
        """
        # TODO: Refactor - Replace manual dict with _generate_request_body(BACK_BTTN)
        data = {
            "org.apache.myfaces.trinidad.faces.FORM": "f1",
            "Adf-Window-Idl": self.__Adf_Window_Id,
            "Adf-Page-Id": self.__Adf_Page_Id,
            "javax.faces.ViewState": self.__javax_faces_ViewState,
            "event": BACK_BTTN_ID,
            f"event.{BACK_BTTN_ID}": BTTN_EVENT_VALUE,
            "oracle.adf.view.rich.PROCESS": f"pt1:r1,{BACK_BTTN_ID}4",
        }
        self.post_request(data)
        self.__STATUS = SiaSessionStatus.ON_CAREER_PAGE

        # TODO: Document - Why select row 1 after exiting? Oracle ADF quirk?
        self.__select_course_row(1)

    @check_status(SiaSessionStatus.ON_CAREER_PAGE)
    def get_course_xml(self, course_index: int) -> str:
        """Retrieve course detail XML for a specific course.

        This is a convenience method that:
        1. Enters course detail page
        2. Captures the XML response
        3. Exits back to course list

        ## Args
            course_index: Index of course in course_list (0-based)

        ## Returns
            Oracle ADF XML containing course details (groups, schedules, prerequisites, etc.)

        ## Raises
            SiaSessionException.InvalidStatus: If not on career page

        ## Note
            # BUG: Known issue - If you request index 1 immediately after index 0, request fails
            # Workaround: Always request index 0 first, or add delay between requests
            # TODO: Investigate Oracle ADF state machine to fix root cause
        """
        xml = self.enter_course_page(course_index).text
        self.exit_course_page()
        # BUG: Oracle ADF navigation quirk - consecutive requests to index 1 after 0 fail

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

    def __generate_specific_request_dict(
        self, id: str, event_type: str, idx: int = -1
    ) -> dict[str, str]:
        """Generate a request dictionary for a specific Oracle ADF interaction.

        ## Args
            id: Oracle ADF component ID (e.g., STUDY_LEVEL_DD_ID)
            event_type: Oracle RichClient XML event payload (e.g., DROPDOWN_EVENT_VALUE)
            idx: Optional table row index for row-based events (default: -1 = not a row event)

        ## Returns
            Complete request dictionary (request_dict + event_dict)

        ## Note
            ### Logic
            1. Get event dict for the specific interaction
            2. Copy request_dict boilerplate
            3. Merge event fields into copy
            4. Return augmented dictionary
        """
        event_dict = self.__get_event_dict(id, event_type, idx)
        request_dict_copy = self.request_dict.copy()

        for key, value in event_dict.items():
            request_dict_copy[key] = value

        return request_dict_copy

    def __get_event_dict(self, id: str, event_type: str, idx: int = -1) -> dict[str, str]:
        """Generate Oracle ADF event fields for a specific component interaction.

        ## Args
            id: Oracle ADF component ID
            event_type: Oracle RichClient XML event payload
            idx: Optional table row index (if >= 0, modifies id with row suffix)

        ## Returns
            Dictionary with Oracle ADF event fields (event, event.{id}, oracle.adf.view.rich.PROCESS)

        ## Note
            ### Logic
            - For table rows (idx >= 0): Append ":{idx}:cl2" to component ID
            - For dropdowns/row selections: PROCESS = component ID
            - For buttons: PROCESS = "pt1:r1,{id}" (different Oracle ADF format)

            # TODO: Refactor - Extract "pt1:r1" prefix and ":cl2" suffix as constants
        """
        if idx >= 0:
            # Oracle ADF table row ID format: {table_id}:{row_index}:cl2
            id = f"{id}:{idx}:cl2"

        process_value = id
        if event_type == DROPDOWN_EVENT_VALUE or event_type == SELECT_ROW_EVENT_VALUE:
            process_value = id
        elif event_type == BTTN_EVENT_VALUE:
            # Oracle ADF button process format differs from dropdown/selection
            process_value = f"pt1:r1,{id}"  # TODO: Extract "pt1:r1" as constant

        return {
            "event": id,
            f"event.{id}": event_type,
            "oracle.adf.view.rich.PROCESS": process_value,
        }

    def _generate_request_body(self, data_name: str, idx: int = -1) -> dict[str, str]:
        """Generate complete Oracle ADF request body for a named action.

        ## Args
            data_name: Logical action name from DATA_MAP (e.g., STUDY_LEVEL_DD, SHOW_COURSES_BTTN)
            idx: Optional table row index for row-based actions (default: -1)

        ## Returns
            Complete request body dictionary ready for POST to SIA

        ## Raises
            KeyError: If data_name not found in DATA_MAP

        ## Note
            ### Logic
            1. Look up (component_id, event_xml) from DATA_MAP
            2. Add action-specific fields to request_dict (e.g., electives campus offset)
            3. Generate specific request dict with event fields
            4. Add final action-specific fields (e.g., table viewport size for SELECT_ROW)
            5. Return complete request body

            # Special handling:
            - FACULTY_CAREER_DD: Sets dropdown value to "0" (first option)
            - CAMPUS_ELECTIVES_DD: Adds +40 offset to campus index (SIA electives convention)
            - SELECT_ROW: Includes table viewport metadata (viewportSize, rows, selectedRowKeys)
            - COURSE_PAGE_LINK: Includes render directive for Oracle ADF partial page rendering
        """
        if data_name in DATA_MAP:
            id, event_value = DATA_MAP[data_name]

            # Add specific fields to request_dict for certain actions
            if data_name == FACULTY_CAREER_DD:
                # TODO: Extract "0" as constant - First option in faculty/career electives dropdown
                self.request_dict[FACULTY_CAREER_DD_ID] = "0"
            elif data_name == CAMPUS_ELECTIVES_DD:
                # Apply SIA electives campus offset (+40 to regular campus index)
                self.request_dict[CAMPUS_ELECTIVES_DD_ID] = str(
                    int(self.career_indexs[1]) + ELECTIVES_CAMPUS_INCREMENT
                )

            specific_request_dict = self.__generate_specific_request_dict(id, event_value, idx)

            # Add Oracle ADF-specific metadata for certain actions
            if data_name == SELECT_ROW:
                # Oracle ADF table selection requires viewport and selection metadata
                # Format: {{table_id={{viewportSize=N,rows=M,selectedRowKeys=idx}}}}
                # TODO: Refactor - Extract table metadata format as a function
                specific_request_dict["oracle.adf.view.rich.DELTAS"] = (
                    f"{{pt1:r1:0:t4={{viewportSize={len(self.__course_list) + 1},rows={len(self.__course_list)},selectedRowKeys={idx}}}}}"
                )
            elif data_name == COURSE_PAGE_LINK:
                # Oracle ADF partial page rendering directive - re-render "pt1:r1" region
                specific_request_dict["oracle.adf.view.rich.RENDER"] = "pt1:r1"

            return specific_request_dict
        raise KeyError(f"Unknown data_name in DATA_MAP: {data_name}")


# ============================================================================
# Module-Level Helper Functions
# ============================================================================


def get_course_list(html: bytes | str, parser: str) -> list[dict[str, str]]:
    """Extract course list from Oracle ADF table HTML.

    ## Args
        html: Oracle ADF page HTML (bytes or string)
        parser: BeautifulSoup parser to use ('html.parser' or 'lxml')

    ## Returns
        List of course dictionaries: [{course_code: course_name}, ...]

    ## Note
        ### Logic
        - Target: Oracle ADF table → <tr class="af_table_data-row"> elements
        - Each row contains <span class="af_column_data-container"> for code and name
        - First span = course code, second span = course name

        # Outside SiaSession class to avoid circular import issues with SiaScraper

        # TODO: Refactor - Magic indices [0] and [1] for code/name columns
        # Should verify column count or use more robust selector
    """
    html_content = html.decode("utf-8", errors="ignore") if isinstance(html, bytes) else html
    soup = BeautifulSoup(html_content, parser)

    # Target: Oracle ADF table → <tr class="af_table_data-row"> (course rows)
    rows = soup.find_all("tr", {"class": "af_table_data-row"})

    course_list = []
    for row in rows:
        # Target: Each row → <span class="af_column_data-container"> (course code & name)
        data = row.find_all("span", {"class": "af_column_data-container"})

        # TODO: Refactor - Hardcoded column indices [0]=code, [1]=name
        course_code = data[0].getText()
        course_name = data[1].getText()

        course_list.append({course_code: course_name})

    return course_list
