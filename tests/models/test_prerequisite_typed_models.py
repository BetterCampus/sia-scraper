"""Tests for typed Rust bridge prerequisite models."""

import pytest
from pydantic import ValidationError

from sia_scraper.models.prerequisite import CoursePrereqsTyped


class TestCoursePrereqsTyped:
    def test_valid_payload(self):
        payload = {
            "course_name": "PROGRAMACION I (2016489)",
            "code": None,
            "credits": 3,
            "typology": "DISCIPLINAR OBLIGATORIA",
            "conditions": [
                {
                    "condition": 1,
                    "type": "M",
                    "all_required": True,
                    "number_of_courses": 1,
                    "prerequisites": [
                        {
                            "course_code": "1000001",
                            "course_name": "CALCULO",
                        }
                    ],
                }
            ],
        }

        parsed = CoursePrereqsTyped.model_validate(payload)
        assert parsed.course_name == "PROGRAMACION I (2016489)"
        assert parsed.credits == 3
        assert parsed.conditions[0].prereq_type == "M"
        assert parsed.conditions[0].number_of_courses == 1

    def test_strict_invalid_credits(self):
        with pytest.raises(ValidationError):
            CoursePrereqsTyped.model_validate(
                {
                    "course_name": "X",
                    "code": None,
                    "credits": "3",
                    "typology": "Y",
                    "conditions": [],
                }
            )

    def test_model_dump_returns_dict(self):
        model = CoursePrereqsTyped(
            course_name="X",
            code=None,
            credits=1,
            typology="Y",
            conditions=[],
        )
        dumped = model.model_dump()
        assert dumped["course_name"] == "X"
