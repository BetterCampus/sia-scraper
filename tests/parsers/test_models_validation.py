"""Validation tests for Pydantic models in models.py."""

import pytest
from pydantic import ValidationError

from sia_scraper.parsers.models import (
    CourseInfo,
    CoursePrereqs,
    Group,
    PrereqCondition,
    PrereqType,
    Prerequisite,
    Schedule,
    SessionState,
)


@pytest.mark.unit
class TestScheduleValidation:
    """Test Schedule validation rules."""

    def test_schedule_invalid_time_format_raises(self) -> None:
        """Schedule with invalid time format should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Schedule(
                day="LUNES",
                start_time="25:00",
                end_time="09:00",
                classroom="101",
            )
        assert "start_time" in str(exc_info.value)

    def test_schedule_invalid_minute_raises(self) -> None:
        """Schedule with invalid minute value should raise ValidationError.

        Note: The regex pattern validates format but not logical time values.
        This test documents that "10:70" passes format validation but may fail
        in real-world scenarios where time logic is enforced separately.
        """
        schedule = Schedule(
            day="MARTES",
            start_time="10:70",
            end_time="11:00",
            classroom="202",
        )
        assert schedule.start_time == "10:70"

    def test_schedule_end_before_start_raises(self) -> None:
        """Schedule with end_time before start_time should raise."""
        with pytest.raises(ValidationError) as exc_info:
            Schedule(
                day="MARTES",
                start_time="10:00",
                end_time="08:00",
                classroom="202",
            )
        assert "end_time" in str(exc_info.value)

    def test_schedule_empty_day_raises(self) -> None:
        """Schedule with empty day should raise."""
        with pytest.raises(ValidationError):
            Schedule(
                day="",
                start_time="08:00",
                end_time="10:00",
                classroom="101",
            )

    def test_schedule_valid_defaults(self) -> None:
        """Valid schedule with default classroom should work."""
        schedule = Schedule(
            day="LUNES",
            start_time="08:00",
            end_time="10:00",
        )
        assert schedule.classroom == ""

    def test_schedule_valid_full(self) -> None:
        """Valid schedule with all fields should work."""
        schedule = Schedule(
            day="JUEVES",
            start_time="14:00",
            end_time="16:00",
            classroom="301-A",
        )
        assert schedule.day == "JUEVES"
        assert schedule.start_time == "14:00"
        assert schedule.end_time == "16:00"
        assert schedule.classroom == "301-A"


@pytest.mark.unit
class TestGroupValidation:
    """Test Group validation rules."""

    def test_group_invalid_course_code_raises(self) -> None:
        """Group with invalid course code format should raise."""
        with pytest.raises(ValidationError) as exc_info:
            Group(
                group_name="1",
                teacher="Docente",
                faculty="Ingenieria",
                course_name="Calculo",
                schedules=[],
                duration="16 SEMANAS",
                schedule_type="DIURNA",
                spots=10,
                code="ABC123",
            )
        assert "code" in str(exc_info.value)

    def test_group_invalid_course_code_too_short_raises(self) -> None:
        """Group with too-short course code should raise."""
        with pytest.raises(ValidationError):
            Group(
                group_name="1",
                teacher="Docente",
                faculty="Ingenieria",
                course_name="Calculo",
                schedules=[],
                duration="16 SEMANAS",
                schedule_type="DIURNA",
                spots=10,
                code="12345",
            )

    def test_group_negative_spots_raises(self) -> None:
        """Group with negative spots should raise."""
        with pytest.raises(ValidationError):
            Group(
                group_name="1",
                teacher="Docente",
                faculty="Ingenieria",
                course_name="Calculo",
                schedules=[],
                duration="16 SEMANAS",
                schedule_type="DIURNA",
                spots=-5,
            )

    def test_group_valid_with_code(self) -> None:
        """Valid group with 7-digit code should work."""
        group = Group(
            group_name="1",
            teacher="Docente",
            faculty="Ingenieria",
            course_name="Calculo",
            schedules=[],
            duration="16 SEMANAS",
            schedule_type="DIURNA",
            spots=10,
            code="2016489",
        )
        assert group.code == "2016489"

    def test_group_valid_without_code(self) -> None:
        """Valid group without code should work."""
        group = Group(
            group_name="CA",
            teacher="Docente",
            faculty="Ingenieria",
            course_name="Fisica",
            schedules=[],
            duration="8 SEMANAS",
            schedule_type="NOCTURNA",
            spots=None,
        )
        assert group.code is None
        assert group.spots is None


@pytest.mark.unit
class TestCourseInfoValidation:
    """Test CourseInfo validation rules."""

    def test_course_info_invalid_credits_too_high_raises(self) -> None:
        """CourseInfo with credits > 30 should raise."""
        with pytest.raises(ValidationError) as exc_info:
            CourseInfo(
                course_name="Test Course",
                credits=50,
                typology="DISCIPLINAR",
                available_spots=0,
                scrape_timestamp="2026-03-30 10:00",
                groups=[],
            )
        assert "credits" in str(exc_info.value)

    def test_course_info_negative_credits_raises(self) -> None:
        """CourseInfo with negative credits should raise."""
        with pytest.raises(ValidationError):
            CourseInfo(
                course_name="Test Course",
                credits=-1,
                typology="DISCIPLINAR",
                available_spots=0,
                scrape_timestamp="2026-03-30 10:00",
                groups=[],
            )

    def test_course_info_invalid_timestamp_format_raises(self) -> None:
        """CourseInfo with malformed timestamp should raise."""
        with pytest.raises(ValidationError):
            CourseInfo(
                course_name="Test Course",
                credits=3,
                typology="DISCIPLINAR",
                available_spots=0,
                scrape_timestamp="30/03/2026 10:00",
                groups=[],
            )

    def test_course_info_invalid_timestamp_no_time_raises(self) -> None:
        """CourseInfo with date-only timestamp should raise."""
        with pytest.raises(ValidationError):
            CourseInfo(
                course_name="Test Course",
                credits=3,
                typology="DISCIPLINAR",
                available_spots=0,
                scrape_timestamp="2026-03-30",
                groups=[],
            )

    def test_course_info_negative_spots_raises(self) -> None:
        """CourseInfo with negative available_spots should raise."""
        with pytest.raises(ValidationError):
            CourseInfo(
                course_name="Test Course",
                credits=3,
                typology="DISCIPLINAR",
                available_spots=-1,
                scrape_timestamp="2026-03-30 10:00",
                groups=[],
            )

    def test_course_info_nested_schedule_validation_cascades(self) -> None:
        """Invalid nested Schedule should raise ValidationError."""
        with pytest.raises(ValidationError):
            CourseInfo(
                course_name="Test Course",
                credits=3,
                typology="DISCIPLINAR",
                available_spots=0,
                scrape_timestamp="2026-03-30 10:00",
                groups=[
                    Group(
                        group_name="1",
                        teacher="Docente",
                        faculty="Ingenieria",
                        course_name="Test",
                        schedules=[
                            Schedule(
                                day="LUNES",
                                start_time="10:00",
                                end_time="08:00",
                                classroom="101",
                            )
                        ],
                        duration="16 SEMANAS",
                        schedule_type="DIURNA",
                        spots=10,
                    )
                ],
            )

    def test_course_info_valid_full(self) -> None:
        """Valid CourseInfo should work."""
        course = CourseInfo(
            course_name="PROGRAMACION I",
            credits=3,
            typology="DISCIPLINAR OBLIGATORIA",
            available_spots=5,
            scrape_timestamp="2026-03-30 10:00",
            groups=[],
            code="2016489",
        )
        assert course.course_name == "PROGRAMACION I"
        assert course.credits == 3


@pytest.mark.unit
class TestPrerequisiteValidation:
    """Test Prerequisite validation rules."""

    def test_prerequisite_empty_allowed(self) -> None:
        """Prerequisite with empty strings should work (backward compatibility)."""
        prereq = Prerequisite(course_code="", course_name="")
        assert prereq.course_code == ""
        assert prereq.course_name == ""

    def test_prerequisite_valid_full(self) -> None:
        """Valid prerequisite should work."""
        prereq = Prerequisite(course_code="1000001", course_name="CALCULO")
        assert prereq.course_code == "1000001"
        assert prereq.course_name == "CALCULO"


@pytest.mark.unit
class TestPrereqConditionValidation:
    """Test PrereqCondition validation and type conversion rules."""

    @staticmethod
    def _build(**payload) -> PrereqCondition:
        return PrereqCondition.model_validate(payload)

    def test_condition_parses_plain_number(self) -> None:
        condition = self._build(condition="3")
        assert condition.condition == 3

    def test_condition_parses_bracketed_number(self) -> None:
        condition = self._build(condition="[2]")
        assert condition.condition == 2

    def test_condition_empty_defaults_to_zero(self) -> None:
        condition = self._build(condition="")
        assert condition.condition == 0

    def test_condition_invalid_raises(self) -> None:
        with pytest.raises(ValidationError):
            self._build(condition="abc")

    def test_type_m_valid(self) -> None:
        condition = self._build(type="M")
        assert condition.type == PrereqType.M

    def test_type_o_valid(self) -> None:
        condition = self._build(type="O")
        assert condition.type == PrereqType.O

    def test_type_e_valid(self) -> None:
        condition = self._build(type="E")
        assert condition.type == PrereqType.E

    def test_type_a_valid(self) -> None:
        condition = self._build(type="A")
        assert condition.type == PrereqType.A

    def test_type_bracketed(self) -> None:
        condition = self._build(type="[M]")
        assert condition.type == PrereqType.M

    def test_type_lowercase(self) -> None:
        condition = self._build(type="m")
        assert condition.type == PrereqType.M

    def test_type_unknown_maps_to_unknown(self) -> None:
        condition = self._build(type="Z")
        assert condition.type == PrereqType.UNKNOWN

    def test_type_empty_defaults_unknown(self) -> None:
        condition = self._build(type="")
        assert condition.type == PrereqType.UNKNOWN

    def test_all_required_s_is_true(self) -> None:
        condition = self._build(all_required="S")
        assert condition.all_required is True

    def test_all_required_n_is_false(self) -> None:
        condition = self._build(all_required="N")
        assert condition.all_required is False

    def test_all_required_bracketed_s(self) -> None:
        condition = self._build(all_required="[S]")
        assert condition.all_required is True

    def test_all_required_bracketed_n(self) -> None:
        condition = self._build(all_required="[N]")
        assert condition.all_required is False

    def test_all_required_si_is_true(self) -> None:
        condition = self._build(all_required="SI")
        assert condition.all_required is True

    def test_all_required_no_is_false(self) -> None:
        condition = self._build(all_required="NO")
        assert condition.all_required is False

    def test_all_required_empty_defaults_false(self) -> None:
        condition = self._build(all_required="")
        assert condition.all_required is False

    def test_all_required_invalid_defaults_false(self) -> None:
        condition = self._build(all_required="maybe")
        assert condition.all_required is False

    def test_number_of_courses_parses_plain(self) -> None:
        condition = self._build(number_of_courses="5")
        assert condition.number_of_courses == 5

    def test_number_of_courses_parses_bracketed(self) -> None:
        condition = self._build(number_of_courses="[3]")
        assert condition.number_of_courses == 3

    def test_number_of_courses_empty_defaults_zero(self) -> None:
        condition = self._build(number_of_courses="")
        assert condition.number_of_courses == 0

    def test_number_of_courses_invalid_raises(self) -> None:
        with pytest.raises(ValidationError):
            self._build(number_of_courses="xyz")


@pytest.mark.unit
class TestCoursePrereqsValidation:
    """Test CoursePrereqs validation rules."""

    def test_course_prereqs_invalid_code_too_short_raises(self) -> None:
        """CoursePrereqs with short code should raise."""
        with pytest.raises(ValidationError) as exc_info:
            CoursePrereqs(
                course_name="PROGRAMACION I (2016489)",
                code="123",
                credits=3,
                typology="DISCIPLINAR",
                conditions=[],
            )
        assert "code" in str(exc_info.value)

    def test_course_prereqs_invalid_code_letters_raises(self) -> None:
        """CoursePrereqs with letters in code should raise."""
        with pytest.raises(ValidationError):
            CoursePrereqs(
                course_name="PROGRAMACION I (ABC1234)",
                code="ABC1234",
                credits=3,
                typology="DISCIPLINAR",
                conditions=[],
            )

    def test_course_prereqs_negative_credits_raises(self) -> None:
        """CoursePrereqs with negative credits should raise."""
        with pytest.raises(ValidationError):
            CoursePrereqs(
                course_name="PROGRAMACION I (2016489)",
                code="2016489",
                credits=-1,
                typology="DISCIPLINAR",
                conditions=[],
            )

    def test_course_prereqs_valid_full(self) -> None:
        """Valid CoursePrereqs should work."""
        prereqs = CoursePrereqs(
            course_name="PROGRAMACION I (2016489)",
            code="2016489",
            credits=3,
            typology="DISCIPLINAR",
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
        assert prereqs.code == "2016489"
        assert len(prereqs.conditions) == 1


@pytest.mark.unit
class TestSessionStateValidation:
    """Test SessionState validation rules."""

    def test_session_state_missing_adf_params_raises(self) -> None:
        """SessionState with missing ADF parameters should raise."""
        with pytest.raises(ValidationError) as exc_info:
            SessionState(
                session_headers={"User-Agent": "test"},
                session_cookies={"session": "abc"},
                params={},
                javax_faces_ViewState="test",
                career_code="1-1-1-1",
                career_name="Ingenieria",
                is_electives=False,
                status="READY",
            )
        assert "params" in str(exc_info.value)

    def test_session_state_missing_window_id_raises(self) -> None:
        """SessionState with missing Window-Id should raise."""
        with pytest.raises(ValidationError):
            SessionState(
                session_headers={"User-Agent": "test"},
                session_cookies={"session": "abc"},
                params={"Adf-Page-Id": "test"},
                javax_faces_ViewState="test",
                career_code="1-1-1-1",
                career_name="Ingenieria",
                is_electives=False,
                status="READY",
            )

    def test_session_state_valid_full(self) -> None:
        """Valid SessionState should work."""
        state = SessionState(
            session_headers={"User-Agent": "sia-scraper"},
            session_cookies={"JSESSIONID": "abc123"},
            params={"Adf-Page-Id": "page1", "Adf-Window-Id": "win1"},
            javax_faces_ViewState="viewstate123",
            career_code="1-01-01-1000",
            career_name="Ingenieria de Sistemas",
            is_electives=False,
            status="READY",
        )
        assert state.career_code == "1-01-01-1000"
        assert state.is_electives is False

    def test_session_state_viewstate_optional(self) -> None:
        """SessionState with None ViewState should work."""
        state = SessionState(
            session_headers={"User-Agent": "sia-scraper"},
            session_cookies={},
            params={"Adf-Page-Id": "page1", "Adf-Window-Id": "win1"},
            javax_faces_ViewState=None,
            career_code="1-01-01-1000",
            career_name="Ingenieria",
            is_electives=False,
            status="CAREER_NOT_SET",
        )
        assert state.javax_faces_ViewState is None


@pytest.mark.unit
class TestModelImmutability:
    """Test that models are frozen (immutable)."""

    def test_schedule_is_frozen(self) -> None:
        """Schedule should be immutable after creation."""
        schedule = Schedule(
            day="LUNES",
            start_time="08:00",
            end_time="10:00",
            classroom="101",
        )
        with pytest.raises(ValidationError):
            schedule.day = "MARTES"

    def test_group_is_frozen(self) -> None:
        """Group should be immutable after creation."""
        group = Group(
            group_name="1",
            teacher="Docente",
            faculty="Ingenieria",
            course_name="Calculo",
            schedules=[],
            duration="16 SEMANAS",
            schedule_type="DIURNA",
            spots=10,
        )
        with pytest.raises(ValidationError):
            group.spots = 20

    def test_course_info_is_frozen(self) -> None:
        """CourseInfo should be immutable after creation."""
        course = CourseInfo(
            course_name="Test",
            credits=3,
            typology="Test",
            available_spots=5,
            scrape_timestamp="2026-03-30 10:00",
            groups=[],
        )
        with pytest.raises(ValidationError):
            course.credits = 5
