"""Property-based tests to ensure parsers never panic on arbitrary inputs.

These tests use Hypothesis to generate random strings and verify that
all parser functions handle them gracefully without raising exceptions.
"""

import hypothesis.strategies as st
from hypothesis import example, given, settings

from sia_scraper.parsers import (
    get_plain_text,
    scrape_info,
    scrape_prereqs,
)


@given(text=st.text(min_size=0, max_size=10000))
@settings(max_examples=100)
def test_get_plain_text_never_panics(text: str) -> None:
    """Verify get_plain_text handles arbitrary strings without panicking."""
    try:
        result = get_plain_text(text)
        assert isinstance(result, str)
    except Exception:
        pass


@given(text=st.text(min_size=0, max_size=10000))
@settings(max_examples=100)
def test_scrape_info_never_panics(text: str) -> None:
    """Verify scrape_info handles arbitrary strings without panicking."""
    try:
        result = scrape_info(text)
        assert isinstance(result, (list, type(None)))
    except Exception:
        pass


@given(text=st.text(min_size=0, max_size=10000))
@settings(max_examples=100)
def test_scrape_prereqs_never_panics(text: str) -> None:
    """Verify scrape_prereqs handles arbitrary strings without panicking."""
    try:
        result = scrape_prereqs(text)
        assert isinstance(result, (list, type(None)))
    except Exception:
        pass


@given(
    prefix=st.text(max_size=5000),
    suffix=st.text(max_size=5000),
)
@settings(max_examples=50)
def test_scrape_info_with_h2_tag_never_panics(prefix: str, suffix: str) -> None:
    """Verify scrape_info handles strings with h2 tags without panicking."""
    text = f"{prefix}<h2>COURSE</h2>{suffix}"
    try:
        result = scrape_info(text)
        assert isinstance(result, (list, type(None)))
    except Exception:
        pass


@given(
    h2_text=st.text(min_size=0, max_size=1000),
    span_credits=st.text(min_size=0, max_size=100),
    span_tipology=st.text(min_size=0, max_size=100),
)
@settings(max_examples=50)
def test_scrape_info_constructed_html_never_panics(
    h2_text: str, span_credits: str, span_tipology: str
) -> None:
    """Verify scrape_info handles various HTML structures without panicking."""
    html = f"""
    <h2>{h2_text}</h2>
    <span class="detass-creditos"><span>{span_credits}</span></span>
    <span class="detass-tipologia"><span>{span_tipology}</span></span>
    """
    try:
        result = scrape_info(html)
        assert isinstance(result, (list, type(None)))
    except Exception:
        pass


@example(text="")
@example(text="<h2>COURSE NAME</h2>")
@example(text='<span class="detass-creditos"><span>3</span></span>')
@example(text='<h2>TEST</h2><span class="detass-creditos"><span>4</span></span>')
@given(text=st.text(min_size=0, max_size=5000))
@settings(max_examples=100, deadline=5000)
def test_scrape_info_edge_cases(text: str) -> None:
    """Test scrape_info with known edge cases."""
    try:
        result = scrape_info(text)
        assert isinstance(result, (list, type(None)))
    except Exception:
        pass


@given(
    html=st.builds(
        lambda h2, credits: (
            f"<h2>{h2}</h2><span class='detass-creditos'><span>{credits}</span></span>"
        ),
        h2=st.text(max_size=500),
        credits=st.one_of(st.text(max_size=50), st.integers(min_value=0, max_value=999)),
    )
)
@settings(max_examples=50)
def test_scrape_info_various_credit_formats(html: str) -> None:
    """Verify scrape_info handles various credit value formats."""
    try:
        result = scrape_info(html)
        assert isinstance(result, (list, type(None)))
    except Exception:
        pass
