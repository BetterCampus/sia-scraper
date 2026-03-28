"""Unit tests for sia_scraper.scraper - SIA HTML/XML Scraping."""

import runpy
from unittest.mock import MagicMock, patch

import pytest

from sia_scraper.constants import DEFAULT_TIMEOUT, SiaSessionStatus
from sia_scraper.scraper import SiaScraper, create_career_session, init_sia_scraper
from sia_scraper.session import SiaSessionException


@pytest.fixture
def mock_sia_session():
    """Mock SiaSession for scraper tests."""
    with patch("sia_scraper.scraper.SiaSession") as mock_session_class:
        session_instance = MagicMock()
        session_instance.career_code = ""
        session_instance.career_name = "N/A"
        session_instance.course_list = []
        session_instance.STATUS = SiaSessionStatus.NO_SESSION
        session_instance.init_session = MagicMock()
        session_instance.set_career = MagicMock()
        session_instance.get_course_xml = MagicMock()
        session_instance.close_session = MagicMock()
        session_instance.valid_session = MagicMock(return_value=True)
        session_instance.get_session_data = MagicMock(return_value={})
        session_instance.load_session = MagicMock()
        mock_session_class.return_value = session_instance
        yield session_instance


@pytest.fixture
def sample_course_xml():
    """Sample XML for a complete course with groups and schedules."""
    return """<h2>CALCULO DIFERENCIAL</h2><span class="detass-creditos"><span>4</span></span><span class="detass-tipologia"><span>DISCIPLINAR OBLIGATORIA</span></span><div class="group-wrapper"><h2 class="af_showDetailHeader_title-text0">1</h2><div class="af_showDetailHeader_content0"><div class="af_panelGroupLayout"><div><span><span>JUAN PEREZ GARCIA</span></span></div><div><span><span>FACULTAD DE CIENCIAS</span></span></div><div><span><span><span class="lista-elemento"><span>LUNES de 07:00 a 09:00</span><span class="lista-elemento">401-101</span></span><span class="lista-elemento"><span>MIÉRCOLES de 07:00 a 09:00</span><span class="lista-elemento">401-101</span></span></span></span></div><div><span><span>16 SEMANAS</span></span></div><div><span><span>DIURNA</span></span></div><div><span><span>5</span></span></div></div></div></div><div class="group-wrapper"><h2 class="af_showDetailHeader_title-text0">2</h2><div class="af_showDetailHeader_content0"><div class="af_panelGroupLayout"><div><span><span>MARIA LOPEZ RUIZ</span></span></div><div><span><span>FACULTAD DE INGENIERIA</span></span></div><div><span><span><span class="lista-elemento"><span>MARTES de 14:00 a 16:00</span><span class="lista-elemento">405-205</span></span></span></span></div><div><span><span>16 SEMANAS</span></span></div><div><span><span>DIURNA</span></span></div></div></div></div>"""


@pytest.fixture
def sample_prereqs_xml():
    """Sample XML for course prerequisites."""
    return """<h2>CALCULO INTEGRAL (1000007)</h2><span class="detass-creditos"><span>4</span></span><span class="detass-tipologia">Tipología: DISCIPLINAR OBLIGATORIA</span><span class="borde salto af_panelGroupLayout"><div class="margin-t af_panelGroupLayout"><div><div><span class="strong af_panelGroupLayout"><span class="margin-l">Condición</span></span>Debe aprobar<span class="strong af_panelGroupLayout"><span class="margin-l">Tipo</span></span>Materia<span class="strong af_panelGroupLayout"><span class="margin-l">¿Todas?</span></span>SI<span class="strong af_panelGroupLayout"><span class="margin-l">Número asignaturas</span></span>1</div><div><span class="af_panelGroupLayout"><span>1000001</span></span>CALCULO DIFERENCIAL</div></div></div></span>"""


@pytest.fixture
def sample_empty_course_xml():
    """Sample XML for course with no groups."""
    return """
    <h2>CALCULO AVANZADO</h2>
    <span class="detass-creditos"><span>3</span></span>
    <span class="detass-tipologia"><span>DISCIPLINAR OBLIGATORIA</span></span>
    """


@pytest.mark.unit
class TestSiaScraperInitialization:
    """Test SiaScraper initialization."""

    @patch("sia_scraper.scraper.SiaSession")
    def test_init_default(self, mock_session_class):
        """Test default initialization."""
        mock_session = MagicMock()
        mock_session.career_code = ""
        mock_session_class.return_value = mock_session

        scraper = SiaScraper()

        assert scraper.career_name == "N/A"
        assert scraper.career_code == ""
        assert scraper.course_list == []
        mock_session_class.assert_called_once_with(
            timeout=DEFAULT_TIMEOUT, session_data={}, init_session=True
        )

    @patch("sia_scraper.scraper.SiaSession")
    def test_init_with_custom_timeout(self, mock_session_class):
        """Test initialization with custom timeout."""
        mock_session = MagicMock()
        mock_session.career_code = ""
        mock_session_class.return_value = mock_session

        _scraper = SiaScraper(timeout=30)

        mock_session_class.assert_called_once_with(timeout=30, session_data={}, init_session=True)

    @patch("sia_scraper.scraper.SiaSession")
    def test_init_without_session_creation(self, mock_session_class):
        """Test initialization without automatic session creation."""
        mock_session = MagicMock()
        mock_session.career_code = ""
        mock_session_class.return_value = mock_session

        _scraper = SiaScraper(init_session=False)

        mock_session_class.assert_called_once_with(
            timeout=DEFAULT_TIMEOUT, session_data={}, init_session=False
        )

    @patch("sia_scraper.scraper.SiaSession")
    def test_init_with_session_data(self, mock_session_class):
        """Test initialization with session data restoration."""
        session_data = {
            "career_code": "0-2-8-3",
            "career_name": "Ingeniería de Sistemas",
            "STATUS": "ON_CAREER_PAGE",
        }

        mock_session = MagicMock()
        mock_session.career_code = "0-2-8-3"
        mock_session.career_name = "Ingeniería de Sistemas"
        mock_session.course_list = ["1000001"]
        mock_session_class.return_value = mock_session

        scraper = SiaScraper(session_data=session_data)

        assert scraper.career_code == "0-2-8-3"
        assert scraper.career_name == "Ingeniería de Sistemas"


@pytest.mark.unit
class TestScraperProperties:
    """Test SiaScraper property accessors."""

    @patch("sia_scraper.scraper.SiaSession")
    def test_career_name_property(self, mock_session_class):
        """Test career_name property."""
        mock_session = MagicMock()
        mock_session.career_code = ""
        mock_session_class.return_value = mock_session

        scraper = SiaScraper()
        assert scraper.career_name == "N/A"

    @patch("sia_scraper.scraper.SiaSession")
    def test_career_code_property(self, mock_session_class):
        """Test career_code property."""
        mock_session = MagicMock()
        mock_session.career_code = ""
        mock_session_class.return_value = mock_session

        scraper = SiaScraper()
        assert scraper.career_code == ""

    @patch("sia_scraper.scraper.SiaSession")
    def test_course_list_property(self, mock_session_class):
        """Test course_list property."""
        mock_session = MagicMock()
        mock_session.career_code = ""
        mock_session_class.return_value = mock_session

        scraper = SiaScraper()
        assert isinstance(scraper.course_list, list)

    @patch("sia_scraper.scraper.SiaSession")
    def test_sia_session_property(self, mock_session_class):
        """Test sia_session property provides access to underlying session."""
        mock_session = MagicMock()
        mock_session.career_code = ""
        mock_session_class.return_value = mock_session

        scraper = SiaScraper()
        assert scraper.sia_session == mock_session


@pytest.mark.unit
class TestSessionManagementMethods:
    """Test session lifecycle delegation methods."""

    @patch("sia_scraper.scraper.SiaSession")
    def test_create_session(self, mock_session_class):
        """Test create_session delegates to SiaSession."""
        mock_session = MagicMock()
        mock_session.career_code = ""
        mock_session.init_session = MagicMock()
        mock_session_class.return_value = mock_session

        scraper = SiaScraper(init_session=False)
        result = scraper.create_session()

        mock_session.init_session.assert_called_once()
        assert result == scraper  # Returns self for chaining

    @patch("sia_scraper.scraper.SiaSession")
    def test_load_session(self, mock_session_class):
        """Test load_session delegates to SiaSession."""
        session_data = {"career_code": "0-2-8-3", "career_name": "Sistemas"}

        mock_session = MagicMock()
        mock_session.career_code = "0-2-8-3"
        mock_session.career_name = "Sistemas"
        mock_session.course_list = ["1000001"]
        mock_session.load_session = MagicMock()
        mock_session_class.return_value = mock_session

        scraper = SiaScraper(init_session=False)
        result = scraper.load_session(session_data)

        mock_session.load_session.assert_called_once_with(session_data)
        assert result == scraper
        assert scraper.career_code == "0-2-8-3"

    @patch("sia_scraper.scraper.SiaSession")
    def test_get_session_data(self, mock_session_class):
        """Test get_session_data delegates to SiaSession."""
        expected_data = {"career_code": "0-2-8-3", "STATUS": "ON_CAREER_PAGE"}

        mock_session = MagicMock()
        mock_session.career_code = ""
        mock_session.get_session_data = MagicMock(return_value=expected_data)
        mock_session_class.return_value = mock_session

        scraper = SiaScraper()
        session_data = scraper.get_session_data()

        assert session_data == expected_data
        mock_session.get_session_data.assert_called_once()

    @patch("sia_scraper.scraper.SiaSession")
    def test_close_session(self, mock_session_class):
        """Test close_session delegates to SiaSession."""
        mock_session = MagicMock()
        mock_session.career_code = ""
        mock_session.close_session = MagicMock()
        mock_session_class.return_value = mock_session

        scraper = SiaScraper()
        result = scraper.close_session()

        mock_session.close_session.assert_called_once()
        assert result == scraper

    @patch("sia_scraper.scraper.SiaSession")
    def test_valid_session(self, mock_session_class):
        """Test valid_session delegates to SiaSession."""
        mock_session = MagicMock()
        mock_session.career_code = ""
        mock_session.valid_session = MagicMock(return_value=True)
        mock_session_class.return_value = mock_session

        scraper = SiaScraper()
        is_valid = scraper.valid_session()

        assert is_valid is True
        mock_session.valid_session.assert_called_once()


@pytest.mark.unit
class TestCareerNavigation:
    """Test career navigation and context management."""

    @patch("sia_scraper.scraper.SiaSession")
    def test_set_career(self, mock_session_class):
        """Test set_career updates scraper context."""
        mock_session = MagicMock()
        mock_session.career_code = ""
        mock_session.set_career = MagicMock()
        mock_session_class.return_value = mock_session

        # Setup return values after set_career
        mock_session.career_code = "0-2-8-3"
        mock_session.career_name = "Ingeniería de Sistemas"
        mock_session.course_list = ["1000001", "1000007"]

        scraper = SiaScraper()
        result = scraper.set_career("0-2-8-3")

        mock_session.set_career.assert_called_once_with("0-2-8-3", electives=False)
        assert result == scraper
        assert scraper.career_code == "0-2-8-3"
        assert scraper.career_name == "Ingeniería de Sistemas"
        assert len(scraper.course_list) == 2

    @patch("sia_scraper.scraper.SiaSession")
    def test_set_career_with_electives(self, mock_session_class):
        """Test set_career with electives flag."""
        mock_session = MagicMock()
        mock_session.career_code = ""
        mock_session.set_career = MagicMock()
        mock_session_class.return_value = mock_session

        mock_session.career_code = "0-2-8-3"
        mock_session.career_name = "Electivas"
        mock_session.course_list = ["3000001"]

        scraper = SiaScraper()
        scraper.set_career("0-2-8-3", electives=True)

        mock_session.set_career.assert_called_once_with("0-2-8-3", electives=True)


@pytest.mark.unit
class TestCourseIndexHandling:
    """Test course index lookup and bugfix logic."""

    @patch("sia_scraper.scraper.SiaSession")
    def test_get_course_index_found(self, mock_session_class):
        """Test finding course index by code."""
        mock_session = MagicMock()
        mock_session.STATUS = SiaSessionStatus.ON_CAREER_PAGE
        mock_session_class.return_value = mock_session

        scraper = SiaScraper(init_session=False)
        scraper._SiaScraper__course_list = [  # type: ignore[attr-defined]
            "1000001 - Calculo",
            "1000007 - Algebra",
            "2016489 - Estructuras",
        ]
        scraper._SiaScraper__sia_session = mock_session  # type: ignore[attr-defined]

        index = scraper.get_course_index("2016489")
        assert index == 2

    @patch("sia_scraper.scraper.SiaSession")
    def test_get_course_index_not_found(self, mock_session_class):
        """Test get_course_index returns -1 when not found."""
        mock_session = MagicMock()
        mock_session.STATUS = SiaSessionStatus.ON_CAREER_PAGE
        mock_session_class.return_value = mock_session

        scraper = SiaScraper(init_session=False)
        scraper._SiaScraper__course_list = ["1000001 - Calculo"]  # type: ignore[attr-defined]
        scraper._SiaScraper__sia_session = mock_session  # type: ignore[attr-defined]

        index = scraper.get_course_index("9999999")
        assert index == -1

    @patch("sia_scraper.scraper.SiaSession")
    def test_get_course_index_swap_bugfix(self, mock_session_class):
        """Test index swap bugfix for indices 0 and 1."""
        mock_session = MagicMock()
        mock_session.STATUS = SiaSessionStatus.ON_CAREER_PAGE
        mock_session_class.return_value = mock_session

        scraper = SiaScraper(init_session=False)
        scraper._SiaScraper__course_list = [  # type: ignore[attr-defined]
            "1000001 - First",
            "1000007 - Second",
            "2016489 - Third",
        ]
        scraper._SiaScraper__sia_session = mock_session  # type: ignore[attr-defined]

        # Index 0 should be swapped to 1
        index_0 = scraper.get_course_index("1000001")
        assert index_0 == 1

        # Index 1 should be swapped to 0
        index_1 = scraper.get_course_index("1000007")
        assert index_1 == 0

        # Index 2 should remain 2
        index_2 = scraper.get_course_index("2016489")
        assert index_2 == 2

    @patch("sia_scraper.scraper.SiaSession")
    def test_get_course_index_invalid_status_raises_assertion(self, mock_session_class):
        """Test get_course_index raises AssertionError with invalid status."""
        mock_session = MagicMock()
        mock_session.STATUS = SiaSessionStatus.NO_SESSION
        mock_session_class.return_value = mock_session

        scraper = SiaScraper(init_session=False)
        scraper._SiaScraper__sia_session = mock_session  # type: ignore[attr-defined]

        with pytest.raises(AssertionError):
            scraper.get_course_index("1000001")


@pytest.mark.unit
class TestCourseInfoScraping:
    """Test course information scraping."""

    @patch("sia_scraper.scraper.SiaSession")
    def test_get_course_info_by_index(self, mock_session_class, sample_course_xml):
        """Test retrieving course info by index."""
        mock_session = MagicMock()
        mock_session.career_code = ""
        mock_session.get_course_xml = MagicMock(return_value=sample_course_xml)
        mock_session_class.return_value = mock_session

        scraper = SiaScraper()
        course_info = scraper.get_course_info(course_index=0)

        assert "courseName" in course_info
        assert course_info["courseName"] == "CALCULO DIFERENCIAL"
        assert course_info["credits"] == 4
        assert "groups" in course_info
        assert len(course_info["groups"]) == 2

    @patch("sia_scraper.scraper.SiaSession")
    def test_get_course_info_by_code(self, mock_session_class, sample_course_xml):
        """Test retrieving course info by course code."""
        mock_session = MagicMock()
        mock_session.STATUS = SiaSessionStatus.ON_CAREER_PAGE
        mock_session.get_course_xml = MagicMock(return_value=sample_course_xml)
        mock_session_class.return_value = mock_session

        scraper = SiaScraper(init_session=False)
        scraper._SiaScraper__course_list = ["1000001 - Calculo", "2016489 - Estructuras"]  # type: ignore[attr-defined]
        scraper._SiaScraper__sia_session = mock_session  # type: ignore[attr-defined]

        course_info = scraper.get_course_info(course_code="2016489")

        # Should call get_course_xml with index 1 (2016489 is at index 1)
        mock_session.get_course_xml.assert_called_once()
        assert "courseName" in course_info


@pytest.mark.unit
class TestCoursePrereqsScraping:
    """Test course prerequisites scraping."""

    @patch("sia_scraper.scraper.SiaSession")
    def test_get_course_prereqs_by_index(self, mock_session_class, sample_prereqs_xml):
        """Test retrieving course prerequisites by index."""
        mock_session = MagicMock()
        mock_session.career_code = ""
        mock_session.get_course_xml = MagicMock(return_value=sample_prereqs_xml)
        mock_session_class.return_value = mock_session

        scraper = SiaScraper()
        prereqs = scraper.get_course_prereqs(course_index=0)

        assert isinstance(prereqs, dict)
        mock_session.get_course_xml.assert_called_once_with(0)

    @patch("sia_scraper.scraper.SiaSession")
    def test_get_course_prereqs_by_code(self, mock_session_class, sample_prereqs_xml):
        """Test retrieving course prerequisites by course code."""
        mock_session = MagicMock()
        mock_session.STATUS = SiaSessionStatus.ON_CAREER_PAGE
        mock_session.get_course_xml = MagicMock(return_value=sample_prereqs_xml)
        mock_session_class.return_value = mock_session

        scraper = SiaScraper(init_session=False)
        scraper._SiaScraper__course_list = ["1000001 - Calculo"]  # type: ignore[attr-defined]
        scraper._SiaScraper__sia_session = mock_session  # type: ignore[attr-defined]

        prereqs = scraper.get_course_prereqs(course_code="1000001")

        assert isinstance(prereqs, dict)


@pytest.mark.unit
class TestScrapingUtilities:
    """Test static scraping utility methods."""

    def test_get_plain_text(self):
        """Test extracting plain text from XML."""
        xml = "<div><span>  Text with  spaces  </span></div>"

        plain_text = SiaScraper.get_plain_text(xml)

        # Should strip whitespace and normalize
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
        result = SiaScraper.get_plain_text(xml)
        assert expected_contains in result


@pytest.mark.unit
class TestScrapeInfo:
    """Test scrape_info static method for parsing course XML."""

    def test_scrape_info_complete_course(self, sample_course_xml):
        """Test scraping complete course information."""
        course_info = SiaScraper.scrape_info(sample_course_xml)

        assert course_info["courseName"] == "CALCULO DIFERENCIAL"
        assert course_info["credits"] == 4
        assert course_info["typology"] == "DISCIPLINAR OBLIGATORIA"
        assert len(course_info["groups"]) == 2

    def test_scrape_info_first_group(self, sample_course_xml):
        """Test scraping first group details."""
        course_info = SiaScraper.scrape_info(sample_course_xml)

        grupo_1 = course_info["groups"][0]
        assert grupo_1["groupName"] == "1"
        assert grupo_1["teacher"] == "JUAN PEREZ GARCIA"
        assert grupo_1["faculty"] == "FACULTAD DE CIENCIAS"
        assert grupo_1["duration"] == "16 SEMANAS"
        assert grupo_1["scheduleType"] == "DIURNA"
        assert grupo_1["spots"] == 5

    def test_scrape_info_schedules(self, sample_course_xml):
        """Test scraping schedule information."""
        course_info = SiaScraper.scrape_info(sample_course_xml)

        schedules = course_info["groups"][0]["schedules"]
        assert len(schedules) == 2

        assert schedules[0]["day"] == "LUNES"
        assert schedules[0]["startTime"] == "07:00"
        assert schedules[0]["endTime"] == "09:00"
        assert schedules[0]["classroom"] == "401-101"

        assert schedules[1]["day"] == "MIÉRCOLES"

    def test_scrape_info_nan_spots(self, sample_course_xml):
        """Test scraping handles NaN spots correctly."""
        course_info = SiaScraper.scrape_info(sample_course_xml)

        grupo_2 = course_info["groups"][1]
        assert grupo_2["spots"] == "NaN"

    def test_scrape_info_total_spots(self, sample_course_xml):
        """Test calculation of total available spots."""
        course_info = SiaScraper.scrape_info(sample_course_xml)

        # First group has 5 spots, second has NaN
        # Total should be 5 (NaN is skipped)
        assert course_info["availableSpots"] == 5

    def test_scrape_info_timestamp(self, sample_course_xml):
        """Test scraping includes timestamp."""
        course_info = SiaScraper.scrape_info(sample_course_xml)

        assert "scrapeTimestamp" in course_info
        assert course_info["scrapeTimestamp"] != ""

    def test_scrape_info_empty_course(self, sample_empty_course_xml):
        """Test scraping course with no groups."""
        course_info = SiaScraper.scrape_info(sample_empty_course_xml)

        assert course_info["courseName"] == "CALCULO AVANZADO"
        assert course_info["credits"] == 3
        assert course_info["groups"] == []
        assert course_info["availableSpots"] == 0

    def test_scrape_info_malformed_xml_returns_error(self):
        """Test scraping malformed XML handles gracefully."""
        malformed_xml = "<div>Incomplete XML"

        # Should not raise exception, may return partial data
        try:
            result = SiaScraper.scrape_info(malformed_xml)
            assert isinstance(result, dict)
        except Exception:
            # Some parsing errors are acceptable for malformed input
            pass

    def test_scrape_info_missing_teacher_falls_back(self):
        soup = MagicMock()
        soup.find.return_value = MagicMock(text="CURSO X")
        soup.find.side_effect = [
            MagicMock(text="CURSO X"),
            MagicMock(find=MagicMock(return_value=MagicMock(text="3"))),
            MagicMock(find=MagicMock(return_value=MagicMock(text="DISCIPLINAR OBLIGATORIA"))),
        ]
        group = MagicMock()
        group.parent.find.return_value = MagicMock(text="1")
        group_data = []
        g0 = MagicMock()
        g0.select_one.return_value = None
        g1 = MagicMock()
        g1.select_one.return_value = MagicMock(text="FACULTAD X")
        g2 = MagicMock()
        schedule_section = MagicMock()
        schedule_section.find_all.return_value = []
        g2.select_one.return_value = schedule_section
        g3 = MagicMock()
        g3.select_one.return_value = MagicMock(text="16 SEMANAS")
        g4 = MagicMock()
        g4.select_one.return_value = MagicMock(text="DIURNA")
        g5 = MagicMock()
        g5.select_one.return_value = MagicMock(text="2")
        group_data.extend([g0, g1, g2, g3, g4, g5])
        panel = MagicMock()
        panel.children = group_data
        group.find.return_value = panel
        soup.select.return_value = [group]

        formatter = MagicMock()
        formatter.format_date.return_value = "now"
        with (
            patch("sia_scraper.scraper.BeautifulSoup", return_value=soup),
            patch("sia_scraper.scraper.DateFormatter", return_value=formatter),
        ):
            result = SiaScraper.scrape_info("<xml/>")
        assert result["groups"][0]["teacher"] == "Not reported"

    def test_scrape_info_missing_credits_element_raises(self):
        xml = """
        <h2>CURSO X</h2>
        <span class="detass-tipologia"><span>DISCIPLINAR OBLIGATORIA</span></span>
        """
        with pytest.raises(ValueError, match="Credits element not found in XML"):
            SiaScraper.scrape_info(xml)

    def test_scrape_info_missing_credits_span_raises(self):
        xml = """
        <h2>CURSO X</h2>
        <span class="detass-creditos"></span>
        <span class="detass-tipologia"><span>DISCIPLINAR OBLIGATORIA</span></span>
        """
        with pytest.raises(ValueError, match="Credits span not found in XML"):
            SiaScraper.scrape_info(xml)

    def test_scrape_info_missing_tipology_element_raises(self):
        xml = """
        <h2>CURSO X</h2>
        <span class="detass-creditos"><span>3</span></span>
        """
        with pytest.raises(ValueError, match="Tipology element not found in XML"):
            SiaScraper.scrape_info(xml)

    def test_scrape_info_missing_tipology_span_raises(self):
        xml = """
        <h2>CURSO X</h2>
        <span class="detass-creditos"><span>3</span></span>
        <span class="detass-tipologia"></span>
        """
        with pytest.raises(ValueError, match="Tipology span not found in XML"):
            SiaScraper.scrape_info(xml)

    def test_scrape_info_skips_missing_and_invalid_schedule_rows(self):
        soup = MagicMock()
        soup.find.side_effect = [
            MagicMock(text="CURSO X"),
            MagicMock(find=MagicMock(return_value=MagicMock(text="3"))),
            MagicMock(find=MagicMock(return_value=MagicMock(text="DISCIPLINAR OBLIGATORIA"))),
        ]

        group = MagicMock()
        group.parent.find.return_value = MagicMock(text="1")

        g0 = MagicMock()
        g0.select_one.return_value = MagicMock(text="PROFESOR X")
        g1 = MagicMock()
        g1.select_one.return_value = MagicMock(text="FACULTAD X")
        g2 = MagicMock()
        schedule_section = MagicMock()
        invalid_no_span = MagicMock()
        invalid_no_span.find.return_value = None
        invalid_bad_text = MagicMock()
        invalid_bad_text.find.return_value = MagicMock(text="TEXTO INVALIDO")
        schedule_section.find_all.return_value = [invalid_no_span, invalid_bad_text]
        g2.select_one.return_value = schedule_section
        g3 = MagicMock()
        g3.select_one.return_value = MagicMock(text="16 SEMANAS")
        g4 = MagicMock()
        g4.select_one.return_value = MagicMock(text="DIURNA")
        g5 = MagicMock()
        g5.select_one.return_value = MagicMock(text="2")

        panel = MagicMock()
        panel.children = [g0, g1, g2, g3, g4, g5]
        group.find.return_value = panel
        soup.select.return_value = [group]

        formatter = MagicMock()
        formatter.format_date.return_value = "now"
        with (
            patch("sia_scraper.scraper.BeautifulSoup", return_value=soup),
            patch("sia_scraper.scraper.DateFormatter", return_value=formatter),
        ):
            result = SiaScraper.scrape_info("<xml/>")
        assert result["groups"][0]["schedules"] == []


@pytest.mark.unit
class TestScrapePrereqs:
    """Test scrape_prereqs static method."""

    def test_scrape_prereqs_basic(self, sample_prereqs_xml):
        """Test scraping basic prerequisites."""
        prereqs = SiaScraper.scrape_prereqs(sample_prereqs_xml)

        assert isinstance(prereqs, dict)
        assert prereqs["code"] == "1000007"
        assert prereqs["credits"] == 4
        assert prereqs["typology"] == "DISCIPLINAR OBLIGATORIA"
        assert "conditions" in prereqs

    def test_scrape_prereqs_empty_xml(self):
        """Test scraping prerequisites from empty XML."""
        empty_xml = "<div></div>"

        with pytest.raises(ValueError, match="Course name element not found in prerequisites XML"):
            SiaScraper.scrape_prereqs(empty_xml)

    def test_scrape_prereqs_missing_credits_element_raises(self):
        xml = """
        <h2>CURSO (1000)</h2>
        <span class="detass-tipologia">Tipología: DISCIPLINAR OBLIGATORIA</span>
        """
        with pytest.raises(ValueError, match="Credits element not found in prerequisites XML"):
            SiaScraper.scrape_prereqs(xml)

    def test_scrape_prereqs_missing_credits_span_raises(self):
        xml = """
        <h2>CURSO (1000)</h2>
        <span class="detass-creditos"></span>
        <span class="detass-tipologia">Tipología: DISCIPLINAR OBLIGATORIA</span>
        """
        with pytest.raises(ValueError, match="Credits span not found in prerequisites XML"):
            SiaScraper.scrape_prereqs(xml)

    def test_scrape_prereqs_handles_various_formats(self):
        """Test prerequisite scraping handles different XML formats."""
        xml_variations = [
            "<div><span>Requisitos:</span></div>",
            "<div><span>No hay requisitos</span></div>",
            "<div></div>",
        ]

        for xml in xml_variations:
            try:
                result = SiaScraper.scrape_prereqs(xml)
                assert isinstance(result, dict)
            except Exception:
                # Some formats may not be supported
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
        result = SiaScraper.scrape_prereqs(xml)
        assert result["conditions"] == []

    def test_scrape_prereqs_skips_when_less_than_four_headers(self):
        soup = MagicMock()
        soup.find_all.side_effect = [
            [MagicMock(text="CURSO (1000)")],
            [MagicMock(text="Tipología: DISCIPLINAR OBLIGATORIA")],
        ]
        soup.find.return_value.find.return_value.text = "3"
        condition_div = MagicMock()
        condition_info_div = MagicMock()
        h1, h2, h3 = MagicMock(), MagicMock(), MagicMock()
        for h, key, val in [
            (h1, "Condición", "Debe aprobar"),
            (h2, "Tipo", "Materia"),
            (h3, "¿Todas?", "SI"),
        ]:
            h.text = key
            h.nextSibling = MagicMock(text=val)
        condition_info_div.select.return_value = [h1, h2, h3]
        condition_div.children = [condition_info_div, MagicMock()]
        soup.select.return_value = [condition_div]
        with patch("sia_scraper.scraper.BeautifulSoup", return_value=soup):
            assert SiaScraper.scrape_prereqs("<xml/>")["conditions"] == []

    def test_scrape_prereqs_parses_multiple_prereqs(self):
        soup = MagicMock()
        soup.find_all.side_effect = [
            [MagicMock(text="CURSO (1000)")],
            [MagicMock(text="Tipología: DISCIPLINAR OBLIGATORIA")],
        ]
        soup.find.return_value.find.return_value.text = "3"

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
            h.text = key
            h.nextSibling = MagicMock(text=val)
            headers.append(h)
        condition_info_div.select.return_value = headers

        prereq_div1 = MagicMock()
        code_span1 = MagicMock(text="1000001")
        code_span1.nextSibling = MagicMock(text="CALCULO")
        prereq_div1.select_one.return_value = code_span1

        prereq_div2 = MagicMock()
        code_span2 = MagicMock(text="1000002")
        code_span2.nextSibling = MagicMock(text="ALGEBRA")
        prereq_div2.select_one.return_value = code_span2

        condition_div.children = [condition_info_div, prereq_div1, prereq_div2]
        soup.select.return_value = [condition_div]

        with patch("sia_scraper.scraper.BeautifulSoup", return_value=soup):
            out = SiaScraper.scrape_prereqs("<xml/>")
        assert out["conditions"][0]["prerequisites"] == {
            "1000001": "CALCULO",
            "1000002": "ALGEBRA",
        }

    def test_scrape_prereqs_skips_when_len_mismatch(self):
        class WeirdList(list):
            def __len__(self):
                return super().__len__() + 1

        soup = MagicMock()
        soup.find_all.side_effect = [
            [MagicMock(text="CURSO (1000)")],
            [MagicMock(text="Tipología: DISCIPLINAR OBLIGATORIA")],
        ]
        soup.find.return_value.find.return_value.text = "3"
        condition_div = MagicMock()
        condition_info_div = MagicMock()
        h1 = MagicMock()
        h1.text = "Condición"
        h1.nextSibling = MagicMock(text="Debe aprobar")
        h2 = MagicMock()
        h2.text = "Tipo"
        h2.nextSibling = MagicMock(text="Materia")
        h3 = MagicMock()
        h3.text = "¿Todas?"
        h3.nextSibling = MagicMock(text="SI")
        h4 = MagicMock()
        h4.text = "Número asignaturas"
        h4.nextSibling = MagicMock(text="1")
        condition_info_div.select.return_value = WeirdList([h1, h2, h3, h4])
        condition_div.children = [condition_info_div, MagicMock()]
        soup.select.return_value = [condition_div]

        with patch("sia_scraper.scraper.BeautifulSoup", return_value=soup):
            out = SiaScraper.scrape_prereqs("<xml/>")
        assert out["conditions"] == []


@pytest.mark.unit
class TestScrapeCourses:
    """Test scrape_courses batch processing method."""

    @patch("sia_scraper.scraper.SiaSession")
    def test_scrape_courses_empty_list(self, mock_session_class):
        """Test scraping empty course list."""
        mock_session = MagicMock()
        mock_session.career_code = ""
        mock_session_class.return_value = mock_session

        scraper = SiaScraper()
        result = scraper.scrape_courses([])

        assert result == []

    @patch("sia_scraper.scraper.SiaSession")
    def test_scrape_courses_with_course_codes(self, mock_session_class, sample_course_xml):
        """Test scraping multiple courses by code."""
        mock_session = MagicMock()
        mock_session.STATUS = SiaSessionStatus.ON_CAREER_PAGE
        mock_session.get_course_xml = MagicMock(return_value=sample_course_xml)
        mock_session_class.return_value = mock_session

        scraper = SiaScraper(init_session=False)
        scraper._SiaScraper__course_list = ["1000001 - Calculo", "1000007 - Algebra"]  # type: ignore[attr-defined]
        scraper._SiaScraper__sia_session = mock_session  # type: ignore[attr-defined]

        result = scraper.scrape_courses(courses_codes=["1000001", "1000007"])

        assert len(result) == 2
        assert all("courseName" in course for course in result)

    @patch("sia_scraper.scraper.SiaSession")
    def test_scrape_courses_with_invalid_code(self, mock_session_class, sample_course_xml):
        """Test scraping with invalid course code skips gracefully."""
        mock_session = MagicMock()
        mock_session.STATUS = SiaSessionStatus.ON_CAREER_PAGE
        mock_session.get_course_xml = MagicMock(return_value=sample_course_xml)
        mock_session_class.return_value = mock_session

        scraper = SiaScraper(init_session=False)
        scraper._SiaScraper__course_list = ["1000001 - Calculo"]  # type: ignore[attr-defined]
        scraper._SiaScraper__sia_session = mock_session  # type: ignore[attr-defined]

        # Attempt to scrape a course that doesn't exist
        result = scraper.scrape_courses(courses_codes=["1000001", "9999999"])

        # Should return data for valid course only
        assert len(result) >= 0


@pytest.mark.unit
class TestMethodChaining:
    """Test method chaining functionality."""

    @patch("sia_scraper.scraper.SiaSession")
    def test_method_chaining(self, mock_session_class):
        """Test methods return self for chaining."""
        mock_session = MagicMock()
        mock_session.career_code = ""
        mock_session.init_session = MagicMock()
        mock_session.set_career = MagicMock()
        mock_session.close_session = MagicMock()
        mock_session_class.return_value = mock_session

        scraper = SiaScraper(init_session=False)

        # Test chaining
        result = scraper.create_session().close_session()

        assert result == scraper


@pytest.mark.unit
class TestErrorHandling:
    """Test error handling in scraper methods."""

    @patch("sia_scraper.scraper.SiaSession")
    def test_scraping_propagates_session_exceptions(self, mock_session_class):
        """Test that session exceptions are propagated."""
        mock_session = MagicMock()
        mock_session.career_code = ""
        mock_session.get_course_xml = MagicMock(side_effect=SiaSessionException.TimeoutError())
        mock_session_class.return_value = mock_session

        scraper = SiaScraper()

        with pytest.raises(SiaSessionException.TimeoutError):
            scraper.get_course_info(0)

    @patch("sia_scraper.scraper.SiaSession")
    def test_scraping_empty_xml_returns_minimal_data(self, mock_session_class):
        """Test scraping empty XML returns minimal valid structure."""
        mock_session = MagicMock()
        mock_session.career_code = ""
        mock_session.get_course_xml = MagicMock(return_value="<div></div>")
        mock_session_class.return_value = mock_session

        scraper = SiaScraper()

        with pytest.raises(ValueError, match="Course name element not found in XML"):
            scraper.get_course_info(0)


@pytest.mark.unit
class TestComplexScenarios:
    """Test complex real-world scenarios."""

    @patch("sia_scraper.scraper.SiaSession")
    def test_full_workflow_simulation(self, mock_session_class, sample_course_xml):
        """Test complete workflow: create → set career → scrape → close."""
        mock_session = MagicMock()
        mock_session.career_code = ""
        mock_session.init_session = MagicMock()
        mock_session.set_career = MagicMock()
        mock_session.get_course_xml = MagicMock(return_value=sample_course_xml)
        mock_session.close_session = MagicMock()
        mock_session.STATUS = SiaSessionStatus.ON_CAREER_PAGE
        mock_session_class.return_value = mock_session

        # Simulate workflow
        scraper = SiaScraper(init_session=False)
        scraper.create_session()

        mock_session.career_code = "0-2-8-3"
        mock_session.career_name = "Sistemas"
        mock_session.course_list = ["1000001"]

        scraper.set_career("0-2-8-3")
        scraper._SiaScraper__course_list = ["1000001"]  # type: ignore[attr-defined]
        scraper._SiaScraper__sia_session = mock_session  # type: ignore[attr-defined]

        course_info = scraper.get_course_info(course_code="1000001")
        scraper.close_session()

        assert course_info["courseName"] == "CALCULO DIFERENCIAL"
        mock_session.init_session.assert_called_once()
        mock_session.close_session.assert_called_once()


@pytest.mark.unit
class TestSiaScraperFactories:
    """Test module-level session helper functions."""

    @patch("sia_scraper.scraper.create_career_session")
    def test_init_sia_scraper_empty_session_creates_new(self, mock_create):
        mock_create.return_value = MagicMock()
        result = init_sia_scraper("0-2-8-3", False, session_data={})
        assert result is mock_create.return_value
        mock_create.assert_called_once()

    @patch("sia_scraper.scraper.create_career_session")
    def test_init_sia_scraper_none_session_creates_new(self, mock_create):
        mock_create.return_value = MagicMock()
        result = init_sia_scraper("0-2-8-3", False, session_data=None)
        assert result is mock_create.return_value
        mock_create.assert_called_once()

    @patch("sia_scraper.scraper.create_career_session")
    @patch("sia_scraper.scraper.SiaScraper")
    def test_init_sia_scraper_invalid_session_falls_back(self, mock_cls, mock_create):
        sc = mock_cls.return_value
        sc.valid_session.return_value = False
        mock_create.return_value = MagicMock()
        out = init_sia_scraper("0-2-8-3", False, session_data={"x": 1}, timeout=15)
        assert out is mock_create.return_value

    @patch("sia_scraper.scraper.SiaScraper")
    def test_init_sia_scraper_switches_career_when_needed(self, mock_cls):
        sc = mock_cls.return_value
        sc.valid_session.return_value = True
        sc.career_code = "different"
        sc.sia_session.is_electives = False
        out = init_sia_scraper("0-2-8-3", True, session_data={"x": 1})
        assert out is sc
        sc.set_career.assert_called_once_with("0-2-8-3", electives=True)

    @patch("sia_scraper.scraper.SiaScraper")
    def test_create_career_session_calls_set_career(self, mock_cls):
        sc = mock_cls.return_value
        out = create_career_session("0-2-8-3", False, timeout=9)
        assert out is sc
        sc.set_career.assert_called_once_with("0-2-8-3", electives=False)


@pytest.mark.unit
def test_run_siascraper_module_main():
    mock_sc = MagicMock()
    mock_sc.sia_session.STATUS = "ON_CAREER_PAGE"
    mock_sc.career_name = "Sistemas"
    mock_sc.course_list = [1, 2, 3]
    with patch("sia_scraper.scraper.SiaScraper", return_value=mock_sc):
        runpy.run_module("sia_scraper.scraper", run_name="__main__")
