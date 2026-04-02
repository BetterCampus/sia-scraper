"""Typed models for Rust/Python boundary payloads.

.. deprecated::
    Use `sia_scraper_rust` module models directly instead. These Python models
    will be removed in version 3.1.0.
"""

# ruff: noqa: E402
import warnings

warnings.warn(
    "sia_scraper.models is deprecated; use sia_scraper_rust models instead",
    DeprecationWarning,
    stacklevel=2,
)

from .course import CourseInfoTyped, GroupTyped, ScheduleTyped  # noqa: E402
from .prerequisite import (  # noqa: E402
    CoursePrereqsTyped,
    PrereqConditionTyped,
    PrerequisiteEntryTyped,
)
from .session import CourseListEntryTyped, SessionStateTyped  # noqa: E402

__all__ = [
    "CourseInfoTyped",
    "GroupTyped",
    "ScheduleTyped",
    "CoursePrereqsTyped",
    "PrereqConditionTyped",
    "PrerequisiteEntryTyped",
    "CourseListEntryTyped",
    "SessionStateTyped",
]
