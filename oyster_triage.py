#!/usr/bin/env python3
# ruff: noqa: E402  # deliberate: sys.path.insert must run before package imports
"""
Oyster deal triage — combines deal score, venue quality, proximity, and your ratings
into a single ranked list sorted by what's actually worth going to.

Run monthly or whenever you want a fresh ranking.
Results saved to ~/oyster_triage.json and printed ranked.

Usage:
    python3 oyster_triage.py          # research + rank all deals
    python3 oyster_triage.py --rank   # just re-rank from cached triage data
"""

import sys
import json
import os
import argparse
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from boston_finder.cache    import get as cache_get
from boston_finder.location import score as proximity_score, label as proximity_label
from boston_finder.ratings  import score as personal_score, is_skipped, summary as ratings_summary
from boston_finder           import costs

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
TRIAGE_FILE = os.path.expanduser("~/oyster_triage.json")
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

# ── Scoring weights (must sum to 1.0) ─────────────────────────────────────────
WEIGHTS = {
    "deal":      0.35,   # how good is the price/deal
    "quality":   0.30,   # venue quality, oyster sourcing, scene
    "proximity": 0.25,   # how easy to get to from South End
    "personal":  0.10,   # your own rating (neutral=5 if unvisited)
}


def research_venue(name: str, address: str, deal_desc: str) -> dict:
    """Ask Claude to assess a venue's quality based on its description."""
    if not ANTHROPIC_API_KEY:
        return {"quality_score": 5, "vibe": "unknown", "oyster_quality": "unknown", "notes": ""}

    prompt = f"""Research this Boston restaurant/bar for someone deciding whether to go for oysters:

Venue: {name}
Location: {address}
Deal: {deal_desc}

Assess:
1. Oyster quality (sourcing, reputation — Wellfleet/Duxbury/Island Creek = top tier)
2. Venue vibe (upscale? dive? scene? good for networking/socializing?)
3. Is it worth making a trip from South End Boston?

Return JSON only:
{{"quality_score": 1-10, "vibe": "one line description", "oyster_quality": "top/good/average/unknown", "notes": "1-2 sentences"}}"""

    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 300,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=15,
        )
        if r.status_code != 200:
            return {"quality_score": 5, "vibe": "unknown", "oyster_quality": "unknown", "notes": ""}

        body = r.json()
        usage = body.get("usage", {})
        costs.log_call(usage.get("input_tokens", 0), usage.get("output_tokens", 0), "oyster_triage")

        text = body["content"][0]["text"]
        start = text.index("{")
        end = text.rindex("}") + 1
        return json.loads(text[start:end])
    except Exception as ex:
        return {"quality_score": 5, "vibe": "unknown", "oyster_quality": "unknown", "notes": str(ex)}


def combined_score(deal: dict) -> float:
    def safe(val, default=5):
        try: return float(val)
        except (TypeError, ValueError): return float(default)
    d = safe(deal.get("deal_score", 5)) / 10
    q = safe(deal.get("quality_score", 5)) / 10
    p = proximity_score(deal.get("address", "")) / 10
    r = personal_score(deal.get("venue", deal.get("name", ""))) / 10
    return round(
        d * WEIGHTS["deal"] +
        q * WEIGHTS["quality"] +
        p * WEIGHTS["proximity"] +
        r * WEIGHTS["personal"],
        3
    )


def load_triage() -> list[dict]:
    if not os.path.exists(TRIAGE_FILE):
        return []
    with open(TRIAGE_FILE) as f:
        return json.load(f)


def save_triage(data: list[dict]):
    with open(TRIAGE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def display(deals: list[dict]):
    print(f"\n{'═'*65}")
    print(f"  OYSTER DEAL TRIAGE  |  {datetime.now().strftime('%B %-d, %Y')}")
    print(f"  Ranked by: deal({int(WEIGHTS['deal']*100)}%) + quality({int(WEIGHTS['quality']*100)}%) + proximity({int(WEIGHTS['proximity']*100)}%) + personal({int(WEIGHTS['personal']*100)}%)")
    print(f"{'═'*65}")

    # group by proximity tier
    tiers = {"nearby / easy": [], "doable": [], "hike / expedition": []}
    for d in deals:
        prox = proximity_score(d.get("address", ""))
        if prox >= 7:
            tiers["nearby / easy"].append(d)
        elif prox >= 5:
            tiers["doable"].append(d)
        else:
            tiers["hike / expedition"].append(d)

    for tier_name, tier_deals in tiers.items():
        if not tier_deals:
            continue
        print(f"\n▸ {tier_name.upper()}")
        print("─" * 55)
        for d in tier_deals:
            final = d.get("final_score", 0)
            skipped = d.get("_skipped", False)
            venue = d.get("venue") or d.get("name", "")
            deal_str = d.get("description", "")
            prox_lbl = proximity_label(proximity_score(d.get("address", "")))
            oyster_q = d.get("oyster_quality", "")
            vibe = d.get("vibe", "")
            notes = d.get("notes", "")

            if skipped:
                print(f"\n  ~~{venue}~~ [skipped]")
                continue

            print(f"\n  {venue}  [{final:.2f}]")
            print(f"  {deal_str}")
            if d.get("address"):
                print(f"  📍 {d['address']} ({prox_lbl})", end="")
            if oyster_q and oyster_q != "unknown":
                print(f"  |  🦪 {oyster_q}", end="")
            print()
            if vibe and vibe != "unknown":
                print(f"  → {vibe}")
            if notes:
                print(f"  {notes}")
            if d.get("url"):
                print(f"  {d['url']}")

    print(f"\n{'═'*65}")
    costs.print_summary()
    print(f"{'═'*65}\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rank", action="store_true", help="Re-rank existing triage data without re-researching")
    parser.add_argument("--persona", default="brian",
                        help="persona whose cached oyster_deals to read (default: brian)")
    args = parser.parse_args()

    if args.rank:
        deals = load_triage()
        if not deals:
            print("No triage data yet. Run without --rank first.")
            sys.exit(1)
    else:
        # load from oyster deals cache — persona-scoped since the refactor,
        # with legacy fallback for caches written by the pre-unification script
        cached = cache_get(f"oyster_deals_{args.persona}") or cache_get("oyster_deals")
        if not cached:
            print(f"No cached oyster deals for persona '{args.persona}'. "
                  f"Run `python3 oyster_deals.py --persona {args.persona} --force` first.")
            sys.exit(1)

        print(f"\nResearching {len(cached)} venues for quality + vibe...\n")
        deals = []
        for i, deal in enumerate(cached):
            venue = deal.get("venue") or deal.get("name", "")
            print(f"  [{i+1}/{len(cached)}] {venue}")

            research = research_venue(
                name=venue,
                address=deal.get("address", ""),
                deal_desc=deal.get("description", ""),
            )
            deal.update(research)
            deals.append(deal)

        save_triage(deals)
        print(f"\n  Triage data saved to {TRIAGE_FILE}")

    # apply personal ratings + skip flags
    for d in deals:
        venue = d.get("venue") or d.get("name", "")
        d["_skipped"] = is_skipped(venue)
        d["deal_score"] = d.get("score", 5)
        d["final_score"] = combined_score(d)

    # sort: skipped to bottom, then by final score
    deals.sort(key=lambda x: (x.get("_skipped", False), -x.get("final_score", 0)))

    display(deals)

    # show your ratings at the bottom
    ratings = ratings_summary()
    if ratings != "No venues rated yet.":
        print("Your ratings:\n" + ratings + "\n")


if __name__ == "__main__":
    main()
