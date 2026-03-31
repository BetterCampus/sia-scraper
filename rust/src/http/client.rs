//! Async HTTP client wrapper with connection pooling.

use std::time::Duration;

use crate::http::{config::HttpClientConfig, errors::HttpError, types::HttpResponse};

pub struct AsyncHttpClient {
    client: reqwest::Client,
    config: HttpClientConfig,
}

impl AsyncHttpClient {
    pub fn with_config(config: HttpClientConfig) -> Result<Self, HttpError> {
        let timeout = Duration::from_secs(config.timeout_secs);
        let connect_timeout = Duration::from_secs(config.connect_timeout_secs);
        let pool_idle_timeout = Duration::from_secs(config.pool_idle_timeout_secs);

        let mut builder = reqwest::Client::builder()
            .timeout(timeout)
            .connect_timeout(connect_timeout)
            .redirect(reqwest::redirect::Policy::limited(config.max_redirects))
            .user_agent(&config.user_agent)
            .cookie_store(config.enable_cookies)
            .pool_idle_timeout(pool_idle_timeout)
            .pool_max_idle_per_host(config.pool_max_idle_per_host);

        builder = match config.tls_backend {
            crate::http::config::TlsBackend::NativeCerts => {
                builder.use_rustls_tls()
            }
            crate::http::config::TlsBackend::WebPkiRoots => {
                builder.use_rustls_tls()
            }
        };

        let client = builder
            .build()
            .map_err(|e: reqwest::Error| HttpError::from(e))?;

        Ok(Self { client, config })
    }

    pub fn new(timeout_secs: u64, _base_url: String) -> Result<Self, HttpError> {
        let mut config = HttpClientConfig::sia_default();
        config.timeout_secs = timeout_secs;
        Self::with_config(config)
    }

    pub async fn get(&self, url: &str) -> Result<HttpResponse, HttpError> {
        let resp = self.client.get(url).send().await?;
        HttpResponse::from_reqwest(resp).await
    }

    pub async fn post(&self, url: &str, body: &str) -> Result<HttpResponse, HttpError> {
        let resp = self
            .client
            .post(url)
            .header("Content-Type", "application/x-www-form-urlencoded")
            .body(body.to_string())
            .send()
            .await?;
        HttpResponse::from_reqwest(resp).await
    }

    pub async fn post_with_headers(
        &self,
        url: &str,
        body: &str,
        headers: &[(&str, &str)],
    ) -> Result<HttpResponse, HttpError> {
        let mut req = self.client.post(url);
        for (key, value) in headers {
            req = req.header(*key, *value);
        }
        let resp = req
            .body(body.to_string())
            .send()
            .await?;
        HttpResponse::from_reqwest(resp).await
    }

    pub fn config(&self) -> &HttpClientConfig {
        &self.config
    }

    pub fn timeout(&self) -> u64 {
        self.config.timeout_secs
    }
}

impl Default for AsyncHttpClient {
    fn default() -> Self {
        Self::new(15, String::new()).unwrap()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::http::config::TlsBackend;

    #[tokio::test]
    async fn test_client_with_default_config() {
        let config = HttpClientConfig::default();
        let client = AsyncHttpClient::with_config(config);
        assert!(client.is_ok());
    }

    #[tokio::test]
    async fn test_client_with_sia_config() {
        let config = HttpClientConfig::sia_default();
        let client = AsyncHttpClient::with_config(config);
        assert!(client.is_ok());
    }

    #[tokio::test]
    async fn test_client_timeout() {
        let config = HttpClientConfig::default().with_timeout(30);
        let client = AsyncHttpClient::with_config(config).unwrap();
        assert_eq!(client.timeout(), 30);
    }

    #[tokio::test]
    async fn test_get_request() {
        let client = AsyncHttpClient::new(15, "https://httpbin.org".to_string()).unwrap();
        let resp = client.get("https://httpbin.org/get").await;
        assert!(resp.is_ok());
        let resp = resp.unwrap();
        assert_eq!(resp.status, 200);
    }

    #[tokio::test]
    async fn test_post_request() {
        let client = AsyncHttpClient::new(15, "https://httpbin.org".to_string()).unwrap();
        let resp = client.post("https://httpbin.org/post", "test=value").await;
        assert!(resp.is_ok());
        let resp = resp.unwrap();
        assert_eq!(resp.status, 200);
    }
}
