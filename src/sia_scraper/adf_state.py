"""Oracle ADF ViewState extraction utilities.

This module provides functions for extracting ViewState tokens from Oracle ADF responses.
"""

from typing import Any

from sia_scraper.constants import VIEW_STATE_REGEX
from sia_scraper.exceptions import SiaSessionException


def extract_view_state(html: bytes | str) -> str:
    """Extract ViewState token from HTML content.

    ## Args
        html: HTML content (bytes or string).

    ## Returns
        Extracted ViewState string.

    ## Raises
        SiaSessionException.SessionNotSet: If ViewState not found in HTML.
    """
    if isinstance(html, str):
        html_bytes = html.encode("utf-8")
    else:
        html_bytes = html

    match = VIEW_STATE_REGEX.search(html_bytes)
    if match is None:
        raise SiaSessionException.SessionNotSet from ValueError("ViewState not found in HTML")
    return match.group(1).decode("utf-8")


def extract_view_state_from_response(response: Any) -> str:
    """Extract ViewState token from a response object.

    ## Args
        response: Response object with content or text attribute.

    ## Returns
        Extracted ViewState string.

    ## Raises
        SiaSessionException.SessionNotSet: If response has no content or ViewState not found.
    """
    if hasattr(response, "content") and response.content:
        content = response.content
    elif hasattr(response, "text") and response.text:
        content = response.text
    else:
        raise SiaSessionException.SessionNotSet from ValueError("Response has no content")

    if isinstance(content, str):
        content_bytes = content.encode("utf-8")
    elif isinstance(content, bytes):
        content_bytes = content
    else:
        raise SiaSessionException.SessionNotSet from TypeError(
            f"Content is not string or bytes: {type(content)}"
        )

    match = VIEW_STATE_REGEX.search(content_bytes)
    if match is None:
        raise SiaSessionException.SessionNotSet from ValueError("ViewState not found in response")
    return match.group(1).decode("utf-8")
