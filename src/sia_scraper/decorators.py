"""SIA Session decorators.

This module provides decorators for SiaSession methods to enforce session state,
career selection, status validation, and timeout error handling.
"""

from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from sia_scraper.constants import SiaSessionStatus
from sia_scraper.exceptions import SiaSessionException

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
        if self._SiaSession__session is None:  # type: ignore[attr-defined]
            raise SiaSessionException.SessionNotSet from SiaSessionException
        return func(*args, **kwargs)

    return wrapper


def check_career(func: Callable[P, R]) -> Callable[P, R]:
    """Decorator: Ensures a career has been selected before executing method.

    ## Raises
        SiaSessionException.CareerNotSet: If career_code is empty
    """

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        self = args[0]
        if self._SiaSession__career_code == "":  # type: ignore[attr-defined]
            raise SiaSessionException.CareerNotSet from SiaSessionException
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
            if self._SiaSession__STATUS != status:  # type: ignore[attr-defined]
                raise SiaSessionException.InvalidStatus from SiaSessionException
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
        from requests.exceptions import ConnectionError, ReadTimeout, Timeout

        try:
            return func(*args, **kwargs)
        except (Timeout, ReadTimeout, ConnectionError) as e:
            raise SiaSessionException.TimeoutError from e

    return wrapper
