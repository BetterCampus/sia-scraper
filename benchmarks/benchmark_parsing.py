#!/usr/bin/env python
"""Parser-specific benchmarks for sia-scraper.

This module provides isolated benchmarks for HTML parsing performance,
allowing direct comparison between Python/lxml and future Rust implementations.

Usage:
    python benchmarks/benchmark_parsing.py
    python benchmarks/benchmark_parsing.py --compare-rust  # After Rust migration
"""

import argparse
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sia_scraper.core import extract_view_state
from sia_scraper.parsers import scrape_info, scrape_prereqs
from sia_scraper.parsers.html_parser import HtmlParser

FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures"


def load_fixture(filename: str, subdir: str = "xml") -> str:
    """Load fixture file from xml or html subdirectory."""
    path = FIXTURES_DIR / subdir / filename
    return path.read_text(encoding="utf-8")


def time_function(
    func: Callable, *args: Any, iterations: int = 100, **kwargs: Any
) -> dict[str, Any]:
    """Time a function over multiple iterations."""

    # Warmup
    for _ in range(5):
        func(*args, **kwargs)

    # Benchmark
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        func(*args, **kwargs)
        end = time.perf_counter()
        times.append(end - start)

    times.sort()

    return {
        "min": min(times) * 1000,  # ms
        "max": max(times) * 1000,  # ms
        "mean": sum(times) / len(times) * 1000,  # ms
        "median": times[len(times) // 2] * 1000,  # ms
        "std_dev": (sum((t - sum(times) / len(times)) ** 2 for t in times) / len(times)) ** 0.5
        * 1000,
        "iterations": iterations,
    }


def benchmark_html_parser_init(html: str) -> dict[str, Any]:
    """Benchmark HtmlParser initialization."""
    return time_function(HtmlParser, html)


def benchmark_html_parser_find(html: str) -> dict[str, Any]:
    """Benchmark HtmlParser.find() method."""
    parser = HtmlParser(html)
    return time_function(parser.find, "span.detass-creditos")


def benchmark_html_parser_text_content(html: str) -> dict[str, Any]:
    """Benchmark text content extraction."""
    parser = HtmlParser(html)
    return time_function(parser.text_content)


def benchmark_scrape_info(xml: str) -> dict[str, Any]:
    """Benchmark full scrape_info function."""
    return time_function(scrape_info, xml, iterations=20)


def benchmark_extract_view_state(html: str) -> dict[str, Any]:
    """Benchmark ViewState extraction."""
    return time_function(extract_view_state, html, iterations=1000)


def benchmark_scrape_prereqs(xml: str) -> dict[str, Any]:
    """Benchmark prerequisite scraping."""
    try:
        return time_function(scrape_prereqs, xml, iterations=20)
    except FileNotFoundError:
        return {"error": "Prereqs fixture not found", "iterations": 0}


def run_all_benchmarks(
    course_xml: str, prereqs_xml: str | None, career_html: str, output_file: str | None = None
) -> dict[str, Any]:
    """Run all benchmarks and return results."""

    print("Running parser benchmarks...")
    print(f"  Course XML size: {len(course_xml)} bytes")

    results: dict[str, Any] = {
        "course_xml_size_bytes": len(course_xml),
        "benchmarks": {},
    }

    benchmarks = [
        ("html_parser_init", lambda: benchmark_html_parser_init(course_xml)),
        ("html_parser_find", lambda: benchmark_html_parser_find(course_xml)),
        ("html_parser_text_content", lambda: benchmark_html_parser_text_content(course_xml)),
        ("scrape_info", lambda: benchmark_scrape_info(course_xml)),
        ("extract_view_state", lambda: benchmark_extract_view_state(career_html)),
        ("scrape_prereqs", lambda: benchmark_scrape_prereqs(prereqs_xml) if prereqs_xml else None),
    ]

    for name, func in benchmarks:
        print(f"  - {name}...", end=" ", flush=True)
        try:
            result = func()
            if result is None:
                results["benchmarks"][name] = {"skipped": "No data available"}
                print("SKIPPED")
            elif "error" in result:
                results["benchmarks"][name] = result
                print(f"ERROR: {result['error']}")
            else:
                results["benchmarks"][name] = result
                print(f"{result['mean']:.3f}ms (median)")
        except Exception as e:
            results["benchmarks"][name] = {"error": str(e)}
            print(f"ERROR: {e}")

    return results


def print_benchmark_report(results: dict[str, Any]) -> None:
    """Print formatted benchmark report."""

    print("\n" + "=" * 70)
    print("PARSER BENCHMARK RESULTS")
    print("=" * 70)
    print(f"\nHTML Size: {results.get('html_size_bytes', 0):,} bytes")
    print("\n{:<35} {:>10} {:>10} {:>10}".format("Benchmark", "Mean (ms)", "Min (ms)", "Max (ms)"))
    print("-" * 70)

    benchmarks = results.get("benchmarks", {})
    for name, data in benchmarks.items():
        if "error" in data:
            print(f"  {name:<33} ERROR: {data['error']}")
        else:
            print(f"  {name:<33} {data['mean']:10.3f} {data['min']:10.3f} {data['max']:10.3f}")

    print("\n" + "=" * 70)

    # Calculate speedup estimates for Rust migration
    print("\nEstimated Rust Speedup (conservative 2-3x):")
    if "scrape_info" in benchmarks and "mean" in benchmarks["scrape_info"]:
        py_time = benchmarks["scrape_info"]["mean"]
        rust_time_2x = py_time / 2
        rust_time_3x = py_time / 3
        print(f"  Current scrape_info: {py_time:.2f}ms")
        print(f"  Expected (2x faster): {rust_time_2x:.2f}ms")
        print(f"  Expected (3x faster): {rust_time_3x:.2f}ms")

    print("=" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark sia-scraper parsers")
    parser.add_argument("--output", "-o", help="Output JSON file for results", default=None)
    args = parser.parse_args()

    # Load fixtures
    course_xml = load_fixture("course_detail_0_2026-03-30.xml", "xml")
    prereqs_xml = load_fixture("course_prereqs_2026-03-30.xml", "xml")
    career_html = load_fixture("career_page_regular_2026-03-30.html", "html")

    results = run_all_benchmarks(course_xml, prereqs_xml, career_html, args.output)
    print_benchmark_report(results)

    if args.output:
        import json

        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {args.output}")


if __name__ == "__main__":
    main()
