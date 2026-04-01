//! Property-based tests for Rust parser panic safety.

use proptest::prelude::*;

use crate::parsers::adf::extract_view_state;
use crate::parsers::course_parser::{get_plain_text, parse_course_xml, parse_prereqs_xml};
use crate::parsers::table_parser::get_course_list;
use crate::{parse_course_info, parse_prereqs};

fn random_input() -> impl Strategy<Value = String> {
    proptest::collection::vec(any::<char>(), 0..4000).prop_map(|chars| chars.into_iter().collect())
}

proptest! {
    #[test]
    fn prop_extract_view_state_never_panics(input in random_input()) {
        let _ = extract_view_state(&input);
    }

    #[test]
    fn prop_get_course_list_never_panics(input in random_input()) {
        let _ = get_course_list(&input);
    }

    #[test]
    fn prop_get_plain_text_never_panics(input in random_input()) {
        let _ = get_plain_text(&input);
    }

    #[test]
    fn prop_parse_course_info_never_panics(input in random_input()) {
        pyo3::Python::with_gil(|_| {
            let _ = parse_course_info(&input);
        });
    }

    #[test]
    fn prop_parse_prereqs_never_panics(input in random_input()) {
        pyo3::Python::with_gil(|_| {
            let _ = parse_prereqs(&input);
        });
    }

    #[test]
    fn prop_parse_course_xml_never_panics(input in random_input()) {
        pyo3::Python::with_gil(|py| {
            let _ = parse_course_xml(&input, py);
        });
    }

    #[test]
    fn prop_parse_prereqs_xml_never_panics(input in random_input()) {
        pyo3::Python::with_gil(|py| {
            let _ = parse_prereqs_xml(&input, py);
        });
    }
}
