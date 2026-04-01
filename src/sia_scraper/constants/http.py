"""SIA System HTTP Configuration.

This module defines HTTP-related constants for connecting to SIA's Oracle ADF backend.

IMPORTANT: These constants must remain synchronized with Rust constants in
`rust/src/constants.rs`. Any changes to URLs, headers, or ADF IDs should be
reflected in both locations. A CI check (`.github/workflows/constants-sync-check.yml`)
verifies this synchronization.

See also:
    - rust/src/constants.rs: Centralized Rust constants
    - scripts/check_constants_sync.py: Local validation script
"""

import re

DEFAULT_TIMEOUT: int = 15

SIA_BASE_URL: str = "https://sia.unal.edu.co/Catalogo/facespublico/public/servicioPublico.jsf"

ADF_ADS_PAGE_ID: str = "1"

SIA_HEADERS: dict[str, str] = {
    "authority": "sia.unal.edu.co",
    "accept": "*/*",
    "accept-language": "es-419,es;q=0.9,en;q=0.8",
    "adf-ads-page-id": ADF_ADS_PAGE_ID,
    "adf-rich-message": "true",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "origin": "https://sia.unal.edu.co",
    "referer": SIA_BASE_URL,
    "sec-ch-ua": '"Google Chrome";v="107", "Chromium";v="107", "Not=A?Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36",
}

VIEW_STATE_REGEX: re.Pattern[bytes] = re.compile(
    b'<input type="hidden" name="javax.faces.ViewState" value="(.*?)">'
)
