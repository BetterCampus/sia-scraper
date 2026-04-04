"""Unit tests for sia_scraper.scraper."""

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import sia_scraper_rust
from sia_scraper.constants import DEFAULT_TIMEOUT, SiaSessionStatus
from sia_scraper.core import SiaSessionException
from sia_scraper.parsers.models import ErrorMode, ScrapeResult
from sia_scraper.scraper import SiaScraper, init_sia_scraper


def _mock_session(scraper: SiaScraper) -> Any:
    """Return mocked session object for patched SiaSession class."""
    return cast(Any, scraper.sia_session)


def _make_state_model(
    career_code: str,
    career_name: str,
    is_electives: bool,
    status: str,
    course_list: list[dict[str, str]],
    view_state: str | None,
) -> sia_scraper_rust.SessionStateModel:
    """Create a typed SessionStateModel for testing."""
    entries = [
        sia_scraper_rust.CourseListEntryModel(code=item["code"], name=item["name"])
        for item in course_list
    ]
    return sia_scraper_rust.SessionStateModel(
        session_headers={},
        session_cookies={},
        params={"Adf-Page-Id": "1", "Adf-Window-Id": ""},
        career_code=career_code,
        career_name=career_name,
        is_electives=is_electives,
        status=status,
        course_list=entries,
        javax_faces_view_state=view_state,
    )


@pytest.fixture
def mock_async_session_class():
    """Mock SiaSession class for scraper async tests."""
    with patch("sia_scraper.scraper.SiaSession") as mock_session_class:
        mock_state = _make_state_model(
            career_code="",
            career_name="N/A",
            is_electives=False,
            status="NO_SESSION",
            course_list=[],
            view_state="test",
        )
        session = MagicMock()
        session.career_code = ""
        session.career_name = "N/A"
        session.course_list = []
        session.is_electives = False
        session.status = SiaSessionStatus.NO_SESSION
        session.init_session = AsyncMock()
        session.set_career = AsyncMock()
        session.scrape_course_info = AsyncMock()
        session.scrape_course_prereqs = AsyncMock()
        session.close = AsyncMock()
        session.get_session_data = MagicMock(return_value=mock_state)
        mock_session_class.return_value = session
        yield mock_session_class


@pytest.mark.unit
class TestSiaScraperInitialization:
    """Test async scraper initialization behavior."""

    def test_init_default(self, mock_async_session_class):
        scraper = SiaScraper(init_session=False)

        assert scraper.career_name == "N/A"

    @pytest.mark.asyncio
    async def test_create_with_session(self, mock_async_session_class):
        with patch("sia_scraper.scraper.SiaSession") as mock_session_class:
            session = MagicMock()
            session.career_code = "0-2-8-3"
            session.career_name = "Ing"
            session.course_list = []
            session.is_electives = False
            session.status = SiaSessionStatus.CAREER_NOT_SET
            session.init_session = AsyncMock()
            session.close = AsyncMock()
            mock_session_class.return_value = session

            scraper = await SiaScraper.create(timeout=10, init_session=True)
            assert scraper._timeout == 10
            session.init_session.assert_awaited_once()

    def test_valid_session_false_on_init(self, mock_async_session_class):
        scraper = SiaScraper(init_session=False)
        assert not scraper.valid_session()


@pytest.mark.unit
class TestSiaScraperCareer:
    """Test career selection behavior."""

    @pytest.mark.asyncio
    async def test_set_career(self, mock_async_session_class):
        scraper = SiaScraper(init_session=False)
        mock_session = _mock_session(scraper)
        mock_session.set_career = AsyncMock()

        out = await scraper.set_career("0-2-8-3", is_electives=True)

        assert out is scraper
        mock_session.set_career.assert_awaited_once_with("0-2-8-3", is_electives=True)


@pytest.mark.unit
class TestSiaScraperScraping:
    """Test async scraping methods."""

    @pytest.mark.asyncio
    async def test_get_course_info_by_index(self, mock_async_session_class):
        scraper = SiaScraper(init_session=False)
        mock_session = _mock_session(scraper)
        mock_session.scrape_course_info.return_value = sia_scraper_rust.CourseInfoModel(
            course_name="Test Course",
            credits=3,
            typology="DISCIPLINAR OBLIGATORIA",
            available_spots=20,
            scrape_timestamp="2024-01-01 12:00",
            groups=[],
            code=None,
        )

        out = await scraper.get_course_info(course_index=0)

        assert isinstance(out, sia_scraper_rust.CourseInfoModel)
        mock_session.scrape_course_info.assert_awaited_once_with(0)

    @pytest.mark.asyncio
    async def test_get_course_info_by_code(self, mock_async_session_class):
        scraper = SiaScraper(init_session=False)
        mock_session = _mock_session(scraper)
        mock_session.status = SiaSessionStatus.ON_CAREER_PAGE
        mock_session.course_list = [
            {"code": "1000001", "name": "Calculo"},
            {"code": "2016489", "name": "Estructuras"},
        ]
        mock_session.scrape_course_info.return_value = sia_scraper_rust.CourseInfoModel(
            course_name="Test Course",
            credits=3,
            typology="DISCIPLINAR OBLIGATORIA",
            available_spots=20,
            scrape_timestamp="2024-01-01 12:00",
            groups=[],
            code=None,
        )

        out = await scraper.get_course_info(course_code="2016489")

        assert isinstance(out, sia_scraper_rust.CourseInfoModel)
        mock_session.scrape_course_info.assert_awaited_once_with(1)

    @pytest.mark.asyncio
    async def test_get_course_prereqs_by_index(self, mock_async_session_class):
        scraper = SiaScraper(init_session=False)
        mock_session = _mock_session(scraper)
        mock_session.scrape_course_prereqs.return_value = sia_scraper_rust.CoursePrereqsModel(
            course_name="Test",
            code=None,
            credits=3,
            typology="DISCIPLINAR",
            conditions=[],
        )

        out = await scraper.get_course_prereqs(course_index=0)

        assert isinstance(out, sia_scraper_rust.CoursePrereqsModel)
        mock_session.scrape_course_prereqs.assert_awaited_once_with(0)

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
    async def test_scrape_courses_abort_mode_sorted_alignment(self, mock_async_session_class):
        scraper = SiaScraper(init_session=False)
        mock_session = _mock_session(scraper)

        course1 = sia_scraper_rust.CourseInfoModel(
            course_name="Course 1",
            credits=3,
            typology="DISCIPLINAR",
            available_spots=20,
            scrape_timestamp="2024-01-01 12:00",
            groups=[],
            code=None,
        )
        course2 = sia_scraper_rust.CourseInfoModel(
            course_name="Course 2",
            credits=3,
            typology="DISCIPLINAR",
            available_spots=20,
            scrape_timestamp="2024-01-01 12:00",
            groups=[],
            code=None,
        )
        course3 = sia_scraper_rust.CourseInfoModel(
            course_name="Course 3",
            credits=3,
            typology="DISCIPLINAR",
            available_spots=20,
            scrape_timestamp="2024-01-01 12:00",
            groups=[],
            code=None,
        )

        mock_result = MagicMock()
        mock_result.successes = [course1, course2, course3]
        mock_session.scrape_courses = AsyncMock(return_value=mock_result)

        out = await scraper.scrape_courses(
            courses_indices=[3, 1, 2],
            courses_codes=["QUIMICA", "ALGEBRA", "FISICA"],
            error_mode=ErrorMode.ABORT,
        )

        assert isinstance(out, list)
        assert len(out) == 3
        mock_session.scrape_courses.assert_awaited_once()
        call_args = mock_session.scrape_courses.call_args
        assert call_args is not None
        assert call_args[0][0] == [1, 2, 3]  # Sorted indices

    @pytest.mark.asyncio
    async def test_scrape_courses_skip_mode_returns_result(self, mock_async_session_class):
        scraper = SiaScraper(init_session=False)
        mock_session = _mock_session(scraper)

        course = sia_scraper_rust.CourseInfoModel(
            course_name="Course A",
            credits=3,
            typology="DISCIPLINAR",
            available_spots=20,
            scrape_timestamp="2024-01-01 12:00",
            groups=[],
            code=None,
        )

        mock_result = MagicMock()
        mock_result.successes = [course]
        mock_result.failures = [(1, "boom")]
        mock_result.total.return_value = 2
        mock_session.scrape_courses = AsyncMock(return_value=mock_result)

        out = await scraper.scrape_courses(
            courses_indices=[0, 1],
            courses_codes=["A", "B"],
            error_mode=ErrorMode.SKIP,
        )

        assert isinstance(out, ScrapeResult)
        assert len(out.successes) == 1


@pytest.mark.unit
class TestSiaScraperSessionState:
    """Test session state handling."""

    @pytest.mark.asyncio
    async def test_constructor_with_session_data(self, mock_async_session_class):
        data = {
            "session_headers": {},
            "session_cookies": {},
            "params": {"Adf-Page-Id": "1", "Adf-Window-Id": ""},
            "javax_faces_ViewState": "vs1",
            "career_code": "0-2-8-3",
            "career_name": "Ingenieria",
            "is_electives": False,
            "status": "ON_CAREER_PAGE",
            "course_list": [],
        }
        scraper = SiaScraper(session_data=data, init_session=False)
        assert scraper.sia_session._career_code == "0-2-8-3"
        assert scraper.sia_session._career_name == "Ingenieria"
        assert scraper.sia_session._status == SiaSessionStatus.ON_CAREER_PAGE

    def test_load_session_restores_state(self, mock_async_session_class):
        scraper = SiaScraper(init_session=False)
        data = {
            "session_headers": {},
            "session_cookies": {},
            "params": {"Adf-Page-Id": "0", "Adf-Window-Id": "win1"},
            "javax_faces_ViewState": "vs-restored",
            "career_code": "1-0-0-1",
            "career_name": "Test Career",
            "is_electives": True,
            "status": "ON_CAREER_PAGE",
            "course_list": [],
        }
        result = scraper.load_session(data)
        assert result is scraper
        assert scraper.sia_session._career_code == "1-0-0-1"
        assert scraper.sia_session._career_name == "Test Career"
        assert scraper.sia_session._is_electives is True
        assert scraper.sia_session._status == SiaSessionStatus.ON_CAREER_PAGE

    def test_load_session_invalid_status_raises(self, mock_async_session_class):
        scraper = SiaScraper(init_session=False)
        with pytest.raises(SiaSessionException):
            scraper.load_session(
                {
                    "session_headers": {},
                    "session_cookies": {},
                    "params": {"Adf-Page-Id": "0", "Adf-Window-Id": ""},
                    "javax_faces_ViewState": None,
                    "career_code": "",
                    "career_name": "",
                    "is_electives": False,
                    "status": "BOGUS_STATUS",
                    "course_list": [],
                }
            )

    def test_valid_session_false_when_no_session(self, mock_async_session_class):
        scraper = SiaScraper(init_session=False)
        assert not scraper.valid_session()

    def test_get_course_index_raises_when_code_not_found(self, mock_async_session_class):
        scraper = SiaScraper(init_session=False)
        mock_session = _mock_session(scraper)
        mock_session.status = SiaSessionStatus.ON_CAREER_PAGE
        scraper.sia_session._course_list = [{"code": "1000001", "name": "Calculo"}]

        with pytest.raises(ValueError, match="Course code '9999999' not found"):
            scraper.get_course_index("9999999")

    @pytest.mark.asyncio
    async def test_get_session_data_returns_session_state(self, mock_async_session_class):
        scraper = SiaScraper(init_session=False)

        mock_session = _mock_session(scraper)
        mock_session.get_session_data = AsyncMock(
            return_value={
                "timeout": 15,
                "state_dict": {
                    "session_headers": {},
                    "session_cookies": {},
                    "params": {},
                    "javax_faces_view_state": "vs",
                    "career_code": "0-2-8-3",
                    "career_name": "Ing",
                    "is_electives": False,
                    "status": "ON_CAREER_PAGE",
                    "course_list": [],
                },
            }
        )
        result = await scraper.get_session_data()
        assert result["state_dict"]["career_code"] == "0-2-8-3"


@pytest.mark.unit
class TestSiaScraperScrapeCoursesEdgeCases:
    """Test scrape_courses edge cases for uncovered lines."""

    @pytest.mark.asyncio
    async def test_scrape_courses_with_progress_callback(self, mock_async_session_class):
        scraper = SiaScraper(init_session=False)
        mock_session = _mock_session(scraper)

        course1 = sia_scraper_rust.CourseInfoModel(
            course_name="Course 0",
            credits=3,
            typology="DISCIPLINAR",
            available_spots=20,
            scrape_timestamp="2024-01-01 12:00",
            groups=[],
            code=None,
        )
        course2 = sia_scraper_rust.CourseInfoModel(
            course_name="Course 1",
            credits=3,
            typology="DISCIPLINAR",
            available_spots=20,
            scrape_timestamp="2024-01-01 12:00",
            groups=[],
            code=None,
        )

        mock_result = MagicMock()
        mock_result.successes = [course1, course2]
        mock_result.failures = []
        mock_result.total.return_value = 2
        mock_session.scrape_courses = AsyncMock(return_value=mock_result)

        progress_calls = []

        def progress_callback(current, total, successes, failures):
            progress_calls.append((current, total, successes, failures))

        await scraper.scrape_courses(
            courses_indices=[0, 1],
            courses_codes=["A", "B"],
            error_mode=ErrorMode.SKIP,
            progress_callback=progress_callback,
        )

        assert len(progress_calls) == 1
        assert progress_calls[0] == (2, 2, 2, 0)

    @pytest.mark.asyncio
    async def test_scrape_courses_with_codes_only(self, mock_async_session_class):
        scraper = SiaScraper(init_session=False)
        mock_session = _mock_session(scraper)
        mock_session.status = SiaSessionStatus.ON_CAREER_PAGE
        mock_session.course_list = [
            {"code": "1000001", "name": "Calculo"},
            {"code": "2016489", "name": "Estructuras"},
        ]

        course = sia_scraper_rust.CourseInfoModel(
            course_name="Course 0",
            credits=3,
            typology="DISCIPLINAR OBLIGATORIA",
            available_spots=20,
            scrape_timestamp="2024-01-01 12:00",
            groups=[],
            code=None,
        )

        mock_result = MagicMock()
        mock_result.successes = [course]
        mock_session.scrape_courses = AsyncMock(return_value=mock_result)

        out = await scraper.scrape_courses(
            courses_codes=["1000001"],
            error_mode=ErrorMode.ABORT,
        )

        assert isinstance(out, list)
        assert len(out) == 1


@pytest.mark.unit
class TestInitSiaScraperEdgeCases:
    """Test init_sia_scraper factory edge cases."""

    @pytest.mark.asyncio
    async def test_init_sia_scraper_with_none_session_data(self):
        mocked_scraper = MagicMock()
        mocked_scraper.valid_session.return_value = False

        with patch(
            "sia_scraper.scraper.create_career_session",
            AsyncMock(return_value=mocked_scraper),
        ) as mock_create:
            out = await init_sia_scraper("0-2-8-3", False, session_data=None)

        assert out is mocked_scraper
        mock_create.assert_awaited_once_with("0-2-8-3", False, timeout=DEFAULT_TIMEOUT)

    @pytest.mark.asyncio
    async def test_init_sia_scraper_with_invalid_session_data(self):
        with pytest.raises(SiaSessionException):
            await init_sia_scraper(
                "0-2-8-3",
                False,
                session_data={
                    "session_headers": {},
                    "session_cookies": {},
                    "params": {"Adf-Page-Id": "1", "Adf-Window-Id": ""},
                    "javax_faces_ViewState": "vs",
                    "career_code": "0-2-8-3",
                    "career_name": "Test",
                    "is_electives": False,
                    "status": "BOGUS_STATUS",
                    "course_list": [],
                },
            )
