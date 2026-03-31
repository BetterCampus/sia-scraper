//! Unit tests for Rust-backed Oracle ADF request building helpers.

use crate::parsers::adf_request::{get_event_dict, OracleAdfRequestBuilderState};

const DROPDOWN_EVENT_VALUE: &str = r#"<m xmlns="http://oracle.com/richClient/comm"><k v="autoSubmit"><b>1</b></k><k v="suppressMessageShow"><s>true</s></k><k v="type"><s>valueChange</s></k></m>"#;
const BTTN_EVENT_VALUE: &str =
    r#"<m xmlns="http://oracle.com/richClient/comm"><k v="type"><s>action</s></k></m>"#;
const SELECT_ROW_EVENT_VALUE: &str =
    r#"<m xmlns="http://oracle.com/richClient/comm"><k v="type"><s>selection</s></k></m>"#;

#[test]
fn test_init_request_dict_contains_base_fields() {
    let mut builder = OracleAdfRequestBuilderState::new();
    let request_dict = builder.init_request_dict(
        "2",
        Some("window-123"),
        Some("page-456"),
        Some("viewstate-789"),
    );

    assert_eq!(
        request_dict.get("Adf-Window-Id"),
        Some(&"window-123".to_string())
    );
    assert_eq!(
        request_dict.get("Adf-Page-Id"),
        Some(&"page-456".to_string())
    );
    assert_eq!(
        request_dict.get("javax.faces.ViewState"),
        Some(&"viewstate-789".to_string())
    );
}

#[test]
fn test_build_request_body_raises_for_unknown_action() {
    let mut builder = OracleAdfRequestBuilderState::new();
    let _ = builder.init_request_dict("2", Some("w"), Some("p"), Some("v"));

    let result = builder.build_request_body("UNKNOWN_ACTION", -1, &["0".to_string()], 2);
    assert!(result.is_err());
}

#[test]
fn test_build_request_body_sets_faculty_career_default_index() {
    let mut builder = OracleAdfRequestBuilderState::new();
    let _ = builder.init_request_dict("2", Some("w"), Some("p"), Some("v"));

    let request_body = builder
        .build_request_body(
            "FACULTY_CAREER_DD",
            -1,
            &["0".to_string(), "5".to_string()],
            2,
        )
        .expect("faculty career body should build");

    assert_eq!(request_body.get("pt1:r1:0:soc5"), Some(&"0".to_string()));
}

#[test]
fn test_build_request_body_sets_electives_campus_increment() {
    let mut builder = OracleAdfRequestBuilderState::new();
    let _ = builder.init_request_dict("2", Some("w"), Some("p"), Some("v"));

    let request_body = builder
        .build_request_body(
            "CAMPUS_ELECTIVES_DD",
            -1,
            &["0".to_string(), "5".to_string()],
            2,
        )
        .expect("electives campus body should build");

    assert_eq!(request_body.get("pt1:r1:0:soc6"), Some(&"45".to_string()));
}

#[test]
fn test_build_request_body_select_row_adds_deltas() {
    let mut builder = OracleAdfRequestBuilderState::new();
    let _ = builder.init_request_dict("2", Some("w"), Some("p"), Some("v"));

    let request_body = builder
        .build_request_body("SELECT_ROW", 1, &["0".to_string(), "5".to_string()], 2)
        .expect("select row body should build");

    let deltas = request_body
        .get("oracle.adf.view.rich.DELTAS")
        .expect("deltas should exist");
    assert!(deltas.contains("viewportSize=3"));
    assert!(deltas.contains("rows=2"));
    assert!(deltas.contains("selectedRowKeys=1"));
}

#[test]
fn test_build_request_body_course_page_link_sets_render_target() {
    let mut builder = OracleAdfRequestBuilderState::new();
    let _ = builder.init_request_dict("2", Some("w"), Some("p"), Some("v"));

    let request_body = builder
        .build_request_body(
            "COURSE_PAGE_LINK",
            -1,
            &["0".to_string(), "5".to_string()],
            2,
        )
        .expect("course page link body should build");

    assert_eq!(
        request_body.get("oracle.adf.view.rich.RENDER"),
        Some(&"pt1:r1".to_string())
    );
}

#[test]
fn test_get_event_dict_dropdown_event_uses_component_id_as_process() {
    let event_dict = get_event_dict("component-id", DROPDOWN_EVENT_VALUE, -1);

    assert_eq!(event_dict.get("event"), Some(&"component-id".to_string()));
    assert_eq!(
        event_dict.get("event.component-id"),
        Some(&DROPDOWN_EVENT_VALUE.to_string())
    );
    assert_eq!(
        event_dict.get("oracle.adf.view.rich.PROCESS"),
        Some(&"component-id".to_string())
    );
}

#[test]
fn test_get_event_dict_select_row_event_with_index_formats_event_id() {
    let event_dict = get_event_dict("table-id", SELECT_ROW_EVENT_VALUE, 4);

    assert_eq!(event_dict.get("event"), Some(&"table-id:4:cl2".to_string()));
    assert_eq!(
        event_dict.get("event.table-id:4:cl2"),
        Some(&SELECT_ROW_EVENT_VALUE.to_string())
    );
    assert_eq!(
        event_dict.get("oracle.adf.view.rich.PROCESS"),
        Some(&"table-id:4:cl2".to_string())
    );
}

#[test]
fn test_get_event_dict_button_event_uses_region_prefixed_process() {
    let event_dict = get_event_dict("button-id", BTTN_EVENT_VALUE, -1);

    assert_eq!(event_dict.get("event"), Some(&"button-id".to_string()));
    assert_eq!(
        event_dict.get("event.button-id"),
        Some(&BTTN_EVENT_VALUE.to_string())
    );
    assert_eq!(
        event_dict.get("oracle.adf.view.rich.PROCESS"),
        Some(&"pt1:r1,button-id".to_string())
    );
}

#[test]
fn test_build_request_body_supports_all_dropdown_and_button_actions() {
    let actions = [
        "STUDY_LEVEL_DD",
        "CAMPUS_DD",
        "FACULTY_DD",
        "CAREER_DD",
        "TIPOLOGY_DD",
        "SHOW_COURSES_BTTN",
        "BACK_BTTN",
    ];

    for action in actions {
        let mut builder = OracleAdfRequestBuilderState::new();
        let _ = builder.init_request_dict("2", Some("w"), Some("p"), Some("v"));

        let body = builder
            .build_request_body(action, -1, &["0".to_string(), "5".to_string()], 10)
            .expect("action should build request body");
        assert!(body.contains_key("event"));
        assert!(body.contains_key("oracle.adf.view.rich.PROCESS"));
    }
}

#[test]
fn test_build_request_body_electives_requires_second_career_index() {
    let mut builder = OracleAdfRequestBuilderState::new();
    let _ = builder.init_request_dict("2", Some("w"), Some("p"), Some("v"));

    let result = builder.build_request_body("CAMPUS_ELECTIVES_DD", -1, &["0".to_string()], 2);
    assert!(result.is_err());
}

#[test]
fn test_build_request_body_electives_requires_numeric_second_index() {
    let mut builder = OracleAdfRequestBuilderState::new();
    let _ = builder.init_request_dict("2", Some("w"), Some("p"), Some("v"));

    let result = builder.build_request_body(
        "CAMPUS_ELECTIVES_DD",
        -1,
        &["0".to_string(), "x".to_string()],
        2,
    );
    assert!(result.is_err());
}
