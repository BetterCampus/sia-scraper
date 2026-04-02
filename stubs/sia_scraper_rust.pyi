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

from typing import Any

class SiaScraperException(Exception):
    """Custom exception raised by sia_scraper_rust when parsing or HTTP operations fail.

    This exception is raised when:
    - XML/HTML parsing fails due to malformed input
    - Required fields are missing from parsed content
    - HTTP requests fail (connection errors, timeouts)

    Example:
        >>> try:
        ...     sia_scraper_rust.parse_course_info("<invalid>")
        ... except sia_scraper_rust.SiaScraperException as e:
        ...     print(f"Parse error: {e}")
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
        group_name: str,
        teacher: str,
        faculty: str,
        course_name: str,
        schedules: list[ScheduleModel],
        duration: str,
        schedule_type: str,
        spots: int | None,
        code: str | None,
    ) -> None:
        """Initialize a GroupModel instance.

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
            ...     "Grupo 1", "Dr. Smith", "Ingeniería",
            ...     "Cálculo", [], "16 semanas", "Diurna", 30, "100"
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
        course_name: str,
        credits: int,
        typology: str,
        available_spots: int,
        scrape_timestamp: str,
        groups: list[GroupModel],
        code: str | None,
    ) -> None:
        """Initialize a CourseInfoModel instance.

        Args:
            course_name: Full course title.
            credits: Number of credits.
            typology: Course type (e.g., "Obligatoria").
            available_spots: Total available spots across groups.
            scrape_timestamp: ISO format timestamp of scrape time.
            groups: List of GroupModel for all course offerings.
            code: Optional course code.

        Example:
            >>> course = CourseInfoModel("Cálculo", 3, "Obligatoria", 30,
            ...                          "2026-04-02 10:00:00", [], "1000001")
        """

class CourseListEntryModel:
    """Represents a single course entry in the course list.

    Used within SessionStateModel to track available courses during
    a career selection session.

    Attributes:
        course_code: Course code identifier (e.g., "1000001").
        course_name: Full course name (e.g., "Cálculo I").

    Example:
        >>> entry = sia_scraper_rust.CourseListEntryModel("1000001", "Cálculo I")
        >>> entry.course_code
        '1000001'
    """

    course_code: str
    course_name: str

    def __init__(self, course_code: str, course_name: str) -> None:
        """Initialize a CourseListEntryModel instance.

        Args:
            course_code: Course code identifier.
            course_name: Full course name.

        Example:
            >>> entry = CourseListEntryModel("1000001", "Cálculo I")
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

    Example:
        >>> import sia_scraper_rust
        >>> state = sia_scraper_rust.init_sia_session(timeout=30)
        >>> print(state.career_code)
        0-2-8-3
        >>> # Save session for later use
        >>> import pickle
        >>> saved = pickle.dumps(state)
        >>> restored = pickle.loads(saved)
        >>> restored.career_name
        'Ingeniería de Sistemas'
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

    def __init__(
        self,
        session_headers: dict[str, str],
        session_cookies: dict[str, str],
        params: dict[str, str],
        career_code: str,
        career_name: str,
        is_electives: bool,
        status: str,
        course_list: list[CourseListEntryModel],
        javax_faces_view_state: str | None = None,
    ) -> None:
        """Initialize a SessionStateModel instance.

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

        Example:
            >>> state = SessionStateModel(
            ...     {"User-Agent": "python"}, {"JSESSIONID": "abc"},
            ...     {"page": "1"}, "0-2-8-3", "Ingeniería",
            ...     False, "ON_CAREER_PAGE", [], "viewstate"
            ... )
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
        condition: int,
        prereq_type: str,
        all_required: bool,
        number_of_courses: int,
        prerequisites: list[PrerequisiteModel],
    ) -> None:
        """Initialize a PrereqConditionModel instance.

        Args:
            condition: Condition number (1, 2, ...).
            prereq_type: Type string (e.g., "CURSOS").
            all_required: True if all must be completed.
            number_of_courses: Number of courses in condition.
            prerequisites: List of required courses.

        Example:
            >>> cond = PrereqConditionModel(1, "CURSOS", True, 1, [])
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
        course_name: str,
        credits: int,
        typology: str,
        conditions: list[PrereqConditionModel],
        code: str | None = None,
    ) -> None:
        """Initialize a CoursePrereqsModel instance.

        Args:
            course_name: Name of the course.
            credits: Number of credits.
            typology: Course typology (e.g., "Obligatoria").
            conditions: List of prerequisite conditions.
            code: Course code (optional).

        Example:
            >>> model = CoursePrereqsModel("Álgebra", 4, "Obligatoria", [], "1000002")
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
    """Parse course information and return JSON string (legacy endpoint).

    Note: This function is deprecated. Use parse_course_info() instead.

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
    """Parse prerequisite information and return JSON string (legacy endpoint).

    Note: This function is deprecated. Use parse_prereqs() instead.

    Args:
        xml: Raw XML/HTML string from SIA course prerequisites page.

    Returns:
        JSON string with prerequisite data.
    """

def get_course_list(html: str | bytes) -> list[dict[str, str]]:
    """Extract course list from Oracle ADF table HTML.

    Parses the course selection table from a career page and returns
    a list of course entries with their codes and names.

    Args:
        html: Raw HTML string or bytes from SIA course list page.

    Returns:
        List of dictionaries with 'code' and 'name' keys.

    Example:
        >>> html = '<table><tr><td>1000001</td><td>Cálculo I</td></tr></table>'
        >>> courses = sia_scraper_rust.get_course_list(html)
        >>> courses[0]['code']
        '1000001'
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
    window_id: str | None = None,
    page_id: str | None = None,
    view_state: str | None = None,
) -> dict[str, Any]:
    """Initialize Oracle ADF request dictionary for SIA interactions.

    Builds the standard ADF request payload structure used for SIA HTTP requests.

    Args:
        tipology_index: Tipology/career index identifier.
        window_id: ADF window ID (optional).
        page_id: ADF page ID (optional).
        view_state: ViewState string (optional, auto-generated if None).

    Returns:
        Dictionary with ADF request structure.

    Example:
        >>> req = sia_scraper_rust.init_oracle_adf_request_dict("0-2-8-3")
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

def async_get(url: str) -> Any:
    """Perform async HTTP GET request (stub).

    Note: This is a stub function. Use Python SiaSession for actual async HTTP.
    """

def async_post(url: str, body: str) -> Any:
    """Perform async HTTP POST request (stub).

    Note: This is a stub function. Use Python SiaSession for actual async HTTP.
    """

def async_get_with_config(
    url: str,
    timeout: int | None = None,
    user_agent: str | None = None,
) -> Any:
    """Perform async HTTP GET with custom configuration (stub).

    Note: This is a stub function. Use Python SiaSession for actual async HTTP.

    Args:
        url: Target URL.
        timeout: Request timeout in seconds.
        user_agent: Custom User-Agent string.
    """

def init_sia_session(timeout: int | None = None) -> SessionStateModel:
    """Initialize a new SIA session with HTTP configuration (stub).

    Note: This is a stub. Use Python sia_scraper.SiaSession for actual session.

    Args:
        timeout: Request timeout in seconds (default: 30).

    Returns:
        SessionStateModel with initialized state.
    """

def init_sia_session_json(timeout: int | None = None) -> Any:
    """Initialize SIA session and return JSON (legacy stub).

    Note: Deprecated. Use init_sia_session() instead.
    """

def set_career(
    timeout: int | None = None,
    search_code: str = "",
    electives: bool | None = None,
) -> SessionStateModel:
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
) -> Any:
    """Set career and return JSON (legacy stub).

    Note: Deprecated. Use set_career() instead.
    """

def get_course_xml(
    timeout: int | None = None,
    course_index: int = 0,
    career_indices: list[str] | None = None,
    electives: bool | None = None,
) -> Any:
    """Get course XML data (stub).

    Note: This is a stub. Use Python sia_scraper.SiaSession for actual course data.

    Args:
        timeout: Request timeout in seconds.
        course_index: Index of course to fetch.
        career_indices: List of career indices.
        electives: True for electives, False for required.

    Returns:
        Raw XML string (stub return type is Any).
    """
