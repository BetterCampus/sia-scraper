//! Typed session state models for Rust/Python boundary transport.

#![allow(non_local_definitions)]

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

type SessionStateModelPickleState = (
    HashMap<String, String>,
    HashMap<String, String>,
    HashMap<String, String>,
    String,
    String,
    bool,
    String,
    Vec<CourseListEntryModel>,
    Option<String>,
);

/// One course entry from the course list table.
#[pyclass(module = "sia_scraper_rust")]
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct CourseListEntryModel {
    #[pyo3(get)]
    pub code: String,
    #[pyo3(get)]
    pub name: String,
}

#[pymethods]
impl CourseListEntryModel {
    #[new]
    fn new(code: String, name: String) -> Self {
        Self { code, name }
    }

    fn __repr__(&self) -> String {
        format!(
            "CourseListEntryModel(code='{}', name='{}')",
            self.code, self.name
        )
    }

    fn __str__(&self) -> String {
        format!("{}: {}", self.code, self.name)
    }

    fn __getnewargs__(&self) -> (String, String) {
        (String::new(), String::new())
    }

    fn __getstate__(&self, py: Python<'_>) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        dict.set_item("code", self.code.clone())?;
        dict.set_item("name", self.name.clone())?;
        Ok(dict.into())
    }

    fn __setstate__(&mut self, state: &PyAny) -> PyResult<()> {
        let dict = state.downcast::<PyDict>()?;
        if let Some(item) = dict.get_item("code")? {
            self.code = item.extract()?;
        } else if let Some(legacy) = dict.get_item("course_code")? {
            self.code = legacy.extract()?;
        } else {
            return Err(PyKeyError::new_err("Missing key: 'code' or 'course_code'"));
        }
        if let Some(item) = dict.get_item("name")? {
            self.name = item.extract()?;
        } else if let Some(legacy) = dict.get_item("course_name")? {
            self.name = legacy.extract()?;
        } else {
            return Err(PyKeyError::new_err("Missing key: 'name' or 'course_name'"));
        }
        Ok(())
    }

    /// Convert to Python dictionary.
    ///
    /// # Arguments
    /// * `py` - Python GIL token
    ///
    /// # Returns
    /// `PyObject` containing `{"code": String, "name": String}`
    ///
    /// # Errors
    /// Returns `PyErr` if dictionary item setting fails
    ///
    /// # Examples
    /// ```rust
    /// use pyo3::Python;
    /// use crate::models::session::CourseListEntryModel;
    ///
    /// Python::with_gil(|py| {
    ///     let entry = CourseListEntryModel {
    ///         code: "1000001".to_string(),
    ///         name: "Calculo".to_string(),
    ///     };
    ///     let dict = entry.to_dict(py).unwrap();
    /// });
    /// ```
    fn to_dict(&self, py: Python<'_>) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        dict.set_item("code", &self.code)?;
        dict.set_item("name", &self.name)?;
        Ok(dict.into())
    }
}

fn parse_course_dict(dict: &PyDict) -> PyResult<CourseListEntryModel> {
    let code: String = if let Some(val) = dict.get_item("code")? {
        val.extract()?
    } else if let Some(legacy) = dict.get_item("course_code")? {
        legacy.extract()?
    } else {
        return Err(PyKeyError::new_err("Missing key: 'code' or 'course_code'"));
    };
    let name: String = if let Some(val) = dict.get_item("name")? {
        val.extract()?
    } else if let Some(legacy) = dict.get_item("course_name")? {
        legacy.extract()?
    } else {
        return Err(PyKeyError::new_err("Missing key: 'name' or 'course_name'"));
    };
    Ok(CourseListEntryModel { code, name })
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

impl Default for SessionStateModel {
    fn default() -> Self {
        Self {
            session_headers: HashMap::new(),
            session_cookies: HashMap::new(),
            params: HashMap::from([
                ("Adf-Page-Id".to_string(), "1".to_string()),
                ("Adf-Window-Id".to_string(), String::new()),
            ]),
            javax_faces_view_state: None,
            career_code: String::new(),
            career_name: String::new(),
            is_electives: false,
            status: "NO_SESSION".to_string(),
            course_list: Vec::new(),
        }
    }
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

    fn __getnewargs__(&self) -> SessionStateModelPickleState {
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

        dict.set_item(
            "javax_faces_view_state",
            self.javax_faces_view_state.clone(),
        )?;
        dict.set_item("career_code", self.career_code.clone())?;
        dict.set_item("career_name", self.career_name.clone())?;
        dict.set_item("is_electives", self.is_electives)?;
        dict.set_item("status", self.status.clone())?;

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
    ///
    /// This method performs normalization of status values for Python consumption:
    /// - "CREATED" → "NO_SESSION"
    /// - "SESSION_SET" → "CAREER_NOT_SET"
    ///
    /// # Arguments
    /// * `state` - Reference to the internal `SessionState` struct
    ///
    /// # Returns
    /// A new `SessionStateModel` with normalized status and cloned fields
    ///
    /// # Examples
    /// ```rust
    /// use crate::http::session::SessionState;
    /// use crate::models::session::SessionStateModel;
    ///
    /// let state = SessionState::default();
    /// let model = SessionStateModel::from_session_state(&state);
    /// assert_eq!(model.status, "NO_SESSION");
    /// ```
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
            course_list: state.course_list.clone(),
        }
    }

    /// Convert to Python dictionary for transport/persistence.
    ///
    /// Serializes all session state including headers, cookies, parameters,
    /// and course list entries using the `code`/`name` contract.
    ///
    /// # Arguments
    /// * `py` - Python GIL token
    ///
    /// # Returns
    /// `PyObject` containing a dictionary representation of the session state
    ///
    /// # Errors
    /// Returns `PyErr` if dictionary item setting fails
    ///
    /// # Examples
    /// ```rust
    /// use pyo3::Python;
    /// use crate::models::session::SessionStateModel;
    ///
    /// Python::with_gil(|py| {
    ///     let model = SessionStateModel::default();
    ///     let dict = model.to_dict(py).unwrap();
    /// });
    /// ```
    pub fn to_dict(&self, py: Python<'_>) -> PyResult<PyObject> {
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

        dict.set_item(
            "javax_faces_view_state",
            self.javax_faces_view_state.clone(),
        )?;
        dict.set_item("career_code", self.career_code.clone())?;
        dict.set_item("career_name", self.career_name.clone())?;
        dict.set_item("is_electives", self.is_electives)?;
        dict.set_item("status", self.status.clone())?;

        let courses = PyList::empty(py);
        for course in &self.course_list {
            courses.append(course.to_dict(py)?)?;
        }
        dict.set_item("course_list", courses)?;

        Ok(dict.into_py(py))
    }

    /// Parse from Python dictionary (for session restoration).
    ///
    /// Supports legacy key fallback for course list entries:
    /// - "code" or "course_code"
    /// - "name" or "course_name"
    ///
    /// # Arguments
    /// * `dict` - Python dictionary containing session state
    ///
    /// # Returns
    /// Reconstructed `SessionStateModel` instance
    ///
    /// # Errors
    /// Returns `PyKeyError` if required keys are missing
    /// Returns `PyErr` if type extraction fails
    ///
    /// # Examples
    /// ```rust
    /// use pyo3::Python;
    /// use pyo3::types::PyDict;
    /// use crate::models::session::SessionStateModel;
    ///
    /// Python::with_gil(|py| {
    ///     let dict = PyDict::new(py);
    ///     // ... populate required fields ...
    ///     let model = SessionStateModel::from_dict(dict).unwrap();
    /// });
    /// ```
    pub fn from_dict(dict: &PyDict) -> PyResult<Self> {
        let get_str_map = |key: &str| -> PyResult<HashMap<String, String>> {
            let sub_dict = required_item(dict, key)?.downcast::<PyDict>()?;
            let mut map = HashMap::new();
            for (k, v) in sub_dict.iter() {
                let key: String = k.extract()?;
                let value: String = v.extract()?;
                map.insert(key, value);
            }
            Ok(map)
        };

        let session_headers = get_str_map("session_headers")?;
        let session_cookies = get_str_map("session_cookies")?;
        let params = get_str_map("params")?;

        let javax_faces_view_state: Option<String> =
            required_item(dict, "javax_faces_view_state")?.extract()?;
        let career_code: String = required_item(dict, "career_code")?.extract()?;
        let career_name: String = required_item(dict, "career_name")?.extract()?;
        let is_electives: bool = required_item(dict, "is_electives")?.extract()?;
        let status: String = required_item(dict, "status")?.extract()?;

        let list = required_item(dict, "course_list")?.downcast::<PyList>()?;
        let mut course_list = Vec::with_capacity(list.len());
        for item in list.iter() {
            let course_dict = item.downcast::<PyDict>()?;
            course_list.push(parse_course_dict(course_dict)?);
        }

        Ok(Self {
            session_headers,
            session_cookies,
            params,
            javax_faces_view_state,
            career_code,
            career_name,
            is_electives,
            status,
            course_list,
        })
    }

    /// Convert back to internal SessionState for Rust session restoration.
    ///
    /// This method performs denormalization of status values from Python representation:
    /// - "NO_SESSION" → "CREATED"
    /// - "CAREER_NOT_SET" → "SESSION_SET"
    ///
    /// # Returns
    /// Internal `SessionState` struct with denormalized status
    ///
    /// # Examples
    /// ```rust
    /// use crate::models::session::SessionStateModel;
    ///
    /// let model = SessionStateModel::default();
    /// let state = model.into_session_state();
    /// assert_eq!(state.status, "CREATED");
    /// ```
    #[must_use]
    pub fn into_session_state(self) -> SessionState {
        SessionState {
            session_headers: self.session_headers,
            session_cookies: self.session_cookies,
            params: self.params,
            javax_faces_ViewState: self.javax_faces_view_state,
            career_code: self.career_code,
            career_name: self.career_name,
            is_electives: self.is_electives,
            status: denormalize_status(&self.status),
            course_list: self.course_list,
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

fn denormalize_status(status: &str) -> String {
    match status {
        "NO_SESSION" => "CREATED".to_string(),
        "CAREER_NOT_SET" => "SESSION_SET".to_string(),
        "ON_CAREER_PAGE" => "ON_CAREER_PAGE".to_string(),
        "ON_COURSE_PAGE" => "ON_COURSE_PAGE".to_string(),
        other => other.to_string(),
    }
}

#[cfg(test)]
mod tests {
    use super::{parse_course_dict, CourseListEntryModel, SessionStateModel};
    use crate::http::session::SessionState;
    use pyo3::Python;

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
    fn test_from_session_state_copies_course_list_entries() {
        let state = SessionState {
            course_list: vec![
                CourseListEntryModel {
                    code: "1000001".to_string(),
                    name: "Calculo".to_string(),
                },
                CourseListEntryModel {
                    code: "2016489".to_string(),
                    name: "Estructuras de Datos".to_string(),
                },
            ],
            ..Default::default()
        };

        let model = SessionStateModel::from_session_state(&state);

        assert_eq!(
            model.course_list,
            vec![
                CourseListEntryModel {
                    code: "1000001".to_string(),
                    name: "Calculo".to_string(),
                },
                CourseListEntryModel {
                    code: "2016489".to_string(),
                    name: "Estructuras de Datos".to_string(),
                }
            ]
        );
    }

    #[test]
    fn test_course_entry_to_dict_from_dict_round_trip() {
        use pyo3::types::PyDict;

        Python::with_gil(|py| {
            let entry = CourseListEntryModel {
                code: "1000001".to_string(),
                name: "Calculo".to_string(),
            };

            let dict_obj = entry.to_dict(py).unwrap();
            let dict = dict_obj.downcast::<PyDict>(py).unwrap();

            assert_eq!(
                dict.get_item("code")
                    .unwrap()
                    .unwrap()
                    .extract::<String>()
                    .unwrap(),
                "1000001"
            );
            assert_eq!(
                dict.get_item("name")
                    .unwrap()
                    .unwrap()
                    .extract::<String>()
                    .unwrap(),
                "Calculo"
            );

            let restored = parse_course_dict(&dict).unwrap();
            assert_eq!(restored, entry);
        });
    }

    #[test]
    fn test_course_entry_from_dict_legacy_keys() {
        use pyo3::types::PyDict;

        Python::with_gil(|py| {
            let dict = PyDict::new(py);
            dict.set_item("course_code", "2016489").unwrap();
            dict.set_item("course_name", "Estructuras de Datos")
                .unwrap();

            let entry = parse_course_dict(dict).unwrap();
            assert_eq!(entry.code, "2016489");
            assert_eq!(entry.name, "Estructuras de Datos");
        });
    }

    #[test]
    fn test_course_entry_from_dict_mixed_keys() {
        use pyo3::types::PyDict;

        Python::with_gil(|py| {
            let dict = PyDict::new(py);
            dict.set_item("code", "1000001").unwrap();
            dict.set_item("course_name", "Calculo").unwrap();

            let entry = parse_course_dict(dict).unwrap();
            assert_eq!(entry.code, "1000001");
            assert_eq!(entry.name, "Calculo");
        });
    }

    #[test]
    fn test_course_entry_from_dict_missing_code() {
        use pyo3::types::PyDict;

        Python::with_gil(|py| {
            let dict = PyDict::new(py);
            dict.set_item("name", "Calculo").unwrap();

            let result = parse_course_dict(dict);
            assert!(result.is_err());
            assert!(result
                .unwrap_err()
                .to_string()
                .contains("Missing key: 'code' or 'course_code'"));
        });
    }

    #[test]
    fn test_course_entry_from_dict_missing_name() {
        use pyo3::types::PyDict;

        Python::with_gil(|py| {
            let dict = PyDict::new(py);
            dict.set_item("code", "1000001").unwrap();

            let result = parse_course_dict(dict);
            assert!(result.is_err());
            assert!(result
                .unwrap_err()
                .to_string()
                .contains("Missing key: 'name' or 'course_name'"));
        });
    }

    #[test]
    fn test_session_model_to_dict_course_list_structure() {
        use pyo3::types::{PyDict, PyList};

        Python::with_gil(|py| {
            let model = SessionStateModel {
                course_list: vec![CourseListEntryModel {
                    code: "1000001".to_string(),
                    name: "Calculo".to_string(),
                }],
                ..Default::default()
            };

            let dict_obj = model.to_dict(py).unwrap();
            let dict = dict_obj.downcast::<PyDict>(py).unwrap();
            let courses = dict
                .get_item("course_list")
                .unwrap()
                .unwrap()
                .downcast::<PyList>()
                .unwrap();

            assert_eq!(courses.len(), 1);
            let course_dict = courses.get_item(0).unwrap().downcast::<PyDict>().unwrap();
            assert_eq!(
                course_dict
                    .get_item("code")
                    .unwrap()
                    .unwrap()
                    .extract::<String>()
                    .unwrap(),
                "1000001"
            );
            assert_eq!(
                course_dict
                    .get_item("name")
                    .unwrap()
                    .unwrap()
                    .extract::<String>()
                    .unwrap(),
                "Calculo"
            );
        });
    }

    #[test]
    fn test_session_model_from_dict_to_dict_round_trip() {
        use pyo3::types::PyDict;

        Python::with_gil(|py| {
            let original = SessionStateModel {
                course_list: vec![CourseListEntryModel {
                    code: "1000001".to_string(),
                    name: "Calculo".to_string(),
                }],
                career_code: "0-2-8-3".to_string(),
                career_name: "Ingenieria".to_string(),
                status: "ON_CAREER_PAGE".to_string(),
                ..Default::default()
            };

            let dict_obj = original.to_dict(py).unwrap();
            let dict = dict_obj.downcast::<PyDict>(py).unwrap();
            let restored = SessionStateModel::from_dict(dict).unwrap();

            assert_eq!(restored.course_list, original.course_list);
            assert_eq!(restored.career_code, original.career_code);
            assert_eq!(restored.status, original.status);
        });
    }

    #[test]
    fn test_session_model_from_dict_legacy_course_keys() {
        use pyo3::types::{PyDict, PyList};

        Python::with_gil(|py| {
            let dict = PyDict::new(py);

            dict.set_item("session_headers", PyDict::new(py)).unwrap();
            dict.set_item("session_cookies", PyDict::new(py)).unwrap();
            dict.set_item("params", PyDict::new(py)).unwrap();
            dict.set_item("javax_faces_view_state", py.None()).unwrap();
            dict.set_item("career_code", "0-2-8-3").unwrap();
            dict.set_item("career_name", "Ingenieria").unwrap();
            dict.set_item("is_electives", false).unwrap();
            dict.set_item("status", "ON_CAREER_PAGE").unwrap();

            let courses = PyList::empty(py);
            let course_dict = PyDict::new(py);
            course_dict.set_item("course_code", "1000001").unwrap();
            course_dict.set_item("course_name", "Calculo").unwrap();
            courses.append(course_dict).unwrap();
            dict.set_item("course_list", courses).unwrap();

            let model = SessionStateModel::from_dict(dict).unwrap();
            assert_eq!(model.course_list.len(), 1);
            assert_eq!(model.course_list[0].code, "1000001");
            assert_eq!(model.course_list[0].name, "Calculo");
        });
    }
}
