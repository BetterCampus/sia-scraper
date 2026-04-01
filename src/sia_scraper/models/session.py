"""Typed session models for Rust/Python transport payloads."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

ALLOWED_SESSION_STATUSES = {
    "NO_SESSION",
    "CAREER_NOT_SET",
    "ON_CAREER_PAGE",
    "ON_COURSE_PAGE",
}


class CourseListEntryTyped(BaseModel):
    """One typed course row from session state."""

    model_config = ConfigDict(strict=True, extra="forbid")

    course_code: str = Field(..., min_length=1)
    course_name: str = Field(default="")


class SessionStateTyped(BaseModel):
    """Typed session payload from Rust session endpoints."""

    model_config = ConfigDict(strict=True, extra="forbid")

    session_headers: dict[str, str] = Field(default_factory=dict)
    session_cookies: dict[str, str] = Field(default_factory=dict)
    params: dict[str, str] = Field(default_factory=dict)
    javax_faces_ViewState: str | None = None
    career_code: str = ""
    career_name: str = "N/A"
    is_electives: bool = False
    status: str = Field(default="NO_SESSION")
    course_list: list[CourseListEntryTyped] = Field(default_factory=list)

    @field_validator("params")
    @classmethod
    def validate_params(cls, value: dict[str, str]) -> dict[str, str]:
        required = {"Adf-Page-Id", "Adf-Window-Id"}
        missing = sorted(required - set(value))
        if missing:
            raise ValueError(f"Missing required ADF parameters: {missing}")
        return value

    @field_validator("career_code")
    @classmethod
    def validate_career_code(cls, value: str) -> str:
        if value == "":
            return value
        segments = value.split("-")
        if len(segments) != 4 or any(segment == "" for segment in segments):
            raise ValueError("career_code must have 4 non-empty segments separated by '-'")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in ALLOWED_SESSION_STATUSES:
            raise ValueError(
                "Invalid session status "
                f"'{value}'. Expected one of: {sorted(ALLOWED_SESSION_STATUSES)}"
            )
        return value

    def course_list_as_dicts(self) -> list[dict[str, str]]:
        """Return legacy course-list shape for existing call sites."""
        return [{entry.course_code: entry.course_name} for entry in self.course_list]
