"""Cross-module integration tests for constants package.

These tests verify relationships and integrity across multiple constants modules.
"""

import pytest

from sia_scraper.constants import (
    ADF_ADS_PAGE_ID,
    CAMPUS_DD,
    CAMPUS_DD_ID,
    CAMPUS_ELECTIVES_DD,
    CAMPUS_ELECTIVES_DD_ID,
    CAREER_DD,
    CAREER_DD_ID,
    DATA_MAP,
    FACULTY_CAREER_DD,
    FACULTY_CAREER_DD_ID,
    FACULTY_DD,
    FACULTY_DD_ID,
    SIA_BASE_URL,
    SIA_HEADERS,
    STUDY_LEVEL_DD,
    STUDY_LEVEL_DD_ID,
    TIPOLOGY_DD,
    TIPOLOGY_DD_ID,
)


@pytest.mark.unit
class TestConstantsIntegration:
    """Test cross-module constants integrity."""

    def test_adf_headers_match_constants(self) -> None:
        """Test SIA_HEADERS references ADF_ADS_PAGE_ID correctly."""
        assert SIA_HEADERS["adf-ads-page-id"] == ADF_ADS_PAGE_ID

    def test_headers_referer_matches_base_url(self) -> None:
        """Test referer header matches SIA_BASE_URL."""
        assert SIA_HEADERS["referer"] == SIA_BASE_URL

    def test_dropdown_action_to_id_consistency(self) -> None:
        """Test dropdown actions map to correct component IDs."""
        expected_mappings = [
            (STUDY_LEVEL_DD, STUDY_LEVEL_DD_ID),
            (CAMPUS_DD, CAMPUS_DD_ID),
            (FACULTY_DD, FACULTY_DD_ID),
            (CAREER_DD, CAREER_DD_ID),
            (TIPOLOGY_DD, TIPOLOGY_DD_ID),
            (FACULTY_CAREER_DD, FACULTY_CAREER_DD_ID),
            (CAMPUS_ELECTIVES_DD, CAMPUS_ELECTIVES_DD_ID),
        ]

        for action, expected_id in expected_mappings:
            assert action in DATA_MAP
            actual_id, _ = DATA_MAP[action]
            assert actual_id == expected_id

    def test_all_dropdown_ids_are_unique(self) -> None:
        """Test all dropdown component IDs are unique."""
        dropdown_ids = [
            STUDY_LEVEL_DD_ID,
            CAMPUS_DD_ID,
            FACULTY_DD_ID,
            CAREER_DD_ID,
            TIPOLOGY_DD_ID,
            FACULTY_CAREER_DD_ID,
            CAMPUS_ELECTIVES_DD_ID,
        ]
        assert len(dropdown_ids) == len(set(dropdown_ids))

    def test_dropdowns_derived_ids_match_action_ids(self) -> None:
        """Test derived DROPDOWNS list matches component IDs."""
        from sia_scraper.constants import DROPDOWNS

        expected = [
            f"{STUDY_LEVEL_DD_ID}::content",
            f"{CAMPUS_DD_ID}::content",
            f"{FACULTY_DD_ID}::content",
            f"{CAREER_DD_ID}::content",
        ]
        assert DROPDOWNS == expected
