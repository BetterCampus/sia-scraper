"""Comprehensive test suite for EnhancedSession module.

This module contains pytest-based unit tests for the EnhancedSession class,
which extends requests.Session to automatically apply default timeouts to
all HTTP requests. The tests cover initialization, timeout behavior, and
parameter forwarding to ensure 100% code coverage.

Tests are organized into logical groups:
- Initialization and session setup
- Default timeout application
- Explicit timeout override behavior
- Parameter passthrough to parent Session
- Type variations (str vs bytes for method/url)

Example:
    Run all tests with coverage::

        pytest tests/test_enhanced_session.py --cov=src/sia_scraper/enhanced_session
"""

from typing import Any
from unittest.mock import MagicMock

import requests

from sia_scraper.enhanced_session import EnhancedSession


class TestEnhancedSessionInitialization:
    """Test initialization and basic setup of EnhancedSession."""

    def test_init_sets_timeout_attribute(self) -> None:
        """Test that __init__ properly sets the timeout attribute.

        Verifies that the timeout value passed to the constructor
        is correctly stored in the instance attribute.
        """
        session = EnhancedSession(timeout=30)
        assert session.timeout == 30

    def test_init_with_different_timeout_values(self) -> None:
        """Test initialization with various timeout values.

        Verifies that different timeout values are correctly stored.
        """
        session_10 = EnhancedSession(timeout=10)
        session_60 = EnhancedSession(timeout=60)
        session_1 = EnhancedSession(timeout=1)

        assert session_10.timeout == 10
        assert session_60.timeout == 60
        assert session_1.timeout == 1

    def test_inherits_from_requests_session(self) -> None:
        """Test that EnhancedSession inherits from requests.Session.

        Verifies that the instance is a valid requests.Session and has
        all expected Session attributes and methods.
        """
        session = EnhancedSession(timeout=15)
        assert isinstance(session, requests.Session)
        assert hasattr(session, "get")
        assert hasattr(session, "post")
        assert hasattr(session, "headers")
        assert hasattr(session, "cookies")


class TestEnhancedSessionDefaultTimeout:
    """Test default timeout application when not explicitly specified."""

    def test_request_uses_default_timeout_when_none(self, mocker: Any) -> None:
        """Test that default timeout is applied when timeout=None.

        Verifies that when no timeout is specified in the request call,
        the session's default timeout is automatically applied.
        """
        mock_parent_request = mocker.patch("requests.Session.request")
        mock_response = MagicMock(spec=requests.Response)
        mock_parent_request.return_value = mock_response

        session = EnhancedSession(timeout=25)
        session.request("GET", "https://example.com")

        mock_parent_request.assert_called_once_with(
            method="GET",
            url="https://example.com",
            params=None,
            data=None,
            headers=None,
            cookies=None,
            files=None,
            auth=None,
            timeout=25,  # Default timeout applied
            allow_redirects=True,
            proxies=None,
            hooks=None,
            stream=None,
            verify=None,
            cert=None,
            json=None,
        )

    def test_get_method_uses_default_timeout(self, mocker: Any) -> None:
        """Test that GET requests use default timeout.

        Verifies that convenience methods like get() inherit the
        default timeout behavior through the request() method.
        """
        mock_parent_request = mocker.patch("requests.Session.request")
        mock_response = MagicMock(spec=requests.Response)
        mock_response.status_code = 200
        mock_parent_request.return_value = mock_response

        session = EnhancedSession(timeout=20)
        response = session.get("https://example.com/api")

        assert response.status_code == 200
        # Verify timeout was passed to underlying request
        call_kwargs = mock_parent_request.call_args.kwargs
        assert call_kwargs["timeout"] == 20

    def test_post_method_uses_default_timeout(self, mocker: Any) -> None:
        """Test that POST requests use default timeout.

        Verifies that POST requests also apply the default timeout.
        """
        mock_parent_request = mocker.patch("requests.Session.request")
        mock_response = MagicMock(spec=requests.Response)
        mock_parent_request.return_value = mock_response

        session = EnhancedSession(timeout=15)
        session.post("https://example.com/submit", data={"key": "value"})

        call_kwargs = mock_parent_request.call_args.kwargs
        assert call_kwargs["timeout"] == 15


class TestEnhancedSessionExplicitTimeout:
    """Test explicit timeout override behavior."""

    def test_explicit_timeout_overrides_default(self, mocker: Any) -> None:
        """Test that explicit timeout parameter overrides session default.

        Verifies that when a timeout is explicitly specified in the
        request call, it takes precedence over the session's default.
        """
        mock_parent_request = mocker.patch("requests.Session.request")
        mock_response = MagicMock(spec=requests.Response)
        mock_parent_request.return_value = mock_response

        session = EnhancedSession(timeout=30)
        session.request("POST", "https://example.com", timeout=5)

        mock_parent_request.assert_called_once_with(
            method="POST",
            url="https://example.com",
            params=None,
            data=None,
            headers=None,
            cookies=None,
            files=None,
            auth=None,
            timeout=5,  # Explicit timeout used, not default 30
            allow_redirects=True,
            proxies=None,
            hooks=None,
            stream=None,
            verify=None,
            cert=None,
            json=None,
        )

    def test_explicit_zero_timeout(self, mocker: Any) -> None:
        """Test that explicit timeout=0 is preserved.

        Verifies that a timeout of 0 (infinite wait) is not replaced
        by the default timeout.
        """
        mock_parent_request = mocker.patch("requests.Session.request")
        mock_response = MagicMock(spec=requests.Response)
        mock_parent_request.return_value = mock_response

        session = EnhancedSession(timeout=30)
        session.request("GET", "https://example.com", timeout=0)

        call_kwargs = mock_parent_request.call_args.kwargs
        assert call_kwargs["timeout"] == 0

    def test_explicit_timeout_with_get(self, mocker: Any) -> None:
        """Test explicit timeout with GET convenience method.

        Verifies that timeout parameter works with get() method.
        """
        mock_parent_request = mocker.patch("requests.Session.request")
        mock_response = MagicMock(spec=requests.Response)
        mock_parent_request.return_value = mock_response

        session = EnhancedSession(timeout=60)
        session.get("https://example.com", timeout=10)

        call_kwargs = mock_parent_request.call_args.kwargs
        assert call_kwargs["timeout"] == 10


class TestEnhancedSessionParameterPassthrough:
    """Test that all parameters are correctly forwarded to parent Session."""

    def test_all_parameters_passed_to_parent(self, mocker: Any) -> None:
        """Test that all request parameters are forwarded to parent.

        Verifies that every parameter accepted by request() is properly
        passed through to the parent Session.request() method.
        """
        mock_parent_request = mocker.patch("requests.Session.request")
        mock_response = MagicMock(spec=requests.Response)
        mock_parent_request.return_value = mock_response

        # Use a named function for hooks to avoid lambda identity issues
        def response_hook(r: Any) -> Any:
            return r

        session = EnhancedSession(timeout=30)
        session.request(
            method="POST",
            url="https://api.example.com/endpoint",
            params={"query": "test"},
            data={"field": "value"},
            headers={"Authorization": "Bearer token"},
            cookies={"session_id": "abc123"},
            files={"upload": "file.txt"},
            auth=("user", "pass"),
            timeout=45,
            allow_redirects=False,
            proxies={"http": "http://proxy:8080"},
            hooks={"response": response_hook},
            stream=True,
            verify=False,
            cert="/path/to/cert",
            json={"json_field": "json_value"},
        )

        # Verify all parameters were passed
        assert mock_parent_request.call_count == 1
        call_kwargs = mock_parent_request.call_args.kwargs

        assert call_kwargs["method"] == "POST"
        assert call_kwargs["url"] == "https://api.example.com/endpoint"
        assert call_kwargs["params"] == {"query": "test"}
        assert call_kwargs["data"] == {"field": "value"}
        assert call_kwargs["headers"] == {"Authorization": "Bearer token"}
        assert call_kwargs["cookies"] == {"session_id": "abc123"}
        assert call_kwargs["files"] == {"upload": "file.txt"}
        assert call_kwargs["auth"] == ("user", "pass")
        assert call_kwargs["timeout"] == 45
        assert call_kwargs["allow_redirects"] is False
        assert call_kwargs["proxies"] == {"http": "http://proxy:8080"}
        assert call_kwargs["hooks"] == {"response": response_hook}
        assert call_kwargs["stream"] is True
        assert call_kwargs["verify"] is False
        assert call_kwargs["cert"] == "/path/to/cert"
        assert call_kwargs["json"] == {"json_field": "json_value"}

    def test_partial_parameters_with_defaults(self, mocker: Any) -> None:
        """Test request with only some parameters specified.

        Verifies that parameters not explicitly set use their defaults
        (None or True for allow_redirects) when forwarded to parent.
        """
        mock_parent_request = mocker.patch("requests.Session.request")
        mock_response = MagicMock(spec=requests.Response)
        mock_parent_request.return_value = mock_response

        session = EnhancedSession(timeout=15)
        session.request(
            "GET",
            "https://example.com",
            headers={"User-Agent": "TestAgent"},
            verify=True,
        )

        mock_parent_request.assert_called_once_with(
            method="GET",
            url="https://example.com",
            params=None,
            data=None,
            headers={"User-Agent": "TestAgent"},
            cookies=None,
            files=None,
            auth=None,
            timeout=15,  # Default timeout
            allow_redirects=True,
            proxies=None,
            hooks=None,
            stream=None,
            verify=True,
            cert=None,
            json=None,
        )

    def test_json_parameter_forwarding(self, mocker: Any) -> None:
        """Test that json parameter is correctly forwarded.

        Verifies that the json parameter (for JSON request bodies)
        is passed through correctly.
        """
        mock_parent_request = mocker.patch("requests.Session.request")
        mock_response = MagicMock(spec=requests.Response)
        mock_parent_request.return_value = mock_response

        session = EnhancedSession(timeout=20)
        json_data = {"key": "value", "nested": {"field": 123}}
        session.request("POST", "https://api.example.com", json=json_data)

        call_kwargs = mock_parent_request.call_args.kwargs
        assert call_kwargs["json"] == json_data


class TestEnhancedSessionMethodVariations:
    """Test different HTTP methods and parameter type variations."""

    def test_different_http_methods(self, mocker: Any) -> None:
        """Test various HTTP methods (GET, POST, PUT, DELETE, PATCH).

        Verifies that all common HTTP methods work correctly.
        """
        mock_parent_request = mocker.patch("requests.Session.request")
        mock_response = MagicMock(spec=requests.Response)
        mock_parent_request.return_value = mock_response

        session = EnhancedSession(timeout=10)

        methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
        for method in methods:
            session.request(method, "https://example.com")

        assert mock_parent_request.call_count == len(methods)

    def test_method_as_bytes(self, mocker: Any) -> None:
        """Test HTTP method parameter as bytes.

        Verifies that the method parameter accepts bytes as per the
        type signature (str | bytes).
        """
        mock_parent_request = mocker.patch("requests.Session.request")
        mock_response = MagicMock(spec=requests.Response)
        mock_parent_request.return_value = mock_response

        session = EnhancedSession(timeout=15)
        session.request(b"GET", "https://example.com")

        call_args = mock_parent_request.call_args
        assert call_args.kwargs["method"] == b"GET"

    def test_url_as_bytes(self, mocker: Any) -> None:
        """Test URL parameter as bytes.

        Verifies that the url parameter accepts bytes as per the
        type signature (str | bytes).
        """
        mock_parent_request = mocker.patch("requests.Session.request")
        mock_response = MagicMock(spec=requests.Response)
        mock_parent_request.return_value = mock_response

        session = EnhancedSession(timeout=15)
        session.request("GET", b"https://example.com")

        call_args = mock_parent_request.call_args
        assert call_args.kwargs["url"] == b"https://example.com"

    def test_both_method_and_url_as_bytes(self, mocker: Any) -> None:
        """Test both method and URL as bytes.

        Verifies that both method and url can be bytes simultaneously.
        """
        mock_parent_request = mocker.patch("requests.Session.request")
        mock_response = MagicMock(spec=requests.Response)
        mock_parent_request.return_value = mock_response

        session = EnhancedSession(timeout=15)
        session.request(b"POST", b"https://api.example.com/data")

        call_args = mock_parent_request.call_args
        assert call_args.kwargs["method"] == b"POST"
        assert call_args.kwargs["url"] == b"https://api.example.com/data"

    def test_lowercase_http_method(self, mocker: Any) -> None:
        """Test HTTP method in lowercase.

        Verifies that lowercase method names work correctly.
        """
        mock_parent_request = mocker.patch("requests.Session.request")
        mock_response = MagicMock(spec=requests.Response)
        mock_parent_request.return_value = mock_response

        session = EnhancedSession(timeout=10)
        session.request("get", "https://example.com")

        call_args = mock_parent_request.call_args
        assert call_args.kwargs["method"] == "get"


class TestEnhancedSessionIntegration:
    """Test complete workflows and integration scenarios."""

    def test_multiple_requests_with_same_session(self, mocker: Any) -> None:
        """Test multiple requests using the same session instance.

        Verifies that the session maintains its default timeout across
        multiple request calls.
        """
        mock_parent_request = mocker.patch("requests.Session.request")
        mock_response = MagicMock(spec=requests.Response)
        mock_parent_request.return_value = mock_response

        session = EnhancedSession(timeout=30)

        session.request("GET", "https://example.com/1")
        session.request("POST", "https://example.com/2")
        session.request("PUT", "https://example.com/3", timeout=10)

        assert mock_parent_request.call_count == 3

        # Check first call used default timeout
        first_call = mock_parent_request.call_args_list[0]
        assert first_call.kwargs["timeout"] == 30

        # Check second call used default timeout
        second_call = mock_parent_request.call_args_list[1]
        assert second_call.kwargs["timeout"] == 30

        # Check third call used explicit timeout
        third_call = mock_parent_request.call_args_list[2]
        assert third_call.kwargs["timeout"] == 10

    def test_session_timeout_independent_across_instances(self) -> None:
        """Test that different session instances have independent timeouts.

        Verifies that creating multiple sessions with different timeouts
        doesn't affect each other.
        """
        session1 = EnhancedSession(timeout=10)
        session2 = EnhancedSession(timeout=50)
        session3 = EnhancedSession(timeout=100)

        assert session1.timeout == 10
        assert session2.timeout == 50
        assert session3.timeout == 100

        # Modify one session's timeout
        session1.timeout = 15
        assert session1.timeout == 15
        assert session2.timeout == 50  # Others unchanged
        assert session3.timeout == 100

    def test_return_value_from_parent_request(self, mocker: Any) -> None:
        """Test that the response from parent request is returned.

        Verifies that the Response object from parent Session.request()
        is correctly returned to the caller.
        """
        mock_parent_request = mocker.patch("requests.Session.request")
        mock_response = MagicMock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.text = "Success"
        mock_parent_request.return_value = mock_response

        session = EnhancedSession(timeout=20)
        response = session.request("GET", "https://example.com")

        assert response.status_code == 200
        assert response.text == "Success"
        assert response is mock_response
