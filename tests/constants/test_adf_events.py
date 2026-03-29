"""Tests for ADF event XML payload constants module."""

import pytest

from sia_scraper.constants import BTTN_EVENT_VALUE, DROPDOWN_EVENT_VALUE, SELECT_ROW_EVENT_VALUE


@pytest.mark.unit
class TestAdfEventXmlPayloads:
    """Test Oracle RichClient event XML payloads."""

    def test_dropdown_event_value(self) -> None:
        """Test dropdown event XML structure."""
        assert '<m xmlns="http://oracle.com/richClient/comm">' in DROPDOWN_EVENT_VALUE
        assert '<k v="type"><s>valueChange</s></k>' in DROPDOWN_EVENT_VALUE
        assert '<k v="autoSubmit"><b>1</b></k>' in DROPDOWN_EVENT_VALUE
        assert "suppressMessageShow" in DROPDOWN_EVENT_VALUE

    def test_button_event_value(self) -> None:
        """Test button event XML structure."""
        assert '<m xmlns="http://oracle.com/richClient/comm">' in BTTN_EVENT_VALUE
        assert '<k v="type"><s>action</s></k>' in BTTN_EVENT_VALUE

    def test_select_row_event_value(self) -> None:
        """Test row selection event XML structure."""
        assert '<m xmlns="http://oracle.com/richClient/comm">' in SELECT_ROW_EVENT_VALUE
        assert '<k v="type"><s>selection</s></k>' in SELECT_ROW_EVENT_VALUE

    def test_event_values_are_xml_formatted(self) -> None:
        """Test that all event values are valid XML fragments."""
        event_values = [DROPDOWN_EVENT_VALUE, BTTN_EVENT_VALUE, SELECT_ROW_EVENT_VALUE]
        for event in event_values:
            assert event.startswith('<m xmlns="http://oracle.com/richClient/comm">')
            assert event.endswith("</m>")
