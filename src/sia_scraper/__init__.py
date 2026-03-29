"""SIA Scraper Library.

A Python library for extracting academic information from Universidad Nacional de Colombia's
SIA (Sistema de Información Académica) system, which is built on Oracle Application
Development Framework (ADF).

## Overview

This library provides tools to scrape course information from SIA's public course catalog,
including:
- Course details (name, credits, typology)
- Schedule information (days, times, classrooms)
- Course groups and available spots
- Prerequisites and enrollment conditions

## Architecture

The library is organized into several modules:

| Module | Purpose |
|--------|---------|
| `session.py` | Core HTTP session management and Oracle ADF state handling |
| `enhanced_session.py` | HTTP session wrapper with automatic timeout handling |
| `scraper.py` | High-level facade for course data extraction |
| `constants/` | Package with Oracle ADF component IDs, request templates, and status enums |
| `date_formatter.py` | Datetime formatting utilities |

## Quick Start

```python
from sia_scraper import SiaScraper

# Create scraper and navigate to a career
scraper = SiaScraper()
scraper.set_career("0-2-8-3")  # Computer Science in Bogotá

# Get course information
course = scraper.get_course_info(course_code="2016489")
print(course["courseName"])
print(f"Credits: {course['credits']}")
print(f"Groups: {len(course['groups'])}")

# Get prerequisites
prereqs = scraper.get_course_prereqs(course_code="2016489")
print(f"Conditions: {len(prereqs['conditions'])}")

# Clean up
scraper.close_session()
```

## Session Persistence

Sessions can be serialized and restored to avoid repeated authentication:

```python
from sia_scraper import SiaScraper, init_sia_scraper

# First time: create session and save it
scraper = SiaScraper()
scraper.set_career("0-2-8-3")
session_data = scraper.get_session_data()

# Later: restore session
scraper = SiaScraper(session_data=session_data)
# Session is restored with career and course list intact
```

## Career Search Codes

Career search codes follow the format `{level}-{campus}-{faculty}-{career}`.
These codes correspond to dropdown positions in SIA's course catalog interface.

## Warning

This library interacts with SIA's Oracle ADF infrastructure which may change
without notice. Component IDs and request formats are brittle dependencies.
"""

from .constants import SiaSessionStatus
from .date_formatter import DateFormatter
from .decorators import check_career, check_session, check_status, handle_timeout_error
from .enhanced_session import EnhancedSession
from .exceptions import SiaSessionException
from .scraper import SiaScraper, create_career_session, init_sia_scraper
from .session import SiaSession

__all__ = [
    "SiaScraper",
    "SiaSession",
    "SiaSessionException",
    "SiaSessionStatus",
    "EnhancedSession",
    "DateFormatter",
    "check_career",
    "check_session",
    "check_status",
    "handle_timeout_error",
    "init_sia_scraper",
    "create_career_session",
]
