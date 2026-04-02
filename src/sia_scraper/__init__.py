"""SIA scraper public package API."""

import warnings

import sia_scraper_rust

from .constants import SiaSessionStatus
from .core import SiaSessionException
from .scraper import SiaScraper, create_career_session, init_sia_scraper
from .session import SiaSession
from .utils import format_date

warnings.warn(
    "sia_scraper module is deprecated; use sia_scraper_rust directly for 3.0 migration",
    DeprecationWarning,
    stacklevel=2,
)

CourseInfoModel = sia_scraper_rust.CourseInfoModel
CoursePrereqsModel = sia_scraper_rust.CoursePrereqsModel
SessionStateModel = sia_scraper_rust.SessionStateModel
CourseListEntryModel = sia_scraper_rust.CourseListEntryModel
GroupModel = sia_scraper_rust.GroupModel
ScheduleModel = sia_scraper_rust.ScheduleModel
PrereqConditionModel = sia_scraper_rust.PrereqConditionModel
PrerequisiteModel = sia_scraper_rust.PrerequisiteModel

__all__ = [
    "SiaScraper",
    "SiaSession",
    "SiaSessionException",
    "SiaSessionStatus",
    "format_date",
    "init_sia_scraper",
    "create_career_session",
    "CourseInfoModel",
    "CoursePrereqsModel",
    "SessionStateModel",
    "CourseListEntryModel",
    "GroupModel",
    "ScheduleModel",
    "PrereqConditionModel",
    "PrerequisiteModel",
]
