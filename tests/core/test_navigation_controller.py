"""Tests for NavigationController."""

from unittest.mock import patch

from sia_scraper.core.navigation_controller import NavigationController


class TestNavigationControllerInit:
    """Tests for NavigationController initialization."""

    def test_init_creates_default_state(self):
        controller = NavigationController()
        assert controller.career_code == ""
        assert controller.career_name == "N/A"
        assert controller.is_electives is False
        assert controller.course_list == []


class TestNavigationControllerSetters:
    """Tests for NavigationController state setters."""

    def test_career_code_setter(self):
        controller = NavigationController()
        controller._career_code = "1-2-3-4"
        assert controller.career_code == "1-2-3-4"

    def test_career_name_setter(self):
        controller = NavigationController()
        controller._career_name = "Ingenieria de Sistemas"
        assert controller.career_name == "Ingenieria de Sistemas"

    def test_is_electives_setter(self):
        controller = NavigationController()
        controller._is_electives = True
        assert controller.is_electives is True


class TestNavigationControllerRestore:
    """Tests for restore_from_session_data."""

    def test_restore_from_dict(self):
        session_data = {
            "career_code": "1-2-3-4",
            "career_name": "Computer Science",
            "is_electives": True,
        }
        controller = NavigationController()
        controller.restore_from_session_data(session_data)

        assert controller.career_code == "1-2-3-4"
        assert controller.career_name == "Computer Science"
        assert controller.is_electives is True

    def test_restore_with_defaults(self):
        session_data = {}
        controller = NavigationController()
        controller.restore_from_session_data(session_data)

        assert controller.career_code == ""
        assert controller.career_name == "N/A"
        assert controller.is_electives is False


class TestNavigationControllerUpdateCourseList:
    """Tests for update_course_list_from_xml."""

    @patch("sia_scraper.parsers.html_parser.get_course_list")
    def test_update_course_list_calls_parser(self, mock_get_course_list):
        mock_get_course_list.return_value = [{"2015555": "Algebra"}]
        controller = NavigationController()
        controller.update_course_list_from_xml("<xml>test</xml>")

        mock_get_course_list.assert_called_once_with("<xml>test</xml>")
        assert controller.course_list == [{"2015555": "Algebra"}]
