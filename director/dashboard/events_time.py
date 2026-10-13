"""One clock for decision timestamps (UTC, ISO 8601 with milliseconds, so ordering within a second is kept)."""
from datetime import datetime, timezone


def now() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
