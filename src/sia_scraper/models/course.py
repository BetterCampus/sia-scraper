"""Typed course payload models used for Rust bridge parsing.

.. deprecated::
    Use `sia_scraper_rust.CourseInfoModel`, `sia_scraper_rust.GroupModel`,
    and `sia_scraper_rust.ScheduleModel` directly instead. These Python models
    will be removed in version 3.1.0.
"""

# ruff: noqa: E402
import warnings

warnings.warn(
    "sia_scraper.models.course is deprecated; use sia_scraper_rust CourseInfoModel instead",
    DeprecationWarning,
    stacklevel=2,
)

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ScheduleTyped(BaseModel):
    """One course schedule entry."""

    model_config = ConfigDict(strict=True, extra="forbid")

    day: str = Field(..., min_length=1)
    start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    classroom: str = Field(default="")


class GroupTyped(BaseModel):
    """One course group entry."""

    model_config = ConfigDict(strict=True, extra="forbid")

    group_name: str = Field(..., min_length=1)
    teacher: str = Field(..., min_length=1)
    faculty: str = Field(default="")
    course_name: str = Field(..., min_length=1)
    schedules: list[ScheduleTyped] = Field(default_factory=list)
    duration: str = Field(default="")
    schedule_type: str = Field(default="")
    spots: int | None = Field(default=None, ge=0)
    code: str | None = None

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.isdigit() or len(value) != 7:
            raise ValueError(f"Course code must be 7 digits, got '{value}'")
        return value


class CourseInfoTyped(BaseModel):
    """Typed course payload from Rust parser."""

    model_config = ConfigDict(strict=True, extra="forbid")

    course_name: str = Field(..., min_length=1)
    credits: int = Field(..., ge=0, le=30)
    typology: str = Field(..., min_length=1)
    available_spots: int = Field(..., ge=0)
    scrape_timestamp: str
    groups: list[GroupTyped] = Field(default_factory=list)
    code: str | None = None

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.isdigit() or len(value) != 7:
            raise ValueError(f"Course code must be 7 digits, got '{value}'")
        return value
