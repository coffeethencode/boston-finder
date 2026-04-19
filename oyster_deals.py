#!/usr/bin/env python3
# ruff: noqa: E402  # deliberate: sys.path.insert must run before package imports
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
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from boston_finder.oyster_sources import get_all as get_oyster_candidates, OYSTER_VENUES
from boston_finder.notify         import send
from boston_finder.cache          import get as cache_get, set as cache_set, age as cache_age
from boston_finder.location       import score as proximity_score, label as proximity_label, PROXIMITY
from boston_finder.personas       import (
    get_persona, active_personas,
    get_proximity,
)
from boston_finder                import costs
from boston_finder                import event_store, oyster_filter, venue_extractor, oyster_discoveries

CACHE_KEY_BASE = "oyster_deals"
CACHE_TTL      = 168  # 7 days in hours

# Verification status file (written by oyster_verify.py)
STATUS_FILE = os.path.expanduser("~/boston_finder_oyster_status.json")


def collect_event_feed_candidates(known_candidates: list[dict] | None = None) -> list[dict]:
    """
    Read the daily event store, apply binary oyster filter, extract venue
    for each candidate, dedupe against OYSTER_VENUES + discoveries log,
    run verify on each unique venue, log to discoveries.

    known_candidates: pre-built list from get_oyster_candidates() so we can
    dedupe against research.txt rows (not just OYSTER_VENUES hardcoded list).

    Returns: list of candidate deal records in the same shape oyster_sources
    produces (source, name, description, url, start, venue, address).
    """
    try:
        events = event_store.read_events(max_age_hours=48)
    except event_store.EventStoreError as ex:
        print(f"  event store read failed — skipping event-feed candidates: {ex}")
        return []

    oyster_events = [e for e in events if oyster_filter.is_oyster_candidate(e)]
    print(f"  {len(oyster_events)} oyster candidates from event store")

    # build set of known-venue normalized names (OYSTER_VENUES hardcoded list)
    known_from_registry = {venue_extractor.normalize(v["name"]) for v in OYSTER_VENUES}
    # also include research.txt rows and any other pre-built candidates
    known_from_candidates = set()
    if known_candidates:
        for c in known_candidates:
            name = c.get("venue") or c.get("name", "")
            if name:
                # strip deal suffix like " — $1 Duxbury oysters" if present
                base = name.split("—")[0].split(" - ")[0].strip() if ("—" in name or " - " in name) else name
                known_from_candidates.add(venue_extractor.normalize(base))
    known_normalized = known_from_registry | known_from_candidates

    # prior discoveries
    discoveries = oyster_discoveries.load_all()
    discovered_normalized = set(discoveries.keys())

    import oyster_verify

    candidates = []
    for evt in oyster_events:
        venue = venue_extractor.extract_venue(evt, use_llm_fallback=True)
        if not venue:
            # all 5 extraction strategies failed → surface for manual review
            candidates.append({
                "source": f"discovery:{evt.get('source', '')}",
                "name": f"{evt.get('name', '(untitled)')[:60]} — venue unclear",
                "description": evt.get("description", "")[:200],
                "url": evt.get("url", ""),
                "start": evt.get("start", ""),
                "venue": "",
                "address": "",
                "verify_status": "⚠️ Unverified",
                "price": None,
                "hours": None,
                "_tentative": True,
                "_needs_review": True,
            })
            continue

        normalized = venue_extractor.normalize(venue)

        # known-venue match → skip (already covered by OYSTER_VENUES scrape)
        if normalized in known_normalized:
            continue

        # try to match existing discovery (alias / prefix rules)
        matched = venue_extractor.match_existing(venue, list(discovered_normalized) + list(known_normalized))

        if matched in known_normalized:
            continue

        verify_result = oyster_verify.verify_event(evt, force=False)

        if matched and matched in discovered_normalized:
            oyster_discoveries.upsert_with_match(
                venue_canonical=venue,
                venue_normalized=normalized,
                matched_key=matched,
                event=evt,
                verify_result=verify_result,
                extraction_strategy="mixed",
            )
        else:
            oyster_discoveries.upsert(
                venue_canonical=venue,
                venue_normalized=normalized,
                event=evt,
                verify_result=verify_result,
                extraction_strategy="mixed",
            )
            discovered_normalized.add(normalized)

        if verify_result.get("price"):
            candidates.append({
                "source": f"discovery:{evt.get('source', '')}",
                "name": f"{venue} — {verify_result['price']} oysters",
                "description": evt.get("name", ""),
                "url": evt.get("url", ""),
                "start": evt.get("start", ""),
                "venue": venue,
                "address": "",
                "verify_status": verify_result.get("status", ""),
                "price": verify_result.get("price"),
                "hours": verify_result.get("hours"),
                "_tentative": True,
            })
        else:
            # verify couldn't extract price → render as "Needs Review"
            candidates.append({
                "source": f"discovery:{evt.get('source', '')}",
                "name": f"{venue} — oysters mentioned, verify manually",
                "description": evt.get("name", ""),
                "url": evt.get("url", ""),
                "start": evt.get("start", ""),
                "venue": venue,
                "address": "",
                "verify_status": verify_result.get("status", "⚠️ Unverified"),
                "price": None,
                "hours": None,
                "_tentative": True,
                "_needs_review": True,
            })

    return candidates


def load_verify_status() -> dict:
    """Load verification status from oyster_verify.py output."""
    if not os.path.exists(STATUS_FILE):
        return {}
    import json
    with open(STATUS_FILE) as f:
        return json.load(f)



def sort_by_proximity(deals: list[dict], persona: str = "brian") -> list[dict]:
    """Sort deals by proximity score for a given persona (highest first)."""
    # `is not None` instead of `or` so a persona can explicitly opt into an
    # empty proximity table (= "no custom bonuses") without falling back to
    # the default one. Today no persona does this, but the semantics matter.
    persona_prox = get_proximity(persona)
    prox_table = persona_prox if persona_prox is not None else PROXIMITY

    def rank_key(d):
        address = (d.get("venue", "") + " " + d.get("address", "")).strip()
        prox = proximity_score(address, prox_table)
        d["_proximity"] = prox
        d["_proximity_label"] = proximity_label(prox)
        # Sort key is (inactive, -prox, -score) and ascending. Translation:
        #   active before inactive (0 < 1)
        #   higher proximity first (negated → bigger prox sorts lower)
        #   higher AI score first (negated below → bigger score sorts lower)
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


def run_persona(persona_name: str, force: bool):
    persona   = get_persona(persona_name)
    label     = persona["nav_label"]
    cache_key = f"{CACHE_KEY_BASE}_{persona_name}"

    if not force:
        cached = cache_get(cache_key)
        if cached is not None:
            age_str = cache_age(cache_key)
            print(f"\n[oyster_deals:{persona_name}] Using cache ({age_str}). --force to refresh.")
            # re-attach verify status in case oyster_verify.py ran since caching
            vstatus = load_verify_status()
            for d in cached:
                src = d.get("source", "")
                if src.startswith("discovery:"):
                    # verify_status + maps_url already baked in from collect_event_feed_candidates()
                    # under event:<url> key — venue-name lookup would overwrite with ⚠️ Unverified
                    d["_inactive"] = "Inactive" in d.get("verify_status", "")
                    continue
                venue_key = (d.get("venue") or d.get("name", "")).lower().replace(" ", "_")
                entry = vstatus.get(venue_key, {})
                d["verify_status"] = entry.get("status", "⚠️ Unverified")
                d["maps_url"]      = entry.get("maps_url", "")
                d["_inactive"]     = "Inactive" in d.get("verify_status", "")
            sorted_deals = sort_by_proximity(cached, persona_name)
            display(sorted_deals, label, from_cache=True, cache_age_str=age_str)
            return

    # known-venue path (hardcoded OYSTER_VENUES + research.txt) — unchanged
    known = get_oyster_candidates()
    # event-feed path — binary filter + venue extraction + verify
    # pass known so dedupe covers research.txt rows, not just OYSTER_VENUES
    event_feed = collect_event_feed_candidates(known)
    deals = known + event_feed

    print(f"\n  {len(known)} known-venue + {len(event_feed)} event-feed candidates for {label}")

    # attach verification status + maps links
    status = load_verify_status()
    for d in deals:
        src = d.get("source", "")
        if src.startswith("discovery:"):
            # verify_status + maps_url already baked in from collect_event_feed_candidates()
            # stored under event:<url> key — venue-name lookup would overwrite with ⚠️ Unverified
            d["_inactive"] = "Inactive" in d.get("verify_status", "")
            continue
        venue_key = (d.get("venue") or d.get("name", "")).lower().replace(" ", "_")
        entry = status.get(venue_key, {})
        d["verify_status"] = entry.get("status", "⚠️ Unverified")
        d["maps_url"]      = entry.get("maps_url", "")
        d["_inactive"]     = "Inactive" in d.get("verify_status", "")

    # Fix 1: gate venue_scrape rows behind price verification.
    # Without an AI scorer to filter weak keyword signals, require a verified
    # price before rendering venue_scrape rows as confirmed deals.
    for d in deals:
        src = d.get("source", "")
        if src == "venue_scrape":
            price = d.get("price")
            if not price:
                # try the verify status file — may have a price from oyster_verify.py
                venue_key = (d.get("venue") or d.get("name", "")).lower().replace(" ", "_")
                price = status.get(venue_key, {}).get("price")
            if not price:
                d["_needs_review"] = True
                d["_tentative"] = True  # same treatment as event-feed uncertain candidates

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

    print("\n[oyster_deals] Running oyster deals pipeline...")

    for persona_name in persona_names:
        run_persona(persona_name, force=args.force)


if __name__ == "__main__":
    main()
