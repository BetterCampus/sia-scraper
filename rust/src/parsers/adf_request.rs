//! Oracle ADF request body builder utilities.

use std::collections::HashMap;

use crate::error::SiaScraperError;

const STUDY_LEVEL_DD_ID: &str = "pt1:r1:0:soc1";
const CAMPUS_DD_ID: &str = "pt1:r1:0:soc9";
const FACULTY_DD_ID: &str = "pt1:r1:0:soc2";
const CAREER_DD_ID: &str = "pt1:r1:0:soc3";
const TIPOLOGY_DD_ID: &str = "pt1:r1:0:soc4";
const SHOW_COURSES_BTTN_ID: &str = "pt1:r1:0:cb1";
const FACULTY_CAREER_DD_ID: &str = "pt1:r1:0:soc5";
const CAMPUS_ELECTIVES_DD_ID: &str = "pt1:r1:0:soc6";
const SELECT_ROW_ID: &str = "pt1:r1:0:t4";

const ORACLE_ADF_REGION_ID: &str = "pt1:r1";
const ORACLE_ADF_RENDER_TARGET: &str = "pt1:r1";

const ORACLE_ADF_UNKNOWN_COMPONENT_1: &str = "pt1:r1:0:soc5";
const ORACLE_ADF_UNKNOWN_COMPONENT_2: &str = "pt1:r1:0:soc10";
const ORACLE_ADF_UNKNOWN_COMPONENT_3: &str = "pt1:r1:0:it10";
const ORACLE_ADF_UNKNOWN_COMPONENT_4: &str = "pt1:r1:0:it11";

const DROPDOWN_EVENT_VALUE: &str = r#"<m xmlns="http://oracle.com/richClient/comm"><k v="autoSubmit"><b>1</b></k><k v="suppressMessageShow"><s>true</s></k><k v="type"><s>valueChange</s></k></m>"#;
const BTTN_EVENT_VALUE: &str =
    r#"<m xmlns="http://oracle.com/richClient/comm"><k v="type"><s>action</s></k></m>"#;
const SELECT_ROW_EVENT_VALUE: &str =
    r#"<m xmlns="http://oracle.com/richClient/comm"><k v="type"><s>selection</s></k></m>"#;

const FACULTY_CAREER_DEFAULT_INDEX: &str = "0";
const ELECTIVES_CAMPUS_INCREMENT: i32 = 40;

const FACULTY_CAREER_DD: &str = "FACULTY_CAREER_DD";
const CAMPUS_ELECTIVES_DD: &str = "CAMPUS_ELECTIVES_DD";
const SELECT_ROW: &str = "SELECT_ROW";
const COURSE_PAGE_LINK: &str = "COURSE_PAGE_LINK";

#[inline]
fn data_map_entry(action: &str) -> Option<(&'static str, &'static str)> {
    match action {
        "STUDY_LEVEL_DD" => Some((STUDY_LEVEL_DD_ID, DROPDOWN_EVENT_VALUE)),
        "CAMPUS_DD" => Some((CAMPUS_DD_ID, DROPDOWN_EVENT_VALUE)),
        "FACULTY_DD" => Some((FACULTY_DD_ID, DROPDOWN_EVENT_VALUE)),
        "CAREER_DD" => Some((CAREER_DD_ID, DROPDOWN_EVENT_VALUE)),
        "TIPOLOGY_DD" => Some((TIPOLOGY_DD_ID, DROPDOWN_EVENT_VALUE)),
        "SHOW_COURSES_BTTN" => Some((SHOW_COURSES_BTTN_ID, BTTN_EVENT_VALUE)),
        FACULTY_CAREER_DD => Some((FACULTY_CAREER_DD_ID, DROPDOWN_EVENT_VALUE)),
        CAMPUS_ELECTIVES_DD => Some((CAMPUS_ELECTIVES_DD_ID, DROPDOWN_EVENT_VALUE)),
        SELECT_ROW => Some((SELECT_ROW_ID, SELECT_ROW_EVENT_VALUE)),
        COURSE_PAGE_LINK => Some((SELECT_ROW_ID, BTTN_EVENT_VALUE)),
        "BACK_BTTN" => Some(("pt1:r1:1:cb4", BTTN_EVENT_VALUE)),
        _ => None,
    }
}

/// Request builder state for Oracle ADF requests.
#[derive(Debug, Clone)]
pub struct OracleAdfRequestBuilderState {
    /// Current request dictionary template.
    pub request_dict: HashMap<String, String>,
}

impl OracleAdfRequestBuilderState {
    /// Creates empty builder state.
    pub fn new() -> Self {
        Self {
            request_dict: HashMap::new(),
        }
    }

    /// Initializes base Oracle ADF request dictionary.
    pub fn init_request_dict(
        &mut self,
        tipology_index: &str,
        window_id: &str,
        page_id: &str,
        view_state: &str,
    ) -> &HashMap<String, String> {
        self.request_dict.clear();

        self.request_dict
            .insert(STUDY_LEVEL_DD_ID.to_string(), String::new());
        self.request_dict
            .insert(CAMPUS_DD_ID.to_string(), String::new());
        self.request_dict
            .insert(FACULTY_DD_ID.to_string(), String::new());
        self.request_dict
            .insert(CAREER_DD_ID.to_string(), String::new());
        self.request_dict
            .insert(TIPOLOGY_DD_ID.to_string(), tipology_index.to_string());
        self.request_dict
            .insert(SHOW_COURSES_BTTN_ID.to_string(), String::new());
        self.request_dict
            .insert(ORACLE_ADF_UNKNOWN_COMPONENT_1.to_string(), String::new());
        self.request_dict
            .insert(ORACLE_ADF_UNKNOWN_COMPONENT_2.to_string(), String::new());
        self.request_dict
            .insert(ORACLE_ADF_UNKNOWN_COMPONENT_3.to_string(), String::new());
        self.request_dict
            .insert(ORACLE_ADF_UNKNOWN_COMPONENT_4.to_string(), String::new());
        self.request_dict.insert(
            "org.apache.myfaces.trinidad.faces.FORM".to_string(),
            "f1".to_string(),
        );
        self.request_dict
            .insert("Adf-Window-Id".to_string(), window_id.to_string());
        self.request_dict
            .insert("Adf-Page-Id".to_string(), page_id.to_string());
        self.request_dict
            .insert("javax.faces.ViewState".to_string(), view_state.to_string());

        &self.request_dict
    }

    /// Builds request body for one data map action.
    pub fn build_request_body(
        mut self,
        data_name: &str,
        idx: i32,
        career_indices: &[String],
        course_list_len: usize,
    ) -> Result<HashMap<String, String>, SiaScraperError> {
        let (component_id, event_value) = data_map_entry(data_name).ok_or_else(|| {
            SiaScraperError::InvalidInput(format!("Unknown data_name in DATA_MAP: {}", data_name))
        })?;

        if data_name == FACULTY_CAREER_DD {
            self.request_dict.insert(
                FACULTY_CAREER_DD_ID.to_string(),
                FACULTY_CAREER_DEFAULT_INDEX.to_string(),
            );
        } else if data_name == CAMPUS_ELECTIVES_DD {
            let second_index = career_indices
                .get(1)
                .ok_or_else(|| {
                    SiaScraperError::InvalidInput(
                        "career_indices must have at least two elements".to_string(),
                    )
                })?
                .parse::<i32>()
                .map_err(|_| {
                    SiaScraperError::InvalidInput(
                        "career_indices[1] must be an integer string".to_string(),
                    )
                })?;
            self.request_dict.insert(
                CAMPUS_ELECTIVES_DD_ID.to_string(),
                (second_index + ELECTIVES_CAMPUS_INCREMENT).to_string(),
            );
        }

        let event_dict = get_event_dict(component_id, event_value, idx);
        self.request_dict.extend(event_dict);

        if data_name == SELECT_ROW {
            self.request_dict.insert(
                "oracle.adf.view.rich.DELTAS".to_string(),
                format!(
                    "{{pt1:r1:0:t4={{viewportSize={},rows={},selectedRowKeys={}}}}}",
                    course_list_len + 1,
                    course_list_len,
                    idx
                ),
            );
        } else if data_name == COURSE_PAGE_LINK {
            self.request_dict.insert(
                "oracle.adf.view.rich.RENDER".to_string(),
                ORACLE_ADF_RENDER_TARGET.to_string(),
            );
        }

        Ok(std::mem::take(&mut self.request_dict))
    }
}

/// Builds Oracle ADF event dictionary.
pub fn get_event_dict(id: &str, event_type: &str, idx: i32) -> HashMap<String, String> {
    let event_id = if idx >= 0 {
        format!("{}:{}:cl2", id, idx)
    } else {
        id.to_string()
    };

    let process_value = if event_type == BTTN_EVENT_VALUE {
        format!("{},{}", ORACLE_ADF_REGION_ID, event_id)
    } else {
        event_id.clone()
    };

    let mut event_dict = HashMap::new();
    event_dict.insert("event".to_string(), event_id.clone());
    event_dict.insert(format!("event.{}", event_id), event_type.to_string());
    event_dict.insert("oracle.adf.view.rich.PROCESS".to_string(), process_value);
    event_dict
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_init_request_dict_contains_base_fields() {
        let mut builder = OracleAdfRequestBuilderState::new();
        let request_dict =
            builder.init_request_dict("2", "window-123", "page-456", "viewstate-789");

        assert_eq!(
            request_dict.get("Adf-Window-Id"),
            Some(&"window-123".to_string())
        );
        assert_eq!(
            request_dict.get("Adf-Page-Id"),
            Some(&"page-456".to_string())
        );
        assert_eq!(
            request_dict.get("javax.faces.ViewState"),
            Some(&"viewstate-789".to_string())
        );
    }

    #[test]
    fn test_build_request_body_raises_for_unknown_action() {
        let mut builder = OracleAdfRequestBuilderState::new();
        let _ = builder.init_request_dict("2", "w", "p", "v");

        let result = builder.build_request_body("UNKNOWN_ACTION", -1, &["0".to_string()], 2);
        assert!(result.is_err());
    }

    #[test]
    fn test_build_request_body_sets_faculty_career_default_index() {
        let mut builder = OracleAdfRequestBuilderState::new();
        let _ = builder.init_request_dict("2", "w", "p", "v");

        let request_body = builder
            .build_request_body(
                FACULTY_CAREER_DD,
                -1,
                &["0".to_string(), "5".to_string()],
                2,
            )
            .unwrap();

        assert_eq!(
            request_body.get(FACULTY_CAREER_DD_ID),
            Some(&FACULTY_CAREER_DEFAULT_INDEX.to_string())
        );
    }

    #[test]
    fn test_build_request_body_sets_electives_campus_increment() {
        let mut builder = OracleAdfRequestBuilderState::new();
        let _ = builder.init_request_dict("2", "w", "p", "v");

        let request_body = builder
            .build_request_body(
                CAMPUS_ELECTIVES_DD,
                -1,
                &["0".to_string(), "5".to_string()],
                2,
            )
            .unwrap();

        assert_eq!(
            request_body.get(CAMPUS_ELECTIVES_DD_ID),
            Some(&"45".to_string())
        );
    }

    #[test]
    fn test_build_request_body_select_row_adds_deltas() {
        let mut builder = OracleAdfRequestBuilderState::new();
        let _ = builder.init_request_dict("2", "w", "p", "v");

        let request_body = builder
            .build_request_body(SELECT_ROW, 1, &["0".to_string(), "5".to_string()], 2)
            .unwrap();

        let deltas = request_body.get("oracle.adf.view.rich.DELTAS").unwrap();
        assert!(deltas.contains("viewportSize=3"));
        assert!(deltas.contains("rows=2"));
        assert!(deltas.contains("selectedRowKeys=1"));
    }

    #[test]
    fn test_build_request_body_course_page_link_sets_render_target() {
        let mut builder = OracleAdfRequestBuilderState::new();
        let _ = builder.init_request_dict("2", "w", "p", "v");

        let request_body = builder
            .build_request_body(COURSE_PAGE_LINK, -1, &["0".to_string(), "5".to_string()], 2)
            .unwrap();

        assert_eq!(
            request_body.get("oracle.adf.view.rich.RENDER"),
            Some(&ORACLE_ADF_RENDER_TARGET.to_string())
        );
    }

    #[test]
    fn test_get_event_dict_dropdown_event_uses_component_id_as_process() {
        let event_dict = get_event_dict("component-id", DROPDOWN_EVENT_VALUE, -1);

        assert_eq!(event_dict.get("event"), Some(&"component-id".to_string()));
        assert_eq!(
            event_dict.get("event.component-id"),
            Some(&DROPDOWN_EVENT_VALUE.to_string())
        );
        assert_eq!(
            event_dict.get("oracle.adf.view.rich.PROCESS"),
            Some(&"component-id".to_string())
        );
    }

    #[test]
    fn test_get_event_dict_select_row_event_with_index_formats_event_id() {
        let event_dict = get_event_dict("table-id", SELECT_ROW_EVENT_VALUE, 4);

        assert_eq!(event_dict.get("event"), Some(&"table-id:4:cl2".to_string()));
        assert_eq!(
            event_dict.get("event.table-id:4:cl2"),
            Some(&SELECT_ROW_EVENT_VALUE.to_string())
        );
        assert_eq!(
            event_dict.get("oracle.adf.view.rich.PROCESS"),
            Some(&"table-id:4:cl2".to_string())
        );
    }

    #[test]
    fn test_get_event_dict_button_event_uses_region_prefixed_process() {
        let event_dict = get_event_dict("button-id", BTTN_EVENT_VALUE, -1);

        assert_eq!(event_dict.get("event"), Some(&"button-id".to_string()));
        assert_eq!(
            event_dict.get("event.button-id"),
            Some(&BTTN_EVENT_VALUE.to_string())
        );
        assert_eq!(
            event_dict.get("oracle.adf.view.rich.PROCESS"),
            Some(&format!("{},button-id", ORACLE_ADF_REGION_ID))
        );
    }
}
