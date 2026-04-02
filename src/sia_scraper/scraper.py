"""Async SIA scraper facade backed by Rust session workflow."""

import asyncio
from collections.abc import Callable

import sia_scraper_rust

from .constants import http, status
from .constants.defaults import DEFAULT_CAREER_NAME
from .core import SiaSessionException
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

    def load_session(
        self, session_data: dict[str, object] | sia_scraper_rust.SessionStateModel
    ) -> "SiaScraper":
        """Restore lightweight async session state from serialized data."""
        if isinstance(session_data, dict):
            return self.load_session_dict(session_data)

        # Handle Rust SessionStateModel
        self._load_session_from_model(session_data)
        return self

    def _load_session_from_model(self, state: sia_scraper_rust.SessionStateModel) -> None:
        """Load session from typed Rust model."""
        self._sia_session._career_code = state.career_code
        self._sia_session._career_name = state.career_name or DEFAULT_CAREER_NAME
        self._sia_session._is_electives = state.is_electives
        self._sia_session._career_indices = (
            state.career_code.split("-") if state.career_code else []
        )
        self._sia_session._status = status.SiaSessionStatus[state.status]

        from .session import _SessionRuntimeState

        runtime = _SessionRuntimeState()
        runtime.javax_faces_ViewState = state.javax_faces_view_state
        runtime.course_list = [
            {entry.course_code: entry.course_name} for entry in state.course_list
        ]
        self._sia_session._session_state = runtime
        self._sia_session._typed_state = state

    def load_session_dict(self, session_data: dict[str, object]) -> "SiaScraper":
        """Restore session from dict (legacy path)."""
        from .session import _SessionRuntimeState

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

        runtime = _SessionRuntimeState()
        viewstate_val = session_data.get("javax_faces_ViewState")
        runtime.javax_faces_ViewState = str(viewstate_val) if viewstate_val is not None else ""

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

        runtime.course_list = course_list_raw

        typed_entries: list[sia_scraper_rust.CourseListEntryModel] = []
        for row in course_list_raw:
            if isinstance(row, dict) and len(row) == 1:
                course_code, course_name = next(iter(row.items()))
                typed_entries.append(
                    sia_scraper_rust.CourseListEntryModel(
                        course_code=course_code,
                        course_name=course_name,
                    )
                )
                typed_entries.append(
                    sia_scraper_rust.CourseListEntryModel(
                        course_code=next(iter(row.keys())),
                        course_name=next(iter(row.values())),
                    )
                )

        def safe_str_dict(d: object) -> dict[str, str]:
            if not isinstance(d, dict):
                return {}
            result: dict[str, str] = {}
            for k, v in d.items():
                if isinstance(k, str) and isinstance(v, str):
                    result[k] = v
            return result

        self._sia_session._typed_state = sia_scraper_rust.SessionStateModel(
            session_headers=safe_str_dict(session_data.get("session_headers")),
            session_cookies=safe_str_dict(session_data.get("session_cookies")),
            params=safe_str_dict(session_data.get("params"))
            or {"Adf-Page-Id": "1", "Adf-Window-Id": ""},
            career_code=self._sia_session._career_code,
            career_name=self._sia_session._career_name,
            is_electives=self._sia_session._is_electives,
            status=status_str,
            course_list=typed_entries,
            javax_faces_view_state=runtime.javax_faces_ViewState or None,
        )

        return self

    def get_session_data(self) -> sia_scraper_rust.SessionStateModel:
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

    async def get_course_info(
        self, course_index: int = 0, course_code: str = ""
    ) -> sia_scraper_rust.CourseInfoModel:
        resolved_index = self._resolve_course_index(course_index, course_code)
        xml = await self._sia_session.get_course_xml(resolved_index)
        return sia_scraper_rust.parse_course_info(xml)  # type: ignore[attr-defined]

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
        resolved_index = self._resolve_course_index(course_index, course_code)
        xml = await self._sia_session.get_course_xml(resolved_index)
        return sia_scraper_rust.parse_prereqs(xml)  # type: ignore[attr-defined]

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
