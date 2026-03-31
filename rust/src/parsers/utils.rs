//! Shared utilities for parsing HTML/XML content.
//!
//! This module provides common helper functions used across multiple parsers.

use scraper::ElementRef;

/// Extracts text content from an HTML element, trimming whitespace.
///
/// # Arguments
/// * `elem` - A reference to an HTML element
///
/// # Returns
/// The trimmed text content of the element as a String
#[inline]
pub fn extract_text_from_elem(elem: &ElementRef<'_>) -> String {
    elem.text().collect::<String>().trim().to_string()
}

#[cfg(test)]
mod tests {
    use super::*;
    use scraper::{Html, Selector};

    #[test]
    fn test_extract_text_from_elem_simple() {
        let html = Html::parse_fragment("<span>Hello World</span>");
        let span = html
            .select(&Selector::parse("span").unwrap())
            .next()
            .unwrap();
        assert_eq!(extract_text_from_elem(&span), "Hello World");
    }

    #[test]
    fn test_extract_text_from_elem_with_whitespace() {
        let html = Html::parse_fragment("<span>  Hello   World  </span>");
        let span = html
            .select(&Selector::parse("span").unwrap())
            .next()
            .unwrap();
        assert_eq!(extract_text_from_elem(&span), "Hello   World");
    }

    #[test]
    fn test_extract_text_from_elem_nested() {
        let html = Html::parse_fragment("<div><span>Nested</span></div>");
        let span = html
            .select(&Selector::parse("span").unwrap())
            .next()
            .unwrap();
        assert_eq!(extract_text_from_elem(&span), "Nested");
    }

    #[test]
    fn test_extract_text_from_elem_empty() {
        let html = Html::parse_fragment("<span></span>");
        let span = html
            .select(&Selector::parse("span").unwrap())
            .next()
            .unwrap();
        assert_eq!(extract_text_from_elem(&span), "");
    }
}
