"""Integration tests for batch scraping functionality.

Tests the Rust batch scraping implementation through the PyO3 boundary,
verifying ErrorMode behavior, ScrapeResult structure, and exception propagation.

Note: Some tests use the `initialized_session` fixture which makes real network
requests to SIA. These are integration tests and should be skipped in environments
without network access using @pytest.mark.network marker.
"""

import pytest

sia_scraper_rust = pytest.importorskip("sia_scraper_rust")


@pytest.fixture(scope="function")
async def initialized_session():
    """Provide an initialized PySiaSession with cleanup.

    Warning: This fixture makes live network requests to SIA via
    PySiaSession.init_session() and PySiaSession.reset().
    Tests using it are integration tests and must be marked with
    @pytest.mark.network so they can be excluded from hermetic unit runs.

    Scope: function - Each test gets a fresh session for maximum isolation.
    This is intentionally kept as an integration test fixture rather than mocked
    to test the full stack from Python through Rust to network.
    """
    session = sia_scraper_rust.PySiaSession()
    await session.init_session()
    yield session
    await session.reset()


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
        """scrape_courses should raise SiaScraperException for invalid mode."""
        # Note: Mode parsing happens before session check, so no init needed
        session = sia_scraper_rust.PySiaSession()
        with pytest.raises(sia_scraper_rust.SiaScraperException, match="Invalid error mode"):
            await session.scrape_courses([0, 1], mode="invalid")

    @pytest.mark.asyncio
    @pytest.mark.network
    async def test_scrape_courses_accepts_abort_mode(self, initialized_session):
        """scrape_courses should accept 'abort' mode."""
        result = await initialized_session.scrape_courses([], mode="abort")
        assert isinstance(result, sia_scraper_rust.ScrapeResult)

    @pytest.mark.asyncio
    @pytest.mark.network
    async def test_scrape_courses_accepts_skip_mode(self, initialized_session):
        """scrape_courses should accept 'skip' mode."""
        result = await initialized_session.scrape_courses([], mode="skip")
        assert isinstance(result, sia_scraper_rust.ScrapeResult)

    @pytest.mark.asyncio
    @pytest.mark.network
    async def test_scrape_courses_accepts_retry_mode(self, initialized_session):
        """scrape_courses should accept 'retry' mode."""
        result = await initialized_session.scrape_courses([], mode="retry")
        assert isinstance(result, sia_scraper_rust.ScrapeResult)

    @pytest.mark.asyncio
    @pytest.mark.network
    async def test_scrape_courses_case_insensitive_mode(self, initialized_session):
        """scrape_courses should accept case-insensitive mode strings."""
        for mode in ["ABORT", "Abort", "SKIP", "Skip", "RETRY", "Retry"]:
            result = await initialized_session.scrape_courses([], mode=mode)
            assert isinstance(result, sia_scraper_rust.ScrapeResult)


class TestBatchScrapingEmptyIndices:
    """Verify batch scraping with empty index list."""

    @pytest.mark.asyncio
    @pytest.mark.network
    async def test_scrape_courses_empty_list_returns_empty_result(self, initialized_session):
        """scrape_courses with empty list should return empty ScrapeResult."""
        result = await initialized_session.scrape_courses([], mode="skip")
        assert result.total() == 0
        assert result.success_rate() == 1.0
        assert len(result.successes) == 0
        assert len(result.failures) == 0

    @pytest.mark.asyncio
    @pytest.mark.network
    async def test_scrape_courses_empty_list_abort_mode(self, initialized_session):
        """scrape_courses with empty list should work in abort mode."""
        result = await initialized_session.scrape_courses([], mode="abort")
        assert result.total() == 0

    @pytest.mark.asyncio
    @pytest.mark.network
    async def test_scrape_courses_empty_list_retry_mode(self, initialized_session):
        """scrape_courses with empty list should work in retry mode."""
        result = await initialized_session.scrape_courses([], mode="retry", retries=5, delay=100)
        assert result.total() == 0


class TestBatchScrapingWithInvalidIndices:
    """Verify batch scraping behavior with invalid course indices."""

    @pytest.mark.asyncio
    @pytest.mark.network
    async def test_scrape_courses_skip_mode_records_failures(self, initialized_session):
        """scrape_courses in skip mode should record failures, not raise."""
        await initialized_session.set_career("0-2-8-3")

        requested = [0, 999, 1]
        result = await initialized_session.scrape_courses(requested, mode="skip")
        assert isinstance(result, sia_scraper_rust.ScrapeResult)
        assert result.total() == len(requested)
        # Index 999 is always out of range, so it should always be in failures
        failure_indices = [idx for idx, _ in result.failures]
        assert 999 in failure_indices
        # Verify at least one failure was recorded (999 is definitely invalid)
        assert len(result.failures) >= 1

    @pytest.mark.asyncio
    @pytest.mark.network
    async def test_scrape_courses_abort_mode_raises_on_failure(self, initialized_session):
        """scrape_courses in abort mode should raise on first failure."""
        await initialized_session.set_career("0-2-8-3")

        with pytest.raises(sia_scraper_rust.AbortError):
            await initialized_session.scrape_courses([999], mode="abort")

    @pytest.mark.asyncio
    @pytest.mark.network
    async def test_scrape_courses_retry_mode_records_failures(self, initialized_session):
        """scrape_courses in retry mode should record failures for invalid indices.

        Note: Course index 999 produces HttpError::InvalidInput which is
        non-retryable per retry.rs should_retry(). The test verifies that
        retry mode still records the failure correctly even when retries
        are not applicable.
        """
        await initialized_session.set_career("0-2-8-3")

        result = await initialized_session.scrape_courses([999], mode="retry", retries=1, delay=50)
        assert isinstance(result, sia_scraper_rust.ScrapeResult)
        assert len(result.failures) == 1
        assert result.failures[0][0] == 999
