"""Unit tests for Rust-backed async session wrapper."""

from unittest.mock import AsyncMock, patch

import pytest

from sia_scraper.constants import SiaSessionStatus
from sia_scraper.session import SiaSession


@pytest.fixture
def mock_rust_module():
    """Patch Rust extension calls used by SiaSession."""
    with patch("sia_scraper.session.sia_scraper_rust") as rust:
        rust.init_sia_session = AsyncMock(return_value={"javax_faces_ViewState": "vs-1"})
        rust.set_career = AsyncMock(
            return_value={
                "career_name": "Ingenieria de Sistemas",
                "course_list": [
                    {"1000001": "Calculo"},
                    {"2016489": "Estructuras de Datos"},
                    {"3000003": "Fisica"},
                ],
                "javax_faces_ViewState": "vs-2",
            }
        )
        rust.get_course_xml = AsyncMock(return_value="<xml>course</xml>")
        yield rust


class TestSiaSessionCreation:
    """Test SiaSession initialization and factory behavior."""

    @pytest.mark.asyncio
    async def test_create_initializes_session(self, mock_rust_module):
        session = await SiaSession.create(timeout=5)
        try:
            assert session.status == SiaSessionStatus.CAREER_NOT_SET
            assert session._session_state.get("javax_faces_ViewState") == "vs-1"
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
            assert session._session_state.get("javax_faces_ViewState") == "vs-2"
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
            assert data.javax_faces_ViewState == "vs-2"
        finally:
            await session.close()
