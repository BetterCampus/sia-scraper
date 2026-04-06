//! Python-accessible SiaSession wrapper with async methods.
//!
//! This module provides a stateful PyO3 wrapper around the Rust SiaSession,
//! enabling Python code to maintain persistent session state across method calls.

#![allow(non_local_definitions)]

use std::str::FromStr;
use std::sync::Arc;
use tokio::sync::RwLock;

use pyo3::prelude::*;
use pyo3::types::PyDict;
use pyo3::Python;
use pyo3_asyncio::tokio::future_into_py;

use crate::constants::SIA_BASE_URL;
use crate::error::{AbortError, SessionError};
use crate::http::sia_session::SiaSession;
use crate::models::scrape_result::ErrorMode;
use crate::models::session::SessionStateModel;

type SiaSessionInner = Option<SiaSession>;

fn required_item<'py>(dict: &'py PyDict, key: &str) -> PyResult<&'py PyAny> {
    dict.get_item(key)?
        .ok_or_else(|| pyo3::exceptions::PyKeyError::new_err(format!("Missing key: {key}")))
}

/// Stateful SIA session wrapper for Python.
///
/// This class wraps the Rust SiaSession and provides async methods
/// that can be called from Python. The session maintains state across
/// method calls, eliminating the need to pass session data back and forth.
///
/// Supports pickle serialization for session persistence and async context
/// manager protocol for `async with PySiaSession() as session:` patterns.
///
/// # Example
/// ```python
/// import asyncio
/// import sia_scraper_rust
///
/// async def main():
///     async with sia_scraper_rust.PySiaSession(timeout=30) as session:
///         await session.init_session()
///         await session.set_career("0-2-8-3")
///         course = await session.scrape_course_info(0)
///         print(course.course_name)
///
/// asyncio.run(main())
/// ```
#[pyclass(module = "sia_scraper_rust")]
pub struct PySiaSession {
    inner: Arc<RwLock<SiaSessionInner>>,
    timeout: u64,
}

/// Suppress non_local_definitions warning caused by PyO3 macro expansion.
/// This is a known false positive with #[pymethods] in Rust 1.81+.
#[pymethods]
impl PySiaSession {
    /// Create a new PySiaSession instance.
    ///
    /// The session is not immediately initialized - call init_session()
    /// to establish the HTTP connection and fetch initial state.
    ///
    /// # Arguments
    /// * `timeout` - Request timeout in seconds (default: 15)
    ///
    /// # Returns
    /// New PySiaSession instance
    ///
    /// # Example
    /// ```python
    /// session = sia_scraper_rust.PySiaSession(timeout=30)
    /// ```
    #[new]
    fn new(timeout: Option<u64>) -> Self {
        Self {
            inner: Arc::new(RwLock::new(None)),
            timeout: timeout.unwrap_or(15),
        }
    }

    /// Initialize the SIA session and fetch initial ViewState.
    ///
    /// This must be called before any other session methods. It establishes
    /// the HTTP session with the SIA server and extracts Oracle ADF parameters.
    ///
    /// # Returns
    /// `SessionStateModel` with initial session state
    ///
    /// # Raises
    /// NetworkError: If connection fails
    /// HttpStatusError: If server returns error status
    /// SiaTimeoutError: If request times out
    /// ParseError: If response cannot be parsed
    /// SessionError: If ViewState not found
    ///
    /// # Example
    /// ```python
    /// session = sia_scraper_rust.PySiaSession()
    /// state = await session.init_session()
    /// print(state.career_code)  # Empty until set_career is called
    /// ```
    fn init_session<'py>(&self, py: Python<'py>) -> PyResult<&'py PyAny> {
        let inner = Arc::clone(&self.inner);
        let timeout = self.timeout;
        let base_url = SIA_BASE_URL.to_string();

        future_into_py(py, async move {
            let session = SiaSession::new(timeout, base_url)
                .map_err(pyo3::PyErr::from)?;

            session
                .init_session()
                .await
                .map_err(pyo3::PyErr::from)?;

            let state = session.get_state().await;

            *inner.write().await = Some(session);

            Ok(SessionStateModel::from_session_state(&state))
        })
    }

    /// Navigate to a career and load the course list.
    ///
    /// # Arguments
    /// * `search_code` - Career search code (e.g., "0-2-8-3")
    /// * `electives` - True for elective courses, False for required (default: false)
    ///
    /// # Returns
    /// `SessionStateModel` with career info and course list
    ///
    /// # Raises
    /// SessionError: If session not initialized
    /// ValueError: If search_code is invalid
    /// NetworkError: If connection fails
    /// HttpStatusError: If server returns error status
    /// SiaTimeoutError: If request times out
    /// ParseError: If response cannot be parsed
    ///
    /// # Example
    /// ```python
    /// state = await session.set_career("0-2-8-3")
    /// print(f"Loaded {len(state.course_list)} courses")
    /// ```
    fn set_career<'py>(
        &self,
        py: Python<'py>,
        search_code: String,
        electives: Option<bool>,
    ) -> PyResult<&'py PyAny> {
        let inner = Arc::clone(&self.inner);
        let electives = electives.unwrap_or(false);

        future_into_py(py, async move {
            let session_guard = inner.read().await;
            let session = session_guard
                .as_ref()
                .ok_or_else(|| SessionError::new_err(
                    "Session not initialized. Call init_session() first."
                ))?;

            let state = session
                .set_career(&search_code, electives)
                .await
                .map_err(pyo3::PyErr::from)?;

            Ok(SessionStateModel::from_session_state(&state))
        })
    }

    /// Scrape course information for the given index.
    ///
    /// Combines HTTP fetch and parsing in a single Rust call, eliminating
    /// string copying across the FFI boundary.
    ///
    /// # Arguments
    /// * `course_index` - Index of course in course_list (0-based)
    ///
    /// # Returns
    /// `CourseInfoModel` with complete course data
    ///
    /// # Raises
    /// SessionError: If session not initialized
    /// ValueError: If course_index is out of range
    /// NetworkError: If connection fails
    /// HttpStatusError: If server returns error status
    /// SiaTimeoutError: If request times out
    /// ParseError: If response cannot be parsed
    ///
    /// # Example
    /// ```python
    /// course = await session.scrape_course_info(0)
    /// print(f"Course: {course.course_name}, Credits: {course.credits}")
    /// ```
    fn scrape_course_info<'py>(&self, py: Python<'py>, course_index: i32) -> PyResult<&'py PyAny> {
        let inner = Arc::clone(&self.inner);

        future_into_py(py, async move {
            let session_guard = inner.read().await;
            let session = session_guard
                .as_ref()
                .ok_or_else(|| SessionError::new_err(
                    "Session not initialized. Call init_session() first."
                ))?;

            session
                .scrape_course_info(course_index)
                .await
                .map_err(pyo3::PyErr::from)
        })
    }

    /// Scrape prerequisite information for the given course index.
    ///
    /// # Arguments
    /// * `course_index` - Index of course in course_list (0-based)
    ///
    /// # Returns
    /// `CoursePrereqsModel` with prerequisite conditions
    ///
    /// # Raises
    /// SessionError: If session not initialized
    /// ValueError: If course_index is out of range
    /// NetworkError: If connection fails
    /// HttpStatusError: If server returns error status
    /// SiaTimeoutError: If request times out
    /// ParseError: If response cannot be parsed
    ///
    /// # Example
    /// ```python
    /// prereqs = await session.scrape_course_prereqs(0)
    /// print(f"Prerequisites: {len(prereqs.conditions)} conditions")
    /// ```
    fn scrape_course_prereqs<'py>(
        &self,
        py: Python<'py>,
        course_index: i32,
    ) -> PyResult<&'py PyAny> {
        let inner = Arc::clone(&self.inner);

        future_into_py(py, async move {
            let session_guard = inner.read().await;
            let session = session_guard
                .as_ref()
                .ok_or_else(|| SessionError::new_err(
                    "Session not initialized. Call init_session() first."
                ))?;

            session
                .scrape_course_prereqs(course_index)
                .await
                .map_err(pyo3::PyErr::from)
        })
    }

    /// Scrape multiple courses sequentially with configurable error handling.
    ///
    /// Iterates over the provided course indices and attempts to scrape each one.
    /// Errors are handled according to the specified `mode`:
    ///
    /// - `"abort"`: Stop immediately on the first error.
    /// - `"skip"`: Record the failure and continue to the next course.
    /// - `"retry"`: Retry failed courses up to `retries` times with
    ///   exponential backoff before recording as a failure.
    ///
    /// # Arguments
    /// * `indices` - List of course indices to scrape
    /// * `mode` - Error handling mode: "abort", "skip", or "retry"
    /// * `retries` - Maximum retry attempts per course (default: 3, used only in retry mode)
    /// * `delay` - Base delay between retries in milliseconds (default: 800)
    ///
    /// # Returns
    /// `ScrapeResult` with successes and failures lists
    ///
    /// # Raises
    /// SessionError: If session not initialized or in Abort mode on first failure
    /// NetworkError: If connection fails
    /// HttpStatusError: If server returns error status
    /// SiaTimeoutError: If request times out
    /// ParseError: If response cannot be parsed
    ///
    /// # Concurrency Safety
    ///
    /// This method uses a generation-based conflict detection to prevent
    /// stale state overwrites when multiple concurrent operations modify
    /// the session state. If another method (e.g., `set_career()`) mutates
    /// the session state during the batch operation, the state update is
    /// skipped and logged at debug level. This ensures concurrent operations
    /// do not overwrite each other's changes.
    ///
    /// # Example
    /// ```python
    /// result = await session.scrape_courses([0, 1, 2], mode="skip")
    /// print(f"Success rate: {result.success_rate():.1%}")
    /// for course in result.successes:
    ///     print(course.course_name)
    /// ```
    #[pyo3(signature = (indices, mode, retries=None, delay=None))]
    fn scrape_courses<'py>(
        &self,
        py: Python<'py>,
        indices: Vec<i32>,
        mode: String,
        retries: Option<u32>,
        delay: Option<u64>,
    ) -> PyResult<&'py PyAny> {
        let inner = Arc::clone(&self.inner);
        let error_mode = ErrorMode::from_str(&mode)?;
        let max_retries = retries.unwrap_or(3);
        let retry_delay_ms = delay.unwrap_or(800);

        future_into_py(py, async move {
            let (cloned_session, result, parent_generation) = {
                let session_guard = inner.read().await;
                let original = session_guard
                    .as_ref()
                    .ok_or_else(|| SessionError::new_err(
                        "Session not initialized. Call init_session() first."
                    ))?;
                let parent_generation = original.get_state().await.generation();
                let cloned = original.clone_with_owned_state().await;
                let result = cloned
                    .scrape_courses_batch(indices, error_mode, max_retries, retry_delay_ms)
                    .await;
                (cloned, result, parent_generation)
            };

            let mutated_state = cloned_session.get_state().await;
            let mut session_guard = inner.write().await;
            if let Some(ref mut session) = *session_guard {
                let current_generation = session.get_state().await.generation();
                if current_generation == parent_generation {
                    session.update_state(mutated_state).await;
                } else {
                    log::debug!(
                        "Skipping state update in scrape_courses: generation mismatch \
                         (expected {}, got {}). Another concurrent operation modified the session.",
                        parent_generation,
                        current_generation
                    );
                }
            }

            result.map_err(|e| {
                if error_mode == ErrorMode::Abort {
                    AbortError::new_err(e.to_string())
                } else {
                    pyo3::PyErr::from(e)
                }
            })
        })
    }

    /// Scrape multiple courses concurrently with configurable parallelism.
    ///
    /// Uses Rust's `tokio` and `futures` ecosystem to execute up to
    /// `max_concurrent` scraping operations simultaneously. This can provide
    /// significant speedups (3x-5x) compared to sequential scraping for
    /// batches of 20+ courses.
    ///
    /// Note: Unlike [`ScrapeCoursesMethod`][super::ScrapeCoursesMethod], this method
    /// operates on a cloned, owned session and does NOT sync ViewState or other
    /// mutations back to the shared parent session. This is intentional to avoid
    /// conflicting concurrent writes to the session state.
    ///
    /// Errors are handled according to the specified `mode`:
    ///
    /// - `"abort"`: Stop immediately on the first error.
    /// - `"skip"`: Record the failure and continue to the next course.
    /// - `"retry"`: Retry failed courses up to `retries` times with
    ///   exponential backoff before recording as a failure.
    ///
    /// # Arguments
    /// * `indices` - List of course indices to scrape
    /// * `mode` - Error handling mode: "abort", "skip", or "retry"
    /// * `max_concurrent` - Maximum number of concurrent scraping operations (default: 5)
    /// * `retries` - Maximum retry attempts per course (default: 3, used only in retry mode)
    /// * `delay` - Base delay between retries in milliseconds (default: 800)
    ///
    /// # Returns
    /// `ScrapeResult` with successes and failures lists
    ///
    /// # Raises
    /// SessionError: If session not initialized or in Abort mode on first failure
    /// NetworkError: If connection fails
    /// HttpStatusError: If server returns error status
    /// SiaTimeoutError: If request times out
    /// ParseError: If response cannot be parsed
    ///
    /// # Example
    /// ```python
    /// result = await session.scrape_courses_parallel([0, 1, 2], max_concurrent=5, mode="skip")
    /// print(f"Success rate: {result.success_rate():.1%}")
    /// for course in result.successes:
    ///     print(course.course_name)
    /// ```
    #[pyo3(signature = (indices, mode, max_concurrent=None, retries=None, delay=None))]
    fn scrape_courses_parallel<'py>(
        &self,
        py: Python<'py>,
        indices: Vec<i32>,
        mode: String,
        max_concurrent: Option<usize>,
        retries: Option<u32>,
        delay: Option<u64>,
    ) -> PyResult<&'py PyAny> {
        let inner = Arc::clone(&self.inner);
        let error_mode = ErrorMode::from_str(&mode)?;
        let concurrency = max_concurrent.unwrap_or(5);
        let max_retries = retries.unwrap_or(3);
        let retry_delay_ms = delay.unwrap_or(800);

        future_into_py(py, async move {
            let session = {
                let session_guard = inner.read().await;
                let original = session_guard
                    .as_ref()
                    .ok_or_else(|| SessionError::new_err(
                        "Session not initialized. Call init_session() first."
                    ))?;
                original.clone_with_owned_state().await
            };

            session
                .scrape_courses_concurrent(indices, concurrency, error_mode, max_retries, retry_delay_ms)
                .await
                .map_err(|e| {
                    if error_mode == ErrorMode::Abort {
                        AbortError::new_err(e.to_string())
                    } else {
                        pyo3::PyErr::from(e)
                    }
                })
        })
    }

    /// Get the current session state.
    ///
    /// # Returns
    /// `SessionStateModel` with current session state
    ///
    /// # Raises
    /// SessionError: If session not initialized
    ///
    /// # Example
    /// ```python
    /// state = await session.get_state()
    /// print(f"Status: {state.status}")
    /// ```
    fn get_state<'py>(&self, py: Python<'py>) -> PyResult<&'py PyAny> {
        let inner = Arc::clone(&self.inner);

        future_into_py(py, async move {
            let session_guard = inner.read().await;
            let session = session_guard
                .as_ref()
                .ok_or_else(|| SessionError::new_err(
                    "Session not initialized. Call init_session() first."
                ))?;

            let state = session.get_state().await;
            Ok(SessionStateModel::from_session_state(&state))
        })
    }

    /// Get the request timeout in seconds.
    ///
    /// # Returns
    /// Timeout value in seconds
    ///
    /// # Example
    /// ```python
    /// session = sia_scraper_rust.PySiaSession(timeout=30)
    /// print(session.timeout)  # 30
    /// ```
    #[getter]
    fn timeout(&self) -> u64 {
        self.timeout
    }

    /// Check if the session has been initialized.
    ///
    /// # Returns
    /// True if init_session() has been called, False otherwise
    ///
    /// # Example
    /// ```python
    /// session = sia_scraper_rust.PySiaSession()
    /// print(session.is_initialized())  # False
    /// await session.init_session()
    /// print(session.is_initialized())  # True
    /// ```
    fn is_initialized(&self) -> bool {
        self.inner
            .try_read()
            .map(|guard| guard.is_some())
            .unwrap_or(false)
    }

    /// Support for pickle serialization.
    ///
    /// Gets the session state for pickling. Note that the actual
    /// SiaSession contains async state that cannot be pickled, so
    /// we only pickle the configuration (timeout).
    fn __getstate__(&self, py: Python<'_>) -> PyResult<PyObject> {
        let dict = pyo3::types::PyDict::new(py);
        dict.set_item("timeout", self.timeout)?;
        Ok(dict.into_py(py))
    }

    /// Support for pickle deserialization.
    ///
    /// Restores session from pickled state. The session will need
    /// to be re-initialized after unpickling.
    fn __setstate__(&mut self, state: &PyAny) -> PyResult<()> {
        let dict = state.downcast::<pyo3::types::PyDict>()?;
        self.timeout = required_item(dict, "timeout")?.extract()?;
        // Re-initialize the inner to None since we can't restore the actual session
        self.inner = Arc::new(RwLock::new(None));
        Ok(())
    }

    /// String representation for debugging.
    fn __repr__(&self) -> String {
        format!("PySiaSession(timeout={})", self.timeout)
    }

    /// Async context manager entry - auto-initializes session if needed.
    ///
    /// If session is not already initialized, this will automatically
    /// call init_session() upon entering the context.
    ///
    /// # Returns
    /// Self (the session)
    ///
    /// # Raises
    /// SessionError: If initialization failure
    /// NetworkError: If connection fails
    /// HttpStatusError: If server returns error status
    /// SiaTimeoutError: If request times out
    /// ParseError: If response cannot be parsed
    ///
    /// # Example
    /// ```python
    /// async with sia_scraper_rust.PySiaSession() as session:
    ///     # Session is automatically initialized
    ///     state = await session.get_state()
    ///     # ... use session ...
    /// ```
    fn __aenter__<'py>(&self, py: Python<'py>) -> PyResult<&'py PyAny> {
        let session_clone = self.clone();
        let base_url = SIA_BASE_URL.to_string();

        future_into_py(py, async move {
            let needs_init = {
                let guard = session_clone.inner.read().await;
                guard.is_none()
            };

            if needs_init {
                let session = SiaSession::new(session_clone.timeout, base_url)
                    .map_err(pyo3::PyErr::from)?;

                session.init_session()
                    .await
                    .map_err(pyo3::PyErr::from)?;

                *session_clone.inner.write().await = Some(session);
            }

            Python::with_gil(|py| Ok(session_clone.into_py(py)))
        })
    }

    /// Async context manager exit - cleanup (no-op).
    ///
    /// Currently a no-op since we don't have explicit cleanup to do.
    /// The session can be re-used if needed.
    fn __aexit__<'py>(
        &self,
        py: Python<'py>,
        _exc_type: &PyAny,
        _exc_val: &PyAny,
        _exc_tb: &PyAny,
    ) -> PyResult<&'py PyAny> {
        future_into_py(py, async move {
            Ok(Python::with_gil(|py| py.None()))
        })
    }

    /// Reset the session state, clearing the underlying Rust session.
    ///
    /// This drops the SiaSession inside the wrapper, releasing all
    /// resources including HTTP connections and cookies. The PySiaSession
    /// can be re-initialized by calling init_session() again.
    ///
    /// # Returns
    /// None
    ///
    /// # Example
    /// ```python
    /// await session.init_session()
    /// # ... use session ...
    /// await session.reset()
    /// # Session is now cleared, can call init_session() again
    /// ```
    fn reset<'py>(&self, py: Python<'py>) -> PyResult<&'py PyAny> {
        let inner = Arc::clone(&self.inner);

        future_into_py::<_, PyObject>(py, async move {
            *inner.write().await = None;
            Ok(Python::with_gil(|py| py.None()))
        })
    }

    /// Restore a session from previously saved state.
    ///
    /// This static method creates a new PySiaSession with an already
    /// initialized Rust session restored from the provided state.
    ///
    /// # Arguments
    /// * `state` - Dictionary with session state data (timeout, state_dict)
    /// * `timeout` - Request timeout in seconds (default: 15)
    ///
    /// # Returns
    /// New PySiaSession with restored state
    ///
    /// # Raises
    /// KeyError: If state_dict key is missing from input
    /// TypeError: If state_dict is not a dictionary
    /// ValueError: If state_dict contains invalid model data
    /// SessionError: If restoration fails
    /// NetworkError: If connection fails during restoration
    /// HttpStatusError: If server returns error status
    /// SiaTimeoutError: If request times out
    ///
    /// # Example
    /// ```python
    /// state = {"timeout": 15, "state_dict": {...}}
    /// session = await PySiaSession.from_state(state)
    /// ```
    #[staticmethod]
    fn from_state<'py>(py: Python<'py>, state: &PyDict, timeout: Option<u64>) -> PyResult<&'py PyAny> {
        let timeout = timeout.unwrap_or(15);

        let state_dict = required_item(state, "state_dict")?
            .downcast::<PyDict>()
            .map_err(|_| pyo3::exceptions::PyTypeError::new_err("state_dict must be a dict"))?;

        let session_state_model = SessionStateModel::from_dict(state_dict)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!(
                "Invalid state_dict: {}", e
            )))?;

        let session_state = session_state_model.into_session_state();

        future_into_py::<_, PyObject>(py, async move {
            let base_url = SIA_BASE_URL.to_string();
            let sia_session = SiaSession::from_state(timeout, base_url, session_state)
                .map_err(pyo3::PyErr::from)?;

            let inner = Arc::new(RwLock::new(Some(sia_session)));

            let py_session = PySiaSession {
                inner,
                timeout,
            };

            Python::with_gil(|py| Ok(py_session.into_py(py)))
        })
    }

    /// Get session data for persistence.
    ///
    /// Returns the complete session state including headers, cookies,
    /// ViewState, career info, and course list as a dictionary.
    ///
    /// # Returns
    /// Dictionary with session data suitable for pickling/serialization
    ///
    /// # Raises
    /// SessionError: If session not initialized
    ///
    /// # Example
    /// ```python
    /// data = await session.get_session_data()
    /// # Save to file or database
    /// ```
    fn get_session_data<'py>(&self, py: Python<'py>) -> PyResult<&'py PyAny> {
        let inner = Arc::clone(&self.inner);
        let timeout = self.timeout;

        future_into_py::<_, PyObject>(py, async move {
            let session_guard = inner.read().await;
            let session = session_guard
                .as_ref()
                .ok_or_else(|| SessionError::new_err(
                    "Session not initialized. Call init_session() first."
                ))?;

            let state = session.get_state().await;
            let state_model = SessionStateModel::from_session_state(&state);

            Python::with_gil(|py| {
                let dict = pyo3::types::PyDict::new(py);
                dict.set_item("timeout", timeout)?;
                dict.set_item("state_dict", state_model.to_dict(py)?)?;
                Ok(dict.into_py(py))
            })
        })
    }
}

impl Clone for PySiaSession {
    fn clone(&self) -> Self {
        Self {
            inner: Arc::clone(&self.inner),
            timeout: self.timeout,
        }
    }
}

impl Default for PySiaSession {
    fn default() -> Self {
        Self {
            inner: Arc::new(RwLock::new(None)),
            timeout: 15,
        }
    }
}