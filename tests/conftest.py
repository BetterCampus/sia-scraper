"""Pytest configuration and shared fixtures for sia_scraper tests."""

import sys

import pytest
from requests.exceptions import ConnectionError, Timeout

from sia_scraper.constants import SIA_BASE_URL


@pytest.fixture(autouse=True)
def skip_network_if_unreachable():
    """Skip tests marked with @pytest.mark.network if SIA is unreachable.

    This fixture runs automatically for all tests, but only takes effect
    when the test is marked with `network`.
    """
    pass


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
    import requests

    try:
        response = requests.head(SIA_BASE_URL, timeout=5)
        if response.status_code >= 500:
            return False, f"Server returned HTTP {response.status_code}"
        return True, ""
    except Timeout:
        return False, "Connection timed out after 5 seconds"
    except ConnectionError as e:
        return False, f"Connection failed: {e}"
    except Exception as e:
        return False, f"Unexpected error: {e}"
