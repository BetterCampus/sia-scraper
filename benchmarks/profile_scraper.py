#!/usr/bin/env python
"""Profiling script for sia-scraper to establish performance baseline.

This script profiles the scraping workflow to identify bottlenecks:
- HTML parsing (lxml)
- Network I/O (requests)
- Pydantic validation
- Oracle ADF logic (ViewState extraction, request building)

Usage:
    python benchmarks/profile_scraper.py
    python benchmarks/profile_scraper.py --output results.json
    python benchmarks/profile_scraper.py --flamegraph
"""

import argparse
import cProfile
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import pstats
    from pstats import SortKey
except ImportError:
    print("Installing profiling dependencies...")
    os.system("pip install -q pypprof")
    import pstats
    from pstats import SortKey

from sia_scraper.core import extract_view_state
from sia_scraper.parsers import scrape_info
from sia_scraper.parsers.html_parser import HtmlParser

FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures"


def load_fixture(filename: str, subdir: str = "html") -> str:
    """Load fixture file from tests/fixtures directory."""
    path = FIXTURES_DIR / subdir / filename
    if not path.exists():
        raise FileNotFoundError(f"Fixture not found: {path}")
    return path.read_text(encoding="utf-8")


def profile_parsing(html: str, iterations: int = 100) -> dict[str, Any]:
    """Profile HTML parsing performance."""

    # Profile HtmlParser initialization
    profiler = cProfile.Profile()
    profiler.enable()

    for _ in range(iterations):
        parser = HtmlParser(html)
        _ = parser.text_content()

    profiler.disable()

    stats = pstats.Stats(profiler)
    stats.sort_stats(SortKey.CUMULATIVE)
    total_time = stats.total_tt

    return {
        "function": "HtmlParser.__init__",
        "iterations": iterations,
        "total_time": total_time,
        "time_per_call": total_time / iterations,
    }


def profile_scrape_info(html: str, iterations: int = 50) -> dict[str, Any]:
    """Profile scrape_info function (parsing + Pydantic validation)."""

    profiler = cProfile.Profile()
    profiler.enable()

    results = []
    for _ in range(iterations):
        result = scrape_info(html)
        results.append(result)

    profiler.disable()

    stats = pstats.Stats(profiler)
    stats.sort_stats(SortKey.CUMULATIVE)

    return {
        "function": "scrape_info",
        "iterations": iterations,
        "total_time": stats.total_tt,
        "time_per_call": stats.total_tt / iterations,
        "sample_result": {
            "course_name": results[0].course_name if results else None,
            "credits": results[0].credits if results else None,
            "groups_count": len(results[0].groups) if results else 0,
        },
    }


def profile_viewstate_extraction(html: str, iterations: int = 1000) -> dict[str, Any]:
    """Profile ViewState extraction regex."""

    profiler = cProfile.Profile()
    profiler.enable()

    results = []
    for _ in range(iterations):
        result = extract_view_state(html)
        results.append(result)

    profiler.disable()

    stats = pstats.Stats(profiler)

    return {
        "function": "extract_view_state",
        "iterations": iterations,
        "total_time": stats.total_tt,
        "time_per_call": stats.total_tt / iterations,
    }


def profile_full_workflow(xml_files: list[str], iterations: int = 10) -> dict[str, Any]:
    """Profile full scraping workflow for multiple courses."""

    xml_contents = [load_fixture(f, "xml") for f in xml_files]

    profiler = cProfile.Profile()
    profiler.enable()

    total_start = time.perf_counter()

    for _ in range(iterations):
        for xml in xml_contents:
            result = scrape_info(xml)
            _ = result.course_name
            _ = result.credits
            _ = result.groups

    total_end = time.perf_counter()
    profiler.disable()

    total_courses = len(xml_files) * iterations

    return {
        "function": "full_workflow",
        "courses_processed": total_courses,
        "total_time": total_end - total_start,
        "time_per_course": (total_end - total_start) / total_courses,
        "courses_per_second": total_courses / (total_end - total_start),
    }


def print_profile_report(results: dict[str, Any]) -> None:
    """Print formatted profile report."""
    print("\n" + "=" * 60)
    print("SIA SCRAPER PERFORMANCE BASELINE")
    print("=" * 60)

    print("\n--- HTML Parsing (HtmlParser) ---")
    parsing = results.get("parsing", {})
    print(f"  Iterations: {parsing.get('iterations', 'N/A')}")
    print(f"  Total time: {parsing.get('total_time', 0):.4f}s")
    print(f"  Time/call: {parsing.get('time_per_call', 0) * 1000:.4f}ms")

    print("\n--- scrape_info (Parsing + Validation) ---")
    scrape = results.get("scrape_info", {})
    print(f"  Iterations: {scrape.get('iterations', 'N/A')}")
    print(f"  Total time: {scrape.get('total_time', 0):.4f}s")
    print(f"  Time/call: {scrape.get('time_per_call', 0) * 1000:.4f}ms")
    if sample := scrape.get("sample_result"):
        print(f"  Sample result: {sample}")

    print("\n--- ViewState Extraction ---")
    viewstate = results.get("viewstate", {})
    print(f"  Iterations: {viewstate.get('iterations', 'N/A')}")
    print(f"  Total time: {viewstate.get('total_time', 0):.4f}s")
    print(f"  Time/call: {viewstate.get('time_per_call', 0) * 1000:.4f}ms")

    print("\n--- Full Workflow (Multiple Courses) ---")
    workflow = results.get("full_workflow", {})
    print(f"  Courses processed: {workflow.get('courses_processed', 'N/A')}")
    print(f"  Total time: {workflow.get('total_time', 0):.4f}s")
    print(f"  Time/course: {workflow.get('time_per_course', 0) * 1000:.2f}ms")
    print(f"  Throughput: {workflow.get('courses_per_second', 0):.2f} courses/sec")

    print("\n" + "=" * 60)
    print("BASELINE ESTABLISHED")
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile sia-scraper performance")
    parser.add_argument("--output", "-o", help="Output JSON file for results", default=None)
    parser.add_argument(
        "--flamegraph", "-f", help="Generate flame graph (requires py-spy)", action="store_true"
    )
    parser.add_argument(
        "--iterations", "-i", type=int, default=100, help="Number of iterations for profiling"
    )
    args = parser.parse_args()

    print("Loading fixtures...")

    # Load fixtures for different purposes
    course_detail_fixture = "course_detail_0_2026-03-30.xml"
    prereqs_fixture = "course_prereqs_2026-03-30.xml"
    career_page_fixture = "career_page_regular_2026-03-30.html"

    # Load course detail XML (for scrape_info)
    try:
        course_xml = load_fixture(course_detail_fixture, "xml")
        print(f"  Loaded {course_detail_fixture}: {len(course_xml)} bytes")
    except FileNotFoundError:
        print(f"  Error: {course_detail_fixture} not found!")
        sys.exit(1)

    # Load prerequisites XML
    try:
        prereqs_xml = load_fixture(prereqs_fixture, "xml")
        print(f"  Loaded {prereqs_fixture}: {len(prereqs_xml)} bytes")
    except FileNotFoundError:
        print(f"  Warning: {prereqs_fixture} not found, skipping prereqs benchmarks")
        prereqs_xml = None

    # Load career page HTML (for ViewState extraction)
    try:
        career_html = load_fixture(career_page_fixture, "html")
        print(f"  Loaded {career_page_fixture}: {len(career_html)} bytes")
    except FileNotFoundError:
        print(f"  Warning: {career_page_fixture} not found")
        career_html = course_xml  # fallback

    print("\nRunning profiling benchmarks...")

    results: dict[str, Any] = {}

    # Profile HTML parsing
    print("  - HTML parsing...")
    results["parsing"] = profile_parsing(course_xml, args.iterations)

    # Profile scrape_info
    print("  - scrape_info (parsing + validation)...")
    results["scrape_info"] = profile_scrape_info(course_xml, min(50, args.iterations // 2))

    # Profile ViewState extraction (use career page for larger HTML)
    print("  - ViewState extraction...")
    results["viewstate"] = profile_viewstate_extraction(career_html, args.iterations * 10)

    # Profile scrape_prereqs if available
    if prereqs_xml:
        print("  - scrape_prereqs...")
        try:
            results["scrape_prereqs"] = profile_scrape_info(
                prereqs_xml, min(20, args.iterations // 5)
            )
        except Exception as e:
            results["scrape_prereqs"] = {"error": str(e)}

    # Profile full workflow
    print("  - Full workflow...")
    results["full_workflow"] = profile_full_workflow(
        [course_detail_fixture], min(10, args.iterations // 10)
    )

    # Print report
    print_profile_report(results)

    # Save results
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {output_path}")

    # Generate flamegraph if requested
    if args.flamegraph:
        print("\nGenerating flame graph...")
        import subprocess

        try:
            subprocess.run(
                [
                    "py-spy",
                    "record",
                    "-o",
                    "benchmarks/profile.svg",
                    "--",
                    "python",
                    "benchmarks/profile_scraper.py",
                ],
                check=True,
                cwd=Path(__file__).parent.parent,
            )
            print("Flame graph saved to: benchmarks/profile.svg")
        except FileNotFoundError:
            print("Warning: py-spy not installed. Install with: pip install py-spy")


if __name__ == "__main__":
    main()
