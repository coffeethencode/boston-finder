"""
SOURCE REGISTRY
───────────────
Add a source here once — all programs that share a tag will use it.

Tags:
  "events"  — daily event finder
  "food"    — oyster/food deals finder
  "civic"   — public records, open meeting law alerts (future)

Types:
  "eventbrite_search"  — searches Eventbrite by keyword in Boston
  "do617_category"     — scrapes a do617.com category page by date
  "scrape_url"         — fetches a URL, AI extracts events from text

To add a source: copy any entry below, change the fields, set enabled: True.
"""

SOURCES = [
    # ── Eventbrite keyword searches ───────────────────────────────────────────
    {"name": "Eventbrite: gala",                "type": "eventbrite_search", "term": "gala",               "tags": ["events"],        "enabled": True},
    {"name": "Eventbrite: fundraiser",           "type": "eventbrite_search", "term": "fundraiser",         "tags": ["events"],        "enabled": True},
    {"name": "Eventbrite: happy hour",           "type": "eventbrite_search", "term": "happy+hour",         "tags": ["events", "food"],"enabled": True},
    {"name": "Eventbrite: oyster",               "type": "eventbrite_search", "term": "oyster",             "tags": ["food"],          "enabled": True},
    {"name": "Eventbrite: networking reception", "type": "eventbrite_search", "term": "networking+reception","tags": ["events"],        "enabled": True},
    {"name": "Eventbrite: charity benefit",      "type": "eventbrite_search", "term": "charity+benefit",    "tags": ["events"],        "enabled": True},
    {"name": "Eventbrite: civic",                "type": "eventbrite_search", "term": "civic",              "tags": ["events", "civic"],"enabled": True},
    {"name": "Eventbrite: panel",                "type": "eventbrite_search", "term": "panel",              "tags": ["events", "civic"],"enabled": True},
    {"name": "Eventbrite: advocacy",             "type": "eventbrite_search", "term": "advocacy",           "tags": ["events", "civic"],"enabled": True},
    {"name": "Eventbrite: fashion",              "type": "eventbrite_search", "term": "fashion",            "tags": ["events"],        "enabled": True},
    {"name": "Eventbrite: open government",      "type": "eventbrite_search", "term": "open+government",    "tags": ["events", "civic"],"enabled": True},
    {"name": "Eventbrite: public records",       "type": "eventbrite_search", "term": "public+records",     "tags": ["events", "civic"],"enabled": True},
    {"name": "Eventbrite: wine dinner",          "type": "eventbrite_search", "term": "wine+dinner",        "tags": ["events", "food"], "enabled": True},

    # ── do617 categories ──────────────────────────────────────────────────────
    {"name": "do617: Food & Drink",              "type": "do617_category",    "path": "food-drink",         "tags": ["events", "food"], "enabled": True},
    {"name": "do617: Film/Theatre/Arts",         "type": "do617_category",    "path": "film-theatre-performing-arts", "tags": ["events"], "enabled": True},

    # ── Add your own sources below ────────────────────────────────────────────
    # {"name": "ACLU MA events",   "type": "scrape_url", "url": "https://www.aclum.org/en/events",      "tags": ["events", "civic"], "enabled": False},
    # {"name": "Boston Bar Assoc", "type": "scrape_url", "url": "https://www.bostonbar.org/events/",    "tags": ["events", "civic"], "enabled": False},
    # {"name": "Island Creek Oysters", "type": "scrape_url", "url": "https://islandcreekoysters.com/pages/events", "tags": ["food"], "enabled": False},
    # {"name": "Row 34 events",    "type": "scrape_url", "url": "https://www.row34.com/events",         "tags": ["food"],            "enabled": False},
]


def get_sources(tag: str) -> list[dict]:
    """Return enabled sources matching a given tag."""
    return [s for s in SOURCES if s["enabled"] and tag in s.get("tags", [])]
