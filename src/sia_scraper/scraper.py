"""Async SIA scraper facade backed by Rust session workflow."""

import asyncio
from collections.abc import Callable
from typing import Any

from .constants import http, status
from .core import SiaSessionException
from .parsers import CourseInfo, CoursePrereqs, scrape_info, scrape_prereqs
from .parsers.models import ErrorMode, ScrapeResult, SessionState
from .session import SiaSession


class SiaScraper:
    """Async facade for SIA course data scraping."""

    def __init__(
        self,
        timeout: int = http.DEFAULT_TIMEOUT,
        session_data: dict[str, Any] | SessionState | None = None,
        init_session: bool = False,
    ) -> None:
        self._timeout = timeout
        self._init_session = init_session
        self._sia_session = SiaSession(timeout=timeout)

        if session_data is not None:
            self.load_session(session_data)

    @classmethod
    async def create(
        cls,
        timeout: int = http.DEFAULT_TIMEOUT,
        session_data: dict[str, Any] | SessionState | None = None,
        init_session: bool = True,
    ) -> "SiaScraper":
        """Factory to create and optionally initialize an async scraper."""
        scraper = cls(timeout=timeout, session_data=session_data, init_session=init_session)

        if session_data is None and init_session:
            await scraper.create_session()

        return scraper

    @property
    def career_name(self) -> str:
        value = self._sia_session.career_name
        return value if isinstance(value, str) else "N/A"

    @property
    def career_code(self) -> str:
        value = self._sia_session.career_code
        return value if isinstance(value, str) else ""

    @property
    def course_list(self) -> list[dict[str, str]]:
        value = self._sia_session.course_list
        return value if isinstance(value, list) else []

    @property
    def sia_session(self) -> Any:
        return self._sia_session

    async def create_session(self) -> "SiaScraper":
        await self._sia_session.init_session()
        return self

    def load_session(self, session_data: dict[str, Any] | SessionState) -> "SiaScraper":
        """Restore lightweight async session state from serialized data."""
        state = SessionState.model_validate(session_data)

        self._sia_session._career_code = state.career_code
        self._sia_session._career_name = state.career_name or "N/A"
        self._sia_session._is_electives = state.is_electives
        self._sia_session._career_indices = (
            state.career_code.split("-") if state.career_code else []
        )

        try:
            restored_status = status.SiaSessionStatus[state.STATUS]
        except KeyError:
            restored_status = status.SiaSessionStatus.NO_SESSION
        self._sia_session._STATUS = restored_status

        self._sia_session._session_state = {
            "javax_faces_ViewState": state.javax_faces_ViewState,
            "course_list": self._sia_session._session_state.get("course_list", []),
        }

        return self

    def get_session_data(self) -> SessionState:
        return self._sia_session.get_session_data()

    async def close_session(self) -> "SiaScraper":
        await self._sia_session.close()
        return self

    async def __aenter__(self) -> "SiaScraper":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        await self._sia_session.close()

    def valid_session(self) -> bool:
        return self._sia_session.STATUS != status.SiaSessionStatus.NO_SESSION

    async def set_career(self, search_code: str, electives: bool = False) -> "SiaScraper":
        await self._sia_session.set_career(search_code, electives=electives)
        return self

    async def get_course_info(self, course_index: int = 0, course_code: str = "") -> CourseInfo:
        resolved_index = self.get_course_index(course_code) if course_code != "" else course_index
        xml = await self._sia_session.get_course_xml(resolved_index)
        return scrape_info(xml)

    def get_course_index(self, course_code: str) -> int:
        if self._sia_session.STATUS not in (
            status.SiaSessionStatus.ON_CAREER_PAGE,
            status.SiaSessionStatus.ON_COURSE_PAGE,
        ):
            raise SiaSessionException.InvalidStatus from None

        for i, course in enumerate(self.course_list):
            if course_code in course:
                return i
        raise ValueError(f"Course code '{course_code}' not found")

    async def get_course_prereqs(
        self, course_index: int = 0, course_code: str = ""
    ) -> CoursePrereqs:
        resolved_index = self.get_course_index(course_code) if course_code != "" else course_index
        xml = await self._sia_session.get_course_xml(resolved_index)
        return scrape_prereqs(xml)

    async def scrape_courses(
        self,
        courses_indices: list[int] | None = None,
        courses_codes: list[str] | None = None,
        error_mode: str = ErrorMode.ABORT,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        progress_callback: Callable[[int, int, int, int], None] | None = None,
    ) -> ScrapeResult | list[CourseInfo]:
        """Batch scrape multiple courses by index or code."""
        if courses_indices is None:
            courses_indices = []
        if courses_codes is None:
            courses_codes = []

        if courses_indices == []:
            courses_indices = [self.get_course_index(course_code) for course_code in courses_codes]

        paired = list(zip(courses_indices, courses_codes, strict=True))
        paired.sort(key=lambda x: x[0])

        if error_mode == str(ErrorMode.ABORT):
            courses: list[CourseInfo] = []
            for index, code in paired:
                course = await self.get_course_info(index)
                course = course.model_copy(update={"code": code})
                courses.append(course)
            return courses

        successes: list[CourseInfo] = []
        failures: list[tuple[int, str]] = []

        for i, (index, code) in enumerate(paired):
            last_error = ""
            for attempt in range(max_retries if error_mode == str(ErrorMode.RETRY) else 1):
                try:
                    course = await self.get_course_info(index)
                    course = course.model_copy(update={"code": code})
                    successes.append(course)
                    last_error = ""
                    break
                except Exception as e:  # noqa: BLE001
                    last_error = str(e)
                    if error_mode == ErrorMode.RETRY and attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)

            if last_error and error_mode == ErrorMode.SKIP:
                failures.append((index, last_error))

            if progress_callback:
                progress_callback(i + 1, len(paired), len(successes), len(failures))

        return ScrapeResult.create(successes, failures)


async def init_sia_scraper(
    search_code: str,
    is_electives: bool,
    session_data: dict[str, Any] | SessionState | None = None,
    timeout: int = http.DEFAULT_TIMEOUT,
) -> SiaScraper:
    """Initialize or restore an async scraper with session management."""
    if session_data is None:
        session_data = {}

    if session_data == {}:
        return await create_career_session(search_code, is_electives, timeout=timeout)

    sc = await SiaScraper.create(timeout=timeout, session_data=session_data, init_session=False)

    if not sc.valid_session():
        await sc.close_session()
        return await create_career_session(search_code, is_electives, timeout=timeout)

    if sc.career_code != search_code or sc.sia_session.is_electives != is_electives:
        await sc.set_career(search_code, electives=is_electives)

    return sc


async def create_career_session(
    search_code: str,
    is_electives: bool,
    timeout: int = http.DEFAULT_TIMEOUT,
) -> SiaScraper:
    """Create a new async scraper and navigate to the requested career."""
    sc = await SiaScraper.create(timeout=timeout)
    await sc.set_career(search_code, electives=is_electives)
    return sc
