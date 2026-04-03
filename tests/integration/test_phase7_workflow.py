"""Phase 7 integration tests with real SIA server.

These tests validate the unified Rust pipeline by hitting the real SIA server.
They run by default but may fail if SIA is unavailable or experiencing issues.

Run with: pytest tests/integration/test_phase7_workflow.py
Run only integration: pytest -m integration tests/integration/
"""

import pytest

import sia_scraper_rust
from sia_scraper import SiaScraper, SiaSession


@pytest.mark.integration
@pytest.mark.network
class TestPhase7Workflow:
    """Integration tests validating Phase 7 unified Rust pipeline."""

    @pytest.mark.asyncio
    async def test_full_workflow_create_setcareer_scrape(self) -> None:
        """Full workflow: create → set_career → scrape courses.

        Validates:
        - Session initialization
        - Career navigation
        - Course list loading
        - Course info scraping via unified Rust pipeline
        """
        async with await SiaScraper.create(timeout=30) as scraper:
            await scraper.set_career("0-2-8-3")  # Systems Engineering

            assert scraper.career_code == "0-2-8-3"
            assert len(scraper.course_list) > 0, "Expected courses in career"

            # Scrape first 3 courses
            for i in range(min(3, len(scraper.course_list))):
                course = await scraper.get_course_info(i)
                assert isinstance(course, sia_scraper_rust.CourseInfoModel), (
                    f"Expected CourseInfoModel, got {type(course)}"
                )
                assert course.course_name, "Expected non-empty course name"
                assert course.credits >= 0, "Expected non-negative credits"

    @pytest.mark.asyncio
    async def test_scrape_course_info_returns_rust_model(self) -> None:
        """Verify scrape_course_info returns native Rust model (zero-copy)."""
        async with await SiaScraper.create(timeout=30) as scraper:
            await scraper.set_career("0-2-8-3")

            course = await scraper.get_course_info(0)

            # Verify Rust model properties
            assert hasattr(course, "course_name")
            assert hasattr(course, "credits")
            assert hasattr(course, "typology")
            assert hasattr(course, "available_spots")
            assert hasattr(course, "groups")
            assert hasattr(course, "scrape_timestamp")
            assert hasattr(course, "code")

            # Verify groups are also Rust models
            if course.groups:
                group = course.groups[0]
                assert hasattr(group, "group_name")
                assert hasattr(group, "teacher")
                assert hasattr(group, "schedules")

    @pytest.mark.asyncio
    async def test_scrape_prereqs_returns_rust_model(self) -> None:
        """Verify scrape_course_prereqs returns native Rust model."""
        async with await SiaScraper.create(timeout=30) as scraper:
            await scraper.set_career("0-2-8-3")

            prereqs = await scraper.get_course_prereqs(0)

            assert isinstance(prereqs, sia_scraper_rust.CoursePrereqsModel), (
                f"Expected CoursePrereqsModel, got {type(prereqs)}"
            )
            assert prereqs.course_name, "Expected non-empty course name"
            assert prereqs.credits >= 0
            assert isinstance(prereqs.conditions, list)

            # Verify condition structure
            for cond in prereqs.conditions:
                assert hasattr(cond, "condition")
                assert hasattr(cond, "prereq_type")
                assert hasattr(cond, "all_required")
                assert hasattr(cond, "number_of_courses")
                assert hasattr(cond, "prerequisites")

    @pytest.mark.asyncio
    async def test_scrape_multiple_courses_sequential(self) -> None:
        """Test sequential scraping of multiple courses."""
        async with await SiaScraper.create(timeout=30) as scraper:
            await scraper.set_career("0-2-8-3")

            num_courses = min(5, len(scraper.course_list))
            scraped_courses = []

            for i in range(num_courses):
                course = await scraper.get_course_info(i)
                scraped_courses.append(course)

            assert len(scraped_courses) == num_courses
            # Verify all have valid data
            for course in scraped_courses:
                assert course.course_name
                assert course.credits >= 0

    @pytest.mark.asyncio
    async def test_scrape_course_by_code(self) -> None:
        """Test scraping course by code instead of index."""
        async with await SiaScraper.create(timeout=30) as scraper:
            await scraper.set_career("0-2-8-3")

            # Get first course code from course list
            first_course = scraper.course_list[0]
            first_code = list(first_course.keys())[0]

            # Scrape by code
            course = await scraper.get_course_info(course_code=first_code)
            assert course is not None
            assert course.code == first_code


@pytest.mark.integration
@pytest.mark.network
class TestPhase7SessionPersistence:
    """Test session state persistence using unified Rust pipeline."""

    @pytest.mark.asyncio
    async def test_get_session_data_returns_dict(self) -> None:
        """Verify get_session_data returns expected dict structure."""
        async with await SiaScraper.create(timeout=30) as scraper:
            await scraper.set_career("0-2-8-3")

            data = await scraper.get_session_data()

            assert isinstance(data, dict), "Expected dict from get_session_data"
            assert "state_dict" in data, "Expected state_dict key"
            assert "timeout" in data, "Expected timeout key"

            state_dict = data["state_dict"]
            assert state_dict["career_code"] == "0-2-8-3"
            assert len(state_dict["course_list"]) > 0

    @pytest.mark.asyncio
    async def test_session_pickle_roundtrip(self) -> None:
        """Test pickle serialization of session state."""
        # Create and populate session
        session1 = await SiaSession.create(timeout=30)
        await session1.set_career("0-2-8-3")

        state = await session1.get_session_data()
        await session1.close()

        # Restore from state
        session2 = await SiaSession.from_state(state)

        try:
            assert session2.career_code == "0-2-8-3"
            assert len(session2.course_list) > 0

            # Verify can continue using restored session
            course = await session2.scrape_course_info(0)
            assert course is not None
            assert course.course_name
        finally:
            await session2.close()

    @pytest.mark.asyncio
    async def test_session_state_contains_http_state(self) -> None:
        """Verify session state includes HTTP headers and cookies."""
        async with await SiaScraper.create(timeout=30) as scraper:
            await scraper.set_career("0-2-8-3")

            data = await scraper.get_session_data()
            state_dict = data["state_dict"]

            # Verify HTTP state is preserved
            assert "session_headers" in state_dict
            assert "session_cookies" in state_dict
            assert "params" in state_dict
            assert "javax_faces_view_state" in state_dict


@pytest.mark.integration
@pytest.mark.network
class TestPhase7ErrorHandling:
    """Test error handling with real SIA server."""

    @pytest.mark.asyncio
    async def test_error_invalid_career_code(self) -> None:
        """Test error handling for invalid career code."""
        async with await SiaScraper.create(timeout=30) as scraper:
            with pytest.raises((RuntimeError, sia_scraper_rust.HttpStatusError)):
                await scraper.set_career("9-9-9-9")

    @pytest.mark.asyncio
    async def test_error_out_of_range_course_index(self) -> None:
        """Test error handling for out-of-range course index."""
        async with await SiaScraper.create(timeout=30) as scraper:
            await scraper.set_career("0-2-8-3")

            # Get valid range
            course_count = len(scraper.course_list)

            with pytest.raises(
                (RuntimeError, ValueError),
                match="out of range|invalid index|negative|Invalid input",
            ):
                await scraper.get_course_info(course_count + 100)

    @pytest.mark.asyncio
    async def test_error_before_set_career(self) -> None:
        """Test that scraping before set_career raises appropriate error."""
        async with await SiaScraper.create(timeout=30) as scraper:
            with pytest.raises(
                (RuntimeError, ValueError, sia_scraper_rust.SessionError),
                match="career not set|not initialized|Invalid input",
            ):
                await scraper.get_course_info(0)


@pytest.mark.integration
@pytest.mark.network
class TestPhase7Electives:
    """Test scraping electives (is_electives=True)."""

    @pytest.mark.asyncio
    async def test_scrape_electives_career(self) -> None:
        """Test scraping courses from electives career."""
        async with await SiaScraper.create(timeout=30) as scraper:
            await scraper.set_career("0-2-8-3", is_electives=True)

            assert scraper.sia_session.is_electives is True

            if len(scraper.course_list) == 0:
                pytest.skip("SIA returned no elective courses for career 0-2-8-3")

            course = await scraper.get_course_info(0)
            assert isinstance(course, sia_scraper_rust.CourseInfoModel)


@pytest.mark.integration
@pytest.mark.network
class TestPhase7PySiaSessionDirect:
    """Test PySiaSession directly (bypassing Python wrapper)."""

    @pytest.mark.asyncio
    async def test_pysiasession_direct_workflow(self) -> None:
        """Test PySiaSession used directly without Python wrapper."""
        session = sia_scraper_rust.PySiaSession(timeout=30)

        try:
            # Initialize
            state = await session.init_session()
            assert state is not None
            assert session.is_initialized()

            # Set career
            state = await session.set_career("0-2-8-3")
            assert state.career_code == "0-2-8-3"

            # Scrape course
            course = await session.scrape_course_info(0)
            assert course is not None
            assert course.course_name
        finally:
            await session.reset()

    @pytest.mark.asyncio
    async def test_pysiasession_from_state(self) -> None:
        """Test PySiaSession.from_state() class method."""
        # Create and save state
        session1 = sia_scraper_rust.PySiaSession(timeout=30)
        await session1.init_session()
        await session1.set_career("0-2-8-3")

        # Get session data
        session_data = await session1.get_session_data()
        await session1.reset()

        # Restore from state
        session2 = await sia_scraper_rust.PySiaSession.from_state(session_data)
        assert session2.is_initialized()

        # Verify restored state
        state2 = await session2.get_state()
        assert state2.career_code == "0-2-8-3"

        # Scrape from restored session
        course = await session2.scrape_course_info(0)
        assert course is not None

        await session2.reset()
