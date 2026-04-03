"""Tests for exception integration between Python and Rust layers."""

import pytest

import sia_scraper_rust
from sia_scraper.core import SiaSessionException
from sia_scraper.core.exceptions import (
    HttpStatusError,
    NetworkError,
    ParseError,
    SessionError,
    SiaScraperException,
    SiaTimeoutError,
)


class TestRustExceptionReExports:
    """Verify that Rust exceptions are properly re-exported."""

    def test_network_error_is_exported(self):
        """NetworkError should be importable from sia_scraper.core.exceptions."""
        assert NetworkError is sia_scraper_rust.NetworkError

    def test_http_status_error_is_exported(self):
        """HttpStatusError should be importable from sia_scraper.core.exceptions."""
        assert HttpStatusError is sia_scraper_rust.HttpStatusError

    def test_sia_timeout_error_is_exported(self):
        """SiaTimeoutError should be importable from sia_scraper.core.exceptions."""
        assert SiaTimeoutError is sia_scraper_rust.SiaTimeoutError

    def test_parse_error_is_exported(self):
        """ParseError should be importable from sia_scraper.core.exceptions."""
        assert ParseError is sia_scraper_rust.ParseError

    def test_session_error_is_exported(self):
        """SessionError should be importable from sia_scraper.core.exceptions."""
        assert SessionError is sia_scraper_rust.SessionError

    def test_sia_scraper_exception_is_exported(self):
        """SiaScraperException should be importable from sia_scraper.core.exceptions."""
        assert SiaScraperException is sia_scraper_rust.SiaScraperException


class TestRustExceptionHierarchy:
    """Verify Rust exception inheritance structure."""

    def test_all_rust_exceptions_inherit_from_sia_scraper_exception(self):
        """All custom Rust exceptions should inherit from SiaScraperException."""
        for exc_class in [NetworkError, HttpStatusError, SiaTimeoutError, ParseError, SessionError]:
            assert issubclass(exc_class, SiaScraperException)

    def test_sia_scraper_exception_inherits_from_exception(self):
        """SiaScraperException should inherit from Exception."""
        assert issubclass(SiaScraperException, Exception)

    def test_can_catch_all_rust_exceptions_with_base(self):
        """Catching SiaScraperException should catch all derived exceptions."""
        for exc_class in [NetworkError, HttpStatusError, SiaTimeoutError, ParseError, SessionError]:
            with pytest.raises(SiaScraperException):
                raise exc_class("test error")


class TestPythonExceptionIndependence:
    """Verify Python exceptions remain independent of Rust hierarchy."""

    def test_sia_session_exception_does_not_inherit_from_rust(self):
        """SiaSessionException should NOT inherit from SiaScraperException."""
        assert not issubclass(SiaSessionException, SiaScraperException)

    def test_sia_session_exception_inherits_from_exception(self):
        """SiaSessionException should inherit from Exception."""
        assert issubclass(SiaSessionException, Exception)

    def test_python_subclasses_inherit_from_sia_session_exception(self):
        """All Python exception subclasses should inherit from SiaSessionException."""
        for exc_class in [
            SiaSessionException.SessionNotSet,
            SiaSessionException.CareerNotSet,
            SiaSessionException.TimeoutError,
            SiaSessionException.InvalidStatus,
            SiaSessionException.ConcurrentAccessError,
        ]:
            assert issubclass(exc_class, SiaSessionException)


class TestExceptionCatchability:
    """Verify exceptions can be caught at different hierarchy levels."""

    def test_rust_network_error_caught_by_sia_scraper_exception(self):
        """NetworkError should be catchable as SiaScraperException."""
        with pytest.raises(SiaScraperException):
            raise NetworkError("network failed")

    def test_rust_network_error_caught_by_exception(self):
        """NetworkError should be catchable as Exception."""
        caught = False
        try:
            raise NetworkError("network failed")
        except Exception:  # noqa: B017
            caught = True
        assert caught

    def test_python_session_not_set_caught_by_sia_session_exception(self):
        """SessionNotSet should be catchable as SiaSessionException."""
        with pytest.raises(SiaSessionException):
            raise SiaSessionException.SessionNotSet()
