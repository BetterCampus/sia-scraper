"""Typed prerequisite payload models used for Rust bridge parsing."""

from __future__ import annotations

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

    def to_dict(self) -> dict[str, object]:
        """Backward-compatible dict helper during migration window."""
        import warnings

        warnings.warn(
            "CoursePrereqsTyped.to_dict() is deprecated; use typed fields directly.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.model_dump(by_alias=True)
