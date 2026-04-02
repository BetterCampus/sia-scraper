"""Rust-backed async SIA session management."""

from contextlib import asynccontextmanager

import sia_scraper_rust

from .constants import status
from .constants.defaults import DEFAULT_CAREER_NAME
from .core import SiaSessionException
from .core.exceptions import ConcurrentAccessError


class _SessionRuntimeState:
    """Lightweight runtime state returned by Rust session helpers."""

    __slots__ = ("javax_faces_ViewState", "course_list")

    def __init__(self) -> None:
        self.javax_faces_ViewState: str | None = None
        self.course_list: list[dict[str, str]] = []


def _typed_state_to_runtime(
    state: sia_scraper_rust.SessionStateModel,
) -> _SessionRuntimeState:
    """Convert typed Rust session state to runtime state."""
    runtime = _SessionRuntimeState()
    runtime.javax_faces_ViewState = state.javax_faces_view_state
    runtime.course_list = [{entry.course_code: entry.course_name} for entry in state.course_list]
    return runtime


def _legacy_course_list_to_typed(
    course_list: object,
) -> list[sia_scraper_rust.CourseListEntryModel]:
    if not isinstance(course_list, list):
        raise TypeError("course_list must be a list")

    typed_entries: list[sia_scraper_rust.CourseListEntryModel] = []
    for index, row in enumerate(course_list):
        if not isinstance(row, dict):
            raise TypeError(f"course_list[{index}] must be a dict")
        if len(row) != 1:
            raise ValueError(f"course_list[{index}] must contain exactly one course entry")
        course_code, course_name = next(iter(row.items()))
        typed_entries.append(
            sia_scraper_rust.CourseListEntryModel(
                course_code=str(course_code),
                course_name=str(course_name),
            )
        )

    return typed_entries


class SiaSession:
    """Async SIA session backed by Rust reqwest/tokio HTTP client.

    **IMPORTANT: This class does NOT support concurrent operations.**

    SiaSession maintains stateful Oracle ADF navigation context. Methods must
    be called sequentially. Concurrent calls will raise `ConcurrentAccessError`.

    For parallel scraping, create multiple independent `SiaSession` instances.

    Example (correct sequential usage):
        >>> session = await SiaSession.create()
        >>> await session.set_career("0-2-8-3")
        >>> for i in range(10):
        ...     xml = await session.get_course_xml(i)  # OK - sequential

    Example (incorrect concurrent usage):
        >>> # DO NOT DO THIS:
        >>> tasks = [session.get_course_xml(i) for i in range(10)]
        >>> await asyncio.gather(*tasks)  # Will raise ConcurrentAccessError!

    Example (correct parallel usage):
        >>> # Create separate sessions for parallel work:
        >>> sessions = [await SiaSession.create() for _ in range(5)]
        >>> tasks = [s.set_career("0-2-8-3") for s in sessions]
        >>> await asyncio.gather(*tasks)  # OK - different instances
    """

    def __init__(self, timeout: int = 15) -> None:
        self._timeout = timeout
        self._career_name = DEFAULT_CAREER_NAME
        self._career_code = ""
        self._is_electives = False
        self._career_indices: list[str] = []
        self._status: status.SiaSessionStatus = status.SiaSessionStatus.NO_SESSION
        self._session_state = _SessionRuntimeState()
        self._typed_state: sia_scraper_rust.SessionStateModel | None = None
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
        return self._session_state.course_list

    @property
    def career_indices(self) -> list[str]:
        """Get parsed career code indices."""
        return self._career_indices

    async def init_session(self) -> None:
        """Initialize HTTP session with SIA and fetch initial ViewState."""
        async with self._operation("init_session"):
            typed_state = await sia_scraper_rust.init_sia_session(self._timeout)  # type: ignore[attr-defined]
            self._status = status.SiaSessionStatus[typed_state.status]
            self._career_code = typed_state.career_code
            self._career_name = typed_state.career_name
            self._is_electives = typed_state.is_electives
            self._career_indices = (
                typed_state.career_code.split("-") if typed_state.career_code else []
            )
            self._session_state = _typed_state_to_runtime(typed_state)
            self._typed_state = typed_state

    async def set_career(self, search_code: str, is_electives: bool = False) -> None:
        """Navigate to career and load course list."""
        async with self._operation("set_career"):
            typed_state = await sia_scraper_rust.set_career(  # type: ignore[attr-defined]
                self._timeout,
                search_code,
                is_electives,
            )
            self._career_code = typed_state.career_code
            self._career_indices = (
                typed_state.career_code.split("-") if typed_state.career_code else []
            )
            self._is_electives = typed_state.is_electives
            self._career_name = typed_state.career_name
            self._session_state = _typed_state_to_runtime(typed_state)
            self._status = status.SiaSessionStatus[typed_state.status]
            self._typed_state = typed_state

    async def get_course_xml(self, course_index: int) -> str:
        """Get course detail XML for given index."""
        async with self._operation("get_course_xml"):
            if self._status not in (
                status.SiaSessionStatus.ON_CAREER_PAGE,
                status.SiaSessionStatus.ON_COURSE_PAGE,
            ):
                raise SiaSessionException.InvalidStatus from None

            course_list = self.course_list
            if not 0 <= course_index < len(course_list):
                raise ValueError(
                    f"Course index {course_index} out of range (0-{max(len(course_list) - 1, 0)})"
                )

            result = await sia_scraper_rust.get_course_xml(  # type: ignore[attr-defined]
                self._timeout,
                course_index,
                self._career_indices,
                self._is_electives,
            )
            return str(result)

    async def close(self) -> None:
        """Close the session and cleanup resources."""
        async with self._operation("close"):
            self._status = status.SiaSessionStatus.NO_SESSION
            self._session_state = _SessionRuntimeState()
            self._typed_state = None

    def get_session_data(self) -> sia_scraper_rust.SessionStateModel:
        """Serialize session state for persistence."""
        if self._typed_state is not None:
            return self._typed_state

        return sia_scraper_rust.SessionStateModel(
            session_headers={},
            session_cookies={},
            params={"Adf-Page-Id": "1", "Adf-Window-Id": ""},
            career_code=self._career_code,
            career_name=self._career_name,
            is_electives=self._is_electives,
            status=self._status.value,
            course_list=_legacy_course_list_to_typed(self.course_list),
            javax_faces_view_state=self._session_state.javax_faces_ViewState,
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
