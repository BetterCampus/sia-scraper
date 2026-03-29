"""Debug logging utilities for Oracle ADF state investigation."""

import os

DEBUG_MODE: bool = os.environ.get("SIA_DEBUG", "0") == "1"


def debug_log(message: str, data: str | dict | None = None) -> None:
    """Log debug messages when DEBUG_MODE is enabled.

    ## Args
        message: Debug message describing the event.
        data: Optional additional data to log (ViewState, DELTAS, etc.).
    """
    if not DEBUG_MODE:
        return

    prefix = "[ADF-DEBUG]"
    if data:
        print(f"{prefix} {message}")
        if isinstance(data, dict):
            for key, value in data.items():
                value_str = str(value)
                if len(value_str) > 200:
                    value_str = value_str[:200] + "..."
                print(f"  {key}: {value_str}")
        else:
            data_str = str(data)
            print(f"  Data: {data_str[:200]}..." if len(data_str) > 200 else f"  Data: {data}")
    else:
        print(f"{prefix} {message}")
