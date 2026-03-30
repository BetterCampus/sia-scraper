#!/usr/bin/env python
"""Rust vs Python benchmark comparison.

This script compares the performance of Rust implementations vs Python implementations.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sia_scraper_rust import (
    extract_view_state as rust_extract_view_state,
)
from sia_scraper_rust import (
    get_course_list as rust_get_course_list,
)
from sia_scraper_rust import (
    get_plain_text as rust_get_plain_text,
)
from sia_scraper_rust import (
    parse_course_info as rust_parse_course_info,
)
from sia_scraper_rust import (
    parse_prereqs as rust_parse_prereqs,
)

from sia_scraper.core import extract_view_state as python_extract_view_state
from sia_scraper.parsers import scrape_info, scrape_prereqs
from sia_scraper.parsers.html_parser import HtmlParser

FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures"


def load_fixture(filename: str, subdir: str = "xml") -> str:
    """Load fixture file from xml or html subdirectory."""
    path = FIXTURES_DIR / subdir / filename
    return path.read_text(encoding="utf-8")


def time_function(func, *args, iterations=100):
    """Time a function over multiple iterations."""
    # Warmup
    for _ in range(5):
        func(*args)

    # Benchmark
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        func(*args)
        end = time.perf_counter()
        times.append((end - start) * 1000)  # Convert to ms

    times.sort()
    return {
        "mean": sum(times) / len(times),
        "min": times[0],
        "max": times[-1],
        "median": times[len(times) // 2],
    }


def python_get_plain_text_baseline(xml: str) -> str:
    """Legacy Python baseline for plain text extraction."""
    parser = HtmlParser(xml)
    return parser.text_content().split("\xa0\xa0\xa0")[0]


def python_get_course_list_baseline(content: str) -> list[dict[str, str]]:
    """Legacy Python baseline for course list parsing."""
    parser = HtmlParser(content)
    rows = parser.find_all("tr", class_="af_table_data-row")
    course_list: list[dict[str, str]] = []

    for row in rows:
        spans = row.findall(".//span[@class='af_column_data-container']")
        if len(spans) < 2:
            continue

        course_code = (spans[0].text_content() or "").strip()
        course_name = (spans[1].text_content() or "").strip()

        if course_code:
            course_list.append({course_code: course_name})

    return course_list


def main():
    print("=" * 70)
    print("RUST VS PYTHON BENCHMARK RESULTS")
    print("=" * 70)

    # Load fixtures
    course_xml = load_fixture("course_detail_0_2026-03-30.xml", "xml")
    prereqs_xml = load_fixture("course_prereqs_2026-03-30.xml", "xml")
    career_html = load_fixture("career_page_regular_2026-03-30.html", "html")

    print("\nFixture sizes:")
    print(f"  course_xml: {len(course_xml):,} bytes")
    print(f"  prereqs_xml: {len(prereqs_xml):,} bytes")
    print(f"  career_html: {len(career_html):,} bytes")

    benchmarks = [
        ("extract_view_state (Rust)", lambda: rust_extract_view_state(career_html)),
        ("extract_view_state (Python)", lambda: python_extract_view_state(career_html)),
        ("get_plain_text (Rust)", lambda: rust_get_plain_text(course_xml)),
        ("get_plain_text (Python)", lambda: python_get_plain_text_baseline(course_xml)),
        ("get_course_list (Rust)", lambda: rust_get_course_list(career_html)),
        (
            "get_course_list (Python)",
            lambda: python_get_course_list_baseline(career_html),
        ),
        ("parse_course_info (Rust)", lambda: rust_parse_course_info(course_xml)),
        ("parse_course_info (Python)", lambda: scrape_info(course_xml)),
        ("parse_prereqs (Rust)", lambda: rust_parse_prereqs(prereqs_xml)),
        ("parse_prereqs (Python)", lambda: scrape_prereqs(prereqs_xml)),
    ]

    results = {}
    for name, func in benchmarks:
        print(f"\n  Running {name}...", end=" ", flush=True)
        try:
            result = time_function(func)
            results[name] = result
            print(f"{result['median']:.3f}ms (median)")
        except Exception as e:
            results[name] = {"error": str(e)}
            print(f"ERROR: {e}")

    # Calculate speedups
    print("\n" + "=" * 70)
    print("SPEEDUP ANALYSIS")
    print("=" * 70)

    pairs = [
        ("extract_view_state", "extract_view_state"),
        ("get_plain_text", "get_plain_text"),
        ("get_course_list", "get_course_list"),
        ("parse_course_info", "parse_course_info"),
        ("parse_prereqs", "parse_prereqs"),
    ]

    for rust_name, py_name in pairs:
        rust_key = f"{rust_name} (Rust)"
        py_key = f"{py_name} (Python)"

        if rust_key in results and py_key in results:
            rust_time = results[rust_key].get("median", 0)
            py_time = results[py_key].get("median", 0)

            if rust_time > 0 and py_time > 0:
                speedup = py_time / rust_time
                print(f"\n{py_name}:")
                print(f"  Python: {py_time:.3f}ms")
                print(f"  Rust:   {rust_time:.3f}ms")
                print(f"  Speedup: {speedup:.2f}x")

    print("=" * 70)


if __name__ == "__main__":
    main()
