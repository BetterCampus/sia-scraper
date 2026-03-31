"""Additional edge-case tests for course parser coverage."""

import pytest

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
        result = _extract_group(group, "CURSO X")
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
