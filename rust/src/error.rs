use pyo3::create_exception;
use pyo3::prelude::*;
use thiserror::Error;

create_exception!(
    sia_scraper_rust,
    SiaScraperException,
    pyo3::exceptions::PyException
);

#[derive(Error, Debug)]
pub enum SiaScraperError {
    #[error("Parse error: {0}")]
    ParseError(String),

    #[error("XML error: {0}")]
    XmlError(String),

    #[error("Invalid input: {0}")]
    InvalidInput(String),

    #[error("Extraction error: {0}")]
    ExtractionError(String),
}

impl From<quick_xml::Error> for SiaScraperError {
    fn from(e: quick_xml::Error) -> Self {
        SiaScraperError::XmlError(e.to_string())
    }
}

impl From<pyo3::PyErr> for SiaScraperError {
    fn from(e: pyo3::PyErr) -> Self {
        SiaScraperError::ParseError(e.to_string())
    }
}

impl From<SiaScraperError> for pyo3::PyErr {
    fn from(e: SiaScraperError) -> Self {
        SiaScraperException::new_err(e.to_string())
    }
}
