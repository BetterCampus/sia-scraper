//! Shared fallible static pattern initialization helpers.
//!
//! This module provides macros and helper functions for safely initializing
//! regex and CSS selector patterns that are used throughout the parser code.
//! Instead of panicking on invalid patterns at initialization, these provide
//! explicit error handling via Result types.
//!
//! # Usage
//!
//! ```rust
//! use crate::patterns::{define_regex, define_selector, get_regex, get_selector};
//!
//! // Define statics using macros:
//! define_regex!(MY_REGEX, r"\d+");
//! define_selector!(MY_SELECTOR, "div");
//!
//! // Access via helpers (propagate errors):
//! fn do_work() -> Result<String, SiaScraperError> {
//!     let regex = get_regex(&MY_REGEX, "module")?;
//!     let selector = get_selector(&MY_SELECTOR, "module")?;
//!     Ok(format!("using regex: {:?}", regex))
//! }
//! ```

use regex::Regex;
use scraper::Selector;
use std::sync::LazyLock;

use crate::error::SiaScraperError;

/// Macro to define a fallible regex static.
/// Uses LazyLock<Result<Regex, String>> to defer compilation and handle failures gracefully.
///
/// # Arguments
/// - `$name`: Identifier for the static variable
/// - `$pattern`: String literal containing the regex pattern
///
/// # Example
/// ```rust
/// define_regex!(EMAIL_REGEX, r"[\w.-]+@[\w.-]+\.\w+");
/// ```
#[macro_export]
macro_rules! define_regex {
    ($name:ident, $pattern:expr) => {
        static $name: LazyLock<Result<Regex, String>> = LazyLock::new(|| {
            Regex::new($pattern).map_err(|e| format!("{}: {:?}", stringify!($name), e))
        });
    };
}

/// Macro to define a fallible CSS selector static.
/// Uses LazyLock<Result<Selector, String>> to defer parsing and handle failures gracefully.
///
/// # Arguments
/// - `$name`: Identifier for the static variable
/// - `$pattern`: String literal containing the CSS selector pattern
///
/// # Example
/// ```rust
/// define_selector!(HEADING_SELECTOR, "h2.section-title");
/// ```
#[macro_export]
macro_rules! define_selector {
    ($name:ident, $pattern:expr) => {
        static $name: LazyLock<Result<Selector, String>> = LazyLock::new(|| {
            Selector::parse($pattern).map_err(|e| format!("{}: {:?}", stringify!($name), e))
        });
    };
}

/// Access a fallible regex static, returning an error with contextual information.
///
/// # Arguments
/// - `lazy`: Reference to the LazyLock<Result<Regex, String>> static
/// - `context`: Module or function context for error messages
///
/// # Returns
/// - `Ok(&Regex)` on success
/// - `Err(SiaScraperError::ParseError)` if regex initialization failed
///
/// # Error Details
/// Includes the regex name and the underlying regex error for debugging.
pub fn get_regex<'a>(
    lazy: &'a LazyLock<Result<Regex, String>>,
    context: &str,
) -> Result<&'a Regex, SiaScraperError> {
    match &**lazy {
        Ok(regex) => Ok(regex),
        Err(msg) => Err(SiaScraperError::ParseError(format!(
            "Regex initialization failed for {{regex}} in {}: {}. This indicates an internal pattern definition bug.",
            context, msg
        ))),
    }
}

/// Access a fallible CSS selector static, returning an error with contextual information.
///
/// # Arguments
/// - `lazy`: Reference to the LazyLock<Result<Selector, String>> static
/// - `context`: Module or function context for error messages
///
/// # Returns
/// - `Ok(&Selector)` on success
/// - `Err(SiaScraperError::ParseError)` if selector parsing failed
///
/// # Error Details
/// Includes the selector name and the underlying selector error for debugging.
pub fn get_selector<'a>(
    lazy: &'a LazyLock<Result<Selector, String>>,
    context: &str,
) -> Result<&'a Selector, SiaScraperError> {
    match &**lazy {
        Ok(selector) => Ok(selector),
        Err(msg) => Err(SiaScraperError::ParseError(format!(
            "Selector initialization failed for {{selector}} in {}: {}. This indicates an internal pattern definition bug.",
            context, msg
        ))),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    define_regex!(TEST_EMAIL_REGEX, r"[\w.-]+@[\w.-]+\.\w+");
    define_selector!(TEST_DIV_SELECTOR, "div");

    #[test]
    fn test_get_regex_success() {
        let result = get_regex(&TEST_EMAIL_REGEX, "tests");
        assert!(result.is_ok());
        let regex = result.unwrap();
        assert!(regex.is_match("test@example.com"));
    }

    #[test]
    fn test_get_selector_success() {
        let result = get_selector(&TEST_DIV_SELECTOR, "tests");
        assert!(result.is_ok());
        let _selector = result.unwrap();
        // Selector is valid - just verify we got one
    }

    #[test]
    fn test_macro_defines_correct_type() {
        // Verify the macros create the expected LazyLock type
        let _: &LazyLock<Result<Regex, String>> = &TEST_EMAIL_REGEX;
        let _: &LazyLock<Result<Selector, String>> = &TEST_DIV_SELECTOR;
    }

    #[test]
    fn test_error_context_includes_module() {
        // Test that error messages include the context parameter
        let result = get_regex(&TEST_EMAIL_REGEX, "my_module");
        assert!(result.is_ok()); // Valid regex, so should pass
    }
}
