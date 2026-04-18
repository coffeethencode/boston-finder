#!/usr/bin/env python3
"""
Kirk's Boston event digest.
VC/startup events, tech meetups, presales community — wider travel range.

Usage:
    python3 kirk_events.py
    python3 kirk_events.py --days 14
"""

import sys
import time
import argparse
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from boston_finder.sources      import get_sources
from boston_finder.fetchers     import fetch_source, enrich_events
from boston_finder.ai_filter    import sports_filter, deduplicate, score
from boston_finder.preferences  import hard_skip_filter
from boston_finder.location     import location_filter
from boston_finder.personas     import get_persona, get_prompt
from boston_finder               import costs

import boston_finder.html_output as _html_mod

KIRK_OUTPUT = "/Users/brian/kirk_events.html"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days",  type=int, default=7)
    parser.add_argument("--no-ai", action="store_true")
    args = parser.parse_args()

    get_persona("kirk")  # fail fast if archived

    run_start = datetime.now()

    try:
        import pull_feedback
        pull_feedback.sync()
    except Exception as ex:
        print(f"  [feedback] sync skipped: {ex}")

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end   = today + timedelta(days=args.days - 1)
    print(f"\nSearching Boston events for Kirk: {today.strftime('%Y-%m-%d')} → {end.strftime('%Y-%m-%d')}")

    all_events: list[dict] = []
    seen_urls:  set[str]   = set()

    for source in get_sources("events"):
        print(f"  [{source['name']}]")
        for e in fetch_source(source, today, end):
            if e.get("url") and e["url"] not in seen_urls:
                seen_urls.add(e["url"])
                all_events.append(e)
            elif not e.get("url"):
                all_events.append(e)
        time.sleep(0.3)

    all_events = hard_skip_filter(sports_filter(deduplicate(all_events)))
    n_total = len(all_events)
    print(f"\n  {n_total} events after filters. Scoring for Kirk...\n")

    if not args.no_ai:
        filtered, n_cached, n_scored = score(all_events, get_prompt("kirk"), persona="kirk")
    else:
        from boston_finder.ai_filter import _keyword_fallback
        filtered = _keyword_fallback(all_events, 1)
        n_cached, n_scored = 0, 0

    filtered = location_filter(filtered, persona="kirk")

    print(f"\n  Enriching {len(filtered)} events (times + prices)...")
    enrich_events(filtered)

    costs.log_run(run_start, n_total, n_cached, n_scored)

    print(f"\n  {len(filtered)} events for Kirk this week")
    costs.print_summary()

    # generate HTML through the shared pipeline
    orig = _html_mod.OUTPUT_FILE
    _html_mod.OUTPUT_FILE = KIRK_OUTPUT
    try:
        _html_mod.generate(filtered, today, args.days, persona="kirk")
    finally:
        _html_mod.OUTPUT_FILE = orig


if __name__ == "__main__":
    main()
