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
    parts = [p for p in slug.split("-") if p and p.lower() not in _STOPWORDS]
    if not parts:
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


def _strategy5_llm(event: dict) -> str | None:
    """
    Narrow Haiku call: given title/description/url, return venue name or 'UNKNOWN'.
    Cached per (url, title) in _CACHE_FILE so each unique event is charged at most once.
    Tests monkeypatch _CACHE_FILE to a tmp_path to avoid touching the real on-disk cache.
    """
    key = _cache_key(event)
    cache = _load_cache(_CACHE_FILE)
    if key in cache:
        cached = cache[key]
        return cached if cached != "UNKNOWN" else None

    prompt = _LLM_PROMPT.format(
        title=event.get("name", ""),
        description=event.get("description", ""),
        url=event.get("url", ""),
    )
    result = (_call_haiku_for_venue(prompt) or "UNKNOWN").strip()

    cache[key] = result
    _save_cache(_CACHE_FILE, cache)

    return result if result != "UNKNOWN" else None


# ── normalization + alias handling ────────────────────────────────────────────

NEIGHBORHOODS = {
    "charlestown", "cambridge", "back bay", "south end", "north end",
    "fort point", "seaport", "fenway", "allston", "brighton", "somerville",
    "providence", "kendall", "harvard square", "beacon hill", "jamaica plain",
    "downtown", "kenmore", "waterfront", "chinatown", "east boston",
}

ALIAS_MAP = {
    "woods hill pier": "woods hill pier 4",
    # add observed aliases here as they surface
}


def normalize(name: str) -> str:
    """Lowercase, strip punctuation (keep digits + spaces), collapse whitespace."""
    s = name.lower()
    s = re.sub(r"[^\w\s]", "", s)  # strip non-word non-space (keeps digits, letters)
    s = re.sub(r"_+", "", s)        # strip underscores (regex \w keeps them)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def match_existing(incoming_name: str, existing_normalized: list[str]) -> str | None:
    """
    Try to match incoming name to an existing normalized name.
    Returns the matched existing normalized name, or None.

    Match order:
      1. Exact normalized match
      2. Alias map
      3. Prefix match where added suffix is a recognized neighborhood
      4. No match (chain branches with non-neighborhood suffixes stay distinct)
    """
    norm = normalize(incoming_name)
    existing_set = set(existing_normalized)

    # 1. exact
    if norm in existing_set:
        return norm

    # 2. alias map both directions
    if norm in ALIAS_MAP and ALIAS_MAP[norm] in existing_set:
        return ALIAS_MAP[norm]
    for alias_key, alias_val in ALIAS_MAP.items():
        if norm == alias_val and alias_key in existing_set:
            return alias_key

    # 3. prefix + neighborhood
    for existing in existing_normalized:
        longer, shorter = (norm, existing) if len(norm) > len(existing) else (existing, norm)
        if longer.startswith(shorter + " "):
            suffix = longer[len(shorter) + 1:].strip()
            if suffix in NEIGHBORHOODS:
                return existing

    return None
