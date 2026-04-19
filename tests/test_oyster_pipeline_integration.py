"""
End-to-end fixtures:
- Park 9 Dog Bar 'Everett Happy Hour' → filter drops it, never reaches verify.
- Tradesman Charlestown oyster event → filter passes, venue extracted from
  title, verify runs, discovery logged.
"""

from boston_finder import event_store, oyster_filter, venue_extractor, oyster_discoveries


PARK_9_EVENT = {
    "source": "do617:food-drink",
    "name": "Everett Happy Hour",
    "description": "",
    "url": "https://do617.com/events/2026/4/24/everett-happy-hour-tickets",
    "start": "2026-04-24T17:00",
    "venue": "Park 9 Dog Bar",
}

TRADESMAN_EVENT = {
    "source": "thebostoncalendar.com",
    "name": "DOLLAR OYSTERS BUCK A SHUCK TRADESMAN CHARLESTOWN",
    "description": "",
    "url": "https://www.thebostoncalendar.com/events/dollar-oysters-buck-a-shuck-tradesman-charlestown--30",
    "start": "",
    "venue": "",
}


def test_park_9_filtered_out():
    assert oyster_filter.is_oyster_candidate(PARK_9_EVENT) is False


def test_tradesman_passes_filter():
    assert oyster_filter.is_oyster_candidate(TRADESMAN_EVENT) is True


def test_tradesman_venue_extracted_from_title():
    venue = venue_extractor.extract_venue(TRADESMAN_EVENT, use_llm_fallback=False)
    assert venue == "Tradesman Charlestown"


def test_event_store_ignores_oyster_deals_cache_key(tmp_path, monkeypatch):
    """Polluted cache keys (like oyster_deals_*) would not end up in the event store
    because write_events writes a list, not the heterogeneous cache. Verify the
    read side refuses to treat non-event payloads as events."""
    import json
    bad_file = tmp_path / "events.json"
    # payload shaped like the main cache — missing 'events' key
    bad_file.write_text(json.dumps({"oyster_deals_brian": [{"name": "x"}]}))
    monkeypatch.setattr(event_store, "EVENTS_FILE", str(bad_file))

    import pytest
    with pytest.raises(event_store.EventStoreError, match="schema"):
        event_store.read_events()


def test_alias_collision_tradesman_then_longer(tmp_path, monkeypatch):
    """Ingest 'Tradesman' alone first; later 'Tradesman Charlestown' upgrades canonical."""
    monkeypatch.setattr(oyster_discoveries, "DISCOVERIES_FILE", str(tmp_path / "d.json"))

    oyster_discoveries.upsert(
        "Tradesman", "tradesman",
        {"url": "u1", "name": "n1", "source": "s1"},
        {"status": "⚠️ Unverified", "price": None},
        "trailing_caps",
    )
    # second ingest — incoming matches via prefix+neighborhood rule
    matched = venue_extractor.match_existing(
        "Tradesman Charlestown", list(oyster_discoveries.load_all().keys())
    )
    assert matched == "tradesman"

    oyster_discoveries.upsert_with_match(
        "Tradesman Charlestown", "tradesman charlestown", matched,
        {"url": "u2", "name": "n2", "source": "s2"},
        {"status": "✅ verified", "price": "$1"},
        "trailing_caps",
    )

    rec = oyster_discoveries.load_all()["tradesman"]
    assert rec["name_canonical"] == "Tradesman Charlestown"
    assert "Tradesman" in rec["aliases_seen"]
    assert rec["event_count"] == 2
