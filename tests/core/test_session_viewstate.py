"""Focused tests for ViewState extraction/sync and set_career response edge cases."""

from unittest.mock import MagicMock, patch

import pytest

from sia_scraper.constants import SiaSessionStatus
from sia_scraper.session import SiaSession, SiaSessionException


def _session_data(status_name: str = "CAREER_NOT_SET") -> dict[str, object]:
    return {
        "session_headers": {"User-Agent": "pytest"},
        "session_cookies": {"JSESSIONID": "abc123"},
        "params": {"Adf-Window-Id": "window-id", "Adf-Page-Id": "0"},
        "javax_faces_ViewState": "old-view-state",
        "career_code": "0-2-8-3",
        "career_name": "Systems Engineering",
        "is_electives": False,
        "STATUS": status_name,
    }


@pytest.mark.unit
class TestViewStateMethods:
    """Cover direct extraction and sync helpers in SiaSession."""

    def test_extract_view_state_from_response_wrapper_returns_token(self) -> None:
        session = SiaSession(init_session=False)
        response = MagicMock()
        response.content = b'<input type="hidden" name="javax.faces.ViewState" value="new-vs">'

        result = session.extract_view_state_from_response(response)

        assert result == "new-vs"

    @patch("sia_scraper.session.get_course_list", return_value=[])
    @patch("sia_scraper.session.EnhancedSession")
    def test_sync_view_state_from_response_updates_request_dict(
        self,
        mock_session_class: MagicMock,
        _mock_get_course_list: MagicMock,
    ) -> None:
        mock_session = MagicMock()
        mock_session.headers = {}
        mock_session.cookies = MagicMock()
        mock_session.cookies.update = MagicMock()
        mock_session.get.return_value = MagicMock(content=b"<html></html>")
        mock_session_class.return_value = mock_session

        session = SiaSession(session_data=_session_data())
        response = MagicMock()
        response.content = b'<input type="hidden" name="javax.faces.ViewState" value="synced-vs">'

        session.sync_view_state_from_response(response)

        assert session._view_state == "synced-vs"
        assert session.request_dict["javax.faces.ViewState"] == "synced-vs"


@pytest.mark.unit
class TestSetCareerEdgeCase:
    """Cover set_career branch where final response is None."""

    @patch("sia_scraper.session.get_course_list", return_value=[])
    @patch("sia_scraper.session.EnhancedSession")
    @patch("sia_scraper.session.HtmlParser")
    def test_set_career_raises_career_not_set_when_final_response_is_none(
        self,
        mock_html_parser: MagicMock,
        mock_session_class: MagicMock,
        _mock_get_course_list: MagicMock,
    ) -> None:
        mock_session = MagicMock()
        mock_session.headers = {}
        mock_session.cookies = MagicMock()
        mock_session.cookies.update = MagicMock()
        mock_session.get.return_value = MagicMock(content=b"<html></html>")
        mock_session_class.return_value = mock_session

        parser = MagicMock()
        option = MagicMock()
        option.text = "Systems Engineering"
        parser.findall.return_value = [MagicMock(), option]
        mock_html_parser.return_value = parser

        session = SiaSession(session_data=_session_data(SiaSessionStatus.CAREER_NOT_SET.name))

        response_ok = MagicMock()
        response_ok.text = "<xml/>"
        session.post_request = MagicMock(
            side_effect=[response_ok, response_ok, response_ok, response_ok, response_ok, None]
        )

        with pytest.raises(SiaSessionException.CareerNotSet):
            session.set_career("0-2-0-0")
