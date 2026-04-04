//! Async SIA Session manager with retry logic.

use std::sync::Arc;
use std::time::Duration;
use tokio::sync::RwLock;
use tokio::time::sleep;

use crate::constants::{
    actions, adf_ids, DROPDOWN_FIRST_OPTION_OFFSET, ELECTIVES_TYPOLOGY_INDEX,
};
use crate::http::client::AsyncHttpClient;
use crate::http::config::HttpClientConfig;
use crate::http::errors::HttpError;
use crate::http::retry::{calculate_delay, should_retry, RetryConfig};
use crate::http::session::SessionState;
use crate::http::types::HttpResponse;
use crate::models::course::CourseInfoModel;
use crate::models::prerequisite::CoursePrereqsModel;
use crate::models::scrape_result::{ErrorMode, ScrapeResult};
use crate::parsers::adf_request::OracleAdfRequestBuilderState;
use crate::parsers::course_parser::{parse_course_model, parse_prereqs_model};
use crate::parsers::table_parser::get_course_list;
use crate::patterns::get_regex;

macro_rules! define_regex {
    ($name:ident, $pattern:expr) => {
        static $name: std::sync::LazyLock<Result<regex::Regex, String>> =
            std::sync::LazyLock::new(|| {
                regex::Regex::new($pattern).map_err(|e| format!("{}: {:?}", stringify!($name), e))
            });
    };
}

define_regex!(ADF_WINDOW_ID_RE, r#"(?is)<input[^>]*name\s*=\s*["']Adf-Window-Id["'][^>]*value\s*=\s*["']([^"']*)["'][^>]*>"#);

#[derive(Clone)]
pub struct SiaSession {
    client: AsyncHttpClient,
    state: Arc<RwLock<SessionState>>,
    base_url: String,
    retry_config: RetryConfig,
}

impl SiaSession {
    /// Create a new SiaSession with default retry configuration.
    pub fn new(timeout_secs: u64, base_url: String) -> Result<Self, HttpError> {
        Self::with_retry_config(timeout_secs, base_url, RetryConfig::sia_optimized())
    }

    /// Create a new SiaSession from saved SessionState.
    ///
    /// This constructor is used to restore a session from previously
    /// persisted state (e.g., after pickle/unpickle or loading from file).
    ///
    /// The session will use the provided state directly without re-fetching
    /// the initial page. The HTTP client is initialized fresh to allow
    /// cookie restoration.
    ///
    /// # Arguments
    /// * `timeout_secs` - Request timeout in seconds
    /// * `base_url` - Base URL for SIA
    /// * `state` - Previously saved SessionState to restore
    ///
    /// # Returns
    /// New SiaSession instance with restored state
    pub fn from_state(
        timeout_secs: u64,
        base_url: String,
        state: SessionState,
    ) -> Result<Self, HttpError> {
        let config = HttpClientConfig::sia_default().with_timeout(timeout_secs);
        let client = AsyncHttpClient::with_config(config)?;

        Ok(Self {
            client,
            state: Arc::new(RwLock::new(state)),
            base_url,
            retry_config: RetryConfig::sia_optimized(),
        })
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

        Err(last_error.unwrap_or(HttpError::NetworkError("Unknown error".to_string())))
    }

    async fn do_init_session(&self) -> Result<(), HttpError> {
        let init_url = format!(
            "{}?taskflowId={}",
            self.base_url,
            crate::constants::SIA_TASKFLOW_ID
        );
        let resp =
            self.client.get(&init_url).await.map_err(|e| {
                HttpError::NetworkError(format!("init_session GET failed: {e}"))
            })?;
        resp.raise_for_status().map_err(|e| match e {
            HttpError::HttpStatusError { status, message } => {
                HttpError::HttpStatusError {
                    status,
                    message: format!("init_session returned error status: {}", message),
                }
            }
            other => other,
        })?;

        let mut state = self.state.write().await;

        if let Ok(view_state) = crate::parsers::adf::extract_view_state(&resp.body) {
            state.update_view_state(view_state);
        }

        let window_id_re = get_regex(&ADF_WINDOW_ID_RE, "sia_session::do_init_session")
            .map_err(|e| HttpError::ParseError(format!("ADF_WINDOW_ID_RE init failed: {}", e)))?;
        if let Some(captures) = window_id_re.captures(&resp.body) {
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

    fn state_as_request_builder(&self, state: &SessionState) -> Result<OracleAdfRequestBuilderState, HttpError> {
        let tipology_index = if state.is_electives {
            ELECTIVES_TYPOLOGY_INDEX
        } else {
            ""
        };

        let window_id = state.params.get("Adf-Window-Id").and_then(|v| {
            if v.is_empty() { None } else { Some(v.as_str()) }
        }).ok_or_else(|| {
            HttpError::InvalidInput("state_as_request_builder: Adf-Window-Id is required".to_string())
        })?;
        let page_id = state.params.get("Adf-Page-Id").and_then(|v| {
            if v.is_empty() { None } else { Some(v.as_str()) }
        }).ok_or_else(|| {
            HttpError::InvalidInput("state_as_request_builder: Adf-Page-Id is required".to_string())
        })?;
        let view_state = state.javax_faces_ViewState.as_deref().ok_or_else(|| {
            HttpError::InvalidInput("state_as_request_builder: javax_faces_ViewState is required".to_string())
        })?;

        let mut builder = OracleAdfRequestBuilderState::new();
        builder.init_request_dict(tipology_index, window_id, page_id, view_state);

        Ok(builder)
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
            let mut builder = self.state_as_request_builder(&state).map_err(|e| {
                HttpError::InvalidInput(format!("state_as_request_builder failed: {}", e))
            })?;
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
            response.raise_for_status().map_err(|e| match e {
                HttpError::HttpStatusError { status, message } => {
                    HttpError::HttpStatusError {
                        status,
                        message: format!("{} POST returned error status: {}", action, message),
                    }
                }
                other => other,
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

    pub(crate) async fn get_course_xml_internal(
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

        let mut builder = self.state_as_request_builder(&career_state).map_err(|e| {
            HttpError::InvalidInput(format!("state_as_request_builder failed: {}", e))
        })?;
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

        let mut builder = self.state_as_request_builder(&self.get_state().await).map_err(|e| {
            HttpError::InvalidInput(format!("state_as_request_builder failed: {}", e))
        })?;
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

    /// Scrape course information for the given index.
    ///
    /// This method combines HTTP fetching and parsing in a single Rust call,
    /// eliminating string copying across the FFI boundary.
    ///
    /// # Arguments
    /// * `course_index` - The index of the course in the current course list
    ///
    /// # Returns
    /// `CourseInfoModel` containing parsed course data
    ///
    /// # Errors
    /// Returns `HttpError` if the session is not on a career or course page, or if
    /// HTTP/parsing fails.
    pub async fn scrape_course_info(&self, course_index: i32) -> Result<CourseInfoModel, HttpError> {
        let state = self.get_state().await;

        if state.status != "ON_CAREER_PAGE" && state.status != "ON_COURSE_PAGE" {
            return Err(HttpError::InvalidInput(
                "scrape_course_info: session not on career or course page".to_string(),
            ));
        }

        let course_list = &state.course_list;
        if course_list.is_empty() {
            return Err(HttpError::InvalidInput(
                "scrape_course_info: course list is empty".to_string(),
            ));
        }
        if course_index < 0 || course_index as usize >= course_list.len() {
            return Err(HttpError::InvalidInput(format!(
                "course index {} out of range (0-{})",
                course_index,
                course_list.len() - 1
            )));
        }

        log::info!("Scrape course info for index {}", course_index);

        let xml = self
            .get_course_xml_internal(&state.career_code, state.is_electives, course_index)
            .await?;

        parse_course_model(&xml).map_err(|e| HttpError::ParseError(e.to_string()))
    }

    /// Scrape course prerequisite information for the given index.
    ///
    /// This method combines HTTP fetching and parsing in a single Rust call,
    /// eliminating string copying across the FFI boundary.
    ///
    /// # Arguments
    /// * `course_index` - The index of the course in the current course list
    ///
    /// # Returns
    /// `CoursePrereqsModel` containing parsed prerequisite data
    ///
    /// # Errors
    /// Returns `HttpError` if the session is not on a career or course page, or if
    /// HTTP/parsing fails.
    pub async fn scrape_course_prereqs(
        &self,
        course_index: i32,
    ) -> Result<CoursePrereqsModel, HttpError> {
        let state = self.get_state().await;

        if state.status != "ON_CAREER_PAGE" && state.status != "ON_COURSE_PAGE" {
            return Err(HttpError::InvalidInput(
                "scrape_course_prereqs: session not on career or course page".to_string(),
            ));
        }

        let course_list = &state.course_list;
        if course_list.is_empty() {
            return Err(HttpError::InvalidInput(
                "scrape_course_prereqs: course list is empty".to_string(),
            ));
        }
        if course_index < 0 || course_index as usize >= course_list.len() {
            return Err(HttpError::InvalidInput(format!(
                "course index {} out of range (0-{})",
                course_index,
                course_list.len() - 1
            )));
        }

        log::info!("Scrape course prerequisites for index {}", course_index);

        let xml = self
            .get_course_xml_internal(&state.career_code, state.is_electives, course_index)
            .await?;

        parse_prereqs_model(&xml).map_err(|e| HttpError::ParseError(e.to_string()))
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

        Err(last_error.unwrap_or(HttpError::NetworkError("Unknown error".to_string())))
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

    /// Scrape multiple courses sequentially with configurable error handling.
    ///
    /// Iterates over the provided course indices and attempts to scrape each one.
    /// Errors are handled according to the specified `ErrorMode`:
    ///
    /// - `Abort`: Returns immediately on the first error.
    /// - `Skip`: Records the failure and continues to the next course.
    /// - `Retry`: Retries up to `max_retries` times with exponential backoff
    ///   before recording as a failure.
    ///
    /// # Arguments
    /// * `indices` - Course indices to scrape
    /// * `mode` - Error handling strategy
    /// * `max_retries` - Maximum retry attempts per course (used only in Retry mode)
    /// * `retry_delay_ms` - Base delay between retries in milliseconds
    ///
    /// # Returns
    /// `ScrapeResult` containing successes and failures
    ///
    /// # Errors
    /// Returns the original `HttpError` on first failure when mode is Abort.
    ///
    /// # Example
    /// ```no_run
    /// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// use sia_scraper::http::sia_session::SiaSession;
    /// use sia_scraper::models::scrape_result::ErrorMode;
    ///
    /// let session = SiaSession::new(30, "https://sia.unal.edu.co".to_string())?;
    /// let result = session
    ///     .scrape_courses_batch(vec![0, 1, 2], ErrorMode::Skip, 0, 100)
    ///     .await?;
    /// println!("Successes: {}", result.successes.len());
    /// println!("Failures: {}", result.failures.len());
    /// # Ok(())
    /// # }
    /// ```
    pub async fn scrape_courses_batch(
        &self,
        indices: Vec<i32>,
        mode: ErrorMode,
        max_retries: u32,
        retry_delay_ms: u64,
    ) -> Result<ScrapeResult, HttpError> {
        let mut result = ScrapeResult::new();
        let total = indices.len();

        for (position, &index) in indices.iter().enumerate() {
            log::info!(
                "Scraping course {}/{} (index {})",
                position + 1,
                total,
                index
            );

            let effective_retries = if mode == ErrorMode::Retry {
                max_retries
            } else {
                0
            };
            let course = self
                .scrape_course_with_retry(index, effective_retries, retry_delay_ms)
                .await;

            match course {
                Ok(info) => {
                    result.successes.push(info);
                }
                Err(e) => match mode {
                    ErrorMode::Abort => {
                        log::error!("Aborted at course index {}: {}", index, e);
                        return Err(e);
                    }
                    ErrorMode::Skip => {
                        result.failures.push((index, e.to_string()));
                    }
                    ErrorMode::Retry => {
                        result.failures.push((index, e.to_string()));
                    }
                },
            }
        }

        Ok(result)
    }

    /// Scrape multiple courses concurrently with configurable parallelism.
    ///
    /// Uses `futures::stream::buffer_unordered` to execute up to `max_concurrent`
    /// scraping operations simultaneously. Each course is scraped independently,
    /// with errors handled according to the specified `ErrorMode`.
    ///
    /// The shared session state (ViewState, cookies) is protected by an `RwLock`,
    /// ensuring safe concurrent access without corruption.
    ///
    /// # Arguments
    /// * `indices` - Course indices to scrape
    /// * `max_concurrent` - Maximum number of concurrent scraping operations
    /// * `mode` - Error handling strategy
    /// * `max_retries` - Maximum retry attempts per course (used only in Retry mode)
    /// * `retry_delay_ms` - Base delay between retries in milliseconds
    ///
    /// # Returns
    /// `ScrapeResult` containing successes and failures
    ///
    /// # Errors
    /// Returns the original `HttpError` on first failure when mode is Abort.
    ///
    /// # Example
    /// ```no_run
    /// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// use sia_scraper::http::sia_session::SiaSession;
    /// use sia_scraper::models::scrape_result::ErrorMode;
    ///
    /// let session = SiaSession::new(30, "https://sia.unal.edu.co".to_string())?;
    /// let result = session
    ///     .scrape_courses_concurrent(vec![0, 1, 2], 5, ErrorMode::Skip, 0, 100)
    ///     .await?;
    /// println!("Successes: {}", result.successes.len());
    /// # Ok(())
    /// # }
    /// ```
    pub async fn scrape_courses_concurrent(
        &self,
        indices: Vec<i32>,
        max_concurrent: usize,
        mode: ErrorMode,
        max_retries: u32,
        retry_delay_ms: u64,
    ) -> Result<ScrapeResult, HttpError> {
        use futures::stream::{self, StreamExt};

        let effective_retries = if mode == ErrorMode::Retry {
            max_retries
        } else {
            0
        };

        let results: Vec<Result<CourseInfoModel, (i32, HttpError)>> = stream::iter(indices)
            .map(|index| {
                let session = self.clone();
                async move {
                    for attempt in 0..=effective_retries {
                        match session.scrape_course_info(index).await {
                            Ok(info) => return Ok(info),
                            Err(e) => {
                                if !should_retry(&e, &session.retry_config)
                                    || attempt == effective_retries
                                {
                                    return Err((index, e));
                                }
                                let base = retry_delay_ms.max(1);
                                let shift = attempt.min(31);
                                let backoff = base.saturating_mul(1u64 << shift);
                                let capped = backoff.min(session.retry_config.max_delay_ms);
                                sleep(Duration::from_millis(capped)).await;
                            }
                        }
                    }
                    unreachable!("retry loop must return before this point")
                }
            })
            .buffer_unordered(max_concurrent)
            .collect()
            .await;

        let mut result = ScrapeResult::new();

        for res in results {
            match res {
                Ok(info) => {
                    result.successes.push(info);
                }
                Err((index, e)) => match mode {
                    ErrorMode::Abort => {
                        log::error!("Aborted at course index {}: {}", index, e);
                        return Err(e);
                    }
                    ErrorMode::Skip | ErrorMode::Retry => {
                        result.failures.push((index, e.to_string()));
                    }
                },
            }
        }

        Ok(result)
    }

    /// Attempt to scrape a single course with retry logic.
    ///
    /// # Arguments
    /// * `index` - Course index to scrape
    /// * `max_retries` - Maximum number of retry attempts
    /// * `retry_delay_ms` - Base delay between retries in milliseconds
    ///
    /// # Returns
    /// `CourseInfoModel` on success, or the last `HttpError` on failure.
    async fn scrape_course_with_retry(
        &self,
        index: i32,
        max_retries: u32,
        retry_delay_ms: u64,
    ) -> Result<CourseInfoModel, HttpError> {
        for attempt in 0..=max_retries {
            match self.scrape_course_info(index).await {
                Ok(info) => return Ok(info),
                Err(e) => {
                    if !should_retry(&e, &self.retry_config) || attempt == max_retries {
                        return Err(e);
                    }
                    let base = retry_delay_ms.max(1);
                    let shift = attempt.min(31);
                    let backoff = base.saturating_mul(1u64 << shift);
                    let capped = backoff.min(self.retry_config.max_delay_ms);
                    sleep(Duration::from_millis(capped)).await;
                }
            }
        }
        unreachable!("retry loop must return before this point");
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::constants::SIA_BASE_URL;

    #[tokio::test]
    async fn test_session_creation() {
        let session = SiaSession::new(15, "https://httpbin.org".to_string());
        assert!(session.is_ok());
    }

    #[tokio::test]
    async fn test_default_session() {
        let session = SiaSession::new(15, SIA_BASE_URL.to_string()).expect("default session should create");
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
        let builder = session.state_as_request_builder(&state).expect("state_as_request_builder should succeed");
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

    #[tokio::test]
    async fn test_scrape_course_info_rejects_invalid_status() {
        let session = SiaSession::new(15, "https://httpbin.org".to_string()).unwrap();
        let result = session.scrape_course_info(0).await;
        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(err.to_string().contains("not on career or course page"));
    }

    #[tokio::test]
    async fn test_scrape_course_info_rejects_out_of_range_index() {
        let session = SiaSession::new(15, "https://httpbin.org".to_string()).unwrap();
        {
            let mut state = session.state.write().await;
            state.status = "ON_CAREER_PAGE".to_string();
            state.career_code = "0-2-8-3".to_string();
            state.course_list = vec![
                std::collections::HashMap::from([("code".to_string(), "COUR-101".to_string())]),
                std::collections::HashMap::from([("code".to_string(), "COUR-102".to_string())]),
                std::collections::HashMap::from([("code".to_string(), "COUR-103".to_string())]),
            ];
        }
        let result = session.scrape_course_info(10).await;
        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(err.to_string().contains("out of range"));
    }

    #[tokio::test]
    async fn test_scrape_course_prereqs_rejects_invalid_status() {
        let session = SiaSession::new(15, "https://httpbin.org".to_string()).unwrap();
        let result = session.scrape_course_prereqs(0).await;
        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(err.to_string().contains("not on career or course page"));
    }

    #[tokio::test]
    async fn test_scrape_course_prereqs_rejects_out_of_range_index() {
        let session = SiaSession::new(15, "https://httpbin.org".to_string()).unwrap();
        {
            let mut state = session.state.write().await;
            state.status = "ON_CAREER_PAGE".to_string();
            state.career_code = "0-2-8-3".to_string();
            state.course_list = vec![
                std::collections::HashMap::from([("code".to_string(), "COUR-101".to_string())]),
            ];
        }
        let result = session.scrape_course_prereqs(5).await;
        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(err.to_string().contains("out of range"));
    }

    #[tokio::test]
    async fn test_scrape_course_info_rejects_negative_index() {
        let session = SiaSession::new(15, "https://httpbin.org".to_string()).unwrap();
        {
            let mut state = session.state.write().await;
            state.status = "ON_CAREER_PAGE".to_string();
            state.career_code = "0-2-8-3".to_string();
            state.course_list = vec![
                std::collections::HashMap::from([("code".to_string(), "COUR-101".to_string())]),
            ];
        }
        let result = session.scrape_course_info(-1).await;
        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(err.to_string().contains("out of range"));
    }

    #[tokio::test]
    async fn test_scrape_course_info_rejects_empty_course_list() {
        let session = SiaSession::new(15, "https://httpbin.org".to_string()).unwrap();
        {
            let mut state = session.state.write().await;
            state.status = "ON_CAREER_PAGE".to_string();
            state.career_code = "0-2-8-3".to_string();
            state.course_list = vec![];
        }
        let result = session.scrape_course_info(0).await;
        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(err.to_string().contains("course list is empty"));
    }

    #[tokio::test]
    async fn test_scrape_course_prereqs_rejects_negative_index() {
        let session = SiaSession::new(15, "https://httpbin.org".to_string()).unwrap();
        {
            let mut state = session.state.write().await;
            state.status = "ON_CAREER_PAGE".to_string();
            state.career_code = "0-2-8-3".to_string();
            state.course_list = vec![
                std::collections::HashMap::from([("code".to_string(), "COUR-101".to_string())]),
            ];
        }
        let result = session.scrape_course_prereqs(-1).await;
        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(err.to_string().contains("out of range"));
    }

    #[tokio::test]
    async fn test_scrape_course_prereqs_rejects_empty_course_list() {
        let session = SiaSession::new(15, "https://httpbin.org".to_string()).unwrap();
        {
            let mut state = session.state.write().await;
            state.status = "ON_CAREER_PAGE".to_string();
            state.career_code = "0-2-8-3".to_string();
            state.course_list = vec![];
        }
        let result = session.scrape_course_prereqs(0).await;
        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(err.to_string().contains("course list is empty"));
    }

    #[tokio::test]
    async fn test_scrape_courses_batch_abort_mode_empty_indices() {
        let session = SiaSession::new(15, "https://httpbin.org".to_string()).unwrap();
        let result = session
            .scrape_courses_batch(vec![], ErrorMode::Abort, 0, 100)
            .await;
        assert!(result.is_ok());
        let result = result.unwrap();
        assert_eq!(result.total(), 0);
        assert_eq!(result.success_rate(), 1.0);
    }

    #[tokio::test]
    async fn test_scrape_courses_batch_skip_mode_invalid_status() {
        let session = SiaSession::new(15, "https://httpbin.org".to_string()).unwrap();
        let result = session
            .scrape_courses_batch(vec![0, 1], ErrorMode::Skip, 0, 100)
            .await;
        assert!(result.is_ok());
        let result = result.unwrap();
        assert_eq!(result.successes.len(), 0);
        assert_eq!(result.failures.len(), 2);
    }

    #[tokio::test]
    async fn test_scrape_courses_batch_abort_mode_invalid_status() {
        let session = SiaSession::new(15, "https://httpbin.org".to_string()).unwrap();
        let result = session
            .scrape_courses_batch(vec![0, 1], ErrorMode::Abort, 0, 100)
            .await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_scrape_courses_batch_retry_mode_invalid_status() {
        let session = SiaSession::new(15, "https://httpbin.org".to_string()).unwrap();
        let result = session
            .scrape_courses_batch(vec![0, 1], ErrorMode::Retry, 1, 100)
            .await;
        assert!(result.is_ok());
        let result = result.unwrap();
        assert_eq!(result.successes.len(), 0);
        assert_eq!(result.failures.len(), 2);
    }

    #[tokio::test]
    async fn test_scrape_courses_batch_skip_mode_processes_all_indices() {
        let session = SiaSession::new(15, "https://httpbin.org".to_string()).unwrap();
        let indices = vec![0, 1, 2, 3, 4];
        let result = session
            .scrape_courses_batch(indices.clone(), ErrorMode::Skip, 0, 100)
            .await;
        assert!(result.is_ok());
        let result = result.unwrap();
        // All indices should be recorded as failures (no valid session)
        assert_eq!(result.total(), indices.len());
        assert_eq!(result.successes.len(), 0);
        assert_eq!(result.failures.len(), indices.len());
        // Verify all indices are recorded
        let failure_indices: Vec<i32> = result.failures.iter().map(|(idx, _)| *idx).collect();
        for idx in &indices {
            assert!(failure_indices.contains(idx));
        }
    }

    #[tokio::test]
    async fn test_scrape_courses_batch_abort_stops_on_first_failure() {
        let session = SiaSession::new(15, "https://httpbin.org".to_string()).unwrap();
        let result = session
            .scrape_courses_batch(vec![0, 1, 2], ErrorMode::Abort, 0, 100)
            .await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_scrape_courses_batch_empty_indices_all_modes() {
        let session = SiaSession::new(15, "https://httpbin.org".to_string()).unwrap();
        for mode in [ErrorMode::Abort, ErrorMode::Skip, ErrorMode::Retry] {
            let result = session
                .scrape_courses_batch(vec![], mode, 0, 100)
                .await;
            assert!(result.is_ok());
            let result = result.unwrap();
            assert_eq!(result.total(), 0);
            assert_eq!(result.success_rate(), 1.0);
            assert!(result.successes.is_empty());
            assert!(result.failures.is_empty());
        }
    }

    #[tokio::test]
    async fn test_scrape_courses_concurrent_empty_indices() {
        let session = SiaSession::new(15, "https://httpbin.org".to_string()).unwrap();
        for mode in [ErrorMode::Abort, ErrorMode::Skip, ErrorMode::Retry] {
            let result = session
                .scrape_courses_concurrent(vec![], 5, mode, 0, 100)
                .await;
            assert!(result.is_ok());
            let result = result.unwrap();
            assert_eq!(result.total(), 0);
            assert_eq!(result.success_rate(), 1.0);
            assert!(result.successes.is_empty());
            assert!(result.failures.is_empty());
        }
    }

    #[tokio::test]
    async fn test_scrape_courses_concurrent_skip_mode_invalid_status() {
        let session = SiaSession::new(15, "https://httpbin.org".to_string()).unwrap();
        let result = session
            .scrape_courses_concurrent(vec![0, 1, 2], 3, ErrorMode::Skip, 0, 100)
            .await;
        assert!(result.is_ok());
        let result = result.unwrap();
        assert_eq!(result.successes.len(), 0);
        assert_eq!(result.failures.len(), 3);
    }

    #[tokio::test]
    async fn test_scrape_courses_concurrent_abort_mode_invalid_status() {
        let session = SiaSession::new(15, "https://httpbin.org".to_string()).unwrap();
        let result = session
            .scrape_courses_concurrent(vec![0, 1, 2], 3, ErrorMode::Abort, 0, 100)
            .await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_scrape_courses_concurrent_retry_mode_invalid_status() {
        let session = SiaSession::new(15, "https://httpbin.org".to_string()).unwrap();
        let result = session
            .scrape_courses_concurrent(vec![0, 1], 2, ErrorMode::Retry, 1, 100)
            .await;
        assert!(result.is_ok());
        let result = result.unwrap();
        assert_eq!(result.successes.len(), 0);
        assert_eq!(result.failures.len(), 2);
    }

    #[tokio::test]
    async fn test_scrape_courses_concurrent_processes_all_indices() {
        let session = SiaSession::new(15, "https://httpbin.org".to_string()).unwrap();
        let indices = vec![0, 1, 2, 3, 4];
        let result = session
            .scrape_courses_concurrent(indices.clone(), 3, ErrorMode::Skip, 0, 100)
            .await;
        assert!(result.is_ok());
        let result = result.unwrap();
        assert_eq!(result.total(), indices.len());
        assert_eq!(result.successes.len(), 0);
        assert_eq!(result.failures.len(), indices.len());
        let failure_indices: Vec<i32> = result.failures.iter().map(|(idx, _)| *idx).collect();
        for idx in &indices {
            assert!(failure_indices.contains(idx));
        }
    }

    #[tokio::test]
    async fn test_scrape_courses_concurrent_abort_stops_on_first_failure() {
        let session = SiaSession::new(15, "https://httpbin.org".to_string()).unwrap();
        let result = session
            .scrape_courses_concurrent(vec![0, 1, 2], 3, ErrorMode::Abort, 0, 100)
            .await;
        assert!(result.is_err());
    }
}
