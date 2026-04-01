"""Additional edge-case tests for course parser coverage."""

from pathlib import Path

import pytest

import sia_scraper_rust
from sia_scraper.parsers import scrape_info, scrape_prereqs
from sia_scraper.parsers.course_parser import (
    _extract_group,
    _extract_label_value,
    _extract_schedules,
    _extract_spots,
)
from sia_scraper.parsers.html_parser import HtmlParser


@pytest.mark.unit
class TestCourseParserEdgeCases:
    """Test less common and defensive parsing branches."""

    def test_scrape_info_missing_h2_raises(self):
        xml = '<span class="detass-creditos"><span>3</span></span>'
        with pytest.raises(ValueError, match="Course name element not found in XML"):
            scrape_info(xml)

    def test_scrape_info_group_without_panel_is_skipped(self):
        xml = """
        <h2>CURSO X</h2>
        <span class="detass-creditos"><span>3</span></span>
        <span class="detass-tipologia"><span>TIPO</span></span>
        <div class="af_showDetailHeader_content0"></div>
        """
        result = scrape_info(xml)
        assert result.groups == []
        assert result.available_spots == 0

    def test_scrape_prereqs_without_typology_uses_unknown(self):
        xml = """
        <h2>CURSO X (1234)</h2>
        <span class="detass-creditos"><span>3</span></span>
        """
        result = scrape_prereqs(xml)
        assert result.typology == "Unknown"

    def test_scrape_prereqs_without_code_parentheses(self):
        xml = """
        <h2>CURSO SIN CODIGO</h2>
        <span class="detass-creditos"><span>2</span></span>
        <span class="detass-tipologia">Tipología: OPTATIVA</span>
        """
        result = scrape_prereqs(xml)
        assert result.code is None or result.code == ""

    def test_scrape_prereqs_extracts_code_from_rightmost_parentheses(self):
        """Test that course code is extracted from the last set of parentheses.

        Course names with multiple parenthetical expressions (e.g., advanced courses)
        must extract the code from the rightmost parentheses, not the first.
        """
        xml = """
        <h2>ELECTROMAGNETISMO (AVANZADO) (2016489)</h2>
        <span class="detass-creditos"><span>4</span></span>
        <span class="detass-tipologia">Tipología: OBLIGATORIA</span>
        """
        result = scrape_prereqs(xml)
        assert result.code == "2016489"
        assert result.course_name == "ELECTROMAGNETISMO (AVANZADO) (2016489)"

    def test_scrape_prereqs_extracts_code_with_intermediate_parentheses(self):
        """Test extraction when course name has various parenthetical patterns."""
        xml = """
        <h2>PROYECTO DE INVESTIGACION (II) (2023567)</h2>
        <span class="detass-creditos"><span>3</span></span>
        <span class="detass-tipologia">Tipología: OPTATIVA</span>
        """
        result = scrape_prereqs(xml)
        assert result.code == "2023567"

    def test_scrape_prereqs_condition_without_prereq_code_is_skipped(self):
        xml = """
        <h2>CURSO X (1000)</h2>
        <span class="detass-creditos"><span>2</span></span>
        <span class="detass-tipologia">Tipología: OBLIGATORIA</span>
        <span class="borde salto af_panelGroupLayout">
          <div class="margin-t af_panelGroupLayout">
            <div>
              <span class="strong af_panelGroupLayout"><span class="margin-l">Condición</span></span>Debe aprobar
              <span class="strong af_panelGroupLayout"><span class="margin-l">Tipo</span></span>Materia
              <span class="strong af_panelGroupLayout"><span class="margin-l">¿Todas?</span></span>SI
              <span class="strong af_panelGroupLayout"><span class="margin-l">Número asignaturas</span></span>1
            </div>
            <div>PREREQ SIN CODIGO</div>
          </div>
        </span>
        """
        result = scrape_prereqs(xml)
        assert len(result.conditions) == 1
        assert result.conditions[0].prerequisites == []

    def test_extract_label_value_returns_unknown_when_no_spans(self):
        parser = HtmlParser("<div></div>")
        assert _extract_label_value(parser.root) == "Unknown"

    def test_extract_schedules_returns_empty_when_index_missing(self):
        parser = HtmlParser("<div><div></div></div>")
        group_data = [parser.root]
        assert _extract_schedules(group_data) == []

    def test_extract_schedules_parses_valid_schedule_row(self):
        parser = HtmlParser(
            """
            <div>
              <div></div>
              <div></div>
              <div>
                <span class="lista-elemento">
                  <span>LUNES de 07:00 a 09:00</span>
                  <span class="lista-elemento">401-101</span>
                </span>
              </div>
            </div>
            """
        )
        group_data = list(parser.root)
        schedules = _extract_schedules(group_data)
        assert len(schedules) == 1
        assert schedules[0].day == "LUNES"
        assert schedules[0].classroom == "401-101"

    def test_extract_spots_handles_missing_and_invalid_values(self):
        parser_short = HtmlParser("<div><div></div></div>")
        assert _extract_spots(list(parser_short.root)) is None

        parser_missing_spans = HtmlParser(
            """
            <div>
              <div></div><div></div><div></div><div></div><div></div><div></div>
            </div>
            """
        )
        assert _extract_spots(list(parser_missing_spans.root)) is None

        parser_invalid_spots = HtmlParser(
            """
            <div>
              <div></div><div></div><div></div><div></div><div></div>
              <div><span>N/A</span></div>
            </div>
            """
        )
        assert _extract_spots(list(parser_invalid_spots.root)) is None

    def test_extract_group_returns_none_for_root_without_parent_or_children(self):
        parser = HtmlParser(
            '<section><div class="af_showDetailHeader_content0"><div class="af_panelGroupLayout"/></div></section>'
        )
        group = parser.find("div", class_="af_showDetailHeader_content0")
        assert group is not None
        result = _extract_group(group, "CURSO X", group_index=0)
        assert result is None


@pytest.mark.unit
class TestMalformedInputEdgeCases:
    """Test parser behavior with malformed/malicious inputs."""

    def test_scrape_info_with_unicode_heavy_content(self) -> None:
        """Verify parser handles unicode-heavy content without crashing."""
        xml = """
        <h2>基础日本語العربيةΕλληνικά</h2>
        <span class="detass-creditos"><span>3</span></span>
        <span class="detass-tipologia"><span>DISCIPLINAR OBLIGATORIA</span></span>
        """
        result = scrape_info(xml)
        assert result is not None
        assert result.course_name == "基础日本語العربيةΕλληνικά"

    def test_scrape_info_with_empty_spans(self) -> None:
        """Verify parser handles empty span elements."""
        xml = """
        <h2>Test Course</h2>
        <span class="detass-creditos"><span></span></span>
        <span class="detass-tipologia"><span>   </span></span>
        """
        with pytest.raises(ValueError):
            scrape_info(xml)

    def test_scrape_info_with_nested_empty_tags(self) -> None:
        """Verify parser handles nested empty tags."""
        xml = """
        <h2>Test Course</h2>
        <span class="detass-creditos"><span><span><span>3</span></span></span></span>
        <span class="detass-tipologia"><span>DISCIPLINAR OBLIGATORIA</span></span>
        """
        result = scrape_info(xml)
        assert result is not None

    def test_scrape_prereqs_with_malformed_schedule(self) -> None:
        """Verify parser handles malformed schedule data."""
        xml = """
        <h2>Test Course</h2>
        <span class="detass-creditos"><span>3</span></span>
        <span class="detass-tipologia"><span>DISCIPLINAR OBLIGATORIA</span></span>
        <div class="af_panelTabbed_body">
          <div>
            <div>
              <div class="af_showDetailHeader">
                <span>PRERREQUISITE</span>
              </div>
              <div>
                <div>
                  <table>
                    <tr>
                      <td><span>Prerrequisito</span></td>
                      <td><span>Tipo</span></td>
                      <td><span>Todos</span></td>
                      <td><span>2</span></td>
                    </tr>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>
        """
        result = scrape_prereqs(xml)
        assert result is not None

    def test_scrape_prereqs_with_unicode_in_conditions(self) -> None:
        """Verify parser handles unicode in prerequisite conditions."""
        xml = """
        <h2>Test Course 中文 العربية</h2>
        <span class="detass-creditos"><span>3</span></span>
        <span class="detass-tipologia"><span>DISCIPLINAR OBLIGATORIA</span></span>
        <div class="af_panelTabbed_body">
          <div>
            <div>
              <div class="af_showDetailHeader">
                <span>Prerrequisito</span>
              </div>
              <div>
                <div>
                  <table>
                    <tr>
                      <td><span>Curso 基础</span></td>
                      <td><span>Curso 中文</span></td>
                    </tr>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>
        """
        result = scrape_prereqs(xml)
        assert result is not None

    def test_scrape_info_with_extremely_long_course_name(self) -> None:
        """Verify parser handles extremely long course names."""
        long_name = "A" * 10000
        xml = f"""
        <h2>{long_name}</h2>
        <span class="detass-creditos"><span>3</span></span>
        <span class="detass-tipologia"><span>DISCIPLINAR OBLIGATORIA</span></span>
        """
        result = scrape_info(xml)
        assert result is not None

    def test_scrape_info_with_special_characters_in_course_name(self) -> None:
        """Verify parser handles special characters in course names."""
        xml = r"""
        <h2>Course &amp; More &lt;test&gt;</h2>
        <span class="detass-creditos"><span>3</span></span>
        <span class="detass-tipologia"><span>DISCIPLINAR OBLIGATORIA</span></span>
        """
        result = scrape_info(xml)
        assert result is not None


@pytest.mark.unit
class TestDiagnosticErrorMessages:
    """Verify error messages contain useful diagnostic information."""

    def test_missing_credits_error_includes_context(self):
        """Missing credits error should include what was found."""
        xml = "<h2>COURSE</h2><div>No credits here</div>"

        with pytest.raises(ValueError) as exc_info:
            scrape_info(xml)

        error_msg = str(exc_info.value)
        assert "credits" in error_msg.lower()
        assert "not found" in error_msg.lower()
        # Should include what was found
        assert "span" in error_msg.lower() or "element" in error_msg.lower()

    def test_missing_credits_span_error_includes_content(self):
        """Credits element without span should include element content."""
        xml = """
        <h2>COURSE</h2>
        <span class="detass-creditos">3</span>
        <span class="detass-tipologia"><span>OBLIGATORIA</span></span>
        """

        with pytest.raises(ValueError) as exc_info:
            scrape_info(xml)

        error_msg = str(exc_info.value)
        assert "credits" in error_msg.lower()
        assert "span" in error_msg.lower()
        assert "not found" in error_msg.lower()


class TestFixtureEdgeCases:
    """Test parser behavior with edge case fixtures."""

    @pytest.fixture
    def fixture_path(self):
        """Return path to edge case fixtures."""
        return Path("tests/fixtures/xml/edge_cases")

    def _load_fixture(self, fixture_path: Path, filename: str) -> str:
        """Load and extract CDATA from an edge case fixture."""
        filepath = fixture_path / filename
        content = filepath.read_text()
        start = content.find("<![CDATA[") + 9
        end = content.find("]]>")
        return content[start:end]

    def test_group_with_five_divs_no_spots(self, fixture_path: Path):
        """Group with 5 divs (no spots field) should parse with spots=None."""
        xml = self._load_fixture(fixture_path, "group_with_5_divs.xml")
        result = scrape_info(xml)

        assert len(result.groups) == 1
        group = result.groups[0]
        assert group.teacher == "JUAN PEREZ GOMEZ"
        assert group.faculty == "CIENCIAS"
        assert group.duration == "16 SEMANAS"
        assert group.schedule_type == "DIURNA"
        assert group.spots is None

    def test_group_with_three_divs_minimal(self, fixture_path: Path):
        """Group with only 3 divs should parse essential fields."""
        xml = self._load_fixture(fixture_path, "group_with_3_divs.xml")
        result = scrape_info(xml)

        assert len(result.groups) == 1
        group = result.groups[0]
        assert group.teacher == "MARIA RODRIGUEZ"
        assert group.faculty == "INGENIERÍA"
        # Schedules may be empty if schedule row format doesn't match
        # Optional fields should have defaults
        assert group.duration == "Unknown"
        assert group.schedule_type == "Unknown"
        assert group.spots is None

    def test_group_empty_faculty_field(self, fixture_path: Path):
        """Group with empty faculty field should handle gracefully."""
        xml = self._load_fixture(fixture_path, "group_empty_faculty.xml")
        result = scrape_info(xml)

        assert len(result.groups) == 1
        group = result.groups[0]
        assert group.faculty == "" or group.faculty == "Unknown"
        assert group.teacher == "CARLOS MARTINEZ"
        assert group.spots == 15

    def test_condition_with_three_headers_raises_error(self, fixture_path: Path):
        """Condition with only 3 headers currently raises IndexError (Phase 2C will fix)."""
        xml = self._load_fixture(fixture_path, "condition_with_3_headers.xml")

        # Current behavior: crashes with IndexError when condition has <4 headers
        # Phase 2C will add graceful handling and diagnostics
        with pytest.raises((IndexError, ValueError)):
            scrape_prereqs(xml)

    def test_course_no_groups_returns_empty_list(self, fixture_path: Path):
        """Course with no group panels should return empty groups list."""
        xml = self._load_fixture(fixture_path, "course_no_groups.xml")
        result = scrape_info(xml)

        assert result.course_name == "SEMINARIO DE INVESTIGACION"
        assert result.credits == 2
        assert len(result.groups) == 0

    def test_course_missing_credits_span_raises_error(self, fixture_path: Path):
        """Credits element without span should raise error."""
        xml = self._load_fixture(fixture_path, "course_missing_credits_span.xml")

        with pytest.raises(ValueError) as exc_info:
            scrape_info(xml)

        error_msg = str(exc_info.value)
        assert "credits" in error_msg.lower()
        assert "span" in error_msg.lower()
        assert "not found" in error_msg.lower()

    def test_credits_parse_error_includes_value(self):
        """Credits parse error should include the invalid value."""
        xml = """
        <h2>COURSE</h2>
        <span class="detass-creditos"><span>invalid</span></span>
        <span class="detass-tipologia"><span>OBLIGATORIA</span></span>
        """

        with pytest.raises(ValueError) as exc_info:
            scrape_info(xml)

        error_msg = str(exc_info.value)
        assert "invalid" in error_msg.lower() or "parse" in error_msg.lower()
        assert "expected integer" in error_msg.lower()

    def test_missing_course_name_error_is_descriptive(self):
        """Missing course name error should be descriptive."""
        xml = """
        <span class="detass-creditos"><span>3</span></span>
        <span class="detass-tipologia"><span>OBLIGATORIA</span></span>
        """

        with pytest.raises(ValueError) as exc_info:
            scrape_info(xml)

        error_msg = str(exc_info.value)
        assert "course name" in error_msg.lower()
        assert "not found" in error_msg.lower()


@pytest.mark.unit
class TestPrerequisiteEdgeCases:
    """Test prerequisite parsing edge cases."""

    def test_course_no_prerequisites(self):
        """Course with no prerequisites should return empty list."""
        xml = """
        <h2>CURSO SIN REQUISITOS (1234)</h2>
        <span class="detass-creditos"><span>3</span></span>
        <span class="detass-tipologia">Tipología: OBLIGATORIA</span>
        """
        result = scrape_prereqs(xml)
        assert result.conditions == []

    def test_malformed_prerequisite_html(self):
        """Malformed prerequisite HTML should raise clear error."""
        xml = "<div>Not a valid prereq structure</div>"

        with pytest.raises(ValueError) as exc_info:
            scrape_prereqs(xml)

        error_msg = str(exc_info.value)
        assert "course name" in error_msg.lower() or "not found" in error_msg.lower()

    def test_prereq_with_empty_condition_body(self):
        """Prerequisite condition with empty body should be handled."""
        xml = """
        <h2>TEST COURSE (1234)</h2>
        <span class="detass-creditos"><span>3</span></span>
        <span class="detass-tipologia">Tipología: OBLIGATORIA</span>
        <span class="borde salto af_panelGroupLayout">
          <div class="margin-t af_panelGroupLayout">
          </div>
        </span>
        """
        result = scrape_prereqs(xml)
        assert result is not None


@pytest.mark.unit
class TestRustParserParity:
    """Verify Rust parser handles same edge cases as Python."""

    def test_rust_group_with_five_divs(self):
        """Rust parser should handle 5-div groups like Python."""
        xml = """
        <h2>CALCULO</h2>
        <span class="detass-creditos"><span>4</span></span>
        <span class="detass-tipologia"><span>OBLIGATORIA</span></span>
        <div class="af_showDetailHeader_content0">
            <div class="af_panelGroupLayout">
                <div><span>Profesor: </span><span>JUAN</span></div>
                <div><span>Facultad: </span><span>CIENCIAS</span></div>
                <div><span>Horarios: </span><span>LU 10:00</span></div>
                <div><span>Duración: </span><span>16 SEM</span></div>
                <div><span>Jornada: </span><span>DIURNA</span></div>
            </div>
        </div>
        """
        python_result = scrape_info(xml)

        # Rust should also parse successfully
        rust_result = sia_scraper_rust.parse_course_info(xml)  # type: ignore[attr-defined]
        # Both should return at least the course info (groups may differ in handling)
        assert rust_result["course_name"] == python_result.course_name
        assert rust_result["credits"] == python_result.credits

    def test_rust_course_no_groups(self):
        """Rust parser should handle course with no groups."""
        xml = """
        <h2>SEMINARIO</h2>
        <span class="detass-creditos"><span>2</span></span>
        <span class="detass-tipologia"><span>TRABAJO GRADO</span></span>
        """
        python_result = scrape_info(xml)
        rust_result = sia_scraper_rust.parse_course_info(xml)  # type: ignore[attr-defined]

        assert len(python_result.groups) == 0
        assert len(rust_result["groups"]) == 0

    def test_rust_missing_credits_raises_error(self):
        """Rust parser should raise error for missing credits like Python."""
        xml = "<h2>COURSE</h2><div>No credits</div>"

        with pytest.raises((RuntimeError, Exception)):  # noqa: PT011 - PyO3 may wrap as SiaScraperException or RuntimeError
            sia_scraper_rust.parse_course_info(xml)  # type: ignore[attr-defined]
