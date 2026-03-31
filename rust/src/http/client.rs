//! Async HTTP client wrapper with connection pooling.

use std::time::Duration;

use crate::http::{config::HttpClientConfig, errors::HttpError, types::HttpResponse};

pub struct AsyncHttpClient {
    client: reqwest::Client,
    #[cfg(test)]
    timeout_secs: u64,
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

        let client = builder.build().map_err(HttpError::from)?;

        Ok(Self {
            client,
            #[cfg(test)]
            timeout_secs: config.timeout_secs,
        })
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

    #[cfg(test)]
    pub fn timeout(&self) -> u64 {
        self.timeout_secs
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
    use std::io::{Read, Write};
    use std::net::TcpListener;

    fn spawn_single_response_server(status: &str, body: &str) -> String {
        let listener = TcpListener::bind("127.0.0.1:0").expect("bind local test server");
        let addr = listener.local_addr().expect("resolve local addr");
        let status = status.to_string();
        let body = body.to_string();

        std::thread::spawn(move || {
            if let Ok((mut stream, _)) = listener.accept() {
                let mut buffer = [0_u8; 4096];
                let _ = stream.read(&mut buffer);
                let response = format!(
                    "HTTP/1.1 {status}\r\nContent-Length: {}\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\n{body}",
                    body.len(),
                );
                let _ = stream.write_all(response.as_bytes());
            }
        });

        format!("http://{}", addr)
    }

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
        let server_url = spawn_single_response_server("200 OK", "mock-get-body");
        let client = AsyncHttpClient::new(15, server_url.clone()).unwrap();
        let resp = client.get(&server_url).await;
        assert!(resp.is_ok());
        let resp = resp.unwrap();
        assert_eq!(resp.status, 200);
        assert_eq!(resp.body, "mock-get-body");
    }

    #[tokio::test]
    async fn test_post_request() {
        let server_url = spawn_single_response_server("200 OK", "mock-post-body");
        let client = AsyncHttpClient::new(15, server_url.clone()).unwrap();
        let resp = client.post(&server_url, "test=value").await;
        assert!(resp.is_ok());
        let resp = resp.unwrap();
        assert_eq!(resp.status, 200);
        assert_eq!(resp.body, "mock-post-body");
    }
}
