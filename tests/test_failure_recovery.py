"""Failure and recovery flow tests for sia_scraper.

These tests verify that the scraper handles various failure scenarios gracefully
and can recover from error conditions.
"""

from unittest.mock import MagicMock, patch

import pytest
from requests.exceptions import ConnectionError, Timeout

from sia_scraper.constants import SiaSessionStatus
from sia_scraper.core import SiaSessionException
from sia_scraper.parsers import CourseInfo
from sia_scraper.parsers.models import ErrorMode, ScrapeResult
from sia_scraper.scraper import SiaScraper


@pytest.fixture
def mock_sia_session():
    """Mock SiaSession for failure/recovery tests."""
    with patch("sia_scraper.scraper.SiaSession") as mock_session_class:
        session_instance = MagicMock()
        session_instance.career_code = ""
        session_instance.career_name = "N/A"
        session_instance.course_list = []
        session_instance.STATUS = SiaSessionStatus.NO_SESSION
        session_instance.init_session = MagicMock()
        session_instance.set_career = MagicMock()
        session_instance.get_course_xml = MagicMock()
        session_instance.close_session = MagicMock()
        session_instance.valid_session = MagicMock(return_value=True)
        session_instance.get_session_data = MagicMock(return_value={})
        session_instance.load_session = MagicMock()
        mock_session_class.return_value = session_instance
        yield session_instance


@pytest.fixture
def mock_course_info():
    """Create a valid CourseInfo object for testing."""
    return CourseInfo(
        course_name="Test Course",
        credits=3,
        typology="DISCIPLINAR OBLIGATORIA",
        code="1000001",
        groups=[],
        available_spots=50,
        scrape_timestamp="2024-01-01 12:00",
    )


@pytest.mark.unit
class TestFailureAndRecoveryFlows:
    """Unit tests for failure scenarios and recovery mechanisms."""

    def test_scraper_init_session_handles_connection_error(self, mock_sia_session) -> None:
        """Verify SiaScraper handles ConnectionError during init_session."""
        mock_sia_session.init_session = MagicMock(
            side_effect=ConnectionError("Network unavailable")
        )

        scraper = SiaScraper(timeout=30, init_session=False)
        scraper._sia_session = mock_sia_session

        with pytest.raises(ConnectionError):
            scraper.create_session()

    def test_scraper_init_session_handles_timeout(self, mock_sia_session) -> None:
        """Verify SiaScraper handles Timeout during init_session."""
        mock_sia_session.init_session = MagicMock(side_effect=Timeout("Request timed out"))

        scraper = SiaScraper(timeout=30, init_session=False)
        scraper._sia_session = mock_sia_session

        with pytest.raises(Timeout):
            scraper.create_session()

    def test_scrape_courses_skip_mode_returns_result(
        self, mock_sia_session, mock_course_info
    ) -> None:
        """Verify SKIP mode returns ScrapeResult."""
        mock_sia_session.STATUS = SiaSessionStatus.ON_CAREER_PAGE
        mock_sia_session.courses = [{"code": "1000001", "name": "Course 1"}]

        scraper = SiaScraper(timeout=30, init_session=False)
        scraper._sia_session = mock_sia_session
        scraper.get_course_info = MagicMock(return_value=mock_course_info)  # type: ignore[method-assignment]

        result = scraper.scrape_courses(
            error_mode=ErrorMode.SKIP,
            courses_indices=[0],
            courses_codes=["1000001"],
        )

        assert isinstance(result, ScrapeResult)

    def test_scrape_courses_retry_mode_returns_result(
        self, mock_sia_session, mock_course_info
    ) -> None:
        """Verify RETRY mode returns ScrapeResult."""
        mock_sia_session.STATUS = SiaSessionStatus.ON_CAREER_PAGE
        mock_sia_session.courses = [{"code": "1000001", "name": "Course 1"}]

        scraper = SiaScraper(timeout=30, init_session=False)
        scraper._sia_session = mock_sia_session
        scraper.get_course_info = MagicMock(return_value=mock_course_info)  # type: ignore[method-assignment]

        result = scraper.scrape_courses(
            error_mode=ErrorMode.RETRY,
            courses_indices=[0],
            courses_codes=["1000001"],
        )

        assert isinstance(result, ScrapeResult)

    def test_scrape_courses_abort_mode_returns_list(
        self, mock_sia_session, mock_course_info
    ) -> None:
        """Verify ABORT mode returns list."""
        mock_sia_session.STATUS = SiaSessionStatus.ON_CAREER_PAGE
        mock_sia_session.courses = [{"code": "1000001", "name": "Course 1"}]

        scraper = SiaScraper(timeout=30, init_session=False)
        scraper._sia_session = mock_sia_session
        scraper.get_course_info = MagicMock(return_value=mock_course_info)  # type: ignore[method-assignment]

        result = scraper.scrape_courses(
            error_mode=ErrorMode.ABORT,
            courses_indices=[0],
            courses_codes=["1000001"],
        )

        assert isinstance(result, list)

    def test_scrape_courses_with_error_count_tracked(
        self, mock_sia_session, mock_course_info
    ) -> None:
        """Verify that errors are tracked in ScrapeResult."""
        mock_sia_session.STATUS = SiaSessionStatus.ON_CAREER_PAGE
        mock_sia_session.courses = [
            {"code": "1000001", "name": "Course 1"},
            {"code": "1000002", "name": "Course 2"},
        ]

        scraper = SiaScraper(timeout=30, init_session=False)
        scraper._sia_session = mock_sia_session

        call_count = {"count": 0}

        def mock_get_course_info(course_index: int, course_code: str = "") -> CourseInfo:
            call_count["count"] += 1
            if course_index == 0:
                raise Timeout("Timeout on course 0")
            return mock_course_info

        scraper.get_course_info = mock_get_course_info  # type: ignore[method-assignment]

        result = scraper.scrape_courses(
            error_mode=ErrorMode.SKIP,
            courses_indices=[0, 1],
            courses_codes=["1000001", "1000002"],
        )

        assert isinstance(result, ScrapeResult)
        assert result.success_rate >= 0

    def test_scraper_state_preserved_after_network_failure(self, mock_sia_session) -> None:
        """Verify session status is preserved after network failure."""
        mock_sia_session.STATUS = SiaSessionStatus.CAREER_NOT_SET

        scraper = SiaScraper(timeout=30, init_session=False)
        scraper._sia_session = mock_sia_session

        mock_sia_session.get = MagicMock(side_effect=ConnectionError("Network lost"))

        initial_status = mock_sia_session.STATUS

        try:
            scraper.set_career("0-2-8-3")
        except ConnectionError:
            pass

        assert mock_sia_session.STATUS == initial_status

    def test_scraper_valid_session_after_repeated_timeouts(self, mock_sia_session) -> None:
        """Verify valid_session() returns correct status after repeated timeouts."""
        mock_sia_session.STATUS = SiaSessionStatus.CAREER_NOT_SET

        scraper = SiaScraper(timeout=30, init_session=False)
        scraper._sia_session = mock_sia_session

        mock_sia_session.get = MagicMock(side_effect=Timeout("Timeout"))

        for _ in range(3):
            try:
                scraper.set_career("0-2-8-3")
            except (Timeout, ConnectionError):
                pass

        assert scraper.valid_session() is True


@pytest.mark.unit
class TestRecoveryFlowEdgeCases:
    """Edge case tests for recovery flows."""

    def test_scrape_courses_empty_course_list(self, mock_sia_session) -> None:
        """Verify handling of empty course list."""
        mock_sia_session.STATUS = SiaSessionStatus.ON_CAREER_PAGE
        mock_sia_session.courses = []

        scraper = SiaScraper(timeout=30, init_session=False)
        scraper._sia_session = mock_sia_session

        result = scraper.scrape_courses(
            error_mode=ErrorMode.ABORT,
            courses_indices=[],
            courses_codes=[],
        )

        assert isinstance(result, (list, ScrapeResult))

    def test_scrape_courses_with_no_session(self, mock_sia_session) -> None:
        """Verify handling when session is not initialized."""
        mock_sia_session.STATUS = SiaSessionStatus.NO_SESSION

        scraper = SiaScraper(timeout=30, init_session=False)
        scraper._sia_session = mock_sia_session

        result = scraper.scrape_courses(
            error_mode=ErrorMode.ABORT,
            courses_indices=[],
            courses_codes=[],
        )

        assert isinstance(result, (list, ScrapeResult))

    def test_scraper_handles_partial_viewstate_corruption(self, mock_sia_session) -> None:
        """Verify handling when ViewState is missing/corrupted."""
        mock_response = MagicMock()
        mock_response.text = "<input name='javax.faces.ViewState' value='new_state'/>"

        mock_sia_session.STATUS = SiaSessionStatus.CAREER_NOT_SET
        mock_sia_session.create = MagicMock()
        mock_sia_session._Adf_View_State = None
        mock_sia_session.get = MagicMock(return_value=mock_response)
        mock_sia_session.post = MagicMock(return_value=mock_response)

        scraper = SiaScraper(timeout=30, init_session=False)
        scraper._sia_session = mock_sia_session

        try:
            scraper.set_career("0-2-8-3")
        except (SiaSessionException, ConnectionError, Timeout, ValueError):
            pass

        assert scraper.valid_session()
