"""Thin Python wrapper around Rust PySiaSession."""

from contextlib import asynccontextmanager
from typing import Literal

import sia_scraper_rust

from .constants import status
from .constants.defaults import DEFAULT_CAREER_NAME
from .core.exceptions import (
    CareerNotSet,
    ConcurrentAccessError,
    SessionNotSet,
    SiaSessionException,
)

_SESSION_NOT_INIT_MARKER = "not initialized"

ErrorModeStr = Literal["abort", "skip", "retry"]


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
        self._course_list = [
            {"code": entry.code, "name": entry.name} for entry in state.course_list
        ]
        self._validate_course_list()

    def _validate_course_list(self) -> None:
        """Validate course list format (defense-in-depth)."""
        for i, course in enumerate(self._course_list):
            if not isinstance(course, dict):
                raise TypeError(
                    f"Invalid course list format at index {i}: {type(course).__name__}. "
                    "Expected dict with 'code' and 'name' string keys."
                )
            if "code" not in course or "name" not in course:
                raise ValueError(
                    f"Invalid course list format at index {i}: {course}. "
                    "Expected dict with 'code' and 'name' keys."
                )
            code_val = course["code"]
            name_val = course["name"]
            if not isinstance(code_val, str) or not isinstance(name_val, str):
                raise TypeError(
                    f"Invalid course list format at index {i}: code={code_val!r}, name={name_val!r}. "
                    "Expected 'code' and 'name' values to be strings."
                )

    def _raise_if_session_not_set(self, exc: Exception) -> None:
        """Raise SessionNotSet when Rust reports an uninitialized session.

        This method provides a fallback mechanism for detecting uninitialized
        session errors from the Rust layer. It uses structured exception type
        checking when available, with string-based fallback to the
        _SESSION_NOT_INIT_MARKER for compatibility.

        Note:
            This string-based detection is fragile if the Rust error message
            changes. Consider adding a stable error constant or structured
            error code on the Rust side for future improvement.

        Args:
            exc: The exception raised by the Rust session.

        Raises:
            SessionNotSet: If the exception indicates an uninitialized session.

        Todo:
            Replace string matching with a dedicated error type or constant
            on the Rust side (e.g., SiaSessionException::SessionNotSet) to
            avoid relying on message content.
        """
        exc_type_name = type(exc).__name__
        if exc_type_name == "SessionError" and _SESSION_NOT_INIT_MARKER in str(exc).lower():
            raise SessionNotSet from exc

    async def init_session(self) -> None:
        """Initialize session by delegating to Rust PySiaSession.

        Raises:
            SessionNotSet: If Rust session initialization fails.
            SiaSessionException: For other session-related errors.
        """
        async with self._operation("init_session"):
            try:
                state = await self._rust_session.init_session()
            except sia_scraper_rust.SessionError as exc:
                raise SessionNotSet from exc
            except SiaSessionException:
                raise
            except sia_scraper_rust.SiaScraperException as exc:
                raise SiaSessionException(f"Session initialization failed: {exc}") from exc
            self._sync_state_from_rust(state)

    async def set_career(self, search_code: str, is_electives: bool = False) -> None:
        """Navigate to career and load course list.

        Raises:
            CareerNotSet: If career selection fails.
            SiaSessionException: For other session-related errors.
        """
        async with self._operation("set_career"):
            try:
                state = await self._rust_session.set_career(search_code, is_electives)
            except sia_scraper_rust.SessionError as exc:
                self._raise_if_session_not_set(exc)
                raise CareerNotSet from exc
            except SiaSessionException:
                raise
            except sia_scraper_rust.SiaScraperException as exc:
                raise SiaSessionException(f"Career selection failed: {exc}") from exc
            self._sync_state_from_rust(state)

    async def scrape_course_info(self, course_index: int) -> sia_scraper_rust.CourseInfoModel:
        """Scrape course info via Rust (zero-copy, no XML crossing FFI).

        Raises:
            sia_scraper_rust.NetworkError: If connection fails.
            sia_scraper_rust.HttpStatusError: If server returns error status.
            sia_scraper_rust.SiaTimeoutError: If request times out.
            sia_scraper_rust.ParseError: If response cannot be parsed.
            sia_scraper_rust.SessionError: If session not initialized.
        """
        async with self._operation("scrape_course_info"):
            return await self._rust_session.scrape_course_info(course_index)

    async def scrape_course_prereqs(self, course_index: int) -> sia_scraper_rust.CoursePrereqsModel:
        """Scrape course prerequisites via Rust.

        Raises:
            sia_scraper_rust.NetworkError: If connection fails.
            sia_scraper_rust.HttpStatusError: If server returns error status.
            sia_scraper_rust.SiaTimeoutError: If request times out.
            sia_scraper_rust.ParseError: If response cannot be parsed.
            sia_scraper_rust.SessionError: If session not initialized.
        """
        async with self._operation("scrape_course_prereqs"):
            return await self._rust_session.scrape_course_prereqs(course_index)

    async def get_state(self) -> sia_scraper_rust.SessionStateModel:
        """Get current session state from Rust and sync local cache."""
        async with self._operation("get_state"):
            state = await self._rust_session.get_state()
            self._sync_state_from_rust(state)
            return state

    async def scrape_courses(
        self,
        indices: list[int],
        mode: ErrorModeStr = "abort",
        retries: int | None = None,
        delay: int | None = None,
    ) -> sia_scraper_rust.ScrapeResult:
        """Scrape multiple courses sequentially using Rust batch scraping.

        Args:
            indices: List of course indices to scrape.
            mode: Error handling mode - "abort", "skip", or "retry".
            retries: Maximum retry attempts per course (retry mode only). None uses Rust default (3).
            delay: Base delay between retries in milliseconds. None uses Rust default (800ms).

        Returns:
            ScrapeResult with successes and failures.

        Raises:
            SessionNotSet: If session not initialized.
            sia_scraper_rust.AbortError: In abort mode on first failure.
            sia_scraper_rust.NetworkError: If connection fails.
            sia_scraper_rust.HttpStatusError: If server returns error status.
            sia_scraper_rust.SiaTimeoutError: If request times out.
            sia_scraper_rust.ParseError: If response cannot be parsed.

        Example:
            >>> result = await session.scrape_courses([0, 1, 2], mode="skip")
            >>> print(f"Success rate: {result.success_rate():.1%}")
            >>> for course in result.successes:
            ...     print(course.course_name)
        """
        async with self._operation("scrape_courses"):
            try:
                return await self._rust_session.scrape_courses(indices, mode, retries, delay)
            except sia_scraper_rust.SessionError as exc:
                self._raise_if_session_not_set(exc)
                raise

    async def scrape_courses_parallel(
        self,
        indices: list[int],
        mode: ErrorModeStr = "abort",
        max_concurrent: int | None = None,
        retries: int | None = None,
        delay: int | None = None,
    ) -> sia_scraper_rust.ScrapeResult:
        """Scrape multiple courses concurrently using Rust parallel scraping.

        Args:
            indices: List of course indices to scrape.
            mode: Error handling mode - "abort", "skip", or "retry".
            max_concurrent: Maximum number of concurrent scraping operations.
                None delegates to the Rust default (5).
            retries: Maximum retry attempts per course (retry mode only). None uses Rust default (3).
            delay: Base delay between retries in milliseconds. None uses Rust default (800ms).

        Returns:
            ScrapeResult with successes and failures.

        Raises:
            SessionNotSet: If session not initialized.
            sia_scraper_rust.AbortError: In abort mode on first failure.
            sia_scraper_rust.NetworkError: If connection fails.
            sia_scraper_rust.HttpStatusError: If server returns error status.
            sia_scraper_rust.SiaTimeoutError: If request times out.
            sia_scraper_rust.ParseError: If response cannot be parsed.

        Example:
            >>> result = await session.scrape_courses_parallel([0, 1, 2], mode="skip", max_concurrent=5)
            >>> print(f"Success rate: {result.success_rate():.1%}")
            >>> for course in result.successes:
            ...     print(course.course_name)
        """
        async with self._operation("scrape_courses_parallel"):
            try:
                return await self._rust_session.scrape_courses_parallel(
                    indices, mode, max_concurrent, retries, delay
                )
            except sia_scraper_rust.SessionError as exc:
                self._raise_if_session_not_set(exc)
                raise

    async def close(self) -> None:
        """Reset session state and clear Rust session."""
        async with self._operation("close"):
            if self._rust_session.is_initialized():
                await self._rust_session.reset()
            self._status = status.SiaSessionStatus.NO_SESSION
            self._career_code = ""
            self._career_name = DEFAULT_CAREER_NAME
            self._is_electives = False
            self._career_indices = []
            self._course_list = []

    async def get_session_data(self) -> dict:
        """Serialize session state for persistence."""
        return await self._rust_session.get_session_data()

    @classmethod
    async def from_state(cls, state: dict) -> "SiaSession":
        """Restore a session from previously saved state.

        Args:
            state: Dictionary with session state (timeout, state_dict)

        Returns:
            Restored SiaSession instance

        Example:
            >>> saved_state = await session.get_session_data()
            >>> new_session = await SiaSession.from_state(saved_state)
        """
        timeout = state.get("timeout", 15)
        session = cls(timeout)
        session._rust_session = await sia_scraper_rust.PySiaSession.from_state(state)
        state_model = await session._rust_session.get_state()
        session._sync_state_from_rust(state_model)
        return session

    async def __aenter__(self) -> "SiaSession":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        await self.close()
