//! Async SIA Session manager.

use std::sync::Arc;
use tokio::sync::RwLock;

use crate::http::client::AsyncHttpClient;
use crate::http::config::HttpClientConfig;
use crate::http::errors::HttpError;
use crate::http::session::SessionState;
use crate::http::HttpResponse;

pub struct SiaSession {
    client: AsyncHttpClient,
    state: Arc<RwLock<SessionState>>,
    base_url: String,
}

impl SiaSession {
    pub fn new(timeout_secs: u64, base_url: String) -> Result<Self, HttpError> {
        let config = HttpClientConfig::sia_default().with_timeout(timeout_secs);
        let client = AsyncHttpClient::with_config(config)?;
        
        Ok(Self {
            client,
            state: Arc::new(RwLock::new(SessionState::default())),
            base_url,
        })
    }

    pub async fn init_session(&self) -> Result<(), HttpError> {
        let resp = self.client.get(&self.base_url).await?;
        resp.raise_for_status()?;
        
        // Extract ViewState from response
        if let Ok(view_state) = crate::parsers::adf::extract_view_state(&resp.body) {
            let mut state = self.state.write().await;
            state.update_view_state(view_state);
            state.set_status("SESSION_SET");
        }
        
        Ok(())
    }

    pub async fn post_request(&self, body: &str) -> Result<HttpResponse, HttpError> {
        let resp = self.client.post(&self.base_url, body).await?;
        
        // Auto-sync ViewState
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
}

impl Default for SiaSession {
    fn default() -> Self {
        Self::new(
            15,
            "https://sia.unal.edu.co/Catalogo/facespublico/public/servicioPublico.jsf".to_string(),
        ).unwrap()
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
}
