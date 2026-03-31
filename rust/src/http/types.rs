//! HTTP response type.

use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct HttpResponse {
    pub status: u16,
    pub headers: HashMap<String, String>,
    pub body: String,
    pub url: String,
}

impl HttpResponse {
    pub async fn from_reqwest(resp: reqwest::Response) -> Result<Self, crate::http::HttpError> {
        let status = resp.status().as_u16();
        let url = resp.url().to_string();
        let headers: HashMap<String, String> = resp
            .headers()
            .iter()
            .map(|(k, v)| (k.to_string(), v.to_str().unwrap_or("").to_string()))
            .collect();
        let body = resp.text().await.map_err(|e| {
            crate::http::HttpError::ParseError(e.to_string())
        })?;

        Ok(Self {
            status,
            headers,
            body,
            url,
        })
    }

    pub fn raise_for_status(&self) -> Result<(), crate::http::HttpError> {
        if self.status >= 400 {
            return Err(crate::http::HttpError::HttpStatus {
                status: self.status,
                url: self.url.clone(),
            });
        }
        Ok(())
    }
}
