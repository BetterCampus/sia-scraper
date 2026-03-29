"""Tests for decorators module."""

import pytest
from requests import ConnectionError, ReadTimeout, Timeout

from sia_scraper.constants import SiaSessionStatus
from sia_scraper.decorators import check_career, check_session, check_status, handle_timeout_error
from sia_scraper.exceptions import SiaSessionException
from sia_scraper.session import SiaSession


class TestCheckSessionDecorator:
    """Test check_session decorator."""

    def test_decorator_allows_valid_session(self, mocker):
        """Verify decorated method runs when session exists."""
        session = mocker.MagicMock(spec=SiaSession)
        session._SiaSession__session = mocker.MagicMock()

        @check_session
        def sample_method(self):
            return "success"

        result = sample_method(session)
        assert result == "success"

    def test_decorator_raises_when_no_session(self, mocker):
        """Verify decorated method raises SessionNotSet when session is None."""
        session = mocker.MagicMock(spec=SiaSession)
        session._SiaSession__session = None

        @check_session
        def sample_method(self):
            return "success"

        with pytest.raises(SiaSessionException.SessionNotSet):
            sample_method(session)


class TestCheckCareerDecorator:
    """Test check_career decorator."""

    def test_decorator_allows_with_career(self, mocker):
        """Verify decorated method runs when career_code is set."""
        session = mocker.MagicMock(spec=SiaSession)
        session._SiaSession__career_code = "1-2-3-4"

        @check_career
        def sample_method(self):
            return "success"

        result = sample_method(session)
        assert result == "success"

    def test_decorator_raises_when_no_career(self, mocker):
        """Verify decorated method raises CareerNotSet when career_code is empty."""
        session = mocker.MagicMock(spec=SiaSession)
        session._SiaSession__career_code = ""

        @check_career
        def sample_method(self):
            return "success"

        with pytest.raises(SiaSessionException.CareerNotSet):
            sample_method(session)


class TestCheckStatusDecorator:
    """Test check_status decorator factory."""

    def test_decorator_allows_matching_status(self, mocker):
        """Verify decorated method runs when STATUS matches required status."""
        session = mocker.MagicMock(spec=SiaSession)
        session._SiaSession__STATUS = SiaSessionStatus.ON_CAREER_PAGE

        @check_status(SiaSessionStatus.ON_CAREER_PAGE)
        def sample_method(self):
            return "success"

        result = sample_method(session)
        assert result == "success"

    def test_decorator_raises_on_mismatched_status(self, mocker):
        """Verify decorated method raises InvalidStatus when STATUS doesn't match."""
        session = mocker.MagicMock(spec=SiaSession)
        session._SiaSession__STATUS = SiaSessionStatus.NO_SESSION

        @check_status(SiaSessionStatus.ON_CAREER_PAGE)
        def sample_method(self):
            return "success"

        with pytest.raises(SiaSessionException.InvalidStatus):
            sample_method(session)


class TestHandleTimeoutErrorDecorator:
    """Test handle_timeout_error decorator."""

    def test_decorator_passes_normal_result(self, mocker):
        """Verify decorated method returns result normally."""
        expected = "success"

        @handle_timeout_error
        def sample_method():
            return expected

        result = sample_method()
        assert result == expected

    def test_decorator_converts_timeout_exception(self, mocker):
        """Verify Timeout exception is converted to SiaSessionException.TimeoutError."""
        original = Timeout("connection timeout")

        @handle_timeout_error
        def sample_method():
            raise original

        with pytest.raises(SiaSessionException.TimeoutError) as exc_info:
            sample_method()
        assert exc_info.value.__cause__ is original

    def test_decorator_converts_read_timeout_exception(self, mocker):
        """Verify ReadTimeout exception is converted to SiaSessionException.TimeoutError."""
        original = ReadTimeout()

        @handle_timeout_error
        def sample_method():
            raise original

        with pytest.raises(SiaSessionException.TimeoutError):
            sample_method()

    def test_decorator_converts_connection_error(self, mocker):
        """Verify ConnectionError is converted to SiaSessionException.TimeoutError."""
        original = ConnectionError("connection refused")

        @handle_timeout_error
        def sample_method():
            raise original

        with pytest.raises(SiaSessionException.TimeoutError):
            sample_method()

    def test_decorator_preserves_other_exceptions(self, mocker):
        """Verify non-timeout exceptions are not caught and are re-raised."""
        original = ValueError("some other error")

        @handle_timeout_error
        def sample_method():
            raise original

        with pytest.raises(ValueError) as exc_info:
            sample_method()
        assert exc_info.value is original
