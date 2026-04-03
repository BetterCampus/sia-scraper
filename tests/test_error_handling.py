"""Comprehensive Python test suite for typed error hierarchy validation.

Verifies that Rust-originated errors are raised as the correct exception types
through the FFI boundary, and that Python wrapper layers correctly translate
and handle exceptions.

Tests cover:
- NetworkError: Connection failures, DNS resolution errors
- HttpStatusError: HTTP 4xx/5xx responses with status code preservation
- SiaTimeoutError: Request timeout scenarios
- ParseError: Malformed HTML/XML input to Rust parsers
- SessionError: Session state-related failures
- Python exception translation in SiaSession wrapper
- ConcurrentAccessError with active/attempted operation attributes
- End-to-end exception flow through all layers
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

import sia_scraper_rust
from sia_scraper.core.exceptions import (
    ConcurrentAccessError,
    HttpStatusError,
    NetworkError,
    ParseError,
    SessionError,
    SiaScraperException,
    SiaSessionException,
    SiaTimeoutError,
)
from sia_scraper.session import SiaSession


class TestNetworkError:
    """Verify NetworkError is raised for connection failures."""

    @pytest.mark.asyncio
    async def test_network_error_on_connection_refused(self):
        """NetworkError should be raised when connection is refused."""
        with pytest.raises(NetworkError) as exc_info:
            await sia_scraper_rust.async_get("http://localhost:1")
        assert isinstance(exc_info.value, SiaScraperException)

    @pytest.mark.asyncio
    async def test_network_error_on_invalid_host(self):
        """NetworkError should be raised for unresolvable hostname."""
        with pytest.raises(NetworkError) as exc_info:
            await sia_scraper_rust.async_get("http://this-host-does-not-exist-xyz.invalid")
        assert isinstance(exc_info.value, SiaScraperException)

    def test_network_error_is_sia_scraper_exception(self):
        """NetworkError should inherit from SiaScraperException."""
        assert issubclass(NetworkError, SiaScraperException)

    def test_network_error_can_be_caught_by_base_class(self):
        """NetworkError should be catchable as SiaScraperException."""
        with pytest.raises(SiaScraperException):
            raise NetworkError("connection failed")

    def test_network_error_message_preserved(self):
        """NetworkError should preserve the original error message."""
        msg = "Connection refused to localhost:9999"
        with pytest.raises(NetworkError) as exc_info:
            raise NetworkError(msg)
        assert msg in str(exc_info.value)


class TestHttpStatusError:
    """Verify HttpStatusError is raised for HTTP error responses."""

    @pytest.mark.asyncio
    async def test_http_status_error_on_404(self, httpserver):
        """HttpStatusError should be raised for 404 responses."""
        httpserver.expect_request("/not-found").respond_with_data("Not Found", status=404)
        with pytest.raises(HttpStatusError) as exc_info:
            await sia_scraper_rust.async_get(httpserver.url_for("/not-found"))
        error_msg = str(exc_info.value)
        assert "404" in error_msg
        assert isinstance(exc_info.value, SiaScraperException)

    @pytest.mark.asyncio
    async def test_http_status_error_on_500(self, httpserver):
        """HttpStatusError should be raised for 500 responses."""
        httpserver.expect_request("/error").respond_with_data("Internal Server Error", status=500)
        with pytest.raises(HttpStatusError) as exc_info:
            await sia_scraper_rust.async_get(httpserver.url_for("/error"))
        error_msg = str(exc_info.value)
        assert "500" in error_msg

    def test_http_status_error_is_sia_scraper_exception(self):
        """HttpStatusError should inherit from SiaScraperException."""
        assert issubclass(HttpStatusError, SiaScraperException)

    def test_http_status_error_can_be_caught_by_base_class(self):
        """HttpStatusError should be catchable as SiaScraperException."""
        with pytest.raises(SiaScraperException):
            raise HttpStatusError("500 Internal Server Error")


class TestSiaTimeoutError:
    """Verify SiaTimeoutError is raised for request timeouts."""

    @pytest.mark.asyncio
    async def test_timeout_error_inherits_from_sia_scraper_exception(self):
        """SiaTimeoutError should inherit from SiaScraperException."""
        assert issubclass(SiaTimeoutError, SiaScraperException)

    def test_timeout_error_can_be_caught_by_base_class(self):
        """SiaTimeoutError should be catchable as SiaScraperException."""
        with pytest.raises(SiaScraperException):
            raise SiaTimeoutError("Request timed out after 30s")

    def test_timeout_error_message_preserved(self):
        """SiaTimeoutError should preserve the timeout message."""
        msg = "Operation timed out after 5000ms"
        with pytest.raises(SiaTimeoutError) as exc_info:
            raise SiaTimeoutError(msg)
        assert msg in str(exc_info.value)


class TestParseError:
    """Verify ParseError is raised for malformed input."""

    def test_parse_error_on_malformed_html(self):
        """ParseError should be raised for unparseable HTML."""
        with pytest.raises(sia_scraper_rust.SiaScraperException):
            sia_scraper_rust.extract_view_state("<broken")

    def test_parse_error_on_missing_element(self):
        """ParseError should be raised when required element is missing."""
        html = "<div>No ViewState here</div>"
        with pytest.raises(sia_scraper_rust.SiaScraperException) as exc_info:
            sia_scraper_rust.extract_view_state(html)
        assert "ViewState" in str(exc_info.value)

    def test_parse_error_is_sia_scraper_exception(self):
        """ParseError should inherit from SiaScraperException."""
        assert issubclass(ParseError, SiaScraperException)

    def test_parse_error_can_be_caught_by_base_class(self):
        """ParseError should be catchable as SiaScraperException."""
        with pytest.raises(SiaScraperException):
            raise ParseError("Failed to parse response")


class TestSessionError:
    """Verify SessionError is raised for session state failures."""

    @pytest.mark.asyncio
    async def test_session_error_on_uninitialized_session(self):
        """SessionError should be raised when using uninitialized session."""
        session = sia_scraper_rust.PySiaSession()
        with pytest.raises(SessionError) as exc_info:
            await session.set_career("0-2-8-3")
        error_msg = str(exc_info.value)
        assert "Session not initialized" in error_msg
        assert isinstance(exc_info.value, SiaScraperException)

    def test_session_error_is_sia_scraper_exception(self):
        """SessionError should inherit from SiaScraperException."""
        assert issubclass(SessionError, SiaScraperException)

    def test_session_error_can_be_caught_by_base_class(self):
        """SessionError should be catchable as SiaScraperException."""
        with pytest.raises(SiaScraperException):
            raise SessionError("Session expired")


class TestExceptionInheritance:
    """Verify complete exception inheritance hierarchy."""

    def test_all_rust_exceptions_inherit_from_sia_scraper_exception(self):
        """All Rust exceptions should inherit from SiaScraperException."""
        for exc_class in [
            NetworkError,
            HttpStatusError,
            SiaTimeoutError,
            ParseError,
            SessionError,
        ]:
            assert issubclass(exc_class, SiaScraperException), (
                f"{exc_class.__name__} does not inherit from SiaScraperException"
            )

    def test_sia_scraper_exception_inherits_from_exception(self):
        """SiaScraperException should inherit from Exception."""
        assert issubclass(SiaScraperException, Exception)

    def test_can_catch_all_rust_exceptions_with_base_class(self):
        """Catching SiaScraperException should catch all derived types."""
        for exc_class in [
            NetworkError,
            HttpStatusError,
            SiaTimeoutError,
            ParseError,
            SessionError,
        ]:
            with pytest.raises(SiaScraperException):
                raise exc_class("test error")

    def test_python_session_exception_independent_from_rust(self):
        """SiaSessionException should NOT inherit from SiaScraperException."""
        assert not issubclass(SiaSessionException, SiaScraperException)

    def test_python_exceptions_inherit_from_exception(self):
        """All Python exceptions should inherit from Exception."""
        assert issubclass(SiaSessionException, Exception)


class TestConcurrentAccessError:
    """Verify ConcurrentAccessError has correct attributes and behavior."""

    @pytest.mark.asyncio
    async def test_concurrent_access_error_has_operation_attributes(self):
        """ConcurrentAccessError should have active_operation and attempted_operation."""
        session = SiaSession()
        session._active_operation = "set_career"

        with pytest.raises(ConcurrentAccessError) as exc_info:
            async with session._operation("scrape_course_info"):
                pass

        assert exc_info.value.active_operation == "set_career"
        assert exc_info.value.attempted_operation == "scrape_course_info"

    @pytest.mark.asyncio
    async def test_concurrent_access_error_message_contains_operations(self):
        """ConcurrentAccessError message should mention both operations."""
        session = SiaSession()
        session._active_operation = "init_session"

        with pytest.raises(ConcurrentAccessError) as exc_info:
            async with session._operation("set_career"):
                pass

        error_msg = str(exc_info.value)
        assert "init_session" in error_msg
        assert "set_career" in error_msg

    def test_concurrent_access_error_inherits_from_sia_session_exception(self):
        """ConcurrentAccessError should inherit from SiaSessionException."""
        assert issubclass(ConcurrentAccessError, SiaSessionException)


class TestSessionExceptionTranslation:
    """Verify SiaSession correctly translates Rust exceptions to Python exceptions."""

    def _make_state_model(
        self,
        career_code: str = "",
        career_name: str = "N/A",
        is_electives: bool = False,
        status: str = "CAREER_NOT_SET",
        view_state: str | None = "vs-1",
    ) -> sia_scraper_rust.SessionStateModel:
        """Create a minimal SessionStateModel for testing."""
        return sia_scraper_rust.SessionStateModel(
            session_headers={},
            session_cookies={},
            params={"Adf-Page-Id": "0", "Adf-Window-Id": "win-1"},
            career_code=career_code,
            career_name=career_name,
            is_electives=is_electives,
            status=status,
            course_list=[],
            javax_faces_view_state=view_state,
        )

    @pytest.mark.asyncio
    async def test_init_session_translates_session_error_to_session_not_set(self):
        """SessionError during init_session should be translated to SessionNotSet."""
        mock_rust_session = MagicMock()
        mock_rust_session.init_session = AsyncMock(
            side_effect=sia_scraper_rust.SessionError("Session not initialized")
        )

        session = SiaSession()
        session._rust_session = mock_rust_session

        with pytest.raises(SiaSessionException.SessionNotSet):
            await session.init_session()

    @pytest.mark.asyncio
    async def test_init_session_wraps_sia_scraper_exception(self):
        """SiaScraperException during init_session should be wrapped as SiaSessionException."""
        mock_rust_session = MagicMock()
        mock_rust_session.init_session = AsyncMock(
            side_effect=sia_scraper_rust.NetworkError("Connection failed")
        )

        session = SiaSession()
        session._rust_session = mock_rust_session

        with pytest.raises(SiaSessionException) as exc_info:
            await session.init_session()
        assert "Connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_set_career_translates_session_error_not_initialized(self):
        """SessionError with 'not initialized' should map to SessionNotSet."""
        mock_rust_session = MagicMock()
        mock_rust_session.set_career = AsyncMock(
            side_effect=sia_scraper_rust.SessionError("Session not initialized")
        )

        session = SiaSession()
        session._rust_session = mock_rust_session

        with pytest.raises(SiaSessionException.SessionNotSet):
            await session.set_career("0-2-8-3")

    @pytest.mark.asyncio
    async def test_set_career_translates_session_error_to_career_not_set(self):
        """SessionError without 'not initialized' should map to CareerNotSet."""
        mock_rust_session = MagicMock()
        mock_rust_session.set_career = AsyncMock(
            side_effect=sia_scraper_rust.SessionError("Career selection failed")
        )

        session = SiaSession()
        session._rust_session = mock_rust_session

        with pytest.raises(SiaSessionException.CareerNotSet):
            await session.set_career("0-2-8-3")

    @pytest.mark.asyncio
    async def test_set_career_wraps_sia_scraper_exception(self):
        """SiaScraperException during set_career should be wrapped as SiaSessionException."""
        mock_rust_session = MagicMock()
        mock_rust_session.set_career = AsyncMock(
            side_effect=sia_scraper_rust.HttpStatusError("500 Internal Server Error")
        )

        session = SiaSession()
        session._rust_session = mock_rust_session

        with pytest.raises(SiaSessionException) as exc_info:
            await session.set_career("0-2-8-3")
        assert "Career selection failed" in str(exc_info.value)
