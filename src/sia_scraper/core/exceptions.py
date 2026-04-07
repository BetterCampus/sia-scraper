"""SIA Exception classes.

This module defines all custom exceptions used throughout the sia_scraper library
for handling session-related errors.

The Rust extension provides granular exception types that are re-exported here
for convenience. Python-level exceptions remain independent to maintain a clean
separation between the Python API and the Rust implementation.

Rust exceptions (re-exported from sia_scraper_rust):
    - NetworkError: Network connectivity failures
    - HttpStatusError: HTTP error responses (4xx, 5xx)
    - SiaTimeoutError: Request timeout errors
    - ParseError: HTML/XML parsing failures
    - SessionError: Session state/lifecycle errors
    - SiaScraperException: Base exception for all Rust exceptions
"""

from sia_scraper_rust import (
    HttpStatusError,
    NetworkError,
    ParseError,
    SessionError,
    SiaScraperException,
    SiaTimeoutError,
)


class SiaSessionException(Exception):
    """Base exception for SIA session-related errors.

    This exception hierarchy is independent of the Rust exception hierarchy.
    Rust exceptions are caught and re-raised as appropriate Python exceptions
    by the session wrapper layer.

    Subclasses:
        - SessionNotSet: Operation attempted without active session
        - CareerNotSet: Operation attempted without selecting a career
        - TimeoutError: Request timeout (legacy, prefer SiaTimeoutError)
        - InvalidStatus: Operation incompatible with current session state
        - ConcurrentAccessError: Concurrent operation detected
        - InvalidSessionDataError: Session data validation failed
        - MissingSessionFieldError: Required field missing from session data
    """

    SessionNotSet: type["SessionNotSet"]
    CareerNotSet: type["CareerNotSet"]
    TimeoutError: type["TimeoutError"]
    InvalidStatus: type["InvalidStatus"]
    ConcurrentAccessError: type["ConcurrentAccessError"]
    InvalidSessionDataError: type["InvalidSessionDataError"]
    MissingSessionFieldError: type["MissingSessionFieldError"]


class SessionNotSet(SiaSessionException):
    """Raised when attempting session operations without an active session.

    Resolution: Call init_session() or load_session(session_data) first.
    """

    def __init__(self) -> None:
        """Initialize with instruction to start session."""
        super().__init__("Must set session by create_session() or load_session(session_data)")


class InvalidSessionDataError(SiaSessionException):
    """Raised when session_data validation fails.

    This exception is raised when loading session data from a dict or
    SessionStateModel and the data fails validation checks (e.g., wrong
    types, missing required fields, invalid format).

    Attributes:
        field: Optional field name where validation failed.
        index: Optional index in a list (e.g., course_list[index]).
    """

    field: str | None
    index: int | None

    def __init__(
        self,
        field: str | None = None,
        index: int | None = None,
        message: str | None = None,
    ) -> None:
        """Initialize with optional field, index, and message context.

        Args:
            field: Optional name of the field that failed validation.
            index: Optional index in a list where validation failed.
            message: Optional custom error message override.
        """
        if message:
            super().__init__(message)
        else:
            msg = "Invalid session_data"
            if field:
                msg += f" '{field}'"
                if index is not None:
                    msg += f"[{index}]"
            elif index is not None:
                msg += f" at index [{index}]"
            msg += ": validation failed"
            super().__init__(msg)
        self.field = field
        self.index = index


class MissingSessionFieldError(SiaSessionException):
    """Raised when a required field is missing from session data.

    This exception is raised during session data loading when required
    fields are missing from the input dictionary or model.

    Attributes:
        field: Name of the missing required field.
    """

    field: str

    def __init__(self, field: str) -> None:
        """Initialize with missing field name.

        Args:
            field: Name of the missing required field.
        """
        super().__init__(f"Missing required session field: '{field}'")
        self.field = field


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

    Note:
        The Rust extension raises SiaTimeoutError for timeout conditions.
        This Python exception is retained for backward compatibility.
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
SiaSessionException.InvalidSessionDataError = InvalidSessionDataError  # type: ignore[attr-defined]
SiaSessionException.MissingSessionFieldError = MissingSessionFieldError  # type: ignore[attr-defined]

__all__ = [
    "SiaSessionException",
    "SessionNotSet",
    "CareerNotSet",
    "TimeoutError",
    "InvalidStatus",
    "ConcurrentAccessError",
    "InvalidSessionDataError",
    "MissingSessionFieldError",
    "SiaScraperException",
    "NetworkError",
    "HttpStatusError",
    "SiaTimeoutError",
    "ParseError",
    "SessionError",
]
