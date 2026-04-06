//! Typed session state models for Rust/Python boundary transport.

#![allow(non_local_definitions)]

use std::collections::HashMap;

use pyo3::exceptions::PyKeyError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyType};
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

    /// Deprecated: use `code` instead. Will be removed in v4.0.0.
    #[getter]
    fn course_code(&self, py: Python<'_>) -> PyResult<String> {
        emit_legacy_warning(py, "course_code getter", 2)?;
        Ok(self.code.clone())
    }

    /// Deprecated: use `name` instead. Will be removed in v4.0.0.
    #[getter]
    fn course_name(&self, py: Python<'_>) -> PyResult<String> {
        emit_legacy_warning(py, "course_name getter", 2)?;
        Ok(self.name.clone())
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
        Ok(self.to_dict(py)?.into_py(py))
    }

    fn __setstate__(&mut self, state: &PyAny) -> PyResult<()> {
        let dict = state.downcast::<PyDict>()?;
        let py = state.py();
        let normalized = normalize_course_dict(dict, py)?;
        self.code = normalized.code;
        self.name = normalized.name;
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
    /// ```python
    /// from sia_scraper_rust import CourseListEntryModel
    ///
    /// # Create a course entry
    /// entry = CourseListEntryModel(code="1000001", name="Calculo Diferencial")
    ///
    /// # Convert to dictionary (current format)
    /// course_dict = entry.to_dict()
    /// assert course_dict == {"code": "1000001", "name": "Calculo Diferencial"}
    ///
    /// # This format is compatible with SessionStateModel.from_dict()
    /// # and can be used for serialization/pickling
    /// ```
    fn to_dict(&self, py: Python<'_>) -> PyResult<Py<PyDict>> {
        let dict = PyDict::new(py);
        dict.set_item("code", &self.code)?;
        dict.set_item("name", &self.name)?;
        Ok(dict.into())
    }

    /// Create from dictionary supporting multiple formats.
    ///
    /// # Supported Formats
    /// - Current: `{"code": "1000001", "name": "Calculo"}`
    /// - Legacy named: `{"course_code": "1000001", "course_name": "Calculo"}`
    /// - Legacy single-key: `{"1000001": "Calculo"}`
    ///
    /// # Arguments
    /// * `_cls` - Class reference (unused, required by classmethod)
    /// * `dict` - Dictionary with course data
    ///
    /// # Returns
    /// New `CourseListEntryModel` instance
    ///
    /// # Errors
    /// - `PyKeyError` if dict doesn't match any supported format (via `normalize_course_dict()`)
    /// - `PyTypeError` if key/value types are wrong (e.g., non-string values in `normalize_course_dict()`)
    /// # Examples
    /// ```python
    /// import sia_scraper_rust
    ///
    /// # Current format
    /// entry = sia_scraper_rust.CourseListEntryModel.from_dict({
    ///     "code": "1000001",
    ///     "name": "Calculo"
    /// })
    ///
    /// # Legacy format (deprecated, emits warning)
    /// entry = sia_scraper_rust.CourseListEntryModel.from_dict({
    ///     "1000001": "Calculo"
    /// })
    /// ```
    #[classmethod]
    fn from_dict(_cls: &PyType, dict: &PyDict) -> PyResult<Self> {
        let py = dict.py();
        normalize_course_dict(dict, py)
    }
}

/// Convenience wrapper that automatically extracts Python context from dict.
#[inline(always)]
fn parse_course_dict(dict: &PyDict) -> PyResult<CourseListEntryModel> {
    normalize_course_dict(dict, dict.py())
}

/// Parse course entry from dict supporting multiple formats.
///
/// # Supported Formats
/// 1. Current: `{"code": "1000001", "name": "Calculo"}`
/// 2. Legacy named keys: `{"course_code": "1000001", "course_name": "Calculo"}`
/// 3. Legacy single-key: `{"1000001": "Calculo"}`
///
/// # Arguments
/// * `dict` - Python dict containing course data
/// * `py` - Python GIL token for warning emission
///
/// # Returns
/// Parsed `CourseListEntryModel`
///
/// # Errors
/// Returns `PyKeyError` if dict doesn't match any supported format
///
/// # Examples
/// ```rust,ignore
/// use pyo3::Python;
/// use pyo3::types::PyDict;
///
/// Python::with_gil(|py| {
///     let dict = PyDict::new(py);
///     dict.set_item("code", "1000001").unwrap();
///     dict.set_item("name", "Calculo").unwrap();
///     let entry = normalize_course_dict(dict, py).unwrap();
/// });
/// ```
fn normalize_course_dict(dict: &PyDict, py: Python<'_>) -> PyResult<CourseListEntryModel> {
    // Try to get code from current or legacy key
    let code_result: Option<(&PyAny, bool)> = if let Some(val) = dict.get_item("code")? {
        Some((val, false))
    } else if let Some(val) = dict.get_item("course_code")? {
        Some((val, true))
    } else {
        None
    };

    // Try to get name from current or legacy key
    let name_result: Option<(&PyAny, bool)> = if let Some(val) = dict.get_item("name")? {
        Some((val, false))
    } else if let Some(val) = dict.get_item("course_name")? {
        Some((val, true))
    } else {
        None
    };

    // If both found, emit warning if either is legacy
    if let (Some((code_val, code_is_legacy)), Some((name_val, name_is_legacy))) =
        (code_result, name_result)
    {
        if code_is_legacy || name_is_legacy {
            emit_legacy_warning(py, "course_code/course_name", 3)?;
        }
        return Ok(CourseListEntryModel {
            code: code_val.extract()?,
            name: name_val.extract()?,
        });
    }

    // Fallback to single-entry legacy format if neither code/name keys found
    if dict.len() == 1 {
        if let Some((key, value)) = dict.iter().next() {
            let key_str: String = key.extract()?;
            if !["code", "name", "course_code", "course_name"].contains(&key_str.as_str()) {
                emit_legacy_warning(py, "single-key dict", 3)?;
                return Ok(CourseListEntryModel {
                    code: key_str,
                    name: value.extract()?,
                });
            }
        }
    }

    // Specific error messages for missing fields
    match (code_result, name_result) {
        (None, None) => Err(PyKeyError::new_err(
            "Dict must contain 'code'/'name' keys (current), \
             'course_code'/'course_name' keys (legacy named), \
             or be a single-entry dict (legacy single-key)",
        )),
        (None, Some(_)) => Err(PyKeyError::new_err("Missing key: 'code' or 'course_code'")),
        (Some(_), None) => Err(PyKeyError::new_err("Missing key: 'name' or 'course_name'")),
        _ => unreachable!(),
    }
}

/// Emit a Python DeprecationWarning for legacy course dict formats.
///
/// Warns users about deprecated course entry formats that will be removed in v4.0.0.
/// The standard format is `{'code': ..., 'name': ...}`.
///
/// # Arguments
/// * `py` - Python GIL token for calling Python APIs
/// * `format_type` - Description of the deprecated format. Supported values:
///   - `"course_code getter"` - Deprecated getter property
///   - `"course_name getter"` - Deprecated getter property
///   - `"course_code/course_name"` - Legacy named key format
///   - `"single-key dict"` - Legacy single-entry dict format
/// * `stacklevel` - Warning stack depth (default: 2 for direct Python calls).
///   Use 3 when called through `normalize_course_dict` from `from_dict`/`__setstate__`.
///
/// # Returns
/// `Ok(())` if warning was successfully emitted
///
/// # Errors
/// Returns `PyErr` if Python warning module import or method call fails
fn emit_legacy_warning(py: Python<'_>, format_type: &str, stacklevel: u32) -> PyResult<()> {
    let warnings = py.import("warnings")?;

    let message = match format_type {
        "course_code getter" => {
            "course_code getter is deprecated. Use code instead. Will be removed in v4.0.0."
                .to_string()
        }
        "course_name getter" => {
            "course_name getter is deprecated. Use name instead. Will be removed in v4.0.0."
                .to_string()
        }
        "javax_faces_ViewState key" => {
            "javax_faces_ViewState key is deprecated. Use javax_faces_view_state instead. \
             Will be removed in v4.0.0."
                .to_string()
        }
        _ => {
            format!(
                "CourseListEntry deserialization from {} format is deprecated. \
             Use {{'code': ..., 'name': ...}} instead. \
             Legacy format support will be removed in version 4.0.0",
                format_type
            )
        }
    };

    warnings.call_method1(
        "warn",
        (
            message,
            py.get_type::<pyo3::exceptions::PyDeprecationWarning>(),
            stacklevel,
        ),
    )?;
    Ok(())
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
        Self::from_session_state(&SessionState::default())
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
        Ok(self.to_dict(py)?.into_py(py))
    }

    fn __setstate__(&mut self, state: &PyAny) -> PyResult<()> {
        let dict = state.downcast::<PyDict>()?;
        *self = Self::from_dict(dict)?;
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
    /// ```rust,ignore
    /// use crate::http::session::SessionState;
    /// use crate::models::session::SessionStateModel;
    /// use std::collections::HashMap;
    ///
    /// let state = SessionState {
    ///     session_headers: HashMap::new(),
    ///     session_cookies: HashMap::new(),
    ///     params: HashMap::new(),
    ///     javax_faces_ViewState: None,
    ///     career_code: String::new(),
    ///     career_name: String::new(),
    ///     is_electives: false,
    ///     status: "CREATED".to_string(),
    ///     course_list: Vec::new(),
    /// };
    /// let model = SessionStateModel::from_session_state(&state);
    /// assert_eq!(model.status, "NO_SESSION"); // "CREATED" normalized to "NO_SESSION"
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
    /// ```rust,ignore
    /// use pyo3::Python;
    /// use crate::models::session::SessionStateModel;
    ///
    /// Python::with_gil(|py| {
    ///     let model = SessionStateModel::default();
    ///     let dict = model.to_dict(py).unwrap();
    /// });
    /// ```
    pub fn to_dict(&self, py: Python<'_>) -> PyResult<Py<PyDict>> {
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
    /// Supports multiple formats for course list entries (legacy compatibility):
    /// - **Current format**: `{"code": "1000001", "name": "Calculo"}`
    /// - **Legacy named keys**: `{"course_code": "1000001", "course_name": "Calculo"}`
    /// - **Legacy single-entry**: `{"1000001": "Calculo"}` (dict mapping code->name;
    ///   deprecated, emits deprecation warning)
    /// - **Mixed formats**: Entries can use different formats within the same course_list
    ///
    /// Also accepts legacy `javax_faces_ViewState` key for pickle compatibility.
    ///
    /// **Note:** The `javax_faces_view_state` key is optional. If neither the current
    /// `javax_faces_view_state` nor the legacy `javax_faces_ViewState` key is present,
    /// the field defaults to `None`.
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
    /// ```rust,ignore
    /// use pyo3::Python;
    /// use pyo3::types::{PyDict, PyList};
    /// use crate::models::session::SessionStateModel;
    ///
    /// Python::with_gil(|py| {
    ///     let dict = PyDict::new(py);
    ///     dict.set_item("session_headers", PyDict::new(py)).unwrap();
    ///     dict.set_item("session_cookies", PyDict::new(py)).unwrap();
    ///     dict.set_item("params", PyDict::new(py)).unwrap();
    ///     dict.set_item("career_code", "0-2-8-3").unwrap();
    ///     dict.set_item("career_name", "Ingenieria").unwrap();
    ///     dict.set_item("is_electives", false).unwrap();
    ///     dict.set_item("status", "ON_CAREER_PAGE").unwrap();
    ///     dict.set_item("javax_faces_view_state", "vs-123").unwrap();
    ///
    ///     // Current format: {"code": "...", "name": "..."}
    ///     let courses = PyList::empty(py);
    ///     let course = PyDict::new(py);
    ///     course.set_item("code", "1000001").unwrap();
    ///     course.set_item("name", "Calculo").unwrap();
    ///     courses.append(course).unwrap();
    ///
    ///     // Legacy named keys format (deprecated)
    ///     let legacy_course = PyDict::new(py);
    ///     legacy_course.set_item("course_code", "2016489").unwrap();
    ///     legacy_course.set_item("course_name", "Estructuras").unwrap();
    ///     courses.append(legacy_course).unwrap();
    ///
    ///     // Legacy single-entry format (deprecated, requires catch_warnings)
    ///     let single_entry = PyDict::new(py);
    ///     single_entry.set_item("3015489", "Algebra Lineal").unwrap();
    ///     courses.append(single_entry).unwrap();
    ///
    ///     dict.set_item("course_list", courses).unwrap();
    ///
    ///     // Suppress deprecation warning for legacy formats
    ///     let warnings = py.import("warnings").unwrap();
    ///     let catch_warnings = warnings.call_method0("catch_warnings").unwrap();
    ///     catch_warnings.call_method0("__enter__").unwrap();
    ///     warnings.call_method1("simplefilter", ("ignore",)).unwrap();
    ///
    ///     let model = SessionStateModel::from_dict(dict).unwrap();
    ///
    ///     catch_warnings
    ///         .call_method1("__exit__", (py.None(), py.None(), py.None()))
    ///         .unwrap();
    ///
    ///     assert_eq!(model.course_list.len(), 3);
    ///     assert_eq!(model.course_list[0].code, "1000001");
    ///     assert_eq!(model.course_list[1].code, "2016489");
    ///     assert_eq!(model.course_list[2].code, "3015489");
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
            if let Some(val) = dict.get_item("javax_faces_view_state")? {
                val.extract()?
            } else if let Some(val) = dict.get_item("javax_faces_ViewState")? {
                emit_legacy_warning(dict.py(), "javax_faces_ViewState key", 2)?;
                val.extract()?
            } else {
                None
            };
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
    /// # Arguments
    /// * `self` — the `SessionStateModel` being converted/consumed (owned)
    ///
    /// # Returns
    /// Internal `SessionState` struct with denormalized status
    ///
    /// # Examples
    /// ```rust,ignore
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
    use pyo3::{types::PyList, PyAny, Python};
    use std::collections::HashMap;

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
    fn test_into_session_state_preserves_course_list_and_denormalizes_status() {
        let model = SessionStateModel {
            session_headers: HashMap::new(),
            session_cookies: HashMap::new(),
            params: HashMap::new(),
            javax_faces_view_state: Some("vs-123".to_string()),
            career_code: "0-2-8-3".to_string(),
            career_name: "Ingenieria".to_string(),
            is_electives: true,
            status: "ON_CAREER_PAGE".to_string(),
            course_list: vec![
                CourseListEntryModel {
                    code: "1000001".to_string(),
                    name: "Calculo".to_string(),
                },
                CourseListEntryModel {
                    code: "2016489".to_string(),
                    name: "Estructuras".to_string(),
                },
            ],
        };

        let state = model.into_session_state();

        assert_eq!(state.status, "ON_CAREER_PAGE");
        assert_eq!(state.course_list.len(), 2);
        assert_eq!(state.course_list[0].code, "1000001");
        assert_eq!(state.course_list[0].name, "Calculo");
        assert_eq!(state.course_list[1].code, "2016489");
        assert_eq!(state.course_list[1].name, "Estructuras");
    }

    #[test]
    fn test_into_session_state_handles_empty_course_list() {
        let model = SessionStateModel {
            course_list: vec![],
            status: "NO_SESSION".to_string(),
            session_headers: HashMap::new(),
            session_cookies: HashMap::new(),
            params: HashMap::new(),
            javax_faces_view_state: None,
            career_code: String::new(),
            career_name: String::new(),
            is_electives: false,
        };

        let state = model.into_session_state();

        assert_eq!(state.course_list.len(), 0);
        assert_eq!(state.status, "CREATED");
    }

    #[test]
    fn test_into_session_state_denormalizes_all_status_values() {
        let test_cases = vec![
            ("NO_SESSION", "CREATED"),
            ("CAREER_NOT_SET", "SESSION_SET"),
            ("ON_CAREER_PAGE", "ON_CAREER_PAGE"),
            ("ON_COURSE_PAGE", "ON_COURSE_PAGE"),
            ("CUSTOM_STATUS", "CUSTOM_STATUS"),
        ];

        for (model_status, expected_state_status) in test_cases {
            let model = SessionStateModel {
                status: model_status.to_string(),
                session_headers: HashMap::new(),
                session_cookies: HashMap::new(),
                params: HashMap::new(),
                javax_faces_view_state: None,
                career_code: String::new(),
                career_name: String::new(),
                is_electives: false,
                course_list: vec![],
            };
            let state = model.into_session_state();
            assert_eq!(
                state.status, expected_state_status,
                "Failed for model status '{}'",
                model_status
            );
        }
    }

    #[test]
    fn test_into_session_state_preserves_all_fields() {
        let mut headers = HashMap::new();
        headers.insert("X-Custom".to_string(), "value".to_string());

        let mut cookies = HashMap::new();
        cookies.insert("session_id".to_string(), "abc123".to_string());

        let mut params = HashMap::new();
        params.insert("Adf-Page-Id".to_string(), "2".to_string());

        let model = SessionStateModel {
            session_headers: headers.clone(),
            session_cookies: cookies.clone(),
            params: params.clone(),
            javax_faces_view_state: Some("vs-xyz".to_string()),
            career_code: "0-2-8-3".to_string(),
            career_name: "Ingenieria de Sistemas".to_string(),
            is_electives: true,
            status: "CAREER_NOT_SET".to_string(),
            course_list: vec![],
        };

        let state = model.into_session_state();

        assert_eq!(state.session_headers, headers);
        assert_eq!(state.session_cookies, cookies);
        assert_eq!(state.params, params);
        assert_eq!(state.javax_faces_ViewState, Some("vs-xyz".to_string()));
        assert_eq!(state.career_code, "0-2-8-3");
        assert_eq!(state.career_name, "Ingenieria de Sistemas");
        assert!(state.is_electives);
        assert_eq!(state.status, "SESSION_SET");
    }

    #[test]
    fn test_course_entry_to_dict_from_dict_round_trip() {
        Python::with_gil(|py| {
            let entry = CourseListEntryModel {
                code: "1000001".to_string(),
                name: "Calculo".to_string(),
            };

            let dict = entry.to_dict(py).unwrap();
            let dict_ref = dict.as_ref(py);

            assert_eq!(
                dict_ref
                    .get_item("code")
                    .unwrap()
                    .unwrap()
                    .extract::<String>()
                    .unwrap(),
                "1000001"
            );
            assert_eq!(
                dict_ref
                    .get_item("name")
                    .unwrap()
                    .unwrap()
                    .extract::<String>()
                    .unwrap(),
                "Calculo"
            );

            let restored = parse_course_dict(dict_ref).unwrap();
            assert_eq!(restored, entry);
        });
    }

    fn assert_deprecation_warning(
        warning_list: &PyAny,
        expected_format: &str,
    ) -> Result<(), pyo3::PyErr> {
        let warnings_list = warning_list.downcast::<PyList>()?;
        let mut found_matching_warning = false;

        for i in 0..warnings_list.len() {
            let warning = warnings_list.get_item(i)?;
            let category = warning.getattr("category")?;
            let message = warning.getattr("message")?;
            let message_str = message.str()?.to_string();

            let category_name = category.str()?.to_string();

            if category_name.contains("DeprecationWarning")
                && message_str.contains(expected_format)
                && message_str.contains("4.0.0")
            {
                found_matching_warning = true;
                break;
            }
        }

        assert!(
            found_matching_warning,
            "Expected at least one deprecation warning containing '{}' and '4.0.0', got {} warnings",
            expected_format,
            warnings_list.len()
        );

        Ok(())
    }

    #[test]
    fn test_course_entry_from_dict_legacy_keys() {
        use pyo3::types::PyDict;

        Python::with_gil(|py| {
            let dict = PyDict::new(py);
            dict.set_item("course_code", "2016489").unwrap();
            dict.set_item("course_name", "Estructuras de Datos")
                .unwrap();

            let warnings = py.import("warnings").unwrap();
            let kwargs = PyDict::new(py);
            kwargs.set_item("record", true).unwrap();
            let catch_warnings = warnings
                .call_method("catch_warnings", (), Some(kwargs))
                .unwrap();
            let warning_list = catch_warnings.call_method0("__enter__").unwrap();
            warnings.call_method1("simplefilter", ("always",)).unwrap();

            let entry = parse_course_dict(dict).unwrap();

            catch_warnings
                .call_method1("__exit__", (py.None(), py.None(), py.None()))
                .unwrap();

            assert_eq!(entry.code, "2016489");
            assert_eq!(entry.name, "Estructuras de Datos");

            assert_deprecation_warning(warning_list, "course_code/course_name").unwrap();
        });
    }

    #[test]
    fn test_course_entry_from_dict_mixed_keys() {
        use pyo3::types::PyDict;

        Python::with_gil(|py| {
            let dict = PyDict::new(py);
            dict.set_item("code", "1000001").unwrap();
            dict.set_item("course_name", "Calculo").unwrap();

            let warnings = py.import("warnings").unwrap();
            let kwargs = PyDict::new(py);
            kwargs.set_item("record", true).unwrap();
            let catch_warnings = warnings
                .call_method("catch_warnings", (), Some(kwargs))
                .unwrap();
            let warning_list = catch_warnings.call_method0("__enter__").unwrap();
            warnings.call_method1("simplefilter", ("always",)).unwrap();

            let entry = parse_course_dict(dict).unwrap();

            catch_warnings
                .call_method1("__exit__", (py.None(), py.None(), py.None()))
                .unwrap();

            assert_eq!(entry.code, "1000001");
            assert_eq!(entry.name, "Calculo");

            assert_deprecation_warning(warning_list, "course_code/course_name").unwrap();
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
            let err_msg = result.unwrap_err().to_string();
            assert!(err_msg.contains("'name' or 'course_name'"));
        });
    }

    #[test]
    fn test_course_entry_from_dict_legacy_single_key() {
        use pyo3::types::PyDict;

        Python::with_gil(|py| {
            let dict = PyDict::new(py);
            dict.set_item("1000001", "Calculo").unwrap();

            let warnings = py.import("warnings").unwrap();
            let kwargs = PyDict::new(py);
            kwargs.set_item("record", true).unwrap();
            let catch_warnings = warnings
                .call_method("catch_warnings", (), Some(kwargs))
                .unwrap();
            let warning_list = catch_warnings.call_method0("__enter__").unwrap();
            warnings.call_method1("simplefilter", ("always",)).unwrap();

            let entry = parse_course_dict(dict).unwrap();

            catch_warnings
                .call_method1("__exit__", (py.None(), py.None(), py.None()))
                .unwrap();

            assert_eq!(entry.code, "1000001");
            assert_eq!(entry.name, "Calculo");

            assert_deprecation_warning(warning_list, "single-key dict").unwrap();
        });
    }

    #[test]
    fn test_course_entry_from_dict_legacy_single_key_alphanumeric() {
        use pyo3::types::PyDict;

        Python::with_gil(|py| {
            let dict = PyDict::new(py);
            dict.set_item("1000003-B", "Álgebra Lineal").unwrap();

            let warnings = py.import("warnings").unwrap();
            let kwargs = PyDict::new(py);
            kwargs.set_item("record", true).unwrap();
            let catch_warnings = warnings
                .call_method("catch_warnings", (), Some(kwargs))
                .unwrap();
            let warning_list = catch_warnings.call_method0("__enter__").unwrap();
            warnings.call_method1("simplefilter", ("always",)).unwrap();

            let entry = parse_course_dict(dict).unwrap();

            catch_warnings
                .call_method1("__exit__", (py.None(), py.None(), py.None()))
                .unwrap();

            assert_eq!(entry.code, "1000003-B");
            assert_eq!(entry.name, "Álgebra Lineal");

            assert_deprecation_warning(warning_list, "single-key dict").unwrap();
        });
    }

    #[test]
    fn test_course_entry_from_dict_invalid_format() {
        use pyo3::types::PyDict;

        Python::with_gil(|py| {
            let dict = PyDict::new(py);
            dict.set_item("invalid_key", "value1").unwrap();
            dict.set_item("another_key", "value2").unwrap();

            let result = parse_course_dict(dict);
            assert!(result.is_err());
            let err_msg = result.unwrap_err().to_string();
            assert!(err_msg.contains("'code'/'name'"));
            assert!(err_msg.contains("'course_code'/'course_name'"));
            assert!(err_msg.contains("single-entry dict"));
        });
    }

    #[test]
    fn test_course_entry_from_dict_single_reserved_key_code() {
        use pyo3::types::PyDict;

        Python::with_gil(|py| {
            let dict = PyDict::new(py);
            dict.set_item("code", "1000001").unwrap();

            let result = parse_course_dict(dict);
            assert!(result.is_err());
            let err_msg = result.unwrap_err().to_string();
            assert!(err_msg.contains("'name' or 'course_name'"));
        });
    }

    #[test]
    fn test_course_entry_from_dict_single_reserved_key_name() {
        use pyo3::types::PyDict;

        Python::with_gil(|py| {
            let dict = PyDict::new(py);
            dict.set_item("name", "Calculo").unwrap();

            let result = parse_course_dict(dict);
            assert!(result.is_err());
            let err_msg = result.unwrap_err().to_string();
            assert!(err_msg.contains("'code' or 'course_code'"));
        });
    }

    #[test]
    fn test_course_entry_from_dict_classmethod() {
        use pyo3::types::PyDict;
        use pyo3::PyTypeInfo;

        Python::with_gil(|py| {
            let cls = CourseListEntryModel::type_object(py);

            let dict = PyDict::new(py);
            dict.set_item("code", "1000001").unwrap();
            dict.set_item("name", "Calculo").unwrap();

            let entry = CourseListEntryModel::from_dict(cls, dict).unwrap();
            assert_eq!(entry.code, "1000001");
            assert_eq!(entry.name, "Calculo");
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

            let dict = model.to_dict(py).unwrap();
            let dict_ref = dict.as_ref(py);
            let courses = dict_ref
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

            let dict = original.to_dict(py).unwrap();
            let dict_ref = dict.as_ref(py);
            let restored = SessionStateModel::from_dict(dict_ref).unwrap();

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

            let warnings = py.import("warnings").unwrap();
            let kwargs = PyDict::new(py);
            kwargs.set_item("record", true).unwrap();
            let catch_warnings = warnings
                .call_method("catch_warnings", (), Some(kwargs))
                .unwrap();
            let warning_list = catch_warnings.call_method0("__enter__").unwrap();
            warnings.call_method1("simplefilter", ("always",)).unwrap();

            let model = SessionStateModel::from_dict(dict).unwrap();

            catch_warnings
                .call_method1("__exit__", (py.None(), py.None(), py.None()))
                .unwrap();

            assert_eq!(model.course_list.len(), 1);
            assert_eq!(model.course_list[0].code, "1000001");
            assert_eq!(model.course_list[0].name, "Calculo");

            assert_deprecation_warning(warning_list, "course_code/course_name").unwrap();
        });
    }

    #[test]
    fn test_session_model_from_dict_legacy_course_single_key() {
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
            course_dict.set_item("1000001", "Calculo").unwrap();
            courses.append(course_dict).unwrap();
            dict.set_item("course_list", courses).unwrap();

            let warnings = py.import("warnings").unwrap();
            let kwargs = PyDict::new(py);
            kwargs.set_item("record", true).unwrap();
            let catch_warnings = warnings
                .call_method("catch_warnings", (), Some(kwargs))
                .unwrap();
            let warning_list = catch_warnings.call_method0("__enter__").unwrap();
            warnings.call_method1("simplefilter", ("always",)).unwrap();

            let model = SessionStateModel::from_dict(dict).unwrap();

            catch_warnings
                .call_method1("__exit__", (py.None(), py.None(), py.None()))
                .unwrap();

            assert_eq!(model.course_list.len(), 1);
            assert_eq!(model.course_list[0].code, "1000001");
            assert_eq!(model.course_list[0].name, "Calculo");

            assert_deprecation_warning(warning_list, "single-key dict").unwrap();
        });
    }

    #[test]
    fn test_session_model_from_dict_missing_course_keys() {
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
            course_dict.set_item("invalid_key", "value1").unwrap();
            course_dict.set_item("another_key", "value2").unwrap();
            courses.append(course_dict).unwrap();
            dict.set_item("course_list", courses).unwrap();

            let result = SessionStateModel::from_dict(dict);
            assert!(result.is_err());
        });
    }

    #[test]
    fn test_session_model_from_dict_viewstate_missing_defaults_none() {
        use pyo3::types::{PyDict, PyList};

        Python::with_gil(|py| {
            let dict = PyDict::new(py);

            dict.set_item("session_headers", PyDict::new(py)).unwrap();
            dict.set_item("session_cookies", PyDict::new(py)).unwrap();
            dict.set_item("params", PyDict::new(py)).unwrap();
            // Intentionally omit javax_faces_view_state key entirely
            dict.set_item("career_code", "0-2-8-3").unwrap();
            dict.set_item("career_name", "Ingenieria").unwrap();
            dict.set_item("is_electives", false).unwrap();
            dict.set_item("status", "ON_CAREER_PAGE").unwrap();

            let courses = PyList::empty(py);
            let course_dict = PyDict::new(py);
            course_dict.set_item("code", "1000001").unwrap();
            course_dict.set_item("name", "Calculo").unwrap();
            courses.append(course_dict).unwrap();
            dict.set_item("course_list", courses).unwrap();

            // Should not raise an error when ViewState key is completely absent
            let model = SessionStateModel::from_dict(dict).unwrap();

            // ViewState should default to None
            assert_eq!(model.javax_faces_view_state, None);
            assert_eq!(model.career_code, "0-2-8-3");
            assert_eq!(model.course_list.len(), 1);
        });
    }

    #[test]
    fn test_session_model_from_dict_viewstate_explicit_none() {
        use pyo3::types::{PyDict, PyList};

        Python::with_gil(|py| {
            let dict = PyDict::new(py);

            dict.set_item("session_headers", PyDict::new(py)).unwrap();
            dict.set_item("session_cookies", PyDict::new(py)).unwrap();
            dict.set_item("params", PyDict::new(py)).unwrap();
            // Key is present but explicitly set to None
            dict.set_item("javax_faces_view_state", py.None()).unwrap();
            dict.set_item("career_code", "0-2-8-3").unwrap();
            dict.set_item("career_name", "Ingenieria").unwrap();
            dict.set_item("is_electives", false).unwrap();
            dict.set_item("status", "ON_CAREER_PAGE").unwrap();

            let courses = PyList::empty(py);
            let course_dict = PyDict::new(py);
            course_dict.set_item("code", "1000001").unwrap();
            course_dict.set_item("name", "Calculo").unwrap();
            courses.append(course_dict).unwrap();
            dict.set_item("course_list", courses).unwrap();

            let model = SessionStateModel::from_dict(dict).unwrap();

            // Should handle explicit None value
            assert_eq!(model.javax_faces_view_state, None);
            assert_eq!(model.career_code, "0-2-8-3");
        });
    }

    #[test]
    fn test_session_model_from_dict_legacy_viewstate_explicit_none() {
        use pyo3::types::{PyDict, PyList};

        Python::with_gil(|py| {
            let dict = PyDict::new(py);

            dict.set_item("session_headers", PyDict::new(py)).unwrap();
            dict.set_item("session_cookies", PyDict::new(py)).unwrap();
            dict.set_item("params", PyDict::new(py)).unwrap();
            // Legacy key is present with explicit None
            dict.set_item("javax_faces_ViewState", py.None()).unwrap();
            dict.set_item("career_code", "0-2-8-3").unwrap();
            dict.set_item("career_name", "Ingenieria").unwrap();
            dict.set_item("is_electives", false).unwrap();
            dict.set_item("status", "ON_CAREER_PAGE").unwrap();

            let courses = PyList::empty(py);
            let course_dict = PyDict::new(py);
            course_dict.set_item("code", "1000001").unwrap();
            course_dict.set_item("name", "Calculo").unwrap();
            courses.append(course_dict).unwrap();
            dict.set_item("course_list", courses).unwrap();

            // Capture deprecation warnings
            let warnings = py.import("warnings").unwrap();
            let kwargs = pyo3::types::PyDict::new(py);
            kwargs.set_item("record", true).unwrap();
            let catch_warnings = warnings
                .call_method("catch_warnings", (), Some(kwargs))
                .unwrap();
            let warning_list = catch_warnings.call_method0("__enter__").unwrap();
            warnings.call_method1("simplefilter", ("always",)).unwrap();

            let model = SessionStateModel::from_dict(dict).unwrap();

            catch_warnings
                .call_method1("__exit__", (py.None(), py.None(), py.None()))
                .unwrap();

            // Should handle legacy key with explicit None
            assert_eq!(model.javax_faces_view_state, None);
            assert_eq!(model.career_code, "0-2-8-3");

            // Verify deprecation warning was emitted for legacy key
            assert_deprecation_warning(warning_list, "javax_faces_ViewState").unwrap();
        });
    }

    #[test]
    fn test_session_model_from_dict_viewstate_with_value() {
        use pyo3::types::{PyDict, PyList};

        Python::with_gil(|py| {
            let dict = PyDict::new(py);

            dict.set_item("session_headers", PyDict::new(py)).unwrap();
            dict.set_item("session_cookies", PyDict::new(py)).unwrap();
            dict.set_item("params", PyDict::new(py)).unwrap();
            // Key present with actual value
            dict.set_item("javax_faces_view_state", "vs-test-123")
                .unwrap();
            dict.set_item("career_code", "0-2-8-3").unwrap();
            dict.set_item("career_name", "Ingenieria").unwrap();
            dict.set_item("is_electives", false).unwrap();
            dict.set_item("status", "ON_CAREER_PAGE").unwrap();

            let courses = PyList::empty(py);
            let course_dict = PyDict::new(py);
            course_dict.set_item("code", "1000001").unwrap();
            course_dict.set_item("name", "Calculo").unwrap();
            courses.append(course_dict).unwrap();
            dict.set_item("course_list", courses).unwrap();

            let model = SessionStateModel::from_dict(dict).unwrap();

            // Should extract the actual value
            assert_eq!(
                model.javax_faces_view_state,
                Some("vs-test-123".to_string())
            );
            assert_eq!(model.career_code, "0-2-8-3");
        });
    }
}
