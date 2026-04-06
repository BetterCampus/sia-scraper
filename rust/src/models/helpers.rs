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
///
/// # Examples
/// ```rust,ignore
/// use pyo3::types::PyDict;
/// Python::with_gil(|py| {
///     let dict = PyDict::new(py);
///     dict.set_item("name", "Test").unwrap();
///     let name: String = require_field(dict, "name").unwrap();
///     assert_eq!(name, "Test");
/// });
/// ```
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
///
/// # Examples
/// ```rust,ignore
/// use pyo3::types::PyDict;
/// Python::with_gil(|py| {
///     let dict = PyDict::new(py);
///     dict.set_item("name", "Test").unwrap();
///     let name: Option<String> = optional_field(dict, "name").unwrap();
///     assert_eq!(name, Some("Test".to_string()));
///
///     // Missing key returns None
///     let missing: Option<String> = optional_field(dict, "missing").unwrap();
///     assert_eq!(missing, None);
/// });
/// ```
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

#[cfg(test)]
mod tests {
    use super::*;
    use pyo3::Python;

    #[test]
    fn test_require_field_happy_path() {
        Python::with_gil(|py| {
            let dict = PyDict::new(py);
            dict.set_item("key", "value").unwrap();
            let result: String = require_field(dict, "key").unwrap();
            assert_eq!(result, "value");
        });
    }

    #[test]
    fn test_require_field_missing_key_returns_error() {
        Python::with_gil(|py| {
            let dict = PyDict::new(py);
            let result: PyResult<String> = require_field(dict, "missing");
            assert!(result.is_err());
        });
    }

    #[test]
    fn test_require_field_wrong_type_returns_error() {
        Python::with_gil(|py| {
            let dict = PyDict::new(py);
            dict.set_item("key", 42).unwrap();
            let result: PyResult<String> = require_field(dict, "key");
            assert!(result.is_err());
        });
    }

    #[test]
    fn test_require_field_none_value_returns_error() {
        Python::with_gil(|py| {
            let dict = PyDict::new(py);
            dict.set_item("key", py.None()).unwrap();
            let result: PyResult<String> = require_field(dict, "key");
            assert!(result.is_err());
        });
    }

    #[test]
    fn test_optional_field_happy_path() {
        Python::with_gil(|py| {
            let dict = PyDict::new(py);
            dict.set_item("key", "value").unwrap();
            let result: Option<String> = optional_field(dict, "key").unwrap();
            assert_eq!(result, Some("value".to_string()));
        });
    }

    #[test]
    fn test_optional_field_missing_key_returns_none() {
        Python::with_gil(|py| {
            let dict = PyDict::new(py);
            let result: Option<String> = optional_field(dict, "missing").unwrap();
            assert!(result.is_none());
        });
    }

    #[test]
    fn test_optional_field_explicit_none_returns_none() {
        Python::with_gil(|py| {
            let dict = PyDict::new(py);
            dict.set_item("key", py.None()).unwrap();
            let result: Option<String> = optional_field(dict, "key").unwrap();
            assert!(result.is_none());
        });
    }

    #[test]
    fn test_optional_field_wrong_type_returns_error() {
        Python::with_gil(|py| {
            let dict = PyDict::new(py);
            dict.set_item("key", 42).unwrap();
            let result: PyResult<Option<String>> = optional_field(dict, "key");
            assert!(result.is_err());
        });
    }
}
