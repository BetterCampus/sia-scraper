"""SIA Exception classes.

This module defines all custom exceptions used throughout the sia_scraper library
for handling session-related errors.
"""


class SiaSessionException(Exception):
    """Base exception for SIA session-related errors."""

    class SessionNotSet(Exception):
        """Raised when attempting session operations without an active session.

        Resolution: Call init_session() or load_session(session_data) first.
        """

        def __init__(self) -> None:
            """Initialize with instruction to start session."""
            super().__init__("Must set session by create_session() or load_session(session_data)")

    class CareerNotSet(Exception):
        """Raised when attempting course operations without selecting a career.

        Resolution: Call set_career(search_code) to navigate to a career page.
        """

        def __init__(self) -> None:
            """Initialize with instruction to set career."""
            super().__init__("Must set career by set_career(search_code)")

    class TimeoutError(Exception):
        """Raised when SIA HTTP requests exceed the configured timeout.

        This typically indicates SIA server overload or network issues.
        """

        def __init__(self) -> None:
            """Initialize with timeout message."""
            super().__init__("Request to SIA took too long")

    class InvalidStatus(Exception):
        """Raised when attempting an action incompatible with current session state.

        Example: Trying to exit_course_page() when STATUS != ON_COURSE_PAGE.
        """

        def __init__(self) -> None:
            """Initialize with invalid status message."""
            super().__init__("Invalid action to current SIA status")
