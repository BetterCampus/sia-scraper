//! Unit tests for course parsing functions.

use crate::{parse_course_info, parse_prereqs};
use pyo3::Python;

#[test]
fn test_parse_course_xml_complete() {
    let xml = r#"
        <html>
            <body>
                <h2>CALCULO AVANZADO</h2>
                <span class="detass-creditos"><span>4</span></span>
                <span class="detass-tipologia"><span>DISCIPLINAR OBLIGATORIA</span></span>
                <div class="af_showDetailHeader_content0">
                    <div class="af_panelGroupLayout">
                        <div><span>Prof. Juan Perez</span></div>
                        <div><span>Facultad de Ciencias</span></div>
                        <div><span class="lista-elemento">Lunes de 08:00 a 10:00<span class="lista-elemento">A101</span></span></div>
                        <div><span>Semestral</span></div>
                        <div><span>Teórico</span></div>
                        <div><span>25</span></div>
                    </div>
                </div>
            </body>
        </html>
    "#;

    Python::with_gil(|py| {
        let result = parse_course_info(xml);
        assert!(result.is_ok());

        let py_result = result.unwrap();
        let dict = py_result.as_ref(py);
        let course_name = dict.get_item("course_name").unwrap();
        assert_eq!(course_name.extract::<String>().unwrap(), "CALCULO AVANZADO");

        let credits = dict.get_item("credits").unwrap();
        assert_eq!(credits.extract::<i32>().unwrap(), 4);

        let typology = dict.get_item("typology").unwrap();
        assert_eq!(
            typology.extract::<String>().unwrap(),
            "DISCIPLINAR OBLIGATORIA"
        );

        let groups = dict.get_item("groups").unwrap();
        let groups_list: Vec<pyo3::Py<pyo3::types::PyAny>> = groups.extract().unwrap();
        assert_eq!(groups_list.len(), 1);
    });
}

#[test]
fn test_parse_course_xml_no_groups() {
    let xml = r#"
        <html>
            <body>
                <h2>INTRODUCCION A LA PROGRAMACION</h2>
                <span class="detass-creditos"><span>3</span></span>
                <span class="detass-tipologia"><span>FORMACION BASICA</span></span>
            </body>
        </html>
    "#;

    Python::with_gil(|py| {
        let result = parse_course_info(xml);
        assert!(result.is_ok());

        let py_result = result.unwrap();
        let dict = py_result.as_ref(py);
        let course_name = dict.get_item("course_name").unwrap();
        assert_eq!(
            course_name.extract::<String>().unwrap(),
            "INTRODUCCION A LA PROGRAMACION"
        );

        let credits = dict.get_item("credits").unwrap();
        assert_eq!(credits.extract::<i32>().unwrap(), 3);

        let groups = dict.get_item("groups").unwrap();
        let groups_list: Vec<pyo3::Py<pyo3::types::PyAny>> = groups.extract().unwrap();
        assert_eq!(groups_list.len(), 0);
    });
}

#[test]
fn test_parse_course_xml_missing_credits() {
    let xml = r#"
        <html>
            <body>
                <h2>CALCULO AVANZADO</h2>
                <span class="detass-tipologia"><span>DISCIPLINAR OBLIGATORIA</span></span>
            </body>
        </html>
    "#;

    let result = Python::with_gil(|_py| parse_course_info(xml));
    assert!(result.is_err());
}

#[test]
fn test_parse_course_xml_invalid_credits() {
    let xml = r#"
        <html>
            <body>
                <h2>CALCULO AVANZADO</h2>
                <span class="detass-creditos"><span>not-a-number</span></span>
                <span class="detass-tipologia"><span>DISCIPLINAR OBLIGATORIA</span></span>
            </body>
        </html>
    "#;

    let result = Python::with_gil(|_py| parse_course_info(xml));
    assert!(result.is_err());
}

#[test]
fn test_parse_course_xml_missing_course_name() {
    let xml = r#"
        <html>
            <body>
                <span class="detass-creditos"><span>4</span></span>
                <span class="detass-tipologia"><span>DISCIPLINAR OBLIGATORIA</span></span>
            </body>
        </html>
    "#;

    let result = Python::with_gil(|_py| parse_course_info(xml));
    assert!(result.is_err());
}

#[test]
fn test_parse_prereqs_xml_complete() {
    let xml = r#"
        <html>
            <body>
                <h2>CALCULO AVANZADO</h2>
                <span class="detass-creditos"><span>4</span></span>
                <span class="detass-tipologia"><span>DISCIPLINAR OBLIGATORIA</span></span>
                <span class="borde salto af_panelGroupLayout">
                    <div class="margin-t af_panelGroupLayout">
                        <div>
                            <span class="strong af_panelGroupLayout">
                                <span class="margin-l">Condición</span>
                            </span>
                            <span>Haber aprobado</span>
                            <span class="strong af_panelGroupLayout">
                                <span class="margin-l">Tipo</span>
                            </span>
                            <span>Materia</span>
                            <span class="strong af_panelGroupLayout">
                                <span class="margin-l">¿Todas?</span>
                            </span>
                            <span>SI</span>
                            <span class="strong af_panelGroupLayout">
                                <span class="margin-l">Número asignaturas</span>
                            </span>
                            <span>2</span>
                        </div>
                        <div>
                            <span class="af_panelGroupLayout"><span>MATE1001</span><span>Calculo I</span></span>
                        </div>
                        <div>
                            <span class="af_panelGroupLayout"><span>MATE1002</span><span>Calculo II</span></span>
                        </div>
                    </div>
                </span>
            </body>
        </html>
    "#;

    Python::with_gil(|py| {
        let result = parse_prereqs(xml);
        assert!(result.is_ok());

        let py_result = result.unwrap();
        let dict = py_result.as_ref(py);
        let course_name = dict.get_item("course_name").unwrap();
        assert_eq!(course_name.extract::<String>().unwrap(), "CALCULO AVANZADO");

        let credits = dict.get_item("credits").unwrap();
        assert_eq!(credits.extract::<i32>().unwrap(), 4);

        let conditions = dict.get_item("conditions").unwrap();
        let conditions_list: Vec<pyo3::Py<pyo3::types::PyAny>> = conditions.extract().unwrap();
        assert!(!conditions_list.is_empty());
    });
}

#[test]
fn test_parse_prereqs_xml_no_conditions() {
    let xml = r#"
        <html>
            <body>
                <h2>INTRODUCCION A LA PROGRAMACION</h2>
                <span class="detass-creditos"><span>3</span></span>
                <span class="detass-tipologia"><span>FORMACION BASICA</span></span>
            </body>
        </html>
    "#;

    Python::with_gil(|py| {
        let result = parse_prereqs(xml);
        assert!(result.is_ok());

        let py_result = result.unwrap();
        let dict = py_result.as_ref(py);
        let conditions = dict.get_item("conditions").unwrap();
        let conditions_list: Vec<pyo3::Py<pyo3::types::PyAny>> = conditions.extract().unwrap();
        assert_eq!(conditions_list.len(), 0);
    });
}

#[test]
fn test_parse_prereqs_xml_missing_course_name() {
    let xml = r#"
        <html>
            <body>
                <span class="detass-creditos"><span>4</span></span>
                <span class="detass-tipologia"><span>DISCIPLINAR OBLIGATORIA</span></span>
            </body>
        </html>
    "#;

    let result = Python::with_gil(|_py| parse_prereqs(xml));
    assert!(result.is_err());
}
