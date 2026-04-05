"""Async SIA scraper facade backed by Rust session workflow."""

import asyncio
import warnings
from collections.abc import Callable

from loguru import logger

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
            {"code": entry.code, "name": entry.name} for entry in state.course_list
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

                # Extract code from current or legacy key
                code_val = item.get("code")
                if code_val is None:
                    code_val = item.get("course_code")
                # Extract name from current or legacy key
                name_val = item.get("name")
                if name_val is None:
                    name_val = item.get("course_name")
                # Check if any legacy keys were used
                used_legacy = "course_code" in item or "course_name" in item

                if code_val is not None and name_val is not None:
                    # Validate types
                    if not isinstance(code_val, str) or not isinstance(name_val, str):
                        raise SiaSessionException(
                            f"Invalid session_data: 'course_list[{index}]' "
                            "code and name must be strings"
                        )
                    # Emit warning if legacy keys detected
                    if used_legacy:
                        warnings.warn(
                            f"session_data 'course_list[{index}]' uses deprecated "
                            "'course_code'/'course_name' keys; use 'code'/'name' instead. "
                            "Support will be removed in version 4.0.0.",
                            DeprecationWarning,
                            stacklevel=2,
                        )
                    # Always create fresh dict to drop any extra keys
                    course_list_raw.append({"code": code_val, "name": name_val})
                elif len(item) == 1:
                    # Single-key legacy format
                    k, v = next(iter(item.items()))
                    # Reject reserved keys as single-key entries
                    if k in {"code", "name", "course_code", "course_name"}:
                        raise SiaSessionException(
                            f"Invalid session_data: 'course_list[{index}]' "
                            f"key '{k}' is reserved; use code/name keys instead"
                        )
                    if not isinstance(k, str) or not isinstance(v, str):
                        raise SiaSessionException(
                            f"Invalid session_data: 'course_list[{index}]' "
                            "key and value must be strings"
                        )
                    warnings.warn(
                        f"session_data 'course_list[{index}]' uses deprecated single-key dict format. "
                        "Use {{'code': ..., 'name': ...}} instead. "
                        "Legacy format support will be removed in version 4.0.0.",
                        DeprecationWarning,
                        stacklevel=2,
                    )
                    course_list_raw.append({"code": k, "name": v})
                else:
                    raise SiaSessionException(
                        f"Invalid session_data: 'course_list[{index}]' "
                        "must have 'code'/'name' keys or be a single-key dict"
                    )

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

    def _prepare_scrape_indices(
        self,
        courses_indices: list[int] | None,
        courses_codes: list[str] | None,
    ) -> tuple[list[tuple[int, str]], list[int]]:
        """Prepare and validate scrape indices from indices and/or codes.

        Note: Indices are sorted in ascending order. Results will be returned
        in sorted index order, not the order provided by the caller. If the
        same index appears multiple times with different codes, the last code
        wins when applied via _apply_course_codes.

        Args:
            courses_indices: List of course indices to scrape.
            courses_codes: List of course codes to scrape (resolved to indices).

        Returns:
            Tuple of (paired list sorted by index, sorted indices list).

        Raises:
            ValueError: If both courses_indices and courses_codes are None or empty.
            ValueError: If both provided but lengths differ.
            ValueError: If any provided course code is not found in the course list.

        Example:
            >>> paired, indices = self._prepare_scrape_indices([0, 2], ["CODE1", "CODE2"])
            >>> paired
            [(0, 'CODE1'), (2, 'CODE2')]
            >>> indices
            [0, 2]

            >>> # Raises when both are empty
            >>> self._prepare_scrape_indices(None, None)  # doctest: +IGNORE_EXCEPTION_DETAIL
            Traceback (most recent call last):
            ValueError: At least one of courses_indices or courses_codes must be provided
        """
        courses_indices = courses_indices or []
        courses_codes = courses_codes or []

        if not courses_indices and not courses_codes:
            raise ValueError("At least one of courses_indices or courses_codes must be provided")

        if not courses_indices:
            courses_indices = [self.get_course_index(code) for code in courses_codes]

        if not courses_codes:
            courses_codes = [""] * len(courses_indices)

        if len(courses_indices) != len(courses_codes):
            raise ValueError(
                f"Length mismatch: courses_indices has {len(courses_indices)} items, "
                f"but courses_codes has {len(courses_codes)} items"
            )

        paired = list(zip(courses_indices, courses_codes, strict=True))
        paired.sort(key=lambda x: x[0])
        indices = [idx for idx, _ in paired]
        return paired, indices

    def _resolve_error_mode(self, error_mode: ErrorMode | str) -> str:
        """Resolve and validate error_mode to a normalized string.

        Args:
            error_mode: ErrorMode enum or string ("abort", "skip", "retry").

        Returns:
            Normalized lowercase mode string.

        Raises:
            ValueError: If error_mode is not a valid mode.
        """
        if isinstance(error_mode, ErrorMode):
            mode = error_mode.value.lower()
        elif isinstance(error_mode, str):
            mode = error_mode.lower()
        else:
            raise ValueError(
                f"Invalid error_mode: {error_mode!r}. Must be an ErrorMode or one of: "
                f"{', '.join(sorted({'abort', 'skip', 'retry'}))}"
            )
        valid_modes = {"abort", "skip", "retry"}
        if mode not in valid_modes:
            raise ValueError(
                f"Invalid error_mode: {error_mode!r}. Must be one of: {', '.join(sorted(valid_modes))}"
            )
        return mode

    def _apply_course_codes(
        self,
        successes: list[sia_scraper_rust.CourseInfoModel],
        paired: list[tuple[int, str]],
        indices: list[int],
        failed_indices: set[int] | None = None,
    ) -> None:
        """Apply course codes to success models.

        Note: This method assumes successes are ordered consistently with
        indices (both sorted by course index). This contract is maintained
        by _prepare_scrape_indices sorting and Rust's result ordering.

        Args:
            successes: List of scraped course models to update in-place.
            paired: Sorted list of (index, code) tuples.
            indices: Sorted list of course indices.
            failed_indices: Set of failed indices (for skip/retry mode).

        Returns:
            None. The function mutates the CourseInfoModel objects in-place.

        Raises:
            No exceptions are raised by this method.

        Example:
            >>> # Abort mode - use indices order
            >>> self._apply_course_codes(successes, paired, indices)
            >>> successes[0].code
            'CODE1'

            >>> # Skip/retry mode - filter by failed_indices
            >>> self._apply_course_codes(successes, paired, indices, failed_indices={1})
            >>> successes[0].code  # index 0 succeeded
            'CODE1'
        """
        code_map = {idx: code for idx, code in paired if code}
        if code_map:
            # Determine which indices correspond to successes
            if failed_indices is None:
                success_indices = indices
            else:
                success_indices = [idx for idx in indices if idx not in failed_indices]

            if len(successes) != len(success_indices):
                logger.warning(
                    f"Success count mismatch: got {len(successes)} successes, "
                    f"expected {len(success_indices)} from indices"
                )

            for i, course in enumerate(successes):
                if i < len(success_indices) and success_indices[i] in code_map:
                    course.code = code_map[success_indices[i]]

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
            if course.get("code") == course_code:
                return i
        raise ValueError(f"Course code '{course_code}' not found")

    async def get_course_prereqs(
        self, course_index: int = 0, course_code: str = ""
    ) -> sia_scraper_rust.CoursePrereqsModel:
        """Get course prerequisites using zero-copy Rust scraping."""
        resolved_index = self._resolve_course_index(course_index, course_code)
        return await self._sia_session.scrape_course_prereqs(resolved_index)

    async def scrape_courses(
        self,
        courses_indices: list[int] | None = None,
        courses_codes: list[str] | None = None,
        error_mode: ErrorMode | str = ErrorMode.ABORT,
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
            progress_callback: Optional callback called once after batch completes
                with (total, total, successes, failures). Note: This is not
                incremental progress; it receives final totals only.
                Deprecated: Will be removed when real-time progress is exposed.

        Returns:
            List of CourseInfoModel in abort mode, or ScrapeResult in skip/retry mode.

        Raises:
            ValueError: If both courses_indices and courses_codes are provided
                but their lengths differ.
            ValueError: If error_mode is not a valid mode.
        """
        paired, indices = self._prepare_scrape_indices(courses_indices, courses_codes)
        mode = self._resolve_error_mode(error_mode)

        if mode == "abort":
            result = await self._sia_session.scrape_courses(
                indices,
                mode="abort",
                retries=0,
                delay=0,
            )
            self._apply_course_codes(result.successes, paired, indices)
            if progress_callback:
                completed = len(result.successes) + len(result.failures)
                progress_callback(
                    completed,
                    result.total(),
                    len(result.successes),
                    len(result.failures),
                )
            return result.successes

        delay_ms = int(retry_delay * 1000)
        rust_result = await self._sia_session.scrape_courses(
            indices,
            mode=mode,
            retries=max_retries if mode == "retry" else 0,
            delay=delay_ms,
        )

        failed_indices = {idx for idx, _ in rust_result.failures}
        self._apply_course_codes(rust_result.successes, paired, indices, failed_indices)

        if progress_callback:
            completed = len(rust_result.successes) + len(rust_result.failures)
            progress_callback(
                completed,
                rust_result.total(),
                len(rust_result.successes),
                len(rust_result.failures),
            )

        return ScrapeResult.create(
            successes=rust_result.successes,
            failures=rust_result.failures,
        )

    async def scrape_courses_parallel(
        self,
        courses_indices: list[int] | None = None,
        courses_codes: list[str] | None = None,
        max_concurrent: int = 5,
        error_mode: ErrorMode | str = ErrorMode.ABORT,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> ScrapeResult | list[sia_scraper_rust.CourseInfoModel]:
        """Batch scrape multiple courses concurrently with configurable parallelism.

        Delegates to Rust concurrent scraping for efficient parallel execution
        with configurable error handling modes.

        Args:
            courses_indices: List of course indices to scrape.
            courses_codes: List of course codes to scrape (resolved to indices).
            max_concurrent: Maximum number of concurrent scraping operations.
            error_mode: Error handling strategy - "abort", "skip", or "retry".
            max_retries: Maximum retry attempts per course (retry mode only).
            retry_delay: Base delay between retries in seconds (retry mode only).

        Returns:
            List of CourseInfoModel in abort mode, or ScrapeResult in skip/retry mode.

        Raises:
            ValueError: If both courses_indices and courses_codes are provided
                but their lengths differ.
            ValueError: If error_mode is not a valid mode.

        Example:
            >>> # Abort mode - returns list of CourseInfoModel
            >>> courses = await scraper.scrape_courses_parallel(
            ...     courses_indices=[0, 1, 2],
            ...     max_concurrent=5,
            ...     error_mode="abort"
            ... )
            >>> len(courses)
            3

            >>> # Skip mode - returns ScrapeResult
            >>> result = await scraper.scrape_courses_parallel(
            ...     courses_indices=[0, 1, 2],
            ...     max_concurrent=5,
            ...     error_mode="skip"
            ... )
            >>> result.success_rate()
            1.0
        """
        paired, indices = self._prepare_scrape_indices(courses_indices, courses_codes)
        mode = self._resolve_error_mode(error_mode)

        if mode == "abort":
            result = await self._sia_session.scrape_courses_parallel(
                indices,
                mode="abort",
                max_concurrent=max_concurrent,
                retries=0,
                delay=0,
            )
            self._apply_course_codes(result.successes, paired, indices)
            return result.successes

        delay_ms = int(retry_delay * 1000)
        rust_result = await self._sia_session.scrape_courses_parallel(
            indices,
            mode=mode,
            max_concurrent=max_concurrent,
            retries=max_retries if mode == "retry" else 0,
            delay=delay_ms,
        )

        failed_indices = {idx for idx, _ in rust_result.failures}
        self._apply_course_codes(rust_result.successes, paired, indices, failed_indices)

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
