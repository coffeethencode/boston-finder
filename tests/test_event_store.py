import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from boston_finder import event_store


def test_write_and_read_roundtrip(tmp_path, monkeypatch):
    events_file = tmp_path / "events.json"
    monkeypatch.setattr(event_store, "EVENTS_FILE", str(events_file))

    events = [
        {"name": "Event A", "url": "https://a.example"},
        {"name": "Event B", "url": "https://b.example"},
    ]
    event_store.write_events(events, fetched_at=datetime.now())

    loaded = event_store.read_events()
    assert loaded == events


def test_stale_events_raises(tmp_path, monkeypatch):
    events_file = tmp_path / "events.json"
    monkeypatch.setattr(event_store, "EVENTS_FILE", str(events_file))

    past = datetime.now() - timedelta(hours=72)
    event_store.write_events([{"name": "X"}], fetched_at=past)

    import pytest
    with pytest.raises(event_store.StaleEventsError):
        event_store.read_events(max_age_hours=48)


def test_missing_file_raises_clear_error(tmp_path, monkeypatch):
    events_file = tmp_path / "nonexistent.json"
    monkeypatch.setattr(event_store, "EVENTS_FILE", str(events_file))

    import pytest
    with pytest.raises(event_store.EventStoreError, match="not found"):
        event_store.read_events()


def test_malformed_file_raises_clear_error(tmp_path, monkeypatch):
    events_file = tmp_path / "events.json"
    events_file.write_text('{"wrong_key": []}')
    monkeypatch.setattr(event_store, "EVENTS_FILE", str(events_file))

    import pytest
    with pytest.raises(event_store.EventStoreError, match="schema"):
        event_store.read_events()
