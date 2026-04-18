"""
Known Boston oyster venues — scraped directly for standing deals.
Add venues to OYSTER_VENUES as you discover them.
The scraper checks each venue's events/specials page for current deals.

Also reads from ~/oyster_research.txt if present — paste your Gemini/ChatGPT
deep research output there and it gets folded in automatically.
"""

import os
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

# ══════════════════════════════════════════════════════════════════════════════
# KNOWN OYSTER VENUES — add to this list as you find good spots
# "specials_url": the page most likely to mention happy hour deals
# ══════════════════════════════════════════════════════════════════════════════
OYSTER_VENUES = [
    {
        "name": "Island Creek Oyster Bar",
        "neighborhood": "Kenmore",
        "url": "https://islandcreekoysters.com/pages/boston",
        "specials_url": "https://islandcreekoysters.com/pages/boston",
        "known_deal": "$1 oysters at the bar, select hours",
    },
    {
        "name": "Row 34",
        "neighborhood": "Fort Point",
        "url": "https://www.row34.com",
        "specials_url": "https://www.row34.com/specials",
        "known_deal": "Dollar oysters Mon–Wed 5–6pm",
    },
    {
        "name": "Neptune Oyster",
        "neighborhood": "North End",
        "url": "https://www.neptuneoyster.com",
        "specials_url": "https://www.neptuneoyster.com",
        "known_deal": None,  # no standing happy hour, but excellent raw bar
    },
    {
        "name": "B&G Oysters",
        "neighborhood": "South End",
        "url": "https://www.bandgoysters.com",
        "specials_url": "https://www.bandgoysters.com",
        "known_deal": None,
    },
    {
        "name": "Saltie Girl",
        "neighborhood": "Back Bay",
        "url": "https://www.saltiegirl.com",
        "specials_url": "https://www.saltiegirl.com",
        "known_deal": None,
    },
    {
        "name": "Woods Hill Pier 4",
        "neighborhood": "Seaport",
        "url": "https://www.woodshillpier4.com",
        "specials_url": "https://www.woodshillpier4.com/specials",
        "known_deal": "Dollar oysters Mon–Wed 5–6pm",
    },
    {
        "name": "Russell House Tavern",
        "neighborhood": "Harvard Square",
        "url": "https://www.russellhouserestaurant.com",
        "specials_url": "https://www.russellhouserestaurant.com/menus",
        "known_deal": "$1 oysters 9–10pm Sun & Mon",
    },
    {
        "name": "Ostra",
        "neighborhood": "Back Bay",
        "url": "https://www.ostraboston.com",
        "specials_url": "https://www.ostraboston.com/menus",
        "known_deal": None,
    },
    {
        "name": "Legal Harborside",
        "neighborhood": "Seaport",
        "url": "https://www.legalseafoods.com/restaurants/boston-legal-harborside",
        "specials_url": "https://www.legalseafoods.com/restaurants/boston-legal-harborside",
        "known_deal": None,
    },
    {
        "name": "Eventide",
        "neighborhood": "Back Bay",
        "url": "https://www.eventideboston.com",
        "specials_url": "https://www.eventideboston.com",
        "known_deal": None,
    },
    {
        "name": "Legal Sea Foods Long Wharf",
        "neighborhood": "Downtown/Waterfront",
        "url": "https://www.legalseafoods.com/restaurants/boston-long-wharf",
        "specials_url": "https://www.legalseafoods.com/restaurants/boston-long-wharf",
        "known_deal": "$1 oysters daily 3-6pm (bar area only)",
    },
    {
        "name": "Legal Sea Foods Prudential",
        "neighborhood": "Back Bay",
        "url": "https://www.legalseafoods.com/restaurants/boston-prudential-center",
        "specials_url": "https://www.legalseafoods.com/restaurants/boston-prudential-center",
        "known_deal": "$1 oysters daily 3-6pm (bar area only)",
    },
    {
        "name": "Legal Harborside",
        "neighborhood": "Seaport",
        "url": "https://www.legalseafoods.com/restaurants/boston-legal-harborside",
        "specials_url": "https://www.legalseafoods.com/restaurants/boston-legal-harborside",
        "known_deal": "$1 oysters daily 3-6pm (bar area only)",
    },
    {
        "name": "Legal Sea Foods Copley",
        "neighborhood": "Back Bay",
        "url": "https://www.legalseafoods.com/restaurants/boston-copley-place",
        "specials_url": "https://www.legalseafoods.com/restaurants/boston-copley-place",
        "known_deal": "$1 oysters daily 3-6pm (bar area only)",
    },
    # ── Providence, RI ───────────────────────────────────────────────────────
    {
        "name": "Providence Oyster Bar",
        "neighborhood": "Federal Hill, Providence RI",
        "url": "https://providenceoysterbar.com/",
        "specials_url": "https://providenceoysterbar.com/",
        "known_deal": "$1 oysters + $1 littlenecks daily 3–5:30pm",
        "city": "Providence",
    },
    {
        "name": "Mill's Tavern",
        "neighborhood": "Downtown Providence RI",
        "url": "https://www.millstavernrestaurant.com",
        "specials_url": "https://www.millstavernrestaurant.com",
        "known_deal": "Half-price oysters + $1 oysters daily 5–6:30pm",
        "city": "Providence",
    },
    {
        "name": "Pizzico Oyster Bar",
        "neighborhood": "Hope Street, Providence RI",
        "url": "https://www.pizzico.com",
        "specials_url": "https://www.pizzico.com",
        "known_deal": "Half-price raw bar oysters daily 4–6pm; 9–10pm weekends",
        "city": "Providence",
    },
    {
        "name": "Federal Taphouse",
        "neighborhood": "Federal Hill, Providence RI",
        "url": "https://www.federaltaphouse.com",
        "specials_url": "https://www.federaltaphouse.com",
        "known_deal": "$1 oysters daily 1–6:30pm",
        "city": "Providence",
    },
    {
        "name": "Hemenway's",
        "neighborhood": "Downtown Providence RI",
        "url": "https://www.hemenways.com",
        "specials_url": "https://www.hemenways.com",
        "known_deal": None,
        "city": "Providence",
    },
    # ── Add more here ────────────────────────────────────────────────────────
]

RESEARCH_FILE = os.path.expanduser("~/oyster_research.txt")


def fetch_venue_text(venue: dict) -> str:
    """Fetch a venue's specials page and return its text."""
    try:
        r = requests.get(venue["specials_url"], headers=HEADERS, timeout=8)
        if r.status_code != 200:
            return ""
        soup = BeautifulSoup(r.text, "html.parser")
        return soup.get_text(separator=" ")[:2000]
    except Exception:
        return ""


def get_all() -> list[dict]:
    """
    Return a list of candidate oyster deal records for AI scoring.
    Each record has the standard event shape plus venue metadata.
    """
    records = []

    # 1. Known venues with hardcoded deals (always include)
    for v in OYSTER_VENUES:
        if v.get("known_deal"):
            records.append({
                "source": "known_venue",
                "name": f"{v['name']} — {v['known_deal']}",
                "description": f"{v['neighborhood']}. Standing deal: {v['known_deal']}",
                "url": v["url"],
                "start": "",
                "venue": v["name"],
                "address": v["neighborhood"],
                "city": v.get("city", "Boston"),
            })

    # 2. Scrape specials pages for any mention of oyster deals
    print("  Checking venue specials pages...")
    for v in OYSTER_VENUES:
        if v.get("known_deal"):
            continue  # already included above
        text = fetch_venue_text(v)
        oyster_keywords = ["oyster", "raw bar", "happy hour", "half price", "$1", "dollar"]
        if any(k in text.lower() for k in oyster_keywords):
            records.append({
                "source": "venue_scrape",
                "name": f"{v['name']} (possible deal found)",
                "description": text[:400],
                "url": v["specials_url"],
                "start": "",
                "venue": v["name"],
                "address": v["neighborhood"],
                "city": v.get("city", "Boston"),
                "_raw": False,
            })

    # 3. Read pasted deep research file if present
    if os.path.exists(RESEARCH_FILE):
        with open(RESEARCH_FILE) as f:
            content = f.read().strip()
        if content:
            print(f"  Reading {RESEARCH_FILE} ...")
            # Google Docs exports tables as one cell per tab-indented line.
            # Group consecutive tab-indented lines into rows of 6: name, neighborhood, deal, hours, type, url
            tab_lines = [l.strip() for l in content.splitlines() if l.startswith("\t") and l.strip()]
            # clean footnote numbers from ends of values (e.g. "3:00 PM 2" → "3:00 PM")
            import re
            tab_lines = [re.sub(r'\s+\d+$', '', l) for l in tab_lines]

            # skip header rows
            skip = {"venue name", "neighborhood", "specific deal", "days and hours",
                    "event type", "website / reservation link", "standing weekly",
                    "seasonal event", "not explicitly listed"}

            table_rows = []
            i = 0
            while i < len(tab_lines) - 3:
                name  = tab_lines[i]
                neigh = tab_lines[i+1]
                deal  = tab_lines[i+2]
                hours = tab_lines[i+3]
                url   = tab_lines[i+5] if i+5 < len(tab_lines) else ""

                if (name.lower() not in skip and
                        any(k in deal.lower() for k in ["$1", "$2", "dollar", "half", "oyster", "buck"])):
                    url_clean = url if url.lower() not in skip and url.startswith("http") else ""
                    records.append({
                        "source": "deep_research",
                        "name": f"{name} — {deal}",
                        "description": f"{neigh}. {deal}, {hours}.",
                        "url": url_clean,
                        "start": "",
                        "venue": name,
                        "address": neigh,
                    })
                    table_rows.append(name)
                    i += 6
                else:
                    i += 1

            print(f"  → extracted {len(table_rows)} venues from research tables")

    return records
