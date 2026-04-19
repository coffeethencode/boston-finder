import json
from datetime import datetime

from boston_finder import oyster_discoveries as od


def test_upsert_new_venue(tmp_path, monkeypatch):
    monkeypatch.setattr(od, "DISCOVERIES_FILE", str(tmp_path / "d.json"))

    od.upsert(
        venue_canonical="Tradesman Charlestown",
        venue_normalized="tradesman charlestown",
        event={"name": "DOLLAR OYSTERS BUCK A SHUCK TRADESMAN CHARLESTOWN",
               "url": "https://bc.example/1",
               "source": "thebostoncalendar.com"},
        verify_result={"status": "✅ verified", "price": "$1"},
        extraction_strategy="trailing_caps",
    )

    records = od.load_all()
    assert "tradesman charlestown" in records
    rec = records["tradesman charlestown"]
    assert rec["name_canonical"] == "Tradesman Charlestown"
    assert rec["event_count"] == 1
    assert rec["first_seen"] == rec["last_seen"]
    assert rec["status"] == "tentative"


def test_upsert_existing_venue_bumps_count(tmp_path, monkeypatch):
    monkeypatch.setattr(od, "DISCOVERIES_FILE", str(tmp_path / "d.json"))

    for i in range(3):
        od.upsert(
            venue_canonical="Tradesman Charlestown",
            venue_normalized="tradesman charlestown",
            event={"name": f"event {i}", "url": f"https://bc.example/{i}", "source": "x"},
            verify_result={"status": "✅ verified"},
            extraction_strategy="trailing_caps",
        )

    rec = od.load_all()["tradesman charlestown"]
    assert rec["event_count"] == 3
    assert len(rec["event_urls"]) == 3


def test_upgrade_canonical_on_longer_form(tmp_path, monkeypatch):
    """If the first sighting was 'Tradesman' and the second is
    'Tradesman Charlestown', upgrade the canonical name."""
    monkeypatch.setattr(od, "DISCOVERIES_FILE", str(tmp_path / "d.json"))

    od.upsert("Tradesman", "tradesman", {"url": "u1", "name": "n1"}, {}, "trailing_caps")
    # second sighting with longer canonical matches the shorter record and upgrades
    od.upsert_with_match("Tradesman Charlestown", "tradesman charlestown", "tradesman",
                         {"url": "u2", "name": "n2"}, {}, "trailing_caps")

    records = od.load_all()
    rec = records["tradesman"]  # keyed by original normalized form
    assert rec["name_canonical"] == "Tradesman Charlestown"
    assert "Tradesman" in rec["aliases_seen"]


def test_load_all_empty_file(tmp_path, monkeypatch):
    monkeypatch.setattr(od, "DISCOVERIES_FILE", str(tmp_path / "nonexistent.json"))
    assert od.load_all() == {}
