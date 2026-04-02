//! Typed session state models for Rust/Python boundary transport.

use std::collections::HashMap;

use pyo3::exceptions::PyKeyError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use serde::{Deserialize, Serialize};

use crate::http::session::SessionState;

fn required_item<'py>(dict: &'py PyDict, key: &str) -> PyResult<&'py PyAny> {
    dict.get_item(key)?
        .ok_or_else(|| PyKeyError::new_err(format!("Missing key: {key}")))
}

/// One course entry from the course list table.
#[pyclass(module = "sia_scraper_rust")]
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct CourseListEntryModel {
    #[pyo3(get)]
    pub course_code: String,
    #[pyo3(get)]
    pub course_name: String,
}

#[pymethods]
impl CourseListEntryModel {
    #[new]
    fn new(course_code: String, course_name: String) -> Self {
        Self {
            course_code,
            course_name,
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "CourseListEntryModel(course_code='{}', course_name='{}')",
            self.course_code, self.course_name
        )
    }

    fn __str__(&self) -> String {
        format!("{}: {}", self.course_code, self.course_name)
    }

    fn __getnewargs__(&self) -> (String, String) {
        (String::new(), String::new())
    }

    fn __getstate__(&self, py: Python<'_>) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        dict.set_item("course_code", &self.course_code)?;
        dict.set_item("course_name", &self.course_name)?;
        Ok(dict.into())
    }

    fn __setstate__(&mut self, state: &PyAny) -> PyResult<()> {
        let dict = state.downcast::<PyDict>()?;
        self.course_code = required_item(dict, "course_code")?.extract()?;
        self.course_name = required_item(dict, "course_name")?.extract()?;
        Ok(())
    }
}

/// Typed session payload used by Python wrappers.
#[pyclass(module = "sia_scraper_rust")]
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SessionStateModel {
    #[pyo3(get)]
    pub session_headers: HashMap<String, String>,
    #[pyo3(get)]
    pub session_cookies: HashMap<String, String>,
    #[pyo3(get)]
    pub params: HashMap<String, String>,
    #[serde(rename = "javax_faces_ViewState")]
    #[pyo3(get)]
    pub javax_faces_view_state: Option<String>,
    #[pyo3(get)]
    pub career_code: String,
    #[pyo3(get)]
    pub career_name: String,
    #[pyo3(get)]
    pub is_electives: bool,
    #[pyo3(get)]
    pub status: String,
    #[pyo3(get)]
    pub course_list: Vec<CourseListEntryModel>,
}

#[pymethods]
impl SessionStateModel {
    #[new]
    #[pyo3(signature = (
        session_headers,
        session_cookies,
        params,
        career_code,
        career_name,
        is_electives,
        status,
        course_list,
        javax_faces_view_state=None
    ))]
    #[allow(clippy::too_many_arguments)]
    fn new(
        session_headers: HashMap<String, String>,
        session_cookies: HashMap<String, String>,
        params: HashMap<String, String>,
        career_code: String,
        career_name: String,
        is_electives: bool,
        status: String,
        course_list: Vec<CourseListEntryModel>,
        javax_faces_view_state: Option<String>,
    ) -> Self {
        Self {
            session_headers,
            session_cookies,
            params,
            javax_faces_view_state,
            career_code,
            career_name,
            is_electives,
            status,
            course_list,
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "SessionStateModel(career_code='{}', status='{}', courses_count={})",
            self.career_code,
            self.status,
            self.course_list.len()
        )
    }

    fn __str__(&self) -> String {
        format!(
            "Session: {} - {} ({} courses)",
            self.career_name,
            self.status,
            self.course_list.len()
        )
    }

    fn __getnewargs__(
        &self,
    ) -> (
        HashMap<String, String>,
        HashMap<String, String>,
        HashMap<String, String>,
        String,
        String,
        bool,
        String,
        Vec<CourseListEntryModel>,
        Option<String>,
    ) {
        (
            HashMap::new(),
            HashMap::new(),
            HashMap::new(),
            String::new(),
            String::new(),
            false,
            String::new(),
            Vec::new(),
            None,
        )
    }

    fn __getstate__(&self, py: Python<'_>) -> PyResult<PyObject> {
        let dict = PyDict::new(py);

        let headers = PyDict::new(py);
        for (k, v) in &self.session_headers {
            headers.set_item(k, v)?;
        }
        dict.set_item("session_headers", headers)?;

        let cookies = PyDict::new(py);
        for (k, v) in &self.session_cookies {
            cookies.set_item(k, v)?;
        }
        dict.set_item("session_cookies", cookies)?;

        let params = PyDict::new(py);
        for (k, v) in &self.params {
            params.set_item(k, v)?;
        }
        dict.set_item("params", params)?;

        dict.set_item("javax_faces_view_state", &self.javax_faces_view_state)?;
        dict.set_item("career_code", &self.career_code)?;
        dict.set_item("career_name", &self.career_name)?;
        dict.set_item("is_electives", &self.is_electives)?;
        dict.set_item("status", &self.status)?;

        let courses = PyList::empty(py);
        for course in &self.course_list {
            courses.append(course.__getstate__(py)?)?;
        }
        dict.set_item("course_list", courses)?;

        Ok(dict.into())
    }

    fn __setstate__(&mut self, state: &PyAny) -> PyResult<()> {
        let dict = state.downcast::<PyDict>()?;

        let headers_dict = required_item(dict, "session_headers")?.downcast::<PyDict>()?;
        let mut session_headers = HashMap::new();
        for (k, v) in headers_dict.iter() {
            let key: String = k.extract()?;
            let value: String = v.extract()?;
            session_headers.insert(key, value);
        }
        self.session_headers = session_headers;

        let cookies_dict = required_item(dict, "session_cookies")?.downcast::<PyDict>()?;
        let mut session_cookies = HashMap::new();
        for (k, v) in cookies_dict.iter() {
            let key: String = k.extract()?;
            let value: String = v.extract()?;
            session_cookies.insert(key, value);
        }
        self.session_cookies = session_cookies;

        let params_dict = required_item(dict, "params")?.downcast::<PyDict>()?;
        let mut params = HashMap::new();
        for (k, v) in params_dict.iter() {
            let key: String = k.extract()?;
            let value: String = v.extract()?;
            params.insert(key, value);
        }
        self.params = params;

        self.javax_faces_view_state = required_item(dict, "javax_faces_view_state")?.extract()?;
        self.career_code = required_item(dict, "career_code")?.extract()?;
        self.career_name = required_item(dict, "career_name")?.extract()?;
        self.is_electives = required_item(dict, "is_electives")?.extract()?;
        self.status = required_item(dict, "status")?.extract()?;

        let list = required_item(dict, "course_list")?.downcast::<PyList>()?;
        let mut course_list = Vec::with_capacity(list.len());
        for item in list.iter() {
            let mut course = CourseListEntryModel::new(String::new(), String::new());
            course.__setstate__(item)?;
            course_list.push(course);
        }
        self.course_list = course_list;

        Ok(())
    }
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
