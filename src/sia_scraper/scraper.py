"""SIA Scraper Orchestrator Module.

This module provides the high-level orchestration layer for scraping course data from
Universidad Nacional de Colombia's SIA (Sistema de Información Académica) system.

The SiaScraper class acts as a facade over SiaSession, delegating session management
and HTTP operations to SiaSession while handling all XML parsing and data extraction:
- Course information (name, credits, typology, groups)
- Schedule data (days, times, classrooms)
- Group details (teacher, faculty, spots, duration)
- Prerequisites and conditions

Architecture:
    SiaScraper (this module) - XML parsing, business logic, data transformation
        ↓ delegates session management to
    SiaSession - HTTP requests, Oracle ADF state management, navigation
        ↓ uses constants from
    SiaConstants - Oracle ADF component IDs, request templates, status enums

The scraper parses Oracle ADF-generated XML/HTML which uses specific CSS classes
and structural patterns. Inline comments document these selectors and parsing logic."""

import re
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup

from .constants import DEFAULT_TIMEOUT, SiaSessionStatus
from .date_formatter import DateFormatter
from .session import SiaSession


class SiaScraper:
    """High-level facade for SIA course data scraping.

    This class provides a simplified interface for scraping course information from SIA
    by delegating session management to SiaSession and handling all XML parsing logic.

    The scraper maintains career context (code, name, course list) and provides methods
    to extract course details, schedules, groups, and prerequisites from Oracle ADF XML.

    ## Typical Workflow
        1. Create scraper: sc = SiaScraper()
        2. Set career: sc.set_career("0-2-8-3")
        3. Scrape courses: course_info = sc.get_course_info(course_code="2016489")
        4. Access data: course_info["groups"][0]["schedules"]
    """

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        session_data: dict[str, Any] | None = None,
        init_session: bool = True,
    ) -> None:
        """Initialize SiaScraper with optional session restoration.

        ## Args
            timeout: HTTP request timeout in seconds for SIA operations.
            session_data: Serialized session state from get_session_data().
                If provided, restores previous session (career, course list, cookies).
            init_session: Whether to initialize a new HTTP session if session_data
                is empty. Set to False to defer session creation.

        ## Note
            Session restoration is used to avoid re-authenticating and re-navigating
            through SIA's multi-page workflow when session_data is available.
        """
        self.__career_name = "N/A"
        self.__career_code = ""
        self.__course_list = []

        if session_data is None:
            session_data = {}

        self.__sia_session = SiaSession(
            timeout=timeout, session_data=session_data, init_session=init_session
        )

        if session_data:
            if self.__sia_session.career_code != "":
                self.__career_code = self.__sia_session.career_code
                self.__career_name = self.__sia_session.career_name
                self.__course_list = self.__sia_session.course_list

    @property
    def career_name(self) -> str:
        """Human-readable name of the current academic program."""
        return self.__career_name

    @property
    def career_code(self) -> str:
        """Search code identifier for the current career (e.g., "0-2-8-3")."""
        return self.__career_code

    @property
    def course_list(self) -> list[dict[str, str]]:
        """List of course codes available in the current career."""
        return self.__course_list

    @property
    def sia_session(self) -> SiaSession:
        """Underlying SiaSession instance for direct access to session operations."""
        return self.__sia_session

    ##################### PUBLIC METHODS #####################

    # ======================== Session Management Methods ========================
    # These methods delegate to SiaSession for HTTP session lifecycle management.
    # SiaScraper adds career context synchronization on top of session operations.

    def create_session(self) -> "SiaScraper":
        """Initialize a new HTTP session with SIA's Oracle ADF backend.

        ## Returns
            Self for method chaining.

        ## Raises
            SiaSessionException.TimeoutError: If SIA server is unreachable.
        """
        self.__sia_session.init_session()
        return self

    def load_session(self, session_data: dict) -> "SiaScraper":
        """Restore a previously saved session from serialized state.

        ## Args
            session_data: Serialized session obtained from get_session_data().
                Contains cookies, Oracle ADF state tokens, career context.

        ## Returns
            Self for method chaining.

        ## Note
            If the session contains career data, synchronizes local career attributes
            (__career_code, __career_name, __course_list) with session state.
        """
        self.__sia_session.load_session(session_data)
        if self.__sia_session.career_code != "":
            self.__career_code = self.__sia_session.career_code
            self.__career_name = self.__sia_session.career_name
            self.__course_list = self.__sia_session.course_list
        return self

    def get_session_data(self) -> dict:
        """Serialize current session state for later restoration.

        ## Returns
            Dictionary containing session cookies, Oracle ADF tokens, and career context.
            Can be passed to load_session() to restore the session.

        ## Note
            Useful for persisting sessions across requests (e.g., in Flask session storage).
        """
        return self.__sia_session.get_session_data()

    def close_session(self) -> "SiaScraper":
        """Close the HTTP session and release resources.

        ## Returns
            Self for method chaining.
        """
        self.__sia_session.close_session()
        return self

    def valid_session(self) -> bool:
        """Check if the current session is still valid for SIA operations.

        ## Returns
            True if session has valid Oracle ADF tokens and is in a navigable state.
            False if session needs to be reinitialized.
        """
        return self.__sia_session.valid_session()

    # ======================== Scraping Methods ========================
    # These methods extract and parse course data from SIA's Oracle ADF XML/HTML.

    def set_career(self, search_code: str, electives: bool = False) -> "SiaScraper":
        """Navigate to a specific academic program and load its course list.

        ## Args
            search_code: Career search code from SIA (e.g., "0-2-8-3" for Computer Science).
                Format: "{study_level}-{campus}-{faculty}-{career_index}"
            electives: If True, navigate to elective courses page instead of core curriculum.

        ## Returns
            Self for method chaining.

        ## Raises
            SiaSessionException.SessionNotSet: If session not initialized.
            SiaSessionException.TimeoutError: If SIA server doesn't respond.

        ## Note
            Updates internal career context: __career_code, __career_name, __course_list.
        """
        self.__sia_session.set_career(search_code, electives=electives)
        self.__career_code = self.__sia_session.career_code
        self.__course_list = self.__sia_session.course_list
        self.__career_name = self.__sia_session.career_name
        return self

    def get_course_info(self, course_index: int = 0, course_code: str = "") -> dict:
        """Retrieve complete course information including all groups and schedules.

        ## Args
            course_index: Zero-based index in current career's course list.
                Ignored if course_code is provided.
            course_code: Course code to search for (e.g., "2016489").
                If provided, overrides course_index.

        ## Returns
            Dictionary with structure:
                {
                    "courseName": str,            # Course name
                    "credits": int,                # Credit hours
                    "typology": str,              # Course typology
                    "availableSpots": int,         # Total available spots across all groups
                    "scrapeTimestamp": str,        # Scrape timestamp
                    "groups": [                   # List of course groups
                        {
                            "groupName": str,      # Group number/name
                            "teacher": str,       # Teacher name
                            "faculty": str,       # Faculty/school
                            "courseName": str,    # Course name
                            "schedules": [       # Schedule entries
                                {
                                    "day": str,      # Day of week (e.g., "LUNES")
                                    "startTime": str, # Start time "HH:MM"
                                    "endTime": str,   # End time "HH:MM"
                                    "classroom": str  # Classroom (may be empty)
                                }
                            ],
                            "duration": str,      # Duration (e.g., "16 SEMANAS")
                            "scheduleType": str,   # Schedule type (e.g., "DIURNA")
                            "spots": int|str,      # Available spots or "NaN"
                            "isFavorite": bool     # Legacy field
                        }
                    ]
                }

        ## Raises
            ValueError: If course name, credits, or tipology elements not found in XML.
            AssertionError: If session not on career/course page.
        """
        course_index = self.get_course_index(course_code) if course_code != "" else course_index
        xml = self.__sia_session.get_course_xml(course_index)
        return self.scrape_info(xml)

    def get_course_index(self, course_code: str) -> int:
        """Find the index of a course code in the current career's course list.

        ## Args
            course_code: Course code to search for (e.g., "2016489").

        ## Returns
            Zero-based index if found, -1 if not found.

        ## Raises
            AssertionError: If session not on career or course page.

        ## Note
            SIA's Oracle ADF table returns indices 0 and 1 in swapped order in its internal
            state (though the course list order is correct). This function applies the
            necessary correction when looking up indices.
        """
        assert self.__sia_session.STATUS in (
            SiaSessionStatus.ON_CAREER_PAGE,
            SiaSessionStatus.ON_COURSE_PAGE,
        ), "Session not on career page or course page, can't get course index"

        for i in range(len(self.__course_list)):
            if course_code in self.__course_list[i]:
                if i == 0 or i == 1:
                    return (i + 1) % 2  # Swap: 0→1, 1→0
                return i
        return -1

    def get_course_prereqs(self, course_index: int = 0, course_code: str = "") -> dict:
        """Retrieve course prerequisites and enrollment conditions.

        ## Args
            course_index: Zero-based index in current career's course list.
                Ignored if course_code is provided.
            course_code: Course code to search for (e.g., "2016489").
                If provided, overrides course_index.

        ## Returns
            Dictionary with structure (see scrape_prereqs() for details).

        ## Raises
            AssertionError: If session not on career/course page.
        """
        course_index = self.get_course_index(course_code) if course_code != "" else course_index
        xml = self.__sia_session.get_course_xml(course_index)
        return self.scrape_prereqs(xml)

    def scrape_courses(
        self, courses_indexs: list[int] | None = None, courses_codes: list[str] | None = None
    ) -> list[dict]:
        """Batch scrape multiple courses by index or code.

        ## Args
            courses_indexs: List of zero-based indices in course list.
                If empty, derives from courses_codes.
            courses_codes: List of course codes to scrape.
                Used to populate courses_indexs if that is empty.

        ## Returns
            List of course info dictionaries (see get_course_info() for structure).
            Each includes "code" field with the course code.

        ## Note
            Sorts indices before scraping for more efficient sequential access.
        """
        if courses_indexs is None:
            courses_indexs = []
        if courses_codes is None:
            courses_codes = []

        if courses_indexs == []:
            courses_indexs = [self.get_course_index(course_code) for course_code in courses_codes]

        courses_indexs.sort()
        courses = [self.get_course_info(course_index) for course_index in courses_indexs]

        for i in range(len(courses)):
            courses[i]["code"] = courses_codes[i]

        return courses

    ##################### STATIC METHODS #####################
    # These methods parse Oracle ADF XML/HTML using BeautifulSoup.
    # Oracle ADF generates specific CSS classes and DOM structures that we target.

    @staticmethod
    def get_plain_text(xml: str) -> str:
        """Extract human-readable plain text from Oracle ADF XML response.

        ## Args
            xml: Raw XML/HTML from SIA Oracle ADF response.

        ## Returns
            Plain text content before the first triple non-breaking space separator.

        ## Note
            Oracle ADF uses \xa0\xa0\xa0 as a visual separator in rendered text.
            This method extracts only the primary content before that separator.
        """
        soup = BeautifulSoup(xml, "lxml")
        return soup.get_text().split("\xa0\xa0\xa0")[0]

    @staticmethod
    def scrape_info(xml: str) -> dict:
        """Parse comprehensive course information from Oracle ADF course detail page.

        This method extracts course metadata and ALL group details (schedules, teachers,
        spots, etc.) from the XML/HTML response of a course detail page.

        ## Args
            xml: Raw XML/HTML from SIA course detail page response.

        ## Returns
            Dictionary with complete course data including all groups and schedules.
            See get_course_info() docstring for full structure.

        ## Oracle ADF XML Structure
            ```html
            <h2>                                    → Course name
            <span class="detass-creditos">          → Credits (nested span)
            <span class="detass-tipologia">         → Tipology (nested span)
            <div class="af_showDetailHeader_content0">  → Each group container
                <h2 class="af_showDetailHeader_title-text0">  → Group name
                <div class="af_panelGroupLayout">   → Group data container
                    [0] <span><span>                → Teacher name
                    [1] <span><span>                → Faculty
                    [2] <span><span>                → Schedules (lista-elemento)
                    [3] <span><span>                → Duration
                    [4] <span><span>                → Jornada (schedule type)
                    [5] <span><span>                → Spots (optional)
            ```

        ## Raises
            ValueError: If course name, credits, or tipology elements not found in XML.
        """
        course_obj = {}
        soup = BeautifulSoup(xml, "lxml")

        # Target: Oracle ADF → <h2> (first occurrence) → Course name
        course_name_elem = soup.find("h2")
        if course_name_elem is None:
            raise ValueError("Course name element not found in XML")
        course_name = course_name_elem.text

        # Target: Oracle ADF → <span class="detass-creditos"> → nested <span> → Credits
        credits_elem = soup.find("span", class_="detass-creditos")
        if credits_elem is None:
            raise ValueError("Credits element not found in XML")
        credits_span = credits_elem.find("span")
        if credits_span is None:
            raise ValueError("Credits span not found in XML")
        credits = int(credits_span.text.strip())

        # Target: Oracle ADF → <span class="detass-tipologia"> → nested <span> → Tipology
        tipology_elem = soup.find("span", class_="detass-tipologia")
        if tipology_elem is None:
            raise ValueError("Tipology element not found in XML")
        tipology_span = tipology_elem.find("span")
        if tipology_span is None:
            raise ValueError("Tipology span not found in XML")
        tipology = tipology_span.text.strip()

        group_list = []

        course_obj["courseName"] = course_name
        course_obj["availableSpots"] = 0  # Accumulated from all groups
        course_obj["scrapeTimestamp"] = DateFormatter(datetime.now()).format_date()
        course_obj["groups"] = group_list
        course_obj["credits"] = credits
        course_obj["typology"] = tipology

        # Target: Oracle ADF → All <div class="af_showDetailHeader_content0"> → Group containers
        # Each div represents one course group with all its details
        groups = soup.select(".af_showDetailHeader_content0")

        # ===== Process each course group =====
        for group in groups:
            group_obj = {}

            # Target: Oracle ADF → group.parent → <h2 class="af_showDetailHeader_title-text0"> → Group name/number
            group_obj["groupName"] = group.parent.find(
                "h2", class_="af_showDetailHeader_title-text0"
            ).text

            # Target: Oracle ADF → <div class="af_panelGroupLayout"> → children array
            # Oracle ADF renders group data as ordered child elements (not labeled):
            # TODO: These indices are fragile - Oracle ADF updates could break this
            group_data = list(group.find("div", class_="af_panelGroupLayout").children)
            # group_data structure:
            #   [0]: Teacher
            #   [1]: Faculty/school
            #   [2]: Schedules
            #   [3]: Duration (e.g., "16 SEMANAS")
            #   [4]: Schedule type (e.g., "DIURNA")
            #   [5]: Available spots - OPTIONAL, may not exist

            # All subsequent selectors use "span > span" to access nested span values
            # Oracle ADF wraps actual values in a nested <span> inside the label <span>

            # Target: group_data[0] → <span> → <span> → Teacher name
            teacher_name_span = group_data[0].select_one("span > span")
            if teacher_name_span:  # Teacher info may not be available for some groups
                group_obj["teacher"] = teacher_name_span.text.strip()
            else:
                group_obj["teacher"] = "Not reported"

            # Target: group_data[1] → <span> → <span> → Faculty name
            group_obj["faculty"] = group_data[1].select_one("span > span").text.strip()
            group_obj["courseName"] = course_name

            # ===== Parse schedule information =====
            # Logic: Each group can have multiple schedule entries (e.g., Mon 8-10, Wed 14-16)
            # Each entry includes day, time range, and optional classroom
            schedules = []
            schedule = {}

            # Target: group_data[2] → <span> → <span> → Schedule container
            schedule_section = group_data[2].select_one("span > span")

            if schedule_section:  # Schedule section may be empty for some groups
                # Target: schedule_section → All <span class="lista-elemento"> (non-recursive)
                # Note: recursive=False prevents selecting nested classroom spans which share the same class
                # Oracle ADF structure: schedule spans contain classroom spans, both use "lista-elemento"
                schedule_containers = schedule_section.find_all(
                    "span", class_="lista-elemento", recursive=False
                )

                for schedule_container in schedule_containers:
                    # Target: schedule_container → <span> → Schedule text
                    # Format: "LUNES de 08:00 a 10:00" (day name, "de" = from, "a" = to)
                    schedule_span = schedule_container.find("span")
                    if schedule_span is None:
                        continue
                    schedule_txt = schedule_span.text

                    # Logic: Parse schedule string using regex
                    # Captures: (day_name) de (HH:MM) a (HH:MM)
                    match = re.match(r"(\w+) de (\d{2}:\d{2}) a (\d{2}:\d{2})", schedule_txt)
                    if match is None:
                        continue
                    day, start_time, end_time = match.groups()
                    schedule["day"] = day
                    schedule["startTime"] = start_time
                    schedule["endTime"] = end_time

                    # Target: schedule_container → nested <span class="lista-elemento"> → Classroom
                    # Classroom info is nested inside schedule container (if available)
                    classroom_container = schedule_container.find("span", class_="lista-elemento")
                    schedule["classroom"] = classroom_container.text if classroom_container else ""

                    schedules.append(schedule)
                    schedule = {}

            group_obj["schedules"] = schedules

            # Target: group_data[3] → <span> → <span> → Duration
            group_obj["duration"] = group_data[3].select_one("span > span").text.strip()

            # Target: group_data[4] → <span> → <span> → Schedule type
            group_obj["scheduleType"] = group_data[4].select_one("span > span").text.strip()

            # ===== Parse available spots (optional field) =====
            # Logic: Spots info only exists if group_data has 6+ elements
            # TODO: Magic number 6 - depends on Oracle ADF template structure
            if len(group_data) < 6:
                # No spots information available for this group
                group_obj["spots"] = "NaN"
            else:
                # Target: group_data[5] → <span> → <span> → Spots count
                spots = int(group_data[5].select_one("span > span").text.strip())
                group_obj["spots"] = spots
                course_obj["availableSpots"] += spots  # Accumulate total spots

            # TODO: Remove this legacy field - not part of SIA data model
            group_obj["isFavorite"] = False

            # Add completed group to course object
            course_obj["groups"].append(group_obj)
            group_obj = {}

        return course_obj

    @staticmethod
    def scrape_prereqs(xml: str) -> dict:
        """Parse course prerequisites and enrollment conditions from Oracle ADF XML.

        Extracts prerequisite courses organized by condition types (e.g., "Must pass ALL",
        "Must pass 2 of the following"). Each condition has metadata and a list of
        prerequisite course codes.

        ## Args
            xml: Raw XML/HTML from SIA course detail page response.

        ## Returns
            Dictionary with structure:
                {
                    "courseName": str,  # Course name with code
                    "code": str,             # Course code extracted from name
                    "credits": int,           # Credit hours
                    "typology": str,          # Course typology
                    "conditions": [           # List of prerequisite conditions
                        {
                            "Condition": str,         # Condition type (from SIA)
                            "Type": str,              # Type (from SIA)
                            "AllRequired": str,       # "All required?" (from SIA)
                            "NumberOfCourses": str,  # Number of courses (from SIA)
                            "prerequisites": {        # Prerequisite courses
                                "COURSE_CODE": "Course Name",
                                ...
                            }
                        }
                    ]
                }

        ## Oracle ADF XML Structure
            ```html
            <h2>                                    → Course name (with code in parens)
            <span class="detass-creditos">          → Credits
            <span class="detass-tipologia">         → "Tipología: VALUE"
            <span class="borde salto af_panelGroupLayout">  → Condition containers
                <div class="margin-t af_panelGroupLayout">  → Each condition block
                    [0] <div> Condition metadata    → Headers + values as siblings
                    [1+] <div> Prerequisite courses → Code + name as siblings
            ```

        Warning:
            TODO: Keys use Spanish strings from SIA (not standardized).
            Future work should normalize to English keys for consistency.

        ## Raises
            ValueError: If course name or credits elements not found in XML.
        """
        course_obj = {}
        soup = BeautifulSoup(xml, "lxml")

        # Target: Oracle ADF → <h2> (first occurrence) → Course name with code
        h2_elements = soup.find_all("h2")
        if not h2_elements:
            raise ValueError("Course name element not found in prerequisites XML")
        course_name = h2_elements[0].text

        # Target: Oracle ADF → <span class="detass-creditos"> → nested <span> → Credits
        credits_elem = soup.find("span", class_="detass-creditos")
        if credits_elem is None:
            raise ValueError("Credits element not found in prerequisites XML")
        credits_span = credits_elem.find("span")
        if credits_span is None:
            raise ValueError("Credits span not found in prerequisites XML")
        credits = int(credits_span.text.strip())

        course_obj["courseName"] = course_name

        # Logic: Extract course code from name - format: "COURSE_NAME (CODE)"
        # TODO: Use regex for more robust parsing
        course_obj["code"] = course_name[course_name.index("(") + 1 : course_name.index(")")]
        course_obj["credits"] = credits

        # Target: Oracle ADF → <span class="detass-tipologia"> → text → "Tipología: VALUE"
        # Split on ": " to extract just the VALUE part
        # TODO: Magic index [1] after split - assumes format never changes
        course_obj["typology"] = soup.find_all("span", class_="detass-tipologia")[0].text.split(
            ": "
        )[1]

        course_obj["conditions"] = []

        # Target: Oracle ADF → CSS selector chain:
        #   <span class="borde salto af_panelGroupLayout">  → Container
        #       > <div class="margin-t af_panelGroupLayout"> → Each condition block
        conditions = soup.select(
            "span.borde.salto.af_panelGroupLayout > div.margin-t.af_panelGroupLayout"
        )

        # ===== Process each prerequisite condition =====
        for condition_div in conditions:
            condition_sub_divs = list(condition_div.children)

            # Logic: Each condition has at least 2 child divs:
            #   [0]: Condition metadata (headers and values)
            #   [1+]: Individual prerequisite courses
            # TODO: Magic number 2 - Oracle ADF structure dependency
            if len(condition_sub_divs) < 2:
                continue  # Skip malformed conditions

            # Target: First child div → Condition metadata container
            condition_info_div = condition_sub_divs[0]

            # Target: Oracle ADF → <span class="strong af_panelGroupLayout"> → <span class="margin-l">
            # These are the header labels (e.g., "Condición:", "Tipo:", "¿Todas?:", "Número asignaturas:")
            condition_headers_spans = condition_info_div.select(
                "span.strong.af_panelGroupLayout > span.margin-l"
            )

            # Target: Oracle ADF quirk - values are stored as nextSibling text nodes
            # Oracle ADF doesn't wrap values in elements, they're just text after the header span
            condition_values_spans = [header.nextSibling for header in condition_headers_spans]

            # Logic: Validate condition structure - must have exactly 4 header-value pairs
            # TODO: Magic number 4 - expected metadata fields from Oracle ADF
            if len(condition_headers_spans) != len(condition_values_spans):
                continue  # Mismatch between headers and values
            if len(condition_headers_spans) < 4:
                continue  # Missing expected metadata fields

            # ===== Extract condition metadata =====
            # WARNING: These keys are Spanish strings from SIA, not standardized constants
            # TODO: Standardize keys to English and normalize value formats
            #       Blocked by: requires DB migration, academic history parser updates,
            #       prerequisite graph algorithm changes
            prereq_info = {}

            # Target: condition_headers_spans[0] → "Condición:" → value → Condition type
            prereq_info[condition_headers_spans[0].text] = condition_values_spans[0].text

            # Target: condition_headers_spans[1] → "Tipo:" → value → Type
            prereq_info[condition_headers_spans[1].text] = condition_values_spans[1].text

            # Target: condition_headers_spans[2] → "¿Todas?:" → value → All required? (yes/no)
            prereq_info[condition_headers_spans[2].text] = condition_values_spans[2].text

            # Target: condition_headers_spans[3] → "Número asignaturas:" → value → Number of courses
            prereq_info[condition_headers_spans[3].text] = condition_values_spans[3].text

            prereq_info["prerequisites"] = {}

            # ===== Extract prerequisite course codes and names =====
            # Target: Remaining child divs (index 1+) → Each prerequisite course
            # TODO: Magic index [1:] - assumes first div is always metadata
            condition_prereqs_divs = condition_sub_divs[1:]

            for prereq_div in condition_prereqs_divs:
                # Target: prereq_div → <span class="af_panelGroupLayout"> → <span> → Course code
                prereq_code_span = prereq_div.select_one("span.af_panelGroupLayout > span")
                prereq_code = prereq_code_span.text

                # Target: Oracle ADF quirk - course name is nextSibling text node (not wrapped)
                # Why does Oracle ADF do this? Unclear, but consistent across all prereq entries
                prereq_name = prereq_code_span.nextSibling.text

                prereq_info["prerequisites"][prereq_code] = prereq_name

            course_obj["conditions"].append(prereq_info)

        return course_obj


##################### MODULE-LEVEL HELPER FUNCTIONS #####################
# These factory functions provide convenient session initialization patterns.


def init_sia_scraper(
    search_code: str,
    is_electives: bool,
    session_data: dict[str, Any] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> SiaScraper:
    """Initialize or restore a SiaScraper with intelligent session management.

    This factory function handles three scenarios:
    1. No session_data: Creates new session and navigates to career
    2. Valid session_data: Restores session and reuses it
    3. Invalid/expired session: Falls back to creating new session

    ## Args
        search_code: Career search code (e.g., "0-2-8-3").
        is_electives: Whether to navigate to electives page.
        session_data: Optional serialized session from get_session_data().
        timeout: HTTP request timeout in seconds.

    ## Returns
        SiaScraper instance ready for scraping the specified career.

    ## Note
        If the career in session_data differs from search_code, automatically
        navigates to the new career while preserving the session.

    Warning:
        Session validation may have false negatives.
        If session appears invalid, falls back to creating new session.
    """
    if session_data is None:
        session_data = {}

    if session_data == {}:
        return create_career_session(search_code, is_electives, timeout=timeout)

    sc = SiaScraper(timeout=timeout, session_data=session_data)

    if not sc.valid_session():
        return create_career_session(search_code, is_electives, timeout=timeout)

    if sc.career_code != search_code or sc.sia_session.is_electives != is_electives:
        sc.set_career(search_code, electives=is_electives)

    return sc


def create_career_session(
    search_code: str, is_electives: bool, timeout: int = DEFAULT_TIMEOUT
) -> SiaScraper:
    """Create a new SiaScraper with a fresh session and navigate to career.

    ## Args
        search_code: Career search code (e.g., "0-2-8-3").
        is_electives: Whether to navigate to electives page.
        timeout: HTTP request timeout in seconds.

    ## Returns
        SiaScraper instance with new session, positioned at career page.
    """
    sc = SiaScraper(timeout=timeout)
    sc.set_career(search_code, electives=is_electives)
    return sc


##################### MODULE TESTING #####################
# Run this module directly for basic functionality testing

if __name__ == "__main__":
    # Example: Create scraper and navigate to a career
    sc = SiaScraper()
    print(f"Initial status: {sc.sia_session.STATUS}")

    # Set career to Computer Science (example code: "0-2-8-3")
    sc.set_career("0-2-8-3", electives=False)
    print(f"Loaded career: {sc.career_name}")
    print(f"Available courses: {len(sc.course_list)}")

    # Switch to different career (example: "0-2-8-1")
    sc.set_career("0-2-8-1", electives=False)
    print(f"Switched to career: {sc.career_name}")

    # Commented out debugging code:
    # print(sc.get_plain_text(sc.__sia_session.get_request(sc.__sia_session.url).text))
    # print(sc.__sia_session.STATUS)
    # print("-------------------")
    # sc.__sia_session.get_course_xml(0)
    # print(sc.get_plain_text(sc.__sia_session.get_request(sc.__sia_session.url).text))
    # print(sc.__sia_session.STATUS)
