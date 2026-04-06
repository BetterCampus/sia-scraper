"""Tests for Rust PyClass prerequisite models."""

import sia_scraper_rust


class TestPrerequisiteModel:
    """Tests for PrerequisiteModel covering both positional and keyword argument construction."""

    def test_creation_with_positional_args(self):
        prereq = sia_scraper_rust.PrerequisiteModel("1000001", "CALCULO")
        assert prereq.course_code == "1000001"
        assert prereq.course_name == "CALCULO"

    def test_repr_output(self):
        prereq = sia_scraper_rust.PrerequisiteModel("1000001", "CALCULO")
        assert "PrerequisiteModel" in repr(prereq)
        assert "1000001" in repr(prereq)

    def test_creation_with_keyword_args(self):
        prereq = sia_scraper_rust.PrerequisiteModel(
            course_code="1000001",
            course_name="CALCULO",
        )
        assert prereq.course_code == "1000001"
        assert prereq.course_name == "CALCULO"


class TestPrereqConditionModel:
    """Tests for PrereqConditionModel using keyword arguments (required due to many parameters)."""

    def test_creation_with_keyword_args(self):
        prereq = sia_scraper_rust.PrerequisiteModel("1000001", "CALCULO")
        cond = sia_scraper_rust.PrereqConditionModel(
            condition=1,
            prereq_type="M",
            all_required=True,
            number_of_courses=1,
            prerequisites=[prereq],
        )
        assert cond.condition == 1
        assert cond.prereq_type == "M"
        assert cond.all_required is True
        assert cond.number_of_courses == 1
        assert len(cond.prerequisites) == 1

    def test_repr_output(self):
        prereq = sia_scraper_rust.PrerequisiteModel("1000001", "CALCULO")
        cond = sia_scraper_rust.PrereqConditionModel(
            condition=1,
            prereq_type="M",
            all_required=True,
            number_of_courses=1,
            prerequisites=[prereq],
        )
        assert "PrereqConditionModel" in repr(cond)
        assert "1" in repr(cond)

    def test_str_output(self):
        prereq = sia_scraper_rust.PrerequisiteModel("1000001", "CALCULO")
        cond = sia_scraper_rust.PrereqConditionModel(
            condition=1,
            prereq_type="M",
            all_required=True,
            number_of_courses=1,
            prerequisites=[prereq],
        )
        str_output = str(cond)
        assert "Condition" in str_output
        assert "M" in str_output

    def test_creation_with_keyword_args_empty_prereqs(self):
        cond = sia_scraper_rust.PrereqConditionModel(
            condition=1,
            prereq_type="M",
            all_required=True,
            number_of_courses=0,
            prerequisites=[],
        )
        assert cond.condition == 1
        assert cond.prereq_type == "M"
        assert len(cond.prerequisites) == 0


class TestCoursePrereqsModel:
    """Tests for CoursePrereqsModel using keyword arguments (required due to many parameters)."""

    def test_creation_with_keyword_args(self):
        cond = sia_scraper_rust.PrereqConditionModel(
            condition=1,
            prereq_type="M",
            all_required=True,
            number_of_courses=1,
            prerequisites=[],
        )
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
        cond = sia_scraper_rust.PrereqConditionModel(
            condition=1,
            prereq_type="M",
            all_required=True,
            number_of_courses=1,
            prerequisites=[],
        )
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
        cond = sia_scraper_rust.PrereqConditionModel(
            condition=1,
            prereq_type="M",
            all_required=True,
            number_of_courses=1,
            prerequisites=[prereq],
        )
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
        cond1 = sia_scraper_rust.PrereqConditionModel(
            condition=1,
            prereq_type="M",
            all_required=True,
            number_of_courses=1,
            prerequisites=[prereq1],
        )
        cond2 = sia_scraper_rust.PrereqConditionModel(
            condition=2,
            prereq_type="O",
            all_required=False,
            number_of_courses=2,
            prerequisites=[prereq1, prereq2],
        )
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
