"""Oracle ADF request body builder.

This module provides a dataclass for generating Oracle ADF request bodies
with proper event formatting and state management.
"""

from dataclasses import dataclass, field
from typing import Protocol

from sia_scraper.constants import (
    CAMPUS_ELECTIVES_DD,
    CAMPUS_ELECTIVES_DD_ID,
    DATA_MAP,
    ELECTIVES_CAMPUS_INCREMENT,
    FACULTY_CAREER_DD,
    FACULTY_CAREER_DD_ID,
)


class OracleAdfSession(Protocol):
    """Structural contract for session attributes used by request builder."""

    @property
    def _tipology_index(self) -> str: ...

    @property
    def _window_id(self) -> str | None: ...

    @property
    def _page_id(self) -> str | None: ...

    @property
    def _view_state(self) -> str | None: ...

    @property
    def course_list(self) -> list[dict[str, str]]: ...

    career_indices: list[str]


@dataclass
class OracleAdfRequestBuilder:
    """Builds Oracle ADF request bodies for SIA interactions.

    This dataclass encapsulates the logic for generating request bodies
    that Oracle ADF expects, including ViewState tokens, event payloads,
    and component-specific metadata.

    ## Attributes
        session: Reference to a session-like object with ADF state attributes.
        request_dict: Current request dictionary template.
    """

    session: OracleAdfSession
    request_dict: dict[str, str] = field(default_factory=dict)

    def init_request_dict(self) -> dict[str, str]:
        """Initialize the request body boilerplate dictionary.

        Returns
            Complete request dictionary with Oracle ADF form fields and state tokens.
        """
        from sia_scraper_rust import init_oracle_adf_request_dict  # type: ignore[attr-defined]

        request_dict = init_oracle_adf_request_dict(
            self.session._tipology_index,
            self.session._window_id,
            self.session._page_id,
            self.session._view_state,
        )
        self.request_dict = dict(request_dict)
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
        from sia_scraper_rust import build_oracle_adf_request_body  # type: ignore[attr-defined]

        if data_name not in DATA_MAP:
            raise KeyError(f"Unknown data_name in DATA_MAP: {data_name}")

        if data_name == FACULTY_CAREER_DD:
            self.request_dict[FACULTY_CAREER_DD_ID] = "0"
        elif data_name == CAMPUS_ELECTIVES_DD:
            self.request_dict[CAMPUS_ELECTIVES_DD_ID] = str(
                int(self.session.career_indices[1]) + ELECTIVES_CAMPUS_INCREMENT
            )

        specific_request_dict = build_oracle_adf_request_body(
            self.request_dict,
            data_name,
            idx,
            self.session.career_indices,
            len(self.session.course_list),
        )

        return dict(specific_request_dict)

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
        from sia_scraper_rust import get_oracle_adf_event_dict  # type: ignore[attr-defined]

        event_dict = get_oracle_adf_event_dict(id, event_type, idx)
        return dict(event_dict)
