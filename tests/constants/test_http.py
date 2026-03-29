"""Tests for HTTP constants module."""

import pytest

from sia_scraper.constants import (
    ADF_ADS_PAGE_ID,
    DEFAULT_TIMEOUT,
    ELECTIVES_CAMPUS_INCREMENT,
    SIA_BASE_URL,
    SIA_HEADERS,
)


@pytest.mark.unit
class TestHttpBasicConstants:
    """Test basic HTTP configuration constants."""

    def test_default_timeout(self) -> None:
        """Test that DEFAULT_TIMEOUT is set to expected value.

        Verifies that the default request timeout for SIA sessions
        is configured to 15 seconds and stored as an integer type.
        """
        assert DEFAULT_TIMEOUT == 15
        assert isinstance(DEFAULT_TIMEOUT, int)

    def test_sia_base_url(self) -> None:
        """Test that SIA_BASE_URL points to the correct endpoint.

        Verifies the base URL for SIA's public service catalog page,
        ensuring it uses HTTPS and points to the correct JSF endpoint.
        """
        assert (
            SIA_BASE_URL
            == "https://sia.unal.edu.co/Catalogo/facespublico/public/servicioPublico.jsf"
        )
        assert SIA_BASE_URL.startswith("https://")

    def test_adf_ads_page_id(self) -> None:
        """Test Oracle ADF page ID constant.

        Verifies the ADF (Application Development Framework) page ID
        used in Oracle's partial page rendering system is set to "1".
        """
        assert ADF_ADS_PAGE_ID == "1"
        assert isinstance(ADF_ADS_PAGE_ID, str)

    def test_electives_campus_increment(self) -> None:
        """Test electives campus code offset value.

        Verifies the numeric offset (40) used to calculate campus codes
        when querying elective courses in the SIA system.
        """
        assert ELECTIVES_CAMPUS_INCREMENT == 40
        assert isinstance(ELECTIVES_CAMPUS_INCREMENT, int)


@pytest.mark.unit
class TestSiaHeaders:
    """Test SIA HTTP headers configuration."""

    def test_sia_headers_structure(self) -> None:
        """Test SIA_HEADERS is a dictionary."""
        assert isinstance(SIA_HEADERS, dict)
        assert len(SIA_HEADERS) > 0

    def test_required_headers_present(self) -> None:
        """Test required Oracle ADF headers are present."""
        required_headers = [
            "authority",
            "accept",
            "adf-ads-page-id",
            "adf-rich-message",
            "content-type",
            "origin",
            "referer",
            "user-agent",
        ]

        for header in required_headers:
            assert header in SIA_HEADERS, f"Header {header} not found in SIA_HEADERS"

    def test_adf_specific_headers(self) -> None:
        """Test Oracle ADF-specific headers have correct values."""
        assert SIA_HEADERS["adf-ads-page-id"] == ADF_ADS_PAGE_ID
        assert SIA_HEADERS["adf-rich-message"] == "true"

    def test_content_type_header(self) -> None:
        """Test content-type header is set for form submission."""
        assert "application/x-www-form-urlencoded" in SIA_HEADERS["content-type"]
        assert "charset=UTF-8" in SIA_HEADERS["content-type"]

    def test_origin_and_referer(self) -> None:
        """Test origin and referer headers match SIA domain."""
        assert SIA_HEADERS["origin"] == "https://sia.unal.edu.co"
        assert SIA_HEADERS["referer"] == SIA_BASE_URL

    def test_security_headers_present(self) -> None:
        """Test security-related headers are present."""
        security_headers = ["sec-fetch-dest", "sec-fetch-mode", "sec-fetch-site"]
        for header in security_headers:
            assert header in SIA_HEADERS

    def test_url_validity(self) -> None:
        """Test SIA base URL is accessible (structure test only)."""
        assert SIA_BASE_URL.startswith("https://")
        assert "sia.unal.edu.co" in SIA_BASE_URL
        assert ".jsf" in SIA_BASE_URL
