//! Typed course parsing models.

#![allow(non_local_definitions)]

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use serde::{Deserialize, Serialize};

use super::helpers::require_field;

type GroupModelPickleState = (
    String,
    String,
    String,
    String,
    Vec<ScheduleModel>,
    String,
    String,
    Option<i64>,
    Option<String>,
);

type CourseInfoModelPickleState = (
    String,
    i32,
    String,
    i64,
    String,
    Vec<GroupModel>,
    Option<String>,
);

/// Class schedule entry.
#[pyclass(module = "sia_scraper_rust")]
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ScheduleModel {
    #[pyo3(get)]
    pub day: String,
    #[pyo3(get)]
    pub start_time: String,
    #[pyo3(get)]
    pub end_time: String,
    #[pyo3(get)]
    pub classroom: String,
}

#[pymethods]
impl ScheduleModel {
    #[new]
    fn new(day: String, start_time: String, end_time: String, classroom: String) -> Self {
        Self {
            day,
            start_time,
            end_time,
            classroom,
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "ScheduleModel(day='{}', start_time='{}', end_time='{}', classroom='{}')",
            self.day, self.start_time, self.end_time, self.classroom
        )
    }

    fn __str__(&self) -> String {
        format!("{} {} - {}", self.day, self.start_time, self.end_time)
    }

    fn __getnewargs__(&self) -> (String, String, String, String) {
        (String::new(), String::new(), String::new(), String::new())
    }

    fn __getstate__(&self, py: Python<'_>) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        dict.set_item("day", self.day.clone())?;
        dict.set_item("start_time", self.start_time.clone())?;
        dict.set_item("end_time", self.end_time.clone())?;
        dict.set_item("classroom", self.classroom.clone())?;
        Ok(dict.into())
    }

    fn __setstate__(&mut self, state: &PyAny) -> PyResult<()> {
        let dict = state.downcast::<PyDict>()?;
        self.day = require_field(dict, "day")?;
        self.start_time = require_field(dict, "start_time")?;
        self.end_time = require_field(dict, "end_time")?;
        self.classroom = require_field(dict, "classroom")?;
        Ok(())
    }
}

/// One available group for a course.
#[pyclass(module = "sia_scraper_rust")]
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct GroupModel {
    #[pyo3(get)]
    pub group_name: String,
    #[pyo3(get)]
    pub teacher: String,
    #[pyo3(get)]
    pub faculty: String,
    #[pyo3(get)]
    pub course_name: String,
    #[pyo3(get)]
    pub schedules: Vec<ScheduleModel>,
    #[pyo3(get)]
    pub duration: String,
    #[pyo3(get)]
    pub schedule_type: String,
    #[pyo3(get)]
    pub spots: Option<i64>,
    #[pyo3(get)]
    pub code: Option<String>,
}

#[pymethods]
impl GroupModel {
    #[new]
    #[pyo3(signature = (group_name, teacher, faculty, course_name, schedules, duration, schedule_type, spots=None, code=None))]
    #[allow(clippy::too_many_arguments)]
    fn new(
        group_name: String,
        teacher: String,
        faculty: String,
        course_name: String,
        schedules: Vec<ScheduleModel>,
        duration: String,
        schedule_type: String,
        spots: Option<i64>,
        code: Option<String>,
    ) -> Self {
        Self {
            group_name,
            teacher,
            faculty,
            course_name,
            schedules,
            duration,
            schedule_type,
            spots,
            code,
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "GroupModel(group_name='{}', teacher='{}', schedules_count={})",
            self.group_name,
            self.teacher,
            self.schedules.len()
        )
    }

    fn __str__(&self) -> String {
        format!("{} - {}", self.group_name, self.teacher)
    }

    fn __getnewargs__(&self) -> GroupModelPickleState {
        (
            self.group_name.clone(),
            self.teacher.clone(),
            self.faculty.clone(),
            self.course_name.clone(),
            self.schedules.clone(),
            self.duration.clone(),
            self.schedule_type.clone(),
            self.spots,
            self.code.clone(),
        )
    }

    fn __getstate__(&self, py: Python<'_>) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        dict.set_item("group_name", self.group_name.clone())?;
        dict.set_item("teacher", self.teacher.clone())?;
        dict.set_item("faculty", self.faculty.clone())?;
        dict.set_item("course_name", self.course_name.clone())?;
        dict.set_item("duration", self.duration.clone())?;
        dict.set_item("schedule_type", self.schedule_type.clone())?;
        dict.set_item("spots", self.spots)?;
        dict.set_item("code", self.code.clone())?;

        let schedules = PyList::empty(py);
        for schedule in &self.schedules {
            schedules.append(schedule.__getstate__(py)?)?;
        }
        dict.set_item("schedules", schedules)?;
        Ok(dict.into())
    }

    fn __setstate__(&mut self, state: &PyAny) -> PyResult<()> {
        let dict = state.downcast::<PyDict>()?;
        self.group_name = require_field(dict, "group_name")?;
        self.teacher = require_field(dict, "teacher")?;
        self.faculty = require_field(dict, "faculty")?;
        self.course_name = require_field(dict, "course_name")?;
        self.duration = require_field(dict, "duration")?;
        self.schedule_type = require_field(dict, "schedule_type")?;
        self.spots = require_field(dict, "spots")?;
        self.code = require_field(dict, "code")?;

        let list = super::helpers::required_item(dict, "schedules")?.downcast::<PyList>()?;
        let mut schedules = Vec::with_capacity(list.len());
        for item in list.iter() {
            let mut schedule = ScheduleModel {
                day: String::new(),
                start_time: String::new(),
                end_time: String::new(),
                classroom: String::new(),
            };
            schedule.__setstate__(item)?;
            schedules.push(schedule);
        }
        self.schedules = schedules;
        Ok(())
    }
}

/// Typed result of course detail parsing.
#[pyclass(module = "sia_scraper_rust")]
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct CourseInfoModel {
    #[pyo3(get)]
    pub course_name: String,
    #[pyo3(get)]
    pub credits: i32,
    #[pyo3(get)]
    pub typology: String,
    #[pyo3(get)]
    pub available_spots: i64,
    #[pyo3(get)]
    pub scrape_timestamp: String,
    #[pyo3(get)]
    pub groups: Vec<GroupModel>,
    #[pyo3(get, set)]
    pub code: Option<String>,
}

#[pymethods]
impl CourseInfoModel {
    #[new]
    #[pyo3(signature = (course_name, credits, typology, available_spots, scrape_timestamp, groups=None, code=None))]
    #[allow(clippy::too_many_arguments)]
    fn new(
        course_name: String,
        credits: i32,
        typology: String,
        available_spots: i64,
        scrape_timestamp: String,
        groups: Option<Vec<GroupModel>>,
        code: Option<String>,
    ) -> Self {
        Self {
            course_name,
            credits,
            typology,
            available_spots,
            scrape_timestamp,
            groups: groups.unwrap_or_default(),
            code,
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "CourseInfoModel(course_name='{}', credits={}, groups_count={})",
            self.course_name,
            self.credits,
            self.groups.len()
        )
    }

    fn __str__(&self) -> String {
        format!("{} ({} credits)", self.course_name, self.credits)
    }

    fn __getnewargs__(&self) -> CourseInfoModelPickleState {
        (
            String::new(),
            0,
            String::new(),
            0,
            String::new(),
            Vec::new(),
            None,
        )
    }

    fn __getstate__(&self, py: Python<'_>) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        dict.set_item("course_name", self.course_name.clone())?;
        dict.set_item("credits", self.credits)?;
        dict.set_item("typology", self.typology.clone())?;
        dict.set_item("available_spots", self.available_spots)?;
        dict.set_item("scrape_timestamp", self.scrape_timestamp.clone())?;
        dict.set_item("code", self.code.clone())?;

        let groups = PyList::empty(py);
        for group in &self.groups {
            groups.append(group.__getstate__(py)?)?;
        }
        dict.set_item("groups", groups)?;
        Ok(dict.into())
    }

    fn __setstate__(&mut self, state: &PyAny) -> PyResult<()> {
        let dict = state.downcast::<PyDict>()?;
        self.course_name = require_field(dict, "course_name")?;
        self.credits = require_field(dict, "credits")?;
        self.typology = require_field(dict, "typology")?;
        self.available_spots = require_field(dict, "available_spots")?;
        self.scrape_timestamp = require_field(dict, "scrape_timestamp")?;
        self.code = require_field(dict, "code")?;

        let list = super::helpers::required_item(dict, "groups")?.downcast::<PyList>()?;
        let mut groups = Vec::with_capacity(list.len());
        for item in list.iter() {
            let mut group = GroupModel {
                group_name: String::new(),
                teacher: String::new(),
                faculty: String::new(),
                course_name: String::new(),
                schedules: Vec::new(),
                duration: String::new(),
                schedule_type: String::new(),
                spots: None,
                code: None,
            };
            group.__setstate__(item)?;
            groups.push(group);
        }
        self.groups = groups;
        Ok(())
    }
}
