//! HTTP-specific error types.

use thiserror::Error;

#[derive(Error, Debug)]
pub enum HttpError {
    #[error("Request timeout after {timeout}s")]
    Timeout { timeout: u64 },

    #[error("Connection failed: {0}")]
    ConnectionFailed(String),

    #[error("HTTP {status}: {url}")]
    HttpStatus { status: u16, url: String },

    #[error("TLS error: {0}")]
    TlsError(String),

    #[error("Invalid request: {0}")]
    InvalidRequest(String),

    #[error("Response parsing error: {0}")]
    ParseError(String),
}

impl From<reqwest::Error> for HttpError {
    fn from(err: reqwest::Error) -> Self {
        if err.is_timeout() {
            HttpError::Timeout {
                timeout: 15, // Default, actual timeout not exposed by reqwest
            }
        } else if err.is_connect() {
            HttpError::ConnectionFailed(err.to_string())
        } else if let Some(status) = err.status() {
            HttpError::HttpStatus {
                status: status.as_u16(),
                url: err.url().map(|u| u.to_string()).unwrap_or_default(),
            }
        } else {
            HttpError::ConnectionFailed(err.to_string())
        }
    }
}

pub type HttpResult<T> = Result<T, HttpError>;
