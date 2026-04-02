//! Typed prerequisite parsing models.

use pyo3::exceptions::PyKeyError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use serde::{Deserialize, Serialize};

fn required_item<'py>(dict: &'py PyDict, key: &str) -> PyResult<&'py PyAny> {
    dict.get_item(key)?
        .ok_or_else(|| PyKeyError::new_err(format!("Missing key: {key}")))
}

/// One prerequisite course reference.
#[pyclass(module = "sia_scraper_rust")]
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct PrerequisiteModel {
    #[pyo3(get)]
    pub course_code: String,
    #[pyo3(get)]
    pub course_name: String,
}

#[pymethods]
impl PrerequisiteModel {
    #[new]
    fn new(course_code: String, course_name: String) -> Self {
        Self {
            course_code,
            course_name,
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "PrerequisiteModel(course_code='{}', course_name='{}')",
            self.course_code, self.course_name
        )
    }

    fn __str__(&self) -> String {
        format!("{}: {}", self.course_code, self.course_name)
    }

    fn __getnewargs__(&self) -> (String, String) {
        (String::new(), String::new())
    }

    fn __getstate__(&self, py: Python<'_>) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        dict.set_item("course_code", &self.course_code)?;
        dict.set_item("course_name", &self.course_name)?;
        Ok(dict.into())
    }

    fn __setstate__(&mut self, state: &PyAny) -> PyResult<()> {
        let dict = state.downcast::<PyDict>()?;
        self.course_code = required_item(dict, "course_code")?.extract()?;
        self.course_name = required_item(dict, "course_name")?.extract()?;
        Ok(())
    }
}

/// One prerequisite condition block.
#[pyclass(module = "sia_scraper_rust")]
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct PrereqConditionModel {
    #[pyo3(get)]
    pub condition: i32,
    #[pyo3(get)]
    pub prereq_type: String,
    #[pyo3(get)]
    pub all_required: bool,
    #[pyo3(get)]
    pub number_of_courses: i32,
    #[pyo3(get)]
    pub prerequisites: Vec<PrerequisiteModel>,
}

#[pymethods]
impl PrereqConditionModel {
    #[new]
    fn new(
        condition: i32,
        prereq_type: String,
        all_required: bool,
        number_of_courses: i32,
        prerequisites: Vec<PrerequisiteModel>,
    ) -> Self {
        Self {
            condition,
            prereq_type,
            all_required,
            number_of_courses,
            prerequisites,
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "PrereqConditionModel(condition={}, prereq_type='{}', prereqs_count={})",
            self.condition,
            self.prereq_type,
            self.prerequisites.len()
        )
    }

    fn __str__(&self) -> String {
        format!(
            "Condition {}: {} ({} courses)",
            self.condition, self.prereq_type, self.number_of_courses
        )
    }

    fn __getnewargs__(&self) -> (i32, String, bool, i32, Vec<PrerequisiteModel>) {
        (0, String::new(), false, 0, Vec::new())
    }

    fn __getstate__(&self, py: Python<'_>) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        dict.set_item("condition", &self.condition)?;
        dict.set_item("prereq_type", &self.prereq_type)?;
        dict.set_item("all_required", &self.all_required)?;
        dict.set_item("number_of_courses", &self.number_of_courses)?;

        let prereqs = PyList::empty(py);
        for prereq in &self.prerequisites {
            prereqs.append(prereq.__getstate__(py)?)?;
        }
        dict.set_item("prerequisites", prereqs)?;
        Ok(dict.into())
    }

    fn __setstate__(&mut self, state: &PyAny) -> PyResult<()> {
        let dict = state.downcast::<PyDict>()?;
        self.condition = required_item(dict, "condition")?.extract()?;
        self.prereq_type = required_item(dict, "prereq_type")?.extract()?;
        self.all_required = required_item(dict, "all_required")?.extract()?;
        self.number_of_courses = required_item(dict, "number_of_courses")?.extract()?;

        let list = required_item(dict, "prerequisites")?.downcast::<PyList>()?;
        let mut prerequisites = Vec::with_capacity(list.len());
        for item in list.iter() {
            let mut prereq = PrerequisiteModel::new(String::new(), String::new());
            prereq.__setstate__(item)?;
            prerequisites.push(prereq);
        }
        self.prerequisites = prerequisites;
        Ok(())
    }
}

/// Typed result of prerequisite parsing.
#[pyclass(module = "sia_scraper_rust")]
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct CoursePrereqsModel {
    #[pyo3(get)]
    pub course_name: String,
    #[pyo3(get)]
    pub code: Option<String>,
    #[pyo3(get)]
    pub credits: i32,
    #[pyo3(get)]
    pub typology: String,
    #[pyo3(get)]
    pub conditions: Vec<PrereqConditionModel>,
}

#[pymethods]
impl CoursePrereqsModel {
    #[new]
    #[pyo3(signature = (course_name, credits, typology, conditions, code=None))]
    fn new(
        course_name: String,
        credits: i32,
        typology: String,
        conditions: Vec<PrereqConditionModel>,
        code: Option<String>,
    ) -> Self {
        Self {
            course_name,
            code,
            credits,
            typology,
            conditions,
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "CoursePrereqsModel(course_name='{}', credits={}, conditions_count={})",
            self.course_name,
            self.credits,
            self.conditions.len()
        )
    }

    fn __str__(&self) -> String {
        format!(
            "{} ({} credits, {} conditions)",
            self.course_name,
            self.credits,
            self.conditions.len()
        )
    }

    fn __getnewargs__(
        &self,
    ) -> (
        String,
        i32,
        String,
        Vec<PrereqConditionModel>,
        Option<String>,
    ) {
        (String::new(), 0, String::new(), Vec::new(), None)
    }

    fn __getstate__(&self, py: Python<'_>) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        dict.set_item("course_name", &self.course_name)?;
        dict.set_item("code", &self.code)?;
        dict.set_item("credits", &self.credits)?;
        dict.set_item("typology", &self.typology)?;

        let conditions = PyList::empty(py);
        for condition in &self.conditions {
            conditions.append(condition.__getstate__(py)?)?;
        }
        dict.set_item("conditions", conditions)?;
        Ok(dict.into())
    }

    fn __setstate__(&mut self, state: &PyAny) -> PyResult<()> {
        let dict = state.downcast::<PyDict>()?;
        self.course_name = required_item(dict, "course_name")?.extract()?;
        self.code = required_item(dict, "code")?.extract()?;
        self.credits = required_item(dict, "credits")?.extract()?;
        self.typology = required_item(dict, "typology")?.extract()?;

        let list = required_item(dict, "conditions")?.downcast::<PyList>()?;
        let mut conditions = Vec::with_capacity(list.len());
        for item in list.iter() {
            let mut condition = PrereqConditionModel::new(0, String::new(), false, 0, Vec::new());
            condition.__setstate__(item)?;
            conditions.push(condition);
        }
        self.conditions = conditions;
        Ok(())
    }
}
