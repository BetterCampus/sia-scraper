"""Async session integration tests."""

import pytest

from sia_scraper.constants import SiaSessionStatus
from sia_scraper.session_async import SiaSessionAsync


class TestSiaSessionAsyncCreation:
    """Test SiaSessionAsync initialization."""

    def test_create_class_method_exists(self):
        assert hasattr(SiaSessionAsync, "create")

    @pytest.mark.asyncio
    async def test_create_initializes_session(self):
        session = await SiaSessionAsync.create(timeout=5)
        try:
            assert session._STATUS == SiaSessionStatus.CAREER_NOT_SET
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_create_with_custom_timeout(self):
        session = await SiaSessionAsync.create(timeout=10)
        try:
            assert session._timeout == 10
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_default_timeout_value(self):
        session = await SiaSessionAsync.create(timeout=5)
        try:
            assert session._timeout == 5
        finally:
            await session.close()


class TestSiaSessionAsyncStateTransitions:
    """Test session state transitions."""

    @pytest.mark.asyncio
    async def test_initial_state_is_no_session(self):
        session = SiaSessionAsync()
        assert session.STATUS == SiaSessionStatus.NO_SESSION

    @pytest.mark.asyncio
    async def test_after_init_session_state(self):
        session = await SiaSessionAsync.create(timeout=5)
        try:
            assert session.STATUS == SiaSessionStatus.CAREER_NOT_SET
            assert session.career_code == ""
            assert session.career_name == "N/A"
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_after_set_career_state(self):
        session = await SiaSessionAsync.create(timeout=5)
        try:
            await session.set_career("0-2-8-3")
            assert session.STATUS == SiaSessionStatus.ON_CAREER_PAGE
            assert session.career_code == "0-2-8-3"
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_after_close_state(self):
        session = await SiaSessionAsync.create(timeout=5)
        await session.close()
        assert session.STATUS == SiaSessionStatus.NO_SESSION


class TestSiaSessionAsyncContextManager:
    """Test context manager support."""

    @pytest.mark.asyncio
    async def test_context_manager_enters(self):
        async with await SiaSessionAsync.create(timeout=5) as session:
            assert session.STATUS == SiaSessionStatus.CAREER_NOT_SET

    @pytest.mark.asyncio
    async def test_context_manager_exits(self):
        async with await SiaSessionAsync.create(timeout=5) as session:
            pass
        assert session.STATUS == SiaSessionStatus.NO_SESSION


class TestSiaSessionAsyncProperties:
    """Test property accessors."""

    @pytest.mark.asyncio
    async def test_career_name_property(self):
        session = await SiaSessionAsync.create(timeout=5)
        try:
            assert session.career_name == "N/A"
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_career_code_property(self):
        session = await SiaSessionAsync.create(timeout=5)
        try:
            assert session.career_code == ""
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_is_electives_property(self):
        session = await SiaSessionAsync.create(timeout=5)
        try:
            assert session.is_electives is False
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_course_list_property(self):
        session = await SiaSessionAsync.create(timeout=5)
        try:
            assert session.course_list == []
        finally:
            await session.close()


class TestSiaSessionAsyncSetCareer:
    """Test set_career method."""

    @pytest.mark.asyncio
    async def test_set_career_with_valid_code(self):
        session = await SiaSessionAsync.create(timeout=5)
        try:
            await session.set_career("0-2-8-3")
            assert session.career_code == "0-2-8-3"
            assert len(session.career_indices) == 4
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_set_career_with_electives(self):
        session = await SiaSessionAsync.create(timeout=5)
        try:
            await session.set_career("0-2-8-3", electives=True)
            assert session.is_electives is True
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_set_career_updates_career_indices(self):
        session = await SiaSessionAsync.create(timeout=5)
        try:
            await session.set_career("1-3-5-2345")
            assert session.career_indices == ["1", "3", "5", "2345"]
        finally:
            await session.close()


class TestSiaSessionAsyncGetSessionData:
    """Test session data serialization."""

    @pytest.mark.asyncio
    async def test_get_session_data_returns_session_state(self):
        session = await SiaSessionAsync.create(timeout=5)
        try:
            data = session.get_session_data()
            assert data is not None
            assert hasattr(data, "career_code")
            assert hasattr(data, "STATUS")
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_get_session_data_after_set_career(self):
        session = await SiaSessionAsync.create(timeout=5)
        try:
            await session.set_career("0-2-8-3")
            data = session.get_session_data()
            assert data.career_code == "0-2-8-3"
        finally:
            await session.close()
