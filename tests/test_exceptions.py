"""Tests for exceptions module."""

import pytest

from sia_scraper.exceptions import SiaSessionException


class TestSiaSessionException:
    """Test SiaSessionException and its subclasses."""

    def test_exception_is_exception_subclass(self):
        """Verify SiaSessionException inherits from Exception."""
        assert issubclass(SiaSessionException, Exception)

    def test_session_not_set_is_exception_subclass(self):
        """Verify SessionNotSet inherits from Exception."""
        assert issubclass(SiaSessionException.SessionNotSet, Exception)
        assert issubclass(SiaSessionException.SessionNotSet, SiaSessionException)

    def test_career_not_set_is_exception_subclass(self):
        """Verify CareerNotSet inherits from Exception."""
        assert issubclass(SiaSessionException.CareerNotSet, Exception)
        assert issubclass(SiaSessionException.CareerNotSet, SiaSessionException)

    def test_invalid_status_is_exception_subclass(self):
        """Verify InvalidStatus inherits from Exception."""
        assert issubclass(SiaSessionException.InvalidStatus, Exception)
        assert issubclass(SiaSessionException.InvalidStatus, SiaSessionException)

    def test_timeout_error_is_exception_subclass(self):
        """Verify TimeoutError inherits from Exception."""
        assert issubclass(SiaSessionException.TimeoutError, Exception)
        assert issubclass(SiaSessionException.TimeoutError, SiaSessionException)


class TestExceptionInstances:
    """Test exception instantiation and behavior."""

    def test_raise_session_not_set(self):
        """Verify SessionNotSet can be raised and caught."""
        with pytest.raises(SiaSessionException.SessionNotSet):
            raise SiaSessionException.SessionNotSet()

    def test_raise_career_not_set(self):
        """Verify CareerNotSet can be raised and caught."""
        with pytest.raises(SiaSessionException.CareerNotSet):
            raise SiaSessionException.CareerNotSet()

    def test_raise_invalid_status(self):
        """Verify InvalidStatus can be raised and caught."""
        with pytest.raises(SiaSessionException.InvalidStatus):
            raise SiaSessionException.InvalidStatus()

    def test_raise_timeout_error(self):
        """Verify TimeoutError can be raised and caught."""
        with pytest.raises(SiaSessionException.TimeoutError):
            raise SiaSessionException.TimeoutError()

    def test_exception_has_default_message(self):
        """Verify exception has a default message."""
        exc = SiaSessionException.SessionNotSet()
        assert "session" in str(exc).lower()

    def test_exception_chaining(self):
        """Verify exception chaining works correctly."""
        original = ValueError("original error")
        exc = SiaSessionException.SessionNotSet()
        exc.__cause__ = original
        assert exc.__cause__ is original
