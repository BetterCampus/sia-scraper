# SIA Test Fixtures

This directory contains sanitized fixture responses captured from live SIA.

## Capture Metadata
- Captured at: 2026-03-30T00:52:36
- SIA URL: https://sia.unal.edu.co/Catalogo/facespublico/public/servicioPublico.jsf
- Career code: 0-2-8-3
- Regular courses requested: 5
- Electives requested: 2
- Sanitization enabled: True
- Keep only latest: True

## Generated Files
- `tests/fixtures/baselines/parser_baseline_2026-03-30.json`
- `tests/fixtures/html/career_page_electives_2026-03-30.html`
- `tests/fixtures/html/career_page_regular_2026-03-30.html`
- `tests/fixtures/html/initial_page_2026-03-30.html`
- `tests/fixtures/html/session_timeout_2026-03-30.html`
- `tests/fixtures/json/course_list_electives_2026-03-30.json`
- `tests/fixtures/json/course_list_regular_2026-03-30.json`
- `tests/fixtures/json/session_data_2026-03-30.json`
- `tests/fixtures/xml/adf_dropdown_response_2026-03-30.xml`
- `tests/fixtures/xml/adf_error_response_2026-03-30.xml`
- `tests/fixtures/xml/course_detail_0_2026-03-30.xml`
- `tests/fixtures/xml/course_detail_1_2026-03-30.xml`
- `tests/fixtures/xml/course_detail_2_2026-03-30.xml`
- `tests/fixtures/xml/course_detail_3_2026-03-30.xml`
- `tests/fixtures/xml/course_detail_4_2026-03-30.xml`
- `tests/fixtures/xml/course_elective_0_2026-03-30.xml`
- `tests/fixtures/xml/course_elective_1_2026-03-30.xml`
- `tests/fixtures/xml/course_prereqs_2026-03-30.xml`

## Notes
- Tokens and cookies are sanitized when enabled in config.
- Date suffix format is `YYYY-MM-DD`.
- Re-run the capture script to refresh fixtures after SIA changes.
