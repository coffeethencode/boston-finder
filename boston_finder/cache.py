"""
Simple JSON cache with TTL (time-to-live).
Used so slow-changing data (oyster deals, venue lists) isn't re-fetched daily.
Also stores scored events so we never re-score the same URL twice.
"""

import json
import os
from datetime import datetime, timedelta

CACHE_FILE       = os.path.expanduser("~/boston_finder_cache.json")
SCORED_CACHE_FILE = os.path.expanduser("~/boston_finder_scored.json")
SCORED_TTL_DAYS  = 14  # forget scored events after 14 days


# ── Scored events cache ────────────────────────────────────────────────────────

def _load_scored() -> dict:
    if not os.path.exists(SCORED_CACHE_FILE):
        return {}
    with open(SCORED_CACHE_FILE) as f:
        return json.load(f)


def _save_scored(data: dict):
    with open(SCORED_CACHE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_scored(url: str, persona: str = "brian") -> dict | None:
    """Return cached score+reason for a URL, or None if unseen/expired."""
    store = _load_scored()
    entry = store.get(f"{persona}:{url}")
    if not entry:
        return None
    scored_at = datetime.fromisoformat(entry["scored_at"])
    if datetime.now() - scored_at > timedelta(days=SCORED_TTL_DAYS):
        return None
    return entry  # {"score": N, "reason": "...", "scored_at": "..."}


def save_scored(url: str, score: int, reason: str, name: str = "", persona: str = "brian"):
    """Persist a score for a URL."""
    store = _load_scored()
    store[f"{persona}:{url}"] = {
        "score":     score,
        "reason":    reason,
        "name":      name,
        "scored_at": datetime.now().isoformat(),
    }
    _save_scored(store)


def prune_scored():
    """Remove expired entries to keep the file small."""
    store = _load_scored()
    cutoff = datetime.now() - timedelta(days=SCORED_TTL_DAYS)
    pruned = {
        url: e for url, e in store.items()
        if datetime.fromisoformat(e["scored_at"]) > cutoff
    }
    _save_scored(pruned)
    return len(store) - len(pruned)


def _load() -> dict:
    if not os.path.exists(CACHE_FILE):
        return {}
    with open(CACHE_FILE) as f:
        return json.load(f)


def _save(data: dict):
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get(key: str) -> list | None:
    """Return cached data if still fresh, else None."""
    store = _load()
    entry = store.get(key)
    if not entry:
        return None
    fetched_at = datetime.fromisoformat(entry["fetched_at"])
    ttl_hours = entry.get("ttl_hours", 24)
    if datetime.now() - fetched_at > timedelta(hours=ttl_hours):
        return None
    return entry["data"]


def set(key: str, data: list, ttl_hours: int = 24):
    """Store data in cache with a TTL."""
    store = _load()
    store[key] = {
        "data": data,
        "fetched_at": datetime.now().isoformat(),
        "ttl_hours": ttl_hours,
    }
    _save(store)


def age(key: str) -> str:
    """Return human-readable age of a cache entry."""
    store = _load()
    entry = store.get(key)
    if not entry:
        return "not cached"
    fetched_at = datetime.fromisoformat(entry["fetched_at"])
    delta = datetime.now() - fetched_at
    hours = int(delta.total_seconds() / 3600)
    if hours < 1:
        return f"{int(delta.total_seconds() / 60)}m ago"
    if hours < 24:
        return f"{hours}h ago"
    return f"{hours // 24}d ago"
