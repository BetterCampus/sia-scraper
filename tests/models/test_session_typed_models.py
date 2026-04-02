"""Tests for Rust PyClass session models."""

import pickle

import sia_scraper_rust


class TestCourseListEntryModel:
    """Tests for CourseListEntryModel covering both positional and keyword argument construction."""

    def test_creation_with_positional_args(self):
        entry = sia_scraper_rust.CourseListEntryModel("1000001", "Calculo")
        assert entry.course_code == "1000001"
        assert entry.course_name == "Calculo"

    def test_repr_output(self):
        entry = sia_scraper_rust.CourseListEntryModel("1000001", "Calculo")
        assert "CourseListEntryModel" in repr(entry)
        assert "1000001" in repr(entry)

    def test_creation_with_keyword_args(self):
        entry = sia_scraper_rust.CourseListEntryModel(
            course_code="1000001",
            course_name="Calculo",
        )
        assert entry.course_code == "1000001"
        assert entry.course_name == "Calculo"


class TestSessionStateModel:
    """Tests for SessionStateModel using keyword arguments (positional construction with 9 params is an anti-pattern)."""

    def test_creation_with_keyword_args(self):
        entry = sia_scraper_rust.CourseListEntryModel("1000001", "Calculo")
        state = sia_scraper_rust.SessionStateModel(
            session_headers={"User-Agent": "test"},
            session_cookies={"JSESSIONID": "abc123"},
            params={"Adf-Page-Id": "0", "Adf-Window-Id": "win-1"},
            career_code="0-2-8-3",
            career_name="Ingenieria de Sistemas",
            is_electives=False,
            status="ON_CAREER_PAGE",
            course_list=[entry],
            javax_faces_view_state="vs-1",
        )
        assert state.career_code == "0-2-8-3"
        assert state.career_name == "Ingenieria de Sistemas"
        assert state.status == "ON_CAREER_PAGE"
        assert state.is_electives is False
        assert len(state.course_list) == 1

    def test_repr_output(self):
        entry = sia_scraper_rust.CourseListEntryModel("1000001", "Calculo")
        state = sia_scraper_rust.SessionStateModel(
            session_headers={},
            session_cookies={},
            params={"Adf-Page-Id": "0", "Adf-Window-Id": "win-1"},
            career_code="0-2-8-3",
            career_name="Ingenieria",
            is_electives=False,
            status="ON_CAREER_PAGE",
            course_list=[entry],
            javax_faces_view_state="vs-1",
        )
        assert "SessionStateModel" in repr(state)
        assert "0-2-8-3" in repr(state)

    def test_empty_course_list(self):
        state = sia_scraper_rust.SessionStateModel(
            session_headers={},
            session_cookies={},
            params={"Adf-Page-Id": "0", "Adf-Window-Id": "win-1"},
            career_code="",
            career_name="N/A",
            is_electives=False,
            status="NO_SESSION",
            course_list=[],
            javax_faces_view_state=None,
        )
        assert len(state.course_list) == 0
        assert state.status == "NO_SESSION"

    def test_course_list_accessible(self):
        entry1 = sia_scraper_rust.CourseListEntryModel("1000001", "Calculo")
        entry2 = sia_scraper_rust.CourseListEntryModel("1000002", "Algebra")
        state = sia_scraper_rust.SessionStateModel(
            session_headers={},
            session_cookies={},
            params={"Adf-Page-Id": "0", "Adf-Window-Id": "win-1"},
            career_code="0-2-8-3",
            career_name="Ingenieria",
            is_electives=False,
            status="ON_CAREER_PAGE",
            course_list=[entry1, entry2],
            javax_faces_view_state="vs-1",
        )
        assert len(state.course_list) == 2
        assert state.course_list[0].course_code == "1000001"
        assert state.course_list[1].course_code == "1000002"

    def test_pickle_serialization_roundtrip(self):
        entry = sia_scraper_rust.CourseListEntryModel("1000001", "Calculo")
        state = sia_scraper_rust.SessionStateModel(
            session_headers={"User-Agent": "test"},
            session_cookies={"JSESSIONID": "abc123"},
            params={"Adf-Page-Id": "0", "Adf-Window-Id": "win-1"},
            career_code="0-2-8-3",
            career_name="Ingenieria de Sistemas",
            is_electives=False,
            status="ON_CAREER_PAGE",
            course_list=[entry],
            javax_faces_view_state="vs-1",
        )
        pickled = pickle.dumps(state)
        unpickled = pickle.loads(pickled)

        assert unpickled.career_code == "0-2-8-3"
        assert unpickled.career_name == "Ingenieria de Sistemas"
        assert unpickled.status == "ON_CAREER_PAGE"
        assert unpickled.is_electives is False
        assert unpickled.javax_faces_view_state == "vs-1"
        assert len(unpickled.course_list) == 1
        assert unpickled.course_list[0].course_code == "1000001"

    def test_pickle_with_multiple_course_entries(self):
        entry1 = sia_scraper_rust.CourseListEntryModel("1000001", "Calculo")
        entry2 = sia_scraper_rust.CourseListEntryModel("1000002", "Algebra")
        entry3 = sia_scraper_rust.CourseListEntryModel("1000003", "Fisica")
        state = sia_scraper_rust.SessionStateModel(
            session_headers={},
            session_cookies={},
            params={"Adf-Page-Id": "0", "Adf-Window-Id": "win-1"},
            career_code="0-2-8-3",
            career_name="Ingenieria",
            is_electives=True,
            status="ON_COURSE_PAGE",
            course_list=[entry1, entry2, entry3],
            javax_faces_view_state="vs-1",
        )
        pickled = pickle.dumps(state)
        unpickled = pickle.loads(pickled)

        assert len(unpickled.course_list) == 3
        assert unpickled.course_list[0].course_name == "Calculo"
        assert unpickled.course_list[1].course_name == "Algebra"
        assert unpickled.course_list[2].course_name == "Fisica"
        assert unpickled.is_electives is True
