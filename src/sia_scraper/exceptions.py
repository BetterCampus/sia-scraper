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

    Example: Trying to exit_course_page() when STATUS != ON_COURSE_PAGE.
    """

    def __init__(self) -> None:
        """Initialize with invalid status message."""
        super().__init__("Invalid action to current SIA status")


# Backward-compatible aliases for existing call sites.
SiaSessionException.SessionNotSet = SessionNotSet  # type: ignore[attr-defined]
SiaSessionException.CareerNotSet = CareerNotSet  # type: ignore[attr-defined]
SiaSessionException.TimeoutError = TimeoutError  # type: ignore[attr-defined]
SiaSessionException.InvalidStatus = InvalidStatus  # type: ignore[attr-defined]
