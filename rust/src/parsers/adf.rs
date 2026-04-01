//! Oracle ADF-specific parsing utilities.
//!
//! This module provides functions for extracting Oracle ADF state information
//! from HTML responses, particularly ViewState values used for form submissions.

use crate::error::{SiaScraperError, SiaScraperError::MissingElement};
use crate::patterns::get_regex;

macro_rules! define_regex {
    ($name:ident, $pattern:expr) => {
        static $name: std::sync::LazyLock<Result<regex::Regex, String>> =
            std::sync::LazyLock::new(|| {
                regex::Regex::new($pattern).map_err(|e| format!("{}: {:?}", stringify!($name), e))
            });
    };
}

define_regex!(
    INPUT_WITH_VIEWSTATE_RE,
    r#"(?is)<input[^>]*(?:name|id)\s*=\s*["'][^"']*ViewState[^"']*["'][^>]*>"#
);

define_regex!(
    VALUE_ATTR_RE,
    r#"(?is)\bvalue\b\s*(?:=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?"#
);

const VIEWSTATE_FAST_PREFIX: &str =
    "<input type=\"hidden\" name=\"javax.faces.ViewState\" value=\"";

define_regex!(
    ADF_WINDOW_ID_RE,
    r#"(?is)<input[^>]*name\s*=\s*["']Adf-Window-Id["'][^>]*value\s*=\s*["']([^"']*)["'][^>]*>"#
);

/// Extracts the ViewState value from Oracle ADF HTML response.
///
/// ViewState is a hidden form field used by Oracle ADF for maintaining
/// component state across requests. This function searches for input elements
/// with "ViewState" in either the name or id attribute.
///
/// # Arguments
/// * `html` - Raw HTML string from SIA Oracle ADF response
///
/// # Returns
/// ViewState string value extracted from hidden input element
///
/// # Errors
/// Returns `SiaScraperError::MissingElement` if ViewState element not found
///
/// # Examples
/// ```rust,ignore
/// let html = r#"<input name="javax.faces.ViewState" value="abc123" />"#;
/// let view_state = extract_view_state(html).unwrap();
/// assert_eq!(view_state, "abc123");
/// ```
///
/// ```rust,ignore
/// // With id attribute
/// let html = r#"<input id="javax_faces.ViewState" value="xyz789" />"#;
/// let view_state = extract_view_state(html).unwrap();
/// assert_eq!(view_state, "xyz789");
/// ```
pub fn extract_view_state(html: &str) -> Result<String, SiaScraperError> {
    if let Some(start) = html.find(VIEWSTATE_FAST_PREFIX) {
        let value_start = start + VIEWSTATE_FAST_PREFIX.len();
        if let Some(value_end_rel) = html[value_start..].find('"') {
            let value_end = value_start + value_end_rel;
            return Ok(html[value_start..value_end].to_string());
        }
    }

    let input_re = get_regex(&INPUT_WITH_VIEWSTATE_RE, "adf::extract_view_state")?;
    let value_re = get_regex(&VALUE_ATTR_RE, "adf::extract_view_state")?;

    for input_match in input_re.find_iter(html) {
        let input_tag = input_match.as_str();

        if let Some(captures) = value_re.captures(input_tag) {
            if let Some(double_quoted) = captures.get(1) {
                return Ok(double_quoted.as_str().to_string());
            }
            if let Some(single_quoted) = captures.get(2) {
                return Ok(single_quoted.as_str().to_string());
            }
            if let Some(unquoted) = captures.get(3) {
                return Ok(unquoted.as_str().to_string());
            }

            return Ok(String::new());
        }
    }

    Err(MissingElement {
        element: "ViewState input".to_string(),
        selector: "input[name*='ViewState'], input[id*='ViewState']".to_string(),
    })
}
