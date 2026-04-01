//! Async SIA Session manager with retry logic.

use regex::Regex;
use std::sync::Arc;
use std::sync::LazyLock;
use tokio::sync::RwLock;
use tokio::time::sleep;

use crate::constants::{
    actions, adf_ids, DROPDOWN_FIRST_OPTION_OFFSET, ELECTIVES_TYPOLOGY_INDEX, SIA_BASE_URL,
};
use crate::http::client::AsyncHttpClient;
use crate::http::config::HttpClientConfig;
use crate::http::errors::HttpError;
use crate::http::retry::{calculate_delay, should_retry, RetryConfig};
use crate::http::session::SessionState;
use crate::http::types::HttpResponse;
use crate::parsers::adf_request::OracleAdfRequestBuilderState;
use crate::parsers::table_parser::get_course_list;

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
                    if !should_retry(&e, &self.retry_config)
                        || attempt == self.retry_config.max_attempts
                    {
                        return Err(e);
                    }
                    let delay = calculate_delay(attempt, &self.retry_config);
                    sleep(delay).await;
                }
            }
        }

        Err(last_error.unwrap_or(HttpError::ConnectionFailed("Unknown error".to_string())))
    }

    async fn do_init_session(&self) -> Result<(), HttpError> {
        let init_url = format!(
            "{}?taskflowId={}",
            self.base_url,
            crate::constants::SIA_TASKFLOW_ID
        );
        let resp =
            self.client.get(&init_url).await.map_err(|e| {
                HttpError::ConnectionFailed(format!("init_session GET failed: {e}"))
            })?;
        resp.raise_for_status().map_err(|e| {
            HttpError::ConnectionFailed(format!("init_session returned error status: {e}"))
        })?;

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

    async fn request_url_with_params(&self) -> Result<String, HttpError> {
        let state = self.state.read().await;
        let mut params: Vec<(&str, &str)> = vec![];

        if let Some(window_id) = state.params.get("Adf-Window-Id") {
            params.push(("Adf-Window-Id", window_id.as_str()));
        }
        if let Some(page_id) = state.params.get("Adf-Page-Id") {
            params.push(("Adf-Page-Id", page_id.as_str()));
        }

        if params.is_empty() {
            return Ok(self.base_url.clone());
        }

        let query = serde_urlencoded::to_string(&params).map_err(|e| {
            HttpError::InvalidInput(format!(
                "Failed to build session URL: invalid query parameters ({e})"
            ))
        })?;
        Ok(format!("{}?{}", self.base_url, query))
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
        let escaped_id = adf_ids::CAREER_DROPDOWN_ID.replace(':', "\\:");
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
            actions::STUDY_LEVEL_DD,
            actions::CAMPUS_DD,
            actions::FACULTY_DD,
            actions::CAREER_DD,
            actions::TIPOLOGY_DD,
        ];

        if electives {
            action_sequence.extend([
                actions::FACULTY_CAREER_DD,
                actions::CAMPUS_ELECTIVES_DD,
                actions::SHOW_COURSES_BTTN,
            ]);
        } else {
            action_sequence.push(actions::SHOW_COURSES_BTTN);
        }

        let mut last_xml = String::new();

        for action in action_sequence {
            let mut builder = self.state_as_request_builder(&state);
            builder.request_dict.insert(
                adf_ids::STUDY_LEVEL_DD_ID.to_string(),
                career_indices[0].clone(),
            );
            builder
                .request_dict
                .insert(adf_ids::CAMPUS_DD_ID.to_string(), career_indices[1].clone());
            builder.request_dict.insert(
                adf_ids::FACULTY_DD_ID.to_string(),
                career_indices[2].clone(),
            );
            builder
                .request_dict
                .insert(adf_ids::CAREER_DD_ID.to_string(), career_indices[3].clone());

            let request_body = builder
                .build_request_body(action, -1, &career_indices, 0)
                .map_err(|e| {
                    HttpError::InvalidInput(format!("build_request_body({action}): {e}"))
                })?;
            let encoded = serde_urlencoded::to_string(request_body).map_err(|e| {
                HttpError::InvalidInput(format!("encode request for {action}: {e}"))
            })?;

            let response = self.post_request(&encoded).await?;
            response.raise_for_status().map_err(|e| {
                HttpError::ConnectionFailed(format!("{action} POST returned error status: {e}"))
            })?;
            last_xml = response.body.clone();

            if action == actions::FACULTY_DD {
                let career_index = career_indices[3].parse::<usize>().map_err(|_| {
                    HttpError::InvalidInput("career index must be numeric".to_string())
                })?;
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
        let course_len = course_list.len();
        let mut current = self.state.write().await;
        current.status = "ON_CAREER_PAGE".to_string();
        current.course_list = course_list;
        current.update_params("course_list_len", course_len.to_string());
        Ok(current.clone())
    }

    pub async fn get_course_xml(
        &self,
        search_code: &str,
        electives: bool,
        course_index: i32,
    ) -> Result<String, HttpError> {
        let career_state = self.set_career(search_code, electives).await?;
        let course_list = &career_state.course_list;

        let career_indices: Vec<String> = search_code.split('-').map(ToString::to_string).collect();
        if career_indices.len() != 4 {
            return Err(HttpError::InvalidInput(format!(
                "career code '{}' must have 4 indices separated by '-'",
                search_code
            )));
        }

        let mut builder = self.state_as_request_builder(&career_state);
        builder.request_dict.insert(
            adf_ids::STUDY_LEVEL_DD_ID.to_string(),
            career_indices[0].clone(),
        );
        builder
            .request_dict
            .insert(adf_ids::CAMPUS_DD_ID.to_string(), career_indices[1].clone());
        builder.request_dict.insert(
            adf_ids::FACULTY_DD_ID.to_string(),
            career_indices[2].clone(),
        );
        builder
            .request_dict
            .insert(adf_ids::CAREER_DD_ID.to_string(), career_indices[3].clone());

        let select_row = builder
            .build_request_body(
                actions::SELECT_ROW,
                course_index,
                &career_indices,
                course_list.len(),
            )
            .map_err(|e| HttpError::InvalidInput(e.to_string()))?;
        let select_row_encoded = serde_urlencoded::to_string(select_row)
            .map_err(|e| HttpError::InvalidInput(e.to_string()))?;
        let _ = self.post_request(&select_row_encoded).await?;

        let mut builder = self.state_as_request_builder(&self.get_state().await);
        builder.request_dict.insert(
            adf_ids::STUDY_LEVEL_DD_ID.to_string(),
            career_indices[0].clone(),
        );
        builder
            .request_dict
            .insert(adf_ids::CAMPUS_DD_ID.to_string(), career_indices[1].clone());
        builder.request_dict.insert(
            adf_ids::FACULTY_DD_ID.to_string(),
            career_indices[2].clone(),
        );
        builder
            .request_dict
            .insert(adf_ids::CAREER_DD_ID.to_string(), career_indices[3].clone());

        let course_page = builder
            .build_request_body(
                actions::COURSE_PAGE_LINK,
                course_index,
                &career_indices,
                course_list.len(),
            )
            .map_err(|e| HttpError::InvalidInput(e.to_string()))?;
        let course_page_encoded = serde_urlencoded::to_string(course_page)
            .map_err(|e| HttpError::InvalidInput(e.to_string()))?;
        let response = self.post_request(&course_page_encoded).await?;
        response.raise_for_status()?;
        let xml = response.body.clone();

        let current_state = self.get_state().await;
        let mut back_body = std::collections::HashMap::new();
        back_body.insert(
            "org.apache.myfaces.trinidad.faces.FORM".to_string(),
            "f1".to_string(),
        );
        let window_id = current_state
            .params
            .get("Adf-Window-Id")
            .cloned()
            .ok_or_else(|| {
                HttpError::InvalidInput("Missing Adf-Window-Id in session state".to_string())
            })?;
        back_body.insert("Adf-Window-Id".to_string(), window_id);

        let page_id = current_state
            .params
            .get("Adf-Page-Id")
            .cloned()
            .ok_or_else(|| {
                HttpError::InvalidInput("Missing Adf-Page-Id in session state".to_string())
            })?;
        back_body.insert("Adf-Page-Id".to_string(), page_id);

        let view_state = current_state.javax_faces_ViewState.ok_or_else(|| {
            HttpError::InvalidInput("Missing ViewState in session state".to_string())
        })?;
        back_body.insert("javax.faces.ViewState".to_string(), view_state);
        back_body.insert("event".to_string(), "pt1:r1:1:cb4".to_string());
        back_body.insert(
            "event.pt1:r1:1:cb4".to_string(),
            r#"<m xmlns="http://oracle.com/richClient/comm"><k v="type"><s>action</s></k></m>"#
                .to_string(),
        );
        back_body.insert(
            "oracle.adf.view.rich.PROCESS".to_string(),
            "pt1:r1,pt1:r1:1:cb44".to_string(),
        );

        let back_encoded = serde_urlencoded::to_string(back_body)
            .map_err(|e| HttpError::InvalidInput(e.to_string()))?;
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
                    if !should_retry(&e, &self.retry_config)
                        || attempt == self.retry_config.max_attempts
                    {
                        return Err(e);
                    }
                    let delay = calculate_delay(attempt, &self.retry_config);
                    sleep(delay).await;
                }
            }
        }

        Err(last_error.unwrap_or(HttpError::ConnectionFailed("Unknown error".to_string())))
    }

    async fn do_post_request(&self, body: &str) -> Result<HttpResponse, HttpError> {
        let url = self.request_url_with_params().await?;
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
        Self::new(15, SIA_BASE_URL.to_string())
            .expect("SiaSession::default() should never fail with standard config")
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

    #[test]
    fn test_extract_career_name_returns_na_for_missing_option() {
        let html = r#"
        <select id="pt1:r1:0:soc3::content">
            <option>Seleccione...</option>
        </select>
        "#;
        let name = SiaSession::extract_career_name(html, 5);
        assert_eq!(name, "N/A");
    }

    #[test]
    fn test_extract_career_name_returns_na_for_empty_text() {
        let html = r#"
        <select id="pt1:r1:0:soc3::content">
            <option>Seleccione...</option>
            <option>   </option>
        </select>
        "#;
        let name = SiaSession::extract_career_name(html, 0);
        assert_eq!(name, "N/A");
    }

    #[tokio::test]
    async fn test_set_career_rejects_invalid_search_code() {
        let session = SiaSession::new(15, "https://httpbin.org".to_string()).unwrap();
        let result = session.set_career("0-2-8", false).await;
        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(err.to_string().contains("4 indices"));
    }

    #[tokio::test]
    async fn test_set_career_rejects_non_numeric_index() {
        let session = SiaSession::new(15, "https://httpbin.org".to_string()).unwrap();
        let result = session.set_career("0-2-8-abc", false).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_request_url_includes_params() {
        let session = SiaSession::new(15, "https://example.com".to_string()).unwrap();
        {
            let mut state = session.state.write().await;
            state.update_params("Adf-Window-Id", "win1".to_string());
            state.update_params("Adf-Page-Id", "0".to_string());
        }
        let url = session.request_url_with_params().await.unwrap();
        assert!(url.contains("Adf-Window-Id=win1"));
        assert!(url.contains("Adf-Page-Id=0"));
    }

    #[tokio::test]
    async fn test_request_url_returns_base_when_no_params() {
        let session = SiaSession::new(15, "https://example.com".to_string()).unwrap();
        // Clear default params set by SessionState::default()
        {
            let mut state = session.state.write().await;
            state.params.clear();
        }
        let url = session.request_url_with_params().await.unwrap();
        assert_eq!(url, "https://example.com");
    }

    #[tokio::test]
    async fn test_state_as_request_builder_initializes_dict() {
        let session = SiaSession::new(15, "https://example.com".to_string()).unwrap();
        {
            let mut state = session.state.write().await;
            state.update_view_state("vs123".to_string());
            state.update_params("Adf-Window-Id", "win1".to_string());
            state.update_params("Adf-Page-Id", "0".to_string());
        }
        let state = session.get_state().await;
        let builder = session.state_as_request_builder(&state);
        assert!(builder.request_dict.contains_key("javax.faces.ViewState"));
        assert_eq!(
            builder.request_dict.get("javax.faces.ViewState").unwrap(),
            "vs123"
        );
    }

    #[tokio::test]
    async fn test_get_state_returns_clone_of_current_state() {
        let session = SiaSession::new(15, "https://example.com".to_string()).unwrap();
        {
            let mut state = session.state.write().await;
            state.update_view_state("vs_get".to_string());
            state.career_code = "1-2-3-4".to_string();
        }
        let snapshot = session.get_state().await;
        assert_eq!(snapshot.javax_faces_ViewState.as_deref(), Some("vs_get"));
        assert_eq!(snapshot.career_code, "1-2-3-4");
    }

    #[tokio::test]
    async fn test_update_state_overwrites_entire_state() {
        let session = SiaSession::new(15, "https://example.com".to_string()).unwrap();
        let new_state = SessionState {
            career_code: "9-9-9-9".to_string(),
            status: "CUSTOM".to_string(),
            ..Default::default()
        };
        session.update_state(new_state).await;

        let state = session.get_state().await;
        assert_eq!(state.career_code, "9-9-9-9");
        assert_eq!(state.status, "CUSTOM");
    }

    #[test]
    fn test_accessors_return_expected_values() {
        let session = SiaSession::new(10, "https://test.example.com".to_string()).unwrap();
        assert_eq!(session.base_url(), "https://test.example.com");
        assert!(session.retry_config().max_attempts >= 1);
    }

    #[test]
    fn test_extract_career_name_returns_na_for_empty_html() {
        let html = "<div>No select here</div>";
        let name = SiaSession::extract_career_name(html, 0);
        assert_eq!(name, "N/A");
    }

    #[test]
    fn test_extract_career_name_returns_na_for_invalid_selector() {
        let html = r#"<select id="wrong_id"><option>Test</option></select>"#;
        let name = SiaSession::extract_career_name(html, 0);
        assert_eq!(name, "N/A");
    }
}
