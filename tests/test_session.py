"""Unit tests for Rust-backed async session wrapper."""

from unittest.mock import AsyncMock, patch

import pytest

import sia_scraper_rust
from sia_scraper.constants import SiaSessionStatus
from sia_scraper.core import SiaSessionException
from sia_scraper.session import SiaSession


@pytest.fixture
def mock_rust_module():
    """Patch Rust extension calls used by SiaSession."""

    def init_payload(timeout: int) -> sia_scraper_rust.SessionStateModel:
        return _make_state_model(
            career_code="",
            career_name="N/A",
            is_electives=False,
            status="CAREER_NOT_SET",
            course_list=[],
            view_state="vs-1",
        )

    def career_payload(
        timeout: int, search_code: str, is_electives: bool
    ) -> sia_scraper_rust.SessionStateModel:
        return _make_state_model(
            career_code=search_code,
            career_name="Ingenieria de Sistemas",
            is_electives=is_electives,
            status="ON_CAREER_PAGE",
            course_list=[
                {"course_code": "1000001", "course_name": "Calculo"},
                {"course_code": "2016489", "course_name": "Estructuras de Datos"},
                {"course_code": "3000003", "course_name": "Fisica"},
            ],
            view_state="vs-2",
        )

    with patch("sia_scraper.session.sia_scraper_rust") as rust:
        rust.init_sia_session = AsyncMock(side_effect=init_payload)
        rust.set_career = AsyncMock(side_effect=career_payload)
        rust.get_course_xml = AsyncMock(return_value="<xml>course</xml>")
        yield rust


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


class TestSiaSessionCreation:
    """Test SiaSession initialization and factory behavior."""

    @pytest.mark.asyncio
    async def test_create_initializes_session(self, mock_rust_module):
        session = await SiaSession.create(timeout=5)
        try:
            assert session.status == SiaSessionStatus.CAREER_NOT_SET
            assert session._session_state.javax_faces_ViewState == "vs-1"
            mock_rust_module.init_sia_session.assert_awaited_once_with(5)
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_default_state_is_no_session(self, mock_rust_module):
        session = SiaSession()
        assert session.status == SiaSessionStatus.NO_SESSION


class TestSiaSessionCareerFlow:
    """Test async career setup and XML retrieval behavior."""

    @pytest.mark.asyncio
    async def test_set_career_updates_state(self, mock_rust_module):
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
            assert session._session_state.javax_faces_ViewState == "vs-2"
            mock_rust_module.set_career.assert_awaited_once_with(5, "0-2-8-3", True)
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_get_course_xml_passes_electives_flag(self, mock_rust_module):
        session = await SiaSession.create(timeout=5)
        try:
            await session.set_career("0-2-8-3", is_electives=True)
            xml = await session.get_course_xml(2)

            assert xml == "<xml>course</xml>"
            mock_rust_module.get_course_xml.assert_awaited_once_with(
                5,
                2,
                ["0", "2", "8", "3"],
                True,
            )
        finally:
            await session.close()


class TestSiaSessionLifecycle:
    """Test context manager and serialization lifecycle."""

    @pytest.mark.asyncio
    async def test_context_manager_closes_session(self, mock_rust_module):
        async with await SiaSession.create(timeout=5) as session:
            assert session.status == SiaSessionStatus.CAREER_NOT_SET

        assert session.status == SiaSessionStatus.NO_SESSION

    @pytest.mark.asyncio
    async def test_get_session_data(self, mock_rust_module):
        session = await SiaSession.create(timeout=5)
        try:
            await session.set_career("0-2-8-3")
            data = session.get_session_data()

            assert data.career_code == "0-2-8-3"
            assert data.career_name == "Ingenieria de Sistemas"
            assert data.is_electives is False
            assert data.status == SiaSessionStatus.ON_CAREER_PAGE.value
            assert data.javax_faces_view_state == "vs-2"
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
    async def test_get_course_xml_raises_invalid_status(self, mock_rust_module):
        session = SiaSession()
        assert session.status == SiaSessionStatus.NO_SESSION

        with pytest.raises(SiaSessionException.InvalidStatus):
            await session.get_course_xml(0)

    @pytest.mark.asyncio
    async def test_get_course_xml_raises_index_out_of_range(self, mock_rust_module):
        session = await SiaSession.create(timeout=5)
        try:
            await session.set_career("0-2-8-3", is_electives=True)
            # course_list has 3 items, index 10 is out of range
            with pytest.raises(ValueError, match="Course index 10 out of range"):
                await session.get_course_xml(10)
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_get_course_xml_raises_negative_index(self, mock_rust_module):
        session = await SiaSession.create(timeout=5)
        try:
            await session.set_career("0-2-8-3", is_electives=True)
            with pytest.raises(ValueError, match="Course index -1 out of range"):
                await session.get_course_xml(-1)
        finally:
            await session.close()
