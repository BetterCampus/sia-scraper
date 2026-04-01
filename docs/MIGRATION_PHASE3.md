# Migration Guide: Typed Models (Phase 3)

## Overview

Phase 3 migrates the SIA scraper from ad-hoc dictionary payloads and index-based
parsing to typed models and selector-driven extraction with strict validation.

This guide covers the breaking changes and migration steps for Phase 3A-3D.

---

## Breaking Changes

### 1. Session payloads are now typed JSON

**Before (Phase 2):**
```python
session_state = await sia_scraper_rust.init_sia_session(15)
# session_state was a dict with mixed types and stringly-typed course_list
```

**After (Phase 3C):**
```python
import json
from sia_scraper.models.session import SessionStateTyped

raw = await sia_scraper_rust.init_sia_session_json(15)
typed = SessionStateTyped.model_validate(json.loads(raw))
# typed.status is validated against allowed values
# typed.course_list is a list of CourseListEntryTyped objects
# typed.params is validated for required ADF keys
```

### 2. Course parser returns typed models

**Before (Phase 2):**
```python
result = await scraper.get_course_info(course_index=0)
# result was a CourseInfo Pydantic model from parser layer
```

**After (Phase 3A):**
```python
from sia_scraper.models.course import CourseInfoTyped

raw_json = sia_scraper_rust.parse_course_info_json(xml)
typed = CourseInfoTyped.model_validate_json(raw_json)
# typed.credits is strictly validated (0-30)
# typed.groups is a list of GroupTyped objects
```

### 3. Prerequisite parser returns typed models

**Before (Phase 2):**
```python
result = await scraper.get_course_prereqs(course_index=0)
# result was a CoursePrereqs Pydantic model from parser layer
```

**After (Phase 3B):**
```python
from sia_scraper.models.prerequisite import CoursePrereqsTyped

raw_json = sia_scraper_rust.parse_prereqs_json(xml)
typed = CoursePrereqsTyped.model_validate_json(raw_json)
# typed.conditions[0].prereq_type is a validated string
# typed.conditions[0].all_required is a strict boolean
```

### 4. SessionState removed from parser layer

The `SessionState` model previously exported from `sia_scraper.parsers` has been
replaced by `SessionStateTyped` in `sia_scraper.models.session`.

**Before:**
```python
from sia_scraper.parsers import SessionState
```

**After:**
```python
from sia_scraper.models.session import SessionStateTyped
```

### 5. `.to_dict()` helpers removed

All typed models previously shipped with a deprecated `.to_dict()` compatibility
helper. These have been removed in Phase 3D.

**Before:**
```python
data = course_model.to_dict()  # DeprecationWarning
```

**After:**
```python
data = course_model.model_dump()  # Standard Pydantic method
```

---

## Migration Steps

### Step 1: Update imports

Replace any imports from `sia_scraper.parsers` that reference `SessionState`
with the new typed equivalents:

```python
# Old
from sia_scraper.parsers import SessionState

# New
from sia_scraper.models.session import SessionStateTyped
```

### Step 2: Use typed session payloads

If you were consuming raw dict payloads from Rust session endpoints, switch to
the JSON bridge endpoints and typed validation:

```python
import json
from sia_scraper.models.session import SessionStateTyped

raw = await sia_scraper_rust.init_sia_session_json(15)
state = SessionStateTyped.model_validate(json.loads(raw))
```

### Step 3: Replace `.to_dict()` calls

Replace any `.to_dict()` calls on typed models with `.model_dump()`:

```python
# Old
data = course.to_dict()

# New
data = course.model_dump()
```

### Step 4: Handle strict validation errors

Typed models now enforce strict validation. Wrap model construction in
try/except if you need graceful fallback:

```python
from pydantic import ValidationError

try:
    state = SessionStateTyped.model_validate(payload)
except ValidationError as e:
    # Handle invalid session state
    logger.error("Invalid session payload: %s", e)
```

---

## Error Handling Modes

The Rust crate supports two error handling modes via Cargo features:

| Feature | Behavior | Recommended for |
|---------|----------|-----------------|
| `full-error-collection` (default) | Collects all errors, provides rich diagnostics | Debugging, CI, development |
| `fail-fast` | Returns on first error | Production scraping where speed matters |

To use fail-fast mode, compile with:
```bash
maturin build --no-default-features --features extension-module,fail-fast
```

---

## Compatibility and Rollout Guidance

- The typed JSON endpoints (`*_json`) coexist with legacy dict endpoints.
- Python wrappers (`SiaSession`, `SiaScraper`) now consume typed payloads internally.
- External consumers should migrate to typed models at their earliest convenience.
- Legacy dict endpoints will be removed in a future major version.

## Quick Checklist

- [ ] Replace `SessionState` imports with `SessionStateTyped`
- [ ] Use `init_sia_session_json` / `set_career_json` for typed payloads
- [ ] Replace `.to_dict()` with `.model_dump()`
- [ ] Add `ValidationError` handling for strict model construction
- [ ] Run `ruff`, `pyright`, `clippy`, and `pytest`
