//! HTTP client configuration.

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HttpClientConfig {
    pub timeout_secs: u64,
    pub connect_timeout_secs: u64,
    pub max_redirects: usize,
    pub user_agent: String,
    pub enable_cookies: bool,
    pub pool_idle_timeout_secs: u64,
    pub pool_max_idle_per_host: usize,
}

impl Default for HttpClientConfig {
    fn default() -> Self {
        Self {
            timeout_secs: 15,
            connect_timeout_secs: 5,
            max_redirects: 10,
            user_agent: "sia-scraper/2.0".to_string(),
            enable_cookies: true,
            pool_idle_timeout_secs: 90,
            pool_max_idle_per_host: 16,
        }
    }
}

impl HttpClientConfig {
    pub fn sia_default() -> Self {
        Self {
            timeout_secs: 15,
            connect_timeout_secs: 5,
            max_redirects: 10,
            user_agent: "sia-scraper/2.0".to_string(),
            enable_cookies: true,
            pool_idle_timeout_secs: 90,
            pool_max_idle_per_host: 16,
        }
    }

    pub fn with_timeout(mut self, timeout_secs: u64) -> Self {
        self.timeout_secs = timeout_secs;
        self
    }

    pub fn with_connect_timeout(mut self, timeout_secs: u64) -> Self {
        self.connect_timeout_secs = timeout_secs;
        self
    }

    pub fn with_user_agent(mut self, user_agent: &str) -> Self {
        self.user_agent = user_agent.to_string();
        self
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_config() {
        let config = HttpClientConfig::default();
        assert_eq!(config.timeout_secs, 15);
    }

    #[test]
    fn test_sia_default_config() {
        let config = HttpClientConfig::sia_default();
        assert_eq!(config.timeout_secs, 15);
        assert!(config.enable_cookies);
    }

    #[test]
    fn test_config_builder() {
        let config = HttpClientConfig::default()
            .with_timeout(30)
            .with_connect_timeout(10);

        assert_eq!(config.timeout_secs, 30);
        assert_eq!(config.connect_timeout_secs, 10);
    }
}
