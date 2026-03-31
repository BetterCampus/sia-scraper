//! Async SIA Session manager with retry logic.

use std::sync::Arc;
use tokio::sync::RwLock;
use tokio::time::sleep;

use crate::http::client::AsyncHttpClient;
use crate::http::config::HttpClientConfig;
use crate::http::errors::HttpError;
use crate::http::retry::{calculate_delay, should_retry, RetryConfig};
use crate::http::session::SessionState;
use crate::http::types::HttpResponse;

pub struct SiaSession {
    client: AsyncHttpClient,
    state: Arc<RwLock<SessionState>>,
    base_url: String,
    retry_config: RetryConfig,
}

impl SiaSession {
    pub fn new(timeout_secs: u64, base_url: String) -> Result<Self, HttpError> {
        Self::with_retry_config(timeout_secs, base_url, RetryConfig::sia_optimized())
    }

    pub fn with_retry_config(
        timeout_secs: u64,
        base_url: String,
        retry_config: RetryConfig,
    ) -> Result<Self, HttpError> {
        let config = HttpClientConfig::sia_default().with_timeout(timeout_secs);
        let client = AsyncHttpClient::with_config(config)?;

        Ok(Self {
            client,
            state: Arc::new(RwLock::new(SessionState::default())),
            base_url,
            retry_config,
        })
    }

    pub async fn init_session(&self) -> Result<(), HttpError> {
        let mut last_error: Option<HttpError> = None;

        for attempt in 1..=self.retry_config.max_attempts {
            match self.do_init_session().await {
                Ok(()) => return Ok(()),
                Err(e) => {
                    last_error = Some(e.clone());
                    if !should_retry(&e, &self.retry_config) || attempt == self.retry_config.max_attempts
                    {
                        return Err(e);
                    }
                    let delay = calculate_delay(attempt, &self.retry_config);
                    sleep(delay).await;
                }
            }
        }

        Err(last_error.unwrap_or(HttpError::ConnectionFailed(
            "Unknown error".to_string(),
        )))
    }

    async fn do_init_session(&self) -> Result<(), HttpError> {
        let resp = self.client.get(&self.base_url).await?;
        resp.raise_for_status()?;

        if let Ok(view_state) = crate::parsers::adf::extract_view_state(&resp.body) {
            let mut state = self.state.write().await;
            state.update_view_state(view_state);
            state.set_status("SESSION_SET");
        }

        Ok(())
    }

    pub async fn post_request(&self, body: &str) -> Result<HttpResponse, HttpError> {
        let mut last_error: Option<HttpError> = None;

        for attempt in 1..=self.retry_config.max_attempts {
            match self.do_post_request(body).await {
                Ok(resp) => return Ok(resp),
                Err(e) => {
                    last_error = Some(e.clone());
                    if !should_retry(&e, &self.retry_config) || attempt == self.retry_config.max_attempts
                    {
                        return Err(e);
                    }
                    let delay = calculate_delay(attempt, &self.retry_config);
                    sleep(delay).await;
                }
            }
        }

        Err(last_error.unwrap_or(HttpError::ConnectionFailed(
            "Unknown error".to_string(),
        )))
    }

    async fn do_post_request(&self, body: &str) -> Result<HttpResponse, HttpError> {
        let resp = self.client.post(&self.base_url, body).await?;

        if let Ok(view_state) = crate::parsers::adf::extract_view_state(&resp.body) {
            let mut state = self.state.write().await;
            state.update_view_state(view_state);
        }

        Ok(resp)
    }

    pub async fn get_state(&self) -> SessionState {
        self.state.read().await.clone()
    }

    pub async fn update_state(&self, state: SessionState) {
        *self.state.write().await = state;
    }

    pub fn base_url(&self) -> &str {
        &self.base_url
    }

    pub fn retry_config(&self) -> &RetryConfig {
        &self.retry_config
    }
}

impl Default for SiaSession {
    fn default() -> Self {
        Self::new(
            15,
            "https://sia.unal.edu.co/Catalogo/facespublico/public/servicioPublico.jsf".to_string(),
        )
        .unwrap()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_session_creation() {
        let session = SiaSession::new(15, "https://httpbin.org".to_string());
        assert!(session.is_ok());
    }

    #[tokio::test]
    async fn test_default_session() {
        let session = SiaSession::default();
        let state = session.get_state().await;
        assert_eq!(state.status, "CREATED");
    }

    #[tokio::test]
    async fn test_session_with_custom_retry() {
        let config = RetryConfig::default().with_max_attempts(5);
        let session = SiaSession::with_retry_config(15, "https://httpbin.org".to_string(), config);
        assert!(session.is_ok());
        assert_eq!(session.unwrap().retry_config().max_attempts, 5);
    }
}
