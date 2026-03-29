"""Oracle ADF request body builder.

This module provides a dataclass for generating Oracle ADF request bodies
with proper event formatting and state management.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sia_scraper.constants import (
    BTTN_EVENT_VALUE,
    CAMPUS_DD_ID,
    CAMPUS_ELECTIVES_DD_ID,
    CAREER_DD_ID,
    COURSE_PAGE_LINK,
    DATA_MAP,
    DROPDOWN_EVENT_VALUE,
    ELECTIVES_CAMPUS_INCREMENT,
    FACULTY_CAREER_DD,
    FACULTY_CAREER_DD_ID,
    FACULTY_CAREER_DEFAULT_INDEX,
    FACULTY_DD_ID,
    ORACLE_ADF_REGION_ID,
    ORACLE_ADF_RENDER_TARGET,
    ORACLE_ADF_UNKNOWN_COMPONENT_1,
    ORACLE_ADF_UNKNOWN_COMPONENT_2,
    ORACLE_ADF_UNKNOWN_COMPONENT_3,
    ORACLE_ADF_UNKNOWN_COMPONENT_4,
    SELECT_ROW,
    SELECT_ROW_EVENT_VALUE,
    SHOW_COURSES_BTTN_ID,
    STUDY_LEVEL_DD_ID,
    TIPOLOGY_DD_ID,
)

if TYPE_CHECKING:
    from sia_scraper.session import SiaSession


@dataclass
class OracleAdfRequestBuilder:
    """Builds Oracle ADF request bodies for SIA interactions.

    This dataclass encapsulates the logic for generating request bodies
    that Oracle ADF expects, including ViewState tokens, event payloads,
    and component-specific metadata.

    ## Attributes
        session: Reference to the parent SiaSession instance.
        request_dict: Current request dictionary template.
    """

    session: "SiaSession"
    request_dict: dict[str, str] = field(default_factory=dict)

    def init_request_dict(self) -> dict[str, str]:
        """Initialize the request body boilerplate dictionary.

        Returns
            Complete request dictionary with Oracle ADF form fields and state tokens.
        """
        tipology_index = self.session._tipology_index  # type: ignore[attr-defined]
        self.request_dict = {
            STUDY_LEVEL_DD_ID: "",
            CAMPUS_DD_ID: "",
            FACULTY_DD_ID: "",
            CAREER_DD_ID: "",
            TIPOLOGY_DD_ID: tipology_index,
            SHOW_COURSES_BTTN_ID: "",
            ORACLE_ADF_UNKNOWN_COMPONENT_1: "",
            ORACLE_ADF_UNKNOWN_COMPONENT_2: "",
            ORACLE_ADF_UNKNOWN_COMPONENT_3: "",
            ORACLE_ADF_UNKNOWN_COMPONENT_4: "",
            "org.apache.myfaces.trinidad.faces.FORM": "f1",
            "Adf-Window-Id": self.session._window_id or "",  # type: ignore[attr-defined]
            "Adf-Page-Id": self.session._page_id or "",  # type: ignore[attr-defined]
            "javax.faces.ViewState": self.session._view_state or "",  # type: ignore[attr-defined]
        }
        return self.request_dict

    def build_request_body(self, data_name: str, idx: int = -1) -> dict[str, str]:
        """Generate complete Oracle ADF request body for a named action.

        Args:
            data_name: Logical action name from DATA_MAP (e.g., STUDY_LEVEL_DD).
            idx: Optional table row index for row-based actions (default: -1).

        Returns:
            Complete request body dictionary ready for POST to SIA.

        Raises:
            KeyError: If data_name not found in DATA_MAP.
        """
        if data_name not in DATA_MAP:
            raise KeyError(f"Unknown data_name in DATA_MAP: {data_name}")

        id, event_value = DATA_MAP[data_name]

        if data_name == FACULTY_CAREER_DD:
            self.request_dict[FACULTY_CAREER_DD_ID] = FACULTY_CAREER_DEFAULT_INDEX
        elif data_name == "CAMPUS_ELECTIVES_DD":
            career_indices = self.session.career_indices  # type: ignore[attr-defined]
            self.request_dict[CAMPUS_ELECTIVES_DD_ID] = str(
                int(career_indices[1]) + ELECTIVES_CAMPUS_INCREMENT
            )

        specific_request_dict = self._generate_specific_request_dict(id, event_value, idx)

        if data_name == SELECT_ROW:
            course_list = self.session.course_list
            specific_request_dict["oracle.adf.view.rich.DELTAS"] = (
                f"{{pt1:r1:0:t4={{viewportSize={len(course_list) + 1},rows={len(course_list)},selectedRowKeys={idx}}}}}"
            )
        elif data_name == COURSE_PAGE_LINK:
            specific_request_dict["oracle.adf.view.rich.RENDER"] = ORACLE_ADF_RENDER_TARGET

        return specific_request_dict

    def _generate_specific_request_dict(
        self, id: str, event_type: str, idx: int = -1
    ) -> dict[str, str]:
        """Generate a request dictionary for a specific Oracle ADF interaction.

        Args:
            id: Oracle ADF component ID (e.g., STUDY_LEVEL_DD_ID).
            event_type: Oracle RichClient XML event payload.
            idx: Optional table row index for row-based events.

        Returns:
            Complete request dictionary (request_dict + event_dict).
        """
        event_dict = self._get_event_dict(id, event_type, idx)
        request_dict_copy = self.request_dict.copy()

        for key, value in event_dict.items():
            request_dict_copy[key] = value

        return request_dict_copy

    def _get_event_dict(self, id: str, event_type: str, idx: int = -1) -> dict[str, str]:
        """Generate Oracle ADF event fields for a specific component interaction.

        Args:
            id: Oracle ADF component ID.
            event_type: Oracle RichClient XML event payload.
            idx: Optional table row index.

        Returns:
            Dictionary with Oracle ADF event fields.
        """
        if idx >= 0:
            id = f"{id}:{idx}:cl2"

        process_value = id
        if event_type == DROPDOWN_EVENT_VALUE or event_type == SELECT_ROW_EVENT_VALUE:
            process_value = id
        elif event_type == BTTN_EVENT_VALUE:
            process_value = f"{ORACLE_ADF_REGION_ID},{id}"

        return {
            "event": id,
            f"event.{id}": event_type,
            "oracle.adf.view.rich.PROCESS": process_value,
        }
