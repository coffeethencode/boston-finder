"""
Personal venue ratings — your verdicts after actually going somewhere.
Stored in ~/boston_venue_ratings.json

Use the CLI:
    python3 rate_venue.py "Row 34" 5 "Perfect Duxbury, great scene"
    python3 rate_venue.py "Loco Taqueria" skip "Not my scene"
"""

import json
import os
from datetime import datetime

RATINGS_FILE = os.path.expanduser("~/boston_venue_ratings.json")


def load() -> dict:
    if not os.path.exists(RATINGS_FILE):
        return {}
    with open(RATINGS_FILE) as f:
        return json.load(f)


def save(data: dict):
    with open(RATINGS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get(venue_name: str) -> dict | None:
    """Return your rating for a venue, or None if unrated."""
    data = load()
    vl = venue_name.lower().strip()
    # 1. exact match first
    for key, val in data.items():
        if key.lower().strip() == vl:
            return val
    # 2. fuzzy: only match if the longer string contains the shorter one AND
    #    the shorter one is at least 80% of the longer one's length (avoids
    #    "Legal Sea Foods" swallowing "Legal Sea Foods Long Wharf")
    for key, val in data.items():
        kl = key.lower().strip()
        shorter, longer = (kl, vl) if len(kl) <= len(vl) else (vl, kl)
        if shorter in longer and len(shorter) / len(longer) >= 0.8:
            return val
    return None


def rate(venue_name: str, rating: int | str, note: str = ""):
    """
    Save a rating for a venue.
    rating: 1-5 int, or "skip" to flag as not worth going back
    """
    data = load()
    data[venue_name] = {
        "rating": rating,
        "note": note,
        "date": datetime.now().strftime("%Y-%m-%d"),
    }
    save(data)
    print(f"Saved: {venue_name} → {rating}" + (f" ({note})" if note else ""))


def score(venue_name: str) -> float:
    """Return 0-10 personal score, or 5 (neutral) if unrated."""
    r = get(venue_name)
    if r is None:
        return 5.0  # neutral — haven't been
    if r["rating"] == "skip":
        return 0.0  # hard filter
    return float(r["rating"]) * 2  # 1-5 → 2-10


def is_skipped(venue_name: str) -> bool:
    r = get(venue_name)
    return r is not None and r.get("rating") == "skip"


def summary() -> str:
    data = load()
    if not data:
        return "No venues rated yet."
    lines = []
    for name, r in sorted(data.items()):
        rating = r["rating"]
        note = f" — {r['note']}" if r.get("note") else ""
        lines.append(f"  {name}: {rating}{note}")
    return "\n".join(lines)
