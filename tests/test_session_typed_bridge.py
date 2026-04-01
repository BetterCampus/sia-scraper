"""Unit tests for typed session payload validation bridge."""

import json

import pytest
from pydantic import ValidationError

from sia_scraper.session import _validate_rust_session_payload


def test_validate_rust_session_payload_accepts_valid_json():
    payload = json.dumps(
        {
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
    )

    parsed = _validate_rust_session_payload(payload)
    assert parsed.status == "ON_CAREER_PAGE"
    assert parsed.course_list[0].course_code == "1000001"


def test_validate_rust_session_payload_requires_json_string():
    with pytest.raises(TypeError, match="JSON string"):
        _validate_rust_session_payload({"status": "CAREER_NOT_SET"})


def test_validate_rust_session_payload_rejects_malformed_course_list():
    payload = json.dumps(
        {
            "session_headers": {},
            "session_cookies": {},
            "params": {"Adf-Page-Id": "0", "Adf-Window-Id": "win-1"},
            "javax_faces_ViewState": "vs-1",
            "career_code": "",
            "career_name": "N/A",
            "is_electives": False,
            "status": "CAREER_NOT_SET",
            "course_list": [{"bad": "shape", "extra": "value"}],
        }
    )

    with pytest.raises(ValidationError):
        _validate_rust_session_payload(payload)
