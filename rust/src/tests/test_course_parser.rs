//! Unit tests for course parsing functions.

use crate::parsers::course_parser::{get_plain_text as rust_get_plain_text, parse_prereqs_xml};
use crate::{parse_course_info, parse_prereqs};
use pyo3::Python;

#[test]
fn test_get_plain_text_empty_input() {
    assert_eq!(rust_get_plain_text(""), "");
}

#[test]
fn test_get_plain_text_without_separator_returns_all_text() {
    let xml = "<html><body>Hello World</body></html>";
    assert_eq!(rust_get_plain_text(xml), "Hello World");
}

#[test]
fn test_get_plain_text_with_separator_returns_prefix() {
    let xml = "<html><body>Head\u{00A0}\u{00A0}\u{00A0}Tail</body></html>";
    assert_eq!(rust_get_plain_text(xml), "Head");
}

#[test]
fn test_parse_course_xml_complete() {
    let xml = r#"
        <html>
            <body>
                <h2>CALCULO AVANZADO</h2>
                <span class="detass-creditos"><span>4</span></span>
                <span class="detass-tipologia"><span>DISCIPLINAR OBLIGATORIA</span></span>
                <h2 class="af_showDetailHeader_title-text0">Grupo 01</h2>
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
fn test_parse_course_xml_typology_defaults_to_unknown() {
    let xml = r#"
        <html>
            <body>
                <h2>CALCULO AVANZADO</h2>
                <span class="detass-creditos"><span>4</span></span>
            </body>
        </html>
    "#;

    Python::with_gil(|py| {
        let result = parse_course_info(xml);
        assert!(result.is_ok());

        let py_result = result.unwrap();
        let dict = py_result.as_ref(py);
        let typology = dict.get_item("typology").unwrap();
        assert_eq!(typology.extract::<String>().unwrap(), "Unknown");
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
fn test_parse_course_xml_missing_credits_span() {
    let xml = r#"
        <html>
            <body>
                <h2>CALCULO AVANZADO</h2>
                <span class="detass-creditos"></span>
                <span class="detass-tipologia"><span>DISCIPLINAR OBLIGATORIA</span></span>
            </body>
        </html>
    "#;

    let result = Python::with_gil(|_py| parse_course_info(xml));
    assert!(result.is_err());
}

#[test]
fn test_parse_course_xml_typology_container_without_inner_span_defaults_unknown() {
    let xml = r#"
        <html>
            <body>
                <h2>CALCULO AVANZADO</h2>
                <span class="detass-creditos"><span>4</span></span>
                <span class="detass-tipologia"></span>
            </body>
        </html>
    "#;

    Python::with_gil(|py| {
        let result = parse_course_info(xml).unwrap();
        let dict = result.as_ref(py);
        let typology = dict.get_item("typology").unwrap();
        assert_eq!(typology.extract::<String>().unwrap(), "Unknown");
    });
}

#[test]
fn test_parse_course_xml_group_defaults_and_group_name_extraction() {
    let xml = r#"
        <html>
            <body>
                <h2>CALCULO AVANZADO</h2>
                <span class="detass-creditos"><span>4</span></span>
                <span class="detass-tipologia"><span>DISCIPLINAR OBLIGATORIA</span></span>
                <div>
                    <h2 class="af_showDetailHeader_title-text0">GRUPO 01</h2>
                    <div class="af_showDetailHeader_content0">
                        <div class="af_panelGroupLayout">
                            <div><span>Profesor Uno</span></div>
                        </div>
                    </div>
                </div>
            </body>
        </html>
    "#;

    Python::with_gil(|py| {
        let result = parse_course_info(xml).unwrap();
        let dict = result.as_ref(py);
        let groups = dict.get_item("groups").unwrap();
        let groups_list: Vec<pyo3::Py<pyo3::types::PyAny>> = groups.extract().unwrap();
        assert_eq!(groups_list.len(), 1);

        let group = groups_list[0].as_ref(py);
        assert_eq!(
            group
                .get_item("group_name")
                .unwrap()
                .extract::<String>()
                .unwrap(),
            "GRUPO 01"
        );
        assert_eq!(
            group
                .get_item("faculty")
                .unwrap()
                .extract::<String>()
                .unwrap(),
            "Unknown"
        );
        assert_eq!(
            group
                .get_item("duration")
                .unwrap()
                .extract::<String>()
                .unwrap(),
            "Unknown"
        );
        assert_eq!(
            group
                .get_item("schedule_type")
                .unwrap()
                .extract::<String>()
                .unwrap(),
            "Unknown"
        );
        assert_eq!(
            group.get_item("spots").unwrap().extract::<i64>().unwrap(),
            0
        );
    });
}

#[test]
fn test_parse_course_xml_extract_label_value_without_span_uses_extracted_text() {
    let xml = r#"
        <html>
            <body>
                <h2>CALCULO AVANZADO</h2>
                <span class="detass-creditos"><span>4</span></span>
                <span class="detass-tipologia"><span>DISCIPLINAR OBLIGATORIA</span></span>
                <div>
                    <h2 class="af_showDetailHeader_title-text0">GRUPO 03</h2>
                    <div class="af_showDetailHeader_content0">
                        <div class="af_panelGroupLayout">
                            <div><span>Profesor Tres</span></div>
                            <div>Facultad Sin Span</div>
                            <div>
                                <span class="lista-elemento">Lunes de 08:00 a 10:00<span class="lista-elemento">A101</span></span>
                            </div>
                            <div><span>Semestral</span></div>
                            <div><span>Teórico</span></div>
                            <div><span>12</span></div>
                        </div>
                    </div>
                </div>
            </body>
        </html>
    "#;

    Python::with_gil(|py| {
        let result = parse_course_info(xml).unwrap();
        let dict = result.as_ref(py);
        let groups = dict.get_item("groups").unwrap();
        let groups_list: Vec<pyo3::Py<pyo3::types::PyAny>> = groups.extract().unwrap();
        assert_eq!(groups_list.len(), 1);

        let group = groups_list[0].as_ref(py);
        assert_eq!(
            group
                .get_item("faculty")
                .unwrap()
                .extract::<String>()
                .unwrap(),
            "Facultad Sin Span"
        );
    });
}

#[test]
fn test_parse_course_xml_group_without_panel_is_skipped() {
    let xml = r#"
        <html>
            <body>
                <h2>CALCULO AVANZADO</h2>
                <span class="detass-creditos"><span>4</span></span>
                <span class="detass-tipologia"><span>DISCIPLINAR OBLIGATORIA</span></span>
                <div class="af_showDetailHeader_content0"></div>
            </body>
        </html>
    "#;

    Python::with_gil(|_py| {
        let result = parse_course_info(xml);
        assert!(result.is_err());
    });
}

#[test]
fn test_parse_course_xml_group_with_empty_panel_data_is_skipped() {
    let xml = r#"
        <html>
            <body>
                <h2>CALCULO AVANZADO</h2>
                <span class="detass-creditos"><span>4</span></span>
                <span class="detass-tipologia"><span>DISCIPLINAR OBLIGATORIA</span></span>
                <div class="af_showDetailHeader_content0">
                    <div class="af_panelGroupLayout"></div>
                </div>
            </body>
        </html>
    "#;

    Python::with_gil(|_py| {
        let result = parse_course_info(xml);
        assert!(result.is_err());
    });
}

#[test]
fn test_parse_course_xml_schedule_non_matching_pattern_is_ignored() {
    let xml = r#"
        <html>
            <body>
                <h2>CALCULO AVANZADO</h2>
                <span class="detass-creditos"><span>4</span></span>
                <span class="detass-tipologia"><span>DISCIPLINAR OBLIGATORIA</span></span>
                <div>
                    <h2 class="af_showDetailHeader_title-text0">GRUPO 02</h2>
                    <div class="af_showDetailHeader_content0">
                        <div class="af_panelGroupLayout">
                            <div><span>Profesor Dos</span></div>
                            <div><span></span></div>
                            <div>
                                <span class="lista-elemento">horario invalido<span class="lista-elemento">A101</span></span>
                            </div>
                            <div><span></span></div>
                            <div><span></span></div>
                            <div></div>
                        </div>
                    </div>
                </div>
            </body>
        </html>
    "#;

    Python::with_gil(|py| {
        let result = parse_course_info(xml).unwrap();
        let dict = result.as_ref(py);
        let groups = dict.get_item("groups").unwrap();
        let groups_list: Vec<pyo3::Py<pyo3::types::PyAny>> = groups.extract().unwrap();
        assert_eq!(groups_list.len(), 1);

        let group = groups_list[0].as_ref(py);
        let schedules = group.get_item("schedules").unwrap();
        let schedule_list: Vec<pyo3::Py<pyo3::types::PyAny>> = schedules.extract().unwrap();
        assert!(schedule_list.is_empty());
        assert_eq!(
            group
                .get_item("faculty")
                .unwrap()
                .extract::<String>()
                .unwrap(),
            "Unknown"
        );
        assert_eq!(
            group.get_item("spots").unwrap().extract::<i64>().unwrap(),
            0
        );
    });
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
fn test_parse_prereqs_xml_extracts_nested_header_values() {
    let xml = r#"
        <html>
            <body>
                <h2>ALGEBRA LINEAL BASICA</h2>
                <span class="detass-creditos"><span>4</span></span>
                <span class="detass-tipologia"><span>FUND. OPTATIVA</span></span>
                <span class="borde salto af_panelGroupLayout">
                    <div class="margin-t af_panelGroupLayout">
                        <div>
                            <span class="strong af_panelGroupLayout">
                                <span class="margin-l">Condición</span>
                                <span>1</span>
                                <span class="margin-l">Tipo</span>
                                <span>M</span>
                                <span class="margin-l">¿Todas?</span>
                                <span>[N]</span>
                                <span class="margin-l">Número asignaturas</span>
                                <span>[1]</span>
                            </span>
                        </div>
                        <div>
                            <span class="af_panelGroupLayout"><span>1000004-B</span><span>Cálculo diferencial</span></span>
                        </div>
                    </div>
                </span>
            </body>
        </html>
    "#;

    Python::with_gil(|py| {
        let result = parse_prereqs(xml).unwrap();
        let dict = result.as_ref(py);
        let conditions = dict.get_item("conditions").unwrap();
        let conditions_list: Vec<pyo3::Py<pyo3::types::PyAny>> = conditions.extract().unwrap();
        assert_eq!(conditions_list.len(), 1);

        let cond = conditions_list[0].as_ref(py);
        assert_eq!(
            cond.get_item("condition")
                .unwrap()
                .extract::<String>()
                .unwrap(),
            "1"
        );
        assert_eq!(
            cond.get_item("type").unwrap().extract::<String>().unwrap(),
            "M"
        );
        assert_eq!(
            cond.get_item("all_required")
                .unwrap()
                .extract::<String>()
                .unwrap(),
            "[N]"
        );
        assert_eq!(
            cond.get_item("number_of_courses")
                .unwrap()
                .extract::<String>()
                .unwrap(),
            "[1]"
        );
    });
}

#[test]
fn test_parse_prereqs_xml_extracts_sibling_header_values() {
    let xml = r#"
        <html>
            <body>
                <h2>CALCULO AVANZADO</h2>
                <span class="detass-creditos"><span>4</span></span>
                <span class="detass-tipologia"><span>DISCIPLINAR OBLIGATORIA</span></span>
                <span class="borde salto af_panelGroupLayout">
                    <div class="margin-t af_panelGroupLayout">
                        <div>
                            <span class="strong af_panelGroupLayout"><span class="margin-l">Condición</span></span>
                            <span>2</span>
                            <span class="strong af_panelGroupLayout"><span class="margin-l">Tipo</span></span>
                            <span>O</span>
                            <span class="strong af_panelGroupLayout"><span class="margin-l">¿Todas?</span></span>
                            <span>S</span>
                            <span class="strong af_panelGroupLayout"><span class="margin-l">Número asignaturas</span></span>
                            <span>3</span>
                        </div>
                        <div>
                            <span class="af_panelGroupLayout"><span>MATE1001</span><span>Calculo I</span></span>
                        </div>
                    </div>
                </span>
            </body>
        </html>
    "#;

    Python::with_gil(|py| {
        let result = parse_prereqs(xml).unwrap();
        let dict = result.as_ref(py);
        let conditions = dict.get_item("conditions").unwrap();
        let conditions_list: Vec<pyo3::Py<pyo3::types::PyAny>> = conditions.extract().unwrap();
        assert_eq!(conditions_list.len(), 1);

        let cond = conditions_list[0].as_ref(py);
        assert_eq!(
            cond.get_item("condition")
                .unwrap()
                .extract::<String>()
                .unwrap(),
            "2"
        );
        assert_eq!(
            cond.get_item("type").unwrap().extract::<String>().unwrap(),
            "O"
        );
        assert_eq!(
            cond.get_item("all_required")
                .unwrap()
                .extract::<String>()
                .unwrap(),
            "S"
        );
        assert_eq!(
            cond.get_item("number_of_courses")
                .unwrap()
                .extract::<String>()
                .unwrap(),
            "3"
        );
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
fn test_parse_prereqs_xml_typology_defaults_to_unknown() {
    let xml = r#"
        <html>
            <body>
                <h2>INTRODUCCION A LA PROGRAMACION</h2>
                <span class="detass-creditos"><span>3</span></span>
            </body>
        </html>
    "#;

    Python::with_gil(|py| {
        let result = parse_prereqs(xml);
        assert!(result.is_ok());

        let py_result = result.unwrap();
        let dict = py_result.as_ref(py);
        let typology = dict.get_item("typology").unwrap();
        assert_eq!(typology.extract::<String>().unwrap(), "Unknown");
    });
}

#[test]
fn test_parse_prereqs_xml_skips_condition_with_too_few_subdivs() {
    let xml = r#"
        <html>
            <body>
                <h2>CALCULO AVANZADO</h2>
                <span class="detass-creditos"><span>4</span></span>
                <span class="detass-tipologia"><span>DISCIPLINAR OBLIGATORIA</span></span>
                <span class="borde salto af_panelGroupLayout">
                    <div class="margin-t af_panelGroupLayout">
                        <div>
                            <span class="strong af_panelGroupLayout"><span class="margin-l">Condición</span></span>
                            <span>Haber aprobado</span>
                        </div>
                    </div>
                </span>
            </body>
        </html>
    "#;

    Python::with_gil(|py| {
        let result = parse_prereqs(xml).unwrap();
        let dict = result.as_ref(py);
        let conditions = dict.get_item("conditions").unwrap();
        let conditions_list: Vec<pyo3::Py<pyo3::types::PyAny>> = conditions.extract().unwrap();
        assert!(conditions_list.is_empty());
    });
}

#[test]
fn test_parse_prereqs_xml_skips_condition_with_too_few_headers() {
    let xml = r#"
        <html>
            <body>
                <h2>CALCULO AVANZADO</h2>
                <span class="detass-creditos"><span>4</span></span>
                <span class="detass-tipologia"><span>DISCIPLINAR OBLIGATORIA</span></span>
                <span class="borde salto af_panelGroupLayout">
                    <div class="margin-t af_panelGroupLayout">
                        <div>
                            <span class="strong af_panelGroupLayout"><span class="margin-l">Condición</span></span>
                            <span>Haber aprobado</span>
                            <span class="strong af_panelGroupLayout"><span class="margin-l">Tipo</span></span>
                            <span>Materia</span>
                        </div>
                        <div>
                            <span class="af_panelGroupLayout"><span>MATE1001</span><span>Calculo I</span></span>
                        </div>
                    </div>
                </span>
            </body>
        </html>
    "#;

    Python::with_gil(|py| {
        let result = parse_prereqs(xml).unwrap();
        let dict = result.as_ref(py);
        let conditions = dict.get_item("conditions").unwrap();
        let conditions_list: Vec<pyo3::Py<pyo3::types::PyAny>> = conditions.extract().unwrap();
        assert!(conditions_list.is_empty());
    });
}

#[test]
fn test_parse_prereqs_xml_fills_missing_header_values_with_empty_string() {
    let xml = r#"
        <html>
            <body>
                <h2>CALCULO AVANZADO</h2>
                <span class="detass-creditos"><span>4</span></span>
                <span class="detass-tipologia"><span>DISCIPLINAR OBLIGATORIA</span></span>
                <span class="borde salto af_panelGroupLayout">
                    <div class="margin-t af_panelGroupLayout">
                        <div>
                            <span class="strong af_panelGroupLayout"><span class="margin-l">Condición</span></span>
                            <span>Haber aprobado</span>
                            <span class="strong af_panelGroupLayout"><span class="margin-l">Tipo</span></span>
                            <span>Materia</span>
                            <span class="strong af_panelGroupLayout"><span class="margin-l">¿Todas?</span></span>
                            <span>SI</span>
                            <span class="strong af_panelGroupLayout"><span class="margin-l">Número asignaturas</span></span>
                        </div>
                        <div>
                            <span class="af_panelGroupLayout"><span>MATE1001</span><span>Calculo I</span></span>
                        </div>
                    </div>
                </span>
            </body>
        </html>
    "#;

    Python::with_gil(|py| {
        let result = parse_prereqs(xml).unwrap();
        let dict = result.as_ref(py);
        let conditions = dict.get_item("conditions").unwrap();
        let conditions_list: Vec<pyo3::Py<pyo3::types::PyAny>> = conditions.extract().unwrap();
        assert_eq!(conditions_list.len(), 1);

        let cond = conditions_list[0].as_ref(py);
        let number_of_courses = cond.get_item("number_of_courses").unwrap();
        assert_eq!(number_of_courses.extract::<String>().unwrap(), "");
    });
}

#[test]
fn test_parse_prereqs_xml_skips_prereq_row_with_few_spans() {
    let xml = r#"
        <html>
            <body>
                <h2>CALCULO AVANZADO</h2>
                <span class="detass-creditos"><span>4</span></span>
                <span class="detass-tipologia"><span>DISCIPLINAR OBLIGATORIA</span></span>
                <span class="borde salto af_panelGroupLayout">
                    <div class="margin-t af_panelGroupLayout">
                        <div>
                            <span class="strong af_panelGroupLayout"><span class="margin-l">Condición</span></span>
                            <span>Haber aprobado</span>
                            <span class="strong af_panelGroupLayout"><span class="margin-l">Tipo</span></span>
                            <span>Materia</span>
                            <span class="strong af_panelGroupLayout"><span class="margin-l">¿Todas?</span></span>
                            <span>SI</span>
                            <span class="strong af_panelGroupLayout"><span class="margin-l">Número asignaturas</span></span>
                            <span>1</span>
                        </div>
                        <div>
                            <span class="af_panelGroupLayout"><span>MATE1001</span></span>
                        </div>
                    </div>
                </span>
            </body>
        </html>
    "#;

    Python::with_gil(|py| {
        let result = parse_prereqs(xml).unwrap();
        let dict = result.as_ref(py);
        let conditions = dict.get_item("conditions").unwrap();
        let conditions_list: Vec<pyo3::Py<pyo3::types::PyAny>> = conditions.extract().unwrap();
        assert_eq!(conditions_list.len(), 1);

        let cond = conditions_list[0].as_ref(py);
        let prereqs = cond.get_item("prerequisites").unwrap();
        let prereq_list: Vec<pyo3::Py<pyo3::types::PyAny>> = prereqs.extract().unwrap();
        assert!(prereq_list.is_empty());
    });
}

#[test]
fn test_parse_prereqs_xml_missing_credits_errors() {
    let xml = r#"
        <html>
            <body>
                <h2>CALCULO AVANZADO</h2>
            </body>
        </html>
    "#;

    let result = Python::with_gil(|py| parse_prereqs_xml(xml, py));
    assert!(result.is_err());
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
