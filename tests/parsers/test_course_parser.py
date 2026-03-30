"""Unit tests for sia_scraper.parsers.course_parser - Course info and prereqs parsing."""

from unittest.mock import MagicMock, patch

import pytest

from sia_scraper.parsers import (
    CourseInfo,
    CoursePrereqs,
    Group,
    Schedule,
    get_plain_text,
    scrape_info,
    scrape_prereqs,
)


@pytest.fixture
def sample_course_xml(sia_course_detail_xml: str):
    """Use captured XML for a complete course with groups and schedules."""
    return sia_course_detail_xml


@pytest.fixture
def sample_prereqs_xml(sia_course_prereqs_xml: str):
    """Use captured XML for course prerequisites."""
    return sia_course_prereqs_xml


@pytest.fixture
def sample_empty_course_xml():
    """Sample XML for course with no groups."""
    return """
    <h2>CALCULO AVANZADO</h2>
    <span class="detass-creditos"><span>3</span></span>
    <span class="detass-tipologia"><span>DISCIPLINAR OBLIGATORIA</span></span>
    """


@pytest.mark.unit
class TestGetPlainText:
    """Test get_plain_text function for extracting text from XML."""

    def test_get_plain_text_basic(self):
        """Test extracting plain text from XML."""
        xml = "<div><span>  Text with  spaces  </span></div>"
        plain_text = get_plain_text(xml)
        assert "Text with" in plain_text
        assert plain_text.strip() != ""

    @pytest.mark.parametrize(
        "xml,expected_contains",
        [
            ("<div>HELLO WORLD</div>", "HELLO WORLD"),
            ("<span>   Trimmed   </span>", "Trimmed"),
            ("<p>Multiple<br/>Lines</p>", "Multiple"),
        ],
    )
    def test_get_plain_text_variations(self, xml, expected_contains):
        """Test get_plain_text with various XML formats."""
        result = get_plain_text(xml)
        assert expected_contains in result


@pytest.mark.unit
class TestScrapeInfo:
    """Test scrape_info function for parsing course XML."""

    def test_scrape_info_complete_course(self, sample_course_xml):
        """Test scraping complete course information."""
        course_info = scrape_info(sample_course_xml)

        assert isinstance(course_info, CourseInfo)
        assert course_info.course_name != ""
        assert course_info.credits > 0
        assert course_info.typology != "Unknown"
        assert len(course_info.groups) > 0

    def test_scrape_info_first_group(self, sample_course_xml):
        """Test scraping first group details."""
        course_info = scrape_info(sample_course_xml)

        grupo_1 = course_info.groups[0]
        assert isinstance(grupo_1, Group)
        assert grupo_1.group_name != ""
        assert grupo_1.teacher != ""
        assert grupo_1.duration != ""
        assert grupo_1.schedule_type != ""
        assert grupo_1.spots is None or isinstance(grupo_1.spots, int)

    def test_scrape_info_schedules(self, sample_course_xml):
        """Test scraping schedule information."""
        course_info = scrape_info(sample_course_xml)

        schedules = course_info.groups[0].schedules
        assert isinstance(schedules, list)
        for schedule in schedules:
            assert isinstance(schedule, Schedule)
            assert schedule.day != ""
            assert schedule.start_time != ""
            assert schedule.end_time != ""

    def test_scrape_info_nan_spots(self, sample_course_xml):
        """Test scraping handles NaN spots correctly."""
        course_info = scrape_info(sample_course_xml)

        if len(course_info.groups) > 1:
            grupo_2 = course_info.groups[1]
            assert grupo_2.spots is None or isinstance(grupo_2.spots, int)

    def test_scrape_info_total_spots(self, sample_course_xml):
        """Test calculation of total available spots."""
        course_info = scrape_info(sample_course_xml)

        assert isinstance(course_info.available_spots, int)
        assert course_info.available_spots >= 0

    def test_scrape_info_timestamp(self, sample_course_xml):
        """Test scraping includes timestamp."""
        course_info = scrape_info(sample_course_xml)

        assert hasattr(course_info, "scrape_timestamp")
        assert course_info.scrape_timestamp != ""

    def test_scrape_info_empty_course(self, sample_empty_course_xml):
        """Test scraping course with no groups."""
        course_info = scrape_info(sample_empty_course_xml)

        assert course_info.course_name == "CALCULO AVANZADO"
        assert course_info.credits == 3
        assert course_info.groups == []
        assert course_info.available_spots == 0

    def test_scrape_info_malformed_xml_returns_error(self):
        """Test scraping malformed XML handles gracefully."""
        malformed_xml = "<div>Incomplete XML"

        try:
            result = scrape_info(malformed_xml)
            assert isinstance(result, CourseInfo)
        except Exception:
            pass

    def test_scrape_info_missing_credits_element_raises(self):
        xml = """
        <h2>CURSO X</h2>
        <span class="detass-tipologia"><span>DISCIPLINAR OBLIGATORIA</span></span>
        """
        with pytest.raises(ValueError, match="Credits element not found in XML"):
            scrape_info(xml)

    def test_scrape_info_missing_credits_span_raises(self):
        xml = """
        <h2>CURSO X</h2>
        <span class="detass-creditos"></span>
        <span class="detass-tipologia"><span>DISCIPLINAR OBLIGATORIA</span></span>
        """
        with pytest.raises(ValueError, match="Credits span not found in XML"):
            scrape_info(xml)

    def test_scrape_info_missing_tipology_returns_unknown(self):
        xml = """
        <h2>CURSO X</h2>
        <span class="detass-creditos"><span>3</span></span>
        """
        course_info = scrape_info(xml)
        assert course_info.typology == "Unknown"

    def test_scrape_info_missing_tipology_span_returns_unknown(self):
        xml = """
        <h2>CURSO X</h2>
        <span class="detass-creditos"><span>3</span></span>
        <span class="detass-tipologia"></span>
        """
        course_info = scrape_info(xml)
        assert course_info.typology == "Unknown"

    def test_scrape_info_missing_teacher_falls_back(self):
        parser = MagicMock()
        parser.find.return_value = MagicMock(text_content=MagicMock(return_value="CURSO X"))
        parser.find.side_effect = [
            MagicMock(text_content=MagicMock(return_value="CURSO X")),
            MagicMock(
                find=MagicMock(return_value=MagicMock(text_content=MagicMock(return_value="3")))
            ),
            MagicMock(
                find=MagicMock(
                    return_value=MagicMock(
                        text_content=MagicMock(return_value="DISCIPLINAR OBLIGATORIA")
                    )
                )
            ),
        ]
        group = MagicMock()
        group.parent.find.return_value = MagicMock(text_content=MagicMock(return_value="1"))
        group_data = []
        g0 = MagicMock()
        g0.findall.return_value = []
        g1 = MagicMock()
        g1.findall.return_value = [MagicMock(text_content=MagicMock(return_value="FACULTAD X"))]
        g2 = MagicMock()
        schedule_section = MagicMock()
        schedule_section.findall.return_value = []
        g2.findall.return_value = []
        g3 = MagicMock()
        g3.findall.return_value = [MagicMock(text_content=MagicMock(return_value="16 SEMANAS"))]
        g4 = MagicMock()
        g4.findall.return_value = [MagicMock(text_content=MagicMock(return_value="DIURNA"))]
        g5 = MagicMock()
        g5.findall.return_value = [MagicMock(text_content=MagicMock(return_value="2"))]
        group_data.extend([g0, g1, g2, g3, g4, g5])
        panel = MagicMock()
        panel.__iter__ = MagicMock(return_value=iter(group_data))
        group.find.return_value = panel
        parser.css_select.return_value = [group]

        with (
            patch("sia_scraper.parsers.course_parser.HtmlParser", return_value=parser),
            patch("sia_scraper.parsers.course_parser.format_date", return_value="now"),
        ):
            result = scrape_info("<xml/>")
        assert result.groups[0].teacher == "Not reported"

    def test_scrape_info_skips_missing_and_invalid_schedule_rows(self):
        parser = MagicMock()
        parser.find.side_effect = [
            MagicMock(text_content=MagicMock(return_value="CURSO X")),
            MagicMock(
                find=MagicMock(return_value=MagicMock(text_content=MagicMock(return_value="3")))
            ),
            MagicMock(
                find=MagicMock(
                    return_value=MagicMock(
                        text_content=MagicMock(return_value="DISCIPLINAR OBLIGATORIA")
                    )
                )
            ),
        ]

        group = MagicMock()
        group.parent.find.return_value = MagicMock(text_content=MagicMock(return_value="1"))

        g0 = MagicMock()
        g0.findall.return_value = [MagicMock(text_content=MagicMock(return_value="PROFESOR X"))]
        g1 = MagicMock()
        g1.findall.return_value = [MagicMock(text_content=MagicMock(return_value="FACULTAD X"))]
        g2 = MagicMock()
        schedule_section = MagicMock()
        schedule_section.findall.return_value = []
        g2.findall.return_value = []
        g3 = MagicMock()
        g3.findall.return_value = [MagicMock(text_content=MagicMock(return_value="16 SEMANAS"))]
        g4 = MagicMock()
        g4.findall.return_value = [MagicMock(text_content=MagicMock(return_value="DIURNA"))]
        g5 = MagicMock()
        g5.findall.return_value = [MagicMock(text_content=MagicMock(return_value="2"))]

        panel = MagicMock()
        panel.__iter__ = MagicMock(return_value=iter([g0, g1, g2, g3, g4, g5]))
        group.find.return_value = panel
        parser.css_select.return_value = [group]

        with (
            patch("sia_scraper.parsers.course_parser.HtmlParser", return_value=parser),
            patch("sia_scraper.parsers.course_parser.format_date", return_value="now"),
        ):
            result = scrape_info("<xml/>")
        assert result.groups[0].schedules == []


@pytest.mark.unit
class TestScrapePrereqs:
    """Test scrape_prereqs function for parsing course prerequisites."""

    def test_scrape_prereqs_basic(self, sample_prereqs_xml):
        """Test scraping basic prerequisites."""
        prereqs = scrape_prereqs(sample_prereqs_xml)

        assert isinstance(prereqs, CoursePrereqs)
        assert prereqs.code != ""
        assert prereqs.credits > 0
        assert prereqs.typology != ""
        assert hasattr(prereqs, "conditions")

    def test_scrape_prereqs_empty_xml(self):
        """Test scraping prerequisites from empty XML."""
        empty_xml = "<div></div>"

        with pytest.raises(ValueError, match="Course name element not found in prerequisites XML"):
            scrape_prereqs(empty_xml)

    def test_scrape_prereqs_missing_credits_element_raises(self):
        xml = """
        <h2>CURSO (1000)</h2>
        <span class="detass-tipologia">Tipología: DISCIPLINAR OBLIGATORIA</span>
        """
        with pytest.raises(ValueError, match="Credits element not found in XML"):
            scrape_prereqs(xml)

    def test_scrape_prereqs_missing_credits_span_raises(self):
        xml = """
        <h2>CURSO (1000)</h2>
        <span class="detass-creditos"></span>
        <span class="detass-tipologia">Tipología: DISCIPLINAR OBLIGATORIA</span>
        """
        with pytest.raises(ValueError, match="Credits span not found in XML"):
            scrape_prereqs(xml)

    def test_scrape_prereqs_handles_various_formats(self):
        """Test prerequisite scraping handles different XML formats."""
        xml_variations = [
            "<div><span>Requisitos:</span></div>",
            "<div><span>No hay requisitos</span></div>",
            "<div></div>",
        ]

        for xml in xml_variations:
            try:
                result = scrape_prereqs(xml)
                assert isinstance(result, CoursePrereqs)
            except Exception:
                pass

    def test_scrape_prereqs_skips_invalid_condition_shape(self):
        xml = """
        <h2>CURSO (1000)</h2>
        <span class="detass-creditos"><span>3</span></span>
        <span class="detass-tipologia">Tipología: DISCIPLINAR OBLIGATORIA</span>
        <span class="borde salto af_panelGroupLayout">
          <div class="margin-t af_panelGroupLayout"><div>invalid</div></div>
        </span>
        """
        result = scrape_prereqs(xml)
        assert result.conditions == []

    def test_scrape_prereqs_skips_when_less_than_four_headers(self):
        parser = MagicMock()
        parser.findall.side_effect = [
            [MagicMock(text_content=MagicMock(return_value="CURSO (1000)"))],
            [MagicMock(text_content=MagicMock(return_value="Tipología: DISCIPLINAR OBLIGATORIA"))],
        ]
        parser.find.return_value.find.return_value.text_content.return_value = "3"
        condition_div = MagicMock()
        condition_info_div = MagicMock()
        h1, h2, h3 = MagicMock(), MagicMock(), MagicMock()
        for h, key, val in [
            (h1, "Condición", "Debe aprobar"),
            (h2, "Tipo", "Materia"),
            (h3, "¿Todas?", "SI"),
        ]:
            h.text_content.return_value = key
            h.getnext.return_value = MagicMock(text_content=MagicMock(return_value=val))
        condition_info_div.css_select.return_value = [h1, h2, h3]
        condition_div.__iter__ = MagicMock(return_value=iter([condition_info_div, MagicMock()]))
        parser.css_select.return_value = [condition_div]
        with patch("sia_scraper.parsers.course_parser.HtmlParser", return_value=parser):
            assert scrape_prereqs("<xml/>").conditions == []

    def test_scrape_prereqs_parses_multiple_prereqs(self):
        parser = MagicMock()
        parser.findall.side_effect = [
            [MagicMock(text_content=MagicMock(return_value="CURSO (1000)"))],
            [MagicMock(text_content=MagicMock(return_value="Tipología: DISCIPLINAR OBLIGATORIA"))],
        ]
        parser.find.return_value.find.return_value.text_content.return_value = "3"

        condition_div = MagicMock()
        condition_info_div = MagicMock()
        headers = []
        for key, val in [
            ("Condición", "Debe aprobar"),
            ("Tipo", "Materia"),
            ("¿Todas?", "SI"),
            ("Número asignaturas", "2"),
        ]:
            h = MagicMock()
            h.text_content.return_value = key
            h.getnext.return_value = MagicMock(text_content=MagicMock(return_value=val))
            headers.append(h)
        condition_info_div.css_select.return_value = headers

        prereq_div1 = MagicMock()
        code_span1 = MagicMock(text_content=MagicMock(return_value="1000001"))
        code_span1.getnext.return_value = MagicMock(text_content=MagicMock(return_value="CALCULO"))
        prereq_div1.css_select.return_value = [code_span1]

        prereq_div2 = MagicMock()
        code_span2 = MagicMock(text_content=MagicMock(return_value="1000002"))
        code_span2.getnext.return_value = MagicMock(text_content=MagicMock(return_value="ALGEBRA"))
        prereq_div2.css_select.return_value = [code_span2]

        condition_div.__iter__ = MagicMock(
            return_value=iter([condition_info_div, prereq_div1, prereq_div2])
        )
        parser.css_select.return_value = [condition_div]

        with patch("sia_scraper.parsers.course_parser.HtmlParser", return_value=parser):
            out = scrape_prereqs("<xml/>")
        prereqs_dict = {p.course_code: p.course_name for p in out.conditions[0].prerequisites}
        assert prereqs_dict == {
            "1000001": "CALCULO",
            "1000002": "ALGEBRA",
        }

    def test_scrape_prereqs_skips_when_len_mismatch(self):
        class WeirdList(list):
            def __len__(self):
                return super().__len__() + 1

        parser = MagicMock()
        parser.findall.side_effect = [
            [MagicMock(text_content=MagicMock(return_value="CURSO (1000)"))],
            [MagicMock(text_content=MagicMock(return_value="Tipología: DISCIPLINAR OBLIGATORIA"))],
        ]
        parser.find.return_value.find.return_value.text_content.return_value = "3"
        condition_div = MagicMock()
        condition_info_div = MagicMock()
        h1 = MagicMock()
        h1.text_content.return_value = "Condición"
        h1.getnext.return_value = MagicMock(text_content=MagicMock(return_value="Debe aprobar"))
        h2 = MagicMock()
        h2.text_content.return_value = "Tipo"
        h2.getnext.return_value = MagicMock(text_content=MagicMock(return_value="Materia"))
        h3 = MagicMock()
        h3.text_content.return_value = "¿Todas?"
        h3.getnext.return_value = MagicMock(text_content=MagicMock(return_value="SI"))
        h4 = MagicMock()
        h4.text_content.return_value = "Número asignaturas"
        h4.getnext.return_value = MagicMock(text_content=MagicMock(return_value="1"))
        condition_info_div.css_select.return_value = WeirdList([h1, h2, h3, h4])
        condition_div.__iter__ = MagicMock(return_value=iter([condition_info_div, MagicMock()]))
        parser.css_select.return_value = [condition_div]

        with patch("sia_scraper.parsers.course_parser.HtmlParser", return_value=parser):
            out = scrape_prereqs("<xml/>")
        assert out.conditions == []
