//! Failure configuration for mock SIA server.

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FailureConfig {
    pub timeout_rate: f64,
    pub connection_reset_rate: f64,
    pub http_503_rate: f64,
    pub http_502_rate: f64,
    pub http_429_rate: f64,
    pub http_504_rate: f64,
    pub success_rate: f64,
}

impl Default for FailureConfig {
    fn default() -> Self {
        Self {
            timeout_rate: 0.20,
            connection_reset_rate: 0.10,
            http_503_rate: 0.15,
            http_502_rate: 0.05,
            http_429_rate: 0.05,
            http_504_rate: 0.05,
            success_rate: 0.40,
        }
    }
}

impl FailureConfig {
    pub fn high_failure() -> Self {
        Self {
            timeout_rate: 0.30,
            connection_reset_rate: 0.15,
            http_503_rate: 0.20,
            http_502_rate: 0.10,
            http_429_rate: 0.05,
            http_504_rate: 0.10,
            success_rate: 0.10,
        }
    }

    pub fn low_failure() -> Self {
        Self {
            timeout_rate: 0.05,
            connection_reset_rate: 0.02,
            http_503_rate: 0.03,
            http_502_rate: 0.01,
            http_429_rate: 0.02,
            http_504_rate: 0.02,
            success_rate: 0.85,
        }
    }

    pub fn validate(&self) -> bool {
        let total = self.timeout_rate
            + self.connection_reset_rate
            + self.http_503_rate
            + self.http_502_rate
            + self.http_429_rate
            + self.http_504_rate
            + self.success_rate;

        (total - 1.0).abs() < 0.001
    }
}
