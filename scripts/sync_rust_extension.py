"""Build and sync the Rust extension into the editable src tree.

This script keeps local editable installs stable by placing the compiled extension
at `src/sia_scraper_rust/sia_scraper_rust<EXT_SUFFIX>`, so `pytest` and regular
imports work without `PYTHONPATH` hacks or environment-specific symlinks.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path


def _run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=cwd, check=True)


def _source_binary(target_dir: Path) -> Path:
    candidates = [
        target_dir / "libsia_scraper_rust.so",
        target_dir / "sia_scraper_rust.dll",
        target_dir / "libsia_scraper_rust.dylib",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "Could not find compiled Rust extension. Expected one of: "
        + ", ".join(str(path) for path in candidates)
    )


def _dest_binary(dest_dir: Path) -> Path:
    ext_suffix = sysconfig.get_config_var("EXT_SUFFIX")
    if not ext_suffix:
        raise RuntimeError("Could not resolve Python EXT_SUFFIX")
    return dest_dir / f"sia_scraper_rust{ext_suffix}"


def _verify_import(project_root: Path) -> None:
    verify_code = (
        "import sys;"
        f"sys.path.insert(0, {str(project_root / 'src')!r});"
        "import sia_scraper;"
        "import sia_scraper_rust;"
        "print('Rust extension import OK')"
    )
    _run([sys.executable, "-c", verify_code], cwd=project_root)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync Rust extension into src/sia_scraper_rust")
    parser.add_argument("--build", action="store_true", help="Run cargo build before syncing")
    parser.add_argument("--release", action="store_true", help="Use release build profile")
    parser.add_argument("--verify", action="store_true", help="Verify Python imports after sync")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    profile = "release" if args.release else "debug"

    if args.build:
        cmd = ["cargo", "build"]
        if args.release:
            cmd.append("--release")
        _run(cmd, cwd=project_root)

    target_dir = project_root / "target" / profile
    source = _source_binary(target_dir)

    dest_dir = project_root / "src" / "sia_scraper_rust"
    dest_dir.mkdir(parents=True, exist_ok=True)
    destination = _dest_binary(dest_dir)

    shutil.copy2(source, destination)
    print(f"Copied Rust extension to: {destination}")

    if args.verify:
        _verify_import(project_root)


if __name__ == "__main__":
    main()
