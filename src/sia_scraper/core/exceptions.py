"""SIA Exception classes.

This module defines all custom exceptions used throughout the sia_scraper library
for handling session-related errors.
"""


class SiaSessionException(Exception):
    """Base exception for SIA session-related errors."""

    SessionNotSet: type["SessionNotSet"]
    CareerNotSet: type["CareerNotSet"]
    TimeoutError: type["TimeoutError"]
    InvalidStatus: type["InvalidStatus"]


class SessionNotSet(SiaSessionException):
    """Raised when attempting session operations without an active session.

    Resolution: Call init_session() or load_session(session_data) first.
    """

    def __init__(self) -> None:
        """Initialize with instruction to start session."""
        super().__init__("Must set session by create_session() or load_session(session_data)")


class CareerNotSet(SiaSessionException):
    """Raised when attempting course operations without selecting a career.

    Resolution: Call set_career(search_code) to navigate to a career page.
    """

    def __init__(self) -> None:
        """Initialize with instruction to set career."""
        super().__init__("Must set career by set_career(search_code)")


class TimeoutError(SiaSessionException):
    """Raised when SIA HTTP requests exceed the configured timeout.

    This typically indicates SIA server overload or network issues.
    """

    def __init__(self) -> None:
        """Initialize with timeout message."""
        super().__init__("Request to SIA took too long")


class InvalidStatus(SiaSessionException):
    """Raised when attempting an action incompatible with current session state.

    Example: Trying to exit_course_page() when status != ON_COURSE_PAGE.
    """

    def __init__(self) -> None:
        """Initialize with invalid status message."""
        super().__init__("Invalid action to current SIA status")


class ConcurrentAccessError(SiaSessionException):
    """Raised when concurrent access to SiaSession is detected.

    SiaSession maintains stateful Oracle ADF navigation state and does not
    support concurrent operations. Methods must be called sequentially.

    Resolution:
        - Await each operation before starting the next
        - Do not use asyncio.gather() on the same session instance
        - Create multiple session instances for parallel operations

    Example of INVALID usage:
        >>> session = await SiaSession.create()
        >>> await session.set_career("0-2-8-3")
        >>> # This will raise ConcurrentAccessError:
        >>> task1 = asyncio.create_task(session.scrape_course_info(0))
        >>> task2 = asyncio.create_task(session.set_career("1-2-3-4"))
        >>> await asyncio.gather(task1, task2)  # ERROR!

    Example of VALID usage:
        >>> session = await SiaSession.create()
        >>> await session.set_career("0-2-8-3")
        >>> course1 = await session.scrape_course_info(0)  # Sequential - OK
        >>> course2 = await session.scrape_course_info(1)  # Sequential - OK
    """

    def __init__(self, active_op: str, attempted_op: str) -> None:
        """Initialize with operation details.

        Args:
            active_op: Name of the currently running operation
            attempted_op: Name of the operation that was attempted
        """
        super().__init__(
            f"Concurrent session access detected: "
            f"cannot start '{attempted_op}' while '{active_op}' is running. "
            f"SiaSession methods must be called sequentially."
        )
        self.active_operation = active_op
        self.attempted_operation = attempted_op


# Backward-compatible aliases for existing call sites.
SiaSessionException.SessionNotSet = SessionNotSet  # type: ignore[attr-defined]
SiaSessionException.CareerNotSet = CareerNotSet  # type: ignore[attr-defined]
SiaSessionException.TimeoutError = TimeoutError  # type: ignore[attr-defined]
SiaSessionException.InvalidStatus = InvalidStatus  # type: ignore[attr-defined]
SiaSessionException.ConcurrentAccessError = ConcurrentAccessError  # type: ignore[attr-defined]
