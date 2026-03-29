"""Tests for debug logging utilities."""

import importlib
import logging
from collections.abc import Generator

import pytest

import sia_scraper.utils.debug as debug_module


@pytest.mark.unit
class TestDebugLogWhenDisabled:
    """Test debug_log behavior when debug mode is disabled."""

    def test_debug_log_returns_early_when_disabled(self, mocker, monkeypatch) -> None:
        monkeypatch.setenv("SIA_DEBUG", "0")
        importlib.reload(debug_module)
        logger_debug = mocker.patch.object(debug_module._LOGGER, "debug")

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
        logger_debug = mocker.patch.object(debug_module._LOGGER, "debug")

        debug_module.debug_log("SYNC_VIEW_STATE")

        logger_debug.assert_called_once_with("[ADF-DEBUG] %s", "SYNC_VIEW_STATE")

    def test_logs_message_and_returns_for_empty_data(self, mocker) -> None:
        logger_debug = mocker.patch.object(debug_module._LOGGER, "debug")

        debug_module.debug_log("EMPTY_DATA", data="")

        logger_debug.assert_called_once_with("[ADF-DEBUG] %s", "EMPTY_DATA")

    def test_logs_dict_data_values(self, mocker) -> None:
        logger_debug = mocker.patch.object(debug_module._LOGGER, "debug")

        debug_module.debug_log("DICT", data={"key1": "value1", "key2": 123})

        assert logger_debug.call_count == 3
        logger_debug.assert_any_call("[ADF-DEBUG] %s", "DICT")
        logger_debug.assert_any_call("  %s: %s", "key1", "value1")
        logger_debug.assert_any_call("  %s: %s", "key2", "123")

    def test_truncates_long_dict_values(self, mocker) -> None:
        logger_debug = mocker.patch.object(debug_module._LOGGER, "debug")
        long_value = "x" * 250

        debug_module.debug_log("DICT_LONG", data={"payload": long_value})

        expected = ("x" * 200) + "..."
        logger_debug.assert_any_call("  %s: %s", "payload", expected)

    def test_logs_string_data(self, mocker) -> None:
        logger_debug = mocker.patch.object(debug_module._LOGGER, "debug")

        debug_module.debug_log("STRING", data="hello")

        assert logger_debug.call_count == 2
        logger_debug.assert_any_call("[ADF-DEBUG] %s", "STRING")
        logger_debug.assert_any_call("  Data: %s", "hello")

    def test_truncates_long_string_data(self, mocker) -> None:
        logger_debug = mocker.patch.object(debug_module._LOGGER, "debug")
        long_data = "y" * 250

        debug_module.debug_log("STRING_LONG", data=long_data)

        expected = ("y" * 200) + "..."
        logger_debug.assert_any_call("  Data: %s", expected)

    def test_module_logger_is_named_consistently(self) -> None:
        assert debug_module._LOGGER.name == "sia_scraper.adf"
        assert isinstance(debug_module._LOGGER, logging.Logger)
