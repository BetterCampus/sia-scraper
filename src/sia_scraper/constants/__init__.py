"""SIA System Constants.

This package contains all constants, identifiers, and configuration values for interacting
with Universidad Nacional de Colombia's SIA (Sistema de Información Académica) system,
which is built on Oracle Application Development Framework (ADF).

## Modules

| Module | Purpose |
|--------|---------|
| `http` | HTTP configuration (timeouts, headers, URLs) |
| `adf_ids` | Oracle ADF component IDs |
| `adf_events` | Oracle ADF XML event payloads |
| `actions` | Action identifiers for UI interactions |
| `data_map` | Action-to-component mapping |
| `business` | Business logic constants (indices, offsets) |
| `status` | Session state enumeration |
"""

from .actions import (
    BACK_BTTN,
    CAMPUS_DD,
    CAMPUS_ELECTIVES_DD,
    CAREER_DD,
    COURSE_PAGE_LINK,
    FACULTY_CAREER_DD,
    FACULTY_DD,
    SELECT_ROW,
    SHOW_COURSES_BTTN,
    STUDY_LEVEL_DD,
    TIPOLOGY_DD,
)
from .adf_events import (
    BTTN_EVENT_VALUE,
    DROPDOWN_EVENT_VALUE,
    SELECT_ROW_EVENT_VALUE,
    SESSION_TIMEOUT_ALERT,
)
from .adf_ids import (
    BACK_BTTN_ID,
    CAMPUS_DD_ID,
    CAMPUS_ELECTIVES_DD_ID,
    CAREER_DD_ID,
    FACULTY_CAREER_DD_ID,
    FACULTY_DD_ID,
    ORACLE_ADF_REGION_ID,
    ORACLE_ADF_RENDER_TARGET,
    ORACLE_ADF_UNKNOWN_COMPONENT_1,
    ORACLE_ADF_UNKNOWN_COMPONENT_2,
    ORACLE_ADF_UNKNOWN_COMPONENT_3,
    ORACLE_ADF_UNKNOWN_COMPONENT_4,
    SELECT_ROW_ID,
    SHOW_COURSES_BTTN_ID,
    STUDY_LEVEL_DD_ID,
    TIPOLOGY_DD_ID,
)
from .business import (
    COURSE_CODE_COL,
    COURSE_NAME_COL,
    DROPDOWN_FIRST_OPTION_OFFSET,
    ELECTIVES_CAMPUS_INCREMENT,
    ELECTIVES_TYPOLOGY_INDEX,
    FACULTY_CAREER_DEFAULT_INDEX,
    GROUP_DURATION_INDEX,
    GROUP_FACULTY_INDEX,
    GROUP_SCHEDULE_TYPE_INDEX,
    GROUP_SCHEDULES_INDEX,
    GROUP_SPOTS_INDEX,
    GROUP_TEACHER_INDEX,
    MIN_CONDITION_DIVS,
    MIN_GROUP_DATA_LENGTH_WITH_SPOTS,
    PREREQ_DIV_START,
    REQUIRED_CONDITION_HEADERS,
    TIPOLOGY_VALUE_INDEX,
)
from .data_map import DATA_MAP, DROPDOWNS
from .http import ADF_ADS_PAGE_ID, DEFAULT_TIMEOUT, SIA_BASE_URL, SIA_HEADERS, VIEW_STATE_REGEX
from .status import SiaSessionStatus

__all__ = [
    # HTTP
    "DEFAULT_TIMEOUT",
    "SIA_BASE_URL",
    "SIA_HEADERS",
    "VIEW_STATE_REGEX",
    # ADF IDs
    "ADF_ADS_PAGE_ID",
    "BACK_BTTN_ID",
    "CAMPUS_DD_ID",
    "CAMPUS_ELECTIVES_DD_ID",
    "CAREER_DD_ID",
    "FACULTY_CAREER_DD_ID",
    "FACULTY_DD_ID",
    "ORACLE_ADF_REGION_ID",
    "ORACLE_ADF_RENDER_TARGET",
    "ORACLE_ADF_UNKNOWN_COMPONENT_1",
    "ORACLE_ADF_UNKNOWN_COMPONENT_2",
    "ORACLE_ADF_UNKNOWN_COMPONENT_3",
    "ORACLE_ADF_UNKNOWN_COMPONENT_4",
    "SELECT_ROW_ID",
    "SHOW_COURSES_BTTN_ID",
    "STUDY_LEVEL_DD_ID",
    "TIPOLOGY_DD_ID",
    # ADF Events
    "BTTN_EVENT_VALUE",
    "DROPDOWN_EVENT_VALUE",
    "SELECT_ROW_EVENT_VALUE",
    "SESSION_TIMEOUT_ALERT",
    # Actions
    "BACK_BTTN",
    "CAMPUS_DD",
    "CAMPUS_ELECTIVES_DD",
    "CAREER_DD",
    "COURSE_PAGE_LINK",
    "FACULTY_CAREER_DD",
    "FACULTY_DD",
    "SELECT_ROW",
    "SHOW_COURSES_BTTN",
    "STUDY_LEVEL_DD",
    "TIPOLOGY_DD",
    # Data Map
    "DATA_MAP",
    "DROPDOWNS",
    # Business
    "COURSE_CODE_COL",
    "COURSE_NAME_COL",
    "DROPDOWN_FIRST_OPTION_OFFSET",
    "ELECTIVES_CAMPUS_INCREMENT",
    "ELECTIVES_TYPOLOGY_INDEX",
    "FACULTY_CAREER_DEFAULT_INDEX",
    "GROUP_DURATION_INDEX",
    "GROUP_FACULTY_INDEX",
    "GROUP_SCHEDULE_TYPE_INDEX",
    "GROUP_SCHEDULES_INDEX",
    "GROUP_SPOTS_INDEX",
    "GROUP_TEACHER_INDEX",
    "MIN_CONDITION_DIVS",
    "MIN_GROUP_DATA_LENGTH_WITH_SPOTS",
    "PREREQ_DIV_START",
    "REQUIRED_CONDITION_HEADERS",
    "TIPOLOGY_VALUE_INDEX",
    # Status
    "SiaSessionStatus",
]
