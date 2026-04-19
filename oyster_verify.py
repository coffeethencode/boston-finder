#!/usr/bin/env python3
# ruff: noqa: E402  # deliberate: sys.path.insert must run before package imports
"""
Oyster venue verification.

Scrapes each venue's specials page, checks for deal keywords,
generates Google Maps links, and updates:
  - ~/boston_finder_oyster_status.json  (machine cache)
  - ~/python-projects/oyster/venues.md  (human-readable registry)

Run weekly: python3 oyster_verify.py
Use --force to re-check all venues even if recently verified.
Use --venue "Name" to check a single venue.

Usage:
    python3 oyster_verify.py
    python3 oyster_verify.py --force
    python3 oyster_verify.py --venue "Row 34"
"""

import sys
import json
import os
import time
import argparse
import re
import urllib.parse
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from boston_finder.oyster_sources import OYSTER_VENUES
from boston_finder.location import score as proximity_score, label as proximity_label, PROXIMITY

STATUS_FILE    = os.path.expanduser("~/boston_finder_oyster_status.json")
VENUES_MD      = os.path.join(os.path.dirname(__file__), "oyster", "venues.md")
VERIFY_TTL     = 7   # days before re-verifying
HEADERS        = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

DEAL_KEYWORDS  = [
    "oyster", "$1", "$2", "dollar oyster", "buck", "half price", "half-price",
    "happy hour", "raw bar special", "discounted", "two-for-one", "2 for 1",
]
CLOSED_SIGNALS = ["permanently closed", "we are closed", "location is closed", "closed permanently"]


# ── Status cache ───────────────────────────────────────────────────────────────

def load_status() -> dict:
    if not os.path.exists(STATUS_FILE):
        return {}
    with open(STATUS_FILE) as f:
        return json.load(f)


def save_status(data: dict):
    with open(STATUS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def maps_link(venue_name: str, neighborhood: str) -> str:
    q = urllib.parse.quote(f"{venue_name} {neighborhood} Boston MA")
    return f"https://maps.google.com/?q={q}"


# ── Verification ───────────────────────────────────────────────────────────────

def verify_venue(venue: dict, force: bool = False) -> dict:
    """
    Check a venue's specials page for oyster deal keywords.
    Returns status dict: {status, verified_at, found_keywords, maps_url, notes}
    """
    name = venue["name"]
    status = load_status()
    key = name.lower().replace(" ", "_")

    # check TTL
    if not force and key in status:
        entry = status[key]
        verified_at = datetime.fromisoformat(entry["verified_at"])
        if datetime.now() - verified_at < timedelta(days=VERIFY_TTL):
            print(f"  {name}: cached ({entry['status']}, {entry['verified_at'][:10]})")
            return entry

    maps_url = maps_link(name, venue.get("neighborhood", ""))

    # fetch specials page
    url = venue.get("specials_url") or venue.get("url", "")
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            result = {
                "status": "⚠️ Unverified",
                "verified_at": datetime.now().isoformat(),
                "found_keywords": [],
                "maps_url": maps_url,
                "notes": f"HTTP {r.status_code}",
            }
            status[key] = result
            save_status(status)
            print(f"  {name}: HTTP {r.status_code}")
            return result

        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text(separator=" ").lower()

        # check for closed signals first
        if any(s in text for s in CLOSED_SIGNALS):
            result = {
                "status": "❌ Inactive",
                "verified_at": datetime.now().isoformat(),
                "found_keywords": [],
                "maps_url": maps_url,
                "notes": "Closure language found on page",
            }
            status[key] = result
            save_status(status)
            print(f"  {name}: ❌ CLOSED signal found")
            return result

        found = [k for k in DEAL_KEYWORDS if k in text]
        if found:
            result = {
                "status": "✅ Active",
                "verified_at": datetime.now().isoformat(),
                "found_keywords": found,
                "maps_url": maps_url,
                "notes": f"Found: {', '.join(found[:3])}",
            }
        else:
            result = {
                "status": "⚠️ Unverified",
                "verified_at": datetime.now().isoformat(),
                "found_keywords": [],
                "maps_url": maps_url,
                "notes": "No deal keywords found on specials page — check manually",
            }

        status[key] = result
        save_status(status)
        print(f"  {name}: {result['status']} — {result['notes']}")
        return result

    except Exception as ex:
        result = {
            "status": "⚠️ Unverified",
            "verified_at": datetime.now().isoformat(),
            "found_keywords": [],
            "maps_url": maps_url,
            "notes": f"Error: {ex}",
        }
        status[key] = result
        save_status(status)
        print(f"  {name}: error — {ex}")
        return result


# ── Markdown generation ────────────────────────────────────────────────────────

PROX_TIERS = [
    (9, "## Nearby (South End / Back Bay)"),
    (7, "## Easy (North End / Fenway / Downtown)"),
    (5, "## Doable (Seaport / Fort Point / Kenmore / Cambridge)"),
    (3, "## Hike (Farther away)"),
    (0, "## Expedition (Suburbs)"),
]


def generate_md(results: list[dict]):
    """Write oyster/venues.md from current results."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        "# Boston Oyster Deals — Venue Registry",
        "",
        f"**Run `python3 oyster_verify.py` weekly to update status.**",
        f"Last verified: {now}",
        "",
        "## Status Legend",
        "| Symbol | Meaning |",
        "|--------|---------|",
        "| ✅ Active | Deal keywords found on venue website within last 30 days |",
        "| ⚠️ Unverified | Not checked recently — deal may have changed |",
        "| ❌ Inactive | Deal no longer listed or venue closed |",
        "",
        "---",
    ]

    # group by proximity tier
    tier_buckets: dict[int, list] = {t[0]: [] for t in PROX_TIERS}
    for r in results:
        prox = proximity_score(r.get("neighborhood", ""))
        for cutoff, _ in PROX_TIERS:
            if prox >= cutoff:
                tier_buckets[cutoff].append(r)
                break

    for cutoff, header in PROX_TIERS:
        bucket = tier_buckets.get(cutoff, [])
        if not bucket:
            continue
        lines += ["", header, ""]
        lines.append("| Venue | Neighborhood | Known Deal | Days / Hours | Status | Maps |")
        lines.append("|-------|-------------|-----------|-------------|--------|------|")
        for r in sorted(bucket, key=lambda x: -proximity_score(x.get("neighborhood", ""))):
            name  = r["name"]
            neigh = r.get("neighborhood", "")
            deal  = r.get("known_deal") or "—"
            hours = r.get("hours", "—")
            vstatus = r.get("verify_status", "⚠️ Unverified")
            murl  = r.get("maps_url", maps_link(name, neigh))
            lines.append(f"| {name} | {neigh} | {deal} | {hours} | {vstatus} | [📍]({murl}) |")

    lines += [
        "",
        "---",
        "",
        "## How to Add a Venue",
        "",
        "1. Add entry to `boston_finder/oyster_sources.py` → `OYSTER_VENUES`",
        "2. Run `python3 oyster_verify.py` — checks the site and rebuilds this file",
        "3. Confirmed deal → status becomes ✅ Active automatically",
        "",
        "## How to Mark a Deal Inactive",
        "",
        "Set `\"known_deal\": None` in `oyster_sources.py` OR wait for verify to mark it ❌.",
    ]

    os.makedirs(os.path.dirname(VENUES_MD), exist_ok=True)
    with open(VENUES_MD, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\n  → Wrote {VENUES_MD}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force",  action="store_true", help="Re-check all venues even if recently verified")
    parser.add_argument("--venue",  type=str, default="",  help="Check a single venue by name (partial match ok)")
    args = parser.parse_args()

    venues = OYSTER_VENUES
    if args.venue:
        needle = args.venue.lower()
        venues = [v for v in venues if needle in v["name"].lower()]
        if not venues:
            print(f"No venue matching '{args.venue}'")
            sys.exit(1)

    # deduplicate by name (oyster_sources has Legal Harborside twice)
    seen_names: set[str] = set()
    unique_venues = []
    for v in venues:
        if v["name"] not in seen_names:
            seen_names.add(v["name"])
            unique_venues.append(v)

    print(f"\n{'─'*55}")
    print(f"  Oyster Venue Verification  |  {datetime.now().strftime('%B %-d, %Y')}")
    print(f"  {len(unique_venues)} venues to check")
    print(f"{'─'*55}\n")

    results = []
    for v in unique_venues:
        entry = verify_venue(v, force=args.force)
        results.append({
            "name":          v["name"],
            "neighborhood":  v.get("neighborhood", ""),
            "known_deal":    v.get("known_deal"),
            "hours":         _extract_hours(v.get("known_deal", "") or ""),
            "verify_status": entry["status"],
            "maps_url":      entry["maps_url"],
            "notes":         entry.get("notes", ""),
            "verified_at":   entry["verified_at"],
        })
        time.sleep(0.3)

    generate_md(results)

    # summary
    active   = [r for r in results if "Active" in r["verify_status"]]
    inactive = [r for r in results if "Inactive" in r["verify_status"]]
    unverified = [r for r in results if "Unverified" in r["verify_status"]]

    print(f"\n{'─'*55}")
    print(f"  ✅ Active:      {len(active)}")
    print(f"  ⚠️  Unverified: {len(unverified)}")
    print(f"  ❌ Inactive:    {len(inactive)}")
    print(f"{'─'*55}")

    if unverified:
        print("\n  Venues needing manual check:")
        for r in unverified:
            print(f"    {r['name']} — {r['notes']}")
            print(f"    {r['maps_url']}")
    print()


def _extract_hours(deal_str: str) -> str:
    """Pull hours/days substring from a known_deal string."""
    if not deal_str:
        return "—"
    # match patterns like "Mon–Wed 5–6pm", "daily 3-6pm", "Sun & Mon 9–10pm"
    m = re.search(r'(daily|mon|tue|wed|thu|fri|sat|sun)[^.,$]{2,30}', deal_str, re.IGNORECASE)
    return m.group(0).strip() if m else "—"


if __name__ == "__main__":
    main()
