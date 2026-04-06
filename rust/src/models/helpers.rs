//! Shared helpers for PyDict extraction in model constructors.
//!
//! This module provides reusable utilities for extracting required and optional
//! fields from Python dictionaries used in `#[new]` constructors.

use pyo3::exceptions::PyKeyError;
use pyo3::prelude::*;
use pyo3::types::PyDict;

pub(crate) fn required_item<'py>(dict: &'py PyDict, key: &str) -> PyResult<&'py PyAny> {
    dict.get_item(key)?
        .ok_or_else(|| PyKeyError::new_err(format!("Missing key: {key}")))
}

/// Extract a required field from a PyDict.
///
/// # Arguments
/// * `dict` - The PyDict to extract from
/// * `key` - The key to look up
///
/// # Returns
/// The extracted value, or `PyErr` if missing
///
/// # Errors
/// Returns `KeyError` if the key is not present in the dictionary
pub fn require_field<'py, T: FromPyObject<'py>>(dict: &'py PyDict, key: &str) -> PyResult<T> {
    required_item(dict, key)?.extract()
}

/// Extract an optional field from a PyDict.
///
/// Handles both missing keys (returns None) and explicit None values
/// (returns None) for optional parameters.
///
/// # Arguments
/// * `dict` - The PyDict to extract from
/// * `key` - The key to look up
///
/// # Returns
/// `Ok(Some(T))` if the key exists with a non-None value,
/// `Ok(None)` if the key is missing or value is None,
/// or `Err` if extraction fails for non-None values
pub fn optional_field<'py, T: FromPyObject<'py>>(
    dict: &'py PyDict,
    key: &str,
) -> PyResult<Option<T>> {
    match dict.get_item(key)? {
        Some(value) => {
            if value.is_none() {
                Ok(None)
            } else {
                value.extract().map(Some)
            }
        }
        None => Ok(None),
    }
}
