"""Time helpers. All graph times are integer epoch milliseconds; open intervals use OPEN."""

import time
from datetime import UTC, datetime

from core.config import get_settings

OPEN = 253402300799000  # 9999-12-31T23:59:59Z
DAY_MS = 86_400_000


def now_ms() -> int:
    """Current time, or the pinned demo clock when DEMO_NOW is set."""
    pinned = get_settings().demo_now_ms
    return pinned if pinned is not None else int(time.time() * 1000)


def to_ms(value: str | datetime) -> int:
    dt = datetime.fromisoformat(value) if isinstance(value, str) else value
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return int(dt.timestamp() * 1000)


def iso(ms: int | None) -> str | None:
    if ms is None or ms >= OPEN:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=UTC).isoformat()
