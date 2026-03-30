"""SIA Session decorators.

This module provides decorators for SiaSession methods to enforce session state,
career selection, status validation, and timeout error handling with automatic retry.
"""

from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from requests.exceptions import ConnectionError, ReadTimeout, Timeout
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from sia_scraper.constants import SiaSessionStatus

from ..core import SiaSessionException

P = ParamSpec("P")
R = TypeVar("R")


def check_session(func: Callable[P, R]) -> Callable[P, R]:
    """Decorator: Ensures an active HTTP session exists before executing method.

    ## Raises
        SiaSessionException.SessionNotSet: If session is None
    """

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        self = args[0]
        if not self._has_session:  # type: ignore[attr-defined]
            raise SiaSessionException.SessionNotSet from None
        return func(*args, **kwargs)

    return wrapper


def check_status(status: SiaSessionStatus) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator factory: Ensures session is in required status before executing.

    ## Args
        status: Required SiaSessionStatus for method execution

    ## Returns
        Decorator function that validates STATUS matches required value

    ## Raises
        SiaSessionException.InvalidStatus: If current STATUS != required status
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        """Apply status check to a function."""

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            self = args[0]
            if self.STATUS != status:  # type: ignore[attr-defined]
                raise SiaSessionException.InvalidStatus from None
            return func(*args, **kwargs)

        return wrapper

    return decorator


def handle_timeout_error(func: Callable[P, R]) -> Callable[P, R]:
    """Decorator: Wraps HTTP operations and converts timeout exceptions.

    ## Raises
        SiaSessionException.TimeoutError: When requests timeout or connection fails
    """

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return func(*args, **kwargs)
        except (Timeout, ReadTimeout, ConnectionError) as e:
            raise SiaSessionException.TimeoutError from e

    return wrapper


def handle_timeout_with_retry(func: Callable[P, R]) -> Callable[P, R]:
    """Decorator: Wraps HTTP operations with retry logic and timeout handling.

    Retries up to 3 times with exponential backoff (2s → 4s → 8s, max 10s)
    on network errors (Timeout, ReadTimeout, ConnectionError).
    Converts final exception to SiaSessionException.TimeoutError.

    ## Configuration
        - Max attempts: 3
        - Backoff: exponential with multiplier=1, min=2, max=10

    ## Raises
        SiaSessionException.TimeoutError: When all retry attempts fail

    ## Example
        @handle_timeout_with_retry
        def get_post(self, data: dict[str, str]) -> Any:
            return self._session.post(url, data=data)
    """

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Timeout, ReadTimeout, ConnectionError)),
        reraise=True,
    )
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return func(*args, **kwargs)
        except (Timeout, ReadTimeout, ConnectionError) as e:
            raise SiaSessionException.TimeoutError from e

    return wrapper
