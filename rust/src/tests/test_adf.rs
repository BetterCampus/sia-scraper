//! Unit tests for ADF parsing functions.

use crate::extract_view_state;

#[test]
fn test_extract_view_state_valid_input() {
    let html = r#"<input name="javax.faces.ViewState" value="test123" />"#;
    let result = extract_view_state(html);
    assert!(result.is_ok());
    assert_eq!(result.unwrap(), "test123");
}

#[test]
fn test_extract_view_state_with_id_attribute() {
    let html = r#"<input id="javax_faces.ViewState" value="xyz789" />"#;
    let result = extract_view_state(html);
    assert!(result.is_ok());
    assert_eq!(result.unwrap(), "xyz789");
}

#[test]
fn test_extract_view_state_not_found() {
    let html = "<div>No ViewState here</div>";
    let result = extract_view_state(html);
    assert!(result.is_err());
}

#[test]
fn test_extract_view_state_empty_string() {
    let html = "";
    let result = extract_view_state(html);
    assert!(result.is_err());
}

#[test]
fn test_extract_view_state_malformed_html() {
    let html = "<input name=\"ViewState\" value>";
    let result = extract_view_state(html);
    assert!(result.is_ok());
    assert_eq!(result.unwrap(), "");
}

#[test]
fn test_extract_view_state_multiple_inputs() {
    let html = r#"
        <input name="other" value="first" />
        <input name="javax.faces.ViewState" value="second" />
    "#;
    let result = extract_view_state(html);
    assert!(result.is_ok());
    assert_eq!(result.unwrap(), "second");
}
