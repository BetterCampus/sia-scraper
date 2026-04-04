"""Async SIA scraper facade backed by Rust session workflow."""

import asyncio
from collections.abc import Callable

import sia_scraper_rust

from .constants import http, status
from .constants.defaults import DEFAULT_CAREER_NAME
from .core import SiaSessionException
from .core.exceptions import SiaScraperException
from .parsers.models import ErrorMode, ScrapeResult
from .session import SiaSession


class SiaScraper:
    """Async facade for SIA course data scraping."""

    def __init__(
        self,
        timeout: int = http.DEFAULT_TIMEOUT,
        session_data: dict[str, object] | sia_scraper_rust.SessionStateModel | None = None,
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
        session_data: dict[str, object] | sia_scraper_rust.SessionStateModel | None = None,
        init_session: bool = True,
    ) -> "SiaScraper":
        """Factory to create and optionally initialize an async scraper."""
        scraper = cls(timeout=timeout, session_data=session_data, init_session=False)

        if session_data is None and init_session:
            await scraper.create_session()
        elif isinstance(session_data, dict) and "state_dict" in session_data:
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

    def load_session(
        self, session_data: dict[str, object] | sia_scraper_rust.SessionStateModel
    ) -> "SiaScraper":
        """Restore lightweight async session state from serialized data."""
        if isinstance(session_data, dict):
            if "state_dict" in session_data:
                asyncio.get_event_loop().run_until_complete(
                    self._load_session_from_state_dict(session_data)
                )
                return self
            return self.load_session_dict(session_data)

        self._load_session_from_model(session_data)
        return self

    async def _load_session_from_state_dict(self, session_data: dict[str, object]) -> None:
        """Load session from new Rust state dict format."""
        self._sia_session = await SiaSession.from_state(session_data)

    def _load_session_from_model(self, state: sia_scraper_rust.SessionStateModel) -> None:
        """Load session from typed Rust model."""
        self._sia_session._career_code = state.career_code
        self._sia_session._career_name = state.career_name or DEFAULT_CAREER_NAME
        self._sia_session._is_electives = state.is_electives
        self._sia_session._career_indices = (
            state.career_code.split("-") if state.career_code else []
        )
        self._sia_session._status = status.SiaSessionStatus[state.status]
        self._sia_session._course_list = [
            {entry.course_code: entry.course_name} for entry in state.course_list
        ]

    def load_session_dict(self, session_data: dict[str, object]) -> "SiaScraper":
        """Restore session from dict (legacy path)."""
        self._sia_session._career_code = str(session_data.get("career_code", ""))
        self._sia_session._career_name = str(session_data.get("career_name", DEFAULT_CAREER_NAME))
        self._sia_session._is_electives = bool(session_data.get("is_electives", False))

        career_code = self._sia_session._career_code
        self._sia_session._career_indices = career_code.split("-") if career_code else []

        status_str = str(session_data.get("status", "NO_SESSION"))
        try:
            self._sia_session._status = status.SiaSessionStatus[status_str]
        except KeyError as exc:
            allowed_statuses = ", ".join(sorted(status.SiaSessionStatus.__members__.keys()))
            message = (
                f"Invalid session status '{status_str}'. Allowed statuses are: {allowed_statuses}"
            )
            raise SiaSessionException(message) from exc

        course_list_raw: list[dict[str, str]] = []
        raw_course_list = session_data.get("course_list")
        if raw_course_list is not None and not isinstance(raw_course_list, list):
            raise SiaSessionException("Invalid session_data: 'course_list' must be a list")

        if isinstance(raw_course_list, list):
            for index, item in enumerate(raw_course_list):
                if not isinstance(item, dict):
                    raise SiaSessionException(
                        f"Invalid session_data: 'course_list[{index}]' must be a dict"
                    )
                if len(item) != 1:
                    raise SiaSessionException(
                        f"Invalid session_data: 'course_list[{index}]' must contain exactly one entry"
                    )
                for k, v in item.items():
                    if not isinstance(k, str) or not isinstance(v, str):
                        raise SiaSessionException(
                            f"Invalid session_data: 'course_list[{index}]' key and value must be strings"
                        )
                course_list_raw.append(item)

        self._sia_session._course_list = course_list_raw
        return self

    async def get_session_data(self) -> dict:
        return await self._sia_session.get_session_data()

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

    async def get_course_info(
        self, course_index: int = 0, course_code: str = ""
    ) -> sia_scraper_rust.CourseInfoModel:
        """Get course info using zero-copy Rust scraping."""
        resolved_index = self._resolve_course_index(course_index, course_code)
        course = await self._sia_session.scrape_course_info(resolved_index)
        if course_code:
            course.code = course_code
        return course

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
    ) -> sia_scraper_rust.CoursePrereqsModel:
        """Get course prerequisites using zero-copy Rust scraping."""
        resolved_index = self._resolve_course_index(course_index, course_code)
        return await self._sia_session.scrape_course_prereqs(resolved_index)

    async def _scrape_abort_mode(
        self, paired: list[tuple[int, str]]
    ) -> list[sia_scraper_rust.CourseInfoModel]:
        """Scrape courses and abort immediately on first failure."""
        courses: list[sia_scraper_rust.CourseInfoModel] = []
        for index, code in paired:
            course = await self.get_course_info(index)
            course.code = code
            courses.append(course)
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
        successes: list[sia_scraper_rust.CourseInfoModel] = []
        failures: list[tuple[int, str]] = []

        for i, (index, code) in enumerate(paired):
            last_error = ""
            attempts = max_retries if error_mode == ErrorMode.RETRY else 1

            for attempt in range(attempts):
                try:
                    course = await self.get_course_info(index)
                    course.code = code
                    successes.append(course)
                    last_error = ""
                    break
                except (RuntimeError, ValueError, SiaSessionException) as exc:
                    last_error = str(exc)
                    if error_mode == ErrorMode.RETRY and attempt < attempts - 1:
                        await asyncio.sleep(retry_delay)
                except SiaScraperException as exc:
                    last_error = str(exc)
                    if error_mode == ErrorMode.RETRY and attempt < attempts - 1:
                        await asyncio.sleep(retry_delay)

            if last_error:
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
    ) -> ScrapeResult | list[sia_scraper_rust.CourseInfoModel]:
        """Batch scrape multiple courses by index or code.

        Delegates to Rust batch scraping for efficient sequential execution
        with configurable error handling modes.

        Args:
            courses_indices: List of course indices to scrape.
            courses_codes: List of course codes to scrape (resolved to indices).
            error_mode: Error handling strategy - "abort", "skip", or "retry".
            max_retries: Maximum retry attempts per course (retry mode only).
            retry_delay: Base delay between retries in seconds (retry mode only).
            progress_callback: Optional callback(current, total, successes, failures).

        Returns:
            List of CourseInfoModel in abort mode, or ScrapeResult in skip/retry mode.
        """
        courses_indices = courses_indices or []
        courses_codes = courses_codes or []

        if not courses_indices:
            courses_indices = [self.get_course_index(course_code) for course_code in courses_codes]

        paired = list(zip(courses_indices, courses_codes, strict=True))
        paired.sort(key=lambda x: x[0])
        indices = [idx for idx, _ in paired]

        if error_mode == ErrorMode.ABORT:
            result = await self._sia_session.scrape_courses(
                indices,
                mode="abort",
                retries=0,
                delay=0,
            )
            # Map course codes back to results (all succeeded in abort mode)
            code_map = {idx: code for idx, code in paired if code}
            for idx, course in enumerate(result.successes):
                if idx < len(indices) and indices[idx] in code_map:
                    course.code = code_map[indices[idx]]
            return result.successes

        delay_ms = int(retry_delay * 1000)
        rust_result = await self._sia_session.scrape_courses(
            indices,
            mode=error_mode.lower(),
            retries=max_retries if error_mode == ErrorMode.RETRY else 0,
            delay=delay_ms,
        )

        if progress_callback:
            progress_callback(
                rust_result.total(),
                rust_result.total(),
                len(rust_result.successes),
                len(rust_result.failures),
            )

        return ScrapeResult.create(
            successes=rust_result.successes,
            failures=rust_result.failures,
        )


async def init_sia_scraper(
    search_code: str,
    is_electives: bool,
    session_data: dict[str, object] | sia_scraper_rust.SessionStateModel | None = None,
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
