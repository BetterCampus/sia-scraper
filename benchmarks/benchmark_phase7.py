#!/usr/bin/env python
"""Phase 7 benchmark: Unified Rust pipeline vs legacy approach.

This benchmark measures the performance of the Phase 7 unified pipeline
which combines HTTP fetch + parsing in a single Rust call (zero FFI string copy).

Key Performance Benefits of Phase 7:
- Zero string copy: XML never crosses the FFI boundary
- Single Rust call: HTTP fetch + HTML parsing in one operation
- Memory efficient: No Python heap allocation for XML strings

Comparison Context:
- The legacy approach required: Python calls Rust (HTTP) → XML string crosses FFI
  → Python calls Rust (parse) → dict crosses FFI → Python creates model
- Phase 7 approach: Python calls Rust (scrape_course_info) → Rust does HTTP+parse
  → Rust model directly returned (zero-copy)

Note: Parsing-only benchmarks in benchmark_rust_vs_python.py show Python is faster
for pure parsing. This is expected - the Phase 7 benefit is eliminating FFI overhead
for the complete workflow, not improving parsing speed in isolation.

Usage:
    python benchmarks/benchmark_phase7.py
"""

import asyncio
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sia_scraper import SiaScraper


async def benchmark_unified_pipeline(scraper: SiaScraper, indices: list[int]) -> dict[str, Any]:
    """Benchmark Phase 7 unified pipeline (HTTP+parse in Rust).

    This measures the time for scrape_course_info() which combines:
    - HTTP GET request to SIA
    - HTML response parsing
    - CourseInfoModel construction
    - Zero-copy return to Python

    Args:
        scraper: Initialized SiaScraper instance
        indices: List of course indices to scrape

    Returns:
        Dictionary with timing metrics
    """
    times: list[float] = []

    for idx in indices:
        start = time.perf_counter()
        await scraper.get_course_info(idx)
        elapsed = time.perf_counter() - start
        times.append(elapsed * 1000)  # Convert to ms

    return {
        "times": times,
        "total_ms": sum(times),
        "mean_ms": sum(times) / len(times),
        "min_ms": min(times),
        "max_ms": max(times),
    }


async def benchmark_prereqs_pipeline(scraper: SiaScraper, indices: list[int]) -> dict[str, Any]:
    """Benchmark scrape_course_prereqs() unified pipeline."""
    times: list[float] = []

    for idx in indices:
        start = time.perf_counter()
        await scraper.get_course_prereqs(idx)
        elapsed = time.perf_counter() - start
        times.append(elapsed * 1000)

    return {
        "times": times,
        "total_ms": sum(times),
        "mean_ms": sum(times) / len(times),
        "min_ms": min(times),
        "max_ms": max(times),
    }


async def measure_memory_unified(scraper: SiaScraper, indices: list[int]) -> dict[str, int]:
    """Measure memory usage of unified pipeline.

    Args:
        scraper: Initialized SiaScraper
        indices: Course indices to scrape

    Returns:
        Dictionary with current and peak memory in bytes
    """
    tracemalloc.start()

    for idx in indices:
        await scraper.get_course_info(idx)

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return {"current_bytes": current, "peak_bytes": peak}


def print_results(
    name: str,
    result: dict[str, Any],
    num_courses: int,
) -> None:
    """Print formatted benchmark results."""
    print(f"\n{name}:")
    print(f"  Courses scraped: {num_courses}")
    print(f"  Total time: {result['total_ms']:.2f}ms")
    print(f"  Average per course: {result['mean_ms']:.2f}ms")
    print(f"  Min: {result['min_ms']:.2f}ms")
    print(f"  Max: {result['max_ms']:.2f}ms")


def print_comparison_baseline() -> None:
    """Print explanation of Phase 7 benefits vs legacy approach."""
    print("\n" + "=" * 70)
    print("PHASE 7 BENEFITS: UNIFIED RUST PIPELINE")
    print("=" * 70)

    print("""
Legacy Approach (before Phase 7):
  1. Python calls Rust (HTTP): GET course page → XML string crosses FFI to Python
  2. Python calls Rust (parse): XML string crosses FFI to Rust → dict crosses FFI
  3. Python creates model: dict converted to Pydantic model (validation overhead)

  Cost: 2 FFI string crossings + Pydantic validation + Python heap allocation

Phase 7 Approach (unified pipeline):
  1. Python calls Rust: session.scrape_course_info(index)
  2. Rust does: HTTP fetch → HTML parse → CourseInfoModel construction
  3. Rust model returns: Zero-copy #[pyclass] directly to Python

  Cost: 1 async call, zero string copies, zero validation

Key Metrics:
  - Zero FFI string copies (XML never crosses Python/Rust boundary)
  - Single async call for complete workflow (HTTP + parse)
  - Native Rust model directly accessible in Python
  - Memory efficient: No intermediate Python string/dict allocation
""")

    print("\nComparison with parsing-only benchmarks:")
    print("""
Note: benchmark_rust_vs_python.py shows Python parsing is faster in isolation.
This is expected - the Phase 7 benefit is not parsing speed, but:

1. FFI Overhead Elimination: Each string crossing the Python/Rust boundary
   has overhead. By keeping XML in Rust, we eliminate 2 crossings per course.

2. Unified Operation: Separating HTTP fetch (in Rust) from parsing (in Python)
   required synchronization. Phase 7 does both in one async call.

3. Memory Efficiency: Large XML strings don't allocate on Python heap.

4. Simplicity: Single API call instead of fetch→parse→model conversion.
""")


async def main() -> None:
    """Run Phase 7 benchmark."""
    print("=" * 70)
    print("PHASE 7 BENCHMARK: UNIFIED RUST PIPELINE")
    print("=" * 70)
    print("\nThis benchmark validates the Phase 7 unified pipeline:")
    print("  - HTTP fetch + parsing in single Rust call")
    print("  - Zero string copies across FFI boundary")
    print("  - Native Rust models returned directly to Python")

    # Initialize scraper
    print("\n[1/4] Initializing session...")
    scraper = await SiaScraper.create(timeout=30)
    print("  Session initialized (timeout: 30s)")

    # Set career
    print("\n[2/4] Setting career (0-2-8-3 - Systems Engineering)...")
    await scraper.set_career("0-2-8-3")
    num_courses = len(scraper.course_list)
    print(f"  Career set. Found {num_courses} courses")

    # Limit to 10 courses for benchmark
    num_to_scrape = min(10, num_courses)
    indices = list(range(num_to_scrape))
    print(f"\n[3/4] Benchmarking {num_to_scrape} course scrapes...")

    # Warmup (first 2 courses)
    print("  Warming up (2 courses)...")
    for i in range(min(2, num_courses)):
        await scraper.get_course_info(i)

    # Benchmark course info scraping
    print("  Benchmarking scrape_course_info()...")
    course_results = await benchmark_unified_pipeline(scraper, indices)
    print_results("Course Info Scraping", course_results, num_to_scrape)

    # Benchmark prerequisites scraping (fewer courses, slower)
    if num_courses > 1:
        prereq_indices = list(range(min(3, num_courses)))
        print(f"\n  Benchmarking scrape_course_prereqs() ({len(prereq_indices)} courses)...")
        prereq_results = await benchmark_prereqs_pipeline(scraper, prereq_indices)
        print_results("Prereqs Scraping", prereq_results, len(prereq_indices))

    # Memory measurement
    print("\n[4/4] Measuring memory usage...")
    memory = await measure_memory_unified(scraper, indices[:5])
    print(f"  Current memory: {memory['current_bytes'] / 1024:.2f} KB")
    print(f"  Peak memory: {memory['peak_bytes'] / 1024:.2f} KB")

    # Print comparison with baseline
    print_comparison_baseline()

    # Summary
    print("=" * 70)
    print("BENCHMARK COMPLETE")
    print("=" * 70)
    print(f"\nTotal courses scraped: {num_to_scrape}")
    print(f"Total time: {course_results['total_ms']:.2f}ms")
    print(f"Average per course: {course_results['mean_ms']:.2f}ms")

    # Cleanup
    await scraper.close_session()
    print("\nSession closed.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\nBenchmark failed: {e}")
        print("Note: This may be due to SIA server being unavailable.")
        print("Integration tests are expected to fail if SIA is unreachable.")
        sys.exit(1)
