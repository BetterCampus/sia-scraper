"""Local import shim for the compiled Rust extension module.

This package expects the compiled binary at:
`src/sia_scraper_rust/sia_scraper_rust<EXT_SUFFIX>`.
Use `python scripts/sync_rust_extension.py --build --release` to build/copy it.
"""

from importlib import import_module

_native = import_module(".sia_scraper_rust", __name__)

__all__ = getattr(_native, "__all__", [name for name in dir(_native) if not name.startswith("_")])

for _name in __all__:
    globals()[_name] = getattr(_native, _name)

__doc__ = getattr(_native, "__doc__", __doc__)
