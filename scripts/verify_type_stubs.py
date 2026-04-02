#!/usr/bin/env python3
"""Verification script for sia_scraper_rust type stubs.

This script verifies that the type stub file (stubs/sia_scraper_rust.pyi)
matches the actual Rust PyClass implementations in the sia_scraper_rust module.

It performs the following checks:
1. Extracts model class definitions from the stub file
2. Imports the actual sia_scraper_rust module and inspects its classes
3. Ensures each expected model exists in both stub and Rust module and compares
   their field names
4. Reports any missing models or fields that are present in Rust but not in the
   stub

Usage:
    python scripts/verify_type_stubs.py

Exit codes:
    0 - All checks passed
    1 - Verification failed (mismatches found)
    2 - Module import error (sia_scraper_rust not installed)
"""

import re
import sys
from pathlib import Path


def parse_stub_file(stub_path: Path) -> dict[str, dict]:
    """Parse the type stub file and extract class definitions.

    Args:
        stub_path: Path to the .pyi stub file.

    Returns:
        Dictionary mapping class names to their field definitions.
    """
    content = stub_path.read_text(encoding="utf-8")
    classes: dict[str, dict] = {}

    class_pattern = re.compile(
        r"class\s+(\w+)\s*:\s*(.*?)(?=\nclass\s|\n(?:def|async def)\s|\Z)",
        re.DOTALL,
    )

    docstring_keywords = {"Attributes:", "Args:", "Example:", "Returns:", "Raises:", "Notes:"}

    for match in class_pattern.finditer(content):
        class_name = match.group(1)
        class_body = match.group(2)

        fields: dict[str, str] = {}

        field_pattern = re.compile(r"^\s{4}(\w+)\s*:\s*(.+)$", re.MULTILINE)
        for field_match in field_pattern.finditer(class_body):
            field_name = field_match.group(1)
            field_type = field_match.group(2).rstrip("\n")

            if field_name in docstring_keywords:
                continue

            fields[field_name] = field_type

        if fields:
            classes[class_name] = {"fields": fields}

    return classes


def inspect_rust_module() -> dict[str, dict]:
    """Inspect the actual sia_scraper_rust module for class definitions.

    Returns:
        Dictionary mapping class names to their field definitions.
    """
    try:
        import sia_scraper_rust
    except ImportError as e:
        print(f"ERROR: Could not import sia_scraper_rust: {e}")
        print("Run 'maturin develop' or 'pip install -e .' first")
        sys.exit(2)

    classes: dict[str, dict] = {}

    for name in dir(sia_scraper_rust):
        obj = getattr(sia_scraper_rust, name)
        if hasattr(obj, "__annotations__") and hasattr(obj, "__init__"):
            annotations = obj.__annotations__
            classes[name] = {
                "fields": {k: str(v) for k, v in annotations.items() if not k.startswith("_")}
            }

    return classes


def compare_classes(stub_classes: dict[str, dict], rust_classes: dict[str, dict]) -> list[str]:
    """Compare stub classes with actual Rust module classes.

    Args:
        stub_classes: Classes parsed from .pyi file.
        rust_classes: Classes from sia_scraper_rust module.

    Returns:
        List of error messages (empty if all checks pass).
    """
    errors: list[str] = []

    expected_models = {
        "ScheduleModel",
        "GroupModel",
        "CourseInfoModel",
        "CourseListEntryModel",
        "SessionStateModel",
        "PrerequisiteModel",
        "PrereqConditionModel",
        "CoursePrereqsModel",
    }

    for model in expected_models:
        if model not in stub_classes:
            errors.append(f"ERROR: Model '{model}' not found in stub file")
            continue
        if model not in rust_classes:
            errors.append(f"ERROR: Model '{model}' not found in Rust module")
            continue

        stub_fields = stub_classes[model]["fields"]
        rust_fields = rust_classes[model]["fields"]

        stub_keys = set(stub_fields.keys())
        rust_keys = set(rust_fields.keys())

        missing_in_stub = rust_keys - stub_keys

        if missing_in_stub:
            errors.append(
                f"ERROR: Model '{model}' has field in Rust but NOT in stub: {sorted(missing_in_stub)}"
            )

    return errors


def main() -> int:
    """Main entry point for type stub verification."""
    print("=" * 60)
    print("sia_scraper_rust Type Stub Verification")
    print("=" * 60)

    stub_path = Path(__file__).parent.parent / "stubs" / "sia_scraper_rust.pyi"

    if not stub_path.exists():
        print(f"ERROR: Stub file not found: {stub_path}")
        return 1

    print(f"\n[1] Parsing stub file: {stub_path}")
    stub_classes = parse_stub_file(stub_path)
    print(f"    Found {len(stub_classes)} classes with fields")

    print("\n[2] Inspecting sia_scraper_rust module")
    rust_classes = inspect_rust_module()
    print(f"    Found {len(rust_classes)} classes with annotations")

    print("\n[3] Comparing classes")
    errors = compare_classes(stub_classes, rust_classes)

    if errors:
        print("\n" + "!" * 60)
        print("VERIFICATION FAILED")
        print("!" * 60)
        for error in errors:
            print(f"  {error}")
        return 1

    print("\n" + "=" * 60)
    print("VERIFICATION PASSED")
    print("=" * 60)
    print("\nAll type stub classes match the Rust module!")
    print(f"  Stub classes: {len(stub_classes)}")
    print(f"  Rust classes: {len(rust_classes)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
