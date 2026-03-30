# Migration Guide: v0.x to v1.0

This guide covers breaking changes when upgrading from v0.x to v1.0.

## Overview

Version 1.0 introduces **Pydantic** for runtime validation of all data models. This provides better data integrity and clearer error messages but requires some changes to how you interact with models.

## Breaking Changes

### 1. Model Instantiation

**Before (v0.x):**
```python
course = CourseInfo(
    "Calculo",
    4,
    "OBLIGATORIA",
    10,
    "2024-03-15 14:30",
    [],
)
```

**After (v1.0):**
```python
course = CourseInfo(
    course_name="Calculo",
    credits=4,
    typology="OBLIGATORIA",
    available_spots=10,
    scrape_timestamp="2024-03-15 14:30",
    groups=[],
)
```

All models now require **keyword arguments**.

### 2. Immutability

All models are now **frozen** (immutable). Attempting to modify attributes after creation will raise a `ValidationError`.

**Before (v0.x):**
```python
course.code = "1000001"  # Worked
```

**After (v1.0):**
```python
course.code = "1000001"  # Raises ValidationError

# Use model_copy() to create a new instance:
new_course = course.model_copy(update={"code": "1000001"})
```

### 3. Session Data

`get_session_data()` now returns a `SessionState` object instead of a dict.

**Before (v0.x):**
```python
session_data = scraper.get_session_data()
cookies = session_data.get("session_cookies", {})
```

**After (v1.0):**
```python
session_state = scraper.get_session_data()
cookies = session_state.session_cookies  # Attribute access
```

To serialize for storage:
```python
json_data = session_state.model_dump_json()
```

To restore from storage:
```python
session_state = SessionState.model_validate_json(json_data)
scraper.load_session(session_state)
```

### 4. Dictionary Access

Models no longer support dict-style access (`model["key"]`). Use attribute access instead.

**Before (v0.x):**
```python
name = course["course_name"]
```

**After (v1.0):**
```python
name = course.course_name
```

### 5. Validation Errors

Invalid data now raises `ValidationError` with detailed messages instead of silently failing or returning incorrect data.

```python
from pydantic import ValidationError

try:
    course = CourseInfo(...)
except ValidationError as e:
    print(e.errors())  # List of validation errors
```

## New Features

### 1. Automatic Validation

All data from SIA is now automatically validated. Common issues like invalid course codes, malformed schedules, or missing required fields are caught early.

### 2. Better Error Messages

Validation errors include clear information about what went wrong:

```
ValidationError: 1 validation error for CourseInfo
code
  Value error, Course code must be 7 digits, got '123' (type=value_error)
```

### 3. IDE Support

Pydantic models provide better type hints for IDE autocomplete and static analysis.

## Updated Dependencies

- Added: `pydantic>=2.0,<3.0`

## Quick Compatibility Checklist

- [ ] Update all model instantiations to use keyword arguments
- [ ] Replace dict-style access with attribute access
- [ ] Use `model_copy(update={...})` instead of direct attribute assignment
- [ ] Update session serialization/deserialization code
- [ ] Handle `ValidationError` for invalid input
