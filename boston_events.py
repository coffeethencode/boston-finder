#!/usr/bin/env python3
"""
Boston daily event digest.
Runs every morning — finds high-status events for the next 7 days.

Usage:
    python3 boston_events.py
    python3 boston_events.py --days 3
    python3 boston_events.py --no-ai
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
from boston_finder.notify       import send
from boston_finder.personas     import get_prompt
from boston_finder               import costs


def display(events: list[dict], today: datetime, days: int):
    if not events:
        print("\nNo matching events found.\n")
        return

    by_date: dict[str, list] = {}
    for e in events:
        raw = e.get("start", "")
        try:
            if "T" in raw:
                dt = datetime.fromisoformat(raw.replace("Z", ""))
                d = dt.strftime("%A, %B %-d")
                t = dt.strftime("%-I:%M %p")
            else:
                dt = datetime.strptime(raw[:10], "%Y-%m-%d")
                d  = dt.strftime("%A, %B %-d")
                t  = ""
        except Exception:
            d, t = "Date unknown", ""
        e["_day"] = d
        e["_time"] = t
        by_date.setdefault(d, []).append(e)

    end_date = today + timedelta(days=days - 1)
    print(f"\n{'═'*62}")
    print(f"  BOSTON EVENTS  |  {today.strftime('%B %-d')} – {end_date.strftime('%B %-d, %Y')}")
    print(f"{'═'*62}")

    for day, day_events in by_date.items():
        day_events.sort(key=lambda x: -x.get("score", 0))
        print(f"\n▸ {day}")
        print("─" * 55)
        for e in day_events:
            score_str = f"  ★{e['score']}" if e.get("score") else ""
            print(f"\n  {e['name']}{score_str}")
            parts = [p for p in [e.get("_time"), e.get("price"), e.get("venue"), e.get("address")] if p]
            if parts:
                print(f"  {' | '.join(parts)}")
            if e.get("reason"):
                print(f"  → {e['reason']}")
            if e.get("url"):
                print(f"  {e['url']}")

    print(f"\n{'═'*62}")
    print(f"  {len(events)} relevant events this week")
    costs.print_summary()
    print(f"{'═'*62}\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days",  type=int, default=7)
    parser.add_argument("--no-ai", action="store_true")
    args = parser.parse_args()

    run_start = datetime.now()

    # sync feedback before scoring so today's run reflects it
    try:
        import pull_feedback
        pull_feedback.sync()
    except Exception as ex:
        print(f"  [feedback] sync skipped: {ex}")

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end   = today + timedelta(days=args.days - 1)
    print(f"\nSearching Boston events: {today.strftime('%Y-%m-%d')} → {end.strftime('%Y-%m-%d')}")

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
    print(f"\n  {n_total} events after filters. Scoring...\n")

    if not args.no_ai:
        filtered, n_cached, n_scored = score(all_events, get_prompt("brian"))
    else:
        filtered = __import__("boston_finder.ai_filter", fromlist=["_keyword_fallback"])._keyword_fallback(all_events, 1)
        n_cached, n_scored = 0, 0

    filtered = location_filter(filtered)

    print(f"\n  Enriching {len(filtered)} events (times + prices)...")
    enrich_events(filtered)

    # source attribution summary
    from collections import Counter
    src_counts = Counter(e.get("source", "unknown").split(":")[0] for e in filtered)
    print(f"\n  Sources: " + "  ".join(f"{s}={n}" for s, n in src_counts.most_common()))

    costs.log_run(run_start, n_total, n_cached, n_scored)
    display(filtered, today, args.days)
    from boston_finder.html_output import generate
    generate(filtered, today, args.days, persona="brian")


if __name__ == "__main__":
    main()
