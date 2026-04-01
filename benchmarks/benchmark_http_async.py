"""HTTP Async Benchmark Script.

Measures performance of the async HTTP client for sia-scraper.
No baseline comparison available (sync API metrics not collected).
"""

import asyncio
import sys
import time
from typing import Any

sys.path.insert(0, "src")

from sia_scraper.session import SiaSession


async def benchmark_session_creation(num_iterations: int = 10) -> dict[str, float]:
    """Benchmark async session creation."""
    times = []
    for _ in range(num_iterations):
        start = time.perf_counter()
        session = await SiaSession.create(timeout=5)
        elapsed = time.perf_counter() - start
        times.append(elapsed)
        await session.close()

    times.sort()
    return {
        "min": times[0],
        "max": times[-1],
        "mean": sum(times) / len(times),
        "p50": times[len(times) // 2],
        "p95": times[int(len(times) * 0.95)],
    }


async def benchmark_set_career(num_iterations: int = 5) -> dict[str, float]:
    """Benchmark set_career operation."""
    times = []
    for _ in range(num_iterations):
        session = await SiaSession.create(timeout=5)
        start = time.perf_counter()
        await session.set_career("0-2-8-3")
        elapsed = time.perf_counter() - start
        times.append(elapsed)
        await session.close()

    times.sort()
    return {
        "min": times[0],
        "max": times[-1],
        "mean": sum(times) / len(times),
        "p50": times[len(times) // 2],
        "p95": times[int(len(times) * 0.95)],
    }


async def benchmark_concurrent_sessions(num_sessions: int = 10) -> dict[str, Any]:
    """Benchmark concurrent session creation."""

    async def create_session():
        session = await SiaSession.create(timeout=5)
        await session.close()
        return session

    start = time.perf_counter()
    tasks = [create_session() for _ in range(num_sessions)]
    await asyncio.gather(*tasks)
    total_time = time.perf_counter() - start

    return {
        "num_sessions": num_sessions,
        "total_time": total_time,
        "sessions_per_second": num_sessions / total_time,
        "avg_per_session": total_time / num_sessions,
    }


def format_results(name: str, results: dict[str, float]) -> str:
    """Format benchmark results."""
    lines = [f"\n{name}:"]
    for key, value in results.items():
        lines.append(f"  {key}: {value:.4f}s")
    return "\n".join(lines)


async def main():
    print("=" * 60)
    print("SIA Scraper Async HTTP Benchmark")
    print("=" * 60)

    print("\n[1/3] Benchmarking session creation...")
    session_results = await benchmark_session_creation(10)
    print(format_results("Session Creation", session_results))

    print("\n[2/3] Benchmarking set_career...")
    career_results = await benchmark_set_career(5)
    print(format_results("Set Career", career_results))

    print("\n[3/3] Benchmarking concurrent sessions...")
    concurrent_results = await benchmark_concurrent_sessions(10)
    print("\nConcurrent Sessions:")
    print(f"  num_sessions: {concurrent_results['num_sessions']}")
    print(f"  total_time: {concurrent_results['total_time']:.4f}s")
    print(f"  sessions_per_second: {concurrent_results['sessions_per_second']:.2f}")
    print(f"  avg_per_session: {concurrent_results['avg_per_session']:.4f}s")

    print("\n" + "=" * 60)
    print("Benchmark complete!")
    print("=" * 60)
    print("\nNote: No baseline comparison available.")
    print("Sync API metrics were not collected for comparison.")


if __name__ == "__main__":
    asyncio.run(main())
