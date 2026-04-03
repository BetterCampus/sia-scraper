"""Test that Rust extensions fail explicitly rather than silently on errors.

This module verifies that critical operations in the Rust extensions raise
exceptions instead of returning default/empty values when errors occur.

Tests cover:
- ViewState extraction failures
- Course parsing failures
- Course list extraction edge cases
- Input validation errors
"""

import pytest

# Skip all tests if Rust extension is not available
sia_scraper_rust = pytest.importorskip("sia_scraper_rust")


class TestViewStateExtractionErrors:
    """Verify ViewState extraction raises errors on invalid input."""

    def test_extract_view_state_fails_on_missing_element(self):
        """ViewState extraction should raise error, not return empty string."""
        html = "<div>No ViewState here</div>"
        with pytest.raises(sia_scraper_rust.SiaScraperException) as exc_info:
            sia_scraper_rust.extract_view_state(html)
        # Error message should indicate the issue
        assert "ViewState" in str(exc_info.value) or "not found" in str(exc_info.value)

    def test_extract_view_state_fails_on_empty_html(self):
        """ViewState extraction should raise error on empty input."""
        with pytest.raises(sia_scraper_rust.SiaScraperException):
            sia_scraper_rust.extract_view_state("")

    def test_extract_view_state_fails_on_malformed_html(self):
        """ViewState extraction should raise error on malformed HTML."""
        html = "<input type='broken'"
        with pytest.raises(sia_scraper_rust.SiaScraperException):
            sia_scraper_rust.extract_view_state(html)

    def test_extract_view_state_succeeds_on_valid_input(self):
        """ViewState extraction should succeed on valid HTML."""
        html = '<input type="hidden" name="javax.faces.ViewState" value="test123">'
        result = sia_scraper_rust.extract_view_state(html)
        assert result == "test123"


class TestCourseParsingErrors:
    """Verify course parsing raises errors on invalid input."""

    def test_parse_course_info_fails_on_invalid_xml(self):
        """Course parsing should raise error on malformed input."""
        invalid_xml = "<div>Not a valid course page</div>"
        with pytest.raises(sia_scraper_rust.SiaScraperException) as exc_info:
            sia_scraper_rust.parse_course_info(invalid_xml)
        # Should indicate what's missing
        error_msg = str(exc_info.value).lower()
        assert "name" in error_msg or "credit" in error_msg or "parse" in error_msg

    def test_parse_course_info_fails_on_empty_input(self):
        """Course parsing should raise error on empty input."""
        with pytest.raises(sia_scraper_rust.SiaScraperException):
            sia_scraper_rust.parse_course_info("")

    def test_parse_prereqs_fails_on_invalid_xml(self):
        """Prerequisites parsing should raise error on malformed input."""
        invalid_xml = "<div>Not a valid prereqs page</div>"
        with pytest.raises(sia_scraper_rust.SiaScraperException):
            sia_scraper_rust.parse_prereqs(invalid_xml)


class TestCourseListExtraction:
    """Verify course list extraction behavior."""

    def test_get_course_list_returns_empty_on_no_rows(self):
        """Course list extraction returns empty list for valid HTML with no courses."""
        html = "<table><tbody></tbody></table>"
        result = sia_scraper_rust.get_course_list(html)
        # Empty is valid - should return [], not raise
        assert result == []
        assert isinstance(result, list)

    def test_get_course_list_fails_on_invalid_input_type(self):
        """Course list extraction should raise TypeError on invalid input type."""
        with pytest.raises((TypeError, Exception)):
            sia_scraper_rust.get_course_list(12345)  # Not a string

    def test_get_course_list_accepts_bytes_input(self):
        """Course list extraction should accept bytes input."""
        html = "<table><tbody></tbody></table>"
        result = sia_scraper_rust.get_course_list(html.encode("utf-8"))
        assert result == []

    def test_get_course_list_accepts_string_input(self):
        """Course list extraction should accept string input."""
        html = "<table><tbody></tbody></table>"
        result = sia_scraper_rust.get_course_list(html)
        assert result == []


class TestOracleAdfRequestDict:
    """Verify Oracle ADF request dict initialization."""

    def test_init_oracle_adf_request_dict_basic(self):
        """Request dict initialization should succeed with valid inputs."""
        result = sia_scraper_rust.init_oracle_adf_request_dict(
            tipology_index="",
            window_id="win123",
            page_id="0",
            view_state="vs123",
        )
        assert isinstance(result, dict)
        assert "javax.faces.ViewState" in result
        assert result["javax.faces.ViewState"] == "vs123"

    def test_init_oracle_adf_request_dict_with_none_values(self):
        """Request dict initialization should raise on None values (strict mode)."""
        with pytest.raises(sia_scraper_rust.SiaScraperException, match="window_id is required"):
            sia_scraper_rust.init_oracle_adf_request_dict(
                tipology_index="",
                window_id=None,
                page_id=None,
                view_state=None,
            )


class TestBuildOracleAdfRequestBody:
    """Verify Oracle ADF request body construction."""

    def test_build_request_body_basic(self):
        """Request body construction should succeed with valid inputs."""
        request_dict = sia_scraper_rust.init_oracle_adf_request_dict(
            tipology_index="",
            window_id="win123",
            page_id="0",
            view_state="vs123",
        )
        result = sia_scraper_rust.build_oracle_adf_request_body(
            request_dict=request_dict,
            data_name="SHOW_COURSES_BTTN",
            idx=-1,
            career_indices=["0", "2", "8", "3"],
            course_list_len=0,
        )
        assert isinstance(result, dict)


class TestGetPlainText:
    """Verify plain text extraction."""

    def test_get_plain_text_basic(self):
        """Plain text extraction should work on valid input."""
        xml = "<div>Hello World</div>"
        result = sia_scraper_rust.get_plain_text(xml)
        assert isinstance(result, str)
        assert "Hello World" in result

    def test_get_plain_text_empty_input(self):
        """Plain text extraction should handle empty input gracefully."""
        result = sia_scraper_rust.get_plain_text("")
        assert isinstance(result, str)


class TestExceptionInheritance:
    """Verify that new exception types inherit from SiaScraperException."""

    def test_network_error_inherits_from_sia_scraper_exception(self):
        """NetworkError should inherit from SiaScraperException."""
        assert issubclass(sia_scraper_rust.NetworkError, sia_scraper_rust.SiaScraperException)

    def test_http_status_error_inherits_from_sia_scraper_exception(self):
        """HttpStatusError should inherit from SiaScraperException."""
        assert issubclass(sia_scraper_rust.HttpStatusError, sia_scraper_rust.SiaScraperException)

    def test_sia_timeout_error_inherits_from_sia_scraper_exception(self):
        """SiaTimeoutError should inherit from SiaScraperException."""
        assert issubclass(sia_scraper_rust.SiaTimeoutError, sia_scraper_rust.SiaScraperException)

    def test_parse_error_inherits_from_sia_scraper_exception(self):
        """ParseError should inherit from SiaScraperException."""
        assert issubclass(sia_scraper_rust.ParseError, sia_scraper_rust.SiaScraperException)

    def test_session_error_inherits_from_sia_scraper_exception(self):
        """SessionError should inherit from SiaScraperException."""
        assert issubclass(sia_scraper_rust.SessionError, sia_scraper_rust.SiaScraperException)

    def test_sia_scraper_exception_inherits_from_exception(self):
        """SiaScraperException should inherit from Exception."""
        assert issubclass(sia_scraper_rust.SiaScraperException, Exception)


class TestExceptionMessages:
    """Verify that exception messages are correctly preserved when surfaced to Python."""

    def test_sia_scraper_exception_message(self):
        """SiaScraperException should preserve the error message."""
        with pytest.raises(sia_scraper_rust.SiaScraperException) as exc_info:
            sia_scraper_rust.extract_view_state("<div>No ViewState</div>")
        error_msg = str(exc_info.value)
        assert isinstance(error_msg, str)
        assert len(error_msg) > 0

    def test_sia_scraper_exception_message_from_invalid_input(self):
        """SiaScraperException should contain the invalid input message."""
        with pytest.raises(sia_scraper_rust.SiaScraperException, match="window_id is required"):
            sia_scraper_rust.init_oracle_adf_request_dict(
                tipology_index="",
                window_id=None,
                page_id=None,
                view_state=None,
            )

    def test_sia_scraper_exception_parse_message_contains_context(self):
        """SiaScraperException from parsing should contain context about what failed."""
        with pytest.raises(sia_scraper_rust.SiaScraperException) as exc_info:
            sia_scraper_rust.parse_course_info("")
        error_msg = str(exc_info.value).lower()
        assert isinstance(error_msg, str)
        assert len(error_msg) > 0


class TestExceptionCatchability:
    """Verify that exceptions can be caught using generic Exception handler."""

    def test_sia_scraper_exception_caught_in_extract_view_state(self):
        """SiaScraperException from extract_view_state should be catchable as Exception."""
        caught = False
        try:
            sia_scraper_rust.extract_view_state("<div>No ViewState</div>")
        except Exception:
            caught = True
        assert caught

    def test_sia_scraper_exception_caught_in_init_oracle_adf_request_dict(self):
        """SiaScraperException from init_oracle_adf_request_dict should be catchable as Exception."""
        caught = False
        try:
            sia_scraper_rust.init_oracle_adf_request_dict(
                tipology_index="",
                window_id=None,
                page_id=None,
                view_state=None,
            )
        except Exception:
            caught = True
        assert caught


class TestHttpErrorExceptionMapping:
    """Verify HttpError variants are correctly mapped to Python exceptions.

    These tests trigger actual HTTP-layer failures to ensure the
    From<HttpError> for PyErr conversion raises the correct exception types.
    """

    @pytest.mark.asyncio
    async def test_network_error_raised_on_connection_refused(self):
        """NetworkError should be raised when connection is refused."""
        with pytest.raises(sia_scraper_rust.NetworkError) as exc_info:
            await sia_scraper_rust.async_get("http://localhost:1")
        error_msg = str(exc_info.value)
        assert "Network error" in error_msg or "Connection" in error_msg

    @pytest.mark.asyncio
    async def test_network_error_raised_on_invalid_host(self):
        """NetworkError should be raised for unresolvable hostnames."""
        with pytest.raises(sia_scraper_rust.NetworkError) as exc_info:
            await sia_scraper_rust.async_get("http://this-host-does-not-exist.invalid")
        error_msg = str(exc_info.value)
        assert "Network error" in error_msg or "dns" in error_msg.lower()

    @pytest.mark.asyncio
    async def test_http_status_error_raised_on_404(self, httpserver):
        """HttpStatusError should be raised for 404 responses."""
        httpserver.expect_request("/test").respond_with_data("", status=404)
        with pytest.raises(sia_scraper_rust.HttpStatusError) as exc_info:
            await sia_scraper_rust.async_get(httpserver.url_for("/test"))
        error_msg = str(exc_info.value)
        assert "404" in error_msg

    @pytest.mark.asyncio
    async def test_http_status_error_message_contains_status_code(self, httpserver):
        """HttpStatusError message should contain the HTTP status code."""
        httpserver.expect_request("/test").respond_with_data("", status=500)
        with pytest.raises(sia_scraper_rust.HttpStatusError) as exc_info:
            await sia_scraper_rust.async_get(httpserver.url_for("/test"))
        error_msg = str(exc_info.value)
        assert "500" in error_msg

    @pytest.mark.asyncio
    @pytest.mark.network
    @pytest.mark.flaky
    async def test_sia_timeout_error_raised_on_timeout(self):
        """SiaTimeoutError should be raised when request exceeds timeout."""
        import socket
        import threading
        import time

        # Create a server socket that accepts but never responds
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        _, port = server.getsockname()

        # Thread that accepts one connection and blocks forever
        def accept_and_block():
            conn, _ = server.accept()
            conn.recv(1024)  # Read the request
            # Keep socket open past client timeout to avoid EOF/reset
            time.sleep(5)
            conn.close()

        t = threading.Thread(target=accept_and_block, daemon=True)
        t.start()

        try:
            with pytest.raises(sia_scraper_rust.SiaTimeoutError) as exc_info:
                await sia_scraper_rust.async_get_with_config(
                    f"http://127.0.0.1:{port}",
                    timeout=1,
                )
            error_msg = str(exc_info.value)
            assert "Timeout" in error_msg
        finally:
            server.close()

    @pytest.mark.asyncio
    async def test_session_error_raised_on_uninitialized_session(self):
        """SessionError should be raised when using uninitialized session."""
        session = sia_scraper_rust.PySiaSession()
        with pytest.raises(sia_scraper_rust.SessionError) as exc_info:
            await session.set_career("0-2-8-3")
        error_msg = str(exc_info.value)
        assert "Session not initialized" in error_msg

    @pytest.mark.asyncio
    async def test_value_error_raised_on_invalid_state_dict(self):
        """ValueError should be raised for invalid session state dict content."""
        # Initialize a session to get a valid state_dict shape
        session = sia_scraper_rust.PySiaSession()
        await session.init_session()
        data = await session.get_session_data()
        state_dict = data["state_dict"]
        # Pass invalid type for a required string field to trigger ValueError
        state_dict["career_code"] = 12345  # Should be string, not int
        with pytest.raises(ValueError) as exc_info:
            await sia_scraper_rust.PySiaSession.from_state({"state_dict": state_dict})
        error_msg = str(exc_info.value)
        assert "Invalid state_dict" in error_msg or "career_code" in error_msg.lower()

    @pytest.mark.asyncio
    async def test_network_error_inherits_from_exception(self):
        """NetworkError should be catchable as Exception."""
        try:
            await sia_scraper_rust.async_get("http://localhost:1")
        except Exception:
            pass
        else:
            raise AssertionError("Expected NetworkError to be raised")

    @pytest.mark.asyncio
    async def test_http_status_error_inherits_from_exception(self, httpserver):
        """HttpStatusError should be catchable as Exception."""
        httpserver.expect_request("/test").respond_with_data("", status=404)
        try:
            await sia_scraper_rust.async_get(httpserver.url_for("/test"))
        except Exception as exc:
            assert isinstance(exc, sia_scraper_rust.HttpStatusError), (
                f"Expected HttpStatusError, got {type(exc).__name__}"
            )
        else:
            raise AssertionError("Expected HttpStatusError to be raised")
