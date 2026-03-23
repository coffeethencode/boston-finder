"""
SOURCE REGISTRY
───────────────
Add a source here once — all programs that share a tag will use it.
Same source list for all personas — scoring prompt handles what's relevant for each person.

Tags:
  "events"  — daily event finder
  "food"    — oyster/food deals finder
  "civic"   — public records, open meeting law alerts

Types:
  "eventbrite_search"  — searches Eventbrite by keyword in Boston
  "do617_category"     — scrapes a do617.com category page by date
  "scrape_url"         — fetches a URL, AI extracts events from text

To add a source: copy any entry below, set enabled: True.
"""

SOURCES = [
    # ── Eventbrite: food & drink ───────────────────────────────────────────────
    {"name": "Eventbrite: oyster",               "type": "eventbrite_search", "term": "oyster",               "tags": ["events", "food"], "enabled": True},
    {"name": "Eventbrite: happy hour",           "type": "eventbrite_search", "term": "happy+hour",           "tags": ["events", "food"], "enabled": True},
    {"name": "Eventbrite: wine dinner",          "type": "eventbrite_search", "term": "wine+dinner",          "tags": ["events", "food"], "enabled": True},
    {"name": "Eventbrite: tasting",              "type": "eventbrite_search", "term": "tasting",              "tags": ["events", "food"], "enabled": True},
    {"name": "Eventbrite: cocktail",             "type": "eventbrite_search", "term": "cocktail",             "tags": ["events", "food"], "enabled": True},
    {"name": "Eventbrite: food festival",        "type": "eventbrite_search", "term": "food+festival",        "tags": ["events", "food"], "enabled": True},
    {"name": "Eventbrite: chef",                 "type": "eventbrite_search", "term": "chef",                 "tags": ["events", "food"], "enabled": True},
    {"name": "Eventbrite: brunch",               "type": "eventbrite_search", "term": "brunch",               "tags": ["events", "food"], "enabled": True},

    # ── Eventbrite: upscale social ─────────────────────────────────────────────
    {"name": "Eventbrite: gala",                 "type": "eventbrite_search", "term": "gala",                 "tags": ["events"],         "enabled": True},
    {"name": "Eventbrite: fundraiser",           "type": "eventbrite_search", "term": "fundraiser",           "tags": ["events"],         "enabled": True},
    {"name": "Eventbrite: charity benefit",      "type": "eventbrite_search", "term": "charity+benefit",      "tags": ["events"],         "enabled": True},
    {"name": "Eventbrite: benefit dinner",       "type": "eventbrite_search", "term": "benefit+dinner",       "tags": ["events"],         "enabled": True},
    {"name": "Eventbrite: reception",            "type": "eventbrite_search", "term": "reception",            "tags": ["events"],         "enabled": True},
    {"name": "Eventbrite: award ceremony",       "type": "eventbrite_search", "term": "award+ceremony",       "tags": ["events"],         "enabled": True},
    {"name": "Eventbrite: auction",              "type": "eventbrite_search", "term": "auction",              "tags": ["events"],         "enabled": True},
    {"name": "Eventbrite: networking reception", "type": "eventbrite_search", "term": "networking+reception", "tags": ["events"],         "enabled": True},
    {"name": "Eventbrite: launch party",         "type": "eventbrite_search", "term": "launch+party",         "tags": ["events"],         "enabled": True},
    {"name": "Eventbrite: rooftop",              "type": "eventbrite_search", "term": "rooftop",              "tags": ["events"],         "enabled": True},
    {"name": "Eventbrite: vip",                  "type": "eventbrite_search", "term": "vip",                  "tags": ["events"],         "enabled": True},
    {"name": "Eventbrite: exclusive",            "type": "eventbrite_search", "term": "exclusive",            "tags": ["events"],         "enabled": True},

    # ── Eventbrite: arts & culture ─────────────────────────────────────────────
    {"name": "Eventbrite: art opening",          "type": "eventbrite_search", "term": "art+opening",          "tags": ["events"],         "enabled": True},
    {"name": "Eventbrite: gallery",              "type": "eventbrite_search", "term": "gallery",              "tags": ["events"],         "enabled": True},
    {"name": "Eventbrite: fashion",              "type": "eventbrite_search", "term": "fashion",              "tags": ["events"],         "enabled": True},
    {"name": "Eventbrite: fashion show",         "type": "eventbrite_search", "term": "fashion+show",         "tags": ["events"],         "enabled": True},
    {"name": "Eventbrite: film screening",       "type": "eventbrite_search", "term": "film+screening",       "tags": ["events"],         "enabled": True},
    {"name": "Eventbrite: photography",          "type": "eventbrite_search", "term": "photography",          "tags": ["events"],         "enabled": True},
    {"name": "Eventbrite: design",               "type": "eventbrite_search", "term": "design",               "tags": ["events"],         "enabled": True},
    {"name": "Eventbrite: pop-up",               "type": "eventbrite_search", "term": "pop-up",               "tags": ["events"],         "enabled": True},

    # ── Eventbrite: civic & professional ──────────────────────────────────────
    {"name": "Eventbrite: civic",                "type": "eventbrite_search", "term": "civic",                "tags": ["events", "civic"],"enabled": True},
    {"name": "Eventbrite: panel",                "type": "eventbrite_search", "term": "panel",                "tags": ["events", "civic"],"enabled": True},
    {"name": "Eventbrite: advocacy",             "type": "eventbrite_search", "term": "advocacy",             "tags": ["events", "civic"],"enabled": True},
    {"name": "Eventbrite: open government",      "type": "eventbrite_search", "term": "open+government",      "tags": ["events", "civic"],"enabled": True},
    {"name": "Eventbrite: public records",       "type": "eventbrite_search", "term": "public+records",       "tags": ["events", "civic"],"enabled": True},
    {"name": "Eventbrite: press",                "type": "eventbrite_search", "term": "press+event",          "tags": ["events"],         "enabled": True},
    {"name": "Eventbrite: media",                "type": "eventbrite_search", "term": "media+event",          "tags": ["events"],         "enabled": True},
    {"name": "Eventbrite: journalism",           "type": "eventbrite_search", "term": "journalism",           "tags": ["events", "civic"],"enabled": True},

    # ── do617 categories ──────────────────────────────────────────────────────
    {"name": "do617: Food & Drink",              "type": "do617_category",    "path": "food-drink",                    "tags": ["events", "food"], "enabled": True},
    {"name": "do617: Film/Theatre/Arts",         "type": "do617_category",    "path": "film-theatre-performing-arts",  "tags": ["events"],         "enabled": True},
    {"name": "do617: Concerts",                  "type": "do617_category",    "path": "concerts",                      "tags": ["events"],         "enabled": True},
    {"name": "do617: Comedy",                    "type": "do617_category",    "path": "comedy",                        "tags": ["events"],         "enabled": True},
    {"name": "do617: DJ/Dance Nights",           "type": "do617_category",    "path": "dj-sets-dance-nights",          "tags": ["events"],         "enabled": True},

    # ── Scrape URL: civic/arts orgs ────────────────────────────────────────────
    {"name": "ACLU MA",          "type": "scrape_url", "url": "https://www.aclum.org/en/events",                     "tags": ["events", "civic"], "enabled": True},
    {"name": "Boston Bar Assoc", "type": "scrape_url", "url": "https://www.bostonbar.org/events/",                   "tags": ["events", "civic"], "enabled": True},
    {"name": "Artsboston",       "type": "scrape_url", "url": "https://artsboston.org/events/",                      "tags": ["events"],          "enabled": True},
    {"name": "WBUR Events",      "type": "scrape_url", "url": "https://www.wbur.org/events",                         "tags": ["events", "civic"], "enabled": True},
    {"name": "MFA Boston",       "type": "scrape_url", "url": "https://www.mfa.org/programs",                        "tags": ["events"],          "enabled": True},
    {"name": "ICA Boston",       "type": "scrape_url", "url": "https://www.icaboston.org/events",                    "tags": ["events"],          "enabled": True},
    {"name": "BSO Events",       "type": "scrape_url", "url": "https://www.bso.org/events",                          "tags": ["events"],          "enabled": True},

    # ── Disabled / to try ─────────────────────────────────────────────────────
    # {"name": "Island Creek Oysters", "type": "scrape_url", "url": "https://islandcreekoysters.com/pages/events", "tags": ["food"], "enabled": False},
    # {"name": "Row 34 events",        "type": "scrape_url", "url": "https://www.row34.com/events",               "tags": ["food"], "enabled": False},
    # {"name": "Eventbrite: model",    "type": "eventbrite_search", "term": "model",                              "tags": ["events"],  "enabled": False},
]


def get_sources(tag: str) -> list[dict]:
    """Return enabled sources matching a given tag."""
    return [s for s in SOURCES if s["enabled"] and tag in s.get("tags", [])]
