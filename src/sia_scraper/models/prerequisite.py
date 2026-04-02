"""Typed prerequisite payload models used for Rust bridge parsing.

.. deprecated::
    Use `sia_scraper_rust.CoursePrereqsModel`, `sia_scraper_rust.PrereqConditionModel`,
    and `sia_scraper_rust.PrerequisiteModel` directly instead. These Python models
    will be removed in version 3.1.0.
"""

# ruff: noqa: E402
import warnings

warnings.warn(
    "sia_scraper.models.prerequisite is deprecated; use sia_scraper_rust.CoursePrereqsModel instead",
    DeprecationWarning,
    stacklevel=2,
)

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class PrerequisiteEntryTyped(BaseModel):
    """One prerequisite course entry."""

    model_config = ConfigDict(strict=True, extra="forbid")

    course_code: str = Field(default="")
    course_name: str = Field(default="")


class PrereqConditionTyped(BaseModel):
    """Typed prerequisite condition payload."""

    model_config = ConfigDict(strict=True, extra="forbid")

    condition: int = Field(default=0, ge=0)
    prereq_type: str = Field(
        default="UNKNOWN", validation_alias=AliasChoices("prereq_type", "type")
    )
    all_required: bool = Field(default=False)
    number_of_courses: int = Field(default=0, ge=0)
    prerequisites: list[PrerequisiteEntryTyped] = Field(default_factory=list)


class CoursePrereqsTyped(BaseModel):
    """Typed prerequisite parse result from Rust parser."""

    model_config = ConfigDict(strict=True, extra="forbid")

    course_name: str = Field(..., min_length=1)
    code: str | None = None
    credits: int = Field(..., ge=0, le=30)
    typology: str = Field(..., min_length=1)
    conditions: list[PrereqConditionTyped] = Field(default_factory=list)

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.isdigit() or len(value) != 7:
            raise ValueError(f"Course code must be 7 digits, got '{value}'")
        return value
