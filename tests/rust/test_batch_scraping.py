"""Integration tests for batch scraping functionality.

Tests the Rust batch scraping implementation through the PyO3 boundary,
verifying ErrorMode behavior, ScrapeResult structure, and exception propagation.
"""

import pytest

sia_scraper_rust = pytest.importorskip("sia_scraper_rust")


class TestScrapeResultModel:
    """Verify ScrapeResult model behavior."""

    def test_scrape_result_has_successes_attribute(self):
        """ScrapeResult should have successes list."""
        result = sia_scraper_rust.ScrapeResult()
        assert hasattr(result, "successes")
        assert isinstance(result.successes, list)

    def test_scrape_result_has_failures_attribute(self):
        """ScrapeResult should have failures list."""
        result = sia_scraper_rust.ScrapeResult()
        assert hasattr(result, "failures")
        assert isinstance(result.failures, list)

    def test_scrape_result_total_empty(self):
        """ScrapeResult.total() should return 0 for empty result."""
        result = sia_scraper_rust.ScrapeResult()
        assert result.total() == 0

    def test_scrape_result_success_rate_empty(self):
        """ScrapeResult.success_rate() should return 1.0 for empty result."""
        result = sia_scraper_rust.ScrapeResult()
        assert result.success_rate() == 1.0

    def test_scrape_result_repr(self):
        """ScrapeResult.__repr__ should return human-readable summary."""
        result = sia_scraper_rust.ScrapeResult()
        repr_str = repr(result)
        assert "ScrapeResult" in repr_str


class TestErrorModeValidation:
    """Verify ErrorMode string parsing in scrape_courses."""

    @pytest.mark.asyncio
    async def test_scrape_courses_rejects_invalid_mode(self):
        """scrape_courses should raise ValueError for invalid mode."""
        session = sia_scraper_rust.PySiaSession()
        with pytest.raises(ValueError, match="Invalid error mode"):
            await session.scrape_courses([0, 1], mode="invalid")

    @pytest.mark.asyncio
    async def test_scrape_courses_accepts_abort_mode(self):
        """scrape_courses should accept 'abort' mode."""
        session = sia_scraper_rust.PySiaSession()
        await session.init_session()
        result = await session.scrape_courses([], mode="abort")
        assert isinstance(result, sia_scraper_rust.ScrapeResult)

    @pytest.mark.asyncio
    async def test_scrape_courses_accepts_skip_mode(self):
        """scrape_courses should accept 'skip' mode."""
        session = sia_scraper_rust.PySiaSession()
        await session.init_session()
        result = await session.scrape_courses([], mode="skip")
        assert isinstance(result, sia_scraper_rust.ScrapeResult)

    @pytest.mark.asyncio
    async def test_scrape_courses_accepts_retry_mode(self):
        """scrape_courses should accept 'retry' mode."""
        session = sia_scraper_rust.PySiaSession()
        await session.init_session()
        result = await session.scrape_courses([], mode="retry")
        assert isinstance(result, sia_scraper_rust.ScrapeResult)

    @pytest.mark.asyncio
    async def test_scrape_courses_case_insensitive_mode(self):
        """scrape_courses should accept case-insensitive mode strings."""
        session = sia_scraper_rust.PySiaSession()
        await session.init_session()
        for mode in ["ABORT", "Abort", "SKIP", "Skip", "RETRY", "Retry"]:
            result = await session.scrape_courses([], mode=mode)
            assert isinstance(result, sia_scraper_rust.ScrapeResult)


class TestBatchScrapingEmptyIndices:
    """Verify batch scraping with empty index list."""

    @pytest.mark.asyncio
    async def test_scrape_courses_empty_list_returns_empty_result(self):
        """scrape_courses with empty list should return empty ScrapeResult."""
        session = sia_scraper_rust.PySiaSession()
        await session.init_session()
        result = await session.scrape_courses([], mode="skip")
        assert result.total() == 0
        assert result.success_rate() == 1.0
        assert len(result.successes) == 0
        assert len(result.failures) == 0

    @pytest.mark.asyncio
    async def test_scrape_courses_empty_list_abort_mode(self):
        """scrape_courses with empty list should work in abort mode."""
        session = sia_scraper_rust.PySiaSession()
        await session.init_session()
        result = await session.scrape_courses([], mode="abort")
        assert result.total() == 0

    @pytest.mark.asyncio
    async def test_scrape_courses_empty_list_retry_mode(self):
        """scrape_courses with empty list should work in retry mode."""
        session = sia_scraper_rust.PySiaSession()
        await session.init_session()
        result = await session.scrape_courses([], mode="retry", retries=5, delay=100)
        assert result.total() == 0


class TestBatchScrapingWithInvalidIndices:
    """Verify batch scraping behavior with invalid course indices."""

    @pytest.mark.asyncio
    async def test_scrape_courses_skip_mode_records_failures(self):
        """scrape_courses in skip mode should record failures, not raise."""
        session = sia_scraper_rust.PySiaSession()
        await session.init_session()
        await session.set_career("0-2-8-3")

        result = await session.scrape_courses([0, 999, 1], mode="skip")
        assert isinstance(result, sia_scraper_rust.ScrapeResult)
        assert result.total() == 3
        assert len(result.failures) > 0

    @pytest.mark.asyncio
    async def test_scrape_courses_abort_mode_raises_on_failure(self):
        """scrape_courses in abort mode should raise on first failure."""
        session = sia_scraper_rust.PySiaSession()
        await session.init_session()
        await session.set_career("0-2-8-3")

        with pytest.raises(sia_scraper_rust.SiaScraperException):
            await session.scrape_courses([999], mode="abort")

    @pytest.mark.asyncio
    async def test_scrape_courses_retry_mode_records_failures(self):
        """scrape_courses in retry mode should record failures after retries."""
        session = sia_scraper_rust.PySiaSession()
        await session.init_session()
        await session.set_career("0-2-8-3")

        result = await session.scrape_courses([999], mode="retry", retries=1, delay=50)
        assert isinstance(result, sia_scraper_rust.ScrapeResult)
        assert len(result.failures) == 1
        assert result.failures[0][0] == 999
