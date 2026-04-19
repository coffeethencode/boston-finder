"""
Daily event persistence layer.

boston_events.py writes the deduped event list here after fetch_shared().
oyster_deals.py (and any other weekly consumer) reads from here to avoid
re-scraping the same sources.

Single file, overwritten daily. No TTL on write — staleness is enforced
on read via read_events(max_age_hours=...).
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

EVENTS_FILE = os.path.expanduser("~/boston_finder_events.json")


class EventStoreError(Exception):
    """Base class for event store read problems."""


class StaleEventsError(EventStoreError):
    """Raised when the on-disk file is older than the caller's max age."""


def write_events(events: list[dict], fetched_at: datetime) -> None:
    """Persist the deduped event list. Overwrites any previous write."""
    payload = {
        "fetched_at": fetched_at.isoformat(),
        "event_count": len(events),
        "events": events,
    }
    Path(EVENTS_FILE).write_text(json.dumps(payload, indent=2))


def read_events(max_age_hours: int = 48) -> list[dict]:
    """
    Return the events written by the most recent write_events() call.

    Raises EventStoreError if the file is missing or malformed.
    Raises StaleEventsError if the file is older than max_age_hours.
    """
    if not os.path.exists(EVENTS_FILE):
        raise EventStoreError(f"event store file not found at {EVENTS_FILE}")

    try:
        payload = json.loads(Path(EVENTS_FILE).read_text())
    except json.JSONDecodeError as ex:
        raise EventStoreError(f"event store file corrupt: {ex}") from ex

    if "events" not in payload or "fetched_at" not in payload:
        raise EventStoreError("event store file schema missing required keys")

    fetched_at = datetime.fromisoformat(payload["fetched_at"])
    if datetime.now() - fetched_at > timedelta(hours=max_age_hours):
        raise StaleEventsError(
            f"events are {(datetime.now() - fetched_at).total_seconds() / 3600:.1f}h old, "
            f"exceeds max_age_hours={max_age_hours}"
        )

    return payload["events"]
