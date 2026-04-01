"""Unit tests for HTML parser abstractions and course list extraction."""

import pytest

from sia_scraper.parsers.html_parser import (
    HtmlElement,
    HtmlParser,
    HtmlParserError,
    get_course_list,
)


@pytest.mark.unit
class TestHtmlParserCore:
    """Test HtmlParser wrapper functionality and edge cases."""

    def test_xml_parser_invalid_xml_raises(self):
        with pytest.raises(HtmlParserError, match="Failed to parse XML"):
            HtmlParser("<root><open></root>", parser="xml")

    def test_children_returns_empty_for_leaf_node(self):
        parser = HtmlParser("<div>text only</div>")
        assert parser.children() == []

    def test_next_sibling_returns_none_for_root(self):
        parser = HtmlParser("<div>solo</div>")
        assert parser.next_sibling() is None

    def test_getitem_returns_child_element(self):
        parser = HtmlParser("<div><span>A</span><span>B</span></div>")
        root = parser.root
        assert root[0].text_content() == "A"

    def test_getitem_on_found_element_returns_wrapped_child(self):
        parser = HtmlParser("<ul><li>A</li><li>B</li></ul>")
        ul = HtmlElement(parser.root)
        first = ul[0]
        second = ul[1]
        assert first.text_content() == "A"
        assert second.text_content() == "B"


@pytest.mark.unit
class TestGetCourseList:
    """Test extraction of course list table rows."""

    def test_get_course_list_from_real_fixture(self, sia_career_page_regular_html: bytes):
        courses = get_course_list(sia_career_page_regular_html)
        assert len(courses) > 0
        assert all(isinstance(item, dict) and item for item in courses)

    def test_get_course_list_skips_rows_with_missing_columns(self):
        html = """
        <table>
            <tr class="af_table_data-row">
                <td><span class="af_column_data-container">1000001</span></td>
            </tr>
        </table>
        """
        assert get_course_list(html) == []

    def test_get_course_list_with_string_content(self):
        html = """
        <table>
            <tr class="af_table_data-row">
                <td><span class="af_column_data-container">1000001</span></td>
                <td><span class="af_column_data-container">CALCULO</span></td>
            </tr>
        </table>
        """
        assert get_course_list(html) == [{"1000001": "CALCULO"}]


@pytest.mark.unit
class TestHtmlElementMethods:
    """Test HtmlElement method edge cases."""

    def test_get_returns_attribute_value(self):
        parser = HtmlParser('<div id="test-id">content</div>')
        elem = HtmlElement(parser.root)
        assert elem.get("id") == "test-id"

    def test_get_returns_default_for_missing_attribute(self):
        parser = HtmlParser("<div>no attrs</div>")
        elem = HtmlElement(parser.root)
        assert elem.get("missing-attr") is None

    def test_get_returns_custom_default_for_missing_attribute(self):
        parser = HtmlParser("<div>no attrs</div>")
        elem = HtmlElement(parser.root)
        assert elem.get("missing-attr", "fallback") == "fallback"

    def test_text_property_returns_direct_text(self):
        parser = HtmlParser("<div>direct text</div>")
        elem = HtmlElement(parser.root)
        assert elem.text == "direct text"

    def test_text_property_returns_empty_for_no_text(self):
        parser = HtmlParser("<div><span>nested</span></div>")
        elem = HtmlElement(parser.root)
        assert elem.text == ""

    def test_text_content_returns_all_text_content(self):
        parser = HtmlParser("<div>hello <span>world</span></div>")
        assert parser.text_content() == "hello world"

    def test_text_content_returns_empty_for_empty_document(self):
        parser = HtmlParser("<div></div>")
        assert parser.text_content() == ""
