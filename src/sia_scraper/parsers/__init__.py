"""SIA HTML/XML Parsing Package.

This package provides functions for parsing course data from Oracle ADF XML/HTML
responses returned by SIA's web interface.

## Modules

| Module | Purpose |
|--------|---------|
| `html_parser` | Low-level HTML/XML parsing with lxml |
| `course_parser` | Course info and prerequisites extraction |
| `models` | Dataclasses for type-safe data structures |
"""

from ..html_parser import HtmlParser, from_html, from_string, from_xml, get_course_list
from .course_parser import get_plain_text, scrape_info, scrape_prereqs
from .models import (
    CourseInfo,
    CoursePrereqs,
    Group,
    PrereqCondition,
    Prerequisite,
    Schedule,
)

__all__ = [
    # HtmlParser
    "HtmlParser",
    "from_html",
    "from_string",
    "from_xml",
    "get_course_list",
    # Course Parser
    "get_plain_text",
    "scrape_info",
    "scrape_prereqs",
    # Models
    "CourseInfo",
    "CoursePrereqs",
    "Group",
    "PrereqCondition",
    "Prerequisite",
    "Schedule",
]
