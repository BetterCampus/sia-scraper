"""Pydantic models for SIA course data structures.

This module provides explicit type definitions for all course-related data
returned by SIA scraper functions, replacing implicit dict structures with
type-safe Pydantic models for runtime validation.
"""

import re

from pydantic import BaseModel, Field, field_validator


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
        if v is None:
            return "Unknown"
        cleaned = str(v).strip()
        return cleaned if cleaned else "Unknown"

    @field_validator("teacher", mode="before")
    @classmethod
    def clean_teacher(cls, v: str | None) -> str:
        """Clean and set default for teacher."""
        if v is None:
            return "Not reported"
        cleaned = str(v).strip()
        return cleaned if cleaned else "Not reported"

    @field_validator("faculty", mode="before")
    @classmethod
    def clean_faculty(cls, v: str | None) -> str:
        """Clean and set default for faculty."""
        if v is None:
            return "Unknown"
        cleaned = str(v).strip()
        return cleaned if cleaned else "Unknown"

    @field_validator("duration", mode="before")
    @classmethod
    def clean_duration(cls, v: str | None) -> str:
        """Clean and set default for duration."""
        if v is None:
            return "Unknown"
        cleaned = str(v).strip()
        return cleaned if cleaned else "Unknown"

    @field_validator("schedule_type", mode="before")
    @classmethod
    def clean_schedule_type(cls, v: str | None) -> str:
        """Clean and set default for schedule_type."""
        if v is None:
            return "Unknown"
        cleaned = str(v).strip()
        return cleaned if cleaned else "Unknown"

    @field_validator("code")
    @classmethod
    def validate_course_code(cls, v: str | None) -> str | None:
        """Ensure course code is 7 digits or None/empty."""
        if v is None or v == "":
            return None
        if not v.isdigit() or len(v) != 7:
            raise ValueError(f"Course code must be 7 digits, got '{v}'")
        return v


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
        if v is None:
            return "Unknown"
        cleaned = str(v).strip()
        return cleaned if cleaned else "Unknown"

    @field_validator("code")
    @classmethod
    def validate_course_code(cls, v: str | None) -> str | None:
        """Ensure course code is 7 digits or None."""
        if v is not None and (not v.isdigit() or len(v) != 7):
            raise ValueError(f"Course code must be 7 digits, got '{v}'")
        return v


class Prerequisite(BaseModel):
    """A prerequisite course.

    Attributes:
        course_code: Course code (e.g., "2016489")
        course_name: Course name
    """

    model_config = {"frozen": True, "populate_by_name": True}

    course_code: str = Field(default="", description="Course code")
    course_name: str = Field(default="", description="Course name")


class PrereqCondition(BaseModel):
    """Prerequisite condition with list of required courses.

    Attributes:
        condition: Condition type from SIA (e.g., "Must pass ALL")
        type: Condition type
        all_required: Whether all courses are required ("Si" or "No")
        number_of_courses: Number of required courses
        prerequisites: List of prerequisite courses
    """

    model_config = {"frozen": True, "populate_by_name": True}

    condition: str = Field(default="", description="Condition description")
    type: str = Field(default="", description="Condition type")
    all_required: str = Field(default="", description="Whether all are required")
    number_of_courses: str = Field(default="", description="Number of required courses")
    prerequisites: list[Prerequisite] = Field(
        default_factory=list, description="List of prerequisite courses"
    )


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
        if v is None or v == "":
            return None
        if not v.isdigit() or len(v) != 7:
            raise ValueError(f"Course code must be 7 digits, got '{v}'")
        return v

    @field_validator("typology", mode="before")
    @classmethod
    def clean_typology(cls, v: str | None) -> str:
        """Clean and set default for typology."""
        if v is None:
            return "Unknown"
        cleaned = str(v).strip()
        if not cleaned:
            return "Unknown"
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
        STATUS: Current session status as string
    """

    model_config = {"frozen": True, "populate_by_name": True}

    session_headers: dict[str, str] = Field(..., description="HTTP session headers")
    session_cookies: dict[str, str] = Field(..., description="HTTP session cookies")
    params: dict[str, str] = Field(..., description="URL parameters including ADF IDs")
    javax_faces_ViewState: str | None = Field(default=None, description="JSF ViewState token")
    career_code: str = Field(default="", description="Career code (empty if no career set)")
    career_name: str = Field(default="", description="Career name (empty if no career set)")
    is_electives: bool = Field(..., description="Whether viewing elective courses")
    STATUS: str = Field(..., description="Session status name")

    @field_validator("params")
    @classmethod
    def validate_params(cls, v: dict[str, str]) -> dict[str, str]:
        """Ensure required ADF parameters are present."""
        required_keys = ["Adf-Page-Id", "Adf-Window-Id"]
        missing = [key for key in required_keys if key not in v]
        if missing:
            raise ValueError(f"Missing required ADF parameters: {missing}")
        return v
