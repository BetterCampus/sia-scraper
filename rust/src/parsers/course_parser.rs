use crate::error::SiaScraperError;
use pyo3::prelude::*;
use scraper::{ElementRef, Html, Selector};

fn css_select<'a>(root: &'a Html, selector_str: &'a str) -> Vec<ElementRef<'a>> {
    let selector = match Selector::parse(selector_str) {
        Ok(s) => s,
        Err(_) => return vec![],
    };
    root.select(&selector).collect()
}

fn extract_text_from_elem(elem: &ElementRef<'_>) -> String {
    elem.text().collect::<String>().trim().to_string()
}

fn extract_credits(root: &Html) -> Result<i32, SiaScraperError> {
    let elems = css_select(root, "span.detass-creditos");
    let elem = elems
        .first()
        .ok_or_else(|| SiaScraperError::ParseError("Credits element not found".to_string()))?;

    // Get child spans of the credits element using descendant selector
    let spans = css_select(root, "span.detass-creditos span");
    let span = spans
        .last()
        .ok_or_else(|| SiaScraperError::ParseError("Credits span not found".to_string()))?;

    let text = extract_text_from_elem(span);
    text.parse::<i32>()
        .map_err(|_| SiaScraperError::ParseError("Failed to parse credits".to_string()))
}

fn extract_typology(root: &Html) -> String {
    let elems = css_select(root, "span.detass-tipologia");
    match elems.first() {
        Some(_elem) => {
            let spans = css_select(root, "span");
            spans
                .last()
                .map(|s| extract_text_from_elem(s))
                .unwrap_or_else(|| "Unknown".to_string())
        }
        None => "Unknown".to_string(),
    }
}

pub fn parse_course_xml(xml: &str, py: Python<'_>) -> Result<Py<PyAny>, SiaScraperError> {
    let document = Html::parse_document(xml);

    // Find course name (h2 element)
    let h2_elems = css_select(&document, "h2");
    let course_name = h2_elems
        .first()
        .map(|e| extract_text_from_elem(&e))
        .ok_or_else(|| SiaScraperError::ParseError("Course name not found".to_string()))?;

    let credits = extract_credits(&document)?;
    let typology = extract_typology(&document);

    // Extract groups - simplified placeholder
    let group_elems = css_select(&document, ".af_showDetailHeader_content0");

    let mut group_list: Vec<pyo3::Py<pyo3::types::PyAny>> = Vec::new();
    let available_spots = 0;

    for _group in group_elems {
        let dict = pyo3::types::PyDict::new(py);
        let _ = dict.set_item("group_name", "Unknown");
        let _ = dict.set_item("teacher", "Not reported");
        let _ = dict.set_item("faculty", "Unknown");
        let _ = dict.set_item("course_name", &course_name);
        let empty_list: Vec<pyo3::Py<pyo3::types::PyAny>> = vec![];
        let _ = dict.set_item("schedules", pyo3::types::PyList::new(py, &empty_list));
        let _ = dict.set_item("duration", "Unknown");
        let _ = dict.set_item("schedule_type", "Unknown");
        let _ = dict.set_item("spots", 0i64);
        let _ = dict.set_item("code", py.None());
        group_list.push(dict.into_py(py));
    }

    let result = pyo3::types::PyDict::new(py);
    let _ = result.set_item("course_name", &course_name);
    let _ = result.set_item("credits", credits);
    let _ = result.set_item("typology", &typology);
    let _ = result.set_item("available_spots", available_spots);
    let _ = result.set_item("groups", pyo3::types::PyList::new(py, &group_list));
    let _ = result.set_item("scrape_timestamp", "");
    let _ = result.set_item("code", py.None());

    Ok(result.into())
}

pub fn parse_prereqs_xml(xml: &str, py: Python<'_>) -> Result<Py<PyAny>, SiaScraperError> {
    let document = Html::parse_document(xml);

    let h2_elems = css_select(&document, "h2");
    let course_name = h2_elems
        .first()
        .map(|e| extract_text_from_elem(&e))
        .ok_or_else(|| SiaScraperError::ParseError("Course name not found".to_string()))?;

    let credits = extract_credits(&document)?;
    let typology = extract_typology(&document);

    let result = pyo3::types::PyDict::new(py);
    let _ = result.set_item("course_name", course_name.trim());
    let _ = result.set_item("code", py.None());
    let _ = result.set_item("credits", credits);
    let _ = result.set_item("typology", typology);
    let empty_conditions: Vec<pyo3::Py<pyo3::types::PyAny>> = vec![];
    let _ = result.set_item(
        "conditions",
        pyo3::types::PyList::new(py, &empty_conditions),
    );

    Ok(result.into())
}
