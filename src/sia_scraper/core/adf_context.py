"""Oracle ADF Context Value Object Module.

This module provides an immutable value object representing the Oracle ADF
request context needed for building request bodies and handling navigation.

The AdfContext encapsulates:
- Oracle ADF component IDs (form, window, page)
- ViewState token
- Career indices (level, campus, faculty, career)

This reduces coupling between OracleAdfRequestBuilder and session internals.
"""

from dataclasses import dataclass

from .exceptions import SiaSessionException


@dataclass(frozen=True)
class AdfContext:
    """Immutable Oracle ADF request context.

    This value object encapsulates all state needed to build Oracle ADF
    request bodies, reducing direct coupling with SiaSession internals.

    Attributes:
        form_id: Oracle ADF form identifier (default: "f1")
        window_id: Oracle ADF Window-Id token
        page_id: Oracle ADF Page-Id token
        view_state: JSF ViewState token
        career_indices: List of [level, campus, faculty, career] indices
        tipology_index: Current tipology selection index ("" or "7" for electives)
    """

    form_id: str = "f1"
    window_id: str | None = None
    page_id: str | None = None
    view_state: str | None = None
    career_indices: list[str] | None = None
    tipology_index: str = ""

    @classmethod
    def from_session(
        cls,
        window_id: str | None,
        page_id: str | None,
        view_state: str | None,
        career_code: str,
        tipology_index: str = "",
    ) -> "AdfContext":
        """Create AdfContext from session attributes.

        ## Args
            window_id: Oracle ADF Window-Id from session
            page_id: Oracle ADF Page-Id from session
            view_state: JSF ViewState from session
            career_code: Hyphen-delimited career code (e.g., "1-2-3-4")
            tipology_index: Current tipology index ("" or "7" for electives)

        ## Returns
            AdfContext instance
        """
        return cls(
            window_id=window_id,
            page_id=page_id,
            view_state=view_state,
            career_indices=career_code.split("-") if career_code else [],
            tipology_index=tipology_index,
        )

    def with_updated_view_state(self, new_view_state: str) -> "AdfContext":
        """Create new context with updated ViewState.

        ## Args
            new_view_state: New JSF ViewState token

        ## Returns
            New AdfContext with updated ViewState
        """
        return AdfContext(
            form_id=self.form_id,
            window_id=self.window_id,
            page_id=self.page_id,
            view_state=new_view_state,
            career_indices=self.career_indices,
            tipology_index=self.tipology_index,
        )

    def validate(self) -> None:
        """Validate that all required ADF state is present.

        ## Raises
            SiaSessionException.SessionNotSet: If required state missing
        """
        if self.window_id is None:
            raise SiaSessionException.SessionNotSet from ValueError("window_id not set")
        if self.page_id is None:
            raise SiaSessionException.SessionNotSet from ValueError("page_id not set")
        if self.view_state is None:
            raise SiaSessionException.SessionNotSet from ValueError("view_state not set")

    def get_window_id(self) -> str:
        """Get window_id with validation.

        ## Returns
            Window ID string
        ## Raises
            SiaSessionException.SessionNotSet: If not set
        """
        if self.window_id is None:
            raise SiaSessionException.SessionNotSet from ValueError("window_id not set")
        return self.window_id

    def get_page_id(self) -> str:
        """Get page_id with validation.

        ## Returns
            Page ID string
        ## Raises
            SiaSessionException.SessionNotSet: If not set
        """
        if self.page_id is None:
            raise SiaSessionException.SessionNotSet from ValueError("page_id not set")
        return self.page_id

    def get_view_state(self) -> str:
        """Get view_state with validation.

        ## Returns
            ViewState string
        ## Raises
            SiaSessionException.SessionNotSet: If not set
        """
        if self.view_state is None:
            raise SiaSessionException.SessionNotSet from ValueError("view_state not set")
        return self.view_state

    def get_career_indices(self) -> list[str]:
        """Get career_indices with validation.

        ## Returns
            List of [level, campus, faculty, career] strings
        ## Raises
            SiaSessionException.SessionNotSet: If not set
        """
        if self.career_indices is None or len(self.career_indices) < 4:
            raise SiaSessionException.SessionNotSet from ValueError(
                "career_indices not properly set"
            )
        return self.career_indices
