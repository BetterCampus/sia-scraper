"""Async SIA Session Management Module.

This module provides async session management backed by Rust's reqwest/tokio HTTP client.
This is the v2.0 async migration replacing Python requests + tenacity.

## Migration from sync API (v1.x -> v2.0)

Before (v1.x):
    session = SiaSession(init_session=True)
    session.set_career("0-2-8-3")
    course_xml = session.get_course_xml(0)

After (v2.0):
    session = await SiaSessionAsync.create()
    await session.set_career("0-2-8-3")
    course_xml = await session.get_course_xml(0)
"""

from typing import Any

import sia_scraper_rust

from .constants import status
from .parsers.models import SessionState


class SiaSessionAsync:
    """Async SIA session backed by Rust reqwest/tokio HTTP client.

    This class provides async versions of SiaSession methods using the Rust
    async HTTP client for better performance and connection pooling.

    ## Usage
        >>> session = await SiaSessionAsync.create()
        >>> await session.set_career("0-2-8-3")
        >>> xml = await session.get_course_xml(0)
    """

    def __init__(self, timeout: int = 15) -> None:
        self._timeout = timeout
        self._career_name = "N/A"
        self._career_code = ""
        self._is_electives = False
        self._career_indices: list[str] = []
        self._STATUS = status.SiaSessionStatus.NO_SESSION
        self._session_state: dict[str, Any] = {}

    @classmethod
    async def create(cls, timeout: int = 15) -> "SiaSessionAsync":
        """Create and initialize a new async session.

        Args:
            timeout: Request timeout in seconds (default: 15)

        Returns:
            Initialized SiaSessionAsync instance
        """
        session = cls(timeout)
        await session.init_session()
        return session

    @property
    def career_name(self) -> str:
        return self._career_name

    @property
    def career_code(self) -> str:
        return self._career_code

    @property
    def is_electives(self) -> bool:
        return self._is_electives

    @property
    def STATUS(self) -> status.SiaSessionStatus:
        return self._STATUS

    @property
    def course_list(self) -> list[dict[str, str]]:
        return self._session_state.get("course_list", [])

    @property
    def career_indices(self) -> list[str]:
        return self._career_indices

    async def init_session(self) -> None:
        """Initialize HTTP session with SIA and fetch initial ViewState."""
        result = await sia_scraper_rust.init_sia_session(self._timeout)  # type: ignore[attr-defined]
        self._STATUS = status.SiaSessionStatus.CAREER_NOT_SET
        self._session_state = dict(result)

    async def set_career(self, search_code: str, electives: bool = False) -> None:
        """Navigate to career and load course list.

        Args:
            search_code: Career search code (e.g., "0-2-8-3")
            electives: Whether to load elective courses
        """
        await sia_scraper_rust.set_career(self._timeout, search_code, electives)  # type: ignore[attr-defined]
        self._career_code = search_code
        self._career_indices = search_code.split("-")
        self._is_electives = electives
        self._STATUS = status.SiaSessionStatus.ON_CAREER_PAGE

    async def get_course_xml(self, course_index: int) -> str:
        """Get course detail XML for given index.

        Args:
            course_index: Index of course in course_list

        Returns:
            Raw XML string from SIA course detail page
        """
        result = await sia_scraper_rust.get_course_xml(  # type: ignore[attr-defined]
            self._timeout,
            course_index,
            self._career_indices,
        )
        return str(result)

    async def close(self) -> None:
        """Close the session and cleanup resources."""
        self._STATUS = status.SiaSessionStatus.NO_SESSION
        self._session_state = {}

    def get_session_data(self) -> SessionState:
        """Serialize session state for persistence.

        Returns:
            SessionState with all data needed to restore session
        """
        return SessionState(
            session_headers={},
            session_cookies={},
            params={"Adf-Page-Id": "1", "Adf-Window-Id": ""},
            javax_faces_ViewState=self._session_state.get("javax_faces_ViewState"),
            career_code=self._career_code,
            career_name=self._career_name,
            is_electives=self._is_electives,
            STATUS=self._STATUS.value,
        )

    async def __aenter__(self) -> "SiaSessionAsync":
        return self

    async def __aexit__(self, exc_type: type, exc_val: Exception, exc_tb: object) -> None:
        await self.close()
