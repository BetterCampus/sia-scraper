"""Navigation Controller Module.

This module provides workflow navigation for SIA sessions, managing transitions
between different pages in the Oracle ADF-based SIA system.

The NavigationController class owns workflow state and navigation logic:
- Career selection workflow (dropdown sequence)
- Course list navigation
- Course detail page transitions

This component was extracted from SiaSession as part of the CQ-H1 refactoring
to improve separation of concerns and testability.
"""

from typing import Any

from requests import Response

from ..constants import actions, adf_events, adf_ids, business, data_map
from ..parsers.html_parser import HtmlParser
from ..utils.debug import debug_log
from .exceptions import SiaSessionException


class NavigationController:
    """Controls navigation workflow through SIA's Oracle ADF interface.

    This class manages the sequential workflow required by Oracle ADF:
    - Career selection: Dropdown sequence (level → campus → faculty → career)
    - Course navigation: Row selection → detail page entry
    - Page transitions: Career page ↔ Course detail page

    ## Attributes
        career_code: Current career search code (format: level-campus-faculty-career)
        career_name: Human-readable career name from SIA
        is_electives: Whether viewing elective courses
        course_list: List of {course_code: course_name} dicts
    """

    def __init__(self) -> None:
        """Initialize NavigationController with default state."""
        self._career_code: str = ""
        self._career_name: str = "N/A"
        self._is_electives: bool = False
        self._tipology_index: str = ""
        self._course_list: list[dict[str, str]] = []

    @property
    def career_code(self) -> str:
        """Current career search code."""
        return self._career_code

    @property
    def career_name(self) -> str:
        """Current career display name."""
        return self._career_name

    @property
    def is_electives(self) -> bool:
        """Whether viewing elective courses."""
        return self._is_electives

    @property
    def course_list(self) -> list[dict[str, str]]:
        """Current course list from career page."""
        return self._course_list

    def set_career(
        self,
        search_code: str,
        electives: bool,
        session: Any,
    ) -> None:
        """Execute career selection workflow.

        ## Args
            search_code: Hyphen-delimited code (e.g., "1-3-5-2345")
            electives: Whether to load elective courses
            session: SiaSession instance for making requests

        ## Raises
            SiaSessionException.CareerNotSet: If career dropdown not found
            SiaSessionException.TimeoutError: If request times out
        """
        if electives:
            self._tipology_index = business.ELECTIVES_TYPOLOGY_INDEX
        else:
            self._tipology_index = ""

        self._career_code = search_code
        career_indices = search_code.split("-")

        action_sequence = [
            actions.STUDY_LEVEL_DD,
            actions.CAMPUS_DD,
            actions.FACULTY_DD,
            actions.CAREER_DD,
            actions.TIPOLOGY_DD,
        ]

        if not electives:
            action_sequence.append(actions.SHOW_COURSES_BTTN)
        else:
            action_sequence.extend(
                [
                    actions.FACULTY_CAREER_DD,
                    actions.CAMPUS_ELECTIVES_DD,
                    actions.SHOW_COURSES_BTTN,
                ]
            )

        response = None
        for action in action_sequence:
            session._init_request_dict()

            session.request_dict[adf_ids.STUDY_LEVEL_DD_ID] = career_indices[0]
            session.request_dict[adf_ids.CAMPUS_DD_ID] = career_indices[1]
            session.request_dict[adf_ids.FACULTY_DD_ID] = career_indices[2]
            session.request_dict[adf_ids.CAREER_DD_ID] = career_indices[3]

            data = session._generate_request_body(action)
            response = session.post_request(data=data)

            if action == actions.FACULTY_DD:
                xml = response.text
                parser = HtmlParser(xml)
                dropdown_elements = parser.findall(f'//*[@id="{data_map.DROPDOWNS[3]}"]/option')
                if not dropdown_elements:
                    raise SiaSessionException.CareerNotSet from ValueError(
                        "Career dropdown not found"
                    )
                option_index = int(career_indices[3]) + business.DROPDOWN_FIRST_OPTION_OFFSET
                self._career_name = dropdown_elements[option_index].text

        if response is None:
            raise SiaSessionException.CareerNotSet from ValueError(
                "No response while setting career"
            )

        from ..parsers.html_parser import get_course_list

        xml = response.text
        self._course_list = get_course_list(xml)
        self._is_electives = electives

        debug_log(f"SET_CAREER: Course list loaded, {len(self._course_list)} courses")

    def select_course_row(self, course_index: int, session: Any) -> None:
        """Select (highlight) a course row in the Oracle ADF table.

        ## Args
            course_index: Index of course in course_list (0-based)
            session: SiaSession instance for making requests

        ## Raises
            SiaSessionException.TimeoutError: If request times out
        """
        debug_log(f"SELECT_ROW: Index={course_index}")

        session._init_request_dict()
        request_body = session._generate_request_body(actions.SELECT_ROW, course_index)

        debug_log(f"SELECT_ROW: Sending request for index {course_index}")
        session.post_request(request_body)

    def enter_course_page(self, course_index: int, session: Any) -> Response:
        """Navigate to course detail page.

        ## Args
            course_index: Index of course in course_list (0-based)
            session: SiaSession instance for making requests

        ## Returns
            Response object containing course detail XML.

        ## Raises
            SiaSessionException.TimeoutError: If request times out
        """
        debug_log(f"ENTER_COURSE_PAGE: Index={course_index}, Status={session.STATUS.value}")

        if course_index < len(self._course_list):
            course_at_idx = self._course_list[course_index]
            debug_log(f"Index {course_index} target", {"course": str(course_at_idx)})

        self.select_course_row(course_index, session)
        session._init_request_dict()

        request_body = session._generate_request_body(actions.COURSE_PAGE_LINK, course_index)
        debug_log(
            f"COURSE_PAGE_LINK request for index {course_index}",
            {"PROCESS": request_body.get("oracle.adf.view.rich.PROCESS", "N/A")},
        )

        response = session.post_request(request_body)

        debug_log(f"ENTER_COURSE_PAGE: Success, Status={session.STATUS.value}")
        return response

    def exit_course_page(self, session: Any) -> None:
        """Return to course list from course detail page.

        Clicks the "Volver" (Back) button.

        ## Args
            session: SiaSession instance for making requests

        ## Raises
            SiaSessionException.TimeoutError: If request times out
        """
        debug_log(f"EXIT_COURSE_PAGE: Current Status={session.STATUS.value}")

        data = {
            "org.apache.myfaces.trinidad.faces.FORM": "f1",
            "Adf-Window-Id": session._window_id,
            "Adf-Page-Id": session._page_id,
            "javax.faces.ViewState": session._view_state,
            "event": adf_ids.BACK_BTTN_ID,
            f"event.{adf_ids.BACK_BTTN_ID}": adf_events.BTTN_EVENT_VALUE,
            "oracle.adf.view.rich.PROCESS": f"{adf_ids.ORACLE_ADF_REGION_ID},{adf_ids.BACK_BTTN_ID}4",
        }
        session.post_request(data)

        debug_log(f"EXIT_COURSE_PAGE: Complete, Status={session.STATUS.value}")

    def get_course_xml(self, course_index: int, session: Any) -> str:
        """Retrieve course detail XML (enter → capture → exit).

        ## Args
            course_index: Index of course in course_list (0-based)
            session: SiaSession instance for making requests

        ## Returns
            Oracle ADF XML containing course details.
        """
        debug_log(f"=== GET_COURSE_XML START: Index={course_index} ===")
        debug_log(f"Current course list size: {len(self._course_list)}")

        if course_index < len(self._course_list):
            course_info = self._course_list[course_index]
            debug_log(f"Course at index {course_index}", {"course": str(course_info)})
        else:
            debug_log(f"WARNING: Index {course_index} out of bounds!")

        xml = self.enter_course_page(course_index, session).text
        debug_log(f"ENTER_COURSE_PAGE returned, XML length: {len(xml)}")

        self.exit_course_page(session)
        debug_log(f"=== GET_COURSE_XML END: Index={course_index} ===")

        return xml

    def update_course_list_from_xml(self, xml: str) -> None:
        """Update course list from XML response.

        ## Args
            xml: Raw XML response from SIA
        """
        from ..parsers.html_parser import get_course_list

        self._course_list = get_course_list(xml)

    def restore_from_session_data(self, session_data: dict[str, Any]) -> None:
        """Restore navigation state from serialized session.

        ## Args
            session_data: Dict with career_code, career_name, is_electives
        """
        self._career_code = session_data.get("career_code", "")
        self._career_name = session_data.get("career_name", "N/A")
        self._is_electives = session_data.get("is_electives", False)
