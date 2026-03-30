"""Unit tests for OracleAdfRequestBuilder request payload generation."""

import pytest

from sia_scraper.constants import (
    BTTN_EVENT_VALUE,
    CAMPUS_ELECTIVES_DD,
    CAMPUS_ELECTIVES_DD_ID,
    COURSE_PAGE_LINK,
    DROPDOWN_EVENT_VALUE,
    ELECTIVES_CAMPUS_INCREMENT,
    FACULTY_CAREER_DD,
    FACULTY_CAREER_DD_ID,
    FACULTY_CAREER_DEFAULT_INDEX,
    ORACLE_ADF_REGION_ID,
    ORACLE_ADF_RENDER_TARGET,
    SELECT_ROW,
    SELECT_ROW_EVENT_VALUE,
)
from sia_scraper.core.oracle_adf_request import OracleAdfRequestBuilder


class _FakeSession:
    def __init__(self) -> None:
        self._tipology_index = "2"
        self._window_id = "window-123"
        self._page_id = "page-456"
        self._view_state = "viewstate-789"
        self.career_indices = ["0", "5"]
        self.course_list = [{"1000001": "CALCULO"}, {"1000002": "ALGEBRA"}]


@pytest.mark.unit
class TestOracleAdfRequestBuilder:
    """Tests for request body initialization and event composition."""

    def test_init_request_dict_contains_base_fields(self) -> None:
        builder = OracleAdfRequestBuilder(session=_FakeSession())

        request_dict = builder.init_request_dict()

        assert request_dict["Adf-Window-Id"] == "window-123"
        assert request_dict["Adf-Page-Id"] == "page-456"
        assert request_dict["javax.faces.ViewState"] == "viewstate-789"

    def test_build_request_body_raises_for_unknown_action(self) -> None:
        builder = OracleAdfRequestBuilder(session=_FakeSession())
        builder.init_request_dict()

        with pytest.raises(KeyError, match="Unknown data_name in DATA_MAP"):
            builder.build_request_body("UNKNOWN_ACTION")

    def test_build_request_body_sets_faculty_career_default_index(self) -> None:
        builder = OracleAdfRequestBuilder(session=_FakeSession())
        builder.init_request_dict()

        request_body = builder.build_request_body(FACULTY_CAREER_DD)

        assert request_body[FACULTY_CAREER_DD_ID] == FACULTY_CAREER_DEFAULT_INDEX

    def test_build_request_body_sets_electives_campus_increment(self) -> None:
        builder = OracleAdfRequestBuilder(session=_FakeSession())
        builder.init_request_dict()

        request_body = builder.build_request_body(CAMPUS_ELECTIVES_DD)

        assert request_body[CAMPUS_ELECTIVES_DD_ID] == str(5 + ELECTIVES_CAMPUS_INCREMENT)

    def test_build_request_body_select_row_adds_deltas(self) -> None:
        builder = OracleAdfRequestBuilder(session=_FakeSession())
        builder.init_request_dict()

        request_body = builder.build_request_body(SELECT_ROW, idx=1)

        deltas = request_body.get("oracle.adf.view.rich.DELTAS")
        assert deltas is not None
        assert "viewportSize=3" in deltas
        assert "rows=2" in deltas
        assert "selectedRowKeys=1" in deltas

    def test_build_request_body_course_page_link_sets_render_target(self) -> None:
        builder = OracleAdfRequestBuilder(session=_FakeSession())
        builder.init_request_dict()

        request_body = builder.build_request_body(COURSE_PAGE_LINK)

        assert request_body["oracle.adf.view.rich.RENDER"] == ORACLE_ADF_RENDER_TARGET

    def test_get_event_dict_dropdown_event_uses_component_id_as_process(self) -> None:
        builder = OracleAdfRequestBuilder(session=_FakeSession())

        event_dict = builder._get_event_dict("component-id", DROPDOWN_EVENT_VALUE)

        assert event_dict["event"] == "component-id"
        assert event_dict["event.component-id"] == DROPDOWN_EVENT_VALUE
        assert event_dict["oracle.adf.view.rich.PROCESS"] == "component-id"

    def test_get_event_dict_select_row_event_with_index_formats_event_id(self) -> None:
        builder = OracleAdfRequestBuilder(session=_FakeSession())

        event_dict = builder._get_event_dict("table-id", SELECT_ROW_EVENT_VALUE, idx=4)

        assert event_dict["event"] == "table-id:4:cl2"
        assert event_dict["event.table-id:4:cl2"] == SELECT_ROW_EVENT_VALUE
        assert event_dict["oracle.adf.view.rich.PROCESS"] == "table-id:4:cl2"

    def test_get_event_dict_button_event_uses_region_prefixed_process(self) -> None:
        builder = OracleAdfRequestBuilder(session=_FakeSession())

        event_dict = builder._get_event_dict("button-id", BTTN_EVENT_VALUE)

        assert event_dict["event"] == "button-id"
        assert event_dict["event.button-id"] == BTTN_EVENT_VALUE
        assert event_dict["oracle.adf.view.rich.PROCESS"] == f"{ORACLE_ADF_REGION_ID},button-id"
