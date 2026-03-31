//! SIA Scraper Rust Extensions
//!
//! This module provides high-performance Rust implementations of core parsing
//! functions for extracting academic information from SIA (Sistema de Información Académica).

use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyString};
use pyo3::PyTypeInfo;

mod error;
mod parsers;
#[cfg(test)]
mod tests;

/// Parse course information from Oracle ADF XML/HTML response.
///
/// Extracts comprehensive course data including course name, credits, typology,
/// and all available groups with their schedules.
///
/// # Arguments
/// * `xml` - Raw XML/HTML string from SIA course detail page
///
/// # Returns
/// Python dictionary containing:
/// - `course_name`: Course title string
/// - `credits`: Credit hours as integer
/// - `typology`: Course typology string
/// - `available_spots`: Total available spots across all groups
/// - `groups`: List of group dictionaries with schedules
/// - `scrape_timestamp`: Timestamp string
/// - `code`: Course code (None for now)
///
/// # Errors
/// Returns `SiaScraperError` if course name or credits not found
///
/// # Examples
/// ```python
/// import sia_scraper_rust
/// result = sia_scraper_rust.parse_course_info(xml_string)
/// print(result["course_name"])  # "CALCULO AVANZADO"
/// ```
#[pyfunction]
fn parse_course_info(xml: &str) -> Result<Py<PyAny>, error::SiaScraperError> {
    Python::with_gil(|py| parsers::course_parser::parse_course_xml(xml, py))
}

/// Extract the ViewState value from Oracle ADF HTML response.
///
/// ViewState is a hidden form field used by Oracle ADF for state management.
///
/// # Arguments
/// * `html` - Raw HTML string from SIA Oracle ADF response
///
/// # Returns
/// ViewState string value extracted from hidden input element
///
/// # Errors
/// Returns `SiaScraperError::ExtractionError` if ViewState element not found
///
/// # Examples
/// ```python
/// import sia_scraper_rust
/// view_state = sia_scraper_rust.extract_view_state(html_string)
/// ```
#[pyfunction]
fn extract_view_state(html: &str) -> Result<String, error::SiaScraperError> {
    parsers::adf::extract_view_state(html)
}

/// Parse course prerequisites and enrollment conditions from Oracle ADF XML.
///
/// Extracts prerequisite information including course details and all
/// prerequisite conditions with their required courses.
///
/// # Arguments
/// * `xml` - Raw XML/HTML string from SIA course prerequisites page
///
/// # Returns
/// Python dictionary containing:
/// - `course_name`: Course title string
/// - `code`: Course code (None for now)
/// - `credits`: Credit hours as integer
/// - `typology`: Course typology string
/// - `conditions`: List of prerequisite condition dictionaries
///
/// # Errors
/// Returns `SiaScraperError` if course name or credits not found
///
/// # Examples
/// ```python
/// import sia_scraper_rust
/// result = sia_scraper_rust.parse_prereqs(xml_string)
/// print(len(result["conditions"]))  # Number of prerequisite conditions
/// ```
#[pyfunction]
fn parse_prereqs(xml: &str) -> Result<Py<PyAny>, error::SiaScraperError> {
    Python::with_gil(|py| parsers::course_parser::parse_prereqs_xml(xml, py))
}

/// Extract course list from Oracle ADF table HTML.
///
/// Parses `<tr class="af_table_data-row">` elements and extracts
/// course code and name from nested spans.
///
/// # Arguments
/// * `html` - Raw HTML string from SIA career page
///
/// # Returns
/// Python list of dictionaries: [{course_code: course_name}, ...]
///
/// # Errors
/// Returns `SiaScraperError` if table structure invalid
///
/// # Examples
/// ```python
/// import sia_scraper_rust
/// result = sia_scraper_rust.get_course_list(html_string)
/// print(len(result))  # Number of courses
/// ```
#[pyfunction]
fn get_course_list(html: &PyAny) -> Result<Py<PyAny>, error::SiaScraperError> {
    let html_str: String = if let Ok(s) = html.downcast::<PyString>() {
        s.to_string()
    } else if let Ok(b) = html.downcast::<PyBytes>() {
        String::from_utf8_lossy(b.as_bytes()).to_string()
    } else {
        return Err(error::SiaScraperError::InvalidInput(
            "Expected str or bytes".to_string(),
        ));
    };
    Python::with_gil(|py| {
        let courses = parsers::table_parser::get_course_list(&html_str)?;
        let mut list: Vec<pyo3::PyObject> = Vec::with_capacity(courses.len());

        for course_map in courses {
            let dict = pyo3::types::PyDict::new(py);
            for (k, v) in course_map {
                dict.set_item(k, v)?;
            }
            list.push(dict.into_py(py));
        }

        Ok(pyo3::types::PyList::new(py, &list).into_py(py))
    })
}

/// Extract human-readable plain text from Oracle ADF XML response.
///
/// # Arguments
/// * `xml` - Raw XML/HTML string from SIA response
///
/// # Returns
/// Plain text content before triple non-breaking-space separator
#[pyfunction]
fn get_plain_text(xml: &str) -> String {
    parsers::course_parser::get_plain_text(xml)
}

/// Initialize Oracle ADF request dictionary boilerplate.
#[pyfunction]
#[allow(clippy::too_many_arguments)]
fn init_oracle_adf_request_dict(
    tipology_index: &str,
    window_id: Option<&str>,
    page_id: Option<&str>,
    view_state: Option<&str>,
) -> Result<Py<PyAny>, error::SiaScraperError> {
    use parsers::adf_request::OracleAdfRequestBuilderState;

    let mut builder = OracleAdfRequestBuilderState::new();
    let request_dict = builder.init_request_dict(tipology_index, window_id, page_id, view_state);

    Python::with_gil(|py| {
        let dict = pyo3::types::PyDict::new(py);
        for (k, v) in request_dict {
            dict.set_item(k, v)?;
        }
        Ok(dict.into_py(py))
    })
}

/// Build Oracle ADF request body for one action.
#[pyfunction]
fn build_oracle_adf_request_body(
    request_dict: &pyo3::types::PyDict,
    data_name: &str,
    idx: i32,
    career_indices: Vec<String>,
    course_list_len: usize,
) -> Result<Py<PyAny>, error::SiaScraperError> {
    use parsers::adf_request::OracleAdfRequestBuilderState;

    let mut state = OracleAdfRequestBuilderState::new();
    let mut rust_request_dict = std::collections::HashMap::new();

    for (k, v) in request_dict {
        let key: String = k.extract().map_err(error::SiaScraperError::from)?;
        let value: String = v.extract().map_err(error::SiaScraperError::from)?;
        rust_request_dict.insert(key, value);
    }

    state.request_dict = rust_request_dict;
    let built = state.build_request_body(data_name, idx, &career_indices, course_list_len)?;

    Python::with_gil(|py| {
        let dict = pyo3::types::PyDict::new(py);
        for (k, v) in built {
            dict.set_item(k, v)?;
        }
        Ok(dict.into_py(py))
    })
}

/// Build Oracle ADF event dictionary for a component action.
#[pyfunction]
fn get_oracle_adf_event_dict(
    id: &str,
    event_type: &str,
    idx: i32,
) -> Result<Py<PyAny>, error::SiaScraperError> {
    let event_dict = parsers::adf_request::get_event_dict(id, event_type, idx);

    Python::with_gil(|py| {
        let dict = pyo3::types::PyDict::new(py);
        for (k, v) in event_dict {
            dict.set_item(k, v)?;
        }
        Ok(dict.into_py(py))
    })
}

/// Fuzzing helper: parse course list and ignore result.
pub fn fuzz_get_course_list(input: &str) {
    let _ = parsers::table_parser::get_course_list(input);
}

/// Fuzzing helper: extract plain text and ignore result.
pub fn fuzz_get_plain_text(input: &str) {
    let _ = parsers::course_parser::get_plain_text(input);
}

/// Fuzzing helper: extract ViewState and ignore result.
pub fn fuzz_extract_view_state(input: &str) {
    let _ = parsers::adf::extract_view_state(input);
}

#[pymodule]
fn sia_scraper_rust(py: Python<'_>, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(parse_course_info, m)?)?;
    m.add_function(wrap_pyfunction!(extract_view_state, m)?)?;
    m.add_function(wrap_pyfunction!(parse_prereqs, m)?)?;
    m.add_function(wrap_pyfunction!(get_course_list, m)?)?;
    m.add_function(wrap_pyfunction!(get_plain_text, m)?)?;
    m.add_function(wrap_pyfunction!(init_oracle_adf_request_dict, m)?)?;
    m.add_function(wrap_pyfunction!(build_oracle_adf_request_body, m)?)?;
    m.add_function(wrap_pyfunction!(get_oracle_adf_event_dict, m)?)?;
    m.add(
        "SiaScraperException",
        error::SiaScraperException::type_object(py),
    )?;
    Ok(())
}
