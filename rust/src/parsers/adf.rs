use crate::error::SiaScraperError;
use scraper::{Html, Selector};

pub fn extract_view_state(html: &str) -> Result<String, SiaScraperError> {
    let document = Html::parse_document(html);

    let selector = Selector::parse("input[name*='ViewState'], input[id*='ViewState']")
        .map_err(|e| SiaScraperError::ParseError(e.to_string()))?;

    for element in document.select(&selector) {
        if let Some(value) = element.value().attr("value") {
            return Ok(value.to_string());
        }
    }

    Err(SiaScraperError::ExtractionError(
        "ViewState not found".to_string(),
    ))
}
