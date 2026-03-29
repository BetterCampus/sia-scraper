"""HTML/XML Parsing Module using lxml.

This module provides a clean interface for parsing HTML/XML content using lxml,
replacing BeautifulSoup for better performance and reduced dependencies.

The HtmlParser class wraps lxml's Element API with methods that mirror common
BeautifulSoup patterns, making migration straightforward while leveraging lxml's
performance benefits.
"""

from abc import ABC, abstractmethod
from typing import Any

from lxml import etree, html
from lxml.cssselect import CSSSelector


class HtmlParserError(Exception):
    """Base exception for HTML parsing errors."""


class BaseHtmlElement(ABC):
    """Base class for HTML/XML element wrappers with shared search methods.

    This abstract class provides common functionality for finding and selecting
    elements using XPath and CSS selectors. Both HtmlElement and HtmlParser
    inherit from this class to avoid code duplication.
    """

    @property
    @abstractmethod
    def _element(self) -> html.HtmlElement:
        """Return the underlying lxml element for search operations."""
        ...

    def find(self, tag: str, **attrs: Any) -> "HtmlElement | None":
        """Find first matching element.

        ## Args
            tag: HTML tag name (e.g., "div", "span", "h2").
            **attrs: Attributes to match (e.g., id="main", class_="header").

        ## Returns
            First matching element wrapped in HtmlElement, or None if not found.

        ## Example
            >>> element.find("div", id="main")
            <HtmlElement div>
        """
        elements = self.find_all(tag, **attrs)
        return elements[0] if elements else None

    def find_all(self, tag: str, **attrs: Any) -> list["HtmlElement"]:
        """Find all matching elements.

        ## Args
            tag: HTML tag name (e.g., "div", "span", "tr").
            **attrs: Attributes to match (e.g., class_="row", id="item").

        ## Returns
            List of HtmlElement wrappers (empty list if none found).

        ## Note
            Attribute names with underscores are converted to hyphens.
            E.g., class_="row" matches class="row".

            For class matching, uses contains() to handle multi-valued class attributes,
            similar to BeautifulSoup's behavior.
        """
        xpath_parts = [f"descendant::{tag}"]
        for key, value in attrs.items():
            normalized_key = key.rstrip("_").replace("_", "-")
            if normalized_key == "class":
                xpath_parts.append(
                    f"[contains(concat(' ', normalize-space(@class), ' '), ' {value} ')]"
                )
            else:
                xpath_parts.append(f"[@{normalized_key}='{value}']")

        xpath_expr = "".join(xpath_parts)
        results = self._element.xpath(xpath_expr)
        return [HtmlElement(r) for r in results]  # type: ignore[misc]

    def findall(self, xpath: str) -> list["HtmlElement"]:
        """Find elements using XPath expression.

        ## Args
            xpath: XPath expression.

        ## Returns
            List of HtmlElement wrappers.

        ## Example
            >>> element.findall("//div[@class='container']//span")
        """
        results = self._element.xpath(xpath)
        return [HtmlElement(r) for r in results]  # type: ignore[misc]

    def css_select(self, selector: str) -> list["HtmlElement"]:
        """Find elements using CSS selector.

        ## Args
            selector: CSS selector string.

        ## Returns
            List of HtmlElement wrappers.

        ## Example
            >>> element.css_select("div.container > span.title")
        """
        sel = CSSSelector(selector)
        return [HtmlElement(el) for el in sel(self._element)]  # type: ignore[misc]


class HtmlElement(BaseHtmlElement):
    """Wrapper for lxml elements with BeautifulSoup-compatible interface.

    This class wraps lxml HtmlElement to provide methods like find(), find_all(),
    findall(), text_content(), and css_select() that work like BeautifulSoup.
    """

    def __init__(self, element: html.HtmlElement) -> None:
        self.__element = element

    @property
    def _element(self) -> html.HtmlElement:
        """Return the underlying lxml element for search operations."""
        return self.__element

    def text_content(self) -> str:
        """Get all text content."""
        return self.__element.text_content() or ""

    def get(self, attr: str, default: str | None = None) -> str | None:
        """Get element attribute."""
        return self.__element.get(attr, default)

    @property
    def text(self) -> str:
        """Get text content of element (like BeautifulSoup)."""
        return self.__element.text or ""

    def getnext(self) -> "HtmlElement | None":
        """Get next sibling element."""
        sibling = self.__element.getnext()
        return HtmlElement(sibling) if sibling is not None else None

    @property
    def parent(self) -> "HtmlElement | None":
        """Get parent element."""
        parent = self.__element.getparent()
        return HtmlElement(parent) if parent is not None else None

    def __iter__(self):
        return iter([HtmlElement(child) for child in self.__element])

    def __len__(self) -> int:
        return len(self.__element)

    def __getitem__(self, index: int) -> html.HtmlElement:
        return self.__element[index]


class HtmlParser(BaseHtmlElement):
    """HTML/XML parser using lxml with BeautifulSoup-compatible interface.

    This class provides a simplified interface for common HTML parsing operations,
    combining lxml's speed with familiar method names.

    ## Example
        >>> parser = HtmlParser('<html><body><div id="main">Content</div></body></html>')
        >>> div = parser.find("div", id="main")
        >>> print(div.text_content())
        Content
    """

    def __init__(self, xml: str, parser: str = "html") -> None:
        """Initialize parser with XML content.

        ## Args
            xml: HTML/XML string to parse.
            parser: Parser to use - "html" (default) or "xml".
                Use "xml" for strict XML parsing.

        ## Raises
            HtmlParserError: If parsing fails.
        """
        self._parser_type = parser
        try:
            if parser == "xml":
                self._root = etree.fromstring(xml.encode("utf-8"))
            else:
                self._root = html.fromstring(xml)
        except etree.XMLSyntaxError as e:
            raise HtmlParserError(f"Failed to parse XML: {e}") from e

    @property
    def _element(self) -> html.HtmlElement:
        """Return the root element for search operations."""
        return self._root

    def text_content(self) -> str:
        """Get all text content of element and its descendants.

        ## Returns
            Concatenated text content of element and children.
        """
        return etree.tostring(self._root, method="text", encoding="unicode")  # type: ignore[return-value]

    def children(self) -> list["HtmlElement"]:
        """Get direct child elements.

        ## Returns
            List of HtmlElement wrappers for direct children.
        """
        return [HtmlElement(child) for child in self._root]

    def next_sibling(self) -> "HtmlElement | None":
        """Get the next sibling element.

        ## Returns
            HtmlElement wrapper for next sibling, or None if this is the last sibling.
        """
        sibling = self._root.getnext()
        return HtmlElement(sibling) if sibling is not None else None

    @property
    def root(self) -> html.HtmlElement:
        """Get the root element for advanced operations."""
        return self._root


def from_string(xml: str, parser: str = "html") -> HtmlParser:
    """Create HtmlParser from string.

    ## Args
        xml: HTML/XML string to parse.
        parser: Parser to use - "html" (default) or "xml".

    ## Returns
        HtmlParser instance.

    ## Example
        >>> parser = from_string('<div>Content</div>')
    """
    return HtmlParser(xml, parser)


def from_html(xml: str) -> HtmlParser:
    """Create HtmlParser from HTML string.

    ## Args
        xml: HTML string to parse.

    ## Returns
        HtmlParser instance for HTML parsing.
    """
    return HtmlParser(xml, parser="html")


def from_xml(xml: str) -> HtmlParser:
    """Create HtmlParser from XML string.

    ## Args
        xml: XML string to parse.

    ## Returns
        HtmlParser instance for XML parsing.
    """
    return HtmlParser(xml, parser="xml")


def get_course_list(html: bytes | str) -> list[dict[str, str]]:
    """Extract course list from Oracle ADF table HTML.

    ## Args
        html: Oracle ADF page HTML (bytes or string).

    ## Returns
        List of course dictionaries: [{course_code: course_name}, ...].

    ## Note
        Target: Oracle ADF table → <tr class="af_table_data-row"> elements.
        Each row contains <span class="af_column_data-container"> for code and name.
        First span = course code, second span = course name.
    """
    from sia_scraper.constants import COURSE_CODE_COL, COURSE_NAME_COL

    html_content = html.decode("utf-8", errors="ignore") if isinstance(html, bytes) else html
    html_parser = HtmlParser(html_content)

    rows = html_parser.find_all("tr", class_="af_table_data-row")

    course_list = []
    for row in rows:
        data_spans = row.findall(".//span[@class='af_column_data-container']")

        course_code = data_spans[COURSE_CODE_COL].text_content().strip()
        course_name = data_spans[COURSE_NAME_COL].text_content().strip()

        course_list.append({course_code: course_name})

    return course_list
