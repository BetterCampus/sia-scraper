"""Tests for Rust PyClass prerequisite models."""

import sia_scraper_rust


class TestPrerequisiteModel:
    def test_creation(self):
        prereq = sia_scraper_rust.PrerequisiteModel("1000001", "CALCULO")
        assert prereq.course_code == "1000001"
        assert prereq.course_name == "CALCULO"

    def test_repr_output(self):
        prereq = sia_scraper_rust.PrerequisiteModel("1000001", "CALCULO")
        assert "PrerequisiteModel" in repr(prereq)
        assert "1000001" in repr(prereq)


class TestPrereqConditionModel:
    def test_creation(self):
        prereq = sia_scraper_rust.PrerequisiteModel("1000001", "CALCULO")
        cond = sia_scraper_rust.PrereqConditionModel(1, "M", True, 1, [prereq])
        assert cond.condition == 1
        assert cond.prereq_type == "M"
        assert cond.all_required is True
        assert cond.number_of_courses == 1
        assert len(cond.prerequisites) == 1

    def test_repr_output(self):
        prereq = sia_scraper_rust.PrerequisiteModel("1000001", "CALCULO")
        cond = sia_scraper_rust.PrereqConditionModel(1, "M", True, 1, [prereq])
        assert "PrereqConditionModel" in repr(cond)
        assert "1" in repr(cond)

    def test_str_output(self):
        prereq = sia_scraper_rust.PrerequisiteModel("1000001", "CALCULO")
        cond = sia_scraper_rust.PrereqConditionModel(1, "M", True, 1, [prereq])
        str_output = str(cond)
        assert "Condition" in str_output
        assert "M" in str_output


class TestCoursePrereqsModel:
    def test_creation(self):
        prereq = sia_scraper_rust.PrerequisiteModel("1000001", "CALCULO")
        cond = sia_scraper_rust.PrereqConditionModel(1, "M", True, 1, [prereq])
        course_prereqs = sia_scraper_rust.CoursePrereqsModel(
            course_name="PROGRAMACION I (2016489)",
            code=None,
            credits=3,
            typology="DISCIPLINAR OBLIGATORIA",
            conditions=[cond],
        )
        assert course_prereqs.course_name == "PROGRAMACION I (2016489)"
        assert course_prereqs.credits == 3
        assert len(course_prereqs.conditions) == 1

    def test_repr_output(self):
        prereq = sia_scraper_rust.PrerequisiteModel("1000001", "CALCULO")
        cond = sia_scraper_rust.PrereqConditionModel(1, "M", True, 1, [prereq])
        course_prereqs = sia_scraper_rust.CoursePrereqsModel(
            course_name="PROGRAMACION I",
            code=None,
            credits=3,
            typology="DISCIPLINAR OBLIGATORIA",
            conditions=[cond],
        )
        assert "CoursePrereqsModel" in repr(course_prereqs)

    def test_nested_prerequisites_accessible(self):
        prereq = sia_scraper_rust.PrerequisiteModel("1000001", "CALCULO")
        cond = sia_scraper_rust.PrereqConditionModel(1, "M", True, 1, [prereq])
        course_prereqs = sia_scraper_rust.CoursePrereqsModel(
            course_name="PROGRAMACION I",
            code=None,
            credits=3,
            typology="DISCIPLINAR OBLIGATORIA",
            conditions=[cond],
        )
        assert course_prereqs.conditions[0].prerequisites[0].course_code == "1000001"

    def test_multiple_conditions(self):
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
        assert course_prereqs.conditions[0].prereq_type == "M"
        assert course_prereqs.conditions[1].prereq_type == "O"
