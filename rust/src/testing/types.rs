//! Failure mode types and request statistics.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum FailureMode {
    Timeout,
    ConnectionReset,
    Http503,
    Http502,
    Http429,
    Http504,
    Success,
}

impl FailureMode {
    pub fn is_transient(&self) -> bool {
        matches!(
            self,
            FailureMode::Timeout
                | FailureMode::ConnectionReset
                | FailureMode::Http503
                | FailureMode::Http502
                | FailureMode::Http429
                | FailureMode::Http504
        )
    }

    pub fn status_code(&self) -> Option<u16> {
        match self {
            FailureMode::Http503 => Some(503),
            FailureMode::Http502 => Some(502),
            FailureMode::Http429 => Some(429),
            FailureMode::Http504 => Some(504),
            _ => None,
        }
    }
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct RequestStats {
    pub total_requests: u64,
    pub failures_by_mode: HashMap<String, u64>,
    pub successful_retries: u64,
    pub failed_after_retries: u64,
    pub retry_counts: HashMap<u8, u64>,
    pub request_durations_ms: Vec<u64>,
}

impl RequestStats {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn record_failure(&mut self, mode: FailureMode, attempt: u8) {
        self.total_requests += 1;
        let mode_name = format!("{:?}", mode).to_lowercase();
        *self.failures_by_mode.entry(mode_name).or_insert(0) += 1;

        if attempt > 1 {
            self.successful_retries += 1;
        } else {
            self.failed_after_retries += 1;
        }

        *self.retry_counts.entry(attempt).or_insert(0) += 1;
    }

    pub fn record_success(&mut self, attempts: u8) {
        self.total_requests += 1;
        let mode_name = "success".to_string();
        *self.failures_by_mode.entry(mode_name).or_insert(0) += 1;
        *self.retry_counts.entry(attempts).or_insert(0) += 1;
    }

    pub fn record_duration(&mut self, duration_ms: u64) {
        self.request_durations_ms.push(duration_ms);
    }

    pub fn success_rate(&self) -> f64 {
        let success = self.failures_by_mode.get("success").copied().unwrap_or(0);
        if self.total_requests == 0 {
            return 0.0;
        }
        success as f64 / self.total_requests as f64
    }

    pub fn retry_success_rate(&self) -> f64 {
        if self.successful_retries + self.failed_after_retries == 0 {
            return 0.0;
        }
        self.successful_retries as f64
            / (self.successful_retries + self.failed_after_retries) as f64
    }

    pub fn avg_attempts(&self) -> f64 {
        if self.total_requests == 0 {
            return 0.0;
        }
        let total_attempts: u64 = self
            .retry_counts
            .iter()
            .map(|(attempt, count)| (*attempt as u64) * count)
            .sum();
        total_attempts as f64 / self.total_requests as f64
    }

    pub fn p50_duration(&self) -> u64 {
        if self.request_durations_ms.is_empty() {
            return 0;
        }
        let mut sorted = self.request_durations_ms.clone();
        sorted.sort();
        let idx = sorted.len() / 2;
        sorted[idx]
    }

    pub fn p95_duration(&self) -> u64 {
        if self.request_durations_ms.is_empty() {
            return 0;
        }
        let mut sorted = self.request_durations_ms.clone();
        sorted.sort();
        let idx = (sorted.len() as f64 * 0.95) as usize;
        sorted[idx.min(sorted.len() - 1)]
    }

    pub fn p99_duration(&self) -> u64 {
        if self.request_durations_ms.is_empty() {
            return 0;
        }
        let mut sorted = self.request_durations_ms.clone();
        sorted.sort();
        let idx = (sorted.len() as f64 * 0.99) as usize;
        sorted[idx.min(sorted.len() - 1)]
    }
}
