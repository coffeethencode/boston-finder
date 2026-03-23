#!/usr/bin/env python3
"""
Chloe's Boston event digest.
Art, food, drinks — fancy version.

Usage:
    python3 chloe_events.py
    python3 chloe_events.py --days 14
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
from boston_finder               import costs

CHLOE_PROMPT = """You are filtering Boston events for Chloe, who wants upscale, interesting things to do in Boston.
She loves:
- Art: gallery openings, museum events, art shows, artist talks, art fairs, photography exhibits, sculpture
- Food & drink: wine tastings, wine dinners, chef's table experiences, cocktail classes, food festivals, upscale restaurant events, mixology
- Fancy experiences: galas, benefit dinners, charity auctions, cultural receptions, film premieres, theater openings
- Design, fashion, and aesthetics — runway shows, design events, interior/architecture tours
- Wellness and beauty events that are upscale (spa launches, product launches, brand events)
- Anything cultured, beautiful, or scene-y

Lower priority for her:
- Pure civic/government/policy events (unless they're glamorous)
- Sports
- Basic networking mixers with no food/drink/art angle

Score 0-10. Only return events with score >= 5."""

import boston_finder.html_output as _html_mod

CHLOE_OUTPUT = "/Users/brian/chloe_events.html"


def generate_chloe_html(events: list[dict], today: datetime, days: int):
    orig = _html_mod.OUTPUT_FILE
    _html_mod.OUTPUT_FILE = CHLOE_OUTPUT
    try:
        _html_mod.generate(events, today, days, persona="chloe")
    finally:
        _html_mod.OUTPUT_FILE = orig

    # deploy chloe.html to Netlify alongside brian's index.html
    import os, shutil, subprocess
    repo = _html_mod.GITHUB_REPO
    deploy_path = os.path.join(repo, "docs", "chloe.html")
    if os.path.exists(CHLOE_OUTPUT) and os.path.isdir(repo):
        shutil.copy(CHLOE_OUTPUT, deploy_path)
        subprocess.run(["git", "-C", repo, "add", "docs/chloe.html"], check=True)
        result = subprocess.run(
            ["git", "-C", repo, "diff", "--cached", "--quiet"], capture_output=True
        )
        if result.returncode != 0:
            ts = datetime.now().strftime("%Y-%m-%d %-I:%M %p")
            subprocess.run(
                ["git", "-C", repo, "commit", "-m", f"Deploy: Chloe events {ts}"],
                check=True, capture_output=True
            )
            subprocess.run(["git", "-C", repo, "push"], check=True, capture_output=True)
            print(f"  [deploy] → https://highendeventfinder.netlify.app/chloe")


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
    print(f"\nSearching Boston events for Chloe: {today.strftime('%Y-%m-%d')} → {end.strftime('%Y-%m-%d')}")

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
    print(f"\n  {n_total} events after filters. Scoring for Chloe...\n")

    if not args.no_ai:
        filtered, n_cached, n_scored = score(all_events, CHLOE_PROMPT, persona="chloe")
    else:
        from boston_finder.ai_filter import _keyword_fallback
        filtered = _keyword_fallback(all_events, 1)
        n_cached, n_scored = 0, 0

    print(f"\n  Enriching {len(filtered)} events (times + prices)...")
    enrich_events(filtered)

    costs.log_run(run_start, n_total, n_cached, n_scored)

    print(f"\n  {len(filtered)} events for Chloe this week")
    costs.print_summary()

    generate_chloe_html(filtered, today, args.days)


if __name__ == "__main__":
    main()
