"""
Focus-Guard Client Utilities
Domain sanitization and time formatting helpers.
"""

import re
from typing import Optional
from urllib.parse import urlparse


def sanitize_domain(raw_input: str) -> Optional[str]:
    """Cleans up URLs and strings into a valid lowercase domain name."""
    raw = raw_input.strip().lower()
    if not raw:
        return None

    if not raw.startswith("http://") and not raw.startswith("https://"):
        raw = "http://" + raw

    try:
        parsed = urlparse(raw)
        host = parsed.netloc or parsed.path
        host = host.split(":")[0]
        if host.startswith("www."):
            host = host[4:]
        if re.match(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", host):
            return host
    except Exception:
        pass
    return None


def format_human_time(seconds: int) -> str:
    """Formats remaining seconds into natural human time."""
    if seconds <= 0:
        return "0s"
    hours = seconds // 3600
    mins = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        if mins > 0:
            return f"{hours}h {mins}m {secs}s"
        return f"{hours}h {secs}s"
    elif mins > 0:
        return f"{mins}m {secs}s"
    else:
        return f"{secs}s"
