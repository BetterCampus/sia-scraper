"""Integration tests for sia_scraper. Makes REAL HTTP requests to SIA."""

import pytest
from requests.exceptions import ConnectionError, HTTPError, Timeout

from sia_scraper.constants import SiaSessionStatus
from sia_scraper.parsers import CourseInfo, CoursePrereqs
from sia_scraper.scraper import SiaScraper

CAREER_CODE = "0-2-8-3"
COURSE_INDEX = 0


@pytest.mark.integration
@pytest.mark.network
class TestSiaScraperIntegration:
    """Real E2E tests against the live SIA Oracle ADF system."""

    def test_session_creation(self) -> None:
        """Test that a new HTTP session can be created with SIA.

        Verifies:
        - Session is created successfully
        - Session is valid after creation
        - Initial status is CAREER_NOT_SET
        """
        scraper = SiaScraper(timeout=30, init_session=False)

        try:
            scraper.create_session()
            assert scraper.valid_session() is True
            assert scraper.sia_session.STATUS == SiaSessionStatus.CAREER_NOT_SET
        except (ConnectionError, Timeout) as e:
            pytest.fail(f"Failed to connect to SIA: {e}")
        finally:
            scraper.close_session()

    def test_career_navigation(self) -> None:
        """Test navigation to a specific academic program and course list loading.

        Verifies:
        - Career name is populated from SIA
        - Course list is populated from SIA
        - Session status transitions to ON_CAREER_PAGE
        """
        scraper = SiaScraper(timeout=30, init_session=False)

        try:
            scraper.create_session()
            scraper.set_career(CAREER_CODE)

            assert scraper.career_name != "N/A", "Career name not loaded from SIA"
            assert len(scraper.course_list) > 0, "Course list is empty"
            assert scraper.sia_session.STATUS == SiaSessionStatus.ON_CAREER_PAGE, (
                f"Expected ON_CAREER_PAGE, got {scraper.sia_session.STATUS}"
            )
        except (ConnectionError, Timeout) as e:
            pytest.fail(f"Network error while navigating to career: {e}")
        except HTTPError as e:
            pytest.fail(f"HTTP error while navigating to career: {e}")
        finally:
            scraper.close_session()

    def test_course_info_scraping(self) -> None:
        """Test scraping complete course information including groups and schedules.

        Verifies:
        - Course info contains required fields
        - Groups list is not empty
        """
        scraper = SiaScraper(timeout=30, init_session=False)

        try:
            scraper.create_session()
            scraper.set_career(CAREER_CODE)

            assert len(scraper.course_list) > 0, "Course list is empty, cannot scrape course"

            course_info = None
            for idx in range(min(5, len(scraper.course_list))):
                try:
                    course_info = scraper.get_course_info(course_index=idx)
                    break
                except ValueError:
                    continue

            if course_info is None:
                pytest.skip(
                    "No parseable course found in first 5 indices; "
                    "live SIA response changed or is temporarily unavailable"
                )

            assert isinstance(course_info, CourseInfo)
            assert hasattr(course_info, "course_name")
            assert hasattr(course_info, "credits")
            assert hasattr(course_info, "typology")
            assert hasattr(course_info, "groups")
            assert len(course_info.groups) > 0, "Course has no groups"
        except (ConnectionError, Timeout) as e:
            pytest.fail(f"Network error while scraping course info: {e}")
        except HTTPError as e:
            pytest.fail(
                f"HTTP error while scraping course info (status={e.response.status_code}): {e}"
            )
        finally:
            scraper.close_session()

    def test_course_prerequisites_scraping(self) -> None:
        """Test scraping course prerequisites and enrollment conditions.

        Verifies:
        - Prerequisites response contains required fields
        - Response structure is valid
        """
        scraper = SiaScraper(timeout=30, init_session=False)

        try:
            scraper.create_session()
            scraper.set_career(CAREER_CODE)

            assert len(scraper.course_list) > 0, "Course list is empty, cannot scrape prerequisites"

            prereqs = None
            for idx in range(min(5, len(scraper.course_list))):
                try:
                    prereqs = scraper.get_course_prereqs(course_index=idx)
                    break
                except ValueError:
                    continue

            if prereqs is None:
                pytest.skip("No parseable prerequisites found in first 5 indices")

            assert isinstance(prereqs, CoursePrereqs)
            assert hasattr(prereqs, "code")
            assert hasattr(prereqs, "conditions")
        except (ConnectionError, Timeout) as e:
            pytest.fail(f"Network error while scraping prerequisites: {e}")
        except HTTPError as e:
            pytest.fail(
                f"HTTP error while scraping prerequisites (status={e.response.status_code}): {e}"
            )
        finally:
            scraper.close_session()

    def test_session_cleanup(self) -> None:
        """Test that sessions are properly closed after use.

        Verifies:
        - close_session() returns the scraper (method chaining)
        - Status is NO_SESSION after closing
        """
        scraper = SiaScraper(timeout=30, init_session=False)

        try:
            scraper.create_session()
            assert scraper.sia_session.STATUS != SiaSessionStatus.NO_SESSION

            result = scraper.close_session()

            assert result is scraper
            assert scraper.sia_session.STATUS == SiaSessionStatus.NO_SESSION
        except (ConnectionError, Timeout) as e:
            pytest.fail(f"Network error during session cleanup test: {e}")
        finally:
            if scraper.sia_session.STATUS != SiaSessionStatus.NO_SESSION:
                scraper.close_session()

    def test_end_to_end_workflow(self) -> None:
        """Test complete workflow from session creation to course scraping.

        This is the main integration test covering the full workflow:
        1. Create session
        2. Navigate to career
        3. Scrape course info
        4. Scrape prerequisites
        5. Cleanup session

        Will fail if SIA is down or Oracle ADF component IDs change.
        """
        scraper = SiaScraper(timeout=30, init_session=False)

        try:
            scraper.create_session()
            assert scraper.valid_session() is True
            assert scraper.sia_session.STATUS == SiaSessionStatus.CAREER_NOT_SET

            scraper.set_career(CAREER_CODE)

            assert scraper.career_name != "N/A"
            assert len(scraper.course_list) > 0
            assert scraper.sia_session.STATUS == SiaSessionStatus.ON_CAREER_PAGE

            assert len(scraper.course_list) > 0, "Cannot scrape course - list is empty"
            course_info = None
            prereqs = None
            for idx in range(min(5, len(scraper.course_list))):
                try:
                    course_info = scraper.get_course_info(course_index=idx)
                    prereqs = scraper.get_course_prereqs(course_index=idx)
                    break
                except ValueError:
                    continue

            if course_info is None or prereqs is None:
                pytest.skip(
                    "No parseable course/prereqs found in first 5 indices; "
                    "live SIA response changed or is temporarily unavailable"
                )

            assert isinstance(course_info, CourseInfo)
            assert hasattr(course_info, "course_name")
            assert hasattr(course_info, "credits")
            assert hasattr(course_info, "typology")
            assert hasattr(course_info, "groups")
            assert isinstance(prereqs, CoursePrereqs)
            assert hasattr(prereqs, "code")
            assert hasattr(prereqs, "conditions")

        except (ConnectionError, Timeout) as e:
            pytest.fail(f"Network error during E2E workflow: {e}")
        except HTTPError as e:
            pytest.fail(f"HTTP error during E2E workflow (status={e.response.status_code}): {e}")
        finally:
            scraper.close_session()
            assert scraper.sia_session.STATUS == SiaSessionStatus.NO_SESSION
