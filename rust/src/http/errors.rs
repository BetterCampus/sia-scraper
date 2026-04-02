//! HTTP-specific error types.
//!
//! This module defines the error hierarchy for HTTP operations in the SIA scraper.
//! It provides granular error variants to enable better error handling and retry logic.

use crate::error::SiaScraperError;
use thiserror::Error;

/// HTTP error types for SIA session operations.
///
/// This enum represents all possible HTTP-related errors that can occur
/// during SIA scraping operations. Each variant represents a distinct
/// failure mode that can be handled differently by callers.
///
/// # Retry Behavior
/// Use [`HttpError::is_retryable`] to determine if an operation should be
/// retried based on the error type and configuration.
#[derive(Error, Debug, Clone)]
pub enum HttpError {
    /// Network connectivity error (DNS resolution failure, connection refused, etc.).
    ///
    /// This typically indicates transient network issues that may resolve
    /// with a retry.
    #[error("Network error: {0}")]
    NetworkError(String),

    /// HTTP response with non-success status code.
    ///
    /// Contains the HTTP status code and a descriptive message about the error.
    /// Not all HTTP errors are retryable; only 5xx errors and 429 are typically retried.
    #[error("HTTP {status}: {message}")]
    HttpStatusError {
        /// The HTTP status code (e.g., 404, 500, 503).
        status: u16,
        /// A human-readable message describing the error.
        message: String,
    },

    /// Request timed out before completing.
    ///
    /// Timeout errors are typically transient and should be retried.
    #[error("Timeout after {timeout}s during {operation}")]
    TimeoutError {
        /// The timeout value that was exceeded (in seconds).
        timeout: u64,
        /// The operation that timed out (e.g., "init_session", "post_request").
        operation: String,
    },

    /// Failed to parse response content.
    ///
    /// This indicates the response body could not be parsed as expected,
    /// possibly due to unexpected response format or encoding issues.
    #[error("Parse error: {0}")]
    ParseError(String),

    /// Invalid input provided by caller.
    ///
    /// This error indicates the caller provided invalid arguments or
    /// the operation was called in an invalid state. These errors
    /// should not be retried as they will fail the same way.
    #[error("Invalid input: {0}")]
    InvalidInput(String),

    /// Session state error (not initialized, expired, etc.).
    ///
    /// This error indicates the session is in an invalid state for
    /// the requested operation (e.g., trying to fetch courses before
    /// setting a career).
    #[error("Session error: {0}")]
    SessionError(String),
}

impl HttpError {
    /// Determines whether this error is transient and the operation should be retried.
    ///
    /// # Returns
    /// `true` if the operation that caused this error might succeed on retry,
    /// `false` if the error indicates a permanent failure that should not be retried.
    ///
    /// # Examples
    ///
    /// ```
    /// let timeout_err = HttpError::TimeoutError { timeout: 15, operation: "init_session".to_string() };
    /// assert!(timeout_err.is_retryable());
    ///
    /// let invalid_input_err = HttpError::InvalidInput("missing required field".to_string());
    /// assert!(!invalid_input_err.is_retryable());
    /// ```
    pub fn is_retryable(&self) -> bool {
        match self {
            HttpError::TimeoutError { .. } => true,
            HttpError::NetworkError(_) => true,
            HttpError::HttpStatusError { status, .. } => {
                matches!(status, 502 | 503 | 504 | 429)
            }
            HttpError::ParseError(_) => true,
            HttpError::InvalidInput(_) => false,
            HttpError::SessionError(_) => false,
        }
    }
}

impl From<reqwest::Error> for HttpError {
    /// Converts a `reqwest::Error` into an `HttpError`.
    ///
    /// This conversion uses structured error detection to map reqwest's
    /// error types to the appropriate `HttpError` variant.
    fn from(err: reqwest::Error) -> Self {
        if err.is_timeout() {
            return HttpError::TimeoutError {
                timeout: 15,
                operation: "request".to_string(),
            };
        }

        if err.is_connect() {
            return HttpError::NetworkError(err.to_string());
        }

        if let Some(status) = err.status() {
            return HttpError::HttpStatusError {
                status: status.as_u16(),
                message: err.url().map(|u| u.to_string()).unwrap_or_default(),
            };
        }

        HttpError::NetworkError(err.to_string())
    }
}

impl From<SiaScraperError> for HttpError {
    /// Converts a `SiaScraperError` into an `HttpError`.
    ///
    /// Parsing errors from the SiaScraper library are mapped to `HttpError::ParseError`.
    /// Other error types are wrapped as `HttpError::SessionError` since they typically
    /// indicate issues with the parsing or state that are relevant to the HTTP operation.
    fn from(err: SiaScraperError) -> Self {
        match err {
            SiaScraperError::ParseError(msg) => HttpError::ParseError(msg),
            SiaScraperError::XmlError(msg) => HttpError::ParseError(msg),
            SiaScraperError::ExtractionError(msg) => HttpError::SessionError(msg),
            SiaScraperError::MissingElement { element, selector } => {
                HttpError::SessionError(format!("missing element: {} at {}", element, selector))
            }
            SiaScraperError::ParseFieldError { field, value } => {
                HttpError::ParseError(format!("failed to parse {}: {}", field, value))
            }
            SiaScraperError::InvalidInput(msg) => HttpError::InvalidInput(msg),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_network_error_display() {
        let err = HttpError::NetworkError("connection refused".to_string());
        assert_eq!(err.to_string(), "Network error: connection refused");
    }

    #[test]
    fn test_http_status_error_display() {
        let err = HttpError::HttpStatusError {
            status: 404,
            message: "Not Found".to_string(),
        };
        assert_eq!(err.to_string(), "HTTP 404: Not Found");
    }

    #[test]
    fn test_timeout_error_display() {
        let err = HttpError::TimeoutError {
            timeout: 30,
            operation: "init_session".to_string(),
        };
        assert_eq!(err.to_string(), "Timeout after 30s during init_session");
    }

    #[test]
    fn test_parse_error_display() {
        let err = HttpError::ParseError("invalid XML".to_string());
        assert_eq!(err.to_string(), "Parse error: invalid XML");
    }

    #[test]
    fn test_invalid_input_display() {
        let err = HttpError::InvalidInput("empty search code".to_string());
        assert_eq!(err.to_string(), "Invalid input: empty search code");
    }

    #[test]
    fn test_session_error_display() {
        let err = HttpError::SessionError("session not initialized".to_string());
        assert_eq!(err.to_string(), "Session error: session not initialized");
    }

    #[test]
    fn test_timeout_error_is_retryable() {
        let err = HttpError::TimeoutError {
            timeout: 15,
            operation: "post_request".to_string(),
        };
        assert!(err.is_retryable());
    }

    #[test]
    fn test_network_error_is_retryable() {
        let err = HttpError::NetworkError("connection refused".to_string());
        assert!(err.is_retryable());
    }

    #[test]
    fn test_502_is_retryable() {
        let err = HttpError::HttpStatusError {
            status: 502,
            message: "Bad Gateway".to_string(),
        };
        assert!(err.is_retryable());
    }

    #[test]
    fn test_503_is_retryable() {
        let err = HttpError::HttpStatusError {
            status: 503,
            message: "Service Unavailable".to_string(),
        };
        assert!(err.is_retryable());
    }

    #[test]
    fn test_504_is_retryable() {
        let err = HttpError::HttpStatusError {
            status: 504,
            message: "Gateway Timeout".to_string(),
        };
        assert!(err.is_retryable());
    }

    #[test]
    fn test_429_is_retryable() {
        let err = HttpError::HttpStatusError {
            status: 429,
            message: "Too Many Requests".to_string(),
        };
        assert!(err.is_retryable());
    }

    #[test]
    fn test_404_is_not_retryable() {
        let err = HttpError::HttpStatusError {
            status: 404,
            message: "Not Found".to_string(),
        };
        assert!(!err.is_retryable());
    }

    #[test]
    fn test_500_is_not_retryable_by_default() {
        let err = HttpError::HttpStatusError {
            status: 500,
            message: "Internal Server Error".to_string(),
        };
        assert!(!err.is_retryable());
    }

    #[test]
    fn test_parse_error_is_retryable() {
        let err = HttpError::ParseError("malformed response".to_string());
        assert!(err.is_retryable());
    }

    #[test]
    fn test_invalid_input_is_not_retryable() {
        let err = HttpError::InvalidInput("invalid search code".to_string());
        assert!(!err.is_retryable());
    }

    #[test]
    fn test_session_error_is_not_retryable() {
        let err = HttpError::SessionError("not initialized".to_string());
        assert!(!err.is_retryable());
    }

    #[test]
    fn test_error_is_clone() {
        let err = HttpError::NetworkError("test".to_string());
        let cloned = err.clone();
        assert_eq!(err.to_string(), cloned.to_string());
    }

    #[test]
    fn test_from_sia_scraper_parse_error() {
        let sia_err = SiaScraperError::ParseError("parse failed".to_string());
        let http_err: HttpError = sia_err.into();
        match http_err {
            HttpError::ParseError(msg) => {
                assert_eq!(msg, "parse failed");
            }
            _ => panic!("Expected ParseError"),
        }
    }

    #[test]
    fn test_from_sia_scraper_invalid_input() {
        let sia_err = SiaScraperError::InvalidInput("bad input".to_string());
        let http_err: HttpError = sia_err.into();
        match http_err {
            HttpError::InvalidInput(msg) => {
                assert_eq!(msg, "bad input");
            }
            _ => panic!("Expected InvalidInput"),
        }
    }

    #[test]
    fn test_from_sia_scraper_missing_element() {
        let sia_err = SiaScraperError::MissingElement {
            element: "ViewState".to_string(),
            selector: "input[name=javax.faces.ViewState]".to_string(),
        };
        let http_err: HttpError = sia_err.into();
        match http_err {
            HttpError::SessionError(msg) => {
                assert!(msg.contains("ViewState"));
            }
            _ => panic!("Expected SessionError"),
        }
    }

    #[test]
    fn test_from_sia_scraper_parse_field_error() {
        let sia_err = SiaScraperError::ParseFieldError {
            field: "course_code".to_string(),
            value: "invalid".to_string(),
        };
        let http_err: HttpError = sia_err.into();
        match http_err {
            HttpError::ParseError(msg) => {
                assert!(msg.contains("course_code"));
            }
            _ => panic!("Expected ParseError"),
        }
    }
}
