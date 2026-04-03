//! Custom error types for SIA Scraper Rust extensions.
//!
//! This module defines the error hierarchy used throughout the Rust parsing
//! code, providing specific error variants for different failure modes.
//!
//! # Error Taxonomy
//! - `InvalidInput`: caller-provided action/input is invalid for the requested operation.
//! - `ExtractionError`: required ADF/token data cannot be extracted from markup.
//! - `MissingElement`: required HTML node is missing for a known selector.
//! - `ParseFieldError`: a specific field value cannot be parsed into the expected type.
//! - `ParseError` / `XmlError`: generic parsing failures where field-level context is unavailable.
//!
//! # Propagation Policy
//! All fallible parser and request-builder operations return `Result<T, SiaScraperError>`.
//! At the Python FFI boundary, errors are mapped into `SiaScraperException` while preserving
//! detailed context in the error message.

use pyo3::create_exception;
use thiserror::Error;

create_exception!(
    sia_scraper_rust,
    SiaScraperException,
    pyo3::exceptions::PyException
);

create_exception!(
    sia_scraper_rust,
    NetworkError,
    SiaScraperException
);

create_exception!(
    sia_scraper_rust,
    HttpStatusError,
    SiaScraperException
);

create_exception!(
    sia_scraper_rust,
    SiaTimeoutError,
    SiaScraperException
);

create_exception!(sia_scraper_rust, ParseError, SiaScraperException);

create_exception!(
    sia_scraper_rust,
    SessionError,
    SiaScraperException
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
        SiaScraperError::XmlError(format!("XML parsing failed at: {}", e))
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

impl From<crate::http::errors::HttpError> for pyo3::PyErr {
    fn from(e: crate::http::errors::HttpError) -> Self {
        use crate::http::errors::HttpError;
        let message = e.to_string();
        match e {
            HttpError::NetworkError(_) => NetworkError::new_err(message),
            HttpError::HttpStatusError { .. } => HttpStatusError::new_err(message),
            HttpError::TimeoutError { .. } => SiaTimeoutError::new_err(message),
            HttpError::ParseError(_) => ParseError::new_err(message),
            HttpError::InvalidInput(_) => pyo3::exceptions::PyValueError::new_err(message),
            HttpError::SessionError(_) => SessionError::new_err(message),
        }
    }
}