//! Table parsing utilities for Oracle ADF course list HTML.
//!
//! This module provides functions to extract course information from Oracle ADF
//! table HTML, specifically parsing the course list displayed on career pages.

use scraper::{ElementRef, Html};

use crate::error::SiaScraperError;
use crate::models::session::CourseListEntryModel;
use crate::parsers::utils::extract_text_from_elem;
use crate::patterns::get_regex;
use crate::patterns::get_selector;

macro_rules! define_regex {
    ($name:ident, $pattern:expr) => {
        static $name: std::sync::LazyLock<Result<regex::Regex, String>> =
            std::sync::LazyLock::new(|| {
                regex::Regex::new($pattern).map_err(|e| format!("{}: {:?}", stringify!($name), e))
            });
    };
}

macro_rules! define_selector {
    ($name:ident, $pattern:expr) => {
        static $name: std::sync::LazyLock<Result<scraper::Selector, String>> =
            std::sync::LazyLock::new(|| {
                scraper::Selector::parse($pattern)
                    .map_err(|e| format!("{}: {:?}", stringify!($name), e))
            });
    };
}

const COURSE_CODE_COL: usize = 0;
const COURSE_NAME_COL: usize = 1;

define_regex!(TAG_REGEX, r"(?is)<[^>]+>");

define_regex!(
    ROW_REGEX,
    r#"(?is)<tr[^>]*class\s*=\s*["'][^"']*\baf_table_data-row\b[^"']*["'][^>]*>(.*?)</tr>"#
);

define_regex!(
    SPAN_REGEX,
    r#"(?is)<span[^>]*class\s*=\s*["'][^"']*\baf_column_data-container\b[^"']*["'][^>]*>(.*?)</span>"#
);

define_selector!(ROW_SELECTOR, "tr.af_table_data-row");

define_selector!(SPAN_SELECTOR, "span.af_column_data-container");

#[inline]
fn strip_tags(content: &str) -> Result<String, SiaScraperError> {
    let regex = get_regex(&TAG_REGEX, "table_parser::strip_tags")?;
    Ok(regex.replace_all(content, "").trim().to_string())
}

fn extract_course_list_from_raw_html(
    html_content: &str,
) -> Result<Vec<CourseListEntryModel>, SiaScraperError> {
    let row_regex = get_regex(
        &ROW_REGEX,
        "table_parser::extract_course_list_from_raw_html",
    )?;
    let span_regex = get_regex(
        &SPAN_REGEX,
        "table_parser::extract_course_list_from_raw_html",
    )?;

    let mut course_list = Vec::new();

    for row_capture in row_regex.captures_iter(html_content) {
        let Some(row_inner_html) = row_capture.get(1).map(|m| m.as_str()) else {
            continue;
        };

        let mut spans = span_regex.captures_iter(row_inner_html);
        let first_span = spans
            .next()
            .and_then(|cap| cap.get(1).map(|m| strip_tags(m.as_str()).ok()))
            .flatten();
        let second_span = spans
            .next()
            .and_then(|cap| cap.get(1).map(|m| strip_tags(m.as_str()).ok()))
            .flatten();

        if let (Some(course_code), Some(course_name)) = (first_span, second_span) {
            if !course_code.is_empty() {
                course_list.push(CourseListEntryModel {
                    code: course_code,
                    name: course_name,
                });
            }
        }
    }

    Ok(course_list)
}

/// Extracts course list from Oracle ADF table HTML.
///
/// Parses `<tr class="af_table_data-row">` elements and extracts
/// course code and name from nested spans.
///
/// # Arguments
/// * `html_content` - Raw HTML string from SIA career page
///
/// # Returns
/// `Result<Vec<CourseListEntryModel>, SiaScraperError>` containing the parsed
/// course entries with `code` and `name` fields, or an error if parsing fails.
///
/// # Errors
/// Returns `SiaScraperError` if HTML parsing fails, required selectors are not found,
/// or table structure is invalid.
///
/// # Examples
/// ```rust,ignore
/// let html = r#"
/// <tr class="af_table_data-row">
///     <td><span class="af_column_data-container">2015555</span></td>
///     <td><span class="af_column_data-container">Algebra Lineal</span></td>
/// </tr>
/// "#;
/// let result = get_course_list(html).unwrap();
/// assert_eq!(result.len(), 1);
/// assert_eq!(result[0].code, "2015555");
/// assert_eq!(result[0].name, "Algebra Lineal");
/// ```
pub fn get_course_list(html_content: &str) -> Result<Vec<CourseListEntryModel>, SiaScraperError> {
    let html = Html::parse_document(html_content);

    let row_selector = get_selector(&ROW_SELECTOR, "table_parser::get_course_list")?;
    let span_selector = get_selector(&SPAN_SELECTOR, "table_parser::get_course_list")?;

    let rows = html.select(row_selector);
    let mut course_list = Vec::new();

    for row in rows {
        let data_spans: Vec<ElementRef> = row.select(span_selector).collect();

        if data_spans.len() >= 2 {
            let course_code = extract_text_from_elem(&data_spans[COURSE_CODE_COL]);
            let course_name = extract_text_from_elem(&data_spans[COURSE_NAME_COL]);

            if course_code.is_empty() {
                continue;
            }

            course_list.push(CourseListEntryModel {
                code: course_code,
                name: course_name,
            });
        }
    }

    if course_list.is_empty() {
        return extract_course_list_from_raw_html(html_content);
    }

    Ok(course_list)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_get_course_list_valid_table() {
        let html = r#"
        <html><body>
        <tr class="af_table_data-row">
            <td><span class="af_column_data-container">2015555</span></td>
            <td><span class="af_column_data-container">Álgebra Lineal</span></td>
        </tr>
        <tr class="af_table_data-row">
            <td><span class="af_column_data-container">2027641</span></td>
            <td><span class="af_column_data-container">Análisis de Datos</span></td>
        </tr>
        </body></html>
        "#;

        let result = get_course_list(html).unwrap();
        assert_eq!(result.len(), 2);
        assert_eq!(result[0].code, "2015555");
        assert_eq!(result[0].name, "Álgebra Lineal");
        assert_eq!(result[1].code, "2027641");
        assert_eq!(result[1].name, "Análisis de Datos");
    }

    #[test]
    fn test_get_course_list_empty_table() {
        let html = r#"<html><body></body></html>"#;

        let result = get_course_list(html).unwrap();
        assert_eq!(result.len(), 0);
    }

    #[test]
    fn test_get_course_list_single_course() {
        let html = r#"
        <html><body>
        <table>
        <tr class="af_table_data-row">
            <td><span class="af_column_data-container">1000001</span></td>
            <td><span class="af_column_data-container">Cálculo Diferencial</span></td>
        </tr>
        </table>
        </body></html>
        "#;

        let result = get_course_list(html).unwrap();
        assert_eq!(result.len(), 1);
        assert_eq!(result[0].code, "1000001");
        assert_eq!(result[0].name, "Cálculo Diferencial");
    }

    #[test]
    fn test_get_course_list_missing_spans() {
        let html = r#"
        <html><body>
        <tr class="af_table_data-row">
            <td><span class="af_column_data-container">2015555</span></td>
        </tr>
        </body></html>
        "#;

        let result = get_course_list(html).unwrap();
        assert_eq!(result.len(), 0);
    }

    #[test]
    fn test_get_course_list_malformed_html() {
        let html = r#"not valid html at all"#;

        let result = get_course_list(html).unwrap();
        assert_eq!(result.len(), 0);
    }

    #[test]
    fn test_get_course_list_empty_course_code() {
        let html = r#"
        <html><body>
        <tr class="af_table_data-row">
            <td><span class="af_column_data-container"></span></td>
            <td><span class="af_column_data-container">Some Course</span></td>
        </tr>
        </body></html>
        "#;

        let result = get_course_list(html).unwrap();
        assert_eq!(result.len(), 0);
    }

    #[test]
    fn test_get_course_list_empty_code_row_is_skipped_in_primary_parser() {
        let html = r#"
        <html><body>
        <table>
            <tr class="af_table_data-row">
                <td><span class="af_column_data-container"></span></td>
                <td><span class="af_column_data-container">Should Skip</span></td>
            </tr>
            <tr class="af_table_data-row">
                <td><span class="af_column_data-container">1000002</span></td>
                <td><span class="af_column_data-container">Valid Course</span></td>
            </tr>
        </table>
        </body></html>
        "#;

        let result = get_course_list(html).unwrap();
        assert_eq!(result.len(), 1);
        assert_eq!(result[0].code, "1000002");
        assert_eq!(result[0].name, "Valid Course");
    }

    #[test]
    fn test_get_course_list_whitespace_handling() {
        let html = r#"
        <html><body>
        <tr class="af_table_data-row">
            <td><span class="af_column_data-container">   2015555   </span></td>
            <td><span class="af_column_data-container">   Álgebra Lineal   </span></td>
        </tr>
        </body></html>
        "#;

        let result = get_course_list(html).unwrap();
        assert_eq!(result.len(), 1);
        assert_eq!(result[0].code, "2015555");
        assert_eq!(result[0].name, "Álgebra Lineal");
    }

    #[test]
    fn test_get_course_list_multiple_rows_same_code() {
        let html = r#"
        <html><body>
        <tr class="af_table_data-row">
            <td><span class="af_column_data-container">2015555</span></td>
            <td><span class="af_column_data-container">Algebra Lineal</span></td>
        </tr>
        <tr class="af_table_data-row">
            <td><span class="af_column_data-container">2015555</span></td>
            <td><span class="af_column_data-container">Algebra Lineal (otro)</span></td>
        </tr>
        </body></html>
        "#;

        let result = get_course_list(html).unwrap();
        assert_eq!(result.len(), 2);
    }

    #[test]
    fn test_get_course_list_with_special_chars() {
        let html = r#"
        <html><body>
        <tr class="af_table_data-row">
            <td><span class="af_column_data-container">2027309</span></td>
            <td><span class="af_column_data-container">Análisis forense digital &amp; más</span></td>
        </tr>
        </body></html>
        "#;

        let result = get_course_list(html).unwrap();
        assert_eq!(result.len(), 1);
        assert_eq!(result[0].code, "2027309");
        assert_eq!(result[0].name, "Análisis forense digital &amp; más");
    }

    #[test]
    fn test_get_course_list_non_row_elements() {
        let html = r#"
        <html><body>
        <tr class="other-class">
            <td><span class="af_column_data-container">2015555</span></td>
            <td><span class="af_column_data-container">Should Not Appear</span></td>
        </tr>
        <tr class="af_table_data-row">
            <td><span class="af_column_data-container">2027641</span></td>
            <td><span class="af_column_data-container">Should Appear</span></td>
        </tr>
        </body></html>
        "#;

        let result = get_course_list(html).unwrap();
        assert_eq!(result.len(), 1);
        assert_eq!(result[0].code, "2027641");
        assert_eq!(result[0].name, "Should Appear");
    }

    #[test]
    fn test_get_course_list_large_batch() {
        let mut html = String::from("<html><body>");
        for i in 0..100 {
            html.push_str(&format!(
                r#"<tr class="af_table_data-row">
                <td><span class="af_column_data-container">20{:05}</span></td>
                <td><span class="af_column_data-container">Curso {}</span></td>
                </tr>"#,
                i, i
            ));
        }
        html.push_str("</body></html>");

        let result = get_course_list(&html).unwrap();
        assert_eq!(result.len(), 100);
        assert_eq!(result[0].code, "2000000");
        assert_eq!(result[0].name, "Curso 0");
        assert_eq!(result[99].code, "2000099");
        assert_eq!(result[99].name, "Curso 99");
    }

    #[test]
    fn test_get_course_list_spans_without_td() {
        let html = r#"
        <table>
          <tr class="af_table_data-row">
            <span class="af_column_data-container">1000001</span>
            <span class="af_column_data-container">CALCULO</span>
          </tr>
        </table>
        "#;

        let result = get_course_list(html).unwrap();
        assert_eq!(result.len(), 1);
        assert_eq!(result[0].code, "1000001");
        assert_eq!(result[0].name, "CALCULO");
    }

    #[test]
    fn test_get_course_list_handles_empty_input() {
        let html = "";
        let result = get_course_list(html);
        assert!(matches!(result, Ok(ref courses) if courses.is_empty()));
    }
}
