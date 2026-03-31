"""Tests for context manager support in SiaScraper and SiaSession."""

from unittest.mock import MagicMock, patch

import pytest

from sia_scraper.constants import SiaSessionStatus
from sia_scraper.scraper import SiaScraper
from sia_scraper.session import SiaSession


@pytest.mark.unit
class TestSiaScraperContextManager:
    """Test SiaScraper context manager protocol."""

    @patch("sia_scraper.scraper.SiaSession")
    def test_context_manager_calls_close_on_exit(self, mock_session_class) -> None:
        """Verify close_session is called when exiting context manager."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        scraper = SiaScraper(timeout=30, init_session=False)
        scraper._sia_session = mock_session

        with scraper:
            pass

        mock_session.close_session.assert_called_once()

    @patch("sia_scraper.scraper.SiaSession")
    def test_context_manager_calls_close_on_exception(self, mock_session_class) -> None:
        """Verify close_session is called even when exception occurs."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        scraper = SiaScraper(timeout=30, init_session=False)
        scraper._sia_session = mock_session

        with pytest.raises(ValueError):
            with scraper:
                raise ValueError("Test exception")

        mock_session.close_session.assert_called_once()

    @patch("sia_scraper.scraper.SiaSession")
    def test_context_manager_returns_self(self, mock_session_class) -> None:
        """Verify __enter__ returns self."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        scraper = SiaScraper(timeout=30, init_session=False)
        scraper._sia_session = mock_session

        with scraper as s:
            assert s is scraper


@pytest.mark.unit
class TestSiaSessionContextManager:
    """Test SiaSession context manager protocol."""

    @patch("requests.Session")
    def test_session_context_manager_calls_close_on_exit(self, mock_session_class) -> None:
        """Verify close_session is called when exiting context manager."""
        mock_session = MagicMock()
        session = SiaSession(timeout=30, init_session=False)
        session._session = mock_session
        session._STATUS = SiaSessionStatus.CAREER_NOT_SET

        with session:
            pass

        mock_session.close.assert_called()

    @patch("requests.Session")
    def test_session_context_manager_calls_close_on_exception(self, mock_session_class) -> None:
        """Verify close_session is called even when exception occurs."""
        mock_session = MagicMock()
        session = SiaSession(timeout=30, init_session=False)
        session._session = mock_session
        session._STATUS = SiaSessionStatus.CAREER_NOT_SET

        with pytest.raises(ValueError):
            with session:
                raise ValueError("Test exception")

        mock_session.close.assert_called()

    @patch("requests.Session")
    def test_session_context_manager_returns_self(self, mock_session_class) -> None:
        """Verify __enter__ returns self."""
        mock_session = MagicMock()
        session = SiaSession(timeout=30, init_session=False)
        session._session = mock_session
        session._STATUS = SiaSessionStatus.CAREER_NOT_SET

        with session as s:
            assert s is session
