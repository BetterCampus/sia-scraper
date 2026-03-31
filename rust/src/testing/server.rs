//! Mock SIA Server for Failure Pattern Analysis
//!
//! This module provides utilities to simulate various SIA failure modes.
//! The actual mock HTTP server is implemented in Python for easier iteration.

use crate::testing::config::FailureConfig;
use crate::testing::types::FailureMode;
use rand::Rng;

pub struct MockServer {
    config: FailureConfig,
    request_count: u64,
}

impl MockServer {
    pub fn new(config: FailureConfig) -> Self {
        Self {
            config,
            request_count: 0,
        }
    }

    pub fn select_failure_mode(&self) -> FailureMode {
        let mut rng = rand::thread_rng();
        let r: f64 = rng.gen();

        let mut cumulative = 0.0;

        cumulative += self.config.timeout_rate;
        if r < cumulative {
            return FailureMode::Timeout;
        }

        cumulative += self.config.connection_reset_rate;
        if r < cumulative {
            return FailureMode::ConnectionReset;
        }

        cumulative += self.config.http_503_rate;
        if r < cumulative {
            return FailureMode::Http503;
        }

        cumulative += self.config.http_502_rate;
        if r < cumulative {
            return FailureMode::Http502;
        }

        cumulative += self.config.http_429_rate;
        if r < cumulative {
            return FailureMode::Http429;
        }

        cumulative += self.config.http_504_rate;
        if r < cumulative {
            return FailureMode::Http504;
        }

        FailureMode::Success
    }

    pub fn increment_request_count(&mut self) {
        self.request_count += 1;
    }

    pub fn get_request_count(&self) -> u64 {
        self.request_count
    }
}

impl Default for MockServer {
    fn default() -> Self {
        Self::new(FailureConfig::default())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_select_failure_mode() {
        let server = MockServer::default();
        for _ in 0..100 {
            let mode = server.select_failure_mode();
            assert!(matches!(
                mode,
                FailureMode::Timeout
                    | FailureMode::ConnectionReset
                    | FailureMode::Http503
                    | FailureMode::Http502
                    | FailureMode::Http429
                    | FailureMode::Http504
                    | FailureMode::Success
            ));
        }
    }

    #[test]
    fn test_custom_config() {
        let config = FailureConfig {
            timeout_rate: 1.0,
            connection_reset_rate: 0.0,
            http_503_rate: 0.0,
            http_502_rate: 0.0,
            http_429_rate: 0.0,
            http_504_rate: 0.0,
            success_rate: 0.0,
        };
        let server = MockServer::new(config);

        for _ in 0..100 {
            let mode = server.select_failure_mode();
            assert_eq!(mode, FailureMode::Timeout);
        }
    }
}
