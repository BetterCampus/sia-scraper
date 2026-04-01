"""Unit tests for sia_scraper.scraper."""

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sia_scraper.constants import DEFAULT_TIMEOUT, SiaSessionStatus
from sia_scraper.core import SiaSessionException
from sia_scraper.parsers import CourseInfo, CoursePrereqs, scrape_info
from sia_scraper.parsers.models import ErrorMode, ScrapeResult, SessionState
from sia_scraper.scraper import SiaScraper, create_career_session, init_sia_scraper


def _mock_session(scraper: SiaScraper) -> Any:
    """Return mocked session object for patched SiaSession class."""
    return cast(Any, scraper.sia_session)


@pytest.fixture
def mock_async_session_class():
    """Mock SiaSession class for scraper async tests."""
    with patch("sia_scraper.scraper.SiaSession") as mock_session_class:
        session = MagicMock()
        session.career_code = ""
        session.career_name = "N/A"
        session.course_list = []
        session.is_electives = False
        session.status = SiaSessionStatus.NO_SESSION
        session.init_session = AsyncMock()
        session.set_career = AsyncMock()
        session.get_course_xml = AsyncMock()
        session.close = AsyncMock()
        session.get_session_data = MagicMock(
            return_value=SessionState(
                session_headers={},
                session_cookies={},
                params={"Adf-Page-Id": "1", "Adf-Window-Id": ""},
                javax_faces_ViewState="test",
                career_code="",
                career_name="N/A",
                is_electives=False,
                status=SiaSessionStatus.NO_SESSION.name,
            )
        )
        mock_session_class.return_value = session
        yield mock_session_class


@pytest.mark.unit
class TestSiaScraperInitialization:
    """Test async scraper initialization behavior."""

    def test_init_default(self, mock_async_session_class):
        scraper = SiaScraper(init_session=False)

        assert scraper.career_name == "N/A"
        assert scraper.career_code == ""
        assert scraper.course_list == []
        mock_async_session_class.assert_called_once_with(timeout=DEFAULT_TIMEOUT)

    @pytest.mark.asyncio
    async def test_create_initializes_session(self, mock_async_session_class):
        scraper = await SiaScraper.create(timeout=9)
        mock_session = _mock_session(scraper)

        assert isinstance(scraper, SiaScraper)
        mock_session.init_session.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_without_init_session(self, mock_async_session_class):
        scraper = await SiaScraper.create(timeout=9, init_session=False)
        mock_session = _mock_session(scraper)

        assert isinstance(scraper, SiaScraper)
        mock_session.init_session.assert_not_awaited()


@pytest.mark.unit
class TestSiaScraperSessionMethods:
    """Test async session lifecycle methods."""

    @pytest.mark.asyncio
    async def test_create_session_delegates(self, mock_async_session_class):
        scraper = SiaScraper(init_session=False)
        mock_session = _mock_session(scraper)

        out = await scraper.create_session()

        assert out is scraper
        mock_session.init_session.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_close_session_delegates(self, mock_async_session_class):
        scraper = SiaScraper(init_session=False)
        mock_session = _mock_session(scraper)

        out = await scraper.close_session()

        assert out is scraper
        mock_session.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_async_session_class):
        async with SiaScraper(init_session=False) as scraper:
            assert scraper.career_name == "N/A"
            mock_session = _mock_session(scraper)

        mock_session.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_set_career(self, mock_async_session_class):
        scraper = SiaScraper(init_session=False)
        mock_session = _mock_session(scraper)

        out = await scraper.set_career("0-2-8-3", is_electives=True)

        assert out is scraper
        mock_session.set_career.assert_awaited_once_with("0-2-8-3", is_electives=True)


@pytest.mark.unit
class TestSiaScraperScraping:
    """Test async scraping methods."""

    @pytest.mark.asyncio
    async def test_get_course_info_by_index(self, mock_async_session_class, sia_course_detail_xml):
        scraper = SiaScraper(init_session=False)
        mock_session = _mock_session(scraper)
        mock_session.get_course_xml.return_value = sia_course_detail_xml

        out = await scraper.get_course_info(course_index=0)

        assert isinstance(out, CourseInfo)
        mock_session.get_course_xml.assert_awaited_once_with(0)

    @pytest.mark.asyncio
    async def test_get_course_info_by_code(self, mock_async_session_class, sia_course_detail_xml):
        scraper = SiaScraper(init_session=False)
        mock_session = _mock_session(scraper)
        mock_session.status = SiaSessionStatus.ON_CAREER_PAGE
        mock_session.course_list = [{"1000001": "Calculo"}, {"2016489": "Estructuras"}]
        mock_session.get_course_xml.return_value = sia_course_detail_xml

        out = await scraper.get_course_info(course_code="2016489")

        assert isinstance(out, CourseInfo)
        mock_session.get_course_xml.assert_awaited_once_with(1)

    @pytest.mark.asyncio
    async def test_get_course_prereqs_by_index(
        self, mock_async_session_class, sia_course_prereqs_xml
    ):
        scraper = SiaScraper(init_session=False)
        mock_session = _mock_session(scraper)
        mock_session.get_course_xml.return_value = sia_course_prereqs_xml

        out = await scraper.get_course_prereqs(course_index=0)

        assert isinstance(out, CoursePrereqs)
        mock_session.get_course_xml.assert_awaited_once_with(0)

    def test_get_course_index_invalid_status_raises(self, mock_async_session_class):
        scraper = SiaScraper(init_session=False)
        mock_session = _mock_session(scraper)
        mock_session.status = SiaSessionStatus.NO_SESSION

        with pytest.raises(SiaSessionException.InvalidStatus):
            scraper.get_course_index("1000001")


@pytest.mark.unit
class TestSiaScraperBatchScraping:
    """Test async batch scrape modes."""

    @pytest.mark.asyncio
    async def test_scrape_courses_abort_mode_sorted_alignment(
        self, mock_async_session_class, sia_course_detail_xml
    ):
        scraper = SiaScraper(init_session=False)
        mock_session = _mock_session(scraper)
        mock_session.get_course_xml.return_value = sia_course_detail_xml

        out = await scraper.scrape_courses(
            courses_indices=[3, 1, 2],
            courses_codes=["QUIMICA", "ALGEBRA", "FISICA"],
            error_mode=ErrorMode.ABORT,
        )

        assert isinstance(out, list)
        assert len(out) == 3
        assert out[0].code == "ALGEBRA"
        assert out[1].code == "FISICA"
        assert out[2].code == "QUIMICA"

    @pytest.mark.asyncio
    async def test_scrape_courses_skip_mode_returns_result(self, mock_async_session_class):
        scraper = SiaScraper(init_session=False)
        sample_course = scrape_info(
            """
            <h2>CURSO X</h2>
            <span class=\"detass-creditos\"><span>3</span></span>
            <span class=\"detass-tipologia\"><span>DISCIPLINAR OBLIGATORIA</span></span>
            """
        )

        scraper.get_course_info = AsyncMock(side_effect=[sample_course, RuntimeError("boom")])

        out = await scraper.scrape_courses(
            courses_indices=[0, 1],
            courses_codes=["A", "B"],
            error_mode=ErrorMode.SKIP,
        )

        assert isinstance(out, ScrapeResult)
        assert len(out.successes) == 1
        assert len(out.failures) == 1

    @pytest.mark.asyncio
    async def test_scrape_courses_retry_mode_retries(self, mock_async_session_class):
        scraper = SiaScraper(init_session=False)
        sample_course = scrape_info(
            """
            <h2>CURSO X</h2>
            <span class=\"detass-creditos\"><span>3</span></span>
            <span class=\"detass-tipologia\"><span>DISCIPLINAR OBLIGATORIA</span></span>
            """
        )

        scraper.get_course_info = AsyncMock(side_effect=[RuntimeError("temp"), sample_course])

        out = await scraper.scrape_courses(
            courses_indices=[0],
            courses_codes=["A"],
            error_mode=ErrorMode.RETRY,
            max_retries=2,
            retry_delay=0.0,
        )

        assert isinstance(out, ScrapeResult)
        assert len(out.successes) == 1
        assert len(out.failures) == 0
        assert scraper.get_course_info.await_count == 2


@pytest.mark.unit
class TestSiaScraperFactories:
    """Test async factory helper functions."""

    @pytest.mark.asyncio
    async def test_create_career_session(self):
        mocked_scraper = MagicMock()
        mocked_scraper.set_career = AsyncMock()

        with patch(
            "sia_scraper.scraper.SiaScraper.create",
            AsyncMock(return_value=mocked_scraper),
        ):
            out = await create_career_session("0-2-8-3", False, timeout=9)

        assert out is mocked_scraper
        mocked_scraper.set_career.assert_awaited_once_with("0-2-8-3", is_electives=False)

    @pytest.mark.asyncio
    async def test_init_sia_scraper_empty_session_creates_new(self):
        mocked_scraper = MagicMock()

        with patch(
            "sia_scraper.scraper.create_career_session",
            AsyncMock(return_value=mocked_scraper),
        ) as mock_create:
            out = await init_sia_scraper("0-2-8-3", False, session_data={})

        assert out is mocked_scraper
        mock_create.assert_awaited_once_with("0-2-8-3", False, timeout=DEFAULT_TIMEOUT)

    @pytest.mark.asyncio
    async def test_init_sia_scraper_switches_career_when_needed(self):
        mocked_scraper = MagicMock()
        mocked_scraper.valid_session.return_value = True
        mocked_scraper.career_code = "different"
        mocked_scraper.sia_session.is_electives = False
        mocked_scraper.set_career = AsyncMock()

        with patch(
            "sia_scraper.scraper.SiaScraper.create",
            AsyncMock(return_value=mocked_scraper),
        ):
            out = await init_sia_scraper(
                "0-2-8-3",
                True,
                session_data={
                    "session_headers": {},
                    "session_cookies": {},
                    "params": {"Adf-Page-Id": "1", "Adf-Window-Id": ""},
                    "javax_faces_ViewState": "x",
                    "career_code": "different",
                    "career_name": "N/A",
                    "is_electives": False,
                    "status": "ON_CAREER_PAGE",
                },
            )

        assert out is mocked_scraper
        mocked_scraper.set_career.assert_awaited_once_with("0-2-8-3", is_electives=True)


@pytest.mark.unit
class TestSiaScraperSessionState:
    """Test session state loading, serialization, and validation."""

    def test_constructor_with_session_data(self, mock_async_session_class):
        data = SessionState(
            session_headers={},
            session_cookies={},
            params={"Adf-Page-Id": "1", "Adf-Window-Id": ""},
            javax_faces_ViewState="vs1",
            career_code="0-2-8-3",
            career_name="Ingenieria",
            is_electives=False,
            status=SiaSessionStatus.ON_CAREER_PAGE.name,
        )
        scraper = SiaScraper(session_data=data, init_session=False)
        assert scraper.sia_session._career_code == "0-2-8-3"
        assert scraper.sia_session._career_name == "Ingenieria"
        assert scraper.sia_session._status == SiaSessionStatus.ON_CAREER_PAGE

    def test_load_session_restores_state(self, mock_async_session_class):
        scraper = SiaScraper(init_session=False)
        data = SessionState(
            session_headers={},
            session_cookies={},
            params={"Adf-Page-Id": "0", "Adf-Window-Id": "win1"},
            javax_faces_ViewState="vs-restored",
            career_code="1-0-0-1",
            career_name="Test Career",
            is_electives=True,
            status=SiaSessionStatus.ON_CAREER_PAGE.name,
        )
        result = scraper.load_session(data)
        assert result is scraper
        assert scraper.sia_session._career_code == "1-0-0-1"
        assert scraper.sia_session._career_name == "Test Career"
        assert scraper.sia_session._is_electives is True
        assert scraper.sia_session._status == SiaSessionStatus.ON_CAREER_PAGE

    def test_load_session_invalid_status_defaults_to_no_session(self, mock_async_session_class):
        scraper = SiaScraper(init_session=False)
        data = SessionState(
            session_headers={},
            session_cookies={},
            params={"Adf-Page-Id": "0", "Adf-Window-Id": ""},
            javax_faces_ViewState=None,
            career_code="",
            career_name="",
            is_electives=False,
            status="BOGUS_STATUS",
        )
        scraper.load_session(data)
        assert scraper.sia_session._status == SiaSessionStatus.NO_SESSION

    def test_valid_session_false_when_no_session(self, mock_async_session_class):
        scraper = SiaScraper(init_session=False)
        assert not scraper.valid_session()

    def test_get_course_index_raises_when_code_not_found(self, mock_async_session_class):
        scraper = SiaScraper(init_session=False)
        mock_session = _mock_session(scraper)
        mock_session.status = SiaSessionStatus.ON_CAREER_PAGE
        scraper.sia_session._session_state = {
            "course_list": [{"1000001": "Calculo"}],
            "javax_faces_ViewState": "vs",
        }
        with pytest.raises(ValueError, match="Course code '9999999' not found"):
            scraper.get_course_index("9999999")
