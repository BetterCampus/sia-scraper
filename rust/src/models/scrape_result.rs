//! Types for batch scraping operations.

use pyo3::prelude::*;
use std::str::FromStr;

use crate::models::course::CourseInfoModel;

/// Error handling mode for batch scraping operations.
///
/// Controls how the batch scraper responds to failures when
/// processing multiple courses.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ErrorMode {
    /// Stop processing immediately on the first error.
    Abort,
    /// Skip failed courses and continue processing.
    Skip,
    /// Retry failed courses before skipping.
    Retry,
}

impl FromStr for ErrorMode {
    type Err = String;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_lowercase().as_str() {
            "abort" => Ok(ErrorMode::Abort),
            "skip" => Ok(ErrorMode::Skip),
            "retry" => Ok(ErrorMode::Retry),
            other => Err(format!(
                "Invalid error mode: '{}'. Must be 'abort', 'skip', or 'retry'",
                other
            )),
        }
    }
}

/// Result of a batch scraping operation.
///
/// Contains both successful course extractions and recorded failures,
/// along with convenience methods for analyzing results.
///
/// # Example
/// ```python
/// result = await session.scrape_courses([0, 1, 2], mode="skip")
/// print(f"Success rate: {result.success_rate():.1%}")
/// for course in result.successes:
///     print(course.course_name)
/// for index, error in result.failures:
///     print(f"Course {index} failed: {error}")
/// ```
#[pyclass(get_all, module = "sia_scraper_rust")]
#[derive(Debug)]
pub struct ScrapeResult {
    /// Successfully scraped courses.
    pub successes: Vec<CourseInfoModel>,
    /// Failed course indices with their error messages.
    pub failures: Vec<(i32, String)>,
}

#[pymethods]
impl ScrapeResult {
    /// Create a new empty ScrapeResult.
    #[new]
    pub fn new() -> Self {
        Self {
            successes: Vec::new(),
            failures: Vec::new(),
        }
    }

    /// Return the total number of courses processed (successes + failures).
    ///
    /// # Returns
    /// Total count of courses attempted.
    pub fn total(&self) -> usize {
        self.successes.len() + self.failures.len()
    }

    /// Return the success rate as a fraction (0.0 to 1.0).
    ///
    /// # Returns
    /// Ratio of successful courses to total courses.
    /// Returns 1.0 if no courses were processed.
    pub fn success_rate(&self) -> f64 {
        let total = self.total();
        if total == 0 {
            return 1.0;
        }
        self.successes.len() as f64 / total as f64
    }

    /// Return a human-readable summary of the scraping result.
    ///
    /// # Returns
    /// String in the format "ScrapeResult: X successes, Y failures".
    pub fn __repr__(&self) -> String {
        format!(
            "ScrapeResult: {} successes, {} failures",
            self.successes.len(),
            self.failures.len()
        )
    }
}

impl Default for ScrapeResult {
    fn default() -> Self {
        Self {
            successes: Vec::new(),
            failures: Vec::new(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_error_mode_from_str_abort() {
        assert_eq!(ErrorMode::from_str("abort").unwrap(), ErrorMode::Abort);
        assert_eq!(ErrorMode::from_str("ABORT").unwrap(), ErrorMode::Abort);
        assert_eq!(ErrorMode::from_str("Abort").unwrap(), ErrorMode::Abort);
    }

    #[test]
    fn test_error_mode_from_str_skip() {
        assert_eq!(ErrorMode::from_str("skip").unwrap(), ErrorMode::Skip);
        assert_eq!(ErrorMode::from_str("SKIP").unwrap(), ErrorMode::Skip);
    }

    #[test]
    fn test_error_mode_from_str_retry() {
        assert_eq!(ErrorMode::from_str("retry").unwrap(), ErrorMode::Retry);
        assert_eq!(ErrorMode::from_str("RETRY").unwrap(), ErrorMode::Retry);
    }

    #[test]
    fn test_error_mode_from_str_invalid() {
        assert!(ErrorMode::from_str("invalid").is_err());
        assert!(ErrorMode::from_str("").is_err());
    }

    #[test]
    fn test_scrape_result_new_is_empty() {
        let result = ScrapeResult::new();
        assert_eq!(result.total(), 0);
        assert_eq!(result.success_rate(), 1.0);
        assert!(result.successes.is_empty());
        assert!(result.failures.is_empty());
    }

    #[test]
    fn test_scrape_result_success_rate_all_success() {
        let result = ScrapeResult {
            successes: vec![],
            failures: vec![],
        };
        assert_eq!(result.success_rate(), 1.0);
    }
}
