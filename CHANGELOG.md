# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-03-30

### Added

- **Pydantic Models**: All data models now use Pydantic BaseModel for runtime validation
  - Models: `Schedule`, `Group`, `CourseInfo`, `Prerequisite`, `PrereqCondition`, `CoursePrereqs`, `SessionState`
  - Immutability: All models are frozen (cannot be modified after creation)
  - Validation: Automatic validation of all fields with clear error messages
- **SessionState Model**: New model for session serialization/deserialization
- **Migration Guide**: Added `docs/MIGRATION_v1.0.md` with detailed upgrade instructions

### Changed

- **Model Instantiation**: All model constructors now require keyword arguments
- **Session Data**: `get_session_data()` returns `SessionState` object instead of dict
- **Dict Access**: Models no longer support dict-style access (`model["key"]`); use attribute access

### Fixed

- **Course code extraction**: Use regex to extract course code from rightmost parentheses in course names with multiple parenthetical expressions (e.g., "ELECTROMAGNETISMO (AVANZADO) (2016489)")
- **Course code misalignment**: Fixed critical bug in `scrape_courses()` where sorting indices without sorting corresponding codes caused mismatched assignments
- **Session resource leak**: Added explicit session cleanup in `init_sia_scraper()` when falling back to a new session

### Refactored

- **PEP 8 compliance**: Replaced double underscore (`__`) private attributes with single underscore (`_`) throughout `scraper.py` and `session.py` to follow Python naming conventions and improve testability
- Removed unnecessary `type: ignore[attr-defined]` comments in tests now that name mangling is no longer used
