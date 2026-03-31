"""Oracle ADF State Manager Module.

This module provides focused state management for Oracle ADF tokens (ViewState,
Window-Id, Page-Id) required by the SIA system's component-based UI framework.

The AdfStateManager class owns all ADF state token lifecycle:
- Extraction from HTML responses
- Validation and synchronization
- Request dict integration

This component was extracted from SiaSession as part of the CQ-H1 refactoring
to improve separation of concerns and testability.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from loguru import logger

from .adf_state import extract_view_state, extract_view_state_from_response
from .exceptions import SiaSessionException

if TYPE_CHECKING:
    from requests import Response  # noqa: F401


@dataclass(frozen=True)
class AdfState:
    """Immutable snapshot of Oracle ADF state tokens."""

    view_state: str | None
    window_id: str | None
    page_id: str | None


class AdfStateManager:
    """Manages Oracle ADF state tokens for SIA session.

    This class handles the lifecycle of Oracle ADF state tokens:
    - ViewState (javax.faces.ViewState) - JSF component state token
    - Window-Id (Adf-Window-Id) - Browser window/tab identifier
    - Page-Id (Adf-Page-Id) - Oracle ADF page identifier

    Oracle ADF requires these tokens to be present in every POST request
    to maintain server-side state consistency.

    ## Attributes
        view_state: Current JSF ViewState token
        window_id: Current Oracle ADF Window-Id
        page_id: Current Oracle ADF Page-Id (typically "0")
    """

    def __init__(self) -> None:
        """Initialize AdfStateManager with empty state."""
        self._view_state: str | None = None
        self._window_id: str | None = None
        self._page_id: str | None = None

    @property
    def view_state(self) -> str | None:
        """Current JSF ViewState token."""
        return self._view_state

    @property
    def window_id(self) -> str | None:
        """Current Oracle ADF Window-Id."""
        return self._window_id

    @property
    def page_id(self) -> str | None:
        """Current Oracle ADF Page-Id."""
        return self._page_id

    @property
    def params(self) -> dict[str, str]:
        """URL parameters dict for Oracle ADF requests."""
        if self._window_id is None or self._page_id is None:
            return {}
        return {"Adf-Window-Id": self._window_id, "Adf-Page-Id": self._page_id}

    @property
    def has_state(self) -> bool:
        """Whether all required ADF state tokens are present."""
        return (
            self._view_state is not None
            and self._window_id is not None
            and self._page_id is not None
        )

    def initialize_from_html(self, html_content: bytes) -> None:
        """Extract and store ADF state tokens from initial page HTML.

        ## Args
            html_content: Raw HTML bytes from initial SIA GET request

        ## Raises
            SiaSessionException.SessionNotSet: If ViewState or Window-Id not found
        """
        html_str = html_content.decode("utf-8", errors="ignore")

        from ..parsers.html_parser import HtmlParser

        parser = HtmlParser(html_str)

        view_state_input = parser.find("input", type="hidden", name="javax.faces.ViewState")
        if view_state_input is None:
            raise SiaSessionException.SessionNotSet from ValueError(
                "ViewState not found in initial page"
            )
        self._view_state = str(view_state_input.get("value"))

        window_id_input = parser.find("input", type="hidden", name="Adf-Window-Id")
        if window_id_input is None:
            raise SiaSessionException.SessionNotSet from ValueError(
                "Adf-Window-Id not found in initial page"
            )
        self._window_id = str(window_id_input.get("value"))

        self._page_id = "0"

    def sync_from_response(self, response: Any) -> None:
        """Sync ViewState from a partial POST response.

        Extracts ViewState from the response and updates internal state.
        If ViewState is not found, preserves current state.

        ## Args
            response: Response object from a POST request.
        """
        old_view_state = self._view_state
        try:
            self._view_state = extract_view_state_from_response(response)
            if old_view_state != self._view_state:
                logger.debug("ViewState updated from POST response")
            else:
                logger.debug("ViewState unchanged after POST response")
        except SiaSessionException.SessionNotSet:
            logger.debug("ViewState extraction failed, preserving current state")

    def sync_from_html(self, html_content: bytes) -> None:
        """Sync ViewState from HTML content (typically from GET requests).

        ## Args
            html_content: Raw HTML bytes from GET request.

        ## Raises
            SiaSessionException.SessionNotSet: If ViewState not found in HTML.
        """
        old_view_state = self._view_state
        html_str = html_content.decode("utf-8", errors="ignore")
        self._view_state = extract_view_state(html_str)
        if old_view_state != self._view_state:
            logger.debug("ViewState updated from GET response")
        else:
            logger.debug("ViewState unchanged after GET response")

    def get_state_snapshot(self) -> AdfState:
        """Get immutable snapshot of current ADF state.

        ## Returns
            AdfState containing current tokens

        ## Raises
            SiaSessionException.SessionNotSet: If state not initialized
        """
        if not self.has_state:
            raise SiaSessionException.SessionNotSet from ValueError("ADF state not initialized")
        return AdfState(
            view_state=self._view_state,
            window_id=self._window_id,
            page_id=self._page_id,
        )

    def restore_from_session_data(self, session_data: dict[str, Any]) -> None:
        """Restore ADF state from serialized session data.

        ## Args
            session_data: Dict with keys: javax_faces_ViewState, params
        """
        self._view_state = session_data.get("javax_faces_ViewState")
        params = session_data.get("params", {})
        self._window_id = params.get("Adf-Window-Id")
        self._page_id = params.get("Adf-Page-Id")

    def build_request_dict(self) -> dict[str, str]:
        """Build base request dict with current ADF state.

        ## Returns
            Dictionary with ViewState and form fields for Oracle ADF POST

        ## Raises
            SiaSessionException.SessionNotSet: If state not initialized
        """
        if not self.has_state:
            raise SiaSessionException.SessionNotSet from ValueError("ADF state not initialized")
        return {
            "org.apache.myfaces.trinidad.faces.FORM": "f1",
            "Adf-Window-Id": self._window_id,
            "Adf-Page-Id": self._page_id,
            "javax.faces.ViewState": self._view_state,
        }  # type: ignore[return-value]
