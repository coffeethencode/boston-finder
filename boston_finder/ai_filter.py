"""
AI filtering via Claude Haiku.
Scores events for relevance, tracks token costs.
Falls back to keyword matching if no API key.
"""

import os
import json
import time
import requests
from . import costs
from .preferences import SOFT_RULES, hard_skip_filter
from .cache import get_scored, save_scored, prune_scored

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = "claude-haiku-4-5-20251001"

# Shared exclusions
SPORTS_EXCLUDE = [
    " vs ", " vs.", "game day", "nba ", "nfl ", "nhl ", "mlb ",
    "marathon training", "5k run", "10k run", "fun run", "road race",
    "triathlon", "swim meet", "cycling race",
    "softball league", "kickball", "dodgeball", "bowling league",
]


def sports_filter(events: list[dict]) -> list[dict]:
    out = []
    for e in events:
        text = (e["name"] + " " + e["description"]).lower()
        if not any(s in text for s in SPORTS_EXCLUDE):
            out.append(e)
    return out


def deduplicate(events: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out = []
    for e in events:
        key = e.get("url") or e.get("name", "")
        if key and key not in seen:
            seen.add(key)
            out.append(e)
    return out


def score(events: list[dict], prompt_role: str, min_score: int = 5, persona: str = "brian") -> tuple[list[dict], int, int]:
    """
    Score a list of events using Claude.
    prompt_role: describes what kinds of events to look for (injected into prompt).
    persona: cache namespace so different people get independent scores.
    Returns (events_with_score >= min_score sorted descending, n_cached, n_scored).
    """
    if not ANTHROPIC_API_KEY:
        return _keyword_fallback(events, min_score), 0, 0

    # ── pull already-scored events from cache ─────────────────────────────────
    prune_scored()
    cached_hits, needs_scoring = [], []
    for e in events:
        url = e.get("url", "")
        if url:
            cached = get_scored(url, persona)
            if cached and cached["score"] >= min_score:
                e["score"]  = cached["score"]
                e["reason"] = cached["reason"]
                cached_hits.append(e)
                continue
            elif cached:
                continue  # previously scored below threshold — skip
        needs_scoring.append(e)

    n_cached = len(cached_hits)
    n_scored = len(needs_scoring)
    print(f"  [cache] {n_cached} events from score cache, {n_scored} need scoring")
    results = list(cached_hits)

    if not needs_scoring:
        return sorted(results, key=lambda x: -x.get("score", 0)), n_cached, 0

    chunk_size = 40
    for i in range(0, len(needs_scoring), chunk_size):
        chunk = needs_scoring[i:i + chunk_size]
        batch = json.dumps(
            [{"index": j, "name": e["name"], "desc": e.get("description", ""), "raw": e.get("_raw", False)}
             for j, e in enumerate(chunk)],
            indent=2,
        )
        try:
            from pull_feedback import get_feedback_context
            feedback_ctx = get_feedback_context(persona)
        except Exception:
            feedback_ctx = ""

        system_prompt = f"""{prompt_role}

{SOFT_RULES}
{(chr(10) + feedback_ctx) if feedback_ctx else ""}
Score each event 0–10. Only return events with score >= {min_score}.
For "_raw: true" entries, extract individual events from the description and score each.
Return ONLY a JSON array: [{{"index": 0, "score": 7, "reason": "brief reason"}}]"""

        try:
            _t0 = time.time()
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "anthropic-beta": "prompt-caching-2024-07-31",
                    "content-type": "application/json",
                },
                json={
                    "model": MODEL,
                    "max_tokens": 2000,
                    "system": [
                        {
                            "type": "text",
                            "text": system_prompt,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                    "messages": [{"role": "user", "content": f"Events:\n{batch}"}],
                },
                timeout=30,
            )
            if r.status_code != 200:
                results += _keyword_fallback(chunk, min_score)
                continue

            body = r.json()
            usage = body.get("usage", {})
            costs.log_call(
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
                source="boston_finder",
                duration_ms=int((time.time() - _t0) * 1000),
            )

            content = body["content"][0]["text"]
            start = content.index("[")
            end = content.rindex("]") + 1
            ratings = json.loads(content[start:end])
            rated_indices = set()
            for rating in ratings:
                idx = rating.get("index", -1)
                if 0 <= idx < len(chunk):
                    s = rating.get("score", 0)
                    r = rating.get("reason", "")
                    url = chunk[idx].get("url", "")
                    name = chunk[idx].get("name", "")
                    rated_indices.add(idx)
                    if url:
                        save_scored(url, s, r, name, persona)
                    if s >= min_score:
                        chunk[idx]["score"] = s
                        chunk[idx]["reason"] = r
                        results.append(chunk[idx])
            # save score=0 for anything the AI didn't mention (below threshold, not worth returning)
            for idx, e in enumerate(chunk):
                if idx not in rated_indices:
                    url = e.get("url", "")
                    if url:
                        save_scored(url, 0, "below threshold", e.get("name", ""), persona)
        except Exception as ex:
            print(f"  [ai_filter] {ex} — keyword fallback")
            results += _keyword_fallback(chunk, min_score)

    return sorted(results, key=lambda x: -x.get("score", 0)), n_cached, n_scored


def _keyword_fallback(events: list[dict], min_score: int) -> list[dict]:
    keywords = [
        "oyster", "gala", "fundraiser", "benefit", "reception", "mixer",
        "public records", "open meeting", "government", "transparency",
        "civic", "nonprofit", "charity", "happy hour", "tasting", "wine",
        "cocktail", "networking", "panel", "forum", "advocacy", "fashion",
        "press", "media", "award", "dinner", "law", "policy",
    ]
    scored = []
    for e in events:
        if e.get("_raw"):
            continue
        text = (e["name"] + " " + e.get("description", "")).lower()
        hits = sum(1 for k in keywords if k in text)
        if hits >= max(1, min_score // 3):
            e["score"] = hits
            e["reason"] = ""
            scored.append(e)
    return sorted(scored, key=lambda x: -x["score"])
