"""Tests for Oracle ADF ViewState extraction utilities."""

from types import SimpleNamespace

import pytest

from sia_scraper.core.adf_state import extract_view_state, extract_view_state_from_response
from sia_scraper.core.exceptions import SiaSessionException


@pytest.mark.unit
class TestExtractViewState:
    """Test direct ViewState extraction from HTML content."""

    def test_extract_view_state_from_bytes(self, sia_initial_html: bytes):
        token = extract_view_state(sia_initial_html)
        assert token != ""
        assert "SANITIZED_VIEWSTATE_TOKEN_12345" in token

    def test_extract_view_state_from_string(self, sia_initial_html: bytes):
        html_text = sia_initial_html.decode("utf-8", errors="ignore")
        token = extract_view_state(html_text)
        assert token != ""
        assert "SANITIZED_VIEWSTATE_TOKEN_12345" in token

    def test_extract_view_state_missing_raises(self):
        with pytest.raises(SiaSessionException.SessionNotSet):
            extract_view_state("<html><body>No view state here</body></html>")


@pytest.mark.unit
class TestExtractViewStateFromResponse:
    """Test ViewState extraction from response-like objects."""

    def test_extract_from_response_content_bytes(self, sia_initial_html: bytes):
        response = SimpleNamespace(content=sia_initial_html, text="")
        token = extract_view_state_from_response(response)
        assert token != ""

    def test_extract_from_response_text(self, sia_initial_html: bytes):
        response = SimpleNamespace(
            content=b"", text=sia_initial_html.decode("utf-8", errors="ignore")
        )
        token = extract_view_state_from_response(response)
        assert token != ""

    def test_extract_raises_when_response_has_no_content(self):
        response = SimpleNamespace(content=b"", text="")
        with pytest.raises(SiaSessionException.SessionNotSet):
            extract_view_state_from_response(response)

    def test_extract_raises_for_non_string_or_bytes_content(self):
        response = SimpleNamespace(content=123, text="")
        with pytest.raises(SiaSessionException.SessionNotSet):
            extract_view_state_from_response(response)

    def test_extract_raises_when_viewstate_missing(self):
        response = SimpleNamespace(content=b"<html><body>missing</body></html>", text="")
        with pytest.raises(SiaSessionException.SessionNotSet):
            extract_view_state_from_response(response)
