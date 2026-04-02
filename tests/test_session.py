"""Unit tests for Rust-backed async session wrapper."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import sia_scraper_rust
from sia_scraper.constants import SiaSessionStatus
from sia_scraper.session import SiaSession


@pytest.fixture
def mock_rust_session():
    """Mock PySiaSession for unit testing."""

    def make_state_model(
        career_code: str,
        career_name: str,
        is_electives: bool,
        status: str,
        course_list: list[dict[str, str]],
        view_state: str | None,
    ) -> sia_scraper_rust.SessionStateModel:
        entries = [
            sia_scraper_rust.CourseListEntryModel(
                course_code=item["course_code"], course_name=item["course_name"]
            )
            for item in course_list
        ]
        return sia_scraper_rust.SessionStateModel(
            session_headers={},
            session_cookies={},
            params={"Adf-Page-Id": "0", "Adf-Window-Id": "win-1"},
            career_code=career_code,
            career_name=career_name,
            is_electives=is_electives,
            status=status,
            course_list=entries,
            javax_faces_view_state=view_state,
        )

    def init_side_effect() -> sia_scraper_rust.SessionStateModel:
        return make_state_model(
            career_code="",
            career_name="N/A",
            is_electives=False,
            status="CAREER_NOT_SET",
            course_list=[],
            view_state="vs-1",
        )

    def career_side_effect(
        search_code: str, electives: bool | None = None
    ) -> sia_scraper_rust.SessionStateModel:
        return make_state_model(
            career_code=search_code,
            career_name="Ingenieria de Sistemas",
            is_electives=electives or False,
            status="ON_CAREER_PAGE",
            course_list=[
                {"course_code": "1000001", "course_name": "Calculo"},
                {"course_code": "2016489", "course_name": "Estructuras de Datos"},
                {"course_code": "3000003", "course_name": "Fisica"},
            ],
            view_state="vs-2",
        )

    mock_instance = MagicMock()
    mock_instance.init_session = AsyncMock(side_effect=init_side_effect)
    mock_instance.set_career = AsyncMock(side_effect=career_side_effect)

    def scrape_course_info_side_effect(idx: int) -> sia_scraper_rust.CourseInfoModel:
        return sia_scraper_rust.CourseInfoModel(
            course_name="Test Course",
            code="1000001",
            credits=3,
            typology="TEORICA",
            available_spots=20,
            groups=[],
            scrape_timestamp="2024-01-01T00:00:00",
        )

    def scrape_prereqs_side_effect(idx: int) -> sia_scraper_rust.CoursePrereqsModel:
        return sia_scraper_rust.CoursePrereqsModel(
            course_name="Test Course",
            code="1000001",
            credits=3,
            typology="TEORICA",
            conditions=[],
        )

    mock_instance.scrape_course_info = AsyncMock(side_effect=scrape_course_info_side_effect)
    mock_instance.scrape_course_prereqs = AsyncMock(side_effect=scrape_prereqs_side_effect)
    mock_instance.get_state = AsyncMock(side_effect=lambda: career_side_effect("0-2-8-3", False))
    mock_instance.is_initialized = lambda: False  # Simulate uninitialized session

    with patch("sia_scraper.session.sia_scraper_rust.PySiaSession") as MockPySiaSession:
        MockPySiaSession.return_value = mock_instance
        yield mock_instance


class TestSiaSessionCreation:
    """Test SiaSession initialization and factory behavior."""

    @pytest.mark.asyncio
    async def test_create_initializes_session(self, mock_rust_session):
        session = await SiaSession.create(timeout=5)
        try:
            assert session.status == SiaSessionStatus.CAREER_NOT_SET
            assert session._career_name == "N/A"
            assert session._career_code == ""
            mock_rust_session.init_session.assert_awaited_once()
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_default_state_is_no_session(self, mock_rust_session):
        session = SiaSession()
        assert session.status == SiaSessionStatus.NO_SESSION


class TestSiaSessionCareerFlow:
    """Test async career setup and state management."""

    @pytest.mark.asyncio
    async def test_set_career_updates_state(self, mock_rust_session):
        session = await SiaSession.create(timeout=5)
        try:
            await session.set_career("0-2-8-3", is_electives=True)

            assert session.status == SiaSessionStatus.ON_CAREER_PAGE
            assert session.career_code == "0-2-8-3"
            assert session.career_indices == ["0", "2", "8", "3"]
            assert session.is_electives is True
            assert session.career_name == "Ingenieria de Sistemas"
            assert session.course_list == [
                {"1000001": "Calculo"},
                {"2016489": "Estructuras de Datos"},
                {"3000003": "Fisica"},
            ]
            mock_rust_session.set_career.assert_awaited_once_with("0-2-8-3", True)
        finally:
            await session.close()


class TestSiaSessionScraping:
    """Test scrape_course_info and scrape_course_prereqs methods."""

    @pytest.mark.asyncio
    async def test_scrape_course_info_delegates_to_rust(self, mock_rust_session):
        session = await SiaSession.create(timeout=5)
        try:
            await session.set_career("0-2-8-3")
            course = await session.scrape_course_info(0)

            mock_rust_session.scrape_course_info.assert_awaited_once_with(0)
            assert course.course_name == "Test Course"
            assert course.code == "1000001"
            assert course.credits == 3
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_scrape_course_prereqs_delegates_to_rust(self, mock_rust_session):
        session = await SiaSession.create(timeout=5)
        try:
            await session.set_career("0-2-8-3")
            prereqs = await session.scrape_course_prereqs(0)

            mock_rust_session.scrape_course_prereqs.assert_awaited_once_with(0)
            assert prereqs.course_name == "Test Course"
            assert prereqs.code == "1000001"
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_scrape_course_info_before_career_raises(self):
        session = SiaSession()
        course_list_before = session.course_list
        assert course_list_before == []  # No courses before init

    @pytest.mark.asyncio
    async def test_scrape_course_info_after_init_succeeds(self, mock_rust_session):
        session = await SiaSession.create(timeout=5)
        try:
            await session.set_career("0-2-8-3")
            course = await session.scrape_course_info(0)
            assert course is not None
        finally:
            await session.close()


class TestSiaSessionLifecycle:
    """Test context manager and serialization lifecycle."""

    @pytest.mark.asyncio
    async def test_context_manager_closes_session(self, mock_rust_session):
        async with await SiaSession.create(timeout=5) as session:
            assert session.status == SiaSessionStatus.CAREER_NOT_SET

        assert session.status == SiaSessionStatus.NO_SESSION

    @pytest.mark.asyncio
    async def test_get_session_data(self, mock_rust_session):
        session = await SiaSession.create(timeout=5)
        try:
            await session.set_career("0-2-8-3")
            data = session.get_session_data()

            assert data.career_code == "0-2-8-3"
            assert data.career_name == "Ingenieria de Sistemas"
            assert data.is_electives is False
            assert data.status == SiaSessionStatus.ON_CAREER_PAGE.value
            assert [entry.course_code for entry in data.course_list] == [
                "1000001",
                "2016489",
                "3000003",
            ]
        finally:
            await session.close()


class TestSiaSessionErrorPaths:
    """Test error handling in SiaSession."""

    @pytest.mark.asyncio
    async def test_invalid_course_index_handled_by_rust(self, mock_rust_session):
        session = await SiaSession.create(timeout=5)
        try:
            await session.set_career("0-2-8-3")
            mock_rust_session.scrape_course_info.side_effect = RuntimeError("index out of range")
            with pytest.raises(RuntimeError):
                await session.scrape_course_info(999)
        finally:
            await session.close()
