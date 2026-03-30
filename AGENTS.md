# AI Agent Custom Instructions: sia-scraper

A Python library for extracting academic information from the SIA (Sistema de Información Académica).

---

## Project Overview

- **Python Version**: 3.10+
- **Structure**: `src/sia_scraper/` (main code), `tests/` (pytest tests mirroring src structure)
- **Core Dependencies**: `requests`, `beautifulsoup4`, `lxml`, `pydantic`, `tenacity`, `loguru`
- **Dev Dependencies**: `pytest`, `pytest-mock`, `pytest-cov`, `pyright`, `ruff`

---

## Build, Test, and Lint Commands

### Environment Setup
```bash
pip install -e ".[dev]"
```

### Running Tests
```bash
# All tests
pytest

# With coverage report
pytest --cov=src/sia_scraper

# Verbose output
pytest -v

# Single test file
pytest tests/utils/test_date_formatter.py

# Specific test class
pytest tests/utils/test_date_formatter.py::TestDateFormatterBasicFunctionality

# Single test function
pytest tests/utils/test_date_formatter.py::TestDateFormatterBasicFunctionality::test_formatDate_typical_datetime

# Run tests matching a pattern
pytest -k "test_format"
```

### Linting & Formatting
```bash
# Check code with ruff
ruff check .

# Auto-fix ruff issues
ruff check --fix .

# Format code
ruff format .

# Combined: fix, format, then check (recommended)
ruff check --fix . && ruff format . && ruff check .
```

### Type Checking
```bash
pyright
```

---

## Code Style Guidelines

### Python 3.10+ Standards

- Use modern syntax: `list[str]` instead of `List[str]`, `X | None` instead of `Optional[X]`
- All function signatures, methods, and class attributes MUST have type hints
- Code must pass `pyright` static type checking without errors
- Minimize `typing.Any`; add inline comment explaining necessity when used
- Handle `None` types explicitly to prevent runtime errors

### Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Variables, Functions, Methods | `snake_case` | `get_available_courses` |
| Classes | `PascalCase` | `AcademicHistory` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_RETRIES` |
| Private Members | `_leading_underscore` | `_internal_helper` |

### Import Order (enforced by ruff)

1. Standard library imports
2. Third-party imports
3. Local/first-party imports (`sia_scraper`)

```python
# Correct order example
import os
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from sia_scraper.constants import BASE_URL, TIMEOUT
from sia_scraper.session import Session
```

### Documentation

- Use **Google-Style Docstrings** formatted in Markdown
- Required sections where applicable:
  - Brief description of behavior
  - `Args:` with parameter names and types
  - `Returns:` with return type and description
  - `Raises:` for exceptions thrown
  - `Examples:` with ` ```python ` code blocks

```python
def format_date(dt: datetime) -> str:
    """Convert datetime to SIA-compatible string format.

    Args:
        dt: The datetime object to format.

    Returns:
        Formatted string in 'YYYY-MM-DD HH:MM' format.

    Raises:
        ValueError: If dt is None.

    Example:
        >>> from datetime import datetime
        >>> format_date(datetime(2024, 3, 15, 14, 30))
        '2024-03-15 14:30'
    """
```

### Error Handling

- Use specific exception types rather than generic `Exception`
- Prefer early returns and guard clauses over deeply nested `if/else`
- Document raised exceptions in docstrings
- Use `pytest.raises` for testing exception scenarios

```python
# Good: specific exception, early return
def get_course(self, course_id: str) -> Course:
    if not course_id:
        raise ValueError("course_id cannot be empty")
    
    response = self._session.get(f"/courses/{course_id}")
    response.raise_for_status()
    return Course.from_dict(response.json())

# Avoid: nesting, catching generic Exception
def get_course(self, course_id: str) -> Course:
    if course_id:
        response = self._session.get(f"/courses/{course_id}")
        if response.status_code == 200:
            return Course.from_dict(response.json())
```

### Code Quality

- Keep functions small and focused on a single responsibility
- Follow DRY principle; extract repetitive logic into helper functions
- Maximum line length: 100 characters
- Eliminate unused variables and imports automatically (ruff handles this)
- No trailing whitespace

---

## Testing Guidelines

### Test Structure

- Place tests in `tests/` directory mirroring src structure
- Name test files `test_<module>.py` (e.g., `test_session.py` tests `session.py`)
- Group related tests into classes: `Test<Module>BasicFunctionality`, `Test<Module>EdgeCases`

### Test Organization

```python
class TestDateFormatterBasicFunctionality:
    def test_formatDate_typical_datetime(self, date_formatter):
        ...

    def test_formatDate_date_only(self, date_formatter):
        ...


class TestDateFormatterEdgeCases:
    def test_formatDate_invalid_input(self, date_formatter):
        ...
```

### Mocking

- Use `pytest-mock` (`mocker` fixture) for external dependencies
- Never make real network requests or database connections in tests
- Mock API calls, file I/O, and time-dependent functions

```python
def test_scraper_get_courses(self, mocker):
    mock_get = mocker.patch("requests.Session.get")
    mock_get.return_value.json.return_value = {"courses": []}
    mock_get.return_value.raise_for_status = mocker.MagicMock()
    
    scraper = Scraper()
    result = scraper.get_courses()
    assert result == []
```

---

## Ruff Configuration

```toml
[tool.ruff]
target-version = "py310"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP"]
ignore = ["E501"]  # Line length handled by 100-char soft limit

[tool.ruff.format]
quote-style = "double"
```

- **E**: pycodestyle errors
- **F**: pyflakes
- **W**: warnings
- **I**: isort (import sorting)
- **B**: bugbear
- **UP**: pyupgrade

---

## Key Modules

### Top-Level Orchestrators

| Module | Purpose |
|--------|---------|
| `session.py` | Handles HTTP sessions and Oracle ADF state with SIA |
| `scraper.py` | Main scraping orchestration facade |

### Core Infrastructure (`core/`)

| Module | Purpose |
|--------|---------|
| `enhanced_session.py` | HTTP session wrapper with timeout handling |
| `exceptions.py` | Session-related exception hierarchy |
| `adf_state.py` | ViewState extraction utilities |
| `oracle_adf_request.py` | Oracle ADF request body builder |

### Utilities (`utils/`)

| Module | Purpose |
|--------|---------|
| `date_formatter.py` | Converts datetime objects to SIA `YYYY-MM-DD HH:MM` format |
| `decorators.py` | Session/status validation and timeout decorators |
| `debug.py` | Debug logging helpers for ADF troubleshooting |

### Supporting Packages

| Package | Purpose |
|---------|---------|
| `constants/` | Configuration constants and ADF IDs/events |
| `parsers/` | HTML and course payload parsing |
