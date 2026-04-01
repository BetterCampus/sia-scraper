"""Async SIA scraper facade backed by Rust session workflow."""

import asyncio
from collections.abc import Callable

from .constants import http, status
from .constants.defaults import DEFAULT_CAREER_NAME
from .core import SiaSessionException
from .models.session import SessionStateTyped
from .parsers import CourseInfo, CoursePrereqs, scrape_info, scrape_prereqs
from .parsers.models import ErrorMode, ScrapeResult
from .session import SiaSession


class SiaScraper:
    """Async facade for SIA course data scraping."""

    def __init__(
        self,
        timeout: int = http.DEFAULT_TIMEOUT,
        session_data: dict[str, object] | SessionStateTyped | None = None,
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
        session_data: dict[str, object] | SessionStateTyped | None = None,
        init_session: bool = True,
    ) -> "SiaScraper":
        """Factory to create and optionally initialize an async scraper."""
        scraper = cls(timeout=timeout, session_data=session_data, init_session=init_session)

        if session_data is None and init_session:
            await scraper.create_session()

        return scraper

    @property
    def career_name(self) -> str:
        """Get the active career display name."""
        return self._sia_session.career_name

    @property
    def career_code(self) -> str:
        """Get the active hyphen-delimited career code."""
        return self._sia_session.career_code

    @property
    def course_list(self) -> list[dict[str, str]]:
        """Get loaded courses for the active career."""
        return self._sia_session.course_list

    @property
    def sia_session(self) -> SiaSession:
        """Get underlying async session wrapper."""
        return self._sia_session

    async def create_session(self) -> "SiaScraper":
        await self._sia_session.init_session()
        return self

    def load_session(self, session_data: dict[str, object] | SessionStateTyped) -> "SiaScraper":
        """Restore lightweight async session state from serialized data."""
        state = SessionStateTyped.model_validate(session_data)

        self._sia_session._career_code = state.career_code
        self._sia_session._career_name = state.career_name or DEFAULT_CAREER_NAME
        self._sia_session._is_electives = state.is_electives
        self._sia_session._career_indices = (
            state.career_code.split("-") if state.career_code else []
        )

        self._sia_session._status = status.SiaSessionStatus[state.status]

        self._sia_session._session_state = {
            "javax_faces_ViewState": state.javax_faces_ViewState,
            "course_list": state.course_list_as_dicts(),
        }
        self._sia_session._typed_state = state

        return self

    def get_session_data(self) -> SessionStateTyped:
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
        return self._sia_session.status != status.SiaSessionStatus.NO_SESSION

    async def set_career(self, search_code: str, is_electives: bool = False) -> "SiaScraper":
        await self._sia_session.set_career(search_code, is_electives=is_electives)
        return self

    def _resolve_course_index(self, course_index: int, course_code: str) -> int:
        """Resolve index from explicit code when provided."""
        return self.get_course_index(course_code) if course_code else course_index

    async def get_course_info(self, course_index: int = 0, course_code: str = "") -> CourseInfo:
        resolved_index = self._resolve_course_index(course_index, course_code)
        xml = await self._sia_session.get_course_xml(resolved_index)
        return scrape_info(xml)

    def get_course_index(self, course_code: str) -> int:
        if self._sia_session.status not in (
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
        resolved_index = self._resolve_course_index(course_index, course_code)
        xml = await self._sia_session.get_course_xml(resolved_index)
        return scrape_prereqs(xml)

    async def _scrape_abort_mode(self, paired: list[tuple[int, str]]) -> list[CourseInfo]:
        """Scrape courses and abort immediately on first failure."""
        courses: list[CourseInfo] = []
        for index, code in paired:
            course = await self.get_course_info(index)
            courses.append(course.model_copy(update={"code": code}))
        return courses

    async def _scrape_resilient_mode(
        self,
        paired: list[tuple[int, str]],
        error_mode: str,
        max_retries: int,
        retry_delay: float,
        progress_callback: Callable[[int, int, int, int], None] | None,
    ) -> ScrapeResult:
        """Scrape courses with skip/retry handling."""
        successes: list[CourseInfo] = []
        failures: list[tuple[int, str]] = []

        for i, (index, code) in enumerate(paired):
            last_error = ""
            attempts = max_retries if error_mode == ErrorMode.RETRY else 1

            for attempt in range(attempts):
                try:
                    course = await self.get_course_info(index)
                    successes.append(course.model_copy(update={"code": code}))
                    last_error = ""
                    break
                except (RuntimeError, ValueError, SiaSessionException) as exc:
                    last_error = str(exc)
                    if error_mode == ErrorMode.RETRY and attempt < attempts - 1:
                        await asyncio.sleep(retry_delay)

            if last_error and error_mode == ErrorMode.SKIP:
                failures.append((index, last_error))

            if progress_callback:
                progress_callback(i + 1, len(paired), len(successes), len(failures))

        return ScrapeResult.create(successes, failures)

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
        courses_indices = courses_indices or []
        courses_codes = courses_codes or []

        if not courses_indices:
            courses_indices = [self.get_course_index(course_code) for course_code in courses_codes]

        paired = list(zip(courses_indices, courses_codes, strict=True))
        paired.sort(key=lambda x: x[0])

        if error_mode == ErrorMode.ABORT:
            return await self._scrape_abort_mode(paired)

        return await self._scrape_resilient_mode(
            paired,
            error_mode,
            max_retries,
            retry_delay,
            progress_callback,
        )


async def init_sia_scraper(
    search_code: str,
    is_electives: bool,
    session_data: dict[str, object] | SessionStateTyped | None = None,
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
        await sc.set_career(search_code, is_electives=is_electives)

    return sc


async def create_career_session(
    search_code: str,
    is_electives: bool,
    timeout: int = http.DEFAULT_TIMEOUT,
) -> SiaScraper:
    """Create a new async scraper and navigate to the requested career."""
    sc = await SiaScraper.create(timeout=timeout)
    await sc.set_career(search_code, is_electives=is_electives)
    return sc
