"""Tests for Rust PyClass models and pickle support."""

import pickle

import pytest

sia_scraper_rust = pytest.importorskip("sia_scraper_rust")


def test_course_models_roundtrip_pickle() -> None:
    schedule = sia_scraper_rust.ScheduleModel("Lunes", "08:00", "10:00", "A-101")
    group = sia_scraper_rust.GroupModel(
        "Grupo 1",
        "Docente",
        "Ingenieria",
        "Calculo",
        [schedule],
        "16 semanas",
        "Diurna",
        20,
        "1000001",
    )
    course = sia_scraper_rust.CourseInfoModel(
        "Calculo",
        3,
        "Obligatoria",
        20,
        "2026-04-01 10:00",
        [group],
        "1000001",
    )

    restored = pickle.loads(pickle.dumps(course))

    assert restored.course_name == "Calculo"
    assert restored.credits == 3
    assert len(restored.groups) == 1
    assert restored.groups[0].teacher == "Docente"
    assert restored.groups[0].schedules[0].day == "Lunes"


def test_prereq_models_roundtrip_pickle() -> None:
    prereq = sia_scraper_rust.PrerequisiteModel("1000001", "Calculo")
    condition = sia_scraper_rust.PrereqConditionModel(1, "CURSOS", True, 1, [prereq])
    model = sia_scraper_rust.CoursePrereqsModel("Algebra", 4, "Obligatoria", [condition], None)

    restored = pickle.loads(pickle.dumps(model))

    assert restored.course_name == "Algebra"
    assert restored.credits == 4
    assert len(restored.conditions) == 1
    assert restored.conditions[0].all_required is True
    assert restored.conditions[0].prerequisites[0].course_code == "1000001"


def test_session_models_roundtrip_pickle() -> None:
    entry = sia_scraper_rust.CourseListEntryModel("1000001", "Calculo")
    state = sia_scraper_rust.SessionStateModel(
        {"User-Agent": "test"},
        {"JSESSIONID": "abc"},
        {"Adf-Page-Id": "1", "Adf-Window-Id": "w1"},
        "0-2-8-3",
        "Ingenieria de Sistemas",
        False,
        "ON_CAREER_PAGE",
        [entry],
        "view-state-1",
    )

    restored = pickle.loads(pickle.dumps(state))

    assert restored.career_code == "0-2-8-3"
    assert restored.status == "ON_CAREER_PAGE"
    assert restored.javax_faces_view_state == "view-state-1"
    assert len(restored.course_list) == 1
    assert restored.course_list[0].course_name == "Calculo"
