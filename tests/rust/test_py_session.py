"""Integration tests for PySiaSession PyO3 class."""

import pickle

import pytest

sia_scraper_rust = pytest.importorskip("sia_scraper_rust")


class TestPySiaSessionCreation:
    """Tests for PySiaSession instantiation."""

    def test_create_session_default_timeout(self) -> None:
        session = sia_scraper_rust.PySiaSession()
        assert session is not None

    def test_create_session_custom_timeout(self) -> None:
        session = sia_scraper_rust.PySiaSession(timeout=30)
        assert session is not None

    def test_repr_includes_timeout(self) -> None:
        session = sia_scraper_rust.PySiaSession(timeout=20)
        repr_str = repr(session)
        assert "PySiaSession" in repr_str
        assert "20" in repr_str


class TestPySiaSessionErrorHandling:
    """Tests for error handling in PySiaSession when not initialized."""

    @pytest.mark.asyncio
    async def test_set_career_before_init_raises(self) -> None:
        session = sia_scraper_rust.PySiaSession()
        with pytest.raises(RuntimeError, match="not initialized"):
            await session.set_career("0-2-8-3")

    @pytest.mark.asyncio
    async def test_scrape_course_info_before_init_raises(self) -> None:
        session = sia_scraper_rust.PySiaSession()
        with pytest.raises(RuntimeError, match="not initialized"):
            await session.scrape_course_info(0)

    @pytest.mark.asyncio
    async def test_scrape_course_prereqs_before_init_raises(self) -> None:
        session = sia_scraper_rust.PySiaSession()
        with pytest.raises(RuntimeError, match="not initialized"):
            await session.scrape_course_prereqs(0)

    @pytest.mark.asyncio
    async def test_get_state_before_init_raises(self) -> None:
        session = sia_scraper_rust.PySiaSession()
        with pytest.raises(RuntimeError, match="not initialized"):
            await session.get_state()

    def test_is_initialized_before_init(self) -> None:
        session = sia_scraper_rust.PySiaSession()
        assert not session.is_initialized()

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires real SIA server access")
    async def test_is_initialized_after_init(self) -> None:
        session = sia_scraper_rust.PySiaSession(timeout=30)
        await session.init_session()
        assert session.is_initialized()


class TestPySiaSessionPickle:
    """Tests for pickle serialization support."""

    def test_pickle_preserves_timeout(self) -> None:
        session = sia_scraper_rust.PySiaSession(timeout=45)
        assert session.timeout == 45
        assert not session.is_initialized()

        pickled = pickle.dumps(session)
        restored = pickle.loads(pickled)

        assert restored.timeout == 45
        assert not restored.is_initialized()
        assert "45" in repr(restored)

    def test_pickle_default_timeout(self) -> None:
        session = sia_scraper_rust.PySiaSession()
        pickled = pickle.dumps(session)
        restored = pickle.loads(pickled)

        assert restored.timeout == 15


class TestPySiaSessionTypeHints:
    """Tests that type hints work correctly with PySiaSession."""

    def test_type_hint_imports(self) -> None:
        """Verify that all types can be imported."""
        from sia_scraper_rust import (
            CourseInfoModel,
            CoursePrereqsModel,
            PySiaSession,
            SessionStateModel,
        )

        assert PySiaSession is not None
        assert SessionStateModel is not None
        assert CourseInfoModel is not None
        assert CoursePrereqsModel is not None

    def test_type_hint_return_types(self) -> None:
        """Verify that type hints are correct."""
        session = sia_scraper_rust.PySiaSession()

        # Verify method signatures exist
        assert hasattr(session, "init_session")
        assert hasattr(session, "set_career")
        assert hasattr(session, "scrape_course_info")
        assert hasattr(session, "scrape_course_prereqs")
        assert hasattr(session, "get_state")
        assert hasattr(session, "is_initialized")
        assert hasattr(session, "__aenter__")
        assert hasattr(session, "__aexit__")


class TestPySiaSessionTimeoutProperty:
    """Tests for timeout property getter."""

    def test_timeout_property_custom(self) -> None:
        session = sia_scraper_rust.PySiaSession(timeout=25)
        assert session.timeout == 25

    def test_timeout_property_default(self) -> None:
        session = sia_scraper_rust.PySiaSession()
        assert session.timeout == 15


class TestPySiaSessionContextManager:
    """Tests for async context manager support."""

    def test_context_manager_methods_exist(self) -> None:
        session = sia_scraper_rust.PySiaSession()
        assert callable(session.__aenter__)
        assert callable(session.__aexit__)


@pytest.mark.integration
class TestPySiaSessionIntegration:
    """Integration tests that hit the real SIA server.

    These tests require network access to SIA and are skipped by default.
    Run with: pytest -m integration tests/rust/test_py_session.py
    """

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires real SIA server access")
    async def test_init_session_real_sia(self) -> None:
        """Test init_session with real SIA server."""
        session = sia_scraper_rust.PySiaSession(timeout=30)
        state = await session.init_session()
        assert state is not None
        assert state.status == "SESSION_SET"

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires real SIA server access")
    async def test_full_workflow_real_sia(self) -> None:
        """Test complete workflow: init -> set_career -> scrape course."""
        session = sia_scraper_rust.PySiaSession(timeout=30)

        # Initialize session
        await session.init_session()

        # Set career
        state = await session.set_career("0-2-8-3")
        assert state.career_code == "0-2-8-3"
        assert len(state.course_list) > 0

        # Scrape first course
        course = await session.scrape_course_info(0)
        assert course is not None
        assert course.course_name is not None
        assert course.credits > 0

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires real SIA server access")
    async def test_scrape_prereqs_real_sia(self) -> None:
        """Test scraping prerequisites from real SIA."""
        session = sia_scraper_rust.PySiaSession(timeout=30)

        await session.init_session()
        await session.set_career("0-2-8-3")

        prereqs = await session.scrape_course_prereqs(0)
        assert prereqs is not None
        assert prereqs.course_name is not None
