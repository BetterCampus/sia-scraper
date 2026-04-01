"""Tests for typed Rust bridge session models."""

import pytest
from pydantic import ValidationError

from sia_scraper.models.session import SessionStateTyped


class TestSessionStateTyped:
    def test_valid_payload(self):
        payload = {
            "session_headers": {},
            "session_cookies": {},
            "params": {"Adf-Page-Id": "0", "Adf-Window-Id": "win-1"},
            "javax_faces_ViewState": "vs-1",
            "career_code": "0-2-8-3",
            "career_name": "Ingenieria de Sistemas",
            "is_electives": False,
            "status": "ON_CAREER_PAGE",
            "course_list": [
                {"course_code": "1000001", "course_name": "Calculo"},
            ],
        }

        model = SessionStateTyped.model_validate(payload)
        assert model.status == "ON_CAREER_PAGE"
        assert model.course_list[0].course_code == "1000001"
        assert model.course_list_as_dicts() == [{"1000001": "Calculo"}]

    def test_missing_required_params_raises(self):
        with pytest.raises(ValidationError):
            SessionStateTyped.model_validate(
                {
                    "session_headers": {},
                    "session_cookies": {},
                    "params": {},
                    "javax_faces_ViewState": "vs-1",
                    "career_code": "",
                    "career_name": "N/A",
                    "is_electives": False,
                    "status": "CAREER_NOT_SET",
                    "course_list": [],
                }
            )

    def test_invalid_status_raises(self):
        with pytest.raises(ValidationError):
            SessionStateTyped.model_validate(
                {
                    "session_headers": {},
                    "session_cookies": {},
                    "params": {"Adf-Page-Id": "0", "Adf-Window-Id": "win-1"},
                    "javax_faces_ViewState": "vs-1",
                    "career_code": "",
                    "career_name": "N/A",
                    "is_electives": False,
                    "status": "BOGUS_STATUS",
                    "course_list": [],
                }
            )
