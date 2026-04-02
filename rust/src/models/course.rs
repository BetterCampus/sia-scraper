//! Typed course parsing models.

use pyo3::exceptions::PyKeyError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use serde::{Deserialize, Serialize};

fn required_item<'py>(dict: &'py PyDict, key: &str) -> PyResult<&'py PyAny> {
    dict.get_item(key)?
        .ok_or_else(|| PyKeyError::new_err(format!("Missing key: {key}")))
}

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
        dict.set_item("day", &self.day)?;
        dict.set_item("start_time", &self.start_time)?;
        dict.set_item("end_time", &self.end_time)?;
        dict.set_item("classroom", &self.classroom)?;
        Ok(dict.into())
    }

    fn __setstate__(&mut self, state: &PyAny) -> PyResult<()> {
        let dict = state.downcast::<PyDict>()?;
        self.day = required_item(dict, "day")?.extract()?;
        self.start_time = required_item(dict, "start_time")?.extract()?;
        self.end_time = required_item(dict, "end_time")?.extract()?;
        self.classroom = required_item(dict, "classroom")?.extract()?;
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

    fn __getnewargs__(
        &self,
    ) -> (
        String,
        String,
        String,
        String,
        Vec<ScheduleModel>,
        String,
        String,
        Option<i64>,
        Option<String>,
    ) {
        (
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            Vec::new(),
            String::new(),
            String::new(),
            None,
            None,
        )
    }

    fn __getstate__(&self, py: Python<'_>) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        dict.set_item("group_name", &self.group_name)?;
        dict.set_item("teacher", &self.teacher)?;
        dict.set_item("faculty", &self.faculty)?;
        dict.set_item("course_name", &self.course_name)?;
        dict.set_item("duration", &self.duration)?;
        dict.set_item("schedule_type", &self.schedule_type)?;
        dict.set_item("spots", &self.spots)?;
        dict.set_item("code", &self.code)?;

        let schedules = PyList::empty(py);
        for schedule in &self.schedules {
            schedules.append(schedule.__getstate__(py)?)?;
        }
        dict.set_item("schedules", schedules)?;
        Ok(dict.into())
    }

    fn __setstate__(&mut self, state: &PyAny) -> PyResult<()> {
        let dict = state.downcast::<PyDict>()?;
        self.group_name = required_item(dict, "group_name")?.extract()?;
        self.teacher = required_item(dict, "teacher")?.extract()?;
        self.faculty = required_item(dict, "faculty")?.extract()?;
        self.course_name = required_item(dict, "course_name")?.extract()?;
        self.duration = required_item(dict, "duration")?.extract()?;
        self.schedule_type = required_item(dict, "schedule_type")?.extract()?;
        self.spots = required_item(dict, "spots")?.extract()?;
        self.code = required_item(dict, "code")?.extract()?;

        let list = required_item(dict, "schedules")?.downcast::<PyList>()?;
        let mut schedules = Vec::with_capacity(list.len());
        for item in list.iter() {
            let mut schedule =
                ScheduleModel::new(String::new(), String::new(), String::new(), String::new());
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
    #[pyo3(get)]
    pub code: Option<String>,
}

#[pymethods]
impl CourseInfoModel {
    #[new]
    #[allow(clippy::too_many_arguments)]
    fn new(
        course_name: String,
        credits: i32,
        typology: String,
        available_spots: i64,
        scrape_timestamp: String,
        groups: Vec<GroupModel>,
        code: Option<String>,
    ) -> Self {
        Self {
            course_name,
            credits,
            typology,
            available_spots,
            scrape_timestamp,
            groups,
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

    fn __getnewargs__(
        &self,
    ) -> (
        String,
        i32,
        String,
        i64,
        String,
        Vec<GroupModel>,
        Option<String>,
    ) {
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
        dict.set_item("course_name", &self.course_name)?;
        dict.set_item("credits", &self.credits)?;
        dict.set_item("typology", &self.typology)?;
        dict.set_item("available_spots", &self.available_spots)?;
        dict.set_item("scrape_timestamp", &self.scrape_timestamp)?;
        dict.set_item("code", &self.code)?;

        let groups = PyList::empty(py);
        for group in &self.groups {
            groups.append(group.__getstate__(py)?)?;
        }
        dict.set_item("groups", groups)?;
        Ok(dict.into())
    }

    fn __setstate__(&mut self, state: &PyAny) -> PyResult<()> {
        let dict = state.downcast::<PyDict>()?;
        self.course_name = required_item(dict, "course_name")?.extract()?;
        self.credits = required_item(dict, "credits")?.extract()?;
        self.typology = required_item(dict, "typology")?.extract()?;
        self.available_spots = required_item(dict, "available_spots")?.extract()?;
        self.scrape_timestamp = required_item(dict, "scrape_timestamp")?.extract()?;
        self.code = required_item(dict, "code")?.extract()?;

        let list = required_item(dict, "groups")?.downcast::<PyList>()?;
        let mut groups = Vec::with_capacity(list.len());
        for item in list.iter() {
            let mut group = GroupModel::new(
                String::new(),
                String::new(),
                String::new(),
                String::new(),
                Vec::new(),
                String::new(),
                String::new(),
                None,
                None,
            );
            group.__setstate__(item)?;
            groups.push(group);
        }
        self.groups = groups;
        Ok(())
    }
}
