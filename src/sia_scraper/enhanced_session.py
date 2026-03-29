"""Enhanced HTTP session with automatic timeout handling."""

from typing import Any

import requests


class EnhancedSession(requests.Session):
    """HTTP session wrapper with automatic timeout handling."""

    def __init__(self, timeout: int) -> None:
        """Initialize enhanced session with default timeout.

        ## Args
            timeout: Default timeout in seconds for all requests.
        """
        super().__init__()
        self.timeout: int = timeout

    def request(  # type: ignore[override]
        self,
        method: str | bytes,
        url: str | bytes,
        timeout: int | None = None,
        **kwargs: Any,
    ) -> requests.Response:
        """Make HTTP request with default timeout if not specified."""
        return super().request(
            method,
            url,
            timeout=(timeout if timeout is not None else self.timeout),
            **kwargs,
        )
