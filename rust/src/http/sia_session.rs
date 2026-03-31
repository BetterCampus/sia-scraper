//! Async SIA Session manager with retry logic.

use std::sync::Arc;
use std::sync::LazyLock;
use tokio::sync::RwLock;
use tokio::time::sleep;
use regex::Regex;

use crate::http::client::AsyncHttpClient;
use crate::http::config::HttpClientConfig;
use crate::http::errors::HttpError;
use crate::http::retry::{calculate_delay, should_retry, RetryConfig};
use crate::http::session::SessionState;
use crate::http::types::HttpResponse;
use crate::parsers::adf_request::OracleAdfRequestBuilderState;
use crate::parsers::table_parser::get_course_list;

const STUDY_LEVEL_DD_ID: &str = "pt1:r1:0:soc1";
const CAMPUS_DD_ID: &str = "pt1:r1:0:soc9";
const FACULTY_DD_ID: &str = "pt1:r1:0:soc2";
const CAREER_DD_ID: &str = "pt1:r1:0:soc3";
const CAREER_DROPDOWN_ID: &str = "pt1:r1:0:soc3::content";

const ACTION_STUDY_LEVEL_DD: &str = "STUDY_LEVEL_DD";
const ACTION_CAMPUS_DD: &str = "CAMPUS_DD";
const ACTION_FACULTY_DD: &str = "FACULTY_DD";
const ACTION_CAREER_DD: &str = "CAREER_DD";
const ACTION_TIPOLOGY_DD: &str = "TIPOLOGY_DD";
const ACTION_SHOW_COURSES_BTTN: &str = "SHOW_COURSES_BTTN";
const ACTION_FACULTY_CAREER_DD: &str = "FACULTY_CAREER_DD";
const ACTION_CAMPUS_ELECTIVES_DD: &str = "CAMPUS_ELECTIVES_DD";
const ACTION_SELECT_ROW: &str = "SELECT_ROW";
const ACTION_COURSE_PAGE_LINK: &str = "COURSE_PAGE_LINK";
const ELECTIVES_TYPOLOGY_INDEX: &str = "7";
const DROPDOWN_FIRST_OPTION_OFFSET: usize = 1;

static ADF_WINDOW_ID_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"(?is)<input[^>]*name\s*=\s*[\"']Adf-Window-Id[\"'][^>]*value\s*=\s*[\"']([^\"']*)[\"'][^>]*>"#)
        .expect("Adf-Window-Id regex must compile")
});

pub struct SiaSession {
    client: AsyncHttpClient,
    state: Arc<RwLock<SessionState>>,
    base_url: String,
    retry_config: RetryConfig,
}

impl SiaSession {
    pub fn new(timeout_secs: u64, base_url: String) -> Result<Self, HttpError> {
        Self::with_retry_config(timeout_secs, base_url, RetryConfig::sia_optimized())
    }

    pub fn with_retry_config(
        timeout_secs: u64,
        base_url: String,
        retry_config: RetryConfig,
    ) -> Result<Self, HttpError> {
        let config = HttpClientConfig::sia_default().with_timeout(timeout_secs);
        let client = AsyncHttpClient::with_config(config)?;

        Ok(Self {
            client,
            state: Arc::new(RwLock::new(SessionState::default())),
            base_url,
            retry_config,
        })
    }

    pub async fn init_session(&self) -> Result<(), HttpError> {
        let mut last_error: Option<HttpError> = None;

        for attempt in 1..=self.retry_config.max_attempts {
            match self.do_init_session().await {
                Ok(()) => return Ok(()),
                Err(e) => {
                    last_error = Some(e.clone());
                    if !should_retry(&e, &self.retry_config) || attempt == self.retry_config.max_attempts
                    {
                        return Err(e);
                    }
                    let delay = calculate_delay(attempt, &self.retry_config);
                    sleep(delay).await;
                }
            }
        }

        Err(last_error.unwrap_or(HttpError::ConnectionFailed(
            "Unknown error".to_string(),
        )))
    }

    async fn do_init_session(&self) -> Result<(), HttpError> {
        let init_url = format!(
            "{}?taskflowId=task-flow-AC_CatalogoAsignaturas",
            self.base_url
        );
        let resp = self.client.get(&init_url).await?;
        resp.raise_for_status()?;

        let mut state = self.state.write().await;

        if let Ok(view_state) = crate::parsers::adf::extract_view_state(&resp.body) {
            state.update_view_state(view_state);
        }

        if let Some(captures) = ADF_WINDOW_ID_RE.captures(&resp.body) {
            if let Some(window_id) = captures.get(1) {
                state.update_params("Adf-Window-Id", window_id.as_str().to_string());
            }
        }

        state.update_params("Adf-Page-Id", "0".to_string());
        state.set_status("SESSION_SET");

        Ok(())
    }

    async fn request_url_with_params(&self) -> String {
        let state = self.state.read().await;
        let mut params: Vec<(&str, &str)> = vec![];

        if let Some(window_id) = state.params.get("Adf-Window-Id") {
            params.push(("Adf-Window-Id", window_id.as_str()));
        }
        if let Some(page_id) = state.params.get("Adf-Page-Id") {
            params.push(("Adf-Page-Id", page_id.as_str()));
        }

        if params.is_empty() {
            return self.base_url.clone();
        }

        let query = serde_urlencoded::to_string(&params).unwrap_or_default();
        format!("{}?{}", self.base_url, query)
    }

    fn state_as_request_builder(&self, state: &SessionState) -> OracleAdfRequestBuilderState {
        let mut builder = OracleAdfRequestBuilderState::new();
        let tipology_index = if state.is_electives {
            ELECTIVES_TYPOLOGY_INDEX
        } else {
            ""
        };

        let window_id = state.params.get("Adf-Window-Id").map(String::as_str);
        let page_id = state.params.get("Adf-Page-Id").map(String::as_str);
        let view_state = state.javax_faces_ViewState.as_deref();

        let _ = builder.init_request_dict(tipology_index, window_id, page_id, view_state);

        builder
    }

    fn extract_career_name(xml: &str, career_index: usize) -> String {
        let escaped_id = CAREER_DROPDOWN_ID.replace(':', "\\:");
        let selector = format!("select#{escaped_id} option");

        let html = scraper::Html::parse_document(xml);
        let Ok(option_selector) = scraper::Selector::parse(&selector) else {
            return "N/A".to_string();
        };

        let options: Vec<scraper::ElementRef<'_>> = html.select(&option_selector).collect();
        let target_index = career_index + DROPDOWN_FIRST_OPTION_OFFSET;
        options
            .get(target_index)
            .map(|elem| elem.text().collect::<String>().trim().to_string())
            .filter(|value| !value.is_empty())
            .unwrap_or_else(|| "N/A".to_string())
    }

    pub async fn set_career(
        &self,
        search_code: &str,
        electives: bool,
    ) -> Result<SessionState, HttpError> {
        let mut state = self.get_state().await;
        let career_indices: Vec<String> = search_code.split('-').map(ToString::to_string).collect();

        if career_indices.len() != 4 {
            return Err(HttpError::InvalidInput(
                "search_code must have 4 indices separated by '-'".to_string(),
            ));
        }

        state.career_code = search_code.to_string();
        state.is_electives = electives;

        let mut action_sequence = vec![
            ACTION_STUDY_LEVEL_DD,
            ACTION_CAMPUS_DD,
            ACTION_FACULTY_DD,
            ACTION_CAREER_DD,
            ACTION_TIPOLOGY_DD,
        ];

        if electives {
            action_sequence.extend([
                ACTION_FACULTY_CAREER_DD,
                ACTION_CAMPUS_ELECTIVES_DD,
                ACTION_SHOW_COURSES_BTTN,
            ]);
        } else {
            action_sequence.push(ACTION_SHOW_COURSES_BTTN);
        }

        let mut last_xml = String::new();

        for action in action_sequence {
            let mut builder = self.state_as_request_builder(&state);
            builder
                .request_dict
                .insert(STUDY_LEVEL_DD_ID.to_string(), career_indices[0].clone());
            builder
                .request_dict
                .insert(CAMPUS_DD_ID.to_string(), career_indices[1].clone());
            builder
                .request_dict
                .insert(FACULTY_DD_ID.to_string(), career_indices[2].clone());
            builder
                .request_dict
                .insert(CAREER_DD_ID.to_string(), career_indices[3].clone());

            let request_body = builder
                .build_request_body(action, -1, &career_indices, 0)
                .map_err(|e| HttpError::InvalidInput(e.to_string()))?;
            let encoded = serde_urlencoded::to_string(request_body)
                .map_err(|e| HttpError::InvalidInput(e.to_string()))?;

            let response = self.post_request(&encoded).await?;
            response.raise_for_status()?;
            last_xml = response.body.clone();

            if action == ACTION_FACULTY_DD {
                let career_index = career_indices[3]
                    .parse::<usize>()
                    .map_err(|_| HttpError::InvalidInput("career index must be numeric".to_string()))?;
                state.career_name = Self::extract_career_name(&last_xml, career_index);
            }

            let mut current = self.state.write().await;
            if let Ok(view_state) = crate::parsers::adf::extract_view_state(&last_xml) {
                current.javax_faces_ViewState = Some(view_state);
            }
            current.career_code = state.career_code.clone();
            current.career_name = state.career_name.clone();
            current.is_electives = state.is_electives;
            state = current.clone();
        }

        let course_list =
            get_course_list(&last_xml).map_err(|e| HttpError::ParseError(e.to_string()))?;
        let mut current = self.state.write().await;
        current.status = "ON_CAREER_PAGE".to_string();
        current.update_params("course_list_len", course_list.len().to_string());
        state = current.clone();

        let mut state_with_courses = state;
        state_with_courses
            .params
            .insert("course_list_len".to_string(), course_list.len().to_string());
        state_with_courses
            .params
            .insert("course_list_json".to_string(), serde_json::to_string(&course_list).unwrap_or_default());
        Ok(state_with_courses)
    }

    pub async fn get_course_xml(
        &self,
        search_code: &str,
        electives: bool,
        course_index: i32,
    ) -> Result<String, HttpError> {
        let career_state = self.set_career(search_code, electives).await?;
        let course_list_json = career_state
            .params
            .get("course_list_json")
            .cloned()
            .unwrap_or_default();
        let course_list: Vec<std::collections::HashMap<String, String>> =
            serde_json::from_str(&course_list_json).unwrap_or_default();

        let career_indices: Vec<String> = search_code.split('-').map(ToString::to_string).collect();

        let mut builder = self.state_as_request_builder(&career_state);
        builder
            .request_dict
            .insert(STUDY_LEVEL_DD_ID.to_string(), career_indices[0].clone());
        builder
            .request_dict
            .insert(CAMPUS_DD_ID.to_string(), career_indices[1].clone());
        builder
            .request_dict
            .insert(FACULTY_DD_ID.to_string(), career_indices[2].clone());
        builder
            .request_dict
            .insert(CAREER_DD_ID.to_string(), career_indices[3].clone());

        let select_row = builder
            .build_request_body(
                ACTION_SELECT_ROW,
                course_index,
                &career_indices,
                course_list.len(),
            )
            .map_err(|e| HttpError::InvalidInput(e.to_string()))?;
        let select_row_encoded =
            serde_urlencoded::to_string(select_row).map_err(|e| HttpError::InvalidInput(e.to_string()))?;
        let _ = self.post_request(&select_row_encoded).await?;

        let mut builder = self.state_as_request_builder(&self.get_state().await);
        builder
            .request_dict
            .insert(STUDY_LEVEL_DD_ID.to_string(), career_indices[0].clone());
        builder
            .request_dict
            .insert(CAMPUS_DD_ID.to_string(), career_indices[1].clone());
        builder
            .request_dict
            .insert(FACULTY_DD_ID.to_string(), career_indices[2].clone());
        builder
            .request_dict
            .insert(CAREER_DD_ID.to_string(), career_indices[3].clone());

        let course_page = builder
            .build_request_body(
                ACTION_COURSE_PAGE_LINK,
                course_index,
                &career_indices,
                course_list.len(),
            )
            .map_err(|e| HttpError::InvalidInput(e.to_string()))?;
        let course_page_encoded =
            serde_urlencoded::to_string(course_page).map_err(|e| HttpError::InvalidInput(e.to_string()))?;
        let response = self.post_request(&course_page_encoded).await?;
        response.raise_for_status()?;
        let xml = response.body.clone();

        let mut back_body = std::collections::HashMap::new();
        back_body.insert(
            "org.apache.myfaces.trinidad.faces.FORM".to_string(),
            "f1".to_string(),
        );
        back_body.insert(
            "Adf-Window-Id".to_string(),
            self.get_state()
                .await
                .params
                .get("Adf-Window-Id")
                .cloned()
                .unwrap_or_default(),
        );
        back_body.insert(
            "Adf-Page-Id".to_string(),
            self.get_state()
                .await
                .params
                .get("Adf-Page-Id")
                .cloned()
                .unwrap_or_default(),
        );
        back_body.insert(
            "javax.faces.ViewState".to_string(),
            self.get_state()
                .await
                .javax_faces_ViewState
                .unwrap_or_default(),
        );
        back_body.insert("event".to_string(), "pt1:r1:1:cb4".to_string());
        back_body.insert(
            "event.pt1:r1:1:cb4".to_string(),
            r#"<m xmlns="http://oracle.com/richClient/comm"><k v="type"><s>action</s></k></m>"#.to_string(),
        );
        back_body.insert(
            "oracle.adf.view.rich.PROCESS".to_string(),
            "pt1:r1,pt1:r1:1:cb44".to_string(),
        );

        let back_encoded =
            serde_urlencoded::to_string(back_body).map_err(|e| HttpError::InvalidInput(e.to_string()))?;
        let _ = self.post_request(&back_encoded).await?;

        let mut state = self.state.write().await;
        state.status = "ON_CAREER_PAGE".to_string();

        Ok(xml)
    }

    pub async fn post_request(&self, body: &str) -> Result<HttpResponse, HttpError> {
        let mut last_error: Option<HttpError> = None;

        for attempt in 1..=self.retry_config.max_attempts {
            match self.do_post_request(body).await {
                Ok(resp) => return Ok(resp),
                Err(e) => {
                    last_error = Some(e.clone());
                    if !should_retry(&e, &self.retry_config) || attempt == self.retry_config.max_attempts
                    {
                        return Err(e);
                    }
                    let delay = calculate_delay(attempt, &self.retry_config);
                    sleep(delay).await;
                }
            }
        }

        Err(last_error.unwrap_or(HttpError::ConnectionFailed(
            "Unknown error".to_string(),
        )))
    }

    async fn do_post_request(&self, body: &str) -> Result<HttpResponse, HttpError> {
        let url = self.request_url_with_params().await;
        let resp = self.client.post(&url, body).await?;

        if let Ok(view_state) = crate::parsers::adf::extract_view_state(&resp.body) {
            let mut state = self.state.write().await;
            state.update_view_state(view_state);
        }

        Ok(resp)
    }

    pub async fn get_state(&self) -> SessionState {
        self.state.read().await.clone()
    }

    pub async fn update_state(&self, state: SessionState) {
        *self.state.write().await = state;
    }

    pub fn base_url(&self) -> &str {
        &self.base_url
    }

    pub fn retry_config(&self) -> &RetryConfig {
        &self.retry_config
    }
}

impl Default for SiaSession {
    fn default() -> Self {
        Self::new(
            15,
            "https://sia.unal.edu.co/Catalogo/facespublico/public/servicioPublico.jsf".to_string(),
        )
        .unwrap()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_session_creation() {
        let session = SiaSession::new(15, "https://httpbin.org".to_string());
        assert!(session.is_ok());
    }

    #[tokio::test]
    async fn test_default_session() {
        let session = SiaSession::default();
        let state = session.get_state().await;
        assert_eq!(state.status, "CREATED");
    }

    #[tokio::test]
    async fn test_session_with_custom_retry() {
        let config = RetryConfig::default().with_max_attempts(5);
        let session = SiaSession::with_retry_config(15, "https://httpbin.org".to_string(), config);
        assert!(session.is_ok());
        assert_eq!(session.unwrap().retry_config().max_attempts, 5);
    }

    #[test]
    fn test_extract_career_name_from_dropdown() {
        let html = r#"
        <select id="pt1:r1:0:soc3::content">
            <option>Seleccione...</option>
            <option>Ingenieria de Sistemas</option>
        </select>
        "#;
        let name = SiaSession::extract_career_name(html, 0);
        assert_eq!(name, "Ingenieria de Sistemas");
    }
}
