//! Types for batch scraping operations.

// Allow non-local definitions for PyO3's #[pymethods] macro which generates
// trait implementations inside the impl block.
#![allow(non_local_definitions)]

use pyo3::prelude::*;
use std::str::FromStr;

use crate::error::SiaScraperError;
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
    type Err = SiaScraperError;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_lowercase().as_str() {
            "abort" => Ok(ErrorMode::Abort),
            "skip" => Ok(ErrorMode::Skip),
            "retry" => Ok(ErrorMode::Retry),
            other => Err(SiaScraperError::InvalidInput(format!(
                "Invalid error mode: '{}'. Must be 'abort', 'skip', or 'retry'",
                other
            ))),
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
#[derive(Debug, Default)]
pub struct ScrapeResult {
    /// Successfully scraped courses.
    pub successes: Vec<CourseInfoModel>,
    /// Failed course indices with their error messages.
    pub failures: Vec<(i32, String)>,
}

#[pymethods]
impl ScrapeResult {
    /// Create a new empty ScrapeResult.
    ///
    /// # Returns
    /// An empty `ScrapeResult` with no successes or failures.
    ///
    /// # Examples
    /// ```python
    /// result = sia_scraper_rust.ScrapeResult()
    /// assert result.total() == 0
    /// assert result.success_rate() == 1.0
    /// ```
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
    /// The sum of `successes.len()` and `failures.len()`.
    ///
    /// # Examples
    /// ```python
    /// result = await session.scrape_courses([0, 1], mode="skip")
    /// print(result.total())  # 2
    /// ```
    pub fn total(&self) -> usize {
        self.successes.len() + self.failures.len()
    }

    /// Return the success rate as a fraction (0.0 to 1.0).
    ///
    /// # Returns
    /// Ratio of successful courses to total courses.
    /// Returns 1.0 if no courses were processed.
    ///
    /// # Examples
    /// ```python
    /// result = await session.scrape_courses([0, 1], mode="skip")
    /// print(f"{result.success_rate():.1%}")  # 50.0% if one succeeded
    /// ```
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
    /// String in format "ScrapeResult: X successes, Y failures".
    /// Uses singular form when count is 1 (e.g., "1 success, 2 failures"),
    /// plural otherwise (e.g., "2 successes, 1 failure").
    ///
    /// # Examples
    /// ```python
    /// result = await session.scrape_courses([0, 1], mode="skip")
    /// print(result)  # ScrapeResult: 1 success, 1 failure
    /// ```
    pub fn __repr__(&self) -> String {
        let success_word = if self.successes.len() == 1 {
            "success"
        } else {
            "successes"
        };
        let failure_word = if self.failures.len() == 1 {
            "failure"
        } else {
            "failures"
        };
        format!(
            "ScrapeResult: {} {}, {} {}",
            self.successes.len(),
            success_word,
            self.failures.len(),
            failure_word
        )
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
    fn test_scrape_result_total_empty_result() {
        let result = ScrapeResult {
            successes: vec![],
            failures: vec![],
        };
        assert_eq!(result.total(), 0);
        assert_eq!(result.success_rate(), 1.0);
    }

    #[test]
    fn test_scrape_result_total_all_failures() {
        let result = ScrapeResult {
            successes: vec![],
            failures: vec![(0, "error".to_string()), (1, "error2".to_string())],
        };
        assert_eq!(result.total(), 2);
        assert_eq!(result.success_rate(), 0.0);
    }

    #[test]
    fn test_scrape_result_success_rate_empty() {
        let result = ScrapeResult {
            successes: vec![],
            failures: vec![],
        };
        assert_eq!(result.success_rate(), 1.0);
    }

    #[test]
    fn test_scrape_result_success_rate_single_failure() {
        let result = ScrapeResult {
            successes: vec![],
            failures: vec![(0, "error".to_string())],
        };
        assert_eq!(result.total(), 1);
        assert_eq!(result.success_rate(), 0.0);
    }

    #[test]
    fn test_scrape_result_total_with_successes() {
        let course = CourseInfoModel {
            course_name: "Cálculo".to_string(),
            credits: 3,
            typology: "Obligatoria".to_string(),
            available_spots: 20,
            scrape_timestamp: "2026-01-01 00:00".to_string(),
            groups: vec![],
            code: None,
        };
        let result = ScrapeResult {
            successes: vec![course],
            failures: vec![(0, "err".to_string())],
        };
        assert_eq!(result.total(), 2);
    }

    #[test]
    fn test_scrape_result_success_rate_mixed() {
        let course1 = CourseInfoModel {
            course_name: "Cálculo".to_string(),
            credits: 3,
            typology: "Obligatoria".to_string(),
            available_spots: 20,
            scrape_timestamp: "2026-01-01 00:00".to_string(),
            groups: vec![],
            code: None,
        };
        let course2 = CourseInfoModel {
            course_name: "Álgebra".to_string(),
            credits: 3,
            typology: "Obligatoria".to_string(),
            available_spots: 15,
            scrape_timestamp: "2026-01-01 00:00".to_string(),
            groups: vec![],
            code: None,
        };
        let result = ScrapeResult {
            successes: vec![course1, course2],
            failures: vec![(2, "err".to_string()), (3, "err2".to_string())],
        };
        assert_eq!(result.total(), 4);
        assert_eq!(result.success_rate(), 0.5);
    }

    #[test]
    fn test_scrape_result_success_rate_all_success() {
        let course = CourseInfoModel {
            course_name: "Cálculo".to_string(),
            credits: 3,
            typology: "Obligatoria".to_string(),
            available_spots: 20,
            scrape_timestamp: "2026-01-01 00:00".to_string(),
            groups: vec![],
            code: None,
        };
        let result = ScrapeResult {
            successes: vec![course],
            failures: vec![],
        };
        assert_eq!(result.total(), 1);
        assert_eq!(result.success_rate(), 1.0);
    }

    #[test]
    fn test_scrape_result_debug_repr() {
        let result = ScrapeResult {
            successes: vec![],
            failures: vec![(0, "err".to_string()), (1, "err2".to_string())],
        };
        let repr = result.__repr__();
        assert_eq!(repr, "ScrapeResult: 0 successes, 2 failures");
    }

    #[test]
    fn test_scrape_result_debug_repr_singular_both() {
        let course = CourseInfoModel {
            course_name: "Cálculo".to_string(),
            credits: 3,
            typology: "Obligatoria".to_string(),
            available_spots: 20,
            scrape_timestamp: "2026-01-01 00:00".to_string(),
            groups: vec![],
            code: Some("1000001".to_string()),
        };
        let result = ScrapeResult {
            successes: vec![course],
            failures: vec![(0, "err".to_string())],
        };
        let repr = result.__repr__();
        assert_eq!(repr, "ScrapeResult: 1 success, 1 failure");
    }

    #[test]
    fn test_scrape_result_debug_repr_only_successes() {
        let course1 = CourseInfoModel {
            course_name: "Cálculo".to_string(),
            credits: 3,
            typology: "Obligatoria".to_string(),
            available_spots: 20,
            scrape_timestamp: "2026-01-01 00:00".to_string(),
            groups: vec![],
            code: Some("1000001".to_string()),
        };
        let course2 = CourseInfoModel {
            course_name: "Álgebra".to_string(),
            credits: 3,
            typology: "Obligatoria".to_string(),
            available_spots: 15,
            scrape_timestamp: "2026-01-01 00:00".to_string(),
            groups: vec![],
            code: Some("1000002".to_string()),
        };
        let result = ScrapeResult {
            successes: vec![course1, course2],
            failures: vec![],
        };
        let repr = result.__repr__();
        assert_eq!(repr, "ScrapeResult: 2 successes, 0 failures");
    }

    #[test]
    fn test_scrape_result_debug_repr_single_success_only() {
        let course = CourseInfoModel {
            course_name: "Cálculo".to_string(),
            credits: 3,
            typology: "Obligatoria".to_string(),
            available_spots: 20,
            scrape_timestamp: "2026-01-01 00:00".to_string(),
            groups: vec![],
            code: Some("1000001".to_string()),
        };
        let result = ScrapeResult {
            successes: vec![course],
            failures: vec![],
        };
        let repr = result.__repr__();
        assert_eq!(repr, "ScrapeResult: 1 success, 0 failures");
    }

    #[test]
    fn test_scrape_result_debug_repr_single_failure_only() {
        let result = ScrapeResult {
            successes: vec![],
            failures: vec![(0, "err".to_string())],
        };
        let repr = result.__repr__();
        assert_eq!(repr, "ScrapeResult: 0 successes, 1 failure");
    }
}
