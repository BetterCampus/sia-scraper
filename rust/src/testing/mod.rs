//! Mock SIA Server for Failure Pattern Analysis
//!
//! This module provides a mock HTTP server that simulates various SIA failure modes
//! to analyze retry strategies and optimize the async HTTP client.

mod analysis;
mod config;
mod server;
mod types;

pub use analysis::{AnalysisReport, FailureAnalyzer, RecommendedRetryConfig};
pub use config::FailureConfig;
pub use server::MockServer;
pub use types::{FailureMode, RequestStats};

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_failure_config_default() {
        let config = config::FailureConfig::default();
        assert!(config.validate());
    }

    #[test]
    fn test_failure_config_high_failure() {
        let config = config::FailureConfig::high_failure();
        assert!(config.validate());
    }

    #[test]
    fn test_failure_config_low_failure() {
        let config = config::FailureConfig::low_failure();
        assert!(config.validate());
    }

    #[test]
    fn test_failure_mode_transient() {
        assert!(types::FailureMode::Timeout.is_transient());
        assert!(types::FailureMode::ConnectionReset.is_transient());
        assert!(types::FailureMode::Http503.is_transient());
        assert!(!types::FailureMode::Success.is_transient());
    }

    #[test]
    fn test_request_stats() {
        let mut stats = types::RequestStats::new();
        stats.record_failure(types::FailureMode::Timeout, 1);
        stats.record_failure(types::FailureMode::Http503, 2);
        stats.record_success(1);

        assert_eq!(stats.total_requests, 3);
        assert_eq!(stats.success_rate(), 1.0 / 3.0);
    }
}
