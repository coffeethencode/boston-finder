"""
5-strategy venue extractor for oyster events.

Strategy 1: event.venue field (if populated)
Strategy 2: "at <venue>" regex in title
Strategy 3: trailing capitalized words in title (after stripping deal tokens)
Strategy 4: URL slug parse (Boston Calendar style)
Strategy 5: LLM fallback (narrow Haiku call, cached)

Returns the extracted venue name as a string, or None if no strategy succeeds.
"""

import re
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
def _strategy5_llm(event: dict) -> str | None:
    """
    Narrow Haiku call: given title/description/url, return venue name or 'UNKNOWN'.
    Cached per (title, url) via extraction_status in discoveries log.

    Implementation deferred to Task 3b once ai_filter integration is wired.
    For now, returns None — Task 3b enables this.
    """
    return None
