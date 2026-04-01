"""Pytest configuration and shared fixtures for sia_scraper tests."""

import json
import re
import socket
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pytest

from sia_scraper.constants import SIA_BASE_URL

_FIXTURE_DATE_RE = re.compile(r"_(\d{4}-\d{2}-\d{2})\.(?:html|xml|json)$")


def _read_fixture_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Fixture file not found: {path}")
    return path.read_text(encoding="utf-8")


def _read_fixture_bytes(path: Path) -> bytes:
    if not path.exists():
        raise FileNotFoundError(f"Fixture file not found: {path}")
    return path.read_bytes()


def _read_fixture_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Fixture file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _find_latest_fixture_date(fixture_root: Path) -> str:
    dates: set[str] = set()
    for ext_dir in (fixture_root / "html", fixture_root / "xml", fixture_root / "json"):
        if not ext_dir.exists():
            continue
        for path in ext_dir.glob("*"):
            if path.name == ".gitkeep":
                continue
            match = _FIXTURE_DATE_RE.search(path.name)
            if match is not None:
                dates.add(match.group(1))

    if not dates:
        raise RuntimeError(f"No dated fixture files found under {fixture_root}")

    return max(dates)


@pytest.fixture(autouse=True)
def skip_network_if_unreachable():
    """Skip tests marked with @pytest.mark.network if SIA is unreachable.

    This fixture runs automatically for all tests, but only takes effect
    when the test is marked with `network`.
    """
    pass


@pytest.fixture
def fixture_path() -> Path:
    """Return root directory for captured SIA fixtures."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def latest_fixture_date(fixture_path: Path) -> str:
    """Return latest available fixture date in YYYY-MM-DD format."""
    return _find_latest_fixture_date(fixture_path)


@pytest.fixture
def sia_initial_html(fixture_path: Path, latest_fixture_date: str) -> bytes:
    """Return captured initial SIA page HTML as bytes."""
    return _read_fixture_bytes(fixture_path / "html" / f"initial_page_{latest_fixture_date}.html")


@pytest.fixture
def sia_career_page_regular_html(fixture_path: Path, latest_fixture_date: str) -> bytes:
    """Return captured regular-career page HTML as bytes."""
    return _read_fixture_bytes(
        fixture_path / "html" / f"career_page_regular_{latest_fixture_date}.html"
    )


@pytest.fixture
def sia_career_page_electives_html(fixture_path: Path, latest_fixture_date: str) -> bytes:
    """Return captured electives-career page HTML as bytes."""
    return _read_fixture_bytes(
        fixture_path / "html" / f"career_page_electives_{latest_fixture_date}.html"
    )


@pytest.fixture
def sia_session_timeout_html(fixture_path: Path, latest_fixture_date: str) -> bytes:
    """Return captured timeout-response HTML as bytes."""
    return _read_fixture_bytes(
        fixture_path / "html" / f"session_timeout_{latest_fixture_date}.html"
    )


@pytest.fixture
def sia_course_detail_xml(fixture_path: Path, latest_fixture_date: str) -> str:
    """Return captured XML for first regular course detail."""
    return _read_fixture_text(fixture_path / "xml" / f"course_detail_0_{latest_fixture_date}.xml")


@pytest.fixture
def sia_course_detail_xml_all(fixture_path: Path, latest_fixture_date: str) -> list[str]:
    """Return captured XML for all regular course details."""
    paths = sorted((fixture_path / "xml").glob(f"course_detail_*_{latest_fixture_date}.xml"))
    if not paths:
        raise RuntimeError(f"No regular course detail fixtures found for {latest_fixture_date}")
    return [_read_fixture_text(path) for path in paths]


@pytest.fixture
def sia_course_elective_xml_all(fixture_path: Path, latest_fixture_date: str) -> list[str]:
    """Return captured XML for all elective course details."""
    paths = sorted((fixture_path / "xml").glob(f"course_elective_*_{latest_fixture_date}.xml"))
    if not paths:
        raise RuntimeError(f"No elective course detail fixtures found for {latest_fixture_date}")
    return [_read_fixture_text(path) for path in paths]


@pytest.fixture
def sia_course_prereqs_xml(fixture_path: Path, latest_fixture_date: str) -> str:
    """Return captured XML for prerequisites response."""
    return _read_fixture_text(fixture_path / "xml" / f"course_prereqs_{latest_fixture_date}.xml")


@pytest.fixture
def sia_adf_dropdown_xml(fixture_path: Path, latest_fixture_date: str) -> str:
    """Return captured Oracle ADF dropdown update response XML."""
    return _read_fixture_text(
        fixture_path / "xml" / f"adf_dropdown_response_{latest_fixture_date}.xml"
    )


@pytest.fixture
def sia_adf_error_xml(fixture_path: Path, latest_fixture_date: str) -> str:
    """Return captured Oracle ADF error response XML."""
    return _read_fixture_text(
        fixture_path / "xml" / f"adf_error_response_{latest_fixture_date}.xml"
    )


@pytest.fixture
def sia_course_list_regular_json(
    fixture_path: Path, latest_fixture_date: str
) -> list[dict[str, str]]:
    """Return captured regular course list JSON."""
    return _read_fixture_json(
        fixture_path / "json" / f"course_list_regular_{latest_fixture_date}.json"
    )


@pytest.fixture
def sia_course_list_electives_json(
    fixture_path: Path, latest_fixture_date: str
) -> list[dict[str, str]]:
    """Return captured elective course list JSON."""
    return _read_fixture_json(
        fixture_path / "json" / f"course_list_electives_{latest_fixture_date}.json"
    )


@pytest.fixture
def sia_session_data_json(fixture_path: Path, latest_fixture_date: str) -> dict[str, Any]:
    """Return captured sanitized session data JSON."""
    return _read_fixture_json(fixture_path / "json" / f"session_data_{latest_fixture_date}.json")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Automatically skip network-dependent tests when SIA is unreachable.

    Runs before test collection is complete, modifying tests marked with
    `@pytest.mark.network` to skip if the network check fails.
    """
    network_tests = []
    for item in items:
        if item.get_closest_marker("network"):
            network_tests.append(item)

    if not network_tests:
        return

    sia_reachable, error_msg = _check_sia_connectivity()

    if sia_reachable:
        return

    print(
        f"\n"
        f"WARNING: Cannot connect to SIA server at {SIA_BASE_URL}\n"
        f"         Reason: {error_msg}\n"
        f"         Skipping {len(network_tests)} network-dependent test(s):\n"
        + "\n".join(f"           - {item.nodeid}" for item in network_tests)
        + "\n",
        file=sys.stderr,
    )

    for item in network_tests:
        item.add_marker(pytest.mark.skip(reason=f"SIA unreachable: {error_msg}"))


def _check_sia_connectivity() -> tuple[bool, str]:
    """Check if the SIA server is reachable and return status with error message.

    Returns:
        Tuple of (is_reachable, error_message).
        If reachable, error_message is empty string.
        If not reachable, error_message describes the failure.
    """
    parsed = urlparse(SIA_BASE_URL)
    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if host is None:
        return False, f"Invalid SIA URL: {SIA_BASE_URL}"

    try:
        with socket.create_connection((host, port), timeout=5):
            return True, ""
    except TimeoutError:
        return False, "Connection timed out after 5 seconds"
    except OSError as e:
        return False, f"Connection failed: {e}"
    except Exception as e:
        return False, f"Unexpected error: {e}"
