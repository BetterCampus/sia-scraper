"""Tests for debug logging utilities using loguru."""

import importlib
from collections.abc import Generator

import pytest
from loguru import logger

import sia_scraper.utils.debug as debug_module


@pytest.mark.unit
class TestDebugLogWhenDisabled:
    """Test debug_log behavior when debug mode is disabled."""

    def test_debug_log_returns_early_when_disabled(self, mocker, monkeypatch) -> None:
        monkeypatch.setenv("SIA_DEBUG", "0")
        importlib.reload(debug_module)
        logger_debug = mocker.patch.object(debug_module.logger, "debug")

        debug_module.debug_log("message", data={"k": "v"})

        logger_debug.assert_not_called()


@pytest.mark.unit
class TestDebugLogWhenEnabled:
    """Test debug_log behavior when debug mode is enabled."""

    @pytest.fixture(autouse=True)
    def _enable_debug(self, monkeypatch) -> Generator[None, None, None]:
        monkeypatch.setenv("SIA_DEBUG", "1")
        importlib.reload(debug_module)
        yield
        monkeypatch.setenv("SIA_DEBUG", "0")
        importlib.reload(debug_module)

    def test_logs_message_only(self, mocker) -> None:
        logger_debug = mocker.patch.object(debug_module.logger, "debug")

        debug_module.debug_log("SYNC_VIEW_STATE")

        logger_debug.assert_called_once_with("SYNC_VIEW_STATE")

    def test_logs_message_and_returns_for_empty_data(self, mocker) -> None:
        logger_debug = mocker.patch.object(debug_module.logger, "debug")

        debug_module.debug_log("EMPTY_DATA", data="")

        logger_debug.assert_called_once_with("EMPTY_DATA", extra={"data": ""})

    def test_logs_dict_data_values(self, mocker) -> None:
        logger_debug = mocker.patch.object(debug_module.logger, "debug")

        debug_module.debug_log("DICT", data={"key1": "value1", "key2": 123})

        logger_debug.assert_called_once_with("DICT", key1="value1", key2=123)

    def test_logs_string_data(self, mocker) -> None:
        logger_debug = mocker.patch.object(debug_module.logger, "debug")

        debug_module.debug_log("STRING", data="hello")

        logger_debug.assert_called_once_with("STRING", extra={"data": "hello"})

    def test_debug_module_has_info_log(self, monkeypatch) -> None:
        monkeypatch.setenv("SIA_DEBUG", "1")
        importlib.reload(debug_module)

        assert hasattr(debug_module, "info_log")
        assert hasattr(debug_module, "error_log")

    def test_module_logger_configured(self) -> None:
        assert hasattr(debug_module, "logger")
        assert debug_module.logger is logger
