//! Parsers for extracting data from SIA Oracle ADF responses.
//!
//! This module provides functions for extracting course information, prerequisites,
//! and course lists from the HTML/XML responses returned by SIA's web interface.
//!
//! ## Modules
//!
//! - [`adf`]: Oracle ADF-specific parsing utilities (ViewState extraction)
//! - [`adf_request`]: Oracle ADF request body builder
//! - [`course_parser`]: Course information and prerequisite parsing
//! - [`table_parser`]: Course list table parsing
//! - [`utils`]: Shared parsing utilities
//!
//! ## Usage Example
//!
//! ```rust
//! use sia_scraper_rust::{parse_course_info, extract_view_state};
//!
//! // Extract ViewState from login response
//! let html = r#"<input type="hidden" name="javax.faces.ViewState" value="abc123">"#;
//! let view_state = extract_view_state(html).unwrap();
//! assert_eq!(view_state, "abc123");
//!
//! // Parse course information from detail page
//! let course_xml = r#"
//!     <h2>CALCULO I</h2>
//!     <span class="detass-creditos"><span>4</span></span>
//!     <span class="detass-tipologia"><span>DISCIPLINAR OBLIGATORIA</span></span>
//! "#;
//! let course_info = parse_course_info(course_xml).unwrap();
//! println!("Course: {}", course_info["course_name"]);
//! ```

pub mod adf;
pub mod adf_request;
pub mod course_parser;
pub mod table_parser;
pub mod utils;
