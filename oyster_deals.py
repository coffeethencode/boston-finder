#!/usr/bin/env python3
"""
Boston oyster deals finder.
Runs weekly — builds a ranked list of where to get dollar/cheap oysters,
sorted by proximity and persona preference.

Usage:
    python3 oyster_deals.py                         # all personas, use cache
    python3 oyster_deals.py --persona brian         # Brian only
    python3 oyster_deals.py --persona chloe         # Chloe only
    python3 oyster_deals.py --force                 # force re-fetch
"""

import sys
import os
import argparse
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from boston_finder.sources        import get_sources
from boston_finder.fetchers       import fetch_source
from boston_finder.ai_filter      import deduplicate, score
from boston_finder.oyster_sources import get_all as get_oyster_candidates
from boston_finder.notify         import send
from boston_finder.cache          import get as cache_get, set as cache_set, age as cache_age
from boston_finder.location       import score as proximity_score, label as proximity_label, PROXIMITY
from boston_finder.personas       import (
    get_persona, PERSONAS, active_personas,
    get_proximity, get_oyster_prompt, get_min_score,
)
from boston_finder                import costs

CACHE_KEY_BASE = "oyster_deals"
CACHE_TTL      = 168  # 7 days in hours

# Verification status file (written by oyster_verify.py)
STATUS_FILE = os.path.expanduser("~/boston_finder_oyster_status.json")


def load_verify_status() -> dict:
    """Load verification status from oyster_verify.py output."""
    if not os.path.exists(STATUS_FILE):
        return {}
    import json
    with open(STATUS_FILE) as f:
        return json.load(f)



def sort_by_proximity(deals: list[dict], persona: str = "brian") -> list[dict]:
    """Sort deals by proximity score for a given persona (highest first)."""
    prox_table = get_proximity(persona) or PROXIMITY

    def rank_key(d):
        address = (d.get("venue", "") + " " + d.get("address", "")).strip()
        prox = proximity_score(address, prox_table)
        d["_proximity"] = prox
        d["_proximity_label"] = proximity_label(prox)
        # secondary sort: inactive to bottom, then by AI score
        inactive = 1 if d.get("_inactive") else 0
        ai_score = -(d.get("score") or 0)
        return (inactive, -prox, ai_score)

    return sorted(deals, key=rank_key)


def display(deals: list[dict], persona_label: str, from_cache: bool, cache_age_str: str):
    print(f"\n{'═'*65}")
    print(f"  BOSTON OYSTER DEALS — {persona_label.upper()}  |  {datetime.now().strftime('%B %-d, %Y')}")
    if from_cache:
        print(f"  (cached {cache_age_str} — runs fresh weekly)")
    print(f"{'═'*65}")

    if not deals:
        print("\n  No oyster deals found.\n")
        return

    current_tier = None
    for d in deals:
        if d.get("_inactive"):
            continue

        tier = d.get("_proximity_label", "")
        if tier != current_tier:
            current_tier = tier
            print(f"\n  ── {tier.upper()} ──")

        score_str = f"  ★{d['score']}" if d.get("score") else ""
        vstatus   = d.get("verify_status", "")
        maps_url  = d.get("maps_url", "")

        venue = d.get("venue") or ""
        name  = d.get("name", "")
        display_name = venue if venue else name

        print(f"\n  {display_name}{score_str}  {vstatus}")
        if d.get("address"):
            prox_lbl = d.get("_proximity_label", "")
            print(f"  📍 {d['address']}", end="")
            if prox_lbl:
                print(f" ({prox_lbl})", end="")
            print()
        if d.get("reason"):
            print(f"  → {d['reason']}")
        if maps_url:
            print(f"  🗺  {maps_url}")
        elif d.get("url"):
            print(f"  {d['url']}")

    print(f"\n{'═'*65}")
    active_count = sum(1 for d in deals if not d.get("_inactive"))
    print(f"  {active_count} active deals found")
    costs.print_summary()
    print(f"{'═'*65}\n")


def run_persona(persona_name: str, all_events: list[dict], force: bool):
    persona  = get_persona(persona_name)
    label    = persona["nav_label"]
    prompt   = get_oyster_prompt(persona_name)
    min_score = get_min_score(persona_name)
    cache_key = f"{CACHE_KEY_BASE}_{persona_name}"

    if not force:
        cached = cache_get(cache_key)
        if cached is not None:
            age_str = cache_age(cache_key)
            print(f"\n[oyster_deals:{persona_name}] Using cache ({age_str}). --force to refresh.")
            # re-attach verify status in case oyster_verify.py ran since caching
            vstatus = load_verify_status()
            for d in cached:
                venue_key = (d.get("venue") or d.get("name", "")).lower().replace(" ", "_")
                entry = vstatus.get(venue_key, {})
                d["verify_status"] = entry.get("status", "⚠️ Unverified")
                d["maps_url"]      = entry.get("maps_url", "")
                d["_inactive"]     = "Inactive" in d.get("verify_status", "")
            sorted_deals = sort_by_proximity(cached, persona_name)
            display(sorted_deals, label, from_cache=True, cache_age_str=age_str)
            return

    oyster_events = [
        e for e in all_events
        if any(k in (e["name"] + e.get("description", "")).lower()
               for k in ["oyster", "raw bar", "seafood", "happy hour", "half price", "dollar", "$1"])
    ] or all_events

    print(f"\n  {len(oyster_events)} candidates for {label}. Scoring...")
    deals, _, _ = score(oyster_events, prompt, min_score=min_score, persona=persona_name)

    # attach verification status + maps links
    status = load_verify_status()
    for d in deals:
        venue_key = (d.get("venue") or d.get("name", "")).lower().replace(" ", "_")
        entry = status.get(venue_key, {})
        d["verify_status"] = entry.get("status", "⚠️ Unverified")
        d["maps_url"]      = entry.get("maps_url", "")
        d["_inactive"]     = "Inactive" in d.get("verify_status", "")

    # sort by proximity
    sorted_deals = sort_by_proximity(deals, persona_name)

    # cache
    cache_set(cache_key, sorted_deals, ttl_hours=CACHE_TTL)

    display(sorted_deals, label, from_cache=False, cache_age_str="")
    if sorted_deals:
        send(sorted_deals, datetime.now(), title=f"Boston Oyster Deals — {label}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force",   action="store_true", help="Ignore cache and re-fetch")
    parser.add_argument("--persona", default="all",
                        help="persona name (e.g. brian) or 'all' for every active persona (default: all)")
    args = parser.parse_args()

    if args.persona == "all":
        persona_names = [p["name"] for p in active_personas()]
    else:
        persona_names = [args.persona]

    print("\n[oyster_deals] Fetching fresh oyster deal data...")

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end   = today + timedelta(days=14)

    all_events: list[dict] = []
    seen_urls:  set[str]   = set()

    print("  [Known venues + research file]")
    all_events += get_oyster_candidates()

    for source in get_sources("food"):
        print(f"  [{source['name']}]")
        for e in fetch_source(source, today, end):
            if e.get("url") and e["url"] not in seen_urls:
                seen_urls.add(e["url"])
                all_events.append(e)
            elif not e.get("url"):
                all_events.append(e)

    all_events = deduplicate(all_events)
    print(f"\n  {len(all_events)} total candidates from all sources")

    for persona_name in persona_names:
        run_persona(persona_name, all_events, force=args.force)


if __name__ == "__main__":
    main()
