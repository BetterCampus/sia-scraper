//! HTTP-specific error types.

use thiserror::Error;

#[derive(Error, Debug, Clone)]
pub enum HttpError {
    #[error("Request timeout after {timeout}s")]
    Timeout { timeout: u64 },

    #[error("Connection failed: {0}")]
    ConnectionFailed(String),

    #[error("Invalid input: {0}")]
    InvalidInput(String),

    #[error("HTTP {status}: {url:?}")]
    HttpStatus { status: u16, url: Option<String> },

    #[error("Response parsing error: {0}")]
    ParseError(String),
}

impl From<reqwest::Error> for HttpError {
    fn from(err: reqwest::Error) -> Self {
        // Use structured error detection instead of substring matching
        if err.is_timeout() {
            return HttpError::Timeout { timeout: 15 };
        }

        if err.is_connect() {
            return HttpError::ConnectionFailed(err.to_string());
        }

        if let Some(status) = err.status() {
            return HttpError::HttpStatus {
                status: status.as_u16(),
                url: err.url().map(|u| u.to_string()),
            };
        }

        HttpError::ConnectionFailed(err.to_string())
    }
}
