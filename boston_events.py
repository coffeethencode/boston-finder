#!/usr/bin/env python3
"""
Boston daily event digest.
Runs every morning and can generate one persona or all active personas.

Usage:
    python3 boston_events.py
    python3 boston_events.py --persona all
    python3 boston_events.py --persona kirk --days 3
    python3 boston_events.py --no-ai
"""

import sys
import time
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter
import os

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from boston_finder.sources      import get_sources
from boston_finder.fetchers     import fetch_source, enrich_events
from boston_finder.ai_filter    import sports_filter, deduplicate, score
from boston_finder.preferences  import hard_skip_filter
from boston_finder.location     import location_filter
from boston_finder.personas     import active_personas, get_persona, get_prompt
from boston_finder               import costs

LOCAL_OUTPUTS = {
    "brian": os.path.expanduser("~/boston_events.html"),
    "dates": os.path.expanduser("~/dates_events.html"),
    "kirk": os.path.expanduser("~/kirk_events.html"),
}


def display(events: list[dict], today: datetime, days: int, persona_label: str):
    if not events:
        print("\nNo matching events found.\n")
        return

    by_date: dict[str, list] = {}
    date_key: dict[str, datetime] = {}
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
            dt = datetime.max
            d, t = "Date unknown", ""
        e["_day"] = d
        e["_time"] = t
        if d not in date_key:
            date_key[d] = dt
        by_date.setdefault(d, []).append(e)

    end_date = today + timedelta(days=days - 1)
    print(f"\n{'═'*62}")
    print(f"  {persona_label.upper()} EVENTS  |  {today.strftime('%B %-d')} – {end_date.strftime('%B %-d, %Y')}")
    print(f"{'═'*62}")

    for day in sorted(by_date, key=lambda d: date_key.get(d, datetime.max)):
        day_events = sorted(by_date[day], key=lambda x: -x.get("score", 0))
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


def fetch_shared(days: int) -> list[dict]:
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end   = today + timedelta(days=days - 1)
    print(f"\nFetching Boston events: {today.strftime('%Y-%m-%d')} → {end.strftime('%Y-%m-%d')}")

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

    return hard_skip_filter(sports_filter(deduplicate(all_events)))


def run_persona(persona_name: str, days: int, no_ai: bool, shared_events: list[dict] | None = None):
    persona = get_persona(persona_name)
    run_start = datetime.now()

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end   = today + timedelta(days=days - 1)
    if shared_events is None:
        print(f"\nSearching Boston events ({persona['nav_label']}): {today.strftime('%Y-%m-%d')} → {end.strftime('%Y-%m-%d')}")
        all_events = fetch_shared(days)
    else:
        all_events = [dict(e) for e in shared_events]

    n_total = len(all_events)
    print(f"\n  {n_total} events after filters. Scoring for {persona['nav_label']}...\n")

    if not no_ai:
        filtered, n_cached, n_scored = score(all_events, get_prompt(persona_name), persona=persona_name)
    else:
        filtered = __import__("boston_finder.ai_filter", fromlist=["_keyword_fallback"])._keyword_fallback(all_events, 1)
        n_cached, n_scored = 0, 0

    filtered = location_filter(filtered, persona=persona_name)

    print(f"\n  Enriching {len(filtered)} events (times + prices)...")
    enrich_events(filtered)

    src_counts = Counter(e.get("source", "unknown").split(":")[0] for e in filtered)
    print(f"\n  Sources: " + "  ".join(f"{s}={n}" for s, n in src_counts.most_common()))

    costs.log_run(run_start, n_total, n_cached, n_scored)
    display(filtered, today, days, persona["nav_label"])
    import boston_finder.html_output as html_output
    original_output = html_output.OUTPUT_FILE
    html_output.OUTPUT_FILE = LOCAL_OUTPUTS.get(persona_name, original_output)
    try:
        html_output.generate(filtered, today, days, persona=persona_name)
    finally:
        html_output.OUTPUT_FILE = original_output


def main():
    parser = argparse.ArgumentParser()
    active_names = [p["name"] for p in active_personas()]
    parser.add_argument("--persona", choices=active_names + ["all"], default="brian")
    parser.add_argument("--days",  type=int, default=7)
    parser.add_argument("--no-ai", action="store_true")
    args = parser.parse_args()

    # sync feedback before scoring so today's run reflects it
    try:
        import pull_feedback
        pull_feedback.sync()
    except Exception as ex:
        print(f"  [feedback] sync skipped: {ex}")

    if args.persona == "all":
        shared = fetch_shared(args.days)
        for persona_name in active_names:
            run_persona(persona_name, args.days, args.no_ai, shared_events=shared)
    else:
        run_persona(args.persona, args.days, args.no_ai)


if __name__ == "__main__":
    main()
