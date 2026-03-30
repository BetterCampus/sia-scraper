//! Custom error types for SIA Scraper Rust extensions.
//!
//! This module defines the error hierarchy used throughout the Rust parsing
//! code, providing specific error variants for different failure modes.

use pyo3::create_exception;
use thiserror::Error;

create_exception!(
    sia_scraper_rust,
    SiaScraperException,
    pyo3::exceptions::PyException
);

/// Custom error types for SIA Scraper operations.
///
/// # Variants
/// - `ParseError`: General parsing failures
/// - `XmlError`: XML/HTML parsing errors
/// - `InvalidInput`: Invalid input data
/// - `ExtractionError`: Failed to extract required data from HTML/XML
/// - `MissingElement`: Required HTML/XML element not found
/// - `ParseFieldError`: Failed to parse a specific field value
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

    #[error("Missing element: {element} at selector: {selector}")]
    MissingElement {
        /// The type of element that was not found
        element: String,
        /// The CSS/XPath selector used in the failed search
        selector: String,
    },

    #[error("Failed to parse {field}: {value}")]
    ParseFieldError {
        /// The field name that failed to parse
        field: String,
        /// The value that could not be parsed
        value: String,
    },
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
