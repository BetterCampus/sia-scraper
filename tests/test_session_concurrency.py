"""Tests for SiaSession concurrency guard.

Verifies that concurrent access to SiaSession raises ConcurrentAccessError
and that sequential operations work correctly.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from sia_scraper.core.exceptions import ConcurrentAccessError
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


class TestConcurrentAccessDetection:
    """Test that concurrent operations are detected and rejected."""

    @pytest.mark.asyncio
    async def test_concurrent_set_career_raises_error(self, mock_rust_module):
        """Two concurrent set_career calls should raise ConcurrentAccessError."""
        session = await SiaSession.create()

        try:

            async def slow_set_career(*args):
                await asyncio.sleep(0.1)
                return {
                    "career_name": "Test Career",
                    "course_list": [],
                    "javax_faces_ViewState": "vs-3",
                }

            mock_rust_module.set_career.side_effect = slow_set_career

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
    async def test_concurrent_get_course_xml_raises_error(self, mock_rust_module):
        """Two concurrent get_course_xml calls should raise error."""
        session = await SiaSession.create()
        await session.set_career("0-2-8-3")

        try:

            async def slow_get_course(*args):
                await asyncio.sleep(0.1)
                return "<xml>test</xml>"

            mock_rust_module.get_course_xml.side_effect = slow_get_course

            task1 = asyncio.create_task(session.get_course_xml(0))
            await asyncio.sleep(0.01)

            with pytest.raises(ConcurrentAccessError) as exc_info:
                await session.get_course_xml(1)

            assert exc_info.value.active_operation == "get_course_xml"
            assert exc_info.value.attempted_operation == "get_course_xml"

            await task1
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_mixed_concurrent_operations_raises_error(self, mock_rust_module):
        """set_career during get_course_xml should raise error."""
        session = await SiaSession.create()
        await session.set_career("0-2-8-3")

        try:

            async def slow_get_course(*args):
                await asyncio.sleep(0.1)
                return "<xml>test</xml>"

            mock_rust_module.get_course_xml.side_effect = slow_get_course

            task1 = asyncio.create_task(session.get_course_xml(0))
            await asyncio.sleep(0.01)

            with pytest.raises(ConcurrentAccessError) as exc_info:
                await session.set_career("1-2-3-4")

            assert exc_info.value.active_operation == "get_course_xml"
            assert exc_info.value.attempted_operation == "set_career"

            await task1
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_concurrent_init_session_raises_error(self, mock_rust_module):
        """Two concurrent init_session calls should raise error."""
        session = SiaSession()

        async def slow_init(*args):
            await asyncio.sleep(0.1)
            return {"javax_faces_ViewState": "test"}

        mock_rust_module.init_sia_session.side_effect = slow_init

        task1 = asyncio.create_task(session.init_session())
        await asyncio.sleep(0.01)

        with pytest.raises(ConcurrentAccessError):
            await session.init_session()

        await task1

    @pytest.mark.asyncio
    async def test_concurrent_close_raises_error(self, mock_rust_module):
        """close during get_course_xml should raise error."""
        session = await SiaSession.create()
        await session.set_career("0-2-8-3")

        try:

            async def slow_get_course(*args):
                await asyncio.sleep(0.1)
                return "<xml>test</xml>"

            mock_rust_module.get_course_xml.side_effect = slow_get_course

            task1 = asyncio.create_task(session.get_course_xml(0))
            await asyncio.sleep(0.01)

            with pytest.raises(ConcurrentAccessError) as exc_info:
                await session.close()

            assert exc_info.value.active_operation == "get_course_xml"
            assert exc_info.value.attempted_operation == "close"

            await task1
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_concurrent_init_during_set_career_raises_error(self, mock_rust_module):
        """init_session during set_career should raise error."""
        session = SiaSession()

        async def slow_set_career(*args):
            await asyncio.sleep(0.1)
            return {
                "career_name": "Test",
                "course_list": [],
                "javax_faces_ViewState": "vs",
            }

        mock_rust_module.set_career.side_effect = slow_set_career

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
    async def test_sequential_set_career_works(self, mock_rust_module):
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
    async def test_sequential_get_course_xml_works(self, mock_rust_module):
        """Sequential get_course_xml calls should work normally."""
        session = await SiaSession.create()
        await session.set_career("0-2-8-3")

        try:
            xml1 = await session.get_course_xml(0)
            xml2 = await session.get_course_xml(1)

            assert xml1 is not None
            assert xml2 is not None
            assert isinstance(xml1, str)
            assert isinstance(xml2, str)
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_operation_guard_releases_on_exception(self, mock_rust_module):
        """Guard should release if operation raises exception."""
        session = await SiaSession.create()

        try:
            mock_rust_module.set_career.side_effect = RuntimeError("Simulated error")

            with pytest.raises(RuntimeError):
                await session.set_career("0-2-8-3")

            mock_rust_module.set_career.side_effect = {
                "career_name": "Test",
                "course_list": [],
                "javax_faces_ViewState": "vs",
            }

            await session.set_career("1-2-3-4")
            assert session.career_code == "1-2-3-4"
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_multiple_sessions_can_run_concurrently(self, mock_rust_module):
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
    async def test_operation_guard_releases_on_success(self, mock_rust_module):
        """Guard should release after successful operation."""
        session = await SiaSession.create()

        try:
            await session.set_career("0-2-8-3")
            assert session._active_operation is None

            xml = await session.get_course_xml(0)
            assert session._active_operation is None
            assert xml == "<xml>course</xml>"
        finally:
            await session.close()
