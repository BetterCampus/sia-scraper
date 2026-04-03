//! Retry configuration and logic for HTTP requests.

use rand::Rng;
use serde::{Deserialize, Serialize};
use std::time::Duration;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RetryConfig {
    pub max_attempts: u32,
    pub initial_delay_ms: u64,
    pub max_delay_ms: u64,
    pub jitter_factor: f64,
    pub retry_on_timeout: bool,
    pub retry_on_connection_error: bool,
    pub retry_on_status: Vec<u16>,
}

impl Default for RetryConfig {
    fn default() -> Self {
        Self {
            max_attempts: 3,
            initial_delay_ms: 1000,
            max_delay_ms: 8000,
            jitter_factor: 0.20,
            retry_on_timeout: true,
            retry_on_connection_error: true,
            retry_on_status: vec![502, 503, 504, 429],
        }
    }
}

impl RetryConfig {
    pub fn sia_optimized() -> Self {
        Self {
            max_attempts: 4,
            initial_delay_ms: 800,
            max_delay_ms: 6000,
            jitter_factor: 0.25,
            retry_on_timeout: true,
            retry_on_connection_error: true,
            retry_on_status: vec![502, 503, 504, 429],
        }
    }

    pub fn with_max_attempts(mut self, attempts: u32) -> Self {
        self.max_attempts = attempts;
        self
    }

    #[cfg(test)]
    pub fn with_initial_delay(mut self, delay_ms: u64) -> Self {
        self.initial_delay_ms = delay_ms;
        self
    }

    #[cfg(test)]
    pub fn with_max_delay(mut self, delay_ms: u64) -> Self {
        self.max_delay_ms = delay_ms;
        self
    }

    #[cfg(test)]
    pub fn with_jitter(mut self, factor: f64) -> Self {
        self.jitter_factor = factor;
        self
    }
}

pub fn calculate_delay(attempt: u32, config: &RetryConfig) -> Duration {
    let exponent = attempt.saturating_sub(1);
    let base_delay = config.initial_delay_ms * (2_u64.pow(exponent));
    let delay = base_delay.min(config.max_delay_ms);

    let jitter_range = (delay as f64 * config.jitter_factor) as i64;
    let mut rng = rand::thread_rng();
    let jitter: i64 = rng.gen_range(-jitter_range..=jitter_range);

    let final_delay = ((delay as i64) + jitter).max(100) as u64;
    Duration::from_millis(final_delay)
}

pub fn should_retry(error: &crate::http::errors::HttpError, config: &RetryConfig) -> bool {
    match error {
        crate::http::errors::HttpError::TimeoutError { .. } => config.retry_on_timeout,
        crate::http::errors::HttpError::NetworkError(_) => config.retry_on_connection_error,
        crate::http::errors::HttpError::HttpStatusError { status, .. } => {
            config.retry_on_status.contains(status)
        }
        crate::http::errors::HttpError::ParseError(_) => true,
        crate::http::errors::HttpError::InvalidInput(_) => false,
        crate::http::errors::HttpError::SessionError(_) => false,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_config() {
        let config = RetryConfig::default();
        assert_eq!(config.max_attempts, 3);
    }

    #[test]
    fn test_sia_optimized_config() {
        let config = RetryConfig::sia_optimized();
        assert_eq!(config.max_attempts, 4);
        assert_eq!(config.initial_delay_ms, 800);
    }

    #[test]
    fn test_should_retry_timeout() {
        let config = RetryConfig::default();
        let error = crate::http::errors::HttpError::TimeoutError {
            timeout: 15,
            operation: "request".to_string(),
        };
        assert!(should_retry(&error, &config));
    }

    #[test]
    fn test_should_retry_503() {
        let config = RetryConfig::default();
        let error = crate::http::errors::HttpError::HttpStatusError {
            status: 503,
            message: "test".to_string(),
        };
        assert!(should_retry(&error, &config));
    }

    #[test]
    fn test_should_not_retry_400() {
        let config = RetryConfig::default();
        let error = crate::http::errors::HttpError::HttpStatusError {
            status: 400,
            message: "test".to_string(),
        };
        assert!(!should_retry(&error, &config));
    }

    #[test]
    fn test_calculate_delay() {
        let config = RetryConfig::default()
            .with_initial_delay(1000)
            .with_max_delay(8000)
            .with_jitter(0.20);
        let delay = calculate_delay(1, &config);
        assert!(delay.as_millis() >= 800);
    }
}
