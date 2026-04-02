"""Thin Python wrapper around Rust PySiaSession."""

from contextlib import asynccontextmanager

import sia_scraper_rust

from .constants import status
from .constants.defaults import DEFAULT_CAREER_NAME
from .core.exceptions import ConcurrentAccessError


class SiaSession:
    """Thin Python wrapper around Rust PySiaSession.

    All HTTP operations and state management are delegated to Rust.
    This class provides:
    - Python-friendly async interface
    - Cached property access (no await needed)
    - Concurrent access protection

    **IMPORTANT: This class does NOT support concurrent operations.**
    Methods must be called sequentially. Use multiple SiaSession instances
    for parallel scraping.

    Example:
        >>> session = await SiaSession.create()
        >>> await session.set_career("0-2-8-3")
        >>> course = await session.scrape_course_info(0)
        >>> print(course.course_name)
    """

    def __init__(self, timeout: int = 15) -> None:
        self._timeout = timeout
        self._rust_session = sia_scraper_rust.PySiaSession(timeout=timeout)

        self._career_name = DEFAULT_CAREER_NAME
        self._career_code = ""
        self._is_electives = False
        self._career_indices: list[str] = []
        self._status: status.SiaSessionStatus = status.SiaSessionStatus.NO_SESSION
        self._course_list: list[dict[str, str]] = []

        self._active_operation: str | None = None

    @classmethod
    async def create(cls, timeout: int = 15) -> "SiaSession":
        """Create and initialize a new async session."""
        session = cls(timeout)
        await session.init_session()
        return session

    @asynccontextmanager
    async def _operation(self, name: str):
        """Guard against concurrent operations.

        Args:
            name: Name of the operation being guarded

        Raises:
            ConcurrentAccessError: If another operation is already active
        """
        if self._active_operation is not None:
            raise ConcurrentAccessError(active_op=self._active_operation, attempted_op=name)

        self._active_operation = name
        try:
            yield
        finally:
            self._active_operation = None

    @property
    def career_name(self) -> str:
        """Get current career display name."""
        return self._career_name

    @property
    def career_code(self) -> str:
        """Get current hyphen-delimited career code."""
        return self._career_code

    @property
    def is_electives(self) -> bool:
        """Return whether elective flow is active."""
        return self._is_electives

    @property
    def status(self) -> status.SiaSessionStatus:
        """Get current lifecycle status."""
        return self._status

    @property
    def course_list(self) -> list[dict[str, str]]:
        """Get loaded course list for the selected career."""
        return self._course_list

    @property
    def career_indices(self) -> list[str]:
        """Get parsed career code indices."""
        return self._career_indices

    def _sync_state_from_rust(self, state: sia_scraper_rust.SessionStateModel) -> None:
        """Sync local cache from Rust state model."""
        self._status = status.SiaSessionStatus[state.status]
        self._career_code = state.career_code
        self._career_name = state.career_name or DEFAULT_CAREER_NAME
        self._is_electives = state.is_electives
        self._career_indices = state.career_code.split("-") if state.career_code else []
        self._course_list = [{entry.course_code: entry.course_name} for entry in state.course_list]

    async def init_session(self) -> None:
        """Initialize session by delegating to Rust PySiaSession."""
        async with self._operation("init_session"):
            state = await self._rust_session.init_session()
            self._sync_state_from_rust(state)

    async def set_career(self, search_code: str, is_electives: bool = False) -> None:
        """Navigate to career and load course list."""
        async with self._operation("set_career"):
            state = await self._rust_session.set_career(search_code, is_electives)
            self._sync_state_from_rust(state)

    async def scrape_course_info(self, course_index: int) -> sia_scraper_rust.CourseInfoModel:
        """Scrape course info via Rust (zero-copy, no XML crossing FFI)."""
        async with self._operation("scrape_course_info"):
            return await self._rust_session.scrape_course_info(course_index)

    async def scrape_course_prereqs(self, course_index: int) -> sia_scraper_rust.CoursePrereqsModel:
        """Scrape course prerequisites via Rust."""
        async with self._operation("scrape_course_prereqs"):
            return await self._rust_session.scrape_course_prereqs(course_index)

    async def get_state(self) -> sia_scraper_rust.SessionStateModel:
        """Get current session state from Rust."""
        async with self._operation("get_state"):
            return await self._rust_session.get_state()

    async def close(self) -> None:
        """Reset session state (Rust session doesn't require explicit close)."""
        async with self._operation("close"):
            self._status = status.SiaSessionStatus.NO_SESSION
            self._career_code = ""
            self._career_name = DEFAULT_CAREER_NAME
            self._is_electives = False
            self._career_indices = []
            self._course_list = []

    def get_session_data(self) -> sia_scraper_rust.SessionStateModel:
        """Serialize session state for persistence."""
        return sia_scraper_rust.SessionStateModel(
            session_headers={},
            session_cookies={},
            params={"Adf-Page-Id": "1", "Adf-Window-Id": ""},
            career_code=self._career_code,
            career_name=self._career_name,
            is_electives=self._is_electives,
            status=self._status.value,
            course_list=[
                sia_scraper_rust.CourseListEntryModel(
                    course_code=next(iter(row.keys())),
                    course_name=next(iter(row.values())),
                )
                for row in self._course_list
            ],
            javax_faces_view_state=None,
        )

    async def __aenter__(self) -> "SiaSession":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        await self.close()
