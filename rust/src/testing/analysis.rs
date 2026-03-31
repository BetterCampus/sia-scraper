//! Failure pattern analyzer for testing retry strategies.

use crate::testing::types::{FailureMode, RequestStats};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnalysisReport {
    pub total_requests: u64,
    pub success_count: u64,
    pub failure_count: u64,
    pub success_rate: f64,
    pub retry_success_rate: f64,
    pub avg_attempts: f64,
    pub failure_distribution: std::collections::HashMap<String, f64>,
    pub retry_distribution: std::collections::HashMap<String, f64>,
    pub latency_p50_ms: u64,
    pub latency_p95_ms: u64,
    pub latency_p99_ms: u64,
    pub recommended_config: RecommendedRetryConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RecommendedRetryConfig {
    pub max_attempts: u8,
    pub initial_delay_ms: u64,
    pub max_delay_ms: u64,
    pub jitter_factor: f64,
    pub rationale: String,
}

pub struct FailureAnalyzer;

impl FailureAnalyzer {
    pub fn analyze(stats: &RequestStats) -> AnalysisReport {
        let failure_distribution: std::collections::HashMap<String, f64> = stats
            .failures_by_mode
            .iter()
            .map(|(k, v)| {
                let rate = if stats.total_requests > 0 {
                    *v as f64 / stats.total_requests as f64
                } else {
                    0.0
                };
                (k.clone(), rate)
            })
            .collect();

        let retry_distribution: std::collections::HashMap<String, f64> = stats
            .retry_counts
            .iter()
            .map(|(k, v)| {
                let rate = if stats.total_requests > 0 {
                    *v as f64 / stats.total_requests as f64
                } else {
                    0.0
                };
                (format!("attempt_{}", k), rate)
            })
            .collect();

        let recommended_config = Self::calculate_recommended_config(stats);

        AnalysisReport {
            total_requests: stats.total_requests,
            success_count: stats.failures_by_mode.get("success").copied().unwrap_or(0),
            failure_count: stats.total_requests
                - stats.failures_by_mode.get("success").copied().unwrap_or(0),
            success_rate: stats.success_rate(),
            retry_success_rate: stats.retry_success_rate(),
            avg_attempts: stats.avg_attempts(),
            failure_distribution,
            retry_distribution,
            latency_p50_ms: stats.p50_duration(),
            latency_p95_ms: stats.p95_duration(),
            latency_p99_ms: stats.p99_duration(),
            recommended_config,
        }
    }

    fn calculate_recommended_config(stats: &RequestStats) -> RecommendedRetryConfig {
        let mut max_attempts = 3u8;
        let mut initial_delay_ms = 1000u64;
        let mut max_delay_ms = 8000u64;
        let mut jitter_factor = 0.20f64;
        let mut rationale = String::new();

        if stats.total_requests == 0 {
            return RecommendedRetryConfig {
                max_attempts,
                initial_delay_ms,
                max_delay_ms,
                jitter_factor,
                rationale: "No data collected yet".to_string(),
            };
        }

        let attempt_4_count = stats.retry_counts.get(&4).copied().unwrap_or(0);
        let attempt_3_count = stats.retry_counts.get(&3).copied().unwrap_or(0);
        let attempt_2_count = stats.retry_counts.get(&2).copied().unwrap_or(0);

        let attempt_4_rate = attempt_4_count as f64 / stats.total_requests as f64;
        let attempt_3_rate = attempt_3_count as f64 / stats.total_requests as f64;
        let _attempt_2_rate = attempt_2_count as f64 / stats.total_requests as f64;

        if attempt_4_rate > 0.10 {
            max_attempts = 4;
            rationale.push_str("Increased to 4 attempts due to >10% success on 4th retry. ");
        }

        if attempt_3_rate > 0.20 {
            initial_delay_ms = 800;
            rationale.push_str("Reduced initial delay to 800ms for faster recovery. ");
        }

        let total_transient = stats
            .failures_by_mode
            .iter()
            .filter(|(k, _)| {
                let mode = match k.as_str() {
                    "timeout" => FailureMode::Timeout,
                    "connection_reset" => FailureMode::ConnectionReset,
                    "http_503" => FailureMode::Http503,
                    "http_502" => FailureMode::Http502,
                    "http_429" => FailureMode::Http429,
                    "http_504" => FailureMode::Http504,
                    _ => FailureMode::Success,
                };
                mode.is_transient()
            })
            .map(|(_, v)| *v)
            .sum::<u64>() as f64;

        let transient_rate = total_transient / stats.total_requests as f64;

        if transient_rate > 0.30 {
            max_delay_ms = 6000;
            jitter_factor = 0.25;
            rationale.push_str(
                "High transient failure rate (>30%) - increased jitter to reduce thundering herd. ",
            );
        }

        if rationale.is_empty() {
            rationale = "Default configuration recommended based on typical SIA failure patterns."
                .to_string();
        }

        RecommendedRetryConfig {
            max_attempts,
            initial_delay_ms,
            max_delay_ms,
            jitter_factor,
            rationale,
        }
    }

    pub fn generate_report_json(stats: &RequestStats) -> String {
        let report = Self::analyze(stats);
        serde_json::to_string_pretty(&report).unwrap_or_default()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_analyze_empty_stats() {
        let stats = RequestStats::new();
        let report = FailureAnalyzer::analyze(&stats);

        assert_eq!(report.total_requests, 0);
        assert_eq!(report.success_rate, 0.0);
    }

    #[test]
    fn test_analyze_with_data() {
        let mut stats = RequestStats::new();
        stats.record_failure(FailureMode::Timeout, 1);
        stats.record_failure(FailureMode::Http503, 1);
        stats.record_success(1);
        stats.record_success(2);
        stats.record_success(3);

        let report = FailureAnalyzer::analyze(&stats);

        assert_eq!(report.total_requests, 5);
        assert_eq!(report.success_count, 3);
        assert!(report.success_rate > 0.0);
    }

    #[test]
    fn test_recommended_config_4_attempts() {
        let mut stats = RequestStats::new();
        for _ in 0..100 {
            stats.record_failure(FailureMode::Http503, 1);
            stats.record_failure(FailureMode::Http503, 2);
            stats.record_failure(FailureMode::Http503, 3);
            stats.record_failure(FailureMode::Http503, 4);
        }

        let report = FailureAnalyzer::analyze(&stats);

        assert_eq!(report.recommended_config.max_attempts, 4);
    }
}
