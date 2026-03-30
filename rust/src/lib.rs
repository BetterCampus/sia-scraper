use pyo3::prelude::*;

mod error;
mod parsers;

#[pyfunction]
fn parse_course_info(xml: &str) -> Result<Py<PyAny>, error::SiaScraperError> {
    Python::with_gil(|py| {
        parsers::course_parser::parse_course_xml(xml, py)
    })
}

#[pyfunction]
fn extract_view_state(html: &str) -> Result<String, error::SiaScraperError> {
    parsers::adf::extract_view_state(html)
}

#[pyfunction]
fn parse_prereqs(xml: &str) -> Result<Py<PyAny>, error::SiaScraperError> {
    Python::with_gil(|py| {
        parsers::course_parser::parse_prereqs_xml(xml, py)
    })
}

#[pymodule]
fn sia_scraper_rust(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(parse_course_info, m)?)?;
    m.add_function(wrap_pyfunction!(extract_view_state, m)?)?;
    m.add_function(wrap_pyfunction!(parse_prereqs, m)?)?;
    Ok(())
}
