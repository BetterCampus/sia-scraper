//! SIA Session state management.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[allow(non_snake_case)]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SessionState {
    pub session_headers: HashMap<String, String>,
    pub session_cookies: HashMap<String, String>,
    pub params: HashMap<String, String>,
    pub javax_faces_ViewState: Option<String>,
    pub career_code: String,
    pub career_name: String,
    pub is_electives: bool,
    pub status: String,
    pub course_list: Vec<HashMap<String, String>>,
}

impl Default for SessionState {
    fn default() -> Self {
        Self {
            session_headers: HashMap::new(),
            session_cookies: HashMap::new(),
            params: HashMap::from([
                ("Adf-Page-Id".to_string(), "1".to_string()),
                ("Adf-Window-Id".to_string(), String::new()),
            ]),
            javax_faces_ViewState: None,
            career_code: String::new(),
            career_name: String::new(),
            is_electives: false,
            status: "CREATED".to_string(),
            course_list: Vec::new(),
        }
    }
}

impl SessionState {
    #[cfg(test)]
    pub fn new() -> Self {
        Self::default()
    }

    #[cfg(test)]
    pub fn with_view_state(mut self, view_state: String) -> Self {
        self.javax_faces_ViewState = Some(view_state);
        self
    }

    #[cfg(test)]
    pub fn with_career(mut self, code: String, name: String) -> Self {
        self.career_code = code;
        self.career_name = name;
        self
    }

    pub fn set_status(&mut self, status: &str) {
        self.status = status.to_string();
    }

    #[cfg(test)]
    pub fn is_view_state_set(&self) -> bool {
        self.javax_faces_ViewState.is_some()
    }

    #[cfg(test)]
    pub fn view_state(&self) -> Option<&String> {
        self.javax_faces_ViewState.as_ref()
    }

    pub fn update_view_state(&mut self, view_state: String) {
        self.javax_faces_ViewState = Some(view_state);
    }

    pub fn update_params(&mut self, key: &str, value: String) {
        self.params.insert(key.to_string(), value);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_state() {
        let state = SessionState::default();
        assert!(state.javax_faces_ViewState.is_none());
        assert!(state.career_code.is_empty());
        assert_eq!(state.status, "CREATED");
    }

    #[test]
    fn test_with_view_state() {
        let state = SessionState::default().with_view_state("test_viewstate".to_string());
        assert_eq!(
            state.javax_faces_ViewState,
            Some("test_viewstate".to_string())
        );
    }

    #[test]
    fn test_with_career() {
        let state =
            SessionState::default().with_career("0-2-8-3".to_string(), "Ingenieria".to_string());
        assert_eq!(state.career_code, "0-2-8-3");
        assert_eq!(state.career_name, "Ingenieria");
    }

    #[test]
    fn test_update_view_state() {
        let mut state = SessionState::default();
        state.update_view_state("new_viewstate".to_string());
        assert_eq!(
            state.javax_faces_ViewState,
            Some("new_viewstate".to_string())
        );
    }

    #[test]
    fn test_default_state_has_empty_course_list() {
        let state = SessionState::default();
        assert!(state.course_list.is_empty());
    }

    #[test]
    fn test_course_list_is_serializable() {
        let mut state = SessionState::default();
        let mut course = HashMap::new();
        course.insert("2019454".to_string(), "CALCULO DIFERENCIAL".to_string());
        state.course_list.push(course);

        let serialized = serde_json::to_string(&state).unwrap();
        let deserialized: SessionState = serde_json::from_str(&serialized).unwrap();

        assert_eq!(deserialized.course_list.len(), 1);
        assert_eq!(
            deserialized.course_list[0].get("2019454"),
            Some(&"CALCULO DIFERENCIAL".to_string())
        );
    }
}
