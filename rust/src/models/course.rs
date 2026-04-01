//! Typed course parsing models.

use serde::{Deserialize, Serialize};

/// Class schedule entry.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ScheduleModel {
    pub day: String,
    pub start_time: String,
    pub end_time: String,
    pub classroom: String,
}

/// One available group for a course.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct GroupModel {
    pub group_name: String,
    pub teacher: String,
    pub faculty: String,
    pub course_name: String,
    pub schedules: Vec<ScheduleModel>,
    pub duration: String,
    pub schedule_type: String,
    pub spots: Option<i64>,
    pub code: Option<String>,
}

/// Typed result of course detail parsing.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct CourseInfoModel {
    pub course_name: String,
    pub credits: i32,
    pub typology: String,
    pub available_spots: i64,
    pub scrape_timestamp: String,
    pub groups: Vec<GroupModel>,
    pub code: Option<String>,
}
