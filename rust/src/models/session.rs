//! Typed session state models for Rust/Python boundary transport.

use std::collections::HashMap;

use serde::{Deserialize, Serialize};

use crate::http::session::SessionState;

/// One course entry from the course list table.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct CourseListEntryModel {
    pub course_code: String,
    pub course_name: String,
}

/// Typed session payload used by Python wrappers.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SessionStateModel {
    pub session_headers: HashMap<String, String>,
    pub session_cookies: HashMap<String, String>,
    pub params: HashMap<String, String>,
    #[serde(rename = "javax_faces_ViewState")]
    pub javax_faces_view_state: Option<String>,
    pub career_code: String,
    pub career_name: String,
    pub is_electives: bool,
    pub status: String,
    pub course_list: Vec<CourseListEntryModel>,
}

impl SessionStateModel {
    /// Build a typed transport model from internal session state.
    #[must_use]
    pub fn from_session_state(state: &SessionState) -> Self {
        Self {
            session_headers: state.session_headers.clone(),
            session_cookies: state.session_cookies.clone(),
            params: state.params.clone(),
            javax_faces_view_state: state.javax_faces_ViewState.clone(),
            career_code: state.career_code.clone(),
            career_name: state.career_name.clone(),
            is_electives: state.is_electives,
            status: normalize_status(&state.status),
            course_list: flatten_course_list(&state.course_list),
        }
    }
}

fn normalize_status(status: &str) -> String {
    match status {
        "CREATED" => "NO_SESSION".to_string(),
        "SESSION_SET" => "CAREER_NOT_SET".to_string(),
        "ON_CAREER_PAGE" => "ON_CAREER_PAGE".to_string(),
        "ON_COURSE_PAGE" => "ON_COURSE_PAGE".to_string(),
        other => other.to_string(),
    }
}

fn flatten_course_list(course_rows: &[HashMap<String, String>]) -> Vec<CourseListEntryModel> {
    let mut entries = Vec::new();

    for row in course_rows {
        let mut row_entries: Vec<(&String, &String)> = row.iter().collect();
        row_entries.sort_by(|a, b| a.0.cmp(b.0));

        for (code, name) in row_entries {
            if code.is_empty() {
                continue;
            }
            entries.push(CourseListEntryModel {
                course_code: code.clone(),
                course_name: name.clone(),
            });
        }
    }

    entries
}

#[cfg(test)]
mod tests {
    use std::collections::HashMap;

    use super::{CourseListEntryModel, SessionStateModel};
    use crate::http::session::SessionState;

    #[test]
    fn test_from_session_state_preserves_core_fields() {
        let state = SessionState {
            career_code: "0-2-8-3".to_string(),
            career_name: "Ingenieria de Sistemas".to_string(),
            status: "ON_CAREER_PAGE".to_string(),
            is_electives: true,
            javax_faces_ViewState: Some("vs-123".to_string()),
            ..Default::default()
        };

        let model = SessionStateModel::from_session_state(&state);

        assert_eq!(model.career_code, "0-2-8-3");
        assert_eq!(model.career_name, "Ingenieria de Sistemas");
        assert_eq!(model.status, "ON_CAREER_PAGE");
        assert!(model.is_electives);
        assert_eq!(model.javax_faces_view_state.as_deref(), Some("vs-123"));
        assert!(model.params.contains_key("Adf-Window-Id"));
        assert!(model.params.contains_key("Adf-Page-Id"));
    }

    #[test]
    fn test_from_session_state_normalizes_internal_status_values() {
        let state = SessionState {
            status: "SESSION_SET".to_string(),
            ..Default::default()
        };

        let model = SessionStateModel::from_session_state(&state);

        assert_eq!(model.status, "CAREER_NOT_SET");
    }

    #[test]
    fn test_from_session_state_flattens_course_maps_to_typed_entries() {
        let state = SessionState {
            course_list: vec![
                HashMap::from([("1000001".to_string(), "Calculo".to_string())]),
                HashMap::from([("2016489".to_string(), "Estructuras de Datos".to_string())]),
            ],
            ..Default::default()
        };

        let model = SessionStateModel::from_session_state(&state);

        assert_eq!(
            model.course_list,
            vec![
                CourseListEntryModel {
                    course_code: "1000001".to_string(),
                    course_name: "Calculo".to_string(),
                },
                CourseListEntryModel {
                    course_code: "2016489".to_string(),
                    course_name: "Estructuras de Datos".to_string(),
                }
            ]
        );
    }
}
