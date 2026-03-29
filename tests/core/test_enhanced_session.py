"""Comprehensive test suite for EnhancedSession module.

This module contains pytest-based unit tests for the EnhancedSession class,
which extends requests.Session to automatically apply default timeouts to
all HTTP requests. The tests cover initialization, timeout behavior, and
parameter forwarding to ensure 100% code coverage.
"""

from typing import Any
from unittest.mock import MagicMock

import requests

from sia_scraper.core import EnhancedSession


class TestEnhancedSessionInitialization:
    """Test initialization and basic setup of EnhancedSession."""

    def test_init_sets_timeout_attribute(self) -> None:
        """Test that __init__ properly sets the timeout attribute."""
        session = EnhancedSession(timeout=30)
        assert session.timeout == 30

    def test_init_with_different_timeout_values(self) -> None:
        """Test initialization with various timeout values."""
        session_10 = EnhancedSession(timeout=10)
        session_60 = EnhancedSession(timeout=60)
        session_1 = EnhancedSession(timeout=1)

        assert session_10.timeout == 10
        assert session_60.timeout == 60
        assert session_1.timeout == 1

    def test_inherits_from_requests_session(self) -> None:
        """Test that EnhancedSession inherits from requests.Session."""
        session = EnhancedSession(timeout=15)
        assert isinstance(session, requests.Session)
        assert hasattr(session, "get")
        assert hasattr(session, "post")
        assert hasattr(session, "headers")
        assert hasattr(session, "cookies")


class TestEnhancedSessionDefaultTimeout:
    """Test default timeout application when not explicitly specified."""

    def test_request_uses_default_timeout_when_none(self, mocker: Any) -> None:
        """Test that default timeout is applied when timeout=None."""
        mock_parent_request = mocker.patch("requests.Session.request")
        mock_response = MagicMock(spec=requests.Response)
        mock_parent_request.return_value = mock_response

        session = EnhancedSession(timeout=25)
        session.request("GET", "https://example.com")

        mock_parent_request.assert_called_once()
        call_args = mock_parent_request.call_args
        assert call_args[0][0] == "GET"
        assert call_args[0][1] == "https://example.com"
        assert call_args[1]["timeout"] == 25

    def test_get_method_uses_default_timeout(self, mocker: Any) -> None:
        """Test that GET requests use default timeout."""
        mock_parent_request = mocker.patch("requests.Session.request")
        mock_response = MagicMock(spec=requests.Response)
        mock_response.status_code = 200
        mock_parent_request.return_value = mock_response

        session = EnhancedSession(timeout=20)
        response = session.get("https://example.com/api")

        assert response.status_code == 200
        call_kwargs = mock_parent_request.call_args.kwargs
        assert call_kwargs["timeout"] == 20

    def test_post_method_uses_default_timeout(self, mocker: Any) -> None:
        """Test that POST requests use default timeout."""
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
        """Test that explicit timeout parameter overrides session default."""
        mock_parent_request = mocker.patch("requests.Session.request")
        mock_response = MagicMock(spec=requests.Response)
        mock_parent_request.return_value = mock_response

        session = EnhancedSession(timeout=30)
        session.request("POST", "https://example.com", timeout=5)

        mock_parent_request.assert_called_once()
        call_args = mock_parent_request.call_args
        assert call_args[0][0] == "POST"
        assert call_args[1]["timeout"] == 5

    def test_explicit_zero_timeout(self, mocker: Any) -> None:
        """Test that explicit timeout=0 is preserved."""
        mock_parent_request = mocker.patch("requests.Session.request")
        mock_response = MagicMock(spec=requests.Response)
        mock_parent_request.return_value = mock_response

        session = EnhancedSession(timeout=30)
        session.request("GET", "https://example.com", timeout=0)

        call_kwargs = mock_parent_request.call_args.kwargs
        assert call_kwargs["timeout"] == 0

    def test_explicit_timeout_with_get(self, mocker: Any) -> None:
        """Test explicit timeout with GET convenience method."""
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
        """Test that all request parameters are forwarded to parent."""
        mock_parent_request = mocker.patch("requests.Session.request")
        mock_response = MagicMock(spec=requests.Response)
        mock_parent_request.return_value = mock_response

        session = EnhancedSession(timeout=30)
        session.request(
            "POST",
            "https://api.example.com/endpoint",
            params={"query": "test"},
            data={"field": "value"},
            headers={"Authorization": "Bearer token"},
            timeout=45,
            allow_redirects=False,
        )

        mock_parent_request.assert_called_once()
        call_args = mock_parent_request.call_args
        call_kwargs = call_args[1]

        assert call_args[0][0] == "POST"
        assert call_args[0][1] == "https://api.example.com/endpoint"
        assert call_kwargs["params"] == {"query": "test"}
        assert call_kwargs["data"] == {"field": "value"}
        assert call_kwargs["headers"] == {"Authorization": "Bearer token"}
        assert call_kwargs["timeout"] == 45
        assert call_kwargs["allow_redirects"] is False

    def test_kwargs_passed_through(self, mocker: Any) -> None:
        """Test that **kwargs are passed through to parent."""
        mock_parent_request = mocker.patch("requests.Session.request")
        mock_response = MagicMock(spec=requests.Response)
        mock_parent_request.return_value = mock_response

        session = EnhancedSession(timeout=20)
        session.request(
            "POST",
            "https://api.example.com",
            json={"key": "value"},
            cookies={"session": "abc"},
        )

        call_kwargs = mock_parent_request.call_args.kwargs
        assert call_kwargs["json"] == {"key": "value"}
        assert call_kwargs["cookies"] == {"session": "abc"}

    def test_partial_parameters_with_defaults(self, mocker: Any) -> None:
        """Test request with only some parameters specified."""
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

        mock_parent_request.assert_called_once()
        call_args = mock_parent_request.call_args
        call_kwargs = call_args[1]

        assert call_args[0][0] == "GET"
        assert call_kwargs["headers"] == {"User-Agent": "TestAgent"}
        assert call_kwargs["verify"] is True
        assert call_kwargs["timeout"] == 15


class TestEnhancedSessionMethodVariations:
    """Test different HTTP methods and parameter type variations."""

    def test_different_http_methods(self, mocker: Any) -> None:
        """Test various HTTP methods (GET, POST, PUT, DELETE, PATCH)."""
        mock_parent_request = mocker.patch("requests.Session.request")
        mock_response = MagicMock(spec=requests.Response)
        mock_parent_request.return_value = mock_response

        session = EnhancedSession(timeout=10)

        methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
        for method in methods:
            session.request(method, "https://example.com")

        assert mock_parent_request.call_count == len(methods)

    def test_method_as_bytes(self, mocker: Any) -> None:
        """Test HTTP method parameter as bytes."""
        mock_parent_request = mocker.patch("requests.Session.request")
        mock_response = MagicMock(spec=requests.Response)
        mock_parent_request.return_value = mock_response

        session = EnhancedSession(timeout=15)
        session.request(b"GET", "https://example.com")

        call_args = mock_parent_request.call_args
        assert call_args[0][0] == b"GET"

    def test_url_as_bytes(self, mocker: Any) -> None:
        """Test URL parameter as bytes."""
        mock_parent_request = mocker.patch("requests.Session.request")
        mock_response = MagicMock(spec=requests.Response)
        mock_parent_request.return_value = mock_response

        session = EnhancedSession(timeout=15)
        session.request("GET", b"https://example.com")

        call_args = mock_parent_request.call_args
        assert call_args[0][1] == b"https://example.com"

    def test_both_method_and_url_as_bytes(self, mocker: Any) -> None:
        """Test both method and URL as bytes."""
        mock_parent_request = mocker.patch("requests.Session.request")
        mock_response = MagicMock(spec=requests.Response)
        mock_parent_request.return_value = mock_response

        session = EnhancedSession(timeout=15)
        session.request(b"POST", b"https://api.example.com/data")

        call_args = mock_parent_request.call_args
        assert call_args[0][0] == b"POST"
        assert call_args[0][1] == b"https://api.example.com/data"

    def test_lowercase_http_method(self, mocker: Any) -> None:
        """Test HTTP method in lowercase."""
        mock_parent_request = mocker.patch("requests.Session.request")
        mock_response = MagicMock(spec=requests.Response)
        mock_parent_request.return_value = mock_response

        session = EnhancedSession(timeout=10)
        session.request("get", "https://example.com")

        call_args = mock_parent_request.call_args
        assert call_args[0][0] == "get"


class TestEnhancedSessionIntegration:
    """Test complete workflows and integration scenarios."""

    def test_multiple_requests_with_same_session(self, mocker: Any) -> None:
        """Test multiple requests using the same session instance."""
        mock_parent_request = mocker.patch("requests.Session.request")
        mock_response = MagicMock(spec=requests.Response)
        mock_parent_request.return_value = mock_response

        session = EnhancedSession(timeout=30)

        session.request("GET", "https://example.com/1")
        session.request("POST", "https://example.com/2")
        session.request("PUT", "https://example.com/3", timeout=10)

        assert mock_parent_request.call_count == 3

        first_call = mock_parent_request.call_args_list[0]
        assert first_call.kwargs["timeout"] == 30

        second_call = mock_parent_request.call_args_list[1]
        assert second_call.kwargs["timeout"] == 30

        third_call = mock_parent_request.call_args_list[2]
        assert third_call.kwargs["timeout"] == 10

    def test_session_timeout_independent_across_instances(self) -> None:
        """Test that different session instances have independent timeouts."""
        session1 = EnhancedSession(timeout=10)
        session2 = EnhancedSession(timeout=50)
        session3 = EnhancedSession(timeout=100)

        assert session1.timeout == 10
        assert session2.timeout == 50
        assert session3.timeout == 100

        session1.timeout = 15
        assert session1.timeout == 15
        assert session2.timeout == 50
        assert session3.timeout == 100

    def test_return_value_from_parent_request(self, mocker: Any) -> None:
        """Test that the response from parent request is returned."""
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
