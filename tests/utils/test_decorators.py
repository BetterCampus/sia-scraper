"""Tests for decorators module."""

import pytest
from requests import ConnectionError, ReadTimeout, Timeout

from sia_scraper.constants import SiaSessionStatus
from sia_scraper.core import SiaSessionException
from sia_scraper.session import SiaSession
from sia_scraper.utils import check_session, check_status, handle_timeout_error


class TestCheckSessionDecorator:
    """Test check_session decorator."""

    def test_decorator_allows_valid_session(self, mocker):
        session = mocker.MagicMock(spec=SiaSession)
        session._has_session = True

        @check_session
        def sample_method(self):
            return "success"

        assert sample_method(session) == "success"

    def test_decorator_raises_when_no_session(self, mocker):
        session = mocker.MagicMock(spec=SiaSession)
        session._has_session = False

        @check_session
        def sample_method(self):
            return "success"

        with pytest.raises(SiaSessionException.SessionNotSet):
            sample_method(session)


class TestCheckStatusDecorator:
    """Test check_status decorator factory."""

    def test_decorator_allows_matching_status(self, mocker):
        session = mocker.MagicMock(spec=SiaSession)
        session.STATUS = SiaSessionStatus.ON_CAREER_PAGE

        @check_status(SiaSessionStatus.ON_CAREER_PAGE)
        def sample_method(self):
            return "success"

        assert sample_method(session) == "success"

    def test_decorator_raises_on_mismatched_status(self, mocker):
        session = mocker.MagicMock(spec=SiaSession)
        session.STATUS = SiaSessionStatus.NO_SESSION

        @check_status(SiaSessionStatus.ON_CAREER_PAGE)
        def sample_method(self):
            return "success"

        with pytest.raises(SiaSessionException.InvalidStatus):
            sample_method(session)


class TestHandleTimeoutErrorDecorator:
    """Test handle_timeout_error decorator."""

    def test_decorator_passes_normal_result(self):
        expected = "success"

        @handle_timeout_error
        def sample_method():
            return expected

        assert sample_method() == expected

    def test_decorator_converts_timeout_exception(self):
        original = Timeout("connection timeout")

        @handle_timeout_error
        def sample_method():
            raise original

        with pytest.raises(SiaSessionException.TimeoutError) as exc_info:
            sample_method()
        assert exc_info.value.__cause__ is original

    def test_decorator_converts_read_timeout_exception(self):
        original = ReadTimeout()

        @handle_timeout_error
        def sample_method():
            raise original

        with pytest.raises(SiaSessionException.TimeoutError):
            sample_method()

    def test_decorator_converts_connection_error(self):
        original = ConnectionError("connection refused")

        @handle_timeout_error
        def sample_method():
            raise original

        with pytest.raises(SiaSessionException.TimeoutError):
            sample_method()

    def test_decorator_preserves_other_exceptions(self):
        original = ValueError("some other error")

        @handle_timeout_error
        def sample_method():
            raise original

        with pytest.raises(ValueError) as exc_info:
            sample_method()
        assert exc_info.value is original
