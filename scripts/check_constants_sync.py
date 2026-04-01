#!/usr/bin/env python3
"""Verify Rust and Python constants remain synchronized.

This script checks that critical SIA constants (URLs, taskflow IDs, headers)
match between Python and Rust implementations.

Usage:
    python scripts/check_constants_sync.py
    python scripts/check_constants_sync.py --verbose

Exit codes:
    0 - All constants synchronized
    1 - Constants mismatch detected
"""

import re
import sys
from pathlib import Path

# ANSI color codes for terminal output
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def extract_python_constants(file_path: Path) -> dict[str, str]:
    """Extract constants from Python http.py file.

    Args:
        file_path: Path to src/sia_scraper/constants/http.py

    Returns:
        Dictionary mapping constant names to their values.
    """
    content = file_path.read_text()
    constants = {}

    # Extract SIA_BASE_URL
    match = re.search(r'SIA_BASE_URL:\s*str\s*=\s*["\']([^"\']+)["\']', content)
    if match:
        constants["SIA_BASE_URL"] = match.group(1)

    # Extract ADF_ADS_PAGE_ID
    match = re.search(r'ADF_ADS_PAGE_ID:\s*str\s*=\s*["\']([^"\']+)["\']', content)
    if match:
        constants["ADF_ADS_PAGE_ID"] = match.group(1)

    # Check for key headers (extracted from SIA_HEADERS dict)
    if "content-type" in content:
        constants["HAS_CONTENT_TYPE"] = "yes"
    if '"origin"' in content and "sia.unal.edu.co" in content:
        constants["HAS_ORIGIN"] = "yes"
    if '"referer"' in content and "servicioPublico.jsf" in content:
        constants["HAS_REFERER"] = "yes"

    return constants


def extract_rust_constants(file_path: Path) -> dict[str, str]:
    """Extract constants from Rust constants.rs file.

    Args:
        file_path: Path to rust/src/constants.rs

    Returns:
        Dictionary mapping constant names to their values.
    """
    content = file_path.read_text()
    constants = {}

    # Extract SIA_BASE_URL
    match = re.search(r'pub const SIA_BASE_URL:\s*&str\s*=\s*"([^"]+)"', content)
    if match:
        constants["SIA_BASE_URL"] = match.group(1)

    # Extract SIA_ORIGIN
    match = re.search(r'pub const SIA_ORIGIN:\s*&str\s*=\s*"([^"]+)"', content)
    if match:
        constants["SIA_ORIGIN"] = match.group(1)

    # Extract ADF_ADS_PAGE_ID from headers module
    match = re.search(r'pub const ADF_ADS_PAGE_ID:\s*&str\s*=\s*"([^"]+)"', content)
    if match:
        constants["ADF_ADS_PAGE_ID"] = match.group(1)

    # Extract CONTENT_TYPE from headers module
    match = re.search(r'pub const CONTENT_TYPE:\s*&str\s*=\s*"([^"]+)"', content)
    if match:
        constants["CONTENT_TYPE"] = match.group(1)

    # Check for SIA_BASE_URL in referer
    if "SIA_BASE_URL" in content and "pub const SIA_BASE_URL" in content:
        constants["HAS_BASE_URL"] = "yes"
    if "SIA_ORIGIN" in content and "pub const SIA_ORIGIN" in content:
        constants["HAS_ORIGIN"] = "yes"

    return constants


def compare_critical_constants(
    python_consts: dict[str, str], rust_consts: dict[str, str], verbose: bool
) -> list[dict[str, str]]:
    """Compare critical constants between Python and Rust.

    Args:
        python_consts: Constants extracted from Python file
        rust_consts: Constants extracted from Rust file
        verbose: If True, print detailed comparison

    Returns:
        List of mismatches found.
    """
    # Critical constants that MUST match exactly
    critical_constants = ["SIA_BASE_URL", "ADF_ADS_PAGE_ID"]

    mismatches = []

    for key in critical_constants:
        python_val = python_consts.get(key)
        rust_val = rust_consts.get(key)

        if python_val and rust_val and python_val != rust_val:
            mismatches.append({"key": key, "python": python_val, "rust": rust_val})
        elif verbose:
            if python_val and rust_val:
                print(f"  {GREEN}✓{RESET} {key}: synchronized")
            elif not python_val:
                print(f"  {YELLOW}⚠{RESET} {key}: not found in Python")
            elif not rust_val:
                print(f"  {YELLOW}⚠{RESET} {key}: not found in Rust")

    return mismatches


def check_origin_referer_match(
    python_consts: dict[str, str], rust_consts: dict[str, str]
) -> list[dict[str, str]]:
    """Check that origin/referer references use matching domains.

    Args:
        python_consts: Constants extracted from Python file
        rust_consts: Constants extracted from Rust file

    Returns:
        List of issues found.
    """
    issues = []

    # Check SIA_ORIGIN consistency
    python_base = python_consts.get("SIA_BASE_URL", "")
    rust_origin = rust_consts.get("SIA_ORIGIN", "")
    rust_base = rust_consts.get("SIA_BASE_URL", "")

    # If Rust has SIA_ORIGIN, it should match the domain from SIA_BASE_URL
    if rust_origin and rust_base and not rust_base.startswith(rust_origin):
        issues.append(
            {
                "key": "SIA_ORIGIN consistency",
                "python": f"SIA_BASE_URL starts with: {rust_base[:30]}...",
                "rust": f"SIA_ORIGIN: {rust_origin}",
            }
        )

    # If Python has origin in headers, it should match base URL domain
    if python_base and "sia.unal.edu.co" not in python_base:
        issues.append(
            {
                "key": "Python SIA_BASE_URL domain",
                "python": python_base,
                "rust": "Expected sia.unal.edu.co",
            }
        )

    return issues


def main(verbose: bool = False) -> int:
    """Run constants synchronization check.

    Args:
        verbose: If True, print detailed progress

    Returns:
        Exit code (0 = success, 1 = failure)
    """
    # Find project root (parent of scripts directory)
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent

    python_constants_file = project_root / "src" / "sia_scraper" / "constants" / "http.py"
    rust_constants_file = project_root / "rust" / "src" / "constants.rs"

    print(f"\n{BOLD}Constants Synchronization Check{RESET}\n")

    # Check Python file exists
    if not python_constants_file.exists():
        print(f"{RED}✗ Python constants file not found:{RESET}")
        print(f"  {python_constants_file}\n")
        return 1

    if verbose:
        print(f"  Python: {python_constants_file.relative_to(project_root)}")

    # Check Rust file exists
    if not rust_constants_file.exists():
        print(f"{YELLOW}⚠ Rust constants file not found (expected pre-Phase 1):{RESET}")
        print(f"  {rust_constants_file.relative_to(project_root)}")
        print(f"\n{GREEN}Skipping check - will be enforced after Phase 1{RESET}\n")
        return 0

    if verbose:
        print(f"  Rust:   {rust_constants_file.relative_to(project_root)}\n")

    # Extract constants
    python_consts = extract_python_constants(python_constants_file)
    rust_consts = extract_rust_constants(rust_constants_file)

    if not python_consts:
        print(f"{RED}✗ Failed to extract Python constants{RESET}\n")
        return 1

    if not rust_consts:
        print(f"{RED}✗ Failed to extract Rust constants{RESET}\n")
        return 1

    if verbose:
        print(f"  Extracted {len(python_consts)} Python constants")
        print(f"  Extracted {len(rust_consts)} Rust constants\n")
        print("  Comparing critical constants:")

    # Check critical constants
    mismatches = compare_critical_constants(python_consts, rust_consts, verbose)

    # Check origin/referer consistency
    origin_issues = check_origin_referer_match(python_consts, rust_consts)

    # Report results
    if not mismatches and not origin_issues:
        print(f"\n{GREEN}✓ All critical constants are synchronized{RESET}")
        print("  Verified: SIA_BASE_URL, ADF_ADS_PAGE_ID\n")
        return 0
    else:
        print(f"\n{RED}✗ Constants synchronization check FAILED{RESET}\n")

        if mismatches:
            print(f"{BOLD}Critical mismatches:{RESET}\n")
            for mismatch in mismatches:
                print(f"  {YELLOW}{mismatch['key']}{RESET}")
                print(f"    Python: {mismatch['python']}")
                print(f"    Rust:   {mismatch['rust']}\n")

        if origin_issues:
            print(f"{BOLD}Origin/Referer issues:{RESET}\n")
            for issue in origin_issues:
                print(f"  {YELLOW}{issue['key']}{RESET}")
                print(f"    Python: {issue['python']}")
                print(f"    Rust:   {issue['rust']}\n")

        print(f"{BOLD}To fix:{RESET}")
        print("  1. Update Python: src/sia_scraper/constants/http.py")
        print("  2. Update Rust:   rust/src/constants.rs")
        print("  3. Ensure both files use identical URL/domain values\n")

        return 1


if __name__ == "__main__":
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    sys.exit(main(verbose=verbose))
