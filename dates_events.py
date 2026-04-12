#!/usr/bin/env python3
"""
Date ideas digest for Boston.
Restaurants, experiences, activities — curated for great dates.

Usage:
    python3 dates_events.py
    python3 dates_events.py --days 14
"""

import sys
import time
import argparse
from datetime import datetime, timedelta

sys.path.insert(0, "/Users/brian/python-projects")
from boston_finder.sources      import get_sources
from boston_finder.fetchers     import fetch_source, enrich_events
from boston_finder.ai_filter    import sports_filter, deduplicate, score
from boston_finder.preferences  import hard_skip_filter
from boston_finder.location     import location_filter
from boston_finder               import costs

DATES_PROMPT = """You are filtering Boston events for date ideas — things two people would enjoy doing together.

Great date events:
- Food & drink: wine tastings, prix fixe dinners, cocktail classes, food festivals, tasting menus, new restaurant openings
- Arts & culture: gallery openings, museum exhibits, live music, jazz, comedy shows, theater, film screenings
- Experiences: cooking classes, pottery, dance lessons, sunset cruises, rooftop events, seasonal markets
- Outdoor: scenic walks, garden events, waterfront activities, bike tours
- Nightlife: speakeasy events, live DJ sets, themed parties, rooftop bars

Lower priority:
- Kids/family-focused events
- Pure networking or professional events
- Large-scale sports (unless it's a unique experience like courtside)
- Conferences, lectures, or panels with no social component

Score 0-10. Only return events with score >= 5."""

import boston_finder.html_output as _html_mod

DATES_OUTPUT = "/Users/brian/dates_events.html"


def generate_dates_html(events: list[dict], today: datetime, days: int):
    orig = _html_mod.OUTPUT_FILE
    _html_mod.OUTPUT_FILE = DATES_OUTPUT
    try:
        _html_mod.generate(events, today, days, persona="dates")
    finally:
        _html_mod.OUTPUT_FILE = orig

    # deploy dates.html to Netlify
    import os, shutil, subprocess
    repo = _html_mod.GITHUB_REPO
    deploy_path = os.path.join(repo, "docs", "dates.html")
    if os.path.exists(DATES_OUTPUT) and os.path.isdir(repo):
        shutil.copy(DATES_OUTPUT, deploy_path)
        subprocess.run(["git", "-C", repo, "add", "docs/dates.html"], check=True)
        result = subprocess.run(
            ["git", "-C", repo, "diff", "--cached", "--quiet"], capture_output=True
        )
        if result.returncode != 0:
            ts = datetime.now().strftime("%Y-%m-%d %-I:%M %p")
            subprocess.run(
                ["git", "-C", repo, "commit", "-m", f"Deploy: Date ideas {ts}"],
                check=True, capture_output=True
            )
            subprocess.run(["git", "-C", repo, "push"], check=True, capture_output=True)
            print(f"  [deploy] → https://highendeventfinder.netlify.app/dates")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days",  type=int, default=7)
    parser.add_argument("--no-ai", action="store_true")
    args = parser.parse_args()

    run_start = datetime.now()

    try:
        import pull_feedback
        pull_feedback.sync()
    except Exception as ex:
        print(f"  [feedback] sync skipped: {ex}")

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end   = today + timedelta(days=args.days - 1)
    print(f"\nSearching Boston date ideas: {today.strftime('%Y-%m-%d')} → {end.strftime('%Y-%m-%d')}")

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
    print(f"\n  {n_total} events after filters. Scoring for dates...\n")

    if not args.no_ai:
        filtered, n_cached, n_scored = score(all_events, DATES_PROMPT, persona="dates")
    else:
        from boston_finder.ai_filter import _keyword_fallback
        filtered = _keyword_fallback(all_events, 1)
        n_cached, n_scored = 0, 0

    filtered = location_filter(filtered, persona="dates")

    print(f"\n  Enriching {len(filtered)} events (times + prices)...")
    enrich_events(filtered)

    costs.log_run(run_start, n_total, n_cached, n_scored)

    print(f"\n  {len(filtered)} date ideas this week")
    costs.print_summary()

    generate_dates_html(filtered, today, args.days)


if __name__ == "__main__":
    main()
