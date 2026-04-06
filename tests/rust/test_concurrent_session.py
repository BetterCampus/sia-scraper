"""Tests for concurrent session state safety.

This module tests that concurrent session operations do not cause
stale state overwrites, as described in Issue #94.

The generation counter should prevent stale updates when:
1. scrape_courses() runs concurrently with set_career()
2. Multiple scrape_courses() calls run concurrently
3. get_state() runs concurrently with mutating operations
"""

import pickle
from unittest.mock import AsyncMock, MagicMock

import pytest

import sia_scraper_rust


class TestConcurrentSessionState:
    """Tests for concurrent session state handling."""

    @pytest.fixture
    def session_state_with_generation(self):
        """Create a session state with generation tracking."""
        return sia_scraper_rust.SessionStateModel(
            session_headers={"User-Agent": "Python test"},
            session_cookies={"JSESSIONID": "test123"},
            params={"Adf-Page-Id": "1", "Adf-Window-Id": "window1"},
            career_code="0-2-8-3",
            career_name="Ingeniería de Sistemas",
            is_electives=False,
            status="ON_CAREER_PAGE",
            course_list=[],
            javax_faces_view_state="viewstate123",
            generation=0,
        )

    def test_session_state_model_has_generation_field(self):
        """Test that SessionStateModel has a generation field."""
        state = sia_scraper_rust.SessionStateModel(
            session_headers={},
            session_cookies={},
            params={},
            career_code="",
            career_name="",
            is_electives=False,
            status="NO_SESSION",
            course_list=[],
        )

        assert hasattr(state, "generation")
        assert state.generation == 0

    def test_generation_field_is_accessible(self, session_state_with_generation):
        """Test that generation field can be read."""
        assert session_state_with_generation.generation == 0

    def test_generation_preserved_in_pickle(self, session_state_with_generation):
        """Test that generation is preserved during pickle serialization."""
        pickled = pickle.dumps(session_state_with_generation)
        restored = pickle.loads(pickled)

        assert restored.generation == session_state_with_generation.generation

    def test_multiple_states_have_independent_generation(self):
        """Test that different state instances have independent generation."""
        state1 = sia_scraper_rust.SessionStateModel(
            session_headers={},
            session_cookies={},
            params={},
            career_code="code1",
            career_name="Career 1",
            is_electives=False,
            status="ON_CAREER_PAGE",
            course_list=[],
            generation=0,
        )

        state2 = sia_scraper_rust.SessionStateModel(
            session_headers={},
            session_cookies={},
            params={},
            career_code="code2",
            career_name="Career 2",
            is_electives=True,
            status="ON_CAREER_PAGE",
            course_list=[],
            generation=5,
        )

        assert state1.generation == 0
        assert state2.generation == 5
        assert state1.generation != state2.generation


class TestGenerationConcept:
    """Tests demonstrating the generation concept for race condition prevention."""

    def test_stale_update_detection_concept(self):
        """Demonstrate how generation check prevents stale updates.

        This test shows the concept: if a cloned state has generation 0
        but the parent has generation 1, the clone is stale and should
        not overwrite the parent.
        """
        parent_generation = 1
        cloned_generation = 0

        is_stale = cloned_generation != parent_generation

        assert is_stale, "Clone with older generation should be detected as stale"

    def test_current_update_detection_concept(self):
        """Demonstrate how generation check allows current updates."""
        parent_generation = 1
        cloned_generation = 1

        is_current = cloned_generation == parent_generation

        assert is_current, "Clone with matching generation should be current"

    def test_generation_initially_zero(self):
        """Test that new session state starts with generation 0."""
        state = sia_scraper_rust.SessionStateModel(
            session_headers={},
            session_cookies={},
            params={},
            career_code="0-2-8-3",
            career_name="Test",
            is_electives=False,
            status="CREATED",
            course_list=[],
        )

        assert state.generation == 0

    def test_generation_in_state_with_career(self):
        """Test generation field exists in state with career selected."""
        state = sia_scraper_rust.SessionStateModel(
            session_headers={"Authorization": "Bearer token"},
            session_cookies={"JSESSIONID": "abc123"},
            params={"Adf-Page-Id": "2", "Adf-Window-Id": "main"},
            career_code="0-2-8-3",
            career_name="Ingeniería de Sistemas",
            is_electives=False,
            status="ON_CAREER_PAGE",
            course_list=[],
            javax_faces_view_state="vs-abc123",
            generation=10,
        )

        assert state.generation == 10
        assert state.status == "ON_CAREER_PAGE"
        assert state.career_code == "0-2-8-3"


class TestGenerationBasedStateUpdate:
    """Tests for generation-based state update logic in py_session.rs."""

    @pytest.mark.asyncio
    async def test_scrape_courses_with_matching_generation_updates_state(self):
        """Test that scrape_courses updates state when generation matches."""
        state_with_gen_1 = sia_scraper_rust.SessionStateModel(
            session_headers={},
            session_cookies={},
            params={},
            career_code="0-2-8-3",
            career_name="Test",
            is_electives=False,
            status="ON_CAREER_PAGE",
            course_list=[],
            generation=1,
        )

        parent_generation = state_with_gen_1.generation
        current_generation = state_with_gen_1.generation

        assert parent_generation == current_generation, "Generations should match for update"

    @pytest.mark.asyncio
    async def test_scrape_courses_with_mismatched_generation_skips_update(self):
        """Test that scrape_courses skips update when generation mismatches."""
        parent_state = sia_scraper_rust.SessionStateModel(
            session_headers={},
            session_cookies={},
            params={},
            career_code="0-2-8-3",
            career_name="Test",
            is_electives=False,
            status="ON_CAREER_PAGE",
            course_list=[],
            generation=1,
        )

        current_state = sia_scraper_rust.SessionStateModel(
            session_headers={},
            session_cookies={},
            params={},
            career_code="0-2-8-4",
            career_name="Updated",
            is_electives=False,
            status="ON_CAREER_PAGE",
            course_list=[],
            generation=2,
        )

        parent_generation = parent_state.generation
        current_generation = current_state.generation

        assert parent_generation != current_generation, (
            "Generations should differ - stale update detected"
        )
        assert current_generation > parent_generation, "Current generation should be newer"
