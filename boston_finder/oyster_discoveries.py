"""
Discoveries log — venues surfaced from event feeds that aren't in OYSTER_VENUES.

Persisted to ~/boston_finder_oyster_discoveries.json. Keyed by normalized
venue name. Each record tracks sighting history + latest verify result.
"""

import json
import os
from datetime import datetime
from pathlib import Path

DISCOVERIES_FILE = os.path.expanduser("~/boston_finder_oyster_discoveries.json")


def load_all() -> dict:
    if not os.path.exists(DISCOVERIES_FILE):
        return {}
    try:
        return json.loads(Path(DISCOVERIES_FILE).read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data: dict) -> None:
    Path(DISCOVERIES_FILE).write_text(json.dumps(data, indent=2))


def upsert(
    venue_canonical: str,
    venue_normalized: str,
    event: dict,
    verify_result: dict,
    extraction_strategy: str,
) -> None:
    """
    Create or update the discovery record keyed by venue_normalized.
    """
    data = load_all()
    today = datetime.now().date().isoformat()

    existing = data.get(venue_normalized)
    if existing is None:
        data[venue_normalized] = {
            "name_canonical": venue_canonical,
            "name_normalized": venue_normalized,
            "aliases_seen": [venue_canonical],
            "neighborhood": "",
            "first_seen": today,
            "last_seen": today,
            "sources_seen": [event.get("source", "")],
            "event_urls": [event.get("url", "")],
            "event_titles": [event.get("name", "")],
            "extraction_strategy": extraction_strategy,
            "verify_result": verify_result,
            "event_count": 1,
            "status": "tentative",
        }
    else:
        existing["last_seen"] = today
        if event.get("source") and event["source"] not in existing["sources_seen"]:
            existing["sources_seen"].append(event["source"])
        if event.get("url") and event["url"] not in existing["event_urls"]:
            existing["event_urls"].append(event["url"])
        if event.get("name") and event["name"] not in existing["event_titles"]:
            existing["event_titles"].append(event["name"])
        if venue_canonical not in existing["aliases_seen"]:
            existing["aliases_seen"].append(venue_canonical)
        existing["verify_result"] = verify_result  # latest wins
        existing["event_count"] += 1

    _save(data)


def upsert_with_match(
    venue_canonical: str,
    venue_normalized: str,
    matched_key: str,
    event: dict,
    verify_result: dict,
    extraction_strategy: str,
) -> None:
    """
    Upsert where incoming name matched an existing record via normalization
    rules (prefix + neighborhood, alias map). Upgrades canonical to longer form.
    """
    data = load_all()
    existing = data.get(matched_key)
    today = datetime.now().date().isoformat()

    if existing is None:
        # fall through to a plain upsert under incoming normalized key
        upsert(venue_canonical, venue_normalized, event, verify_result, extraction_strategy)
        return

    # upgrade canonical if incoming is longer / more specific
    if len(venue_canonical) > len(existing["name_canonical"]):
        existing["aliases_seen"].append(existing["name_canonical"])
        existing["name_canonical"] = venue_canonical

    if venue_canonical not in existing["aliases_seen"]:
        existing["aliases_seen"].append(venue_canonical)

    existing["last_seen"] = today
    if event.get("source") and event["source"] not in existing["sources_seen"]:
        existing["sources_seen"].append(event["source"])
    if event.get("url") and event["url"] not in existing["event_urls"]:
        existing["event_urls"].append(event["url"])
    if event.get("name") and event["name"] not in existing["event_titles"]:
        existing["event_titles"].append(event["name"])
    existing["verify_result"] = verify_result
    existing["event_count"] += 1

    _save(data)
