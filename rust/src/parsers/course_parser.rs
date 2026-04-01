//! Course information and prerequisite parsing utilities.
//!
//! This module provides functions for extracting course data and prerequisites
//! from Oracle ADF XML/HTML responses returned by SIA's web interface.

use crate::error::SiaScraperError;
use crate::parsers::utils::extract_text_from_elem;
use pyo3::prelude::*;
use pyo3::Py;
use regex::Regex;
use scraper::{ElementRef, Html, Selector};
use std::sync::LazyLock;

static SCHEDULE_REGEX: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(\w+) de (\d{2}:\d{2}) a (\d{2}:\d{2})").unwrap());

static H2_SELECTOR: LazyLock<Selector> =
    LazyLock::new(|| Selector::parse("h2").expect("h2 selector must parse"));
static CREDITS_SELECTOR: LazyLock<Selector> =
    LazyLock::new(|| Selector::parse("span.detass-creditos").expect("credits selector must parse"));
static CREDITS_SPAN_SELECTOR: LazyLock<Selector> = LazyLock::new(|| {
    Selector::parse("span.detass-creditos span").expect("credits span selector must parse")
});
static TYPOLOGY_SELECTOR: LazyLock<Selector> = LazyLock::new(|| {
    Selector::parse("span.detass-tipologia").expect("typology selector must parse")
});
static TYPOLOGY_SPAN_SELECTOR: LazyLock<Selector> = LazyLock::new(|| {
    Selector::parse("span.detass-tipologia span").expect("typology span selector must parse")
});
static GENERIC_SPAN_SELECTOR: LazyLock<Selector> =
    LazyLock::new(|| Selector::parse("span").expect("span selector must parse"));
static LISTA_ELEMENTO_SELECTOR: LazyLock<Selector> = LazyLock::new(|| {
    Selector::parse("span.lista-elemento").expect("lista-elemento selector must parse")
});
static GROUP_TITLE_SELECTOR: LazyLock<Selector> = LazyLock::new(|| {
    Selector::parse("h2.af_showDetailHeader_title-text0").expect("group title selector must parse")
});
static PANEL_GROUP_SELECTOR: LazyLock<Selector> = LazyLock::new(|| {
    Selector::parse("div.af_panelGroupLayout").expect("panel group selector must parse")
});
static DIV_SELECTOR: LazyLock<Selector> =
    LazyLock::new(|| Selector::parse("div").expect("div selector must parse"));
static GROUP_CONTENT_SELECTOR: LazyLock<Selector> = LazyLock::new(|| {
    Selector::parse(".af_showDetailHeader_content0").expect("group content selector must parse")
});
static PREREQ_CONDITION_SELECTOR: LazyLock<Selector> = LazyLock::new(|| {
    Selector::parse("span.borde.salto.af_panelGroupLayout > div.margin-t.af_panelGroupLayout")
        .expect("prereq condition selector must parse")
});
static PREREQ_STRONG_SELECTOR: LazyLock<Selector> = LazyLock::new(|| {
    Selector::parse("span.strong.af_panelGroupLayout").expect("prereq strong selector must parse")
});
static PREREQ_VALUE_SIBLING_SELECTOR: LazyLock<Selector> = LazyLock::new(|| {
    Selector::parse("span.strong.af_panelGroupLayout + span")
        .expect("prereq sibling value selector must parse")
});
static PREREQ_HEADER_SELECTOR: LazyLock<Selector> = LazyLock::new(|| {
    Selector::parse("span.strong.af_panelGroupLayout > span.margin-l")
        .expect("prereq header selector must parse")
});
static PREREQ_SPAN_SELECTOR: LazyLock<Selector> = LazyLock::new(|| {
    Selector::parse("span.af_panelGroupLayout > span").expect("prereq span selector must parse")
});

const GROUP_TEACHER_INDEX: usize = 0;
const GROUP_FACULTY_INDEX: usize = 1;
const GROUP_SCHEDULES_INDEX: usize = 2;
const GROUP_DURATION_INDEX: usize = 3;
const GROUP_SCHEDULE_TYPE_INDEX: usize = 4;
const GROUP_SPOTS_INDEX: usize = 5;
const MIN_GROUP_DATA_LENGTH_WITH_SPOTS: usize = 6;

fn css_select_html<'a>(root: &'a Html, selector: &Selector) -> Vec<ElementRef<'a>> {
    root.select(selector).collect()
}

#[inline]
fn css_select_elem<'a>(root: &'a ElementRef<'a>, selector: &Selector) -> Vec<ElementRef<'a>> {
    root.select(selector).collect()
}

#[inline]
pub fn get_plain_text(xml: &str) -> String {
    let document = Html::parse_document(xml);
    let full_text = document.root_element().text().collect::<String>();
    full_text
        .split("\u{00A0}\u{00A0}\u{00A0}")
        .next()
        .unwrap_or_default()
        .to_string()
}

#[inline]
fn extract_credits(root: &Html) -> Result<i32, SiaScraperError> {
    let elems = css_select_html(root, &CREDITS_SELECTOR);
    let _elem = elems
        .first()
        .ok_or_else(|| SiaScraperError::ParseError("Credits element not found".to_string()))?;

    let spans = css_select_html(root, &CREDITS_SPAN_SELECTOR);
    let span = spans
        .last()
        .ok_or_else(|| SiaScraperError::ParseError("Credits span not found".to_string()))?;

    let text = extract_text_from_elem(span);
    text.parse::<i32>()
        .map_err(|_| SiaScraperError::ParseError("Failed to parse credits".to_string()))
}

#[inline]
fn extract_typology(root: &Html) -> String {
    let elems = css_select_html(root, &TYPOLOGY_SELECTOR);
    match elems.first() {
        Some(_elem) => {
            let spans = css_select_html(root, &TYPOLOGY_SPAN_SELECTOR);
            spans
                .last()
                .map(|s| extract_text_from_elem(s))
                .unwrap_or_else(|| "Unknown".to_string())
        }
        None => "Unknown".to_string(),
    }
}

#[inline]
fn extract_label_value(elem: &ElementRef<'_>) -> String {
    let spans = css_select_elem(elem, &GENERIC_SPAN_SELECTOR);
    match spans.last() {
        Some(s) => {
            let text = extract_text_from_elem(s);
            if text.is_empty() {
                "Unknown".to_string()
            } else {
                text
            }
        }
        None => "Unknown".to_string(),
    }
}

fn extract_schedules(elem: &ElementRef<'_>) -> Vec<Py<pyo3::types::PyAny>> {
    let mut schedules: Vec<Py<pyo3::types::PyAny>> = Vec::new();

    let lista_spans = css_select_elem(elem, &LISTA_ELEMENTO_SELECTOR);

    for lista_span in lista_spans {
        let nested_classroom = css_select_elem(&lista_span, &LISTA_ELEMENTO_SELECTOR);
        if nested_classroom.is_empty() {
            continue;
        }

        let schedule_txt = extract_text_from_elem(&lista_span);

        if let Some(captures) = SCHEDULE_REGEX.captures(&schedule_txt) {
            let day = captures.get(1).map_or("", |m| m.as_str());
            let start_time = captures.get(2).map_or("", |m| m.as_str());
            let end_time = captures.get(3).map_or("", |m| m.as_str());

            let classroom = nested_classroom
                .last()
                .map(|c| extract_text_from_elem(c))
                .unwrap_or_default();

            Python::with_gil(|py| {
                let dict = pyo3::types::PyDict::new(py);
                let _ = dict.set_item("day", day);
                let _ = dict.set_item("start_time", start_time);
                let _ = dict.set_item("end_time", end_time);
                let _ = dict.set_item("classroom", classroom);
                schedules.push(dict.into_py(py));
            });
        }
    }

    schedules
}

#[inline]
fn extract_spots(elem: &ElementRef<'_>) -> Option<i64> {
    let spans = css_select_elem(elem, &GENERIC_SPAN_SELECTOR);
    if spans.is_empty() {
        return None;
    }
    let last_span = spans.last()?;
    let text = extract_text_from_elem(last_span);
    text.trim().parse::<i64>().ok()
}

fn extract_group(
    group: &ElementRef<'_>,
    course_name: &str,
) -> Option<(Py<pyo3::types::PyAny>, i64)> {
    let group_name = extract_group_name(group)?;
    let fields = extract_group_fields(group)?;
    let spots = fields.spots;

    let dict = Python::with_gil(|py| {
        let dict = pyo3::types::PyDict::new(py);
        let _ = dict.set_item("group_name", &group_name);
        let _ = dict.set_item("teacher", &fields.teacher);
        let _ = dict.set_item("faculty", &fields.faculty);
        let _ = dict.set_item("course_name", course_name);
        let _ = dict.set_item("schedules", pyo3::types::PyList::new(py, &fields.schedules));
        let _ = dict.set_item("duration", &fields.duration);
        let _ = dict.set_item("schedule_type", &fields.schedule_type);
        let _ = dict.set_item("spots", fields.spots);
        let _ = dict.set_item("code", py.None());
        dict.into_py(py)
    });

    Some((dict, spots))
}

fn extract_group_name(group: &ElementRef<'_>) -> Option<String> {
    let parent_ref = group.parent().and_then(ElementRef::wrap).unwrap_or(*group);
    let h2_elems = css_select_elem(&parent_ref, &GROUP_TITLE_SELECTOR);
    h2_elems.first().map(|e| extract_text_from_elem(e))
}

struct GroupFields {
    teacher: String,
    faculty: String,
    schedules: Vec<Py<pyo3::types::PyAny>>,
    duration: String,
    schedule_type: String,
    spots: i64,
}

fn extract_group_fields(group: &ElementRef<'_>) -> Option<GroupFields> {
    let panel_elems = css_select_elem(group, &PANEL_GROUP_SELECTOR);
    if panel_elems.is_empty() {
        return None;
    }

    let panel = &panel_elems[0];
    let group_data: Vec<ElementRef<'_>> = css_select_elem(panel, &DIV_SELECTOR);

    if group_data.is_empty() {
        return None;
    }

    let teacher_elems = css_select_elem(&group_data[GROUP_TEACHER_INDEX], &GENERIC_SPAN_SELECTOR);
    let teacher = teacher_elems
        .last()
        .map(|e| extract_text_from_elem(e))
        .unwrap_or_default();

    let faculty = if group_data.len() > GROUP_FACULTY_INDEX {
        extract_label_value(&group_data[GROUP_FACULTY_INDEX])
    } else {
        "Unknown".to_string()
    };

    let schedules = if group_data.len() > GROUP_SCHEDULES_INDEX {
        extract_schedules(&group_data[GROUP_SCHEDULES_INDEX])
    } else {
        vec![]
    };

    let duration = if group_data.len() > GROUP_DURATION_INDEX {
        extract_label_value(&group_data[GROUP_DURATION_INDEX])
    } else {
        "Unknown".to_string()
    };

    let schedule_type = if group_data.len() > GROUP_SCHEDULE_TYPE_INDEX {
        extract_label_value(&group_data[GROUP_SCHEDULE_TYPE_INDEX])
    } else {
        "Unknown".to_string()
    };

    let spots = if group_data.len() >= MIN_GROUP_DATA_LENGTH_WITH_SPOTS {
        extract_spots(&group_data[GROUP_SPOTS_INDEX]).unwrap_or(0)
    } else {
        0
    };

    Some(GroupFields {
        teacher,
        faculty,
        schedules,
        duration,
        schedule_type,
        spots,
    })
}

/// Parse comprehensive course information from Oracle ADF course detail page.
///
/// # Arguments
/// * `xml` - Raw XML/HTML string from SIA course detail page
/// * `py` - Python interpreter GIL handle
///
/// # Returns
/// Python dictionary with course_name, credits, typology, available_spots, groups, scrape_timestamp, code
///
/// # Errors
/// Returns SiaScraperError if course name or credits not found
pub fn parse_course_xml(xml: &str, py: Python<'_>) -> Result<Py<PyAny>, SiaScraperError> {
    let document = Html::parse_document(xml);

    let h2_elems = css_select_html(&document, &H2_SELECTOR);
    let course_name = h2_elems
        .first()
        .map(|e| extract_text_from_elem(e))
        .ok_or_else(|| SiaScraperError::ParseError("Course name not found".to_string()))?;

    let credits = extract_credits(&document)?;
    let typology = extract_typology(&document);

    let group_elems = css_select_html(&document, &GROUP_CONTENT_SELECTOR);

    let mut group_list: Vec<Py<pyo3::types::PyAny>> = Vec::new();
    let mut available_spots: i64 = 0;

    for group in &group_elems {
        if let Some((group_dict, spots)) = extract_group(group, &course_name) {
            available_spots += spots;
            group_list.push(group_dict);
        }
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

/// Parse course prerequisites and enrollment conditions from Oracle ADF XML.
///
/// # Arguments
/// * `xml` - Raw XML/HTML string from SIA course prerequisites page
/// * `py` - Python interpreter GIL handle
///
/// # Returns
/// Python dictionary with course_name, code, credits, typology, conditions
///
/// # Errors
/// Returns SiaScraperError if course name or credits not found
pub fn parse_prereqs_xml(xml: &str, py: Python<'_>) -> Result<Py<PyAny>, SiaScraperError> {
    let document = Html::parse_document(xml);

    let h2_elems = css_select_html(&document, &H2_SELECTOR);
    let course_name = h2_elems
        .first()
        .map(|e| extract_text_from_elem(e))
        .ok_or_else(|| SiaScraperError::ParseError("Course name not found".to_string()))?;

    let credits = extract_credits(&document)?;
    let typology = extract_typology(&document);

    let condition_divs = css_select_html(&document, &PREREQ_CONDITION_SELECTOR);

    let mut conditions: Vec<Py<pyo3::types::PyAny>> = Vec::new();

    for condition_div in condition_divs {
        let sub_divs: Vec<ElementRef<'_>> = css_select_elem(&condition_div, &DIV_SELECTOR);

        if sub_divs.len() < 2 {
            continue;
        }

        let info_div = &sub_divs[0];
        let strong_spans = css_select_elem(info_div, &PREREQ_STRONG_SELECTOR);
        let mut all_spans: Vec<ElementRef<'_>> = Vec::new();
        if let Some(strong_span) = strong_spans.first() {
            for nested_span in css_select_elem(strong_span, &GENERIC_SPAN_SELECTOR) {
                let is_header = nested_span
                    .value()
                    .classes()
                    .any(|class_name| class_name == "margin-l");
                if !is_header {
                    all_spans.push(nested_span);
                }
            }
        }

        let header_spans = css_select_elem(info_div, &PREREQ_HEADER_SELECTOR);
        let header_count = header_spans.len();

        if header_count < 4 {
            continue;
        }

        if all_spans.len() < header_count {
            all_spans = css_select_elem(info_div, &PREREQ_VALUE_SIBLING_SELECTOR);
        }

        let mut header_values: Vec<String> = Vec::new();
        for i in 0..header_count {
            if let Some(value_span) = all_spans.get(i) {
                header_values.push(extract_text_from_elem(value_span));
            } else {
                header_values.push(String::new());
            }
        }

        let mut prereqs: Vec<Py<pyo3::types::PyAny>> = Vec::new();
        for prereq_div in &sub_divs[1..] {
            let prereq_spans = css_select_elem(prereq_div, &PREREQ_SPAN_SELECTOR);
            if prereq_spans.len() < 2 {
                continue;
            }

            let course_code = extract_text_from_elem(&prereq_spans[0]);
            let course_name_prereq = extract_text_from_elem(&prereq_spans[1]);

            Python::with_gil(|py| {
                let dict = pyo3::types::PyDict::new(py);
                let _ = dict.set_item("course_code", &course_code);
                let _ = dict.set_item("course_name", &course_name_prereq);
                prereqs.push(dict.into_py(py));
            });
        }

        Python::with_gil(|py| {
            let dict = pyo3::types::PyDict::new(py);
            let _ = dict.set_item("condition", &header_values[0]);
            let _ = dict.set_item("type", &header_values[1]);
            let _ = dict.set_item("all_required", &header_values[2]);
            let _ = dict.set_item("number_of_courses", &header_values[3]);
            let _ = dict.set_item("prerequisites", pyo3::types::PyList::new(py, &prereqs));
            conditions.push(dict.into_py(py));
        });
    }

    let result = pyo3::types::PyDict::new(py);
    let _ = result.set_item("course_name", course_name.trim());
    let _ = result.set_item("code", py.None());
    let _ = result.set_item("credits", credits);
    let _ = result.set_item("typology", typology);
    let _ = result.set_item("conditions", pyo3::types::PyList::new(py, &conditions));

    Ok(result.into())
}
