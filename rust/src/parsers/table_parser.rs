//! Table parsing utilities for Oracle ADF course list HTML.
//!
//! This module provides functions to extract course information from Oracle ADF
//! table HTML, specifically parsing the course list displayed on career pages.

use std::collections::HashMap;
use std::sync::LazyLock;

use regex::Regex;
use scraper::{ElementRef, Html, Selector};

use crate::error::SiaScraperError;
use crate::parsers::utils::extract_text_from_elem;

const COURSE_CODE_COL: usize = 0;
const COURSE_NAME_COL: usize = 1;

static TAG_REGEX: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?is)<[^>]+>").expect("tag regex must compile"));

static ROW_REGEX: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r#"(?is)<tr[^>]*class\s*=\s*[\"'][^\"']*\baf_table_data-row\b[^\"']*[\"'][^>]*>(.*?)</tr>"#,
    )
    .expect("row regex must compile")
});

static SPAN_REGEX: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r#"(?is)<span[^>]*class\s*=\s*[\"'][^\"']*\baf_column_data-container\b[^\"']*[\"'][^>]*>(.*?)</span>"#,
    )
    .expect("span regex must compile")
});

static ROW_SELECTOR: LazyLock<Selector> =
    LazyLock::new(|| Selector::parse("tr.af_table_data-row").expect("row selector must parse"));

static SPAN_SELECTOR: LazyLock<Selector> = LazyLock::new(|| {
    Selector::parse("span.af_column_data-container").expect("span selector must parse")
});

#[inline]
fn strip_tags(content: &str) -> String {
    TAG_REGEX.replace_all(content, "").trim().to_string()
}

fn extract_course_list_from_raw_html(html_content: &str) -> Vec<HashMap<String, String>> {
    let mut course_list = Vec::new();

    for row_capture in ROW_REGEX.captures_iter(html_content) {
        let row_inner_html = row_capture
            .get(1)
            .expect("row regex capture group must exist")
            .as_str();

        let mut spans = SPAN_REGEX.captures_iter(row_inner_html);
        let first_span = spans
            .next()
            .and_then(|cap| cap.get(1).map(|m| strip_tags(m.as_str())));
        let second_span = spans
            .next()
            .and_then(|cap| cap.get(1).map(|m| strip_tags(m.as_str())));

        if let (Some(course_code), Some(course_name)) = (first_span, second_span) {
            if !course_code.is_empty() {
                let mut entry = HashMap::new();
                entry.insert(course_code, course_name);
                course_list.push(entry);
            }
        }
    }

    course_list
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
/// Vec of HashMap entries where key=course_code, value=course_name
///
/// # Errors
/// Returns `SiaScraperError::MissingElement` if table structure invalid
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
/// assert_eq!(result[0].get("2015555"), Some(&"Algebra Lineal".to_string()));
/// ```
pub fn get_course_list(
    html_content: &str,
) -> Result<Vec<HashMap<String, String>>, SiaScraperError> {
    let html = Html::parse_document(html_content);

    let rows = html.select(&ROW_SELECTOR);
    let mut course_list = Vec::new();

    for row in rows {
        let data_spans: Vec<ElementRef> = row.select(&SPAN_SELECTOR).collect();

        if data_spans.len() >= 2 {
            let course_code = extract_text_from_elem(&data_spans[COURSE_CODE_COL]);
            let course_name = extract_text_from_elem(&data_spans[COURSE_NAME_COL]);

            if course_code.is_empty() {
                continue;
            }

            let mut entry = HashMap::new();
            entry.insert(course_code, course_name);
            course_list.push(entry);
        }
    }

    if course_list.is_empty() {
        return Ok(extract_course_list_from_raw_html(html_content));
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
        assert_eq!(
            result[0].get("2015555"),
            Some(&"Álgebra Lineal".to_string())
        );
        assert_eq!(
            result[1].get("2027641"),
            Some(&"Análisis de Datos".to_string())
        );
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
        assert_eq!(
            result[0].get("1000001"),
            Some(&"Cálculo Diferencial".to_string())
        );
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
        assert_eq!(result[0].get("1000002"), Some(&"Valid Course".to_string()));
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
        assert_eq!(
            result[0].get("2015555"),
            Some(&"Álgebra Lineal".to_string())
        );
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
        assert_eq!(
            result[0].get("2027309"),
            Some(&"Análisis forense digital &amp; más".to_string())
        );
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
        assert_eq!(result[0].get("2027641"), Some(&"Should Appear".to_string()));
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
        assert_eq!(result[0].get("2000000"), Some(&"Curso 0".to_string()));
        assert_eq!(result[99].get("2000099"), Some(&"Curso 99".to_string()));
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
        assert_eq!(result[0].get("1000001"), Some(&"CALCULO".to_string()));
    }
}
