"""Property tests for typed prerequisite models."""

import json

import pytest
from hypothesis import given
from hypothesis import strategies as st

from sia_scraper.models.prerequisite import CoursePrereqsTyped


@given(
    st.fixed_dictionaries(
        {
            "course_name": st.text(min_size=1, max_size=60),
            "code": st.none(),
            "credits": st.integers(min_value=0, max_value=30),
            "typology": st.text(min_size=1, max_size=40),
            "conditions": st.lists(
                st.fixed_dictionaries(
                    {
                        "condition": st.integers(min_value=0, max_value=20),
                        "type": st.text(min_size=1, max_size=8),
                        "all_required": st.booleans(),
                        "number_of_courses": st.integers(min_value=0, max_value=10),
                        "prerequisites": st.lists(
                            st.fixed_dictionaries(
                                {
                                    "course_code": st.text(max_size=10),
                                    "course_name": st.text(max_size=60),
                                }
                            ),
                            max_size=5,
                        ),
                    }
                ),
                max_size=4,
            ),
        }
    )
)
def test_prereq_typed_roundtrip(payload):
    model = CoursePrereqsTyped.model_validate(payload)
    dumped = model.model_dump_json(by_alias=True)
    reparsed = CoursePrereqsTyped.model_validate_json(dumped)
    assert reparsed == model


@given(st.integers(min_value=0, max_value=40))
def test_prereq_typed_credit_bounds(value):
    payload = {
        "course_name": "COURSE",
        "code": None,
        "credits": value,
        "typology": "X",
        "conditions": [],
    }

    serialized = json.dumps(payload)
    if 0 <= value <= 30:
        model = CoursePrereqsTyped.model_validate_json(serialized)
        assert model.credits == value
    else:
        with pytest.raises(Exception):  # noqa: B017 - Pydantic validation errors are runtime exceptions
            CoursePrereqsTyped.model_validate_json(serialized)
