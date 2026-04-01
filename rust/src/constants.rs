//! SIA System Constants
//!
//! Centralized constants for SIA URLs, taskflow IDs, required headers, and ADF IDs/actions.
//!
//! These constants must remain synchronized with Python constants in
//! `src/sia_scraper/constants/http.py`. Any changes to URLs, headers, or ADF IDs
//! should be reflected in both locations. A CI check (`.github/workflows/constants-sync-check.yml`)
//! verifies this synchronization.

// ============================================================================
// Base URLs and Taskflow IDs
// ============================================================================

/// SIA base URL for public catalog service
///
/// Must match `SIA_BASE_URL` in `src/sia_scraper/constants/http.py`.
pub const SIA_BASE_URL: &str =
    "https://sia.unal.edu.co/Catalogo/facespublico/public/servicioPublico.jsf";

/// Taskflow query parameter for catalog navigation
pub const SIA_TASKFLOW_ID: &str = "task-flow-AC_CatalogoAsignaturas";

/// Origin header value for SIA requests
///
/// Must match the origin used in `SIA_HEADERS` in `src/sia_scraper/constants/http.py`.
pub const SIA_ORIGIN: &str = "https://sia.unal.edu.co";

// ============================================================================
// Required HTTP Headers for SIA POST requests
// ============================================================================

/// Header constants for SIA HTTP requests.
///
/// These values must match `SIA_HEADERS` in `src/sia_scraper/constants/http.py`.
pub mod headers {
    /// Accept header value
    pub const ACCEPT: &str = "*/*";

    /// Accept-Language header value
    pub const ACCEPT_LANGUAGE: &str = "es-419,es;q=0.9,en;q=0.8";

    /// ADF ads page ID header value
    pub const ADF_ADS_PAGE_ID: &str = "1";

    /// ADF rich message header value
    pub const ADF_RICH_MESSAGE: &str = "true";

    /// Content-Type for form-encoded POST requests
    pub const CONTENT_TYPE: &str = "application/x-www-form-urlencoded";
}

// ============================================================================
// Oracle ADF Component IDs
// ============================================================================

/// Oracle ADF component IDs for dropdowns and UI elements.
pub mod adf_ids {
    /// Study level dropdown ID
    pub const STUDY_LEVEL_DD_ID: &str = "pt1:r1:0:soc1";

    /// Campus dropdown ID
    pub const CAMPUS_DD_ID: &str = "pt1:r1:0:soc9";

    /// Faculty dropdown ID
    pub const FACULTY_DD_ID: &str = "pt1:r1:0:soc2";

    /// Career dropdown ID
    pub const CAREER_DD_ID: &str = "pt1:r1:0:soc3";

    /// Career dropdown content ID (for option extraction)
    pub const CAREER_DROPDOWN_ID: &str = "pt1:r1:0:soc3::content";
}

// ============================================================================
// Oracle ADF Action Names
// ============================================================================

/// Oracle ADF action names for form submissions.
pub mod actions {
    /// Study level dropdown action
    pub const STUDY_LEVEL_DD: &str = "STUDY_LEVEL_DD";

    /// Campus dropdown action
    pub const CAMPUS_DD: &str = "CAMPUS_DD";

    /// Faculty dropdown action
    pub const FACULTY_DD: &str = "FACULTY_DD";

    /// Career dropdown action
    pub const CAREER_DD: &str = "CAREER_DD";

    /// Tipology dropdown action
    pub const TIPOLOGY_DD: &str = "TIPOLOGY_DD";

    /// Show courses button action
    pub const SHOW_COURSES_BTTN: &str = "SHOW_COURSES_BTTN";

    /// Faculty-career dropdown action (for electives)
    pub const FACULTY_CAREER_DD: &str = "FACULTY_CAREER_DD";

    /// Campus electives dropdown action
    pub const CAMPUS_ELECTIVES_DD: &str = "CAMPUS_ELECTIVES_DD";

    /// Select row action (course selection)
    pub const SELECT_ROW: &str = "SELECT_ROW";

    /// Course page link action
    pub const COURSE_PAGE_LINK: &str = "COURSE_PAGE_LINK";
}

// ============================================================================
// Miscellaneous Constants
// ============================================================================

/// Typology index value for elective courses
pub const ELECTIVES_TYPOLOGY_INDEX: &str = "7";

/// Offset for first option in dropdown (skip "Seleccione..." placeholder)
pub const DROPDOWN_FIRST_OPTION_OFFSET: usize = 1;

// ============================================================================
// Tests
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_base_url_is_valid_https() {
        assert!(SIA_BASE_URL.starts_with("https://"));
        assert!(SIA_BASE_URL.contains("sia.unal.edu.co"));
    }

    #[test]
    fn test_origin_matches_base_url_domain() {
        assert!(SIA_BASE_URL.starts_with(SIA_ORIGIN));
    }

    #[test]
    fn test_headers_are_non_empty() {
        assert!(!headers::ACCEPT.is_empty());
        assert!(!headers::CONTENT_TYPE.is_empty());
        assert_eq!(headers::ADF_ADS_PAGE_ID, "1");
        assert_eq!(headers::ADF_RICH_MESSAGE, "true");
    }

    #[test]
    fn test_adf_ids_are_non_empty() {
        assert!(!adf_ids::STUDY_LEVEL_DD_ID.is_empty());
        assert!(!adf_ids::CAREER_DD_ID.is_empty());
        assert!(adf_ids::CAREER_DROPDOWN_ID.contains("::content"));
    }

    #[test]
    fn test_actions_are_non_empty() {
        assert!(!actions::SHOW_COURSES_BTTN.is_empty());
        assert_eq!(actions::SELECT_ROW, "SELECT_ROW");
    }

    #[test]
    fn test_electives_typology_index() {
        assert_eq!(ELECTIVES_TYPOLOGY_INDEX, "7");
    }

    #[test]
    fn test_dropdown_offset() {
        assert_eq!(DROPDOWN_FIRST_OPTION_OFFSET, 1);
    }
}
