//! Typed prerequisite parsing models.

use serde::{Deserialize, Serialize};

/// One prerequisite course reference.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct PrerequisiteModel {
    pub course_code: String,
    pub course_name: String,
}

/// One prerequisite condition block.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct PrereqConditionModel {
    pub condition: i32,
    pub prereq_type: String,
    pub all_required: bool,
    pub number_of_courses: i32,
    pub prerequisites: Vec<PrerequisiteModel>,
}

/// Typed result of prerequisite parsing.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct CoursePrereqsModel {
    pub course_name: String,
    pub code: Option<String>,
    pub credits: i32,
    pub typology: String,
    pub conditions: Vec<PrereqConditionModel>,
}
