#!/usr/bin/env python3
"""
Boston oyster deals finder.
Runs weekly — builds a definitive list of where to get dollar/cheap oysters.
Results are cached for 7 days and referenced by the daily events digest.

Usage:
    python3 oyster_deals.py          # use cache if fresh, else re-fetch
    python3 oyster_deals.py --force  # force re-fetch even if cache is fresh
"""

import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from boston_finder.sources       import get_sources
from boston_finder.fetchers      import fetch_source
from boston_finder.ai_filter     import deduplicate, score
from boston_finder.oyster_sources import get_all as get_oyster_candidates
from boston_finder.notify        import send
from boston_finder.cache         import get as cache_get, set as cache_set, age as cache_age
from boston_finder                import costs

CACHE_KEY  = "oyster_deals"
CACHE_TTL  = 168  # 7 days in hours

OYSTER_PROMPT = """You are building a definitive list of Boston-area oyster happy hours and deals.
Look for:
- Dollar oyster hours (e.g. $1 oysters during happy hour)
- Half-price oyster specials
- Oyster tasting events
- Raw bar deals at upscale seafood spots
- Any restaurant/bar running a recurring oyster promotion

For each match extract: venue name, deal details, days/hours if mentioned, neighborhood.
Score 0–10 for how good the deal is (10 = dollar oysters at a great venue, 5 = modest discount)."""


def display(deals: list[dict], from_cache: bool, cache_age_str: str):
    print(f"\n{'═'*62}")
    print(f"  BOSTON OYSTER DEALS  |  {datetime.now().strftime('%B %-d, %Y')}")
    if from_cache:
        print(f"  (cached {cache_age_str} — runs fresh weekly)")
    print(f"{'═'*62}")

    if not deals:
        print("\n  No oyster deals found.\n")
        return

    for d in deals:
        score_str = f"  ★{d['score']}" if d.get("score") else ""
        print(f"\n  {d['name']}{score_str}")
        parts = [p for p in [d.get("venue"), d.get("address")] if p]
        if parts:
            print(f"  {' | '.join(parts)}")
        if d.get("reason"):
            print(f"  → {d['reason']}")
        if d.get("url"):
            print(f"  {d['url']}")

    print(f"\n{'═'*62}")
    print(f"  {len(deals)} deals found")
    costs.print_summary()
    print(f"{'═'*62}\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Ignore cache and re-fetch")
    args = parser.parse_args()

    # check cache first
    if not args.force:
        cached = cache_get(CACHE_KEY)
        if cached is not None:
            print(f"\n[oyster_deals] Using cached data ({cache_age(CACHE_KEY)}). Use --force to refresh.")
            display(cached, from_cache=True, cache_age_str=cache_age(CACHE_KEY))
            return

    print(f"\n[oyster_deals] Fetching fresh oyster deal data...")

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end   = today + timedelta(days=14)  # look 2 weeks out for recurring events

    all_events: list[dict] = []
    seen_urls:  set[str]   = set()

    # known venues + deep research file
    print("  [Known venues + research file]")
    all_events += get_oyster_candidates()

    # eventbrite + do617 food sources
    for source in get_sources("food"):
        print(f"  [{source['name']}]")
        for e in fetch_source(source, today, end):
            if e.get("url") and e["url"] not in seen_urls:
                seen_urls.add(e["url"])
                all_events.append(e)
            elif not e.get("url"):
                all_events.append(e)

    all_events = deduplicate(all_events)
    oyster_events = [
        e for e in all_events
        if any(k in (e["name"] + e.get("description", "")).lower()
               for k in ["oyster", "raw bar", "seafood", "happy hour", "half price", "dollar", "$1"])
    ] or all_events

    print(f"\n  {len(oyster_events)} candidates. Scoring for oyster relevance...\n")
    deals, _, _ = score(oyster_events, OYSTER_PROMPT, min_score=5)

    # cache for 7 days
    cache_set(CACHE_KEY, deals, ttl_hours=CACHE_TTL)
    print(f"  Cached for {CACHE_TTL // 24} days.")

    display(deals, from_cache=False, cache_age_str="")
    if deals:
        send(deals, today, title="Boston Oyster Deals")


if __name__ == "__main__":
    main()
