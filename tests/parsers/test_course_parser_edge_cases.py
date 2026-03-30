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
        assert result.code == ""

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
