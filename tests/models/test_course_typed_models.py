"""Tests for Rust PyClass course models."""

import sia_scraper_rust


class TestScheduleModel:
    def test_creation_with_positional_args(self):
        schedule = sia_scraper_rust.ScheduleModel("Lunes", "08:00", "10:00", "A101")
        assert schedule.day == "Lunes"
        assert schedule.start_time == "08:00"
        assert schedule.end_time == "10:00"
        assert schedule.classroom == "A101"

    def test_repr_output(self):
        schedule = sia_scraper_rust.ScheduleModel("Lunes", "08:00", "10:00", "A101")
        assert "ScheduleModel" in repr(schedule)
        assert "Lunes" in repr(schedule)

    def test_str_output(self):
        schedule = sia_scraper_rust.ScheduleModel("Lunes", "08:00", "10:00", "A101")
        str_output = str(schedule)
        assert "Lunes" in str_output
        assert "08:00" in str_output
        assert "10:00" in str_output


class TestGroupModel:
    def test_creation_with_positional_args(self):
        schedule = sia_scraper_rust.ScheduleModel("Lunes", "08:00", "10:00", "A101")
        group = sia_scraper_rust.GroupModel(
            group_name="GRUPO 01",
            teacher="Profesor Uno",
            faculty="Facultad de Ciencias",
            course_name="CALCULO AVANZADO",
            schedules=[schedule],
            duration="16 SEMANAS",
            schedule_type="DIURNA",
            spots=10,
            code=None,
        )
        assert group.group_name == "GRUPO 01"
        assert group.teacher == "Profesor Uno"
        assert group.faculty == "Facultad de Ciencias"
        assert len(group.schedules) == 1

    def test_repr_output(self):
        schedule = sia_scraper_rust.ScheduleModel("Lunes", "08:00", "10:00", "A101")
        group = sia_scraper_rust.GroupModel(
            group_name="GRUPO 01",
            teacher="Profesor Uno",
            faculty="Facultad de Ciencias",
            course_name="CALCULO AVANZADO",
            schedules=[schedule],
            duration="16 SEMANAS",
            schedule_type="DIURNA",
            spots=10,
            code=None,
        )
        assert "GroupModel" in repr(group)
        assert "GRUPO 01" in repr(group)

    def test_schedules_accessible(self):
        schedule = sia_scraper_rust.ScheduleModel("Lunes", "08:00", "10:00", "A101")
        group = sia_scraper_rust.GroupModel(
            group_name="GRUPO 01",
            teacher="Profesor Uno",
            faculty="Facultad de Ciencias",
            course_name="CALCULO AVANZADO",
            schedules=[schedule],
            duration="16 SEMANAS",
            schedule_type="DIURNA",
            spots=10,
            code=None,
        )
        assert group.schedules[0].day == "Lunes"


class TestCourseInfoModel:
    def test_creation_with_positional_args(self):
        course = sia_scraper_rust.CourseInfoModel(
            course_name="CALCULO AVANZADO",
            credits=4,
            typology="DISCIPLINAR OBLIGATORIA",
            available_spots=10,
            scrape_timestamp="2024-03-15 14:30",
            groups=[],
            code=None,
        )
        assert course.course_name == "CALCULO AVANZADO"
        assert course.credits == 4
        assert course.typology == "DISCIPLINAR OBLIGATORIA"
        assert course.available_spots == 10

    def test_repr_output(self):
        course = sia_scraper_rust.CourseInfoModel(
            course_name="CALCULO AVANZADO",
            credits=4,
            typology="DISCIPLINAR OBLIGATORIA",
            available_spots=10,
            scrape_timestamp="",
            groups=[],
            code=None,
        )
        assert "CourseInfoModel" in repr(course)
        assert "CALCULO AVANZADO" in repr(course)

    def test_nested_groups_accessible(self):
        schedule = sia_scraper_rust.ScheduleModel("Lunes", "08:00", "10:00", "A101")
        group = sia_scraper_rust.GroupModel(
            group_name="GRUPO 01",
            teacher="Profesor Uno",
            faculty="Facultad de Ciencias",
            course_name="CALCULO AVANZADO",
            schedules=[schedule],
            duration="16 SEMANAS",
            schedule_type="DIURNA",
            spots=10,
            code=None,
        )
        course = sia_scraper_rust.CourseInfoModel(
            course_name="CALCULO AVANZADO",
            credits=4,
            typology="DISCIPLINAR OBLIGATORIA",
            available_spots=10,
            scrape_timestamp="",
            groups=[group],
            code=None,
        )
        assert len(course.groups) == 1
        assert course.groups[0].group_name == "GRUPO 01"
        assert course.groups[0].schedules[0].day == "Lunes"

    def test_code_field_settable(self):
        course = sia_scraper_rust.CourseInfoModel(
            course_name="CALCULO AVANZADO",
            credits=4,
            typology="DISCIPLINAR OBLIGATORIA",
            available_spots=10,
            scrape_timestamp="",
            groups=[],
            code=None,
        )
        assert course.code is None
        course.code = "1000001"
        assert course.code == "1000001"
