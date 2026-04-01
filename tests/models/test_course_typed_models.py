"""Tests for typed Rust bridge course models."""

import pytest
from pydantic import ValidationError

from sia_scraper.models.course import CourseInfoTyped, GroupTyped, ScheduleTyped


class TestCourseInfoTyped:
    def test_valid_payload(self):
        payload = {
            "course_name": "CALCULO AVANZADO",
            "credits": 4,
            "typology": "DISCIPLINAR OBLIGATORIA",
            "available_spots": 10,
            "scrape_timestamp": "",
            "groups": [
                {
                    "group_name": "GRUPO 01",
                    "teacher": "Profesor Uno",
                    "faculty": "Facultad de Ciencias",
                    "course_name": "CALCULO AVANZADO",
                    "schedules": [
                        {
                            "day": "Lunes",
                            "start_time": "08:00",
                            "end_time": "10:00",
                            "classroom": "A101",
                        }
                    ],
                    "duration": "16 SEMANAS",
                    "schedule_type": "DIURNA",
                    "spots": 10,
                    "code": None,
                }
            ],
            "code": None,
        }

        parsed = CourseInfoTyped.model_validate(payload)
        assert parsed.course_name == "CALCULO AVANZADO"
        assert parsed.credits == 4
        assert parsed.available_spots == 10
        assert len(parsed.groups) == 1
        assert isinstance(parsed.groups[0], GroupTyped)
        assert isinstance(parsed.groups[0].schedules[0], ScheduleTyped)

    def test_strict_invalid_credits(self):
        payload = {
            "course_name": "X",
            "credits": "4",
            "typology": "Y",
            "available_spots": 0,
            "scrape_timestamp": "",
            "groups": [],
            "code": None,
        }
        with pytest.raises(ValidationError):
            CourseInfoTyped.model_validate(payload)

    def test_model_dump_returns_dict(self):
        model = CourseInfoTyped(
            course_name="X",
            credits=1,
            typology="Y",
            available_spots=0,
            scrape_timestamp="",
            groups=[],
            code=None,
        )
        data = model.model_dump()
        assert data["course_name"] == "X"
