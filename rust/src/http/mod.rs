//! Async HTTP client module for Phase 4.
//!
//! This module provides async HTTP functionality using reqwest with tokio runtime.
//! It exposes async methods to Python via pyo3-asyncio.

pub mod client;
pub mod config;
pub mod errors;
pub mod retry;
pub mod session;
pub mod sia_session;
pub mod types;

pub use client::AsyncHttpClient;
pub use config::{HttpClientConfig, TlsBackend};
pub use errors::HttpError;
pub use retry::{calculate_delay, should_retry, RetryConfig};
pub use session::SessionState;
pub use sia_session::SiaSession;
pub use types::HttpResponse;
