"""
AI filtering via Claude Haiku.
Scores events for relevance, tracks token costs.
Falls back to keyword matching if no API key.
"""

import os
import json
import re
import time
import requests
from datetime import datetime
from . import costs
from .preferences import SOFT_RULES, hard_skip_filter
from .cache import get_scored, save_scored, prune_scored, get_extracted, save_extracted

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


def _normalize_name(name: str) -> str:
    n = name.lower().strip()
    n = re.sub(r'\s+', ' ', n)
    n = re.sub(r'[^a-z0-9 ]', '', n)
    for filler in ['at boston', 'in boston', 'boston ma', '- boston', 'boston ']:
        n = n.replace(filler, '')
    return n.strip()[:60]


def deduplicate(events: list[dict]) -> list[dict]:
    """Dedup by URL first, then by normalized (name, date). URL-having entries win."""
    url_seen: set[str] = set()
    name_seen: set[str] = set()
    out = []
    # events with URLs first — they're the canonical version
    for e in sorted(events, key=lambda e: (0 if e.get('url') else 1)):
        url = (e.get('url') or '').strip()
        name = _normalize_name(e.get('name') or '')
        date = (e.get('start') or '')[:10]
        if url and url in url_seen:
            continue
        name_key = f"{name}|{date}"
        if name and name_key in name_seen:
            continue
        if url:
            url_seen.add(url)
        if name:
            name_seen.add(name_key)
        out.append(e)
    return out


def _extract_raw_events(raw_pages: list[dict]) -> list[dict]:
    """Use AI to extract individual events from scraped page blobs. One API call per page."""
    if not ANTHROPIC_API_KEY or not raw_pages:
        return []
    extracted = []
    today_str = datetime.now().strftime("%Y-%m-%d")
    system = f"""Extract all upcoming events from this web page. Today is {today_str}.
Return ONLY a JSON array (no prose). Each event:
{{"name": "<event name>", "start": "<YYYY-MM-DD or YYYY-MM-DDTHH:MM>", "venue": "<venue name>", "address": "<city, state>", "description": "<1-2 sentence description>", "url": "<event url if found, else empty string>"}}
Rules:
- Only include events on or after {today_str}. Skip past events entirely.
- Only include events with a specific name and date. Skip navigation, headers, footer, ads.
- If no events found, return an empty array: []
- Extract ALL events you can find."""

    for page in raw_pages:
        page_text = page.get("description", "")[:6000]
        source_name = page["source"]
        page_url = page["url"]

        # check cache first — skip API call if freshly extracted
        cached_events = get_extracted(page_url)
        if cached_events is not None:
            print(f"  [extract_raw:{source_name}] {len(cached_events)} events (cached)")
            extracted += cached_events
            continue

        try:
            _t0 = time.time()
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": MODEL,
                    "max_tokens": 2000,
                    "system": system,
                    "messages": [{"role": "user", "content": f"Source: {source_name}\nURL: {page_url}\n\n{page_text}"}],
                },
                timeout=30,
            )
            if r.status_code != 200:
                print(f"  [extract_raw:{source_name}] HTTP {r.status_code}")
                continue
            body = r.json()
            usage = body.get("usage", {})
            costs.log_call(
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
                source="extract_raw",
                duration_ms=int((time.time() - _t0) * 1000),
            )
            content = body["content"][0]["text"].strip()
            if "[" not in content or "]" not in content:
                save_extracted(page_url, [])
                print(f"  [extract_raw:{source_name}] no events")
                continue
            start = content.index("[")
            end = content.rindex("]") + 1
            items = json.loads(content[start:end])
            page_events = []
            for item in items:
                if item.get("name") and item.get("start"):
                    url = item.get("url", "") or page_url
                    page_events.append({
                        "source": source_name,
                        "name": item["name"],
                        "description": item.get("description", ""),
                        "url": url,
                        "start": item.get("start", ""),
                        "venue": item.get("venue", ""),
                        "address": item.get("address", ""),
                    })
            save_extracted(page_url, page_events)
            extracted += page_events
            print(f"  [extract_raw:{source_name}] {len(page_events)} events")
        except Exception as ex:
            print(f"  [extract_raw:{source_name}] {ex}")
    print(f"  [extract_raw] total: {len(extracted)} events from {len(raw_pages)} pages")
    return extracted


def score(events: list[dict], prompt_role: str, min_score: int = 5, persona: str = "brian") -> tuple[list[dict], int, int]:
    """
    Score a list of events using Claude.
    prompt_role: describes what kinds of events to look for (injected into prompt).
    persona: cache namespace so different people get independent scores.
    Returns (events_with_score >= min_score sorted descending, n_cached, n_scored).
    """
    if not ANTHROPIC_API_KEY:
        return _keyword_fallback(events, min_score), 0, 0

    # ── extract events from raw scraped pages first ────────────────────────────
    raw_pages = [e for e in events if e.get("_raw")]
    events    = [e for e in events if not e.get("_raw")]
    if raw_pages:
        events += _extract_raw_events(raw_pages)

    # ── pull already-scored events from cache ─────────────────────────────────
    prune_scored()
    cached_hits, needs_scoring = [], []
    for e in events:
        url = e.get("url", "")
        # use source:name as cache key for events without a unique URL
        cache_key = url if url else f"nourl:{e.get('source','')}:{e.get('name','')}"
        if cache_key:
            cached = get_scored(cache_key, persona)
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
            if "[" not in content or "]" not in content:
                results += _keyword_fallback(chunk, min_score)
                continue
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
                    url = chunk[idx].get("url", "")
                    cache_key = url if url else f"nourl:{chunk[idx].get('source','')}:{chunk[idx].get('name','')}"
                    if cache_key:
                        save_scored(cache_key, s, r, name, persona)
                    if s >= min_score:
                        chunk[idx]["score"] = s
                        chunk[idx]["reason"] = r
                        results.append(chunk[idx])
            # save score=0 for anything the AI didn't mention (below threshold, not worth returning)
            for idx, e in enumerate(chunk):
                if idx not in rated_indices:
                    url = e.get("url", "")
                    cache_key = url if url else f"nourl:{e.get('source','')}:{e.get('name','')}"
                    if cache_key:
                        save_scored(cache_key, 0, "below threshold", e.get("name", ""), persona)
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
