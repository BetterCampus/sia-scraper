//! Async HTTP client wrapper.

use std::time::Duration;
use std::sync::Arc;
use tokio::sync::RwLock;

use crate::http::{errors::HttpError, types::HttpResponse};

pub struct AsyncHttpClient {
    client: reqwest::Client,
    timeout: Duration,
    base_url: String,
}

impl AsyncHttpClient {
    pub fn new(timeout_secs: u64, base_url: String) -> Result<Self, HttpError> {
        let timeout = Duration::from_secs(timeout_secs);
        
        let client = reqwest::Client::builder()
            .timeout(timeout)
            .cookie_store(true)
            .use_rustls_tls()
            .build()
            .map_err(|e| HttpError::ConnectionFailed(e.to_string()))?;

        Ok(Self {
            client,
            timeout,
            base_url,
        })
    }

    pub async fn get(&self, url: &str) -> Result<HttpResponse, HttpError> {
        let resp = self.client.get(url).send().await?;
        HttpResponse::from_reqwest(resp).await
    }

    pub async fn post(&self, url: &str, body: &str) -> Result<HttpResponse, HttpError> {
        let resp = self.client
            .post(url)
            .header("Content-Type", "application/x-www-form-urlencoded")
            .body(body.to_string())
            .send()
            .await?;
        HttpResponse::from_reqwest(resp).await
    }

    pub fn base_url(&self) -> &str {
        &self.base_url
    }
}

pub type AsyncHttpClientHandle = Arc<RwLock<AsyncHttpClient>>;

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_client_creation() {
        let client = AsyncHttpClient::new(15, "https://httpbin.org".to_string());
        assert!(client.is_ok());
    }

    #[tokio::test]
    async fn test_get_request() {
        let client = AsyncHttpClient::new(15, "https://httpbin.org".to_string()).unwrap();
        let resp = client.get("/get").await;
        assert!(resp.is_ok());
        let resp = resp.unwrap();
        assert_eq!(resp.status, 200);
    }

    #[tokio::test]
    async fn test_post_request() {
        let client = AsyncHttpClient::new(15, "https://httpbin.org".to_string()).unwrap();
        let resp = client.post("/post", "test=value").await;
        assert!(resp.is_ok());
        let resp = resp.unwrap();
        assert_eq!(resp.status, 200);
    }
}
