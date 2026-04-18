#!/usr/bin/env python3
"""
Pull event feedback from Netlify Forms → ~/boston_finder_feedback.json

Run this any time to sync feedback that Brian or Chloe submitted via the web UI.
The feedback is then picked up by the AI scoring prompt on the next run.

Usage:
    python3 pull_feedback.py          # sync + show summary
    python3 pull_feedback.py --show   # just show current feedback
"""

import sys
import json
import os
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FEEDBACK_FILE = os.path.expanduser("~/boston_finder_feedback.json")
NETLIFY_SITE  = "highendeventfinder"


def _load() -> list:
    if not os.path.exists(FEEDBACK_FILE):
        return []
    with open(FEEDBACK_FILE) as f:
        return json.load(f)


def _save(data: list):
    with open(FEEDBACK_FILE, "w") as f:
        json.dump(data, f, indent=2)


def pull():
    """Fetch submissions from Netlify Forms API via CLI."""
    form_id = _get_form_id()
    if not form_id:
        return []
    result = subprocess.run(
        ["netlify", "api", "listFormSubmissions", "--data", json.dumps({"formId": form_id})],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return []
    try:
        data = json.loads(result.stdout)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _get_site_id() -> str:
    """Get numeric site ID from site name."""
    result = subprocess.run(
        ["netlify", "api", "getSite", "--data", json.dumps({"site_id": NETLIFY_SITE})],
        capture_output=True, text=True
    )
    try:
        return json.loads(result.stdout).get("id", NETLIFY_SITE)
    except Exception:
        return NETLIFY_SITE


def _get_form_id() -> str:
    """Find the form ID for 'event-feedback' on our site."""
    site_id = _get_site_id()
    result = subprocess.run(
        ["netlify", "api", "listSiteForms", "--data", json.dumps({"site_id": site_id})],
        capture_output=True, text=True
    )
    try:
        forms = json.loads(result.stdout)
        if isinstance(forms, list):
            for f in forms:
                if f.get("name") == "event-feedback":
                    return f["id"]
    except Exception:
        pass
    return ""


def sync():
    """Pull Netlify submissions and merge into local feedback file."""
    existing = _load()
    existing_ids = {e.get("netlify_id") for e in existing if e.get("netlify_id")}

    form_id = _get_form_id()
    if not form_id:
        print("  [feedback] form not yet registered on Netlify (submit one feedback first)")
        return existing

    submissions = pull()
    new_count = 0
    for s in submissions:
        sid = s.get("id", "")
        if sid in existing_ids:
            continue
        data = s.get("data", s)
        entry = {
            "netlify_id":  sid,
            "persona":     data.get("persona", ""),
            "vote":        data.get("vote", ""),
            "event_url":   data.get("event_url", ""),
            "event_name":  data.get("event_name", ""),
            "created_at":  s.get("created_at", datetime.now().isoformat()),
        }
        existing.append(entry)
        new_count += 1

    _save(existing)
    print(f"  Synced {new_count} new feedback entries ({len(existing)} total)")
    return existing


def show(feedback: list):
    from collections import defaultdict
    by_persona = defaultdict(lambda: {"up": [], "down": []})
    for f in feedback:
        by_persona[f["persona"]][f["vote"]].append(f["event_name"] or f["event_url"][:60])

    for persona, votes in sorted(by_persona.items()):
        print(f"\n  {persona.upper()}")
        if votes["up"]:
            print(f"    👍 liked ({len(votes['up'])}):")
            for n in votes["up"][-5:]:
                print(f"       {n}")
        if votes["down"]:
            print(f"    👎 skipped ({len(votes['down'])}):")
            for n in votes["down"][-5:]:
                print(f"       {n}")


def get_feedback_context(persona: str) -> str:
    """
    Returns a string injected into the AI prompt summarising this persona's feedback.
    Called from ai_filter.py before scoring.
    """
    feedback = _load()
    liked   = [f["event_name"] for f in feedback if f["persona"] == persona and f["vote"] == "up"  and f["event_name"]][-20:]
    skipped = [f["event_name"] for f in feedback if f["persona"] == persona and f["vote"] == "down" and f["event_name"]][-20:]
    parts = []
    if liked:
        parts.append(f"Previously liked by {persona}: {', '.join(liked)}")
    if skipped:
        parts.append(f"Previously skipped by {persona} (score lower): {', '.join(skipped)}")
    return "\n".join(parts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--show", action="store_true", help="Just show current feedback without syncing")
    args = parser.parse_args()

    if args.show:
        show(_load())
    else:
        feedback = sync()
        show(feedback)
