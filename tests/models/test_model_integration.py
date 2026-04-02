"""Integration tests for Rust PyClass models."""

import pickle

import sia_scraper_rust


class TestCourseModelIntegration:
    def test_nested_model_traversal(self):
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
        assert course.groups[0].schedules[0].day == "Lunes"
        assert course.groups[0].schedules[0].classroom == "A101"
        assert course.groups[0].teacher == "Profesor Uno"

    def test_none_values_handled(self):
        course = sia_scraper_rust.CourseInfoModel(
            course_name="TEST",
            credits=3,
            typology="ELECTIVA",
            available_spots=0,
            scrape_timestamp="",
            groups=[],
            code=None,
        )
        assert course.code is None
        assert course.available_spots == 0

    def test_empty_lists_handled(self):
        course = sia_scraper_rust.CourseInfoModel(
            course_name="TEST",
            credits=3,
            typology="ELECTIVA",
            available_spots=0,
            scrape_timestamp="",
            groups=[],
            code=None,
        )
        assert course.groups == []


class TestPrerequisiteModelIntegration:
    def test_nested_prerequisite_traversal(self):
        prereq = sia_scraper_rust.PrerequisiteModel("1000001", "CALCULO")
        cond = sia_scraper_rust.PrereqConditionModel(1, "M", True, 1, [prereq])
        course_prereqs = sia_scraper_rust.CoursePrereqsModel(
            course_name="PROGRAMACION I",
            code=None,
            credits=3,
            typology="DISCIPLINAR OBLIGATORIA",
            conditions=[cond],
        )
        assert course_prereqs.conditions[0].prerequisites[0].course_name == "CALCULO"
        assert course_prereqs.conditions[0].prereq_type == "M"

    def test_multiple_nested_levels(self):
        prereq1 = sia_scraper_rust.PrerequisiteModel("1000001", "CALCULO")
        prereq2 = sia_scraper_rust.PrerequisiteModel("1000002", "ALGEBRA")
        cond1 = sia_scraper_rust.PrereqConditionModel(1, "M", True, 1, [prereq1])
        cond2 = sia_scraper_rust.PrereqConditionModel(2, "O", False, 2, [prereq1, prereq2])
        course_prereqs = sia_scraper_rust.CoursePrereqsModel(
            course_name="PROGRAMACION II",
            code=None,
            credits=3,
            typology="DISCIPLINAR OBLIGATORIA",
            conditions=[cond1, cond2],
        )
        assert len(course_prereqs.conditions) == 2
        assert len(course_prereqs.conditions[1].prerequisites) == 2
        assert course_prereqs.conditions[1].prerequisites[1].course_code == "1000002"


class TestSessionModelIntegration:
    def test_session_state_pickle_preserves_nested_models(self):
        entry = sia_scraper_rust.CourseListEntryModel("1000001", "Calculo")
        state = sia_scraper_rust.SessionStateModel(
            session_headers={"User-Agent": "sia-scraper"},
            session_cookies={"SESSION": "abc"},
            params={"Adf-Page-Id": "1", "Adf-Window-Id": "w1"},
            career_code="0-2-8-3",
            career_name="Ingenieria",
            is_electives=False,
            status="ON_CAREER_PAGE",
            course_list=[entry],
            javax_faces_view_state="vs-1",
        )
        pickled = pickle.dumps(state)
        unpickled = pickle.loads(pickled)

        assert len(unpickled.course_list) == 1
        assert unpickled.course_list[0].course_name == "Calculo"
        assert unpickled.session_headers["User-Agent"] == "sia-scraper"

    def test_session_state_empty_collections(self):
        state = sia_scraper_rust.SessionStateModel(
            session_headers={},
            session_cookies={},
            params={},
            career_code="",
            career_name="",
            is_electives=False,
            status="NO_SESSION",
            course_list=[],
            javax_faces_view_state=None,
        )
        assert state.session_headers == {}
        assert state.session_cookies == {}
        assert state.params == {}
        assert state.course_list == []


class TestModelEdgeCases:
    def test_model_with_special_characters(self):
        course = sia_scraper_rust.CourseInfoModel(
            course_name="CÁLCULO AVANZADO (CON ÉXITOS)",
            credits=4,
            typology="DISCIPLINAR OBLIGATORÍA",
            available_spots=10,
            scrape_timestamp="2024-03-15 14:30:00",
            groups=[],
            code="1000-ABC",
        )
        assert "CÁLCULO" in course.course_name
        assert course.code == "1000-ABC"

    def test_model_with_large_numbers(self):
        course = sia_scraper_rust.CourseInfoModel(
            course_name="TEST",
            credits=999,
            typology="TEST",
            available_spots=999999999,
            scrape_timestamp="",
            groups=[],
            code=None,
        )
        assert course.credits == 999
        assert course.available_spots == 999999999

    def test_multiple_groups_with_multiple_schedules(self):
        sched1 = sia_scraper_rust.ScheduleModel("Lunes", "08:00", "10:00", "A101")
        sched2 = sia_scraper_rust.ScheduleModel("Miercoles", "14:00", "16:00", "B202")
        group1 = sia_scraper_rust.GroupModel(
            group_name="GRUPO 01",
            teacher="Profesor Uno",
            faculty="Facultad",
            course_name="TEST",
            schedules=[sched1],
            duration="16 SEMANAS",
            schedule_type="DIURNA",
            spots=10,
            code=None,
        )
        group2 = sia_scraper_rust.GroupModel(
            group_name="GRUPO 02",
            teacher="Profesor Dos",
            faculty="Facultad",
            course_name="TEST",
            schedules=[sched2],
            duration="16 SEMANAS",
            schedule_type="DIURNA",
            spots=5,
            code=None,
        )
        course = sia_scraper_rust.CourseInfoModel(
            course_name="TEST",
            credits=3,
            typology="TEST",
            available_spots=15,
            scrape_timestamp="",
            groups=[group1, group2],
            code=None,
        )
        assert len(course.groups) == 2
        assert len(course.groups[0].schedules) == 1
        assert len(course.groups[1].schedules) == 1
        assert course.groups[0].schedules[0].day == "Lunes"
        assert course.groups[1].schedules[0].day == "Miercoles"
