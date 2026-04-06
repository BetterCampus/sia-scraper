"""Tests for SiaSession concurrency guard.

Verifies that concurrent access to SiaSession raises ConcurrentAccessError
and that sequential operations work correctly.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import sia_scraper_rust
from sia_scraper.core.exceptions import ConcurrentAccessError, SiaSessionException
from sia_scraper.session import SiaSession


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
        params={"Adf-Page-Id": "0", "Adf-Window-Id": "win-1"},
        career_code=career_code,
        career_name=career_name,
        is_electives=is_electives,
        status=status,
        course_list=entries,
        javax_faces_view_state=view_state,
    )


def _make_course_info_model() -> sia_scraper_rust.CourseInfoModel:
    """Create a CourseInfoModel for testing."""
    return sia_scraper_rust.CourseInfoModel(
        course_name="Test Course",
        code="1000001",
        credits=3,
        typology="TEORICA",
        available_spots=20,
        groups=[],
        scrape_timestamp="2024-01-01T00:00:00",
    )


@pytest.fixture
def mock_rust_session():
    """Mock PySiaSession for unit testing."""

    def init_side_effect() -> sia_scraper_rust.SessionStateModel:
        return _make_state_model(
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
        return _make_state_model(
            career_code=search_code,
            career_name="Ingenieria de Sistemas",
            is_electives=electives or False,
            status="ON_CAREER_PAGE",
            course_list=[
                {"code": "1000001", "name": "Calculo"},
                {"code": "2016489", "name": "Estructuras de Datos"},
                {"code": "3000003", "name": "Fisica"},
            ],
            view_state="vs-2",
        )

    mock_instance = MagicMock()
    mock_instance.init_session = AsyncMock(side_effect=init_side_effect)
    mock_instance.set_career = AsyncMock(side_effect=career_side_effect)
    mock_instance.scrape_course_info = AsyncMock(return_value=_make_course_info_model())
    mock_instance.scrape_course_prereqs = AsyncMock(
        return_value=sia_scraper_rust.CoursePrereqsModel(
            course_name="Test Course",
            code="1000001",
            credits=3,
            typology="TEORICA",
            conditions=[],
        )
    )
    mock_instance.get_state = AsyncMock(side_effect=lambda: career_side_effect("0-2-8-3", False))
    mock_instance.is_initialized = lambda: False

    with patch("sia_scraper.session.sia_scraper_rust.PySiaSession") as MockPySiaSession:
        MockPySiaSession.return_value = mock_instance
        yield mock_instance


class TestConcurrentAccessDetection:
    """Test that concurrent operations are detected and rejected."""

    @pytest.mark.asyncio
    async def test_concurrent_set_career_raises_error(self, mock_rust_session):
        """Two concurrent set_career calls should raise ConcurrentAccessError."""
        session = await SiaSession.create()

        try:

            async def slow_set_career(*args) -> sia_scraper_rust.SessionStateModel:
                await asyncio.sleep(0.1)
                return _make_state_model(
                    career_code="0-2-8-3",
                    career_name="Test Career",
                    is_electives=False,
                    status="ON_CAREER_PAGE",
                    course_list=[],
                    view_state="vs-3",
                )

            mock_rust_session.set_career.side_effect = slow_set_career

            task1 = asyncio.create_task(session.set_career("0-2-8-3"))
            await asyncio.sleep(0.01)

            with pytest.raises(ConcurrentAccessError) as exc_info:
                await session.set_career("1-2-3-4")

            assert exc_info.value.active_operation == "set_career"
            assert exc_info.value.attempted_operation == "set_career"
            assert "set_career" in str(exc_info.value)
            assert "must be called sequentially" in str(exc_info.value)

            await task1
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_concurrent_scrape_course_info_raises_error(self, mock_rust_session):
        """Two concurrent scrape_course_info calls should raise error."""
        session = await SiaSession.create()
        await session.set_career("0-2-8-3")

        try:

            async def slow_scrape_course(*args):
                await asyncio.sleep(0.1)
                return _make_course_info_model()

            mock_rust_session.scrape_course_info.side_effect = slow_scrape_course

            task1 = asyncio.create_task(session.scrape_course_info(0))
            await asyncio.sleep(0.01)

            with pytest.raises(ConcurrentAccessError) as exc_info:
                await session.scrape_course_info(1)

            assert exc_info.value.active_operation == "scrape_course_info"
            assert exc_info.value.attempted_operation == "scrape_course_info"

            await task1
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_mixed_concurrent_operations_raises_error(self, mock_rust_session):
        """set_career during scrape_course_info should raise error."""
        session = await SiaSession.create()
        await session.set_career("0-2-8-3")

        try:

            async def slow_scrape_course(*args):
                await asyncio.sleep(0.1)
                return _make_course_info_model()

            mock_rust_session.scrape_course_info.side_effect = slow_scrape_course

            task1 = asyncio.create_task(session.scrape_course_info(0))
            await asyncio.sleep(0.01)

            with pytest.raises(ConcurrentAccessError) as exc_info:
                await session.set_career("1-2-3-4")

            assert exc_info.value.active_operation == "scrape_course_info"
            assert exc_info.value.attempted_operation == "set_career"

            await task1
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_concurrent_init_session_raises_error(self, mock_rust_session):
        """Two concurrent init_session calls should raise error."""
        session = SiaSession()

        async def slow_init(*args) -> sia_scraper_rust.SessionStateModel:
            await asyncio.sleep(0.1)
            return _make_state_model(
                career_code="",
                career_name="N/A",
                is_electives=False,
                status="CAREER_NOT_SET",
                course_list=[],
                view_state="test",
            )

        mock_rust_session.init_session.side_effect = slow_init

        task1 = asyncio.create_task(session.init_session())
        await asyncio.sleep(0.01)

        with pytest.raises(ConcurrentAccessError):
            await session.init_session()

        await task1

    @pytest.mark.asyncio
    async def test_concurrent_close_raises_error(self, mock_rust_session):
        """close during scrape_course_info should raise error."""
        session = await SiaSession.create()
        await session.set_career("0-2-8-3")

        try:

            async def slow_scrape_course(*args):
                await asyncio.sleep(0.1)
                return _make_course_info_model()

            mock_rust_session.scrape_course_info.side_effect = slow_scrape_course

            task1 = asyncio.create_task(session.scrape_course_info(0))
            await asyncio.sleep(0.01)

            with pytest.raises(ConcurrentAccessError) as exc_info:
                await session.close()

            assert exc_info.value.active_operation == "scrape_course_info"
            assert exc_info.value.attempted_operation == "close"

            await task1
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_concurrent_init_during_set_career_raises_error(self, mock_rust_session):
        """init_session during set_career should raise error."""
        session = SiaSession()

        async def slow_set_career(*args) -> sia_scraper_rust.SessionStateModel:
            await asyncio.sleep(0.1)
            return _make_state_model(
                career_code="0-2-8-3",
                career_name="Test",
                is_electives=False,
                status="ON_CAREER_PAGE",
                course_list=[],
                view_state="vs",
            )

        mock_rust_session.set_career.side_effect = slow_set_career

        await session.init_session()

        task1 = asyncio.create_task(session.set_career("0-2-8-3"))
        await asyncio.sleep(0.01)

        with pytest.raises(ConcurrentAccessError) as exc_info:
            await session.init_session()

        assert exc_info.value.active_operation == "set_career"
        assert exc_info.value.attempted_operation == "init_session"

        await task1


class TestSequentialOperationsStillWork:
    """Verify that sequential operations are not affected by the guard."""

    @pytest.mark.asyncio
    async def test_sequential_set_career_works(self, mock_rust_session):
        """Sequential set_career calls should work normally."""
        session = await SiaSession.create()

        try:
            await session.set_career("0-2-8-3")
            assert session.career_code == "0-2-8-3"

            await session.set_career("1-2-3-4")
            assert session.career_code == "1-2-3-4"
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_sequential_scrape_course_info_works(self, mock_rust_session):
        """Sequential scrape_course_info calls should work normally."""
        session = await SiaSession.create()
        await session.set_career("0-2-8-3")

        try:
            course1 = await session.scrape_course_info(0)
            course2 = await session.scrape_course_info(1)

            assert course1 is not None
            assert course2 is not None
            assert isinstance(course1, sia_scraper_rust.CourseInfoModel)
            assert isinstance(course2, sia_scraper_rust.CourseInfoModel)
            assert course1.course_name == "Test Course"
            assert course2.course_name == "Test Course"
            assert course1.code == "1000001"
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_operation_guard_releases_on_exception(self, mock_rust_session):
        """Guard should release if operation raises exception."""
        session = await SiaSession.create()

        try:
            mock_rust_session.set_career.side_effect = sia_scraper_rust.NetworkError(
                "Simulated error"
            )

            with pytest.raises(SiaSessionException, match="Simulated error") as exc_info:
                await session.set_career("0-2-8-3")
            assert type(exc_info.value) is SiaSessionException

            mock_rust_session.set_career.side_effect = None
            mock_rust_session.set_career.return_value = _make_state_model(
                career_code="1-2-3-4",
                career_name="Test",
                is_electives=False,
                status="ON_CAREER_PAGE",
                course_list=[],
                view_state="vs",
            )

            await session.set_career("1-2-3-4")
            assert session.career_code == "1-2-3-4"
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_multiple_sessions_can_run_concurrently(self, mock_rust_session):
        """Different session instances CAN run concurrently."""
        session1 = await SiaSession.create()
        session2 = await SiaSession.create()

        try:
            await asyncio.gather(
                session1.set_career("0-2-8-3"),
                session2.set_career("1-2-3-4"),
            )

            assert session1.career_code == "0-2-8-3"
            assert session2.career_code == "1-2-3-4"
        finally:
            await session1.close()
            await session2.close()

    @pytest.mark.asyncio
    async def test_operation_guard_releases_on_success(self, mock_rust_session):
        """Guard should release after successful operation."""
        session = await SiaSession.create()

        try:
            await session.set_career("0-2-8-3")
            assert session._active_operation is None

            course = await session.scrape_course_info(0)
            assert session._active_operation is None
            assert isinstance(course, sia_scraper_rust.CourseInfoModel)
            assert course.course_name == "Test Course"
        finally:
            await session.close()
