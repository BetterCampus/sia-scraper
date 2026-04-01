//! Course information and prerequisite parsing utilities.
//!
//! This module provides functions for extracting course data and prerequisites
//! from Oracle ADF XML/HTML responses returned by SIA's web interface.

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use pyo3::Py;
use regex::Regex;
use scraper::{ElementRef, Html, Selector};
use std::sync::LazyLock;

use crate::error::SiaScraperError;
use crate::models::course::{CourseInfoModel, GroupModel, ScheduleModel};
use crate::parsers::utils::extract_text_from_elem;

static SCHEDULE_REGEX: LazyLock<Result<Regex, String>> = LazyLock::new(|| {
    Regex::new(r"(\w+) de (\d{2}:\d{2}) a (\d{2}:\d{2})").map_err(|e| e.to_string())
});

const H2_SELECTOR: &str = "h2";
const CREDITS_SELECTOR: &str = "span.detass-creditos";
const CREDITS_SPAN_SELECTOR: &str = "span.detass-creditos span";
const TYPOLOGY_SPAN_SELECTOR: &str = "span.detass-tipologia span";
const GENERIC_SPAN_SELECTOR: &str = "span";
const LISTA_ELEMENTO_SELECTOR: &str = "span.lista-elemento";
const GROUP_TITLE_SELECTOR: &str = "h2.af_showDetailHeader_title-text0";
const PANEL_GROUP_SELECTOR: &str = "div.af_panelGroupLayout";
const DIV_SELECTOR: &str = "div";
const GROUP_CONTENT_SELECTOR: &str = ".af_showDetailHeader_content0";
const PREREQ_CONDITION_SELECTOR: &str =
    "span.borde.salto.af_panelGroupLayout > div.margin-t.af_panelGroupLayout";
const PREREQ_STRONG_SELECTOR: &str = "span.strong.af_panelGroupLayout";
const PREREQ_VALUE_SIBLING_SELECTOR: &str = "span.strong.af_panelGroupLayout + span";
const PREREQ_HEADER_SELECTOR: &str = "span.strong.af_panelGroupLayout > span.margin-l";
const PREREQ_SPAN_SELECTOR: &str = "span.af_panelGroupLayout > span";

const REQUIRED_PREREQ_HEADERS: usize = 4;

const TEACHER_LABELS: [&str; 4] = ["profesor", "teacher", "docente", "prof."];
const FACULTY_LABELS: [&str; 2] = ["facultad", "faculty"];
const DURATION_LABELS: [&str; 2] = ["duración", "duracion"];
const SCHEDULE_TYPE_LABELS: [&str; 2] = ["jornada", "schedule type"];
const SPOTS_LABELS: [&str; 2] = ["cupos", "spots"];

fn schedule_regex() -> Result<&'static Regex, SiaScraperError> {
    match &*SCHEDULE_REGEX {
        Ok(regex) => Ok(regex),
        Err(msg) => Err(SiaScraperError::ParseError(format!(
            "Schedule regex initialization failed: {msg}"
        ))),
    }
}

fn parse_selector(selector_str: &str) -> Result<Selector, SiaScraperError> {
    Selector::parse(selector_str).map_err(|e| {
        SiaScraperError::ParseError(format!(
            "Invalid selector '{selector_str}': {e:?}. This is a selector registry bug."
        ))
    })
}

fn css_select_html<'a>(
    root: &'a Html,
    selector_str: &str,
) -> Result<Vec<ElementRef<'a>>, SiaScraperError> {
    let selector = parse_selector(selector_str)?;
    Ok(root.select(&selector).collect())
}

fn css_select_elem<'a>(
    root: &'a ElementRef<'a>,
    selector_str: &str,
) -> Result<Vec<ElementRef<'a>>, SiaScraperError> {
    let selector = parse_selector(selector_str)?;
    Ok(root.select(&selector).collect())
}

fn html_snippet(html: &str) -> String {
    html.chars().take(220).collect()
}

fn elem_snippet(elem: &ElementRef<'_>) -> String {
    extract_text_from_elem(elem).chars().take(120).collect()
}

fn parse_error_with_context(
    field: &str,
    selector: &str,
    context: &str,
    snippet: &str,
    stack_context: &[&str],
) -> SiaScraperError {
    let stack = if stack_context.is_empty() {
        String::from("[]")
    } else {
        format!("[{}]", stack_context.join(" -> "))
    };
    SiaScraperError::ParseError(format!(
        "Field '{field}' parse failure\nSelector: {selector}\nContext: {context}\nHTML snippet: {snippet}\nStack: {stack}"
    ))
}

fn parse_error_with_elem_context(
    field: &str,
    selector: &str,
    context: &str,
    elem: &ElementRef<'_>,
    stack_context: &[&str],
) -> SiaScraperError {
    parse_error_with_context(field, selector, context, &elem_snippet(elem), stack_context)
}

#[inline]
pub fn get_plain_text(xml: &str) -> String {
    let document = Html::parse_document(xml);
    let full_text = document.root_element().text().collect::<String>();
    match full_text.split("\u{00A0}\u{00A0}\u{00A0}").next() {
        Some(text) => text.to_string(),
        None => String::new(),
    }
}

fn extract_credits(root: &Html, xml: &str) -> Result<i32, SiaScraperError> {
    let elems = css_select_html(root, CREDITS_SELECTOR)?;
    let elem = elems.first().ok_or_else(|| {
        parse_error_with_context(
            "credits",
            CREDITS_SELECTOR,
            "Required credits container was not found",
            &html_snippet(xml),
            &["parse_course_model", "extract_credits"],
        )
    })?;

    let spans = css_select_html(root, CREDITS_SPAN_SELECTOR)?;
    let span = spans.last().ok_or_else(|| {
        parse_error_with_elem_context(
            "credits",
            CREDITS_SPAN_SELECTOR,
            "Credits container exists but has no nested <span>",
            elem,
            &["parse_course_model", "extract_credits"],
        )
    })?;

    let text = extract_text_from_elem(span);
    text.parse::<i32>().map_err(|e| {
        parse_error_with_context(
            "credits",
            CREDITS_SPAN_SELECTOR,
            &format!("Expected integer credits, got '{text}'. Parse error: {e}"),
            &html_snippet(xml),
            &["parse_course_model", "extract_credits"],
        )
    })
}

fn extract_typology(root: &Html) -> Result<String, SiaScraperError> {
    let spans = css_select_html(root, TYPOLOGY_SPAN_SELECTOR)?;
    match spans.last() {
        Some(span) => {
            let text = extract_text_from_elem(span);
            if text.is_empty() {
                Ok("Unknown".to_string())
            } else {
                Ok(text)
            }
        }
        None => Ok("Unknown".to_string()),
    }
}

fn row_texts(panel: &ElementRef<'_>) -> Result<Vec<String>, SiaScraperError> {
    let rows = css_select_elem(panel, DIV_SELECTOR)?;
    Ok(rows.iter().map(extract_text_from_elem).collect())
}

fn extract_labeled_or_inferred_value(
    panel: &ElementRef<'_>,
    labels: &[&str],
    field_name: &str,
    required: bool,
) -> Result<Option<String>, SiaScraperError> {
    let rows = css_select_elem(panel, DIV_SELECTOR)?;
    for row in rows {
        let text = extract_text_from_elem(&row);
        let lowered = text.to_lowercase();
        if labels.iter().any(|label| lowered.contains(label)) {
            let spans = css_select_elem(&row, GENERIC_SPAN_SELECTOR)?;
            if spans.len() >= 2 {
                if let Some(last_span) = spans.last() {
                    let value = extract_text_from_elem(last_span);
                    if !value.is_empty() {
                        return Ok(Some(value));
                    }
                }
            }
            let mut cleaned = text;
            for label in labels {
                cleaned = cleaned.replace(label, "");
                cleaned = cleaned.replace(&label.to_uppercase(), "");
            }
            let value = cleaned.trim().trim_matches(':').trim().to_string();
            if !value.is_empty() {
                return Ok(Some(value));
            }
        }
    }

    if field_name == "teacher" {
        let rows_text = row_texts(panel)?;
        for row_text in rows_text {
            let lowered = row_text.to_lowercase();
            if lowered.contains("prof") || lowered.contains("docente") {
                let inferred = row_text.trim().to_string();
                if !inferred.is_empty() {
                    return Ok(Some(inferred));
                }
            }
        }
    }

    if required {
        return Err(parse_error_with_elem_context(
            field_name,
            "label-based field extraction",
            &format!(
                "Missing required field. Tried labels: {}",
                labels.join(", ")
            ),
            panel,
            &["parse_course_model", "extract_group_model"],
        ));
    }

    Ok(None)
}

fn extract_schedules(panel: &ElementRef<'_>) -> Result<Vec<ScheduleModel>, SiaScraperError> {
    let mut schedules: Vec<ScheduleModel> = Vec::new();
    let regex = schedule_regex()?;
    let lista_spans = css_select_elem(panel, LISTA_ELEMENTO_SELECTOR)?;

    for lista_span in lista_spans {
        let schedule_txt = extract_text_from_elem(&lista_span);
        if let Some(captures) = regex.captures(&schedule_txt) {
            let day = if let Some(match_value) = captures.get(1) {
                match_value.as_str().to_string()
            } else {
                continue;
            };
            let start_time = if let Some(match_value) = captures.get(2) {
                match_value.as_str().to_string()
            } else {
                continue;
            };
            let end_time = if let Some(match_value) = captures.get(3) {
                match_value.as_str().to_string()
            } else {
                continue;
            };

            if day.is_empty() || start_time.is_empty() || end_time.is_empty() {
                continue;
            }

            let nested_classroom = css_select_elem(&lista_span, LISTA_ELEMENTO_SELECTOR)?;
            let classroom = if let Some(classroom_elem) = nested_classroom.last() {
                extract_text_from_elem(classroom_elem)
            } else {
                String::new()
            };

            schedules.push(ScheduleModel {
                day,
                start_time,
                end_time,
                classroom,
            });
        }
    }

    Ok(schedules)
}

fn extract_spots(panel: &ElementRef<'_>) -> Result<Option<i64>, SiaScraperError> {
    let field = extract_labeled_or_inferred_value(panel, &SPOTS_LABELS, "spots", false)?;
    let Some(spots_text) = field else {
        return Ok(None);
    };

    let digits_only = spots_text
        .chars()
        .filter(|c| c.is_ascii_digit())
        .collect::<String>();

    if digits_only.is_empty() {
        return Ok(None);
    }

    match digits_only.parse::<i64>() {
        Ok(value) => Ok(Some(value)),
        Err(_) => Ok(None),
    }
}

fn extract_group_name(group: &ElementRef<'_>) -> Result<Option<String>, SiaScraperError> {
    if let Some(parent_ref) = group.parent().and_then(ElementRef::wrap) {
        let h2_elems = css_select_elem(&parent_ref, GROUP_TITLE_SELECTOR)?;
        if let Some(title_elem) = h2_elems.first() {
            let value = extract_text_from_elem(title_elem);
            if !value.is_empty() {
                return Ok(Some(value));
            }
        }
    }
    Ok(None)
}

fn extract_group_model(
    group: &ElementRef<'_>,
    course_name: &str,
    group_index: usize,
) -> Result<GroupModel, SiaScraperError> {
    let panel_elems = css_select_elem(group, PANEL_GROUP_SELECTOR)?;
    let panel = panel_elems.first().ok_or_else(|| {
        parse_error_with_elem_context(
            "group_panel",
            PANEL_GROUP_SELECTOR,
            &format!("Group {group_index} has no panel container"),
            group,
            &[
                "parse_course_model",
                "extract_groups",
                "extract_group_model",
            ],
        )
    })?;

    let group_name = extract_group_name(group)?.unwrap_or_else(|| "Unknown".to_string());
    let teacher = extract_labeled_or_inferred_value(panel, &TEACHER_LABELS, "teacher", true)?
        .ok_or_else(|| {
            parse_error_with_elem_context(
                "teacher",
                "teacher labels",
                &format!("Group {group_index} has no teacher value"),
                panel,
                &[
                    "parse_course_model",
                    "extract_groups",
                    "extract_group_model",
                ],
            )
        })?;

    let faculty = extract_labeled_or_inferred_value(panel, &FACULTY_LABELS, "faculty", false)?
        .unwrap_or_else(|| "Unknown".to_string());
    let duration = extract_labeled_or_inferred_value(panel, &DURATION_LABELS, "duration", false)?
        .unwrap_or_else(|| "Unknown".to_string());
    let schedule_type =
        extract_labeled_or_inferred_value(panel, &SCHEDULE_TYPE_LABELS, "schedule_type", false)?
            .unwrap_or_else(|| "Unknown".to_string());
    let schedules = extract_schedules(panel)?;
    let spots = extract_spots(panel)?;

    Ok(GroupModel {
        group_name,
        teacher,
        faculty,
        course_name: course_name.to_string(),
        schedules,
        duration,
        schedule_type,
        spots,
        code: None,
    })
}

fn extract_groups(root: &Html, course_name: &str) -> Result<Vec<GroupModel>, SiaScraperError> {
    let group_elems = css_select_html(root, GROUP_CONTENT_SELECTOR)?;
    let mut groups = Vec::with_capacity(group_elems.len());
    let mut errors: Vec<SiaScraperError> = Vec::new();

    for (idx, group) in group_elems.iter().enumerate() {
        match extract_group_model(group, course_name, idx) {
            Ok(model) => groups.push(model),
            Err(err) => errors.push(err),
        }
    }

    if !errors.is_empty() {
        let combined = errors
            .into_iter()
            .map(|e| e.to_string())
            .collect::<Vec<_>>()
            .join("\n---\n");
        return Err(SiaScraperError::ParseError(format!(
            "One or more groups failed strict parsing:\n{combined}"
        )));
    }

    Ok(groups)
}

#[cfg(all(feature = "fail-fast", not(feature = "full-error-collection")))]
fn parse_course_model(xml: &str) -> Result<CourseInfoModel, SiaScraperError> {
    let document = Html::parse_document(xml);
    let h2_elems = css_select_html(&document, H2_SELECTOR)?;
    let course_name = h2_elems
        .first()
        .map(extract_text_from_elem)
        .ok_or_else(|| {
            parse_error_with_context(
                "course_name",
                H2_SELECTOR,
                "Course title <h2> not found",
                &html_snippet(xml),
                &["parse_course_model"],
            )
        })?;

    let credits = extract_credits(&document, xml)?;
    let typology = extract_typology(&document)?;
    let groups = extract_groups(&document, &course_name)?;
    let available_spots = groups.iter().filter_map(|g| g.spots).sum::<i64>();

    Ok(CourseInfoModel {
        course_name,
        credits,
        typology,
        available_spots,
        scrape_timestamp: String::new(),
        groups,
        code: None,
    })
}

#[cfg(any(not(feature = "fail-fast"), feature = "full-error-collection"))]
fn parse_course_model(xml: &str) -> Result<CourseInfoModel, SiaScraperError> {
    let document = Html::parse_document(xml);
    let mut errors: Vec<SiaScraperError> = Vec::new();

    let course_name = {
        let h2_elems = css_select_html(&document, H2_SELECTOR)?;
        match h2_elems.first().map(extract_text_from_elem) {
            Some(value) if !value.is_empty() => Some(value),
            _ => {
                errors.push(parse_error_with_context(
                    "course_name",
                    H2_SELECTOR,
                    "Course title <h2> not found",
                    &html_snippet(xml),
                    &["parse_course_model"],
                ));
                None
            }
        }
    };

    let credits = match extract_credits(&document, xml) {
        Ok(v) => Some(v),
        Err(e) => {
            errors.push(e);
            None
        }
    };

    let typology = match extract_typology(&document) {
        Ok(v) => Some(v),
        Err(e) => {
            errors.push(e);
            None
        }
    };

    if !errors.is_empty() {
        let combined = errors
            .iter()
            .map(ToString::to_string)
            .collect::<Vec<_>>()
            .join("\n---\n");
        return Err(SiaScraperError::ParseError(format!(
            "Course parsing failed with aggregated errors:\n{combined}"
        )));
    }

    let course_name_value = course_name.ok_or_else(|| {
        SiaScraperError::ParseError("Course parsing failed: course_name missing".to_string())
    })?;
    let credits_value = credits.ok_or_else(|| {
        SiaScraperError::ParseError("Course parsing failed: credits missing".to_string())
    })?;
    let typology_value = typology.ok_or_else(|| {
        SiaScraperError::ParseError("Course parsing failed: typology missing".to_string())
    })?;

    let groups = extract_groups(&document, &course_name_value)?;
    let available_spots = groups.iter().filter_map(|g| g.spots).sum::<i64>();

    Ok(CourseInfoModel {
        course_name: course_name_value,
        credits: credits_value,
        typology: typology_value,
        available_spots,
        scrape_timestamp: String::new(),
        groups,
        code: None,
    })
}

/// Parse comprehensive course information from Oracle ADF course detail page and return JSON.
pub fn parse_course_model_json(xml: &str) -> Result<String, SiaScraperError> {
    let model = parse_course_model(xml)?;
    serde_json::to_string(&model)
        .map_err(|e| SiaScraperError::ParseError(format!("Course JSON serialization failed: {e}")))
}

/// Parse comprehensive course information from Oracle ADF course detail page.
pub fn parse_course_xml(xml: &str, py: Python<'_>) -> Result<Py<PyAny>, SiaScraperError> {
    let model = parse_course_model(xml)?;

    let result = PyDict::new(py);
    result.set_item("course_name", &model.course_name)?;
    result.set_item("credits", model.credits)?;
    result.set_item("typology", &model.typology)?;
    result.set_item("available_spots", model.available_spots)?;
    result.set_item("scrape_timestamp", &model.scrape_timestamp)?;
    result.set_item("code", py.None())?;

    let groups_list = PyList::empty(py);
    for group in model.groups {
        let group_dict = PyDict::new(py);
        group_dict.set_item("group_name", group.group_name)?;
        group_dict.set_item("teacher", group.teacher)?;
        group_dict.set_item("faculty", group.faculty)?;
        group_dict.set_item("course_name", group.course_name)?;
        group_dict.set_item("duration", group.duration)?;
        group_dict.set_item("schedule_type", group.schedule_type)?;
        match group.spots {
            Some(spots) => group_dict.set_item("spots", spots)?,
            None => group_dict.set_item("spots", 0_i64)?,
        }
        group_dict.set_item("code", py.None())?;

        let schedules_list = PyList::empty(py);
        for schedule in group.schedules {
            let schedule_dict = PyDict::new(py);
            schedule_dict.set_item("day", schedule.day)?;
            schedule_dict.set_item("start_time", schedule.start_time)?;
            schedule_dict.set_item("end_time", schedule.end_time)?;
            schedule_dict.set_item("classroom", schedule.classroom)?;
            schedules_list.append(schedule_dict)?;
        }

        group_dict.set_item("schedules", schedules_list)?;
        groups_list.append(group_dict)?;
    }

    result.set_item("groups", groups_list)?;
    Ok(result.into())
}

/// Parse course prerequisites and enrollment conditions from Oracle ADF XML.
pub fn parse_prereqs_xml(xml: &str, py: Python<'_>) -> Result<Py<PyAny>, SiaScraperError> {
    let document = Html::parse_document(xml);

    let h2_elems = css_select_html(&document, H2_SELECTOR)?;
    let course_name = h2_elems
        .first()
        .map(extract_text_from_elem)
        .ok_or_else(|| {
            parse_error_with_context(
                "course_name",
                H2_SELECTOR,
                "Course name not found",
                &html_snippet(xml),
                &["parse_prereqs_xml"],
            )
        })?;

    let credits = extract_credits(&document, xml)?;
    let typology = extract_typology(&document)?;

    let condition_divs = css_select_html(&document, PREREQ_CONDITION_SELECTOR)?;

    let conditions = PyList::empty(py);

    for condition_div in condition_divs {
        let sub_divs: Vec<ElementRef<'_>> = css_select_elem(&condition_div, DIV_SELECTOR)?;
        if sub_divs.len() < 2 {
            continue;
        }

        let info_div = &sub_divs[0];
        let strong_spans = css_select_elem(info_div, PREREQ_STRONG_SELECTOR)?;

        let mut all_spans: Vec<ElementRef<'_>> = Vec::new();
        if let Some(strong_span) = strong_spans.first() {
            for nested_span in css_select_elem(strong_span, GENERIC_SPAN_SELECTOR)? {
                let is_header = nested_span
                    .value()
                    .classes()
                    .any(|class_name| class_name == "margin-l");
                if !is_header {
                    all_spans.push(nested_span);
                }
            }
        }

        let header_spans = css_select_elem(info_div, PREREQ_HEADER_SELECTOR)?;
        let header_count = header_spans.len();
        if header_count < REQUIRED_PREREQ_HEADERS {
            continue;
        }

        if all_spans.len() < header_count {
            all_spans = css_select_elem(info_div, PREREQ_VALUE_SIBLING_SELECTOR)?;
        }

        let mut header_values: Vec<String> = Vec::with_capacity(header_count);
        for index in 0..header_count {
            if let Some(value_span) = all_spans.get(index) {
                header_values.push(extract_text_from_elem(value_span));
            } else {
                header_values.push(String::new());
            }
        }

        let prereqs = PyList::empty(py);
        for prereq_div in &sub_divs[1..] {
            let prereq_spans = css_select_elem(prereq_div, PREREQ_SPAN_SELECTOR)?;
            if prereq_spans.len() < 2 {
                continue;
            }

            let course_code = extract_text_from_elem(&prereq_spans[0]);
            let course_name_prereq = extract_text_from_elem(&prereq_spans[1]);

            let prereq_dict = PyDict::new(py);
            prereq_dict.set_item("course_code", course_code)?;
            prereq_dict.set_item("course_name", course_name_prereq)?;
            prereqs.append(prereq_dict)?;
        }

        let condition_dict = PyDict::new(py);
        condition_dict.set_item("condition", &header_values[0])?;
        condition_dict.set_item("type", &header_values[1])?;
        condition_dict.set_item("all_required", &header_values[2])?;
        condition_dict.set_item("number_of_courses", &header_values[3])?;
        condition_dict.set_item("prerequisites", prereqs)?;
        conditions.append(condition_dict)?;
    }

    let result = PyDict::new(py);
    result.set_item("course_name", course_name.trim())?;
    result.set_item("code", py.None())?;
    result.set_item("credits", credits)?;
    result.set_item("typology", typology)?;
    result.set_item("conditions", conditions)?;

    Ok(result.into())
}
