"""Capture real SIA responses and store them as sanitized test fixtures.

This script is temporary tooling intended to refresh fixtures used by tests.
It uses the public `SiaScraper` API and stores responses under `tests/fixtures/`.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover - runtime dependency message
    raise SystemExit(
        "PyYAML is required to run this script. Install dev dependencies with: "
        "pip install -e '.[dev]'"
    ) from exc

from sia_scraper import SiaScraper
from sia_scraper.constants import SIA_BASE_URL
from sia_scraper.core import SiaSessionException


@dataclass(frozen=True)
class CaptureConfig:
    """Configuration values loaded from YAML file."""

    career_code: str
    num_regular_courses: int
    num_elective_courses: int
    timeout: int
    include_electives: bool
    sanitization_enabled: bool
    sanitize_viewstate: bool
    sanitize_window_id: bool
    sanitize_page_id: bool
    sanitize_cookies: bool
    capture_timeout_error: bool
    include_timestamp: bool
    keep_only_latest: bool


def load_config(config_path: Path) -> CaptureConfig:
    """Load and validate capture config from YAML."""
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Invalid YAML format: expected a top-level mapping")

    career = _as_dict(raw.get("career"), "career")
    capture = _as_dict(raw.get("capture"), "capture")
    sanitization = _as_dict(raw.get("sanitization"), "sanitization")
    error_scenarios = _as_dict(raw.get("error_scenarios"), "error_scenarios")
    output = _as_dict(raw.get("output"), "output")

    return CaptureConfig(
        career_code=str(career.get("code", "0-2-8-3")),
        num_regular_courses=int(capture.get("num_regular_courses", 5)),
        num_elective_courses=int(capture.get("num_elective_courses", 2)),
        timeout=int(capture.get("timeout", 30)),
        include_electives=bool(capture.get("include_electives", True)),
        sanitization_enabled=bool(sanitization.get("enabled", True)),
        sanitize_viewstate=bool(sanitization.get("sanitize_viewstate", True)),
        sanitize_window_id=bool(sanitization.get("sanitize_window_id", True)),
        sanitize_page_id=bool(sanitization.get("sanitize_page_id", False)),
        sanitize_cookies=bool(sanitization.get("sanitize_cookies", True)),
        capture_timeout_error=bool(error_scenarios.get("capture_timeout", True)),
        include_timestamp=bool(output.get("include_timestamp", True)),
        keep_only_latest=bool(output.get("keep_only_latest", True)),
    )


def _as_dict(value: Any, section_name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"Invalid YAML: '{section_name}' must be a mapping")
    return value


def ensure_directories(fixtures_root: Path) -> None:
    """Ensure fixtures directory structure exists."""
    (fixtures_root / "html").mkdir(parents=True, exist_ok=True)
    (fixtures_root / "xml").mkdir(parents=True, exist_ok=True)
    (fixtures_root / "json").mkdir(parents=True, exist_ok=True)


def build_filename(base_name: str, extension: str, with_date: bool) -> str:
    """Build fixture file name with optional date suffix."""
    if with_date:
        return f"{base_name}_{date.today().isoformat()}.{extension}"
    return f"{base_name}.{extension}"


def clean_old_versions(target_dir: Path, base_name: str, extension: str) -> None:
    """Delete older versions for a logical fixture base name."""
    pattern = f"{base_name}_*.{extension}"
    for old_file in target_dir.glob(pattern):
        old_file.unlink(missing_ok=True)


def write_fixture(
    target_dir: Path,
    base_name: str,
    extension: str,
    content: str,
    include_timestamp: bool,
    keep_only_latest: bool,
) -> Path:
    """Write fixture content and optionally remove old versions."""
    if keep_only_latest and include_timestamp:
        clean_old_versions(target_dir, base_name, extension)

    file_name = build_filename(base_name, extension, include_timestamp)
    file_path = target_dir / file_name
    file_path.write_text(content, encoding="utf-8")
    return file_path


def sanitize_text(content: str, replacements: dict[str, str], enabled: bool) -> str:
    """Sanitize sensitive values in text content."""
    if not enabled:
        return content

    sanitized = content
    for original, placeholder in replacements.items():
        if original:
            sanitized = sanitized.replace(original, placeholder)

    sanitized = re.sub(
        r'(name=["\']javax\.faces\.ViewState["\']\s+value=["\'])[^"\']+(["\'])',
        r"\1SANITIZED_VIEWSTATE_TOKEN_12345\2",
        sanitized,
    )
    sanitized = re.sub(
        r'(<update\s+id=["\'].*?ViewState.*?["\']><!\[CDATA\[).*?(\]\]></update>)',
        r"\1SANITIZED_VIEWSTATE_TOKEN_12345\2",
        sanitized,
        flags=re.DOTALL,
    )
    sanitized = re.sub(
        r"(<ViewState>).*?(</ViewState>)",
        r"\1SANITIZED_VIEWSTATE_TOKEN_12345\2",
        sanitized,
        flags=re.DOTALL,
    )

    return sanitized


def sanitize_json_data(value: Any, replacements: dict[str, str], enabled: bool) -> Any:
    """Recursively sanitize JSON-serializable data."""
    if not enabled:
        return value

    if isinstance(value, dict):
        return {k: sanitize_json_data(v, replacements, enabled) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize_json_data(v, replacements, enabled) for v in value]
    if isinstance(value, str):
        sanitized = value
        for original, placeholder in replacements.items():
            if original:
                sanitized = sanitized.replace(original, placeholder)
        return sanitized
    return value


def extract_replacements(scraper: SiaScraper, config: CaptureConfig) -> dict[str, str]:
    """Extract sensitive runtime values and map them to placeholders."""
    session = scraper.sia_session
    session_data = scraper.get_session_data()

    replacements: dict[str, str] = {}

    if config.sanitize_viewstate and session._view_state:
        replacements[session._view_state] = "SANITIZED_VIEWSTATE_TOKEN_12345"
    if config.sanitize_window_id and session._window_id:
        replacements[session._window_id] = "SANITIZED_WINDOW_ID_67890"
    if config.sanitize_page_id and session._page_id:
        replacements[session._page_id] = "SANITIZED_PAGE_ID_000"

    if config.sanitize_cookies:
        cookies = session_data.get("session_cookies", {})
        if isinstance(cookies, dict):
            for cookie_name, cookie_value in cookies.items():
                if isinstance(cookie_value, str) and cookie_value:
                    replacements[cookie_value] = f"SANITIZED_{cookie_name}_VALUE"

    return replacements


def save_json_fixture(
    target_dir: Path,
    base_name: str,
    payload: Any,
    include_timestamp: bool,
    keep_only_latest: bool,
) -> Path:
    """Save JSON fixture with stable formatting."""
    content = json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True)
    return write_fixture(
        target_dir=target_dir,
        base_name=base_name,
        extension="json",
        content=content + "\n",
        include_timestamp=include_timestamp,
        keep_only_latest=keep_only_latest,
    )


def generate_fixtures_readme(
    fixtures_root: Path,
    config: CaptureConfig,
    generated_files: list[Path],
) -> None:
    """Generate metadata README under tests/fixtures/."""
    now = datetime.now().isoformat(timespec="seconds")
    rel_files = sorted(
        str(path.relative_to(fixtures_root.parent.parent)) for path in generated_files
    )

    lines = [
        "# SIA Test Fixtures",
        "",
        "This directory contains sanitized fixture responses captured from live SIA.",
        "",
        "## Capture Metadata",
        f"- Captured at: {now}",
        f"- SIA URL: {SIA_BASE_URL}",
        f"- Career code: {config.career_code}",
        f"- Regular courses requested: {config.num_regular_courses}",
        f"- Electives requested: {config.num_elective_courses if config.include_electives else 0}",
        f"- Sanitization enabled: {config.sanitization_enabled}",
        f"- Keep only latest: {config.keep_only_latest}",
        "",
        "## Generated Files",
    ]

    lines.extend(f"- `{path}`" for path in rel_files)
    lines.extend(
        [
            "",
            "## Notes",
            "- Tokens and cookies are sanitized when enabled in config.",
            "- Date suffix format is `YYYY-MM-DD`.",
            "- Re-run the capture script to refresh fixtures after SIA changes.",
        ]
    )

    (fixtures_root / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def capture_timeout_error(config: CaptureConfig, replacements: dict[str, str]) -> str:
    """Capture timeout exception information as an error fixture."""
    timeout_scraper = SiaScraper(timeout=1, init_session=False)
    try:
        timeout_scraper.create_session()
        timeout_scraper.sia_session.timeout = 0
        timeout_scraper.sia_session.keep_alive()
        return "<html><body>No timeout error captured.</body></html>"
    except Exception as exc:  # pragma: no cover - depends on runtime network
        html = (
            "<html><body>"
            "<h1>SIA Timeout Error</h1>"
            f"<p>{type(exc).__name__}</p>"
            f"<pre>{exc}</pre>"
            "</body></html>"
        )
        return sanitize_text(html, replacements, config.sanitization_enabled)
    finally:
        try:
            timeout_scraper.close_session()
        except Exception:
            pass


def capture_adf_error_response(config: CaptureConfig, replacements: dict[str, str]) -> str:
    """Capture a deterministic library-level error response payload."""
    error_scraper = SiaScraper(timeout=config.timeout, init_session=False)
    try:
        error_scraper.create_session()
        error_scraper.get_course_info(course_index=0)
        error_xml = "<error><type>NoError</type><message>No error captured.</message></error>"
    except Exception as exc:  # pragma: no cover - depends on runtime behavior
        error_xml = (
            "<error>"
            f"<type>{type(exc).__name__}</type>"
            f"<message>{exc}</message>"
            "<context>precondition_violation</context>"
            "</error>"
        )
    finally:
        try:
            error_scraper.close_session()
        except Exception:
            pass

    return sanitize_text(error_xml, replacements, config.sanitization_enabled)


def main() -> int:
    """Execute fixture capture workflow."""
    repo_root = Path(__file__).resolve().parent.parent
    config_path = repo_root / "scripts" / "capture_config.yaml"
    fixtures_root = repo_root / "tests" / "fixtures"

    if not config_path.exists():
        print(f"Config file not found: {config_path}", file=sys.stderr)
        return 1

    config = load_config(config_path)
    ensure_directories(fixtures_root)

    generated_files: list[Path] = []
    scraper = SiaScraper(timeout=config.timeout, init_session=False)

    try:
        print("[1/6] Creating SIA session...")
        scraper.create_session()

        replacements = extract_replacements(scraper, config)

        print("[2/6] Capturing initial page...")
        initial_bytes = scraper.sia_session.main_page_html or b""
        initial_html = initial_bytes.decode("utf-8", errors="ignore")
        initial_html = sanitize_text(initial_html, replacements, config.sanitization_enabled)
        generated_files.append(
            write_fixture(
                target_dir=fixtures_root / "html",
                base_name="initial_page",
                extension="html",
                content=initial_html,
                include_timestamp=config.include_timestamp,
                keep_only_latest=config.keep_only_latest,
            )
        )

        print("[3/6] Capturing regular courses flow...")
        scraper.set_career(config.career_code, electives=False)
        replacements = extract_replacements(scraper, config)

        regular_page_xml = scraper.sia_session.get_current_xml()
        regular_page_xml = sanitize_text(
            regular_page_xml, replacements, config.sanitization_enabled
        )
        generated_files.append(
            write_fixture(
                target_dir=fixtures_root / "html",
                base_name="career_page_regular",
                extension="html",
                content=regular_page_xml,
                include_timestamp=config.include_timestamp,
                keep_only_latest=config.keep_only_latest,
            )
        )
        generated_files.append(
            write_fixture(
                target_dir=fixtures_root / "xml",
                base_name="adf_dropdown_response",
                extension="xml",
                content=regular_page_xml,
                include_timestamp=config.include_timestamp,
                keep_only_latest=config.keep_only_latest,
            )
        )

        regular_courses = scraper.course_list
        generated_files.append(
            save_json_fixture(
                target_dir=fixtures_root / "json",
                base_name="course_list_regular",
                payload=regular_courses,
                include_timestamp=config.include_timestamp,
                keep_only_latest=config.keep_only_latest,
            )
        )

        regular_capture_count = min(config.num_regular_courses, len(regular_courses))
        for idx in range(regular_capture_count):
            xml = scraper.sia_session.get_course_xml(idx)
            xml = sanitize_text(xml, replacements, config.sanitization_enabled)
            generated_files.append(
                write_fixture(
                    target_dir=fixtures_root / "xml",
                    base_name=f"course_detail_{idx}",
                    extension="xml",
                    content=xml,
                    include_timestamp=config.include_timestamp,
                    keep_only_latest=config.keep_only_latest,
                )
            )

        prereqs_xml: str | None = None
        for idx in range(regular_capture_count):
            try:
                prereqs_xml = scraper.sia_session.get_course_xml(idx)
                scraper.get_course_prereqs(course_index=idx)
                break
            except ValueError:
                continue

        if prereqs_xml is not None:
            prereqs_xml = sanitize_text(prereqs_xml, replacements, config.sanitization_enabled)
            generated_files.append(
                write_fixture(
                    target_dir=fixtures_root / "xml",
                    base_name="course_prereqs",
                    extension="xml",
                    content=prereqs_xml,
                    include_timestamp=config.include_timestamp,
                    keep_only_latest=config.keep_only_latest,
                )
            )

        if config.include_electives:
            print("[4/6] Capturing electives flow...")
            elective_scraper = SiaScraper(timeout=config.timeout, init_session=False)
            try:
                elective_scraper.create_session()
                elective_scraper.set_career(config.career_code, electives=True)
                elective_replacements = extract_replacements(elective_scraper, config)

                electives_page_xml = elective_scraper.sia_session.get_current_xml()
                electives_page_xml = sanitize_text(
                    electives_page_xml, elective_replacements, config.sanitization_enabled
                )
                generated_files.append(
                    write_fixture(
                        target_dir=fixtures_root / "html",
                        base_name="career_page_electives",
                        extension="html",
                        content=electives_page_xml,
                        include_timestamp=config.include_timestamp,
                        keep_only_latest=config.keep_only_latest,
                    )
                )

                elective_courses = elective_scraper.course_list
                generated_files.append(
                    save_json_fixture(
                        target_dir=fixtures_root / "json",
                        base_name="course_list_electives",
                        payload=elective_courses,
                        include_timestamp=config.include_timestamp,
                        keep_only_latest=config.keep_only_latest,
                    )
                )

                elective_capture_count = min(config.num_elective_courses, len(elective_courses))
                for idx in range(elective_capture_count):
                    xml = elective_scraper.sia_session.get_course_xml(idx)
                    xml = sanitize_text(xml, elective_replacements, config.sanitization_enabled)
                    generated_files.append(
                        write_fixture(
                            target_dir=fixtures_root / "xml",
                            base_name=f"course_elective_{idx}",
                            extension="xml",
                            content=xml,
                            include_timestamp=config.include_timestamp,
                            keep_only_latest=config.keep_only_latest,
                        )
                    )
            finally:
                try:
                    elective_scraper.close_session()
                except Exception:
                    pass

        error_xml = capture_adf_error_response(config, replacements)
        generated_files.append(
            write_fixture(
                target_dir=fixtures_root / "xml",
                base_name="adf_error_response",
                extension="xml",
                content=error_xml,
                include_timestamp=config.include_timestamp,
                keep_only_latest=config.keep_only_latest,
            )
        )

        print("[5/6] Saving session metadata...")
        session_data = scraper.get_session_data()
        session_data = sanitize_json_data(session_data, replacements, config.sanitization_enabled)
        generated_files.append(
            save_json_fixture(
                target_dir=fixtures_root / "json",
                base_name="session_data",
                payload=session_data,
                include_timestamp=config.include_timestamp,
                keep_only_latest=config.keep_only_latest,
            )
        )

        if config.capture_timeout_error:
            timeout_html = capture_timeout_error(config, replacements)
            generated_files.append(
                write_fixture(
                    target_dir=fixtures_root / "html",
                    base_name="session_timeout",
                    extension="html",
                    content=timeout_html,
                    include_timestamp=config.include_timestamp,
                    keep_only_latest=config.keep_only_latest,
                )
            )

        print("[6/6] Writing fixtures README...")
        generate_fixtures_readme(fixtures_root, config, generated_files)

        print("Capture completed successfully.")
        for path in generated_files:
            print(f"- {path.relative_to(repo_root)}")
        return 0

    except (SiaSessionException, ValueError, KeyError) as exc:
        print(f"Capture failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        try:
            scraper.close_session()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
