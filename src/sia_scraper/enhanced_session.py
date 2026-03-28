"""Enhanced HTTP session with automatic timeout handling."""

from typing import Any

import requests


class EnhancedSession(requests.Session):
    """HTTP session wrapper with automatic timeout handling.

    Extends requests.Session to automatically apply a default timeout
    to all requests that don't explicitly specify one. Prevents indefinite
    hangs when remote servers are slow or unresponsive.

    ## Attributes
        timeout (int): Default request timeout in seconds applied to all requests.

    ## Note
        This is a thin wrapper around requests.Session. All parameters and return
        values are passed through to the parent class unchanged.

    ## Example
        >>> session = EnhancedSession(timeout=15)
        >>> response = session.get('https://sia.unal.edu.co/...')  # Uses 15s timeout
        >>> response = session.post(url, timeout=30)  # Override: uses 30s timeout
    """

    def __init__(self, timeout: int) -> None:
        """Initialize enhanced session with default timeout.

        ## Args
            timeout: Default timeout in seconds for all requests without explicit timeout.
        """
        super().__init__()
        self.timeout: int = timeout

    def request(
        self,
        method: str | bytes,
        url: str | bytes,
        params: Any = None,
        data: Any = None,
        headers: Any = None,
        cookies: Any = None,
        files: Any = None,
        auth: Any = None,
        timeout: Any = None,
        allow_redirects: bool = True,
        proxies: Any = None,
        hooks: Any = None,
        stream: Any = None,
        verify: Any = None,
        cert: Any = None,
        json: Any = None,
    ) -> requests.Response:
        """Make HTTP request with default timeout if not specified.

        ## Args
            method: HTTP method ('GET', 'POST', etc.).
            url: Request URL.
            params: Query parameters to append to URL.
            data: Request body data.
            headers: HTTP headers dictionary.
            cookies: Cookies to send with request.
            files: Files to upload.
            auth: Authentication tuple or object.
            timeout: Request timeout in seconds. Uses session default if not specified.
            allow_redirects: Whether to follow redirects.
            proxies: Proxy configuration dictionary.
            hooks: Event hooks dictionary.
            stream: Whether to stream the response.
            verify: SSL verification setting.
            cert: Client certificate configuration.
            json: JSON data to send in request body.

        ## Returns
            requests.Response object with server's HTTP response.

        ## Raises
            requests.exceptions.Timeout: If request times out.
            requests.exceptions.ConnectionError: If connection to server fails.
            requests.exceptions.HTTPError: If response status code indicates error.
        """
        if timeout is None:
            timeout = self.timeout
        return super().request(
            method=method,
            url=url,
            params=params,
            data=data,
            headers=headers,
            cookies=cookies,
            files=files,
            auth=auth,
            timeout=timeout,
            allow_redirects=allow_redirects,
            proxies=proxies,
            hooks=hooks,
            stream=stream,
            verify=verify,
            cert=cert,
            json=json,
        )
