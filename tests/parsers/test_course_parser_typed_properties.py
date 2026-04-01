"""Property tests for typed Rust bridge payloads."""

import json

import pytest
from hypothesis import given
from hypothesis import strategies as st

from sia_scraper.models.course import CourseInfoTyped


@given(
    st.fixed_dictionaries(
        {
            "course_name": st.text(min_size=1, max_size=40),
            "credits": st.integers(min_value=0, max_value=30),
            "typology": st.text(min_size=1, max_size=40),
            "available_spots": st.integers(min_value=0, max_value=200),
            "scrape_timestamp": st.text(max_size=20),
            "groups": st.lists(
                st.fixed_dictionaries(
                    {
                        "group_name": st.text(min_size=1, max_size=20),
                        "teacher": st.text(min_size=1, max_size=40),
                        "faculty": st.text(max_size=40),
                        "course_name": st.text(min_size=1, max_size=40),
                        "schedules": st.lists(
                            st.fixed_dictionaries(
                                {
                                    "day": st.text(min_size=1, max_size=10),
                                    "start_time": st.from_regex(r"^\d{2}:\d{2}$", fullmatch=True),
                                    "end_time": st.from_regex(r"^\d{2}:\d{2}$", fullmatch=True),
                                    "classroom": st.text(max_size=20),
                                }
                            ),
                            max_size=3,
                        ),
                        "duration": st.text(max_size=20),
                        "schedule_type": st.text(max_size=20),
                        "spots": st.one_of(st.none(), st.integers(min_value=0, max_value=200)),
                        "code": st.none(),
                    }
                ),
                max_size=4,
            ),
            "code": st.none(),
        }
    )
)
def test_typed_model_roundtrip(payload):
    model = CourseInfoTyped.model_validate(payload)
    dumped = model.model_dump_json()
    reparsed = CourseInfoTyped.model_validate_json(dumped)
    assert reparsed == model


@given(st.integers(min_value=0, max_value=40))
def test_typed_model_credit_bounds(value):
    payload = {
        "course_name": "COURSE",
        "credits": value,
        "typology": "T",
        "available_spots": 0,
        "scrape_timestamp": "",
        "groups": [],
        "code": None,
    }

    serialized = json.dumps(payload)
    if 0 <= value <= 30:
        model = CourseInfoTyped.model_validate_json(serialized)
        assert model.credits == value
    else:
        with pytest.raises(Exception):  # noqa: B017 - Pydantic validation errors are runtime exceptions
            CourseInfoTyped.model_validate_json(serialized)
