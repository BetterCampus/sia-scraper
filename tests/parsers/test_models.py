"""Unit tests for parser dataclasses in models.py."""

import pytest

from sia_scraper.parsers.models import (
    CourseInfo,
    CoursePrereqs,
    Group,
    PrereqCondition,
    PrereqType,
    Prerequisite,
    Schedule,
)


@pytest.mark.unit
class TestScheduleModel:
    """Tests for Schedule dataclass."""

    def test_schedule_fields(self) -> None:
        schedule = Schedule(
            day="LUNES",
            start_time="07:00",
            end_time="09:00",
            classroom="401-101",
        )

        assert schedule.day == "LUNES"
        assert schedule.start_time == "07:00"
        assert schedule.end_time == "09:00"
        assert schedule.classroom == "401-101"


@pytest.mark.unit
class TestGroupModel:
    """Tests for Group dataclass."""

    def test_group_fields_with_spots_and_code(self) -> None:
        schedules = [
            Schedule(day="MARTES", start_time="10:00", end_time="12:00", classroom="301-202"),
            Schedule(day="JUEVES", start_time="10:00", end_time="12:00", classroom="301-202"),
        ]
        group = Group(
            group_name="1",
            teacher="Docente",
            faculty="Ingenieria",
            course_name="Calculo",
            schedules=schedules,
            duration="16 SEMANAS",
            schedule_type="DIURNA",
            spots=12,
            code="2016489",
        )

        assert group.group_name == "1"
        assert group.teacher == "Docente"
        assert group.schedules == schedules
        assert group.spots == 12
        assert group.code == "2016489"

    def test_group_optional_defaults(self) -> None:
        group = Group(
            group_name="CA",
            teacher="Docente 2",
            faculty="Ingenieria",
            course_name="Fisica",
            schedules=[],
            duration="8 SEMANAS",
            schedule_type="NOCTURNA",
            spots=None,
        )

        assert group.spots is None
        assert group.code is None


@pytest.mark.unit
class TestCourseInfoModel:
    """Tests for CourseInfo dataclass."""

    def test_course_info_fields(self) -> None:
        group = Group(
            group_name="1",
            teacher="Docente",
            faculty="Ingenieria",
            course_name="Programacion",
            schedules=[
                Schedule(day="VIERNES", start_time="08:00", end_time="10:00", classroom="A-101")
            ],
            duration="16 SEMANAS",
            schedule_type="DIURNA",
            spots=5,
        )
        course = CourseInfo(
            course_name="PROGRAMACION I",
            credits=3,
            typology="DISCIPLINAR OBLIGATORIA",
            available_spots=5,
            scrape_timestamp="2026-03-30 10:00",
            groups=[group],
        )

        assert course.course_name == "PROGRAMACION I"
        assert course.credits == 3
        assert course.typology == "DISCIPLINAR OBLIGATORIA"
        assert course.available_spots == 5
        assert len(course.groups) == 1
        assert course.code is None


@pytest.mark.unit
class TestPrereqModels:
    """Tests for prerequisite-related dataclasses."""

    def test_prerequisite_fields(self) -> None:
        prereq = Prerequisite(course_code="1000001", course_name="CALCULO")

        assert prereq.course_code == "1000001"
        assert prereq.course_name == "CALCULO"

    def test_prereq_condition_fields(self) -> None:
        condition = PrereqCondition(
            condition=1,
            type=PrereqType.M,
            all_required=True,
            number_of_courses=2,
            prerequisites=[
                Prerequisite(course_code="1000001", course_name="CALCULO"),
                Prerequisite(course_code="1000002", course_name="ALGEBRA"),
            ],
        )

        assert condition.condition == 1
        assert condition.type == PrereqType.M
        assert condition.all_required is True
        assert condition.number_of_courses == 2
        assert len(condition.prerequisites) == 2

    def test_course_prereqs_fields(self) -> None:
        course_prereqs = CoursePrereqs(
            course_name="PROGRAMACION I (2016489)",
            code="2016489",
            credits=3,
            typology="DISCIPLINAR OBLIGATORIA",
            conditions=[
                PrereqCondition(
                    condition=1,
                    type=PrereqType.M,
                    all_required=True,
                    number_of_courses=1,
                    prerequisites=[Prerequisite(course_code="1000001", course_name="CALCULO")],
                )
            ],
        )

        assert course_prereqs.course_name == "PROGRAMACION I (2016489)"
        assert course_prereqs.code == "2016489"
        assert course_prereqs.credits == 3
        assert course_prereqs.typology == "DISCIPLINAR OBLIGATORIA"
        assert len(course_prereqs.conditions) == 1
