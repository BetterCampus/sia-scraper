"""Tests for Rust PyClass models and pickle support."""

import pickle

import pytest

sia_scraper_rust = pytest.importorskip("sia_scraper_rust")


def test_course_models_roundtrip_pickle() -> None:
    schedule = sia_scraper_rust.ScheduleModel("Lunes", "08:00", "10:00", "A-101")
    group = sia_scraper_rust.GroupModel(
        group_name="Grupo 1",
        teacher="Docente",
        faculty="Ingenieria",
        course_name="Calculo",
        schedules=[schedule],
        duration="16 semanas",
        schedule_type="Diurna",
        spots=20,
        code="1000001",
    )
    course = sia_scraper_rust.CourseInfoModel(
        course_name="Calculo",
        credits=3,
        typology="Obligatoria",
        available_spots=20,
        scrape_timestamp="2026-04-01 10:00",
        groups=[group],
        code="1000001",
    )

    restored = pickle.loads(pickle.dumps(course))

    assert restored.course_name == "Calculo"
    assert restored.credits == 3
    assert len(restored.groups) == 1
    assert restored.groups[0].teacher == "Docente"
    assert restored.groups[0].schedules[0].day == "Lunes"


def test_prereq_models_roundtrip_pickle() -> None:
    prereq = sia_scraper_rust.PrerequisiteModel("1000001", "Calculo")
    condition = sia_scraper_rust.PrereqConditionModel(
        condition=1,
        prereq_type="CURSOS",
        all_required=True,
        number_of_courses=1,
        prerequisites=[prereq],
    )
    model = sia_scraper_rust.CoursePrereqsModel(
        course_name="Algebra",
        credits=4,
        typology="Obligatoria",
        conditions=[condition],
        code=None,
    )

    restored = pickle.loads(pickle.dumps(model))

    assert restored.course_name == "Algebra"
    assert restored.credits == 4
    assert len(restored.conditions) == 1
    assert restored.conditions[0].all_required is True
    assert restored.conditions[0].prerequisites[0].course_code == "1000001"


def test_session_models_roundtrip_pickle() -> None:
    entry = sia_scraper_rust.CourseListEntryModel("1000001", "Calculo")
    state = sia_scraper_rust.SessionStateModel(
        session_headers={"User-Agent": "test"},
        session_cookies={"JSESSIONID": "abc"},
        params={"Adf-Page-Id": "1", "Adf-Window-Id": "w1"},
        career_code="0-2-8-3",
        career_name="Ingenieria de Sistemas",
        is_electives=False,
        status="ON_CAREER_PAGE",
        course_list=[entry],
        javax_faces_view_state="view-state-1",
    )

    restored = pickle.loads(pickle.dumps(state))

    assert restored.career_code == "0-2-8-3"
    assert restored.status == "ON_CAREER_PAGE"
    assert restored.javax_faces_view_state == "view-state-1"
    assert len(restored.course_list) == 1
    assert restored.course_list[0].name == "Calculo"
