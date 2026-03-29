"""Unit tests for `sia_scraper.session` SIA session management."""

from unittest.mock import MagicMock, patch

import pytest
from requests.exceptions import ConnectionError, ReadTimeout, Timeout

from sia_scraper.constants import (
    DEFAULT_TIMEOUT,
    SIA_BASE_URL,
    STUDY_LEVEL_DD,
    SiaSessionStatus,
)
from sia_scraper.session import SiaSession, SiaSessionException, get_course_list


@pytest.fixture
def mock_enhanced_session():
    """Mock EnhancedSession for HTTP operations."""
    with patch("sia_scraper.session.EnhancedSession") as mock_session_class:
        session_instance = MagicMock()
        session_instance.get = MagicMock()
        session_instance.post = MagicMock()
        session_instance.close = MagicMock()
        session_instance.headers = {}
        session_instance.cookies = MagicMock()
        session_instance.cookies.get_dict.return_value = {"JSESSIONID": "test_session_id"}
        mock_session_class.return_value = session_instance
        yield session_instance


@pytest.fixture
def mock_sia_initial_html():
    """Mock HTML response for SIA initial page load."""
    return b"""
    <!DOCTYPE html>
    <html>
    <body>
        <input type="hidden" name="javax.faces.ViewState" value="test_view_state_12345">
        <input type="hidden" name="Adf-Window-Id" value="test_window_id_67890">
        <input type="hidden" name="Adf-Page-Id" value="0">
    </body>
    </html>
    """


@pytest.fixture
def mock_sia_career_page_html():
    """Mock HTML response for SIA career page with course list."""
    return b"""
    <!DOCTYPE html>
    <html>
    <body>
        <table class="af_table_data-row">
            <tr><td>1000001 - Calculo Diferencial</td></tr>
            <tr><td>1000007 - Calculo Integral</td></tr>
            <tr><td>2016489 - Estructuras de Datos</td></tr>
        </table>
    </body>
    </html>
    """


@pytest.fixture
def mock_sia_course_detail_xml():
    """Mock XML response for course detail page."""
    return """
    <div class="course-detail">
        <div class="course-name">Calculo Diferencial</div>
        <div class="course-credits">4</div>
        <div class="course-groups">
            <div class="group">Grupo 1</div>
        </div>
    </div>
    """


@pytest.fixture
def sample_session_data():
    """Sample session data for loading/restoring session."""
    return {
        "session_headers": {
            "User-Agent": "Mozilla/5.0",
            "Accept": "*/*",
        },
        "session_cookies": {
            "JSESSIONID": "test_session_12345",
            "OAM_ID": "test_oam_67890",
        },
        "params": {
            "Adf-Window-Id": "window_123",
            "Adf-Page-Id": "0",
        },
        "javax_faces_ViewState": "view_state_abc",
        "career_code": "0-2-8-3",
        "career_name": "Ingeniería de Sistemas",
        "is_electives": False,
        "STATUS": "ON_CAREER_PAGE",
    }


@pytest.mark.unit
class TestSiaSessionExceptions:
    """Test SIA session exception classes."""

    def test_session_not_set_exception(self):
        """Test SessionNotSet exception."""
        with pytest.raises(SiaSessionException.SessionNotSet) as exc_info:
            raise SiaSessionException.SessionNotSet()

        assert "Must set session" in str(exc_info.value)

    def test_career_not_set_exception(self):
        """Test CareerNotSet exception."""
        with pytest.raises(SiaSessionException.CareerNotSet) as exc_info:
            raise SiaSessionException.CareerNotSet()

        assert "Must set career" in str(exc_info.value)

    def test_timeout_error_exception(self):
        """Test TimeoutError exception."""
        with pytest.raises(SiaSessionException.TimeoutError) as exc_info:
            raise SiaSessionException.TimeoutError()

        assert "took too long" in str(exc_info.value).lower()

    def test_invalid_status_exception(self):
        """Test InvalidStatus exception."""
        with pytest.raises(SiaSessionException.InvalidStatus) as exc_info:
            raise SiaSessionException.InvalidStatus()

        assert "Invalid action" in str(exc_info.value)


@pytest.mark.unit
class TestSiaSessionInitialization:
    """Test SiaSession initialization."""

    def test_init_without_session(self):
        """Test initialization without creating session."""
        session = SiaSession(init_session=False)

        assert session.timeout == DEFAULT_TIMEOUT
        assert session.STATUS == SiaSessionStatus.NO_SESSION
        assert session.career_code == ""
        assert session.career_name == "N/A"
        assert session.course_list == []
        assert session.is_electives is False

    def test_init_with_custom_timeout(self):
        """Test initialization with custom timeout."""
        session = SiaSession(timeout=30, init_session=False)

        assert session.timeout == 30

    @patch("sia_scraper.session.EnhancedSession")
    @patch("sia_scraper.session.HtmlParser")
    def test_init_with_session_creation(
        self, mock_HtmlParser, mock_session_class, mock_sia_initial_html
    ):
        """Test initialization with automatic session creation."""
        mock_response = MagicMock()
        mock_response.content = mock_sia_initial_html

        mock_session_instance = MagicMock()
        mock_session_instance.get.return_value = mock_response
        mock_session_class.return_value = mock_session_instance

        mock_parser = MagicMock()
        view_state_el = MagicMock()
        view_state_el.get.return_value = "test_view_state"
        window_id_el = MagicMock()
        window_id_el.get.return_value = "test_window_id"
        mock_parser.find.side_effect = [view_state_el, window_id_el]
        mock_HtmlParser.return_value = mock_parser

        session = SiaSession(init_session=True)

        assert session.STATUS == SiaSessionStatus.CAREER_NOT_SET
        mock_session_instance.get.assert_called_once()

    def test_init_with_session_data(self, sample_session_data):
        """Test initialization with session data restoration."""
        with patch("sia_scraper.session.EnhancedSession") as mock_session_class:
            with patch("sia_scraper.session.get_course_list") as mock_get_courses:
                mock_session_instance = MagicMock()
                mock_response = MagicMock()
                mock_response.content = b"<html></html>"
                mock_session_instance.get.return_value = mock_response
                mock_session_class.return_value = mock_session_instance
                mock_get_courses.return_value = ["1000001", "1000007"]

                session = SiaSession(session_data=sample_session_data)

                assert session.career_code == "0-2-8-3"
                assert session.career_name == "Ingeniería de Sistemas"
                assert session.STATUS == SiaSessionStatus.ON_CAREER_PAGE


@pytest.mark.unit
class TestSiaSessionProperties:
    """Test SiaSession property accessors."""

    def test_url_property(self):
        """Test url property returns SIA base URL."""
        session = SiaSession(init_session=False)
        assert session.url == SIA_BASE_URL

    def test_career_name_property(self):
        """Test career_name property."""
        session = SiaSession(init_session=False)
        assert session.career_name == "N/A"

    def test_career_code_property(self):
        """Test career_code property."""
        session = SiaSession(init_session=False)
        assert session.career_code == ""

    def test_is_electives_property(self):
        """Test is_electives property."""
        session = SiaSession(init_session=False)
        assert session.is_electives is False

    def test_course_list_property(self):
        """Test course_list property."""
        session = SiaSession(init_session=False)
        assert isinstance(session.course_list, list)
        assert session.course_list == []

    def test_status_property(self):
        """Test STATUS property."""
        session = SiaSession(init_session=False)
        assert session.STATUS == SiaSessionStatus.NO_SESSION


@pytest.mark.unit
class TestSessionLifecycle:
    """Test session lifecycle methods."""

    @patch("sia_scraper.session.EnhancedSession")
    @patch("sia_scraper.session.HtmlParser")
    def test_init_session(self, mock_HtmlParser, mock_session_class, mock_sia_initial_html):
        """Test creating a new session."""
        mock_response = MagicMock()
        mock_response.content = mock_sia_initial_html

        mock_session_instance = MagicMock()
        mock_session_instance.get.return_value = mock_response
        mock_session_class.return_value = mock_session_instance

        mock_parser = MagicMock()
        view_state_el = MagicMock()
        view_state_el.get.return_value = "view_state_123"
        window_id_el = MagicMock()
        window_id_el.get.return_value = "window_id_456"
        mock_parser.find.side_effect = [view_state_el, window_id_el]
        mock_HtmlParser.return_value = mock_parser

        session = SiaSession(init_session=False)
        session.init_session()

        assert session.STATUS == SiaSessionStatus.CAREER_NOT_SET
        assert session.main_page_html is not None
        mock_session_instance.get.assert_called_once()

    @patch("sia_scraper.session.EnhancedSession")
    @patch("sia_scraper.session.HtmlParser")
    def test_init_session_missing_view_state_raises(
        self, mock_HtmlParser, mock_session_class, mock_sia_initial_html
    ):
        mock_response = MagicMock()
        mock_response.content = mock_sia_initial_html
        mock_session_instance = MagicMock()
        mock_session_instance.get.return_value = mock_response
        mock_session_class.return_value = mock_session_instance

        mock_parser = MagicMock()
        view_state_el = None
        window_id_el = MagicMock()
        window_id_el.get.return_value = "window_id_456"
        mock_parser.find.side_effect = [view_state_el, window_id_el]
        mock_HtmlParser.return_value = mock_parser

        session = SiaSession(init_session=False)
        with pytest.raises(SiaSessionException.SessionNotSet):
            session.init_session()

    @patch("sia_scraper.session.EnhancedSession")
    @patch("sia_scraper.session.HtmlParser")
    def test_init_session_missing_window_id_raises(
        self, mock_HtmlParser, mock_session_class, mock_sia_initial_html
    ):
        mock_response = MagicMock()
        mock_response.content = mock_sia_initial_html
        mock_session_instance = MagicMock()
        mock_session_instance.get.return_value = mock_response
        mock_session_class.return_value = mock_session_instance

        mock_parser = MagicMock()
        view_state_el = MagicMock()
        view_state_el.get.return_value = "view_state_123"
        window_id_el = None
        mock_parser.find.side_effect = [view_state_el, window_id_el]
        mock_HtmlParser.return_value = mock_parser

        session = SiaSession(init_session=False)
        with pytest.raises(SiaSessionException.SessionNotSet):
            session.init_session()

    @patch("sia_scraper.session.EnhancedSession")
    @patch("sia_scraper.session.get_course_list")
    def test_load_session(self, mock_get_courses, mock_session_class, sample_session_data):
        """Test loading a serialized session."""
        mock_session_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.content = b"<html></html>"
        mock_session_instance.get.return_value = mock_response
        mock_session_class.return_value = mock_session_instance
        mock_get_courses.return_value = ["1000001"]

        session = SiaSession(init_session=False)
        result = session.load_session(sample_session_data)

        assert result == session  # Returns self for chaining
        assert session.career_code == "0-2-8-3"
        assert session.career_name == "Ingeniería de Sistemas"
        assert session.STATUS == SiaSessionStatus.ON_CAREER_PAGE

    @patch("sia_scraper.session.EnhancedSession")
    @patch("sia_scraper.session.HtmlParser")
    def test_get_session_data(self, mock_HtmlParser, mock_session_class, mock_sia_initial_html):
        """Test serializing session data."""
        mock_response = MagicMock()
        mock_response.content = mock_sia_initial_html

        mock_session_instance = MagicMock()
        mock_session_instance.get.return_value = mock_response
        mock_session_instance.headers = {"User-Agent": "Test"}
        mock_session_instance.cookies.get_dict.return_value = {"JSESSIONID": "test"}
        mock_session_class.return_value = mock_session_instance

        mock_parser = MagicMock()
        view_state_el = MagicMock()
        view_state_el.get.return_value = "view_state"
        window_id_el = MagicMock()
        window_id_el.get.return_value = "window_id"
        mock_parser.find.side_effect = [view_state_el, window_id_el]
        mock_HtmlParser.return_value = mock_parser

        session = SiaSession(init_session=True)
        session_data = session.get_session_data()

        assert "session_headers" in session_data
        assert "session_cookies" in session_data
        assert "params" in session_data
        assert "javax_faces_ViewState" in session_data
        assert "career_code" in session_data
        assert "STATUS" in session_data
        assert session_data["STATUS"] == "CAREER_NOT_SET"

    def test_get_session_data_internal_guard_with_wrapped(self):
        """Exercise internal None-session guard in get_session_data implementation."""
        session = SiaSession(init_session=False)
        session._SiaSession__session = None  # type: ignore[attr-defined]
        with pytest.raises(SiaSessionException.SessionNotSet):
            SiaSession.get_session_data.__wrapped__(session)  # type: ignore[attr-defined]

    @patch("sia_scraper.session.EnhancedSession")
    @patch("sia_scraper.session.HtmlParser")
    def test_close_session(self, mock_HtmlParser, mock_session_class, mock_sia_initial_html):
        """Test closing an active session."""
        mock_response = MagicMock()
        mock_response.content = mock_sia_initial_html

        mock_session_instance = MagicMock()
        mock_session_instance.get.return_value = mock_response
        mock_session_class.return_value = mock_session_instance

        mock_parser = MagicMock()
        view_state_el = MagicMock()
        view_state_el.get.return_value = "view_state"
        window_id_el = MagicMock()
        window_id_el.get.return_value = "window_id"
        mock_parser.find.side_effect = [view_state_el, window_id_el]
        mock_HtmlParser.return_value = mock_parser

        session = SiaSession(init_session=True)
        session.close_session()

        assert session.STATUS == SiaSessionStatus.NO_SESSION
        assert session.career_code == ""
        assert session.course_list == []
        mock_session_instance.close.assert_called_once()

    def test_close_session_internal_guard_with_wrapped(self):
        """Exercise internal None-session guard in close_session implementation."""
        session = SiaSession(init_session=False)
        session._SiaSession__session = None  # type: ignore[attr-defined]
        with pytest.raises(SiaSessionException.SessionNotSet):
            SiaSession.close_session.__wrapped__(session)  # type: ignore[attr-defined]

    def test_session_not_set_raises_exception(self):
        """Test operations without session raise SessionNotSet."""
        session = SiaSession(init_session=False)

        with pytest.raises(SiaSessionException.SessionNotSet):
            session.valid_session()


@pytest.mark.unit
class TestSessionValidation:
    """Test session validation methods."""

    @patch("sia_scraper.session.EnhancedSession")
    @patch("sia_scraper.session.HtmlParser")
    def test_valid_session_returns_true(
        self, mock_HtmlParser, mock_session_class, mock_sia_initial_html
    ):
        """Test valid_session returns True for active session."""
        mock_response_init = MagicMock()
        mock_response_init.content = mock_sia_initial_html

        mock_response_valid = MagicMock()
        mock_response_valid.text = "No timeout message"

        mock_session_instance = MagicMock()
        mock_session_instance.get.return_value = mock_response_init
        mock_session_instance.post.return_value = mock_response_valid
        mock_session_class.return_value = mock_session_instance

        mock_parser = MagicMock()
        view_state_el = MagicMock()
        view_state_el.get.return_value = "view_state"
        window_id_el = MagicMock()
        window_id_el.get.return_value = "window_id"
        mock_parser.find.side_effect = [view_state_el, window_id_el]
        mock_HtmlParser.return_value = mock_parser

        session = SiaSession(init_session=True)
        is_valid = session.valid_session()

        assert is_valid is True

    @patch("sia_scraper.session.EnhancedSession")
    @patch("sia_scraper.session.HtmlParser")
    def test_valid_session_detects_timeout(
        self, mock_HtmlParser, mock_session_class, mock_sia_initial_html
    ):
        """Test valid_session returns False when session timed out."""
        mock_response_init = MagicMock()
        mock_response_init.content = mock_sia_initial_html

        mock_response_timeout = MagicMock()
        mock_response_timeout.text = "AdfPage.PAGE.__getSessionTimeoutHelper().__alertTimeout()"

        mock_session_instance = MagicMock()
        mock_session_instance.get.return_value = mock_response_init
        mock_session_instance.post.return_value = mock_response_timeout
        mock_session_class.return_value = mock_session_instance

        mock_parser = MagicMock()
        view_state_el = MagicMock()
        view_state_el.get.return_value = "view_state"
        window_id_el = MagicMock()
        window_id_el.get.return_value = "window_id"
        mock_parser.find.side_effect = [view_state_el, window_id_el]
        mock_HtmlParser.return_value = mock_parser

        session = SiaSession(init_session=True)
        is_valid = session.valid_session()

        assert is_valid is False


@pytest.mark.unit
class TestHttpRequests:
    """Test HTTP request methods."""

    @patch("sia_scraper.session.EnhancedSession")
    @patch("sia_scraper.session.HtmlParser")
    def test_post_request(self, mock_HtmlParser, mock_session_class, mock_sia_initial_html):
        """Test making POST requests."""
        mock_response_init = MagicMock()
        mock_response_init.content = mock_sia_initial_html

        mock_response_post = MagicMock()
        mock_response_post.text = "Response text"

        mock_session_instance = MagicMock()
        mock_session_instance.get.return_value = mock_response_init
        mock_session_instance.post.return_value = mock_response_post
        mock_session_class.return_value = mock_session_instance

        mock_parser = MagicMock()
        view_state_el = MagicMock()
        view_state_el.get.return_value = "view_state"
        window_id_el = MagicMock()
        window_id_el.get.return_value = "window_id"
        mock_parser.find.side_effect = [view_state_el, window_id_el]
        mock_HtmlParser.return_value = mock_parser

        session = SiaSession(init_session=True)
        response = session.post_request({"key": "value"})

        assert response.text == "Response text"
        mock_session_instance.post.assert_called()

    @patch("sia_scraper.session.EnhancedSession")
    def test_get_request(self, mock_session_class):
        """Test making GET requests."""
        mock_response = MagicMock()
        mock_response.content = b"<html></html>"

        mock_session_instance = MagicMock()
        mock_session_instance.get.return_value = mock_response
        mock_session_class.return_value = mock_session_instance

        session = SiaSession(init_session=False)
        session._SiaSession__session = mock_session_instance  # type: ignore[attr-defined]

        response = session.get_request("https://example.com")

        assert response.content == b"<html></html>"
        mock_session_instance.get.assert_called_with("https://example.com", params={})

    def test_post_request_without_session_raises(self):
        session = SiaSession(init_session=False)
        with pytest.raises(SiaSessionException.SessionNotSet):
            session.post_request({"k": "v"})

    def test_post_request_internal_guard_with_wrapped(self):
        """Exercise internal None-session guard in post_request implementation."""
        session = SiaSession(init_session=False)
        session._SiaSession__session = None  # type: ignore[attr-defined]
        with pytest.raises(SiaSessionException.SessionNotSet):
            SiaSession.post_request.__wrapped__.__wrapped__(session, {"k": "v"})  # type: ignore[attr-defined]

    def test_get_request_without_session_raises(self):
        session = SiaSession(init_session=False)
        with pytest.raises(SiaSessionException.SessionNotSet):
            session.get_request("https://example.com")

    @patch("sia_scraper.session.EnhancedSession")
    def test_keep_alive(self, mock_session_class):
        """Test keep_alive method."""
        mock_response = MagicMock()
        mock_session_instance = MagicMock()
        mock_session_instance.post.return_value = mock_response
        mock_session_class.return_value = mock_session_instance

        session = SiaSession(init_session=False)
        session._SiaSession__session = mock_session_instance  # type: ignore[attr-defined]

        result = session.keep_alive()

        assert result == mock_response
        mock_session_instance.post.assert_called_once()


@pytest.mark.unit
class TestTimeoutHandling:
    """Test timeout and error handling."""

    @patch("sia_scraper.session.EnhancedSession")
    def test_timeout_exception_handling(self, mock_session_class):
        """Test timeout exceptions are converted to SiaSessionException.TimeoutError."""
        mock_session_instance = MagicMock()
        mock_session_instance.get.side_effect = Timeout("Connection timeout")
        mock_session_class.return_value = mock_session_instance

        session = SiaSession(init_session=False)
        session._SiaSession__session = mock_session_instance  # type: ignore[attr-defined]

        with pytest.raises(SiaSessionException.TimeoutError):
            session.get_request("https://example.com")

    @patch("sia_scraper.session.EnhancedSession")
    def test_read_timeout_exception_handling(self, mock_session_class):
        """Test ReadTimeout exceptions are converted."""
        mock_session_instance = MagicMock()
        mock_session_instance.get.side_effect = ReadTimeout("Read timeout")
        mock_session_class.return_value = mock_session_instance

        session = SiaSession(init_session=False)
        session._SiaSession__session = mock_session_instance  # type: ignore[attr-defined]

        with pytest.raises(SiaSessionException.TimeoutError):
            session.get_request("https://example.com")

    @patch("sia_scraper.session.EnhancedSession")
    def test_connection_error_handling(self, mock_session_class):
        """Test ConnectionError exceptions are converted."""
        mock_session_instance = MagicMock()
        mock_session_instance.get.side_effect = ConnectionError("Connection failed")
        mock_session_class.return_value = mock_session_instance

        session = SiaSession(init_session=False)
        session._SiaSession__session = mock_session_instance  # type: ignore[attr-defined]

        with pytest.raises(SiaSessionException.TimeoutError):
            session.get_request("https://example.com")


@pytest.mark.unit
class TestCareerNavigation:
    """Test career navigation and course list handling."""

    @patch("sia_scraper.session.get_course_list")
    def test_set_career(self, mock_get_courses):
        """Test setting a career and loading course list."""
        mock_get_courses.return_value = ["1000001 - Calculo", "2016489 - Estructuras"]
        session = SiaSession(init_session=False)
        session._SiaSession__session = MagicMock()  # type: ignore[attr-defined]
        session._SiaSession__STATUS = SiaSessionStatus.CAREER_NOT_SET  # type: ignore[attr-defined]
        session._SiaSession__javax_faces_ViewState = "view_state"  # type: ignore[attr-defined]
        session._SiaSession__Adf_Window_Id = "window_id"  # type: ignore[attr-defined]
        session._SiaSession__Adf_Page_Id = "page_id"  # type: ignore[attr-defined]
        session._SiaSession__params = {"Adf-Window-Id": "window_id", "Adf-Page-Id": "page_id"}  # type: ignore[attr-defined]
        session.request_dict = {"javax.faces.ViewState": "view_state"}

        response = MagicMock()
        response.text = '<select id="pt1:r1:0:soc3::content"><option>--</option><option>A</option><option>B</option><option>C</option><option>Ingenieria de Sistemas</option></select>'
        session.post_request = MagicMock(return_value=response)
        session.update_view_state = MagicMock()
        session.get_course_xml = MagicMock(return_value="<xml/>")

        with patch("sia_scraper.session.HtmlParser") as mock_HtmlParser:
            mock_parser = MagicMock()
            dd = MagicMock()
            dd.find_all.return_value = [
                MagicMock(text_content=MagicMock(return_value="--")),
                MagicMock(text_content=MagicMock(return_value="A")),
                MagicMock(text_content=MagicMock(return_value="B")),
                MagicMock(text_content=MagicMock(return_value="C")),
                MagicMock(text_content=MagicMock(return_value="Ingenieria de Sistemas")),
            ]
            mock_parser.find.return_value = dd
            mock_HtmlParser.return_value = mock_parser
            result = session.set_career("0-2-8-3")

        assert result == session  # Returns self for chaining
        assert session.STATUS == SiaSessionStatus.ON_CAREER_PAGE
        assert session.career_code == "0-2-8-3"
        assert len(session.course_list) > 0

    def test_set_career_without_session_raises_exception(self):
        """Test set_career without session raises SessionNotSet."""
        session = SiaSession(init_session=False)

        with pytest.raises(SiaSessionException.SessionNotSet):
            session.set_career("0-2-8-3")


@pytest.mark.unit
class TestCoursePageNavigation:
    """Test course page navigation methods."""

    @patch("sia_scraper.session.get_course_list")
    def test_enter_course_page(self, mock_get_courses):
        """Test entering a course detail page."""
        mock_get_courses.return_value = ["1000001", "1000007"]
        session = SiaSession(init_session=False)
        session._SiaSession__session = MagicMock()  # type: ignore[attr-defined]
        session._SiaSession__STATUS = SiaSessionStatus.CAREER_NOT_SET  # type: ignore[attr-defined]
        session._SiaSession__javax_faces_ViewState = "view_state"  # type: ignore[attr-defined]
        session._SiaSession__Adf_Window_Id = "window_id"  # type: ignore[attr-defined]
        session._SiaSession__Adf_Page_Id = "page_id"  # type: ignore[attr-defined]
        session._SiaSession__params = {"Adf-Window-Id": "window_id", "Adf-Page-Id": "page_id"}  # type: ignore[attr-defined]
        session.request_dict = {"javax.faces.ViewState": "view_state"}
        response = MagicMock()
        response.text = '<select id="pt1:r1:0:soc3::content"><option>--</option><option>A</option><option>B</option><option>C</option><option>Ingenieria de Sistemas</option></select>'
        session.post_request = MagicMock(return_value=response)
        session.update_view_state = MagicMock()
        session.get_course_xml = MagicMock(return_value="<xml/>")

        with patch("sia_scraper.session.HtmlParser") as mock_HtmlParser:
            mock_parser = MagicMock()
            dd = MagicMock()
            dd.find_all.return_value = [
                MagicMock(text_content=MagicMock(return_value="--")),
                MagicMock(text_content=MagicMock(return_value="A")),
                MagicMock(text_content=MagicMock(return_value="B")),
                MagicMock(text_content=MagicMock(return_value="C")),
                MagicMock(text_content=MagicMock(return_value="Ingenieria de Sistemas")),
            ]
            mock_parser.find.return_value = dd
            mock_HtmlParser.return_value = mock_parser
            session.set_career("0-2-8-3")
        session.enter_course_page(0)

        assert session.STATUS == SiaSessionStatus.ON_COURSE_PAGE

    @patch("sia_scraper.session.get_course_list")
    def test_exit_course_page(self, mock_get_courses):
        """Test exiting a course detail page back to career page."""
        mock_get_courses.return_value = ["1000001", "1000007"]
        session = SiaSession(init_session=False)
        session._SiaSession__session = MagicMock()  # type: ignore[attr-defined]
        session._SiaSession__STATUS = SiaSessionStatus.CAREER_NOT_SET  # type: ignore[attr-defined]
        session._SiaSession__javax_faces_ViewState = "view_state"  # type: ignore[attr-defined]
        session._SiaSession__Adf_Window_Id = "window_id"  # type: ignore[attr-defined]
        session._SiaSession__Adf_Page_Id = "page_id"  # type: ignore[attr-defined]
        session._SiaSession__params = {"Adf-Window-Id": "window_id", "Adf-Page-Id": "page_id"}  # type: ignore[attr-defined]
        session.request_dict = {"javax.faces.ViewState": "view_state"}
        response = MagicMock()
        response.text = '<select id="pt1:r1:0:soc3::content"><option>--</option><option>A</option><option>B</option><option>C</option><option>Ingenieria de Sistemas</option></select>'
        session.post_request = MagicMock(return_value=response)
        session.update_view_state = MagicMock()
        session.get_course_xml = MagicMock(return_value="<xml/>")

        with patch("sia_scraper.session.HtmlParser") as mock_HtmlParser:
            mock_parser = MagicMock()
            dd = MagicMock()
            dd.find_all.return_value = [
                MagicMock(text_content=MagicMock(return_value="--")),
                MagicMock(text_content=MagicMock(return_value="A")),
                MagicMock(text_content=MagicMock(return_value="B")),
                MagicMock(text_content=MagicMock(return_value="C")),
                MagicMock(text_content=MagicMock(return_value="Ingenieria de Sistemas")),
            ]
            mock_parser.find.return_value = dd
            mock_HtmlParser.return_value = mock_parser
            session.set_career("0-2-8-3")
        session.enter_course_page(0)
        session.exit_course_page()

        assert session.STATUS == SiaSessionStatus.ON_CAREER_PAGE

    def test_exit_course_page_wrong_status_raises_exception(self):
        """Test exit_course_page with wrong STATUS raises InvalidStatus."""
        session = SiaSession(init_session=False)

        with pytest.raises(SiaSessionException.InvalidStatus):
            session.exit_course_page()


@pytest.mark.unit
class TestRequestBodyGeneration:
    """Test request body generation for Oracle ADF."""

    @patch("sia_scraper.session.EnhancedSession")
    @patch("sia_scraper.session.HtmlParser")
    def test_generate_request_body(
        self, mock_HtmlParser, mock_session_class, mock_sia_initial_html
    ):
        """Test generating Oracle ADF request body."""
        mock_response = MagicMock()
        mock_response.content = mock_sia_initial_html

        mock_session_instance = MagicMock()
        mock_session_instance.get.return_value = mock_response
        mock_session_class.return_value = mock_session_instance

        mock_parser = MagicMock()
        view_state_el = MagicMock()
        view_state_el.get.return_value = "view_state"
        window_id_el = MagicMock()
        window_id_el.get.return_value = "window_id"
        mock_parser.find.side_effect = [view_state_el, window_id_el]
        mock_HtmlParser.return_value = mock_parser

        session = SiaSession(init_session=True)
        request_body = session._generate_request_body(STUDY_LEVEL_DD, idx=0)

        assert isinstance(request_body, dict)
        assert "javax.faces.ViewState" in request_body
        assert "Adf-Window-Id" in request_body

    @patch("sia_scraper.session.EnhancedSession")
    @patch("sia_scraper.session.HtmlParser")
    def test_update_view_state(self, mock_HtmlParser, mock_session_class):
        """Test updating ViewState token."""
        mock_response_init = MagicMock()
        mock_response_init.content = (
            b'<input type="hidden" name="javax.faces.ViewState" value="initial_state">'
        )

        mock_response_update = MagicMock()
        mock_response_update.content = (
            b'<input type="hidden" name="javax.faces.ViewState" value="updated_state">'
        )

        mock_session_instance = MagicMock()
        mock_session_instance.get.side_effect = [mock_response_init, mock_response_update]
        mock_session_class.return_value = mock_session_instance

        mock_parser = MagicMock()
        view_state_el = MagicMock()
        view_state_el.get.return_value = "initial_state"
        window_id_el = MagicMock()
        window_id_el.get.return_value = "window_id"
        mock_parser.find.side_effect = [view_state_el, window_id_el]
        mock_HtmlParser.return_value = mock_parser

        session = SiaSession(init_session=True)
        session.update_view_state()

        mock_session_instance.get.assert_called()

    @patch("sia_scraper.session.EnhancedSession")
    @patch("sia_scraper.session.HtmlParser")
    def test_update_view_state_raises_when_regex_misses(self, mock_HtmlParser, mock_session_class):
        mock_response_init = MagicMock()
        mock_response_init.content = (
            b'<input type="hidden" name="javax.faces.ViewState" value="initial_state">'
        )
        mock_response_update = MagicMock()
        mock_response_update.content = b"<html>No view state token</html>"
        mock_session_instance = MagicMock()
        mock_session_instance.get.side_effect = [mock_response_init, mock_response_update]
        mock_session_class.return_value = mock_session_instance

        mock_parser = MagicMock()
        view_state_el = MagicMock()
        view_state_el.get.return_value = "initial_state"
        window_id_el = MagicMock()
        window_id_el.get.return_value = "window_id"
        mock_parser.find.side_effect = [view_state_el, window_id_el]
        mock_HtmlParser.return_value = mock_parser

        session = SiaSession(init_session=True)
        with pytest.raises(SiaSessionException.SessionNotSet):
            session.update_view_state()

    def test_generate_request_body_unknown_data_name_raises(self):
        session = SiaSession(init_session=False)
        session._SiaSession__career_code = "0-2-8-3"  # type: ignore[attr-defined]
        session._SiaSession__session = MagicMock()  # type: ignore[attr-defined]
        session._SiaSession__Adf_Window_Id = "window"  # type: ignore[attr-defined]
        session._SiaSession__Adf_Page_Id = "0"  # type: ignore[attr-defined]
        session._SiaSession__javax_faces_ViewState = "vs"  # type: ignore[attr-defined]
        session._SiaSession__init_request_dict()  # type: ignore[attr-defined]
        with pytest.raises(KeyError, match="Unknown data_name"):
            session._generate_request_body("UNKNOWN_DATA_NAME")


@pytest.mark.unit
class TestDecoratorValidation:
    """Test decorator-based validation."""

    def test_check_session_decorator_blocks_without_session(self):
        """Test @check_session decorator prevents execution without session."""
        session = SiaSession(init_session=False)

        with pytest.raises(SiaSessionException.SessionNotSet):
            session.get_session_data()

    def test_check_career_decorator_blocks_without_career(self):
        """Test @check_career decorator prevents execution without career."""
        session = SiaSession(init_session=False)

        # Even if we have a session, career operations should fail
        with patch("sia_scraper.session.EnhancedSession"):
            session._SiaSession__session = MagicMock()  # type: ignore[attr-defined]

            with pytest.raises(SiaSessionException.InvalidStatus):
                session.get_course_xml(0)

    def test_check_status_decorator_validates_status(self):
        """Test @check_status decorator validates session status."""
        session = SiaSession(init_session=False)

        with pytest.raises(SiaSessionException.InvalidStatus):
            session.exit_course_page()


@pytest.mark.unit
class TestElectivesHandling:
    """Test electives-specific functionality."""

    @patch("sia_scraper.session.get_course_list")
    def test_set_career_with_electives(self, mock_get_courses):
        """Test setting career for electives courses."""
        mock_get_courses.return_value = ["3000001 - Electiva I"]
        session = SiaSession(init_session=False)
        session._SiaSession__session = MagicMock()  # type: ignore[attr-defined]
        session._SiaSession__STATUS = SiaSessionStatus.CAREER_NOT_SET  # type: ignore[attr-defined]
        session._SiaSession__javax_faces_ViewState = "view_state"  # type: ignore[attr-defined]
        session._SiaSession__Adf_Window_Id = "window_id"  # type: ignore[attr-defined]
        session._SiaSession__Adf_Page_Id = "page_id"  # type: ignore[attr-defined]
        session._SiaSession__params = {"Adf-Window-Id": "window_id", "Adf-Page-Id": "page_id"}  # type: ignore[attr-defined]
        session.request_dict = {"javax.faces.ViewState": "view_state"}
        response = MagicMock()
        response.text = '<select id="pt1:r1:0:soc3::content"><option>--</option><option>A</option><option>B</option><option>C</option><option>Ingenieria de Sistemas</option></select>'
        session.post_request = MagicMock(return_value=response)
        session.update_view_state = MagicMock()
        session.get_course_xml = MagicMock(return_value="<xml/>")

        with patch("sia_scraper.session.HtmlParser") as mock_HtmlParser:
            mock_parser = MagicMock()
            dd = MagicMock()
            dd.find_all.return_value = [
                MagicMock(text_content=MagicMock(return_value="--")),
                MagicMock(text_content=MagicMock(return_value="A")),
                MagicMock(text_content=MagicMock(return_value="B")),
                MagicMock(text_content=MagicMock(return_value="C")),
                MagicMock(text_content=MagicMock(return_value="Ingenieria de Sistemas")),
            ]
            mock_parser.find.return_value = dd
            mock_HtmlParser.return_value = mock_parser
            session.set_career("0-2-8-3", electives=True)

        assert session.is_electives is True
        assert session.STATUS == SiaSessionStatus.ON_CAREER_PAGE


@pytest.mark.unit
class TestSessionPersistence:
    """Test session data persistence and restoration."""

    @patch("sia_scraper.session.EnhancedSession")
    @patch("sia_scraper.session.HtmlParser")
    @patch("sia_scraper.session.get_course_list")
    def test_session_round_trip(
        self, mock_get_courses, mock_HtmlParser, mock_session_class, mock_sia_initial_html
    ):
        """Test saving and restoring session data maintains state."""
        mock_response = MagicMock()
        mock_response.content = mock_sia_initial_html

        mock_session_instance = MagicMock()
        mock_session_instance.get.return_value = mock_response
        mock_session_instance.headers = {"User-Agent": "Test"}
        mock_session_instance.cookies.get_dict.return_value = {"JSESSIONID": "123"}
        mock_session_class.return_value = mock_session_instance

        mock_parser = MagicMock()
        view_state_el = MagicMock()
        view_state_el.get.return_value = "view_state_original"
        window_id_el = MagicMock()
        window_id_el.get.return_value = "window_id_original"
        mock_parser.find.side_effect = [view_state_el, window_id_el]
        mock_HtmlParser.return_value = mock_parser

        mock_get_courses.return_value = ["1000001"]

        # Create and serialize session
        session1 = SiaSession(init_session=True)
        session_data = session1.get_session_data()

        # Restore in new session
        session2 = SiaSession(session_data=session_data)

        assert session2.STATUS == session1.STATUS

    def test_check_career_decorator_raises_when_not_set(self):
        session = SiaSession(init_session=False)

        @SiaSession.check_career
        def dummy(self):
            return "ok"

        with pytest.raises(SiaSessionException.CareerNotSet):
            dummy(session)

    def test_check_career_decorator_runs_when_career_is_set(self):
        session = SiaSession(init_session=False)
        session._SiaSession__career_code = "0-2-8-3"  # type: ignore[attr-defined]

        @SiaSession.check_career
        def dummy(self):
            return "ok"

        assert dummy(session) == "ok"

    def test_get_current_xml_calls_get_request(self):
        session = SiaSession(init_session=False)
        session._SiaSession__session = MagicMock()  # type: ignore[attr-defined]
        session._SiaSession__url = "http://x"  # type: ignore[attr-defined]
        session._SiaSession__params = {"a": "b"}  # type: ignore[attr-defined]
        response = MagicMock()
        response.text = "<xml/>"
        session.get_request = MagicMock(return_value=response)
        assert session.get_current_xml() == "<xml/>"

    def test_get_course_xml_calls_enter_and_exit(self):
        session = SiaSession(init_session=False)
        session._SiaSession__session = MagicMock()  # type: ignore[attr-defined]
        session._SiaSession__STATUS = SiaSessionStatus.ON_CAREER_PAGE  # type: ignore[attr-defined]
        enter_resp = MagicMock()
        enter_resp.text = "<course/>"
        session.enter_course_page = MagicMock(return_value=enter_resp)
        session.exit_course_page = MagicMock()
        assert session.get_course_xml(0) == "<course/>"
        session.enter_course_page.assert_called_once_with(0)
        session.exit_course_page.assert_called_once()

    def test_get_course_list_parser_with_empty_rows(self):
        html = "<table></table>"
        assert get_course_list(html) == []

    def test_get_course_list_parser_extracts_course(self):
        html = """
        <table>
          <tr class="af_table_data-row">
            <span class="af_column_data-container">1000001</span>
            <span class="af_column_data-container">CALCULO</span>
          </tr>
        </table>
        """
        assert get_course_list(html) == [{"1000001": "CALCULO"}]

    @patch("sia_scraper.session.get_course_list")
    def test_set_career_raises_when_dropdown_not_found(self, mock_get_courses):
        mock_get_courses.return_value = []
        session = SiaSession(init_session=False)
        session._SiaSession__session = MagicMock()  # type: ignore[attr-defined]
        session._SiaSession__STATUS = SiaSessionStatus.CAREER_NOT_SET  # type: ignore[attr-defined]
        session._SiaSession__javax_faces_ViewState = "view_state"  # type: ignore[attr-defined]
        session._SiaSession__Adf_Window_Id = "window_id"  # type: ignore[attr-defined]
        session._SiaSession__Adf_Page_Id = "page_id"  # type: ignore[attr-defined]
        session._SiaSession__params = {"Adf-Window-Id": "window_id", "Adf-Page-Id": "page_id"}  # type: ignore[attr-defined]
        session.request_dict = {"javax.faces.ViewState": "view_state"}
        session.update_view_state = MagicMock()
        session.get_course_xml = MagicMock(return_value="<xml/>")

        resp1, resp2, resp3, resp4, resp5, resp6 = (MagicMock() for _ in range(6))
        for resp in [resp1, resp2, resp3, resp4, resp5, resp6]:
            resp.text = "<xml/>"
        session.post_request = MagicMock(side_effect=[resp1, resp2, resp3, resp4, resp5, resp6])

        with patch("sia_scraper.session.HtmlParser") as mock_HtmlParser:
            mock_parser = MagicMock()
            mock_parser.find.return_value = None
            mock_parser.find_all.return_value = []
            mock_parser.find_by_xpath.return_value = []
            mock_HtmlParser.return_value = mock_parser
            with pytest.raises(SiaSessionException.CareerNotSet):
                session.set_career("0-2-8-3")

    @patch("sia_scraper.session.get_course_list")
    def test_set_career_raises_when_no_response_generated(self, mock_get_courses):
        """Exercise guard when Oracle sequence yields no final response object."""
        mock_get_courses.return_value = []
        session = SiaSession(init_session=False)
        session._SiaSession__session = MagicMock()  # type: ignore[attr-defined]
        session._SiaSession__STATUS = SiaSessionStatus.CAREER_NOT_SET  # type: ignore[attr-defined]
        session._SiaSession__javax_faces_ViewState = "view_state"  # type: ignore[attr-defined]
        session._SiaSession__Adf_Window_Id = "window_id"  # type: ignore[attr-defined]
        session._SiaSession__Adf_Page_Id = "page_id"  # type: ignore[attr-defined]
        session._SiaSession__params = {"Adf-Window-Id": "window_id", "Adf-Page-Id": "page_id"}  # type: ignore[attr-defined]
        session.request_dict = {"javax.faces.ViewState": "view_state"}
        session.update_view_state = MagicMock()

        class NeverEqual:
            def __eq__(self, other: object) -> bool:
                return False

        session._generate_request_body = MagicMock(return_value=NeverEqual())  # type: ignore[method-assign]
        session.post_request = MagicMock(return_value=None)

        with pytest.raises(SiaSessionException.CareerNotSet):
            session.set_career("0-2-8-3")
