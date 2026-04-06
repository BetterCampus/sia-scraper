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

### Quick Reference (Recommended)

The project uses a Makefile for all standard workflows. Run `make help` to see
all available targets.

| Command | Description |
|---------|-------------|
| `make setup` | Install deps + build extension (checkout → ready) |
| `make develop` | Rebuild Rust extension after changes |
| `make build` | Build release wheels |
| `make lint` | Lint Python + Rust |
| `make lint-python` | Python lint only |
| `make lint-rust` | Rust lint only |
| `make format` | Format Python code |
| `make typecheck` | Run pyright |
| `make test` | Run all tests |
| `make test-python` | Python tests only |
| `make test-python-cov` | Python tests with coverage |
| `make test-rust` | Rust tests only |
| `make check` | Full pre-commit (stops on first failure) |
| `make check-python` | Python checks (reports all failures) |
| `make check-rust` | Rust checks (reports all failures) |
| `make clean` | Remove build artifacts |

Argument pass-through for test targets:
```bash
make test-python ARGS="-k test_format -v"
make test-rust ARGS="-- helpers"
```

### Environment Setup
```bash
make setup
```

### Local Verification (run before commit)
```bash
make check
```

### Advanced: Raw Commands

For fine-grained control, individual tools can be run directly:

#### Running Tests
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

#### Linting & Formatting
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

#### Type Checking
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

#### Mutable Default Arguments

**Never use mutable objects as default argument values.** This is a common Python pitfall that can lead to bugs that are difficult to reproduce.

```python
# BAD - mutable default argument
def add_item(item, items=[]):
    items.append(item)
    return items

# GOOD - use None and create new list inside
def add_item(item, items=None):
    if items is None:
        items = []
    items.append(item)
    return items

# GOOD - use default_factory for dataclass fields
from dataclasses import dataclass, field

@dataclass
class Example:
    items: list[str] = field(default_factory=list)
```

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

---

## Rust Extensions (PyO3 + Maturin)

### Overview

- **Rust Version**: 2021 edition (Rust 1.56+)
- **Structure**: `rust/src/` (Rust code), built into `sia_scraper_rust` Python module
- **Build System**: Maturin for building Python wheels with Rust extensions
- **Core Dependencies**: `pyo3`, `scraper`, `quick-xml`, `thiserror`, `log`, `regex`

### Build Commands

#### Quick Reference
```bash
make develop    # Build and install into current virtualenv (debug mode)
make build      # Build release wheels
make check-rust # Lint + test
```

#### Advanced: Raw Commands
```bash
# Build in debug mode
maturin build

# Build in release mode (optimized)
maturin build --release

# Build and install into current virtualenv
maturin develop

# Install specific wheel
pip install target/wheels/sia_scraper-*.whl --force-reinstall
```

#### Development Workflow
```bash
# Check Rust code (fast, no build)
cargo check

# Run clippy linter
cargo clippy --all-targets --all-features -- -D warnings

# Auto-fix clippy warnings
cargo clippy --fix

# Run Rust tests (requires --no-default-features to disable extension-module feature
# which prevents Python linking during pure Rust unit tests)
cargo test --no-default-features --lib

# Build optimized release
maturin build --release

# Install and test with Python
pip install target/wheels/sia_scraper-*.whl --force-reinstall
pytest tests/
```

### Rust Code Quality Standards

#### Clippy Compliance
- Code MUST pass `cargo clippy` with zero warnings
- Use `cargo clippy --fix` to auto-fix common issues
- Never commit code with unused imports or variables
- Avoid needless borrows and references

#### Testing Requirements
- All public functions must have unit tests
- Test structure: `#[cfg(test)] mod tests { ... }`
- Minimum coverage: happy path + 2 edge cases + 1 error case per function
- Use `assert_eq!`, `assert!`, and `Result<T, E>` pattern matching for tests

#### Documentation Standards
- All public functions MUST have rustdoc comments
- Format: Triple-slash `///` comments above function declarations
- Required sections:
  - Brief description (one-line summary)
  - `# Arguments` - parameter descriptions
  - `# Returns` - return value description
  - `# Errors` - error conditions (if applicable)
  - `# Examples` - usage examples with ` ```rust ` code blocks

#### Example Documented Function
```rust
/// Extracts the ViewState value from Oracle ADF HTML response.
///
/// # Arguments
/// * `html` - Raw HTML string from SIA Oracle ADF response
///
/// # Returns
/// ViewState string value extracted from hidden input element
///
/// # Errors
/// Returns `SiaScraperError::ExtractionError` if ViewState element not found
///
/// # Examples
/// ```rust
/// let html = r#"<input name="javax.faces.ViewState" value="abc123" />"#;
/// let view_state = extract_view_state(html)?;
/// assert_eq!(view_state, "abc123");
/// ```
pub fn extract_view_state(html: &str) -> Result<String, SiaScraperError> {
    // implementation
}
```

### Error Handling Patterns

#### Custom Error Types
- Use `thiserror::Error` derive macro for error enums
- Implement `From<SiaScraperError> for pyo3::PyErr` for Python exceptions
- Specific error variants for different failure modes

```rust
#[derive(Error, Debug)]
pub enum SiaScraperError {
    #[error("Parse error: {0}")]
    ParseError(String),
    
    #[error("XML parsing failed: {0}")]
    XmlError(String),
    
    #[error("Invalid input: {0}")]
    InvalidInput(String),
    
    #[error("Missing element: {element} at selector: {selector}")]
    MissingElement { element: String, selector: String },
    
    #[error("Failed to parse {field}: {value}")]
    ParseFieldError { field: String, value: String },
}
```

#### Result Types
- All fallible operations return `Result<T, SiaScraperError>`
- Use `?` operator for error propagation
- Avoid `.unwrap()` and `.expect()` in production code

### PyO3 Best Practices

#### Python Type Conversions
- Use `pyo3::types::PyDict` for dictionary returns
- Use `pyo3::types::PyList` for list returns
- Explicit type annotations for empty collections: `Vec<Py<PyAny>>`
- Always use `Python::with_gil(|py| ...)` for GIL-protected operations

#### Common Pitfalls
1. **Lifetime annotations**: ElementRef requires explicit lifetimes
2. **ElementRef storage**: Cannot clone or store; extract data immediately
3. **PyList/PyDict inference**: Compiler needs explicit types for empty collections
4. **GIL handling**: Never hold GIL across long-running operations

### Testing Strategy

#### Unit Test Structure
```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_view_state_valid_input() {
        let html = r#"<input name="ViewState" value="test123" />"#;
        let result = extract_view_state(html);
        assert!(result.is_ok());
        assert_eq!(result.unwrap(), "test123");
    }

    #[test]
    fn test_extract_view_state_missing() {
        let html = "<div>No ViewState here</div>";
        let result = extract_view_state(html);
        assert!(result.is_err());
    }
}
```

#### Integration with Python Tests
- Python tests in `tests/` directory test the compiled extension
- Use `sia_scraper_rust.function_name()` to test Rust functions from Python
- Compare Rust output with Python implementation for correctness

### Performance Optimization

#### Release Profile Settings
```toml
[profile.release]
opt-level = 3          # Maximum optimization
lto = true             # Link-time optimization
codegen-units = 1      # Single codegen unit for better optimization
```

#### Benchmarking
- Use `benchmarks/benchmark_parsing.py` for performance comparison
- Always benchmark Python vs Rust before/after changes
- Target: Rust should be 2-5x faster than Python for parsing operations

### Common Rust Patterns in This Project

#### CSS Selection Pattern
```rust
fn css_select<'a>(root: &'a Html, selector_str: &'a str) -> Vec<ElementRef<'a>> {
    let selector = Selector::parse(selector_str).ok()?;
    root.select(&selector).collect()
}
```

#### Text Extraction Pattern
```rust
fn extract_text_from_elem(elem: &ElementRef) -> String {
    elem.text().collect::<String>().trim().to_string()
}
```

#### PyDict Construction Pattern
```rust
Python::with_gil(|py| {
    let dict = pyo3::types::PyDict::new(py);
    dict.set_item("key", "value")?;
    dict.set_item("number", 42)?;
    Ok(dict.into_py(py))
})
```
