"""Pydantic models for SIA course data structures.

This module provides explicit type definitions for all course-related data
returned by SIA scraper functions, replacing implicit dict structures with
type-safe Pydantic models for runtime validation.
"""

import re
from enum import Enum

from pydantic import BaseModel, Field, field_validator

from ..constants.defaults import (
    DEFAULT_CAREER_NAME,
    DEFAULT_DURATION,
    DEFAULT_FACULTY,
    DEFAULT_GROUP_NAME,
    DEFAULT_SCHEDULE_TYPE,
    DEFAULT_TEACHER,
    DEFAULT_TYPOLOGY,
)


def _clean_string_field(value: str | None, default: str) -> str:
    """Clean optional string field and apply fallback default."""
    if value is None:
        return default
    cleaned = str(value).strip()
    return cleaned if cleaned else default


def _validate_course_code(value: str | None, allow_empty: bool = True) -> str | None:
    """Validate 7-digit course code.

    Args:
        value: Raw code value.
        allow_empty: Whether empty string should be normalized to None.

    Returns:
        Normalized code or None.

    Raises:
        ValueError: If code is not a 7-digit numeric string.
    """
    if value is None:
        return None

    if value == "":
        if allow_empty:
            return None
        raise ValueError("Course code cannot be empty")

    if not value.isdigit() or len(value) != 7:
        raise ValueError(f"Course code must be 7 digits, got '{value}'")
    return value


class Schedule(BaseModel):
    """Schedule entry for a course group.

    Attributes:
        day: Day of week (e.g., "LUNES", "MARTES")
        start_time: Start time in "HH:MM" format (24-hour)
        end_time: End time in "HH:MM" format (24-hour)
        classroom: Classroom location (may be empty string)
    """

    model_config = {"frozen": True, "populate_by_name": True}

    day: str = Field(..., min_length=1, description="Day of week")
    start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="Start time in HH:MM format")
    end_time: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="End time in HH:MM format")
    classroom: str = Field(default="", description="Classroom location")

    @field_validator("classroom", mode="before")
    @classmethod
    def clean_classroom(cls, v: str | None) -> str:
        """Clean and normalize classroom value."""
        if v is None:
            return ""
        cleaned = str(v).strip()
        return cleaned if cleaned else ""

    @field_validator("end_time")
    @classmethod
    def validate_end_after_start(cls, v: str, info) -> str:
        """Ensure end_time is after start_time."""
        if "start_time" in info.data:
            start = info.data["start_time"]
            if v <= start:
                raise ValueError(f"end_time ({v}) must be after start_time ({start})")
        return v


class Group(BaseModel):
    """Course group with teacher, schedules, and availability.

    Attributes:
        group_name: Group identifier (e.g., "1", "CA")
        teacher: Teacher name
        faculty: Faculty/school name
        course_name: Course name
        schedules: List of schedule entries
        duration: Duration string (e.g., "16 SEMANAS")
        schedule_type: Schedule type (e.g., "DIURNA")
        spots: Available spots (None if unavailable)
        code: Course code (optional, 7 digits)
    """

    model_config = {"frozen": True, "populate_by_name": True}

    group_name: str = Field(..., min_length=1, description="Group identifier")
    teacher: str = Field(..., min_length=1, description="Teacher name")
    faculty: str = Field(..., min_length=1, description="Faculty or school name")
    course_name: str = Field(..., min_length=1, description="Course name")
    schedules: list[Schedule] = Field(default_factory=list, description="List of schedules")
    duration: str = Field(..., min_length=1, description="Duration string")
    schedule_type: str = Field(..., min_length=1, description="Schedule type")
    spots: int | None = Field(default=None, ge=0, description="Available spots")
    code: str | None = Field(default=None, description="7-digit course code")

    @field_validator("group_name", mode="before")
    @classmethod
    def clean_group_name(cls, v: str | None) -> str:
        """Clean and set default for group_name."""
        return _clean_string_field(v, DEFAULT_GROUP_NAME)

    @field_validator("teacher", mode="before")
    @classmethod
    def clean_teacher(cls, v: str | None) -> str:
        """Clean and set default for teacher."""
        return _clean_string_field(v, DEFAULT_TEACHER)

    @field_validator("faculty", mode="before")
    @classmethod
    def clean_faculty(cls, v: str | None) -> str:
        """Clean and set default for faculty."""
        return _clean_string_field(v, DEFAULT_FACULTY)

    @field_validator("duration", mode="before")
    @classmethod
    def clean_duration(cls, v: str | None) -> str:
        """Clean and set default for duration."""
        return _clean_string_field(v, DEFAULT_DURATION)

    @field_validator("schedule_type", mode="before")
    @classmethod
    def clean_schedule_type(cls, v: str | None) -> str:
        """Clean and set default for schedule_type."""
        return _clean_string_field(v, DEFAULT_SCHEDULE_TYPE)

    @field_validator("code")
    @classmethod
    def validate_course_code(cls, v: str | None) -> str | None:
        """Ensure course code is 7 digits or None/empty."""
        return _validate_course_code(v)


class CourseInfo(BaseModel):
    """Complete course information including all groups and schedules.

    Attributes:
        course_name: Full course name
        credits: Credit hours (typical range 0-30)
        typology: Course typology
        available_spots: Total available spots across all groups
        scrape_timestamp: Timestamp when data was scraped in "YYYY-MM-DD HH:MM" format
        groups: List of course groups
        code: Course code (optional, 7 digits)
    """

    model_config = {"frozen": True, "populate_by_name": True}

    course_name: str = Field(..., min_length=1, description="Full course name")
    credits: int = Field(..., ge=0, le=30, description="Credit hours")
    typology: str = Field(..., min_length=1, description="Course typology")
    available_spots: int = Field(..., ge=0, description="Total available spots")
    scrape_timestamp: str = Field(
        ...,
        pattern=r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$",
        description="Timestamp in YYYY-MM-DD HH:MM format",
    )
    groups: list[Group] = Field(default_factory=list, description="List of course groups")
    code: str | None = Field(default=None, description="7-digit course code")

    @field_validator("course_name", mode="before")
    @classmethod
    def clean_course_name(cls, v: str | None) -> str:
        """Clean course name value."""
        if v is None:
            raise ValueError("course_name cannot be None")
        cleaned = str(v).strip()
        if not cleaned:
            raise ValueError("course_name cannot be empty")
        return cleaned

    @field_validator("typology", mode="before")
    @classmethod
    def clean_typology(cls, v: str | None) -> str:
        """Clean and set default for typology."""
        return _clean_string_field(v, DEFAULT_TYPOLOGY)

    @field_validator("code")
    @classmethod
    def validate_course_code(cls, v: str | None) -> str | None:
        """Ensure course code is 7 digits or None."""
        return _validate_course_code(v, allow_empty=False)


class Prerequisite(BaseModel):
    """A prerequisite course.

    Attributes:
        course_code: Course code (e.g., "2016489")
        course_name: Course name
    """

    model_config = {"frozen": True, "populate_by_name": True}

    course_code: str = Field(default="", description="Course code")
    course_name: str = Field(default="", description="Course name")


class PrereqType(str, Enum):
    """SIA prerequisite condition type codes.

    Attributes:
        M: Cannot enroll without passing prerequisite.
        O: Can enroll, but cannot be graded without passing prerequisite.
        E: Must enroll simultaneously or have enrolled before.
        A: Cancellation due to incompatibility.
        UNKNOWN: Fallback for unrecognized future SIA type codes.
    """

    M = "M"
    O = "O"  # noqa: E741
    E = "E"
    A = "A"
    UNKNOWN = "UNKNOWN"


class PrereqCondition(BaseModel):
    """Prerequisite condition with list of required courses.

    Attributes:
        condition: Condition number from SIA.
        type: Prerequisite condition type code.
        all_required: Whether all listed courses are required.
        number_of_courses: Number of listed prerequisite courses.
        prerequisites: List of prerequisite courses
    """

    model_config = {"frozen": True, "populate_by_name": True}

    condition: int = Field(default=0, ge=0, description="Condition number")
    type: PrereqType = Field(
        default=PrereqType.UNKNOWN,
        description="Prerequisite type code (M/O/E/A/UNKNOWN)",
    )
    all_required: bool = Field(default=False, description="Whether all listed courses are required")
    number_of_courses: int = Field(default=0, ge=0, description="Number of required courses")
    prerequisites: list[Prerequisite] = Field(
        default_factory=list, description="List of prerequisite courses"
    )

    @staticmethod
    def _normalize_token(value: object) -> str:
        """Normalize input token by stripping whitespace and brackets."""
        token = str(value).strip()
        if token.startswith("[") and token.endswith("]"):
            token = token[1:-1].strip()
        return token

    @field_validator("condition", mode="before")
    @classmethod
    def parse_condition(cls, v: object) -> int:
        """Parse condition number from SIA value."""
        if v is None:
            return 0
        token = cls._normalize_token(v)
        if not token:
            return 0

        if token.isdigit():
            return int(token)

        match = re.search(r"(\d+)", token)
        if match:
            return int(match.group(1))

        raise ValueError(f"Condition must contain a number, got '{v}'")

    @field_validator("type", mode="before")
    @classmethod
    def parse_type(cls, v: object) -> PrereqType:
        """Map raw SIA prerequisite type to PrereqType enum."""
        if isinstance(v, PrereqType):
            return v
        if v is None:
            return PrereqType.UNKNOWN
        token = cls._normalize_token(v).upper()
        if not token:
            return PrereqType.UNKNOWN

        try:
            return PrereqType(token)
        except ValueError:
            return PrereqType.UNKNOWN

    @field_validator("all_required", mode="before")
    @classmethod
    def parse_all_required(cls, v: object) -> bool:
        """Parse all_required flag from SIA values (S/N, SI/NO)."""
        if isinstance(v, bool):
            return v
        if v is None:
            return False
        token = cls._normalize_token(v).upper()
        if token in {"S", "SI"}:
            return True
        if token in {"N", "NO"}:
            return False
        return False

    @field_validator("number_of_courses", mode="before")
    @classmethod
    def parse_number_of_courses(cls, v: object) -> int:
        """Parse number of prerequisite courses from SIA value."""
        if v is None:
            return 0
        token = cls._normalize_token(v)
        if not token:
            return 0
        if token.isdigit():
            return int(token)
        raise ValueError(f"number_of_courses must be numeric, got '{v}'")


class CoursePrereqs(BaseModel):
    """Course prerequisites and enrollment conditions.

    Attributes:
        course_name: Course name with code
        code: Course code (7 digits)
        credits: Credit hours
        typology: Course typology
        conditions: List of prerequisite conditions
    """

    model_config = {"frozen": True, "populate_by_name": True}

    course_name: str = Field(..., min_length=1, description="Course name with code")
    code: str | None = Field(default=None, description="7-digit course code")
    credits: int = Field(..., ge=0, le=30, description="Credit hours")
    typology: str = Field(..., min_length=1, description="Course typology")
    conditions: list[PrereqCondition] = Field(
        default_factory=list, description="List of prerequisite conditions"
    )

    @field_validator("code", mode="before")
    @classmethod
    def extract_code_from_name(cls, v: str | None, info) -> str | None:
        """Extract course code from course_name if code not explicitly provided."""
        if v is not None:
            return v
        course_name = info.data.get("course_name")
        if course_name:
            match = re.search(r"\((\d+)\)$", str(course_name).strip())
            if match:
                code = match.group(1)
                if len(code) == 7 and code.isdigit():
                    return code
        return None

    @field_validator("code")
    @classmethod
    def validate_course_code(cls, v: str | None) -> str | None:
        """Ensure course code is 7 digits or None/empty."""
        return _validate_course_code(v)

    @field_validator("typology", mode="before")
    @classmethod
    def clean_typology(cls, v: str | None) -> str:
        """Clean and set default for typology."""
        cleaned = _clean_string_field(v, DEFAULT_TYPOLOGY)
        if ": " in cleaned:
            cleaned = cleaned.split(": ")[-1]
        return cleaned


class SessionState(BaseModel):
    """Session state for serialization and persistence.

    This model encapsulates all data required to restore a SIA session,
    including HTTP headers, cookies, Oracle ADF tokens, and career context.

    Attributes:
        session_headers: HTTP headers from the session
        session_cookies: HTTP cookies from the session
        params: URL parameters including Oracle ADF identifiers
        javax_faces_ViewState: JSF ViewState token for Oracle ADF requests
        career_code: Hyphen-delimited career code (level-campus-faculty-career)
        career_name: Name of the academic program
        is_electives: Whether the current view shows elective courses
        status: Current session status as string
    """

    model_config = {"frozen": True, "populate_by_name": True}

    session_headers: dict[str, str] = Field(..., description="HTTP session headers")
    session_cookies: dict[str, str] = Field(..., description="HTTP session cookies")
    params: dict[str, str] = Field(..., description="URL parameters including ADF IDs")
    javax_faces_ViewState: str | None = Field(default=None, description="JSF ViewState token")
    career_code: str = Field(default="", description="Career code (empty if no career set)")
    career_name: str = Field(
        default=DEFAULT_CAREER_NAME,
        description="Career name (default if no career set)",
    )
    is_electives: bool = Field(..., description="Whether viewing elective courses")
    status: str = Field(..., description="Session status name")

    @field_validator("params")
    @classmethod
    def validate_params(cls, v: dict[str, str]) -> dict[str, str]:
        """Ensure required ADF parameters are present."""
        required_keys = ["Adf-Page-Id", "Adf-Window-Id"]
        missing = [key for key in required_keys if key not in v]
        if missing:
            raise ValueError(f"Missing required ADF parameters: {missing}")
        return v


class ScrapeResult(BaseModel):
    """Result from batch scraping operation.

    This model encapsulates the outcome of a batch scrape operation,
    including success/failure counts and detailed results.

    Attributes:
        successes: List of successfully scraped courses
        failures: List of (index, error_message) tuples for failed scrapes
        total: Total number of courses attempted
        success_rate: Percentage of successful scrapes (0-100)
    """

    model_config = {"frozen": True, "populate_by_name": True}

    successes: list[CourseInfo] = Field(
        default_factory=list, description="Successfully scraped courses"
    )
    failures: list[tuple[int, str]] = Field(
        default_factory=list, description="Failed scrape attempts as (index, error)"
    )
    total: int = Field(ge=0, description="Total courses attempted")
    success_rate: float = Field(ge=0, le=100, description="Success rate as percentage")

    @classmethod
    def create(
        cls,
        successes: list[CourseInfo],
        failures: list[tuple[int, str]],
    ) -> "ScrapeResult":
        """Create a ScrapeResult with calculated success rate."""
        total = len(successes) + len(failures)
        success_rate = (len(successes) / total * 100) if total > 0 else 0.0
        return cls(
            successes=successes,
            failures=failures,
            total=total,
            success_rate=round(success_rate, 2),
        )


class ErrorMode(str, Enum):
    """Error handling mode for batch scraping operations."""

    SKIP = "skip"
    RETRY = "retry"
    ABORT = "abort"
