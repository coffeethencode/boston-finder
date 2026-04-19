"""
5-strategy venue extractor for oyster events.

Strategy 1: event.venue field (if populated)
Strategy 2: "at <venue>" regex in title
Strategy 3: trailing capitalized words in title (after stripping deal tokens)
Strategy 4: URL slug parse (Boston Calendar style)
Strategy 5: LLM fallback (narrow Haiku call, cached)

Returns the extracted venue name as a string, or None if no strategy succeeds.
"""

import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse

# Tokens stripped from title before strategy 3's trailing-caps extraction.
# These are oyster/deal/generic-event words that should never be treated as venue.
_STOPWORDS = {
    "oyster", "oysters", "raw", "bar", "shuck", "shucked", "shucking", "buck",
    "a", "happy", "hour", "dollar", "dollars", "half", "price", "half-price",
    "bogo", "for", "and", "the", "of", "at", "with", "on", "in",
    "sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday",
    "special", "specials", "deal", "deals", "night", "brunch", "menu",
    "fest", "festival", "party", "event",
}

# Price token prefixes we strip from the start/end of a title.
_PRICE_RE = re.compile(r"\$\d+(?:\.\d+)?")


def extract_venue(event: dict, use_llm_fallback: bool = True) -> str | None:
    """Run the 5 strategies in order; return first hit, or None."""
    venue = _strategy1_field(event)
    if venue:
        return venue

    venue = _strategy2_at_pattern(event.get("name", ""))
    if venue:
        return venue

    venue = _strategy3_trailing_caps(event.get("name", ""))
    if venue:
        return venue

    venue = _strategy4_url_slug(event.get("url", ""))
    if venue:
        return venue

    if use_llm_fallback:
        venue = _strategy5_llm(event)
        if venue:
            return venue

    return None


# ── strategy 1 ────────────────────────────────────────────────────────────────
def _strategy1_field(event: dict) -> str | None:
    v = (event.get("venue") or "").strip()
    return v or None


# ── strategy 2 ────────────────────────────────────────────────────────────────
_AT_RE = re.compile(
    r"(?i)\b(?:at|@|hosted\s+at|held\s+at)\s+(.+?)(?:\s*[—–|,\-]|\s*$)"
)


def _strategy2_at_pattern(title: str) -> str | None:
    m = _AT_RE.search(title)
    if not m:
        return None
    candidate = m.group(1).strip()
    # filter out trivially short or stopword-only captures
    if len(candidate) < 2 or candidate.lower() in _STOPWORDS:
        return None
    return candidate


# ── strategy 3 ────────────────────────────────────────────────────────────────
def _strategy3_trailing_caps(title: str) -> str | None:
    if not title:
        return None

    # strip price tokens
    cleaned = _PRICE_RE.sub("", title).strip()
    tokens = [t for t in re.split(r"\s+", cleaned) if t]

    # walk from the end, collecting capitalized tokens until a non-cap or stopword
    venue_tokens: list[str] = []
    for tok in reversed(tokens):
        t_lower = tok.lower().strip(".,;:!-")
        if not t_lower:
            continue
        if t_lower in _STOPWORDS:
            break
        if not tok[0].isupper() and not tok.isupper():
            break
        venue_tokens.append(tok)

    if not venue_tokens:
        return None

    venue_tokens.reverse()
    result = " ".join(venue_tokens).title()

    # reject if result is only stopwords (shouldn't happen given the walk but guard)
    if all(t.lower() in _STOPWORDS for t in result.split()):
        return None

    # require at least one alphabetic token
    if not any(re.search(r"[A-Za-z]", t) for t in venue_tokens):
        return None

    return result


# ── strategy 4 ────────────────────────────────────────────────────────────────
_SLUG_TRAILING_COUNTER_RE = re.compile(r"--\d+$")


def _strategy4_url_slug(url: str) -> str | None:
    if not url:
        return None

    try:
        path = urlparse(url).path
    except ValueError:
        return None

    # last path segment
    segments = [s for s in path.split("/") if s]
    if not segments:
        return None

    slug = segments[-1]
    slug = _SLUG_TRAILING_COUNTER_RE.sub("", slug)

    # split on hyphens; apply same stopword filter as strategy 3
    # require at least 2 meaningful parts — single-word slugs are too ambiguous
    parts = [p for p in slug.split("-") if p and p.lower() not in _STOPWORDS]
    if len(parts) < 2:
        return None

    # require at least one alphabetic part (reject pure-numeric slugs like "123")
    if not any(re.search(r"[A-Za-z]", p) for p in parts):
        return None

    result = " ".join(parts).title()
    if len(result) < 2:
        return None
    return result


# ── strategy 5 ────────────────────────────────────────────────────────────────
_CACHE_FILE = os.path.expanduser("~/boston_finder_venue_extraction_cache.json")
_ORIGINAL_CACHE_FILE = _CACHE_FILE  # sentinel for monkeypatch detection

_LLM_PROMPT = """Given this event, return ONLY the venue name (restaurant, bar, shop, or building). No extra text, no punctuation, no explanation. If unclear, return exactly: UNKNOWN

Title: {title}
Description: {description}
URL: {url}
"""


def _load_cache(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        return json.loads(Path(path).read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save_cache(path: str, data: dict) -> None:
    Path(path).write_text(json.dumps(data, indent=2))


def _cache_key(event: dict) -> str:
    return f"{event.get('url', '')}|{event.get('name', '')}"


def _call_haiku_for_venue(prompt: str) -> str:
    """
    Invoke Haiku for venue extraction. Kept as a separate function so tests
    can monkeypatch it without mocking the full anthropic HTTP call.
    """
    import time
    import requests
    from boston_finder import costs
    from boston_finder.ai_filter import ANTHROPIC_API_KEY, MODEL

    t0 = time.time()
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": MODEL,
            "max_tokens": 40,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=15,
    )
    if r.status_code != 200:
        return "UNKNOWN"

    body = r.json()
    usage = body.get("usage", {})
    costs.log_call(
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        source="venue_extract",
        duration_ms=int((time.time() - t0) * 1000),
    )
    return body["content"][0]["text"].strip()


# Set after function definition so _strategy5_llm can detect monkeypatching.
_ORIGINAL_CALL_HAIKU = _call_haiku_for_venue


def _strategy5_llm(event: dict) -> str | None:
    """
    Narrow Haiku call: given title/description/url, return venue name or 'UNKNOWN'.
    Cached per (url, title) in ~/boston_finder_venue_extraction_cache.json so each
    unique event is charged at most once.

    Cache behaviour under test:
    - If only _call_haiku_for_venue is patched (but not _CACHE_FILE), the cache is
      bypassed entirely so tests don't contaminate the real on-disk cache or each other.
    - If _CACHE_FILE is also patched to a temp path (as in the caching test), the
      cache is used normally against that temp file, exercising real cache logic.
    """
    import boston_finder.venue_extractor as _self

    # use_cache = real LLM in use, OR caller explicitly redirected _CACHE_FILE
    using_real_llm = _self._call_haiku_for_venue is _ORIGINAL_CALL_HAIKU
    cache_redirected = _self._CACHE_FILE != _ORIGINAL_CACHE_FILE
    use_cache = using_real_llm or cache_redirected

    cache_path = _self._CACHE_FILE
    key = _cache_key(event)

    if use_cache:
        cache = _load_cache(cache_path)
        if key in cache:
            cached = cache[key]
            return cached if cached != "UNKNOWN" else None
    else:
        cache = {}

    prompt = _LLM_PROMPT.format(
        title=event.get("name", ""),
        description=event.get("description", ""),
        url=event.get("url", ""),
    )
    result = (_self._call_haiku_for_venue(prompt) or "UNKNOWN").strip()

    if use_cache:
        cache[key] = result
        _save_cache(cache_path, cache)

    return result if result != "UNKNOWN" else None
