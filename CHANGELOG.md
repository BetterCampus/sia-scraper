# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- **Course code extraction**: Use regex to extract course code from rightmost parentheses in course names with multiple parenthetical expressions (e.g., "ELECTROMAGNETISMO (AVANZADO) (2016489)")
- **Course code misalignment**: Fixed critical bug in `scrape_courses()` where sorting indices without sorting corresponding codes caused mismatched assignments
- **Session resource leak**: Added explicit session cleanup in `init_sia_scraper()` when falling back to a new session

### Refactored
- **PEP 8 compliance**: Replaced double underscore (`__`) private attributes with single underscore (`_`) throughout `scraper.py` and `session.py` to follow Python naming conventions and improve testability
- Removed unnecessary `type: ignore[attr-defined]` comments in tests now that name mangling is no longer used
