use crate::error::SiaScraperError;
use pyo3::prelude::*;
use quick_xml::events::Event;
use quick_xml::Reader;

pub fn parse_course_xml(xml: &str, py: Python<'_>) -> Result<Py<PyAny>, SiaScraperError> {
    let mut reader = Reader::from_str(xml);
    reader.trim_text(true);

    let mut buf = Vec::new();
    let mut course_name = String::new();
    let mut course_code = String::new();

    loop {
        match reader.read_event_into(&mut buf) {
            Ok(Event::Start(ref e)) if e.name().as_ref() == b"nombre" => {
                if let Ok(Event::Text(t)) = reader.read_event_into(&mut buf) {
                    course_name = t.unescape().unwrap_or_default().to_string();
                }
            }
            Ok(Event::Start(ref e)) if e.name().as_ref() == b"codigo" => {
                if let Ok(Event::Text(t)) = reader.read_event_into(&mut buf) {
                    course_code = t.unescape().unwrap_or_default().to_string();
                }
            }
            Ok(Event::Eof) => break,
            Err(e) => return Err(SiaScraperError::XmlError(e.to_string())),
            _ => {}
        }
        buf.clear();
    }

    let result = pyo3::types::PyDict::new(py);
    result.set_item("nombre", course_name)?;
    result.set_item("codigo", course_code)?;

    Ok(result.into())
}

pub fn parse_prereqs_xml(xml: &str, py: Python<'_>) -> Result<Py<PyAny>, SiaScraperError> {
    let mut reader = Reader::from_str(xml);
    reader.trim_text(true);

    let mut buf = Vec::new();
    let mut prereqs = Vec::new();

    loop {
        match reader.read_event_into(&mut buf) {
            Ok(Event::Start(ref e)) if e.name().as_ref() == b"prerequisito" => {
                if let Ok(Event::Text(t)) = reader.read_event_into(&mut buf) {
                    prereqs.push(t.unescape().unwrap_or_default().to_string());
                }
            }
            Ok(Event::Eof) => break,
            Err(e) => return Err(SiaScraperError::XmlError(e.to_string())),
            _ => {}
        }
        buf.clear();
    }

    let result = pyo3::types::PyList::new(py, &prereqs);
    Ok(result.into())
}
