# Migration Guide: v0.1.0 -> v0.2.0

## Overview

Version `0.2.0` includes breaking API changes focused on:

- Modern Python conventions (snake_case attributes, simplified APIs)
- Improved exception handling and defensive parsing behavior
- Oracle ADF ViewState auto-synchronization for more reliable navigation

## Breaking Changes

### 1) Model field names now use snake_case

All parser dataclass fields were renamed from camelCase to snake_case.

Before (`v0.1.0`):

```python
course.courseName
course.courseId
course.courseCode
course.teacherName
course.enrolledStudents
course.totalSpots
course.availableSpots
```

After (`v0.2.0`):

```python
course.course_name
course.course_id
course.course_code
course.teacher_name
course.enrolled_students
course.total_spots
course.available_spots
```

Additional renamed fields:

- `courseSchedule` -> `course_schedule`
- `dayOfWeek` -> `day_of_week`
- `startTime` -> `start_time`
- `endTime` -> `end_time`
- `groupName` -> `group_name`
- `scheduleType` -> `schedule_type`
- `scrapeTimestamp` -> `scrape_timestamp`

### 2) `DateFormatter` class replaced by `format_date()`

The `DateFormatter` class was removed and replaced with a plain helper function.

Before:

```python
from sia_scraper import DateFormatter

formatter = DateFormatter(dt)
formatted = formatter.format_date()
```

After:

```python
from sia_scraper import format_date

formatted = format_date(dt)
```

### 3) `get_course_index()` now raises `ValueError`

`get_course_index()` no longer returns `-1` when a course code is not found.
It now raises `ValueError`.

Before:

```python
index = scraper.get_course_index(code)
if index == -1:
    handle_missing_course()
else:
    scrape(index)
```

After:

```python
try:
    index = scraper.get_course_index(code)
    scrape(index)
except ValueError:
    handle_missing_course()
```

### 4) `spots` uses `None` instead of the string `"NaN"`

When spots are not available, the parser now returns `None`.

Before:

```python
if group.spots == "NaN":
    ...
```

After:

```python
if group.spots is None:
    ...
```

### 5) Removed exports

The following symbols were removed from public exports:

- `check_career`
- `from_html`
- `from_string`
- `from_xml`

Use `HtmlParser(...)` directly instead of those parser helper exports.

### 6) Exception hierarchy corrected

Session-related sub-exceptions now properly inherit from `SiaSessionException`.

This means broad handling now works correctly:

```python
from sia_scraper.exceptions import SiaSessionException

try:
    # SIA session operations
    ...
except SiaSessionException:
    # catches InvalidStatus, SessionNotSet, TimeoutError, etc.
    ...
```

## Quick Migration

Use these targeted find/replace patterns to accelerate migration.

### Common attribute replacements

```text
.courseName -> .course_name
.courseId -> .course_id
.courseCode -> .course_code
.teacherName -> .teacher_name
.enrolledStudents -> .enrolled_students
.totalSpots -> .total_spots
.availableSpots -> .available_spots
.courseSchedule -> .course_schedule
.dayOfWeek -> .day_of_week
.startTime -> .start_time
.endTime -> .end_time
.groupName -> .group_name
.scheduleType -> .schedule_type
.scrapeTimestamp -> .scrape_timestamp
```

### Formatter replacement

```text
DateFormatter(<expr>).format_date() -> format_date(<expr>)
```

### Spots checks

```text
== "NaN" -> is None
!= "NaN" -> is not None
```

### Course index checks

`if index == -1` patterns need manual conversion to `try/except ValueError`.

## Non-Breaking Improvements

### ViewState auto-sync for Oracle ADF

`SiaSession.post_request()` now syncs ViewState after each POST response.
This removes the need for manual `update_view_state()` calls between actions and
reduces extra request round-trips.

### Defensive parser behavior

- Added bounds checks in HTML parser row extraction
- Added safer guards around malformed prerequisite/name parsing
- Reduced brittle index-based assumptions in course parsing logic

### Internal maintainability improvements

- Reduced name-mangled private attribute coupling
- Replaced print-based debug output with `logging`
- Improved parser internals (`HtmlElement` iteration, selector caching)

## Upgrade Checklist

- [ ] Update all dataclass attribute access to snake_case names
- [ ] Replace `DateFormatter` usage with `format_date()`
- [ ] Update `get_course_index()` callers to catch `ValueError`
- [ ] Replace `"NaN"` checks with `None` checks for `spots`
- [ ] Remove imports of deleted exports (`check_career`, `from_html`, `from_string`, `from_xml`)
- [ ] Verify broad exception handling now catches `SiaSessionException` subclasses
- [ ] Run tests and static checks

## Validation Commands

```bash
pytest
ruff check --fix . && ruff format . && ruff check .
pyright
```

## v0.2.0 -> v0.2.1

### Internal module reorganization

Version `0.2.1` reorganizes internal modules into `core/` and `utils/` to make
the package layout easier to navigate and maintain.

- `core/`: `adf_state.py`, `enhanced_session.py`, `exceptions.py`, `oracle_adf_request.py`
- `utils/`: `date_formatter.py`, `decorators.py`, `debug.py`
- Top-level orchestrators remain `session.py` and `scraper.py`

### Public API impact

No public API changes are required for normal usage. Imports from
`sia_scraper` root continue to work.

```python
from sia_scraper import SiaScraper, SiaSessionException, format_date
```
