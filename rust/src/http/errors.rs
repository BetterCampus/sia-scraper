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
        let error_str = err.to_string();

        // Check for timeout in error message (reqwest 0.12+)
        if error_str.contains("timeout") || error_str.contains("timed out") {
            return HttpError::Timeout { timeout: 15 };
        }

        if err.is_connect() {
            return HttpError::ConnectionFailed(error_str);
        }

        if let Some(status) = err.status() {
            return HttpError::HttpStatus {
                status: status.as_u16(),
                url: err.url().map(|u| u.to_string()).unwrap_or_default(),
            };
        }

        HttpError::ConnectionFailed(error_str)
    }
}

pub type HttpResult<T> = Result<T, HttpError>;
