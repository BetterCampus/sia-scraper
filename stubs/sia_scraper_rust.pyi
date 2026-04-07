"""Type stubs for sia_scraper_rust PyO3 extension module.

This module provides type annotations for the Rust-based SIA scraper extension.
All model classes are exposed via PyO3 #[pyclass] attributes and support:
- Attribute access (e.g., course.credits)
- Pickle serialization (pickle.dumps/loads)
- String representations (__repr__, __str__)

Example:
    >>> import sia_scraper_rust
    >>> course = sia_scraper_rust.parse_course_info(xml_string)
    >>> print(course.course_name)
    "CALCULO AVANZADO"
    >>> print(course.credits)
    3
"""

from collections.abc import Awaitable
from typing import Any, Literal, TypedDict

ErrorModeStr = Literal["abort", "skip", "retry"]

class SiaScraperException(Exception):
    """Custom exception raised by sia_scraper_rust for parsing and validation errors.

    This exception is typically raised when:
    - XML/HTML parsing fails due to malformed input
    - Required fields are missing from parsed content

    Note:
        Network or HTTP-related failures in the underlying implementation may
        surface as RuntimeError rather than SiaScraperException.

    Example:
        >>> try:
        ...     sia_scraper_rust.parse_course_info("<invalid>")
        ... except sia_scraper_rust.SiaScraperException as e:
        ...     print(f"Parse error: {e}")
    """

class NetworkError(SiaScraperException):
    """Exception raised for network connectivity failures.

    This exception is raised when network operations fail due to:
    - DNS resolution failures
    - Connection refused errors
    - Network unreachable errors

    Example:
        >>> import asyncio
        >>> async def main():
        ...     session = sia_scraper_rust.PySiaSession()
        ...     try:
        ...         await session.init_session()
        ...     except sia_scraper_rust.NetworkError as e:
        ...         print(f"Network error: {e}")
        >>> asyncio.run(main())
    """

class HttpStatusError(SiaScraperException):
    """Exception raised for HTTP responses with non-success status codes.

    Contains the HTTP status code and a descriptive message about the error.
    Typically raised for 4xx and 5xx responses that indicate server or client errors.

    Example:
        >>> import asyncio
        >>> async def main():
        ...     session = sia_scraper_rust.PySiaSession()
        ...     try:
        ...         await session.set_career("0-2-8-3")
        ...     except sia_scraper_rust.HttpStatusError as e:
        ...         print(f"HTTP error: {e}")
        >>> asyncio.run(main())
    """

class SiaTimeoutError(SiaScraperException):
    """Exception raised when a request times out before completing.

    Contains the timeout value and the operation that timed out.
    Timeout errors are typically transient and may succeed on retry.

    Example:
        >>> import asyncio
        >>> import sia_scraper_rust
        >>> async def main():
        ...     session = sia_scraper_rust.PySiaSession(timeout=1)
        ...     try:
        ...         await session.scrape_course_info(0)
        ...     except sia_scraper_rust.SiaTimeoutError as e:
        ...         print(f"Timeout: {e}")
        >>> asyncio.run(main())
    """

class ParseError(SiaScraperException):
    """Exception raised when response content cannot be parsed as expected.

    This exception indicates the response body could not be parsed,
    possibly due to unexpected response format or encoding issues.

    Example:
        >>> try:
        ...     sia_scraper_rust.parse_course_info("<invalid>")
        ... except sia_scraper_rust.ParseError as e:
        ...     print(f"Parse error: {e}")
    """

class SessionError(SiaScraperException):
    """Exception raised for session state errors.

    This exception indicates the session is in an invalid state for
    the requested operation, such as:
    - Session not initialized
    - Session expired
    - Invalid session state for operation

    Example:
        >>> import asyncio
        >>> async def main():
        ...     session = sia_scraper_rust.PySiaSession()
        ...     try:
        ...         await session.set_career("0-2-8-3")
        ...     except sia_scraper_rust.SessionError as e:
        ...         print(f"Session error: {e}")
        >>> asyncio.run(main())
    """

class AbortError(SessionError):
    """Exception raised when batch operation is aborted.

    This exception is a subclass of SessionError and is raised when
    a batch scraping operation is aborted (e.g., in abort mode when
    any course fetch fails). Catching SessionError will also catch
    AbortError.

    Example:
        >>> import asyncio
        >>> async def main():
        ...     session = sia_scraper_rust.PySiaSession()
        ...     try:
        ...         await session.scrape_courses([0, 1], mode="abort")
        ...     except sia_scraper_rust.AbortError as e:
        ...         print(f"Operation aborted: {e}")
        >>> asyncio.run(main())
    """

class ScheduleModel:
    """Represents a single class schedule entry with day, time, and location.

    This model captures the scheduling information for a single time slot
    within a course group, including the day of the week, start/end times,
    and classroom location.

    Attributes:
        day: Day of the week (e.g., "Lunes", "Martes", "Miércoles").
        start_time: Start time in 24-hour format (e.g., "08:00").
        end_time: End time in 24-hour format (e.g., "10:00").
        classroom: Classroom or building identifier (e.g., "A-101", "LAB-3").

    Example:
        >>> schedule = sia_scraper_rust.ScheduleModel(
        ...     day="Lunes",
        ...     start_time="08:00",
        ...     end_time="10:00",
        ...     classroom="A-101"
        ... )
        >>> print(schedule)
        Lunes 08:00 - 10:00
    """

    day: str
    start_time: str
    end_time: str
    classroom: str

    def __init__(
        self,
        day: str,
        start_time: str,
        end_time: str,
        classroom: str,
    ) -> None:
        """Initialize a ScheduleModel instance.

        Args:
            day: Day of the week (e.g., "Lunes", "Martes").
            start_time: Start time in HH:MM format (e.g., "08:00").
            end_time: End time in HH:MM format (e.g., "10:00").
            classroom: Classroom identifier (e.g., "A-101").

        Example:
            >>> schedule = ScheduleModel("Lunes", "08:00", "10:00", "A-101")
            >>> schedule.day
            'Lunes'
        """

class GroupModel:
    """Represents a course group with teacher, schedules, and availability.

    A course group is a specific offering of a course with a designated
    teacher, schedule(s), and available spots. Courses may have multiple
    groups (e.g., Group 1, Group 2) with different schedules.

    Attributes:
        group_name: Group identifier (e.g., "Grupo 1", "Grupo 2").
        teacher: Full name of the assigned teacher.
        faculty: Faculty or department (e.g., "Ingeniería").
        course_name: Name of the course (e.g., "Cálculo Avanzado").
        schedules: List of ScheduleModel instances for this group.
        duration: Duration string (e.g., "16 semanas", "Semestral").
        schedule_type: Type of schedule (e.g., "Diurna", "Nocturna").
        spots: Number of available spots, or None if unlimited.
        code: Optional group code identifier.

    Example:
        >>> import sia_scraper_rust
        >>> schedule = sia_scraper_rust.ScheduleModel("Lunes", "08:00", "10:00", "A-101")
        >>> group = sia_scraper_rust.GroupModel(
        ...     group_name="Grupo 1",
        ...     teacher="Dr. Smith",
        ...     faculty="Ingeniería",
        ...     course_name="Cálculo",
        ...     schedules=[schedule],
        ...     duration="16 semanas",
        ...     schedule_type="Diurna",
        ...     spots=30,
        ...     code="1000001"
        ... )
        >>> group.teacher
        'Dr. Smith'
    """

    group_name: str
    teacher: str
    faculty: str
    course_name: str
    schedules: list[ScheduleModel]
    duration: str
    schedule_type: str
    spots: int | None
    code: str | None

    def __init__(
        self,
        *,
        group_name: str,
        teacher: str,
        faculty: str,
        course_name: str,
        schedules: list[ScheduleModel],
        duration: str,
        schedule_type: str,
        spots: int | None = None,
        code: str | None = None,
    ) -> None:
        """Initialize a GroupModel instance.

        All arguments must be passed as keyword arguments.

        Args:
            group_name: Name/identifier of the group (e.g., "Grupo 1").
            teacher: Full name of the teacher.
            faculty: Faculty or department name.
            course_name: Name of the course.
            schedules: List of ScheduleModel for class times.
            duration: Duration description (e.g., "16 semanas").
            schedule_type: Schedule type (e.g., "Diurna").
            spots: Available spots (None for unlimited).
            code: Optional group code.

        Example:
            >>> group = GroupModel(
            ...     group_name="Grupo 1",
            ...     teacher="Dr. Smith",
            ...     faculty="Ingeniería",
            ...     course_name="Cálculo",
            ...     schedules=[],
            ...     duration="16 semanas",
            ...     schedule_type="Diurna",
            ...     spots=30,
            ...     code="100"
            ... )
        """

class CourseInfoModel:
    """Represents complete course information including all groups and schedules.

    This is the primary model returned by parse_course_info(), containing
    comprehensive course metadata along with all available course groups.

    Attributes:
        course_name: Full name of the course (e.g., "CÁLCULO AVANZADO").
        credits: Number of academic credits for the course.
        typology: Course typology (e.g., "Obligatoria", "Electiva").
        available_spots: Total available spots across all groups.
        scrape_timestamp: ISO timestamp when data was scraped.
        groups: List of GroupModel instances representing all offerings.
        code: Optional course code identifier.

    Example:
        >>> import sia_scraper_rust
        >>> xml = '<panel><name>CALCULO</name><credits>3</credits>...</panel>'
        >>> course = sia_scraper_rust.parse_course_info(xml)
        >>> print(course.course_name)
        CALCULO
        >>> print(f"Credits: {course.credits}")
        Credits: 3
        >>> print(f"Groups: {len(course.groups)}")
        Groups: 2
    """

    course_name: str
    credits: int
    typology: str
    available_spots: int
    scrape_timestamp: str
    groups: list[GroupModel]
    code: str | None

    def __init__(
        self,
        *,
        course_name: str,
        credits: int,
        typology: str,
        available_spots: int,
        scrape_timestamp: str,
        groups: list[GroupModel] | None = None,
        code: str | None = None,
    ) -> None:
        """Initialize a CourseInfoModel instance.

        All arguments must be passed as keyword arguments.

        Args:
            course_name: Full course title.
            credits: Number of credits.
            typology: Course type (e.g., "Obligatoria").
            available_spots: Total available spots across groups.
            scrape_timestamp: ISO format timestamp of scrape time.
            groups: List of GroupModel for all course offerings.
            code: Optional course code.

        Example:
            >>> course = CourseInfoModel(
            ...     course_name="Cálculo",
            ...     credits=3,
            ...     typology="Obligatoria",
            ...     available_spots=30,
            ...     scrape_timestamp="2026-04-02 10:00:00",
            ...     groups=[],
            ...     code="1000001"
            ... )
        """

class ScrapeResult:
    """Result of a batch scraping operation.

    Contains both successful course extractions and recorded failures,
    along with convenience methods for analyzing results.

    Attributes:
        successes: List of successfully scraped CourseInfoModel instances.
        failures: List of tuples (course_index, error_message) for failed courses.

    Example:
        >>> result = await session.scrape_courses([0, 1, 2], mode="skip")
        >>> print(f"Success rate: {result.success_rate():.1%}")
        >>> for course in result.successes:
        ...     print(course.course_name)
        >>> for index, error in result.failures:
        ...     print(f"Course {index} failed: {error}")
    """

    successes: list[CourseInfoModel]
    failures: list[tuple[int, str]]

    def __init__(self) -> None:
        """Initialize an empty ScrapeResult instance."""
        ...

    def total(self) -> int:
        """Return total number of courses processed (successes + failures)."""
        ...

    def success_rate(self) -> float:
        """Return success rate as a fraction (0.0 to 1.0).

        Returns 1.0 if no courses were processed.
        """
        ...

    def __repr__(self) -> str:
        """Return human-readable summary."""
        ...

class CourseListEntryModel:
    """Represents a single course entry in the course list.

    Used within SessionStateModel to track available courses during
    a career selection session.

    Attributes:
        code: Course code identifier (e.g., "1000001").
        name: Full course name (e.g., "Cálculo I").

    Example:
        >>> entry = sia_scraper_rust.CourseListEntryModel("1000001", "Cálculo I")
        >>> entry.code
        '1000001'
    """

    code: str
    name: str

    @property
    def course_code(self) -> str:
        """Deprecated: use code instead. Will be removed in v4.0.0."""
        ...
    @property
    def course_name(self) -> str:
        """Deprecated: use name instead. Will be removed in v4.0.0."""
        ...

    def __init__(self, code: str, name: str) -> None:
        """Initialize a CourseListEntryModel instance.

        Args:
            code: Course code identifier.
            name: Full course name.

        Example:
            >>> entry = CourseListEntryModel("1000001", "Cálculo I")
        """

    def to_dict(self) -> CourseListEntry:
        """Convert to dictionary with "code" and "name" keys.

        Returns:
            CourseListEntry with "code" and "name" string keys.
        """

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> CourseListEntryModel:
        """Create from dictionary supporting three formats.

        Supports three input formats:
        1. Current format: {"code": "1000001", "name": "Cálculo"}
        2. Legacy named keys: {"course_code": "1000001", "course_name": "Cálculo"}
        3. Legacy single-key: {"1000001": "Cálculo"} (key=code, value=name)

        Args:
            data: Dictionary in one of the supported formats above.

        Returns:
            CourseListEntryModel instance.

        Example:
            >>> # Current format
            >>> CourseListEntryModel.from_dict({"code": "1000001", "name": "Cálculo"})
            >>> # Legacy named keys
            >>> CourseListEntryModel.from_dict({"course_code": "1000001", "course_name": "Cálculo"})
            >>> # Legacy single-key
            >>> CourseListEntryModel.from_dict({"1000001": "Cálculo"})
        """

class SessionStateModel:
    """Represents the complete session state for SIA interactions.

    This model encapsulates all HTTP state (headers, cookies), SIA parameters,
    ViewState for Oracle ADF, career info, and the course list. It supports
    pickle serialization for session persistence.

    Attributes:
        session_headers: HTTP headers used in requests.
        session_cookies: Session cookies (e.g., JSESSIONID).
        params: Oracle ADF parameters and state.
        javax_faces_view_state: Oracle ADF ViewState string.
        career_code: Selected career code.
        career_name: Selected career name.
        is_electives: Whether viewing electives (True) or required courses (False).
        status: Current session status (e.g., "ON_CAREER_PAGE").
        course_list: List of CourseListEntryModel for available courses.
        generation: Counter for detecting stale state updates (for concurrency safety).

    Example:
        >>> import asyncio
        >>> import pickle
        >>> import sia_scraper_rust
        >>>
        >>> async def main() -> None:
        ...     state = await sia_scraper_rust.init_sia_session(timeout=30)
        ...     print(state.career_code)
        ...     saved = pickle.dumps(state)
        ...     restored = pickle.loads(saved)
        ...     print(restored.career_name)
        >>>
        >>> asyncio.run(main())
    """

    session_headers: dict[str, str]
    session_cookies: dict[str, str]
    params: dict[str, str]
    javax_faces_view_state: str | None
    career_code: str
    career_name: str
    is_electives: bool
    status: str
    course_list: list[CourseListEntryModel]
    generation: int

    def __init__(
        self,
        *,
        session_headers: dict[str, str],
        session_cookies: dict[str, str],
        params: dict[str, str],
        career_code: str,
        career_name: str,
        is_electives: bool,
        status: str,
        course_list: list[CourseListEntryModel],
        javax_faces_view_state: str | None = None,
        generation: int = 0,
    ) -> None:
        """Initialize a SessionStateModel instance.

        All arguments must be passed as keyword arguments.

        Args:
            session_headers: HTTP request headers.
            session_cookies: Session cookies dict.
            params: ADF parameters dict.
            career_code: Career code (e.g., "0-2-8-3").
            career_name: Career name (e.g., "Ingeniería de Sistemas").
            is_electives: True for electives, False for required.
            status: Session status string.
            course_list: List of available courses.
            javax_faces_view_state: Oracle ADF ViewState (optional).
            generation: Counter for concurrency safety (optional).

        Example:
            >>> state = SessionStateModel(
            ...     session_headers={"User-Agent": "python"},
            ...     session_cookies={"JSESSIONID": "abc"},
            ...     params={"page": "1"},
            ...     career_code="0-2-8-3",
            ...     career_name="Ingeniería",
            ...     is_electives=False,
            ...     status="ON_CAREER_PAGE",
            ...     course_list=[],
            ...     javax_faces_view_state="viewstate",
            ...     generation=0
            ... )
        """

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for transport/persistence.

        Returns:
            Dictionary containing all session state including course_list
            with "code" and "name" keys.
        """

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionStateModel:
        """Create from dictionary (supports legacy course keys).

        Supports three course entry formats:
        1. Current format: {"code": "1000001", "name": "Cálculo"}
        2. Legacy named keys: {"course_code": "1000001", "course_name": "Cálculo"}
        3. Legacy single-key: {"1000001": "Cálculo"} (key=code, value=name)

        Args:
            data: Dictionary with session state. Course entries can use
                any of the supported formats above.

        Returns:
            SessionStateModel instance.
        """

class PrerequisiteModel:
    """Represents a single prerequisite course.

    Attributes:
        course_code: Code of the prerequisite course.
        course_name: Name of the prerequisite course.

    Example:
        >>> prereq = sia_scraper_rust.PrerequisiteModel("1000001", "Cálculo I")
        >>> prereq.course_code
        '1000001'
    """

    course_code: str
    course_name: str

    def __init__(self, course_code: str, course_name: str) -> None:
        """Initialize a PrerequisiteModel instance.

        Args:
            course_code: Prerequisite course code.
            course_name: Prerequisite course name.

        Example:
            >>> prereq = PrerequisiteModel("1000001", "Cálculo I")
        """

class PrereqConditionModel:
    """Represents a prerequisite condition with multiple courses.

    A condition defines a group of courses that satisfy a prerequisite
    requirement. The condition specifies whether all courses are required
    or just a subset.

    Attributes:
        condition: Condition identifier (1, 2, 3, ...).
        prereq_type: Type of prerequisite (e.g., "CURSOS", "CERTIFICADO").
        all_required: True if all courses required, False if any allowed.
        number_of_courses: Number of courses in this condition.
        prerequisites: List of PrerequisiteModel for required courses.

    Example:
        >>> prereq = sia_scraper_rust.PrerequisiteModel("1000001", "Cálculo I")
        >>> condition = sia_scraper_rust.PrereqConditionModel(
        ...     condition=1,
        ...     prereq_type="CURSOS",
        ...     all_required=True,
        ...     number_of_courses=1,
        ...     prerequisites=[prereq]
        ... )
        >>> condition.all_required
        True
    """

    condition: int
    prereq_type: str
    all_required: bool
    number_of_courses: int
    prerequisites: list[PrerequisiteModel]

    def __init__(
        self,
        *,
        condition: int,
        prereq_type: str,
        all_required: bool,
        number_of_courses: int,
        prerequisites: list[PrerequisiteModel] | None = None,
    ) -> None:
        """Initialize a PrereqConditionModel instance.

        All arguments must be passed as keyword arguments.

        Args:
            condition: Condition number (1, 2, ...).
            prereq_type: Type string (e.g., "CURSOS").
            all_required: True if all must be completed.
            number_of_courses: Number of courses in condition.
            prerequisites: List of required courses.

        Example:
            >>> cond = PrereqConditionModel(
            ...     condition=1,
            ...     prereq_type="CURSOS",
            ...     all_required=True,
            ...     number_of_courses=1,
            ...     prerequisites=[]
            ... )
        """

class CoursePrereqsModel:
    """Represents complete prerequisite information for a course.

    This model is returned by parse_prereqs() and contains all prerequisite
    conditions that must be satisfied to enroll in a course.

    Attributes:
        course_name: Name of the course.
        code: Course code (None if not available).
        credits: Number of credits for the course.
        typology: Course typology (e.g., "Obligatoria").
        conditions: List of PrereqConditionModel for prerequisites.

    Example:
        >>> import sia_scraper_rust
        >>> xml = '<panel><name>ALGEBRA</name><credits>4</credits>...</panel>'
        >>> prereqs = sia_scraper_rust.parse_prereqs(xml)
        >>> print(prereqs.course_name)
        ALGEBRA
        >>> print(f"Conditions: {len(prereqs.conditions)}")
        Conditions: 2
    """

    course_name: str
    code: str | None
    credits: int
    typology: str
    conditions: list[PrereqConditionModel]

    def __init__(
        self,
        *,
        course_name: str,
        credits: int,
        typology: str,
        conditions: list[PrereqConditionModel] | None = None,
        code: str | None = None,
    ) -> None:
        """Initialize a CoursePrereqsModel instance.

        All arguments must be passed as keyword arguments.

        Args:
            course_name: Name of the course.
            credits: Number of credits.
            typology: Course typology (e.g., "Obligatoria").
            conditions: List of prerequisite conditions.
            code: Course code (optional).

        Example:
            >>> model = CoursePrereqsModel(
            ...     course_name="Álgebra",
            ...     credits=4,
            ...     typology="Obligatoria",
            ...     conditions=[],
            ...     code="1000002"
            ... )
        """

def parse_course_info(xml: str) -> CourseInfoModel:
    """Parse course information from Oracle ADF XML/HTML response.

    Extracts comprehensive course data including course name, credits, typology,
    and all available groups with their schedules.

    Args:
        xml: Raw XML/HTML string from SIA course detail page.

    Returns:
        CourseInfoModel with course metadata and list of groups.

    Raises:
        SiaScraperException: If course name or credits not found in XML.

    Example:
        >>> import sia_scraper_rust
        >>> xml = '''
        ... <panel>
        ...   <name>CALCULO AVANZADO</name>
        ...   <credits>3</credits>
        ...   <typology>Obligatoria</typology>
        ... </panel>
        ... '''
        >>> course = sia_scraper_rust.parse_course_info(xml)
        >>> print(course.course_name)
        CALCULO AVANZADO
        >>> print(course.credits)
        3
    """

def parse_course_info_json(xml: str) -> str:
    """Parse course information and return a JSON string representation.

    Deprecated:
        Use `parse_course_info()` to get `CourseInfoModel` directly.

    This function is kept for backwards compatibility with callers that still
    need JSON serialization.

    Args:
        xml: Raw XML/HTML string from SIA course detail page.

    Returns:
        JSON string with course data.

    Example:
        >>> json_str = sia_scraper_rust.parse_course_info_json(xml)
        >>> import json
        >>> data = json.loads(json_str)
    """

def extract_view_state(html: str) -> str:
    """Extract the ViewState value from Oracle ADF HTML response.

    ViewState is a hidden form field used by Oracle ADF for state management.
    This function extracts the value from the javax.faces.ViewState input.

    Args:
        html: Raw HTML string from SIA Oracle ADF response.

    Returns:
        ViewState string value extracted from hidden input element.

    Raises:
        SiaScraperException: If ViewState element not found.

    Example:
        >>> html = '<input name="javax.faces.ViewState" value="0-2-8-3" />'
        >>> view_state = sia_scraper_rust.extract_view_state(html)
        >>> print(view_state)
        0-2-8-3
    """

def parse_prereqs(xml: str) -> CoursePrereqsModel:
    """Parse prerequisite information from Oracle ADF XML/HTML response.

    Extracts prerequisite conditions that must be satisfied to enroll in a course.

    Args:
        xml: Raw XML/HTML string from SIA course prerequisites page.

    Returns:
        CoursePrereqsModel with course info and prerequisite conditions.

    Raises:
        SiaScraperException: If course name or credits not found in XML.

    Example:
        >>> import sia_scraper_rust
        >>> xml = '''
        ... <panel>
        ...   <name>ALGEBRA</name>
        ...   <credits>4</credits>
        ...   <typology>Obligatoria</typology>
        ... </panel>
        ... '''
        >>> prereqs = sia_scraper_rust.parse_prereqs(xml)
        >>> print(prereqs.course_name)
        ALGEBRA
    """

def parse_prereqs_json(xml: str) -> str:
    """Parse prerequisite information and return a JSON string representation.

    Deprecated:
        Use `parse_prereqs()` to get `CoursePrereqsModel` directly.

    This function is kept for backwards compatibility with callers that still
    need JSON serialization.

    Args:
        xml: Raw XML/HTML string from SIA course prerequisites page.

    Returns:
        JSON string with prerequisite data.
    """

class CourseListEntry(TypedDict):
    """A single course entry with code and name."""

    code: str
    name: str

def get_course_list(html: str | bytes) -> list[CourseListEntry]:
    """Extract course list from Oracle ADF table HTML.

    Parses the course selection table from a career page and returns
    a list of dictionaries with "code" and "name" keys.

    Args:
        html: Raw HTML string or bytes from SIA course list page.

    Returns:
        List of CourseListEntry dicts with "code" and "name" keys,
        e.g. [{"code": "1000001", "name": "Cálculo I"}].

    Example:
        >>> html = '''
        ... <tr class="af_table_data-row">
        ...     <td><span class="af_column_data-container">1000001</span></td>
        ...     <td><span class="af_column_data-container">Cálculo I</span></td>
        ... </tr>
        ... '''
        >>> courses = sia_scraper_rust.get_course_list(html)
        >>> courses[0]["code"]
        '1000001'
        >>> courses[0]["name"]
        'Cálculo I'
    """

def get_plain_text(xml: str) -> str:
    """Extract plain text content from XML panel elements.

    Utility function to extract text content from XML while stripping
    HTML/XML tags and normalizing whitespace.

    Args:
        xml: XML string to extract text from.

    Returns:
        Cleaned plain text content.

    Example:
        >>> xml = '<name>  CALCULO  </name>'
        >>> text = sia_scraper_rust.get_plain_text(xml)
        >>> text
        'CALCULO'
    """

def init_oracle_adf_request_dict(
    tipology_index: str,
    window_id: str,
    page_id: str,
    view_state: str,
) -> dict[str, Any]:
    """Initialize Oracle ADF request dictionary for SIA interactions.

    Builds the standard ADF request payload structure used for SIA HTTP requests.

    Args:
        tipology_index: Tipology/career index identifier.
        window_id: ADF window ID.
        page_id: ADF page ID.
        view_state: ViewState string.

    Returns:
        Dictionary with ADF request structure.

    Example:
        >>> req = sia_scraper_rust.init_oracle_adf_request_dict("0-2-8-3", "w1", "p1", "vs1")
        >>> req['tipologyIndex']
        '0-2-8-3'
    """

def build_oracle_adf_request_body(
    request_dict: dict[str, Any],
    data_name: str,
    idx: int,
    career_indices: list[str],
    course_list_len: int,
) -> dict[str, Any]:
    """Build Oracle ADF request body with course selection data.

    Constructs the full ADF request payload including form data for
    course selection interactions.

    Args:
        request_dict: Base ADF request dict from init_oracle_adf_request_dict.
        data_name: Data field name for course data.
        idx: Index of selected course.
        career_indices: List of career indices.
        course_list_len: Length of course list.

    Returns:
        Complete ADF request body dictionary.

    Example:
        >>> base = init_oracle_adf_request_dict("0-2-8-3")
        >>> body = build_oracle_adf_request_body(base, "course", 0, ["0-2-8-3"], 10)
    """

def get_oracle_adf_event_dict(
    id: str,
    event_type: str,
    idx: int,
) -> dict[str, Any]:
    """Build Oracle ADF event dictionary for AJAX events.

    Creates the event payload for ADF partial page updates (AJAX).

    Args:
        id: Component ID triggering the event.
        event_type: Type of event (e.g., "action", "valueChange").
        idx: Event index.

    Returns:
        ADF event dictionary.

    Example:
        >>> event = sia_scraper_rust.get_oracle_adf_event_dict("btn1", "action", 0)
    """

def async_get(url: str) -> Awaitable[dict[str, Any]]:
    """Perform async HTTP GET request (stub).

    Note: This is a stub function. Use Python SiaSession for actual async HTTP.
    """

def async_post(url: str, body: str) -> Awaitable[dict[str, Any]]:
    """Perform async HTTP POST request (stub).

    Note: This is a stub function. Use Python SiaSession for actual async HTTP.
    """

def async_get_with_config(
    url: str,
    timeout: int | None = None,
    user_agent: str | None = None,
) -> Awaitable[dict[str, Any]]:
    """Perform async HTTP GET with custom configuration (stub).

    Note: This is a stub function. Use Python SiaSession for actual async HTTP.

    Args:
        url: Target URL.
        timeout: Request timeout in seconds.
        user_agent: Custom User-Agent string.
    """

def init_sia_session(timeout: int | None = None) -> Awaitable[SessionStateModel]:
    """Initialize a new SIA session with HTTP configuration (stub).

    Note: This is a stub. Use Python sia_scraper.SiaSession for actual session.

    Args:
        timeout: Request timeout in seconds (default: 30).

    Returns:
        SessionStateModel with initialized state.
    """

def init_sia_session_json(timeout: int | None = None) -> Awaitable[str]:
    """Initialize SIA session and return typed JSON state payload."""

def set_career(
    timeout: int | None = None,
    search_code: str = "",
    electives: bool | None = None,
) -> Awaitable[SessionStateModel]:
    """Set career selection in SIA session (stub).

    Note: This is a stub. Use Python sia_scraper.SiaSession.set_career() instead.

    Args:
        timeout: Request timeout in seconds.
        search_code: Career search code.
        electives: True for electives, False for required.

    Returns:
        SessionStateModel with career selection.
    """

def set_career_json(
    timeout: int | None = None,
    search_code: str = "",
    electives: bool | None = None,
) -> Awaitable[str]:
    """Set career and return typed JSON session payload."""

def get_course_xml(
    timeout: int | None = None,
    course_index: int = 0,
    career_indices: list[str] | None = None,
    electives: bool | None = None,
) -> Awaitable[str]:
    """Get course XML data (stub).

    Note: This is a stub. Use Python sia_scraper.SiaSession for actual course data.

    Args:
        timeout: Request timeout in seconds.
        course_index: Index of course to fetch.
        career_indices: List of career indices.
        electives: True for electives, False for required.

    Returns:
        Awaitable resolving to raw XML string.
    """

class PySiaSession:
    """Stateful SIA session for performing authenticated HTTP operations.

    This class wraps a Rust session and maintains state across method calls.
    All methods that perform network I/O are async and must be awaited.

    Supports:
    - Async context manager: `async with PySiaSession() as session:`
    - Pickle serialization: `pickle.dumps(session)` (session must be re-initialized)

    Example:
        >>> import asyncio
        >>> import sia_scraper_rust
        >>>
        >>> async def main():
        ...     async with sia_scraper_rust.PySiaSession(timeout=30) as session:
        ...         # Session is automatically initialized on entry
        ...         await session.set_career("0-2-8-3")
        ...         course = await session.scrape_course_info(0)
        ...         print(course.course_name)
        >>>
        >>> asyncio.run(main())
    """

    def __init__(self, timeout: int | None = None) -> None:
        """Create a new PySiaSession.

        Args:
            timeout: Request timeout in seconds (default: 15).
        """
        ...

    def init_session(self) -> Awaitable[SessionStateModel]:
        """Initialize the SIA session and fetch initial ViewState.

        Must be called before any other methods. Establishes HTTP session
        with SIA server and extracts Oracle ADF parameters.

        Returns:
            SessionStateModel with initial session state.

        Raises:
            NetworkError: If connection fails.
            HttpStatusError: If server returns error status.
            SiaTimeoutError: If request times out.
            ParseError: If response cannot be parsed.
            SessionError: If ViewState not found.
        """
        ...

    def set_career(
        self,
        search_code: str,
        electives: bool | None = None,
    ) -> Awaitable[SessionStateModel]:
        """Navigate to a career and load the course list.

        Args:
            search_code: Career search code (e.g., "0-2-8-3").
            electives: True for elective courses, False for required (default: False).

        Returns:
            SessionStateModel with career info and course list.

        Raises:
            SessionError: If session not initialized.
            NetworkError: If connection fails.
            HttpStatusError: If server returns error status.
            SiaTimeoutError: If request times out.
            ParseError: If response cannot be parsed.
        """
        ...

    def scrape_course_info(self, course_index: int) -> Awaitable[CourseInfoModel]:
        """Scrape course information for the given index.

        Combines HTTP fetch and parsing in a single Rust call, eliminating
        string copying across the FFI boundary.

        Args:
            course_index: Index of course in course_list (0-based).

        Returns:
            CourseInfoModel with complete course data.

        Raises:
            SessionError: If session not initialized.
            ValueError: If course_index is out of range.
            NetworkError: If connection fails.
            HttpStatusError: If server returns error status.
            SiaTimeoutError: If request times out.
            ParseError: If response cannot be parsed.
        """
        ...

    def scrape_course_prereqs(self, course_index: int) -> Awaitable[CoursePrereqsModel]:
        """Scrape prerequisite information for the given course index.

        Args:
            course_index: Index of course in course_list (0-based).

        Returns:
            CoursePrereqsModel with prerequisite conditions.

        Raises:
            SessionError: If session not initialized.
            ValueError: If course_index is out of range.
            NetworkError: If connection fails.
            HttpStatusError: If server returns error status.
            SiaTimeoutError: If request times out.
            ParseError: If response cannot be parsed.
        """
        ...

    def scrape_courses(
        self,
        indices: list[int],
        mode: ErrorModeStr,
        retries: int | None = None,
        delay: int | None = None,
    ) -> Awaitable[ScrapeResult]:
        """Scrape multiple courses sequentially with configurable error handling.

        Iterates over the provided course indices and attempts to scrape each one.
        Errors are handled according to the specified mode:

        - "abort": Stop immediately on the first error.
        - "skip": Record the failure and continue to the next course.
        - "retry": Retry failed courses up to retries times with exponential
          backoff before recording as a failure.

        Args:
            indices: List of course indices to scrape (0-based).
            mode: Error handling mode: "abort", "skip", or "retry".
            retries: Maximum retry attempts per course (default: 3).
                Used only in "retry" mode.
            delay: Base delay between retries in milliseconds (default: 800).

        Returns:
            ScrapeResult with successes and failures lists.

        Raises:
            SessionError: If session is not initialized.
            SiaScraperException: If mode is not one of "abort", "skip", "retry".
            AbortError: If an in-runtime abort occurs (abort-mode failures are rewrapped).
            NetworkError: If connection fails.
            HttpStatusError: If server returns error status.
            SiaTimeoutError: If request times out.
            ParseError: If response cannot be parsed.

        Example:
            >>> result = await session.scrape_courses([0, 1, 2], mode="skip")
            >>> print(f"Success rate: {result.success_rate():.1%}")
            >>> for course in result.successes:
            ...     print(course.course_name)
        """
        ...

    def scrape_courses_parallel(
        self,
        indices: list[int],
        mode: ErrorModeStr,
        max_concurrent: int | None = None,
        retries: int | None = None,
        delay: int | None = None,
    ) -> Awaitable[ScrapeResult]:
        """Scrape multiple courses concurrently with configurable parallelism.

        Uses Rust's tokio and futures ecosystem to execute up to
        max_concurrent scraping operations simultaneously. This can provide
        significant speedups (3x-5x) compared to sequential scraping for
        batches of 20+ courses.

        Errors are handled according to the specified mode:

        - "abort": Stop immediately on the first error.
        - "skip": Record the failure and continue to the next course.
        - "retry": Retry failed courses up to retries times with exponential
          backoff before recording as a failure.

        Args:
            indices: List of course indices to scrape (0-based).
            mode: Error handling mode: "abort", "skip", or "retry".
            max_concurrent: Maximum number of concurrent scraping operations (default: 5).
            retries: Maximum retry attempts per course (default: 3).
                Used only in "retry" mode.
            delay: Base delay between retries in milliseconds (default: 800).

        Returns:
            ScrapeResult with successes and failures lists.

        Raises:
            SessionError: If session is not initialized.
            SiaScraperException: If mode is not one of "abort", "skip", "retry".
            AbortError: If an in-runtime abort occurs (abort-mode failures are rewrapped).
            NetworkError: If connection fails.
            HttpStatusError: If server returns error status.
            SiaTimeoutError: If request times out.
            ParseError: If response cannot be parsed.

        Example:
            >>> result = await session.scrape_courses_parallel([0, 1, 2], mode="skip", max_concurrent=5)
            >>> print(f"Success rate: {result.success_rate():.1%}")
            >>> for course in result.successes:
            ...     print(course.course_name)
        """
        ...

    def get_state(self) -> Awaitable[SessionStateModel]:
        """Get the current session state.

        Returns:
            SessionStateModel with current session state.

        Raises:
            SessionError: If session not initialized.
        """
        ...

    @property
    def timeout(self) -> int:
        """Get the request timeout in seconds.

        Returns:
            Timeout value in seconds (default: 15).
        """
        ...

    def is_initialized(self) -> bool:
        """Check if the session has been initialized.

        Returns:
            True if init_session() has been called, False otherwise.
        """
        ...

    def __getstate__(self) -> dict[str, Any]:
        """Get state for pickle serialization.

        Returns only the timeout configuration, not the actual session.
        Session must be re-initialized after unpickling.
        """
        ...

    def __setstate__(self, state: dict[str, Any]) -> None:
        """Restore session from pickled state.

        The session will need to be re-initialized after unpickling.
        """
        ...

    def __aenter__(self) -> Awaitable[PySiaSession]:
        """Async context manager entry.

        Automatically initializes session if not already initialized.

        Returns:
            Self for use in `async with` statement.

        Raises:
            SessionError: If session not initialized.
            NetworkError: If connection fails.
            HttpStatusError: If server returns error status.
            SiaTimeoutError: If request times out.
            ParseError: If response cannot be parsed.
        """
        ...

    def __aexit__(
        self,
        exc_type: type | None,
        exc_val: BaseException | None,
        exc_tb: Any | None,
    ) -> Awaitable[None]:
        """Async context manager exit.

        Currently a no-op.
        """
        ...

    def reset(self) -> Awaitable[None]:
        """Reset the session state, clearing the underlying Rust session.

        This drops the SiaSession inside the wrapper, releasing all
        resources including HTTP connections and cookies. The PySiaSession
        can be re-initialized by calling init_session() again.

        Returns:
            None

        Example:
            >>> await session.init_session()
            >>> # ... use session ...
            >>> await session.reset()
            >>> # Session is now cleared, can call init_session() again
        """
        ...

    @staticmethod
    async def from_state(state: dict[str, Any], timeout: int | None = None) -> PySiaSession:
        """Restore a session from previously saved state.

        This static method creates a new PySiaSession with an already
        initialized Rust session restored from the provided state.

        Args:
            state: Dictionary with session state data (timeout, state_dict).
            timeout: Request timeout in seconds (default: 15).

        Returns:
            New PySiaSession with restored state.

        Raises:
            KeyError: If 'state_dict' key is missing from input.
            TypeError: If state_dict is not a dictionary.
            ValueError: If state_dict contains invalid model data.
            SessionError: If state_dict is invalid or restoration fails.
            NetworkError: If connection fails during restoration.
            HttpStatusError: If server returns error status.
            SiaTimeoutError: If request times out.

        Example:
            >>> state = {"timeout": 15, "state_dict": {...}}
            >>> session = await PySiaSession.from_state(state)
        """
        ...

    def get_session_data(self) -> Awaitable[dict[str, Any]]:
        """Get session data for persistence.

        Returns the complete session state including headers, cookies,
        ViewState, career info, and course list as a dictionary.

        Returns:
            Dictionary with session data suitable for pickling/serialization.

        Raises:
            SessionError: If session not initialized.

        Example:
            >>> data = await session.get_session_data()
            >>> # Save to file or database
        """
        ...
