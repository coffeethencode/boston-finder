# Oyster Pipeline Simplification + Discovery — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace AI-based oyster scoring with a rule-based binary filter + extended verify that extracts price/hours. Share fetched events with the oyster pipeline via a new event store. Log event-feed venues not in `OYSTER_VENUES` for manual promotion.

**Architecture:** Daily event finder run persists its deduped event list to `~/boston_finder_events.json` (new `event_store.py`). Weekly oyster run reads that file, applies a pure-rules binary keyword filter (`oyster_filter.py`), extracts venue from messy data via a 5-strategy extractor (`venue_extractor.py`, includes LLM fallback), normalizes/dedupes venue names against `OYSTER_VENUES` + a discoveries log (`oyster_discoveries.py`), then runs the existing verify step — extended with regex price/hours extractors — to produce deterministic deal records. HTML output renders three states: verified, tentative (discovery + verify OK), needs review (verify couldn't extract price).

**Tech Stack:** Python 3 (venv at `/Users/brian/python-projects/myenv`), `requests`, `beautifulsoup4`, `pytest` (new). No framework changes.

**Spec:** `tracking/specs/2026-04-19-oyster-pipeline-unification-design.md` (commit `acaf57f`).

## File map

**New files:**
| File | Responsibility |
|------|---------------|
| `requirements-dev.txt` | Dev-only deps (pytest) |
| `tests/__init__.py` | Empty package marker |
| `tests/conftest.py` | pytest path setup so tests can `import boston_finder` |
| `tests/test_event_store.py` | Roundtrip, staleness, schema |
| `tests/test_oyster_filter.py` | Keyword classifier positive + negative |
| `tests/test_venue_extractor.py` | 5 extraction strategies |
| `tests/test_venue_normalizer.py` | Name normalization + alias handling |
| `tests/test_oyster_verify_extractors.py` | price regex, hours regex (multi-window) |
| `tests/test_oyster_discoveries.py` | Upsert, first/last seen, status field |
| `tests/test_oyster_pipeline_integration.py` | End-to-end Park 9 + Tradesman |
| `boston_finder/event_store.py` | write_events / read_events + StaleEventsError |
| `boston_finder/oyster_filter.py` | is_oyster_candidate (binary) |
| `boston_finder/venue_extractor.py` | extract_venue (5-strategy, incl. LLM fallback) + normalize + alias resolution |
| `boston_finder/oyster_discoveries.py` | Read/write discoveries.json; upsert logic |

**Modified files:**
| File | Change |
|------|--------|
| `boston_events.py` | Call `event_store.write_events()` at end of `fetch_shared()` |
| `boston_finder/personas.py` | Remove `oyster_prompt` + `get_oyster_prompt` (simplify) |
| `oyster_verify.py` | Add `extract_price`, `extract_hours`; accept event dicts, not just `OYSTER_VENUES` |
| `oyster_deals.py` | Drop AI scoring path; read event_store, use binary filter + venue extractor + discoveries merge |
| `boston_finder/html_output.py` | Add "new" badge (tentative) + "Needs Review" strip |
| `boston_finder/oyster_sources.py` | `get_all()` merges known venues + research.txt + event-derived candidates (from oyster_deals) |

**Note on tests:** project has no existing tests directory. Task 0 bootstraps it.

**Note on location:** plan lives in `tracking/plans/` to match `tracking/specs/` convention this repo uses (not `docs/superpowers/plans/` — `docs/` is the Netlify-served directory for HTML output).

---

## Task 0: Bootstrap test infrastructure

**Files:**
- Create: `requirements-dev.txt`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create `requirements-dev.txt`**

```
pytest>=7.0,<9.0
```

- [ ] **Step 2: Install pytest into project venv**

Run: `/Users/brian/python-projects/myenv/bin/pip install -r requirements-dev.txt`
Expected: `Successfully installed pytest-...`

- [ ] **Step 3: Create `tests/__init__.py`**

Empty file.

- [ ] **Step 4: Create `tests/conftest.py`**

```python
"""pytest config — put repo root on sys.path so tests can import boston_finder."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
```

- [ ] **Step 5: Verify pytest discovers the tests dir**

Run: `/Users/brian/python-projects/myenv/bin/pytest tests/ -v --collect-only`
Expected: `collected 0 items` (no tests yet, but discovery succeeds with no errors).

- [ ] **Step 6: Commit**

```bash
git add requirements-dev.txt tests/__init__.py tests/conftest.py
git commit -m "chore: bootstrap pytest test infrastructure"
```

---

## Task 1: `event_store` module — persist daily events

**Files:**
- Create: `boston_finder/event_store.py`
- Create: `tests/test_event_store.py`

The event_store is the load-bearing Phase 1 plumbing: `boston_events.py` writes the deduped event list after `fetch_shared()`; `oyster_deals.py` reads from it. Stale-file handling must be explicit so a failed daily run doesn't silently poison the weekly oyster run.

- [ ] **Step 1: Write failing roundtrip test**

Create `tests/test_event_store.py`:

```python
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from boston_finder import event_store


def test_write_and_read_roundtrip(tmp_path, monkeypatch):
    events_file = tmp_path / "events.json"
    monkeypatch.setattr(event_store, "EVENTS_FILE", str(events_file))

    events = [
        {"name": "Event A", "url": "https://a.example"},
        {"name": "Event B", "url": "https://b.example"},
    ]
    event_store.write_events(events, fetched_at=datetime.now())

    loaded = event_store.read_events()
    assert loaded == events


def test_stale_events_raises(tmp_path, monkeypatch):
    events_file = tmp_path / "events.json"
    monkeypatch.setattr(event_store, "EVENTS_FILE", str(events_file))

    past = datetime.now() - timedelta(hours=72)
    event_store.write_events([{"name": "X"}], fetched_at=past)

    import pytest
    with pytest.raises(event_store.StaleEventsError):
        event_store.read_events(max_age_hours=48)


def test_missing_file_raises_clear_error(tmp_path, monkeypatch):
    events_file = tmp_path / "nonexistent.json"
    monkeypatch.setattr(event_store, "EVENTS_FILE", str(events_file))

    import pytest
    with pytest.raises(event_store.EventStoreError, match="not found"):
        event_store.read_events()


def test_malformed_file_raises_clear_error(tmp_path, monkeypatch):
    events_file = tmp_path / "events.json"
    events_file.write_text('{"wrong_key": []}')
    monkeypatch.setattr(event_store, "EVENTS_FILE", str(events_file))

    import pytest
    with pytest.raises(event_store.EventStoreError, match="schema"):
        event_store.read_events()
```

- [ ] **Step 2: Run test, expect failure (module doesn't exist)**

Run: `/Users/brian/python-projects/myenv/bin/pytest tests/test_event_store.py -v`
Expected: `ModuleNotFoundError: No module named 'boston_finder.event_store'`

- [ ] **Step 3: Implement `boston_finder/event_store.py`**

```python
"""
Daily event persistence layer.

boston_events.py writes the deduped event list here after fetch_shared().
oyster_deals.py (and any other weekly consumer) reads from here to avoid
re-scraping the same sources.

Single file, overwritten daily. No TTL on write — staleness is enforced
on read via read_events(max_age_hours=...).
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

EVENTS_FILE = os.path.expanduser("~/boston_finder_events.json")


class EventStoreError(Exception):
    """Base class for event store read problems."""


class StaleEventsError(EventStoreError):
    """Raised when the on-disk file is older than the caller's max age."""


def write_events(events: list[dict], fetched_at: datetime) -> None:
    """Persist the deduped event list. Overwrites any previous write."""
    payload = {
        "fetched_at": fetched_at.isoformat(),
        "event_count": len(events),
        "events": events,
    }
    Path(EVENTS_FILE).write_text(json.dumps(payload, indent=2))


def read_events(max_age_hours: int = 48) -> list[dict]:
    """
    Return the events written by the most recent write_events() call.

    Raises EventStoreError if the file is missing or malformed.
    Raises StaleEventsError if the file is older than max_age_hours.
    """
    if not os.path.exists(EVENTS_FILE):
        raise EventStoreError(f"event store file not found at {EVENTS_FILE}")

    try:
        payload = json.loads(Path(EVENTS_FILE).read_text())
    except json.JSONDecodeError as ex:
        raise EventStoreError(f"event store file corrupt: {ex}") from ex

    if "events" not in payload or "fetched_at" not in payload:
        raise EventStoreError("event store file schema missing required keys")

    fetched_at = datetime.fromisoformat(payload["fetched_at"])
    if datetime.now() - fetched_at > timedelta(hours=max_age_hours):
        raise StaleEventsError(
            f"events are {(datetime.now() - fetched_at).total_seconds() / 3600:.1f}h old, "
            f"exceeds max_age_hours={max_age_hours}"
        )

    return payload["events"]
```

- [ ] **Step 4: Run tests, expect pass**

Run: `/Users/brian/python-projects/myenv/bin/pytest tests/test_event_store.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add boston_finder/event_store.py tests/test_event_store.py
git commit -m "feat(event_store): add daily event persistence layer

write_events() persists deduped event list with fetched_at timestamp.
read_events(max_age_hours=48) returns the latest events or raises
StaleEventsError if the file is older than allowed.

Part 1 of oyster pipeline simplification plan."
```

---

## Task 2: `oyster_filter` module — binary keyword classifier

**Files:**
- Create: `boston_finder/oyster_filter.py`
- Create: `tests/test_oyster_filter.py`

Pure-rules classifier. No AI. Title or description substring match against the keyword set. See spec §2 for rationale.

- [ ] **Step 1: Write failing classifier tests**

Create `tests/test_oyster_filter.py`:

```python
from boston_finder import oyster_filter


def _evt(name="", description=""):
    return {"name": name, "description": description}


# primary keyword positives
def test_oyster_in_name_passes():
    assert oyster_filter.is_oyster_candidate(_evt(name="$1 Oyster Brunch")) is True

def test_oysters_plural_passes():
    assert oyster_filter.is_oyster_candidate(_evt(name="Oysters at Lincoln Tavern")) is True

def test_raw_bar_passes():
    assert oyster_filter.is_oyster_candidate(_evt(description="Raw Bar Happy Hour all night")) is True

def test_shuck_passes():
    assert oyster_filter.is_oyster_candidate(_evt(name="Shuck & Sip Thursday")) is True

def test_buck_a_shuck_passes():
    assert oyster_filter.is_oyster_candidate(_evt(name="DOLLAR OYSTERS BUCK A SHUCK TRADESMAN CHARLESTOWN")) is True

# secondary keyword positives
def test_bivalves_passes():
    assert oyster_filter.is_oyster_candidate(_evt(description="bivalves tasting night")) is True

def test_wellfleet_passes():
    assert oyster_filter.is_oyster_candidate(_evt(name="Wellfleets $1 Monday")) is True

def test_duxbury_passes():
    assert oyster_filter.is_oyster_candidate(_evt(description="$1 Duxbury oysters 5-6pm")) is True

def test_shellfish_happy_hour_passes():
    assert oyster_filter.is_oyster_candidate(_evt(name="Shellfish Happy Hour at Island Creek")) is True

# negatives
def test_everett_happy_hour_fails():
    assert oyster_filter.is_oyster_candidate(_evt(name="Everett Happy Hour", description="")) is False

def test_wine_tasting_fails():
    assert oyster_filter.is_oyster_candidate(_evt(name="Wine Tasting", description="")) is False

def test_bare_happy_hour_fails():
    assert oyster_filter.is_oyster_candidate(_evt(name="Happy Hour", description="")) is False

def test_dollar_beer_fails():
    assert oyster_filter.is_oyster_candidate(_evt(name="$1 Beer Tuesday", description="")) is False

# deliberate passthrough (acknowledged false positive — verify step drops it)
def test_oyster_mushroom_passes_but_verify_will_drop():
    """The word 'oyster' in 'oyster mushroom' passes this filter by design;
    the verify step's price extractor near oyster-food context will drop it."""
    assert oyster_filter.is_oyster_candidate(_evt(name="Oyster Mushroom Workshop")) is True

# case insensitive
def test_case_insensitive():
    assert oyster_filter.is_oyster_candidate(_evt(name="oYsTeR FeSt")) is True
```

- [ ] **Step 2: Run, expect failure (module missing)**

Run: `/Users/brian/python-projects/myenv/bin/pytest tests/test_oyster_filter.py -v`
Expected: `ModuleNotFoundError: No module named 'boston_finder.oyster_filter'`

- [ ] **Step 3: Implement `boston_finder/oyster_filter.py`**

```python
"""
Binary oyster-event classifier. Pure keyword rules, no AI.

Called per event from the cached event store. Events passing this filter
are candidates for venue extraction + verify.
"""

PRIMARY_KEYWORDS = (
    "oyster", "oysters",
    "raw bar",
    "shuck", "shucked", "shucking",
    "buck a shuck", "buck-a-shuck",
)

SECONDARY_KEYWORDS = (
    "bivalve", "bivalves",
    "wellfleet", "wellfleets",
    "duxbury", "duxburys",
    "shellfish happy hour",
    "raw bar happy hour",
)

_ALL_KEYWORDS = PRIMARY_KEYWORDS + SECONDARY_KEYWORDS


def is_oyster_candidate(event: dict) -> bool:
    """
    Return True if the event's title or description mentions oysters.

    Deliberately loose — verify step handles price/deal confirmation.
    Missed events (no keyword in any field) are acceptable per spec policy.
    """
    haystack = f"{event.get('name', '')} {event.get('description', '')}".lower()
    return any(kw in haystack for kw in _ALL_KEYWORDS)
```

- [ ] **Step 4: Run tests, expect all pass**

Run: `/Users/brian/python-projects/myenv/bin/pytest tests/test_oyster_filter.py -v`
Expected: 15 passed.

- [ ] **Step 5: Commit**

```bash
git add boston_finder/oyster_filter.py tests/test_oyster_filter.py
git commit -m "feat(oyster_filter): add rule-based binary oyster classifier

Replaces AI scoring with deterministic keyword match. Primary keywords
catch oyster/raw bar/shuck; secondary catches common varieties
(Wellfleet, Duxbury) and phrases (shellfish happy hour).

Part 2 of oyster pipeline simplification plan."
```

---

## Task 3: `venue_extractor` module — 5-strategy extraction

**Files:**
- Create: `boston_finder/venue_extractor.py`
- Create: `tests/test_venue_extractor.py`

Boston Calendar events have empty `venue`/`description` fields; venue lives in the title only. This module tries multiple strategies in order until one succeeds. The LLM fallback (strategy 5) is optional and cached per (title, url).

Strategies 1–4 are pure deterministic. Strategy 5 calls Haiku via existing `ai_filter`-style helper and caches result in the discoveries status file.

- [ ] **Step 1: Write failing tests for strategies 1–4**

Create `tests/test_venue_extractor.py`:

```python
from boston_finder import venue_extractor


# Strategy 1: event.venue populated
def test_strategy1_venue_field_populated():
    evt = {"name": "$1 Oysters", "venue": "Neptune Oyster"}
    assert venue_extractor.extract_venue(evt) == "Neptune Oyster"


def test_strategy1_venue_field_empty_falls_through():
    evt = {"name": "$1 Oysters at Lincoln Tavern & Restaurant", "venue": ""}
    assert venue_extractor.extract_venue(evt) == "Lincoln Tavern & Restaurant"


# Strategy 2: "at X" pattern
def test_strategy2_at_venue():
    evt = {"name": "$1 Oysters at Lincoln Tavern & Restaurant", "venue": None}
    assert venue_extractor.extract_venue(evt) == "Lincoln Tavern & Restaurant"


def test_strategy2_at_venue_with_dash_suffix():
    evt = {"name": "$1 Oyster Brunch at Grays Hall — Sunday Special", "venue": None}
    assert venue_extractor.extract_venue(evt) == "Grays Hall"


def test_strategy2_hosted_at():
    evt = {"name": "Oyster night hosted at Ostra", "venue": None}
    assert venue_extractor.extract_venue(evt) == "Ostra"


# Strategy 3: trailing caps
def test_strategy3_trailing_caps_tradesman():
    evt = {"name": "DOLLAR OYSTERS BUCK A SHUCK TRADESMAN CHARLESTOWN", "venue": None}
    result = venue_extractor.extract_venue(evt)
    # title-case correction applied
    assert result == "Tradesman Charlestown"


def test_strategy3_trailing_caps_single_word():
    evt = {"name": "$1 OYSTERS NEPTUNE", "venue": None}
    assert venue_extractor.extract_venue(evt) == "Neptune"


# Strategy 4: URL slug parse
def test_strategy4_url_slug():
    evt = {
        "name": "$1 Oysters",  # too generic for strategies 2/3
        "venue": None,
        "url": "https://www.thebostoncalendar.com/events/dollar-oysters-buck-a-shuck-tradesman-charlestown--30",
    }
    assert venue_extractor.extract_venue(evt) == "Tradesman Charlestown"


# No match — returns None (strategy 5 LLM tested separately with mock)
def test_no_match_returns_none():
    evt = {"name": "$1 Oyster Night", "venue": None, "url": "https://example.com/events/123"}
    # no strategy can extract a venue here
    assert venue_extractor.extract_venue(evt, use_llm_fallback=False) is None


# Strategy 3 stopword handling — avoids picking up "SUNDAY SPECIAL"
def test_strategy3_rejects_stopword_only_result():
    evt = {"name": "RAW BAR HAPPY HOUR SUNDAY SPECIAL", "venue": None}
    assert venue_extractor.extract_venue(evt, use_llm_fallback=False) is None
```

- [ ] **Step 2: Run, expect failure**

Run: `/Users/brian/python-projects/myenv/bin/pytest tests/test_venue_extractor.py -v`
Expected: `ModuleNotFoundError: No module named 'boston_finder.venue_extractor'`

- [ ] **Step 3: Implement strategies 1–4 in `boston_finder/venue_extractor.py`**

```python
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
```

- [ ] **Step 4: Run tests, expect deterministic tests pass, LLM fallback tests to pass (since we return None and `use_llm_fallback=False` in test)**

Run: `/Users/brian/python-projects/myenv/bin/pytest tests/test_venue_extractor.py -v`
Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add boston_finder/venue_extractor.py tests/test_venue_extractor.py
git commit -m "feat(venue_extractor): add 5-strategy venue extractor (strategies 1-4)

Needed because Boston Calendar events have empty venue/description fields
(venue lives in title only, e.g. 'DOLLAR OYSTERS BUCK A SHUCK TRADESMAN
CHARLESTOWN'). Strategies: field → 'at X' regex → trailing caps → URL
slug → LLM fallback (stubbed, wired next task).

Part 3 of oyster pipeline simplification plan."
```

---

## Task 3b: Wire strategy 5 — LLM fallback for venue extraction

**Files:**
- Modify: `boston_finder/venue_extractor.py`
- Modify: `tests/test_venue_extractor.py`

The existing `boston_finder/ai_filter.py` already integrates Haiku via the project's `costs.py` tracking. Reuse the same entry point pattern, but with a narrow single-extraction prompt.

- [ ] **Step 1: Write failing LLM fallback test (with mock)**

Append to `tests/test_venue_extractor.py`:

```python
def test_strategy5_llm_returns_venue(monkeypatch):
    evt = {"name": "$1 Oyster Night", "venue": None, "url": "https://example.com/x"}

    def fake_haiku(prompt: str) -> str:
        return "Neptune Oyster"

    monkeypatch.setattr(venue_extractor, "_call_haiku_for_venue", fake_haiku)
    assert venue_extractor.extract_venue(evt) == "Neptune Oyster"


def test_strategy5_llm_unknown_returns_none(monkeypatch):
    evt = {"name": "$1 Oyster Night", "venue": None, "url": "https://example.com/x"}

    monkeypatch.setattr(
        venue_extractor, "_call_haiku_for_venue", lambda prompt: "UNKNOWN"
    )
    assert venue_extractor.extract_venue(evt) is None


def test_strategy5_llm_cached_per_url(monkeypatch, tmp_path):
    evt = {"name": "$1 Oyster Night", "venue": None, "url": "https://example.com/unique"}

    calls = []

    def counting_haiku(prompt: str) -> str:
        calls.append(prompt)
        return "Somewhere Bar"

    monkeypatch.setattr(venue_extractor, "_call_haiku_for_venue", counting_haiku)
    monkeypatch.setattr(venue_extractor, "_CACHE_FILE", str(tmp_path / "cache.json"))

    assert venue_extractor.extract_venue(evt) == "Somewhere Bar"
    assert venue_extractor.extract_venue(evt) == "Somewhere Bar"
    assert len(calls) == 1  # second call hit the cache
```

- [ ] **Step 2: Run, expect new tests to fail (strategy 5 returns None)**

Run: `/Users/brian/python-projects/myenv/bin/pytest tests/test_venue_extractor.py -v -k strategy5`
Expected: 3 failures.

- [ ] **Step 3: Implement strategy 5 + caching in `venue_extractor.py`**

Replace the existing `_strategy5_llm` stub and add helpers:

```python
import json
import os
from pathlib import Path

_CACHE_FILE = os.path.expanduser("~/boston_finder_venue_extraction_cache.json")

_LLM_PROMPT = """Given this event, return ONLY the venue name (restaurant, bar, shop, or building). No extra text, no punctuation, no explanation. If unclear, return exactly: UNKNOWN

Title: {title}
Description: {description}
URL: {url}
"""


def _load_cache() -> dict:
    if not os.path.exists(_CACHE_FILE):
        return {}
    try:
        return json.loads(Path(_CACHE_FILE).read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save_cache(data: dict) -> None:
    Path(_CACHE_FILE).write_text(json.dumps(data, indent=2))


def _cache_key(event: dict) -> str:
    return f"{event.get('url', '')}|{event.get('name', '')}"


def _strategy5_llm(event: dict) -> str | None:
    key = _cache_key(event)
    cache = _load_cache()
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
    _save_cache(cache)

    return result if result != "UNKNOWN" else None


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
```

Note: this reuses `ai_filter`'s `ANTHROPIC_API_KEY` and `MODEL` module-level constants (the existing scoring path hits the messages endpoint directly via `requests.post`, not via the anthropic SDK — so no "client" to construct). Cost tracking flows through the existing `costs.log_call` with a distinct `source="venue_extract"` label.

- [ ] **Step 5: Run full test file**

Run: `/Users/brian/python-projects/myenv/bin/pytest tests/test_venue_extractor.py -v`
Expected: 13 passed.

- [ ] **Step 6: Commit**

```bash
git add boston_finder/venue_extractor.py tests/test_venue_extractor.py
git commit -m "feat(venue_extractor): wire LLM fallback for strategy 5

Adds narrow Haiku one-shot extraction for events that deterministic
strategies can't handle. Cached per (url, title) in
~/boston_finder_venue_extraction_cache.json so each unique event
is charged at most once.

Part 3b of oyster pipeline simplification plan."
```

---

## Task 4: Venue normalization + alias handling

**Files:**
- Modify: `boston_finder/venue_extractor.py` (add normalize + alias functions)
- Create: `tests/test_venue_normalizer.py`

Same venue surfaces under multiple strings. Normalize + apply alias rules so dedup works. See spec §4 for the dedup rule ladder.

- [ ] **Step 1: Write failing normalization tests**

Create `tests/test_venue_normalizer.py`:

```python
from boston_finder import venue_extractor as ve


def test_normalize_lowercase():
    assert ve.normalize("Tradesman Charlestown") == "tradesman charlestown"


def test_normalize_strips_punctuation():
    assert ve.normalize("Tradesman, Charlestown") == "tradesman charlestown"
    assert ve.normalize("B&G Oysters") == "bg oysters"
    assert ve.normalize("Woods Hill Pier 4") == "woods hill pier 4"


def test_normalize_collapses_whitespace():
    assert ve.normalize("TRADESMAN   Charlestown") == "tradesman charlestown"


def test_same_venue_different_cases_match():
    existing = ["tradesman charlestown"]
    assert ve.match_existing("TRADESMAN  Charlestown", existing) == "tradesman charlestown"


def test_prefix_with_neighborhood_suffix_matches():
    """Tradesman + Tradesman Charlestown → same venue (Charlestown is a known neighborhood)."""
    existing = ["tradesman"]
    # longer form incoming matches shorter existing; caller should upgrade canonical
    assert ve.match_existing("Tradesman Charlestown", existing) == "tradesman"


def test_prefix_with_neighborhood_suffix_reverse_order():
    """Tradesman Charlestown exists; Tradesman ingested second → match."""
    existing = ["tradesman charlestown"]
    assert ve.match_existing("Tradesman", existing) == "tradesman charlestown"


def test_chain_branches_distinct():
    """Legal Sea Foods Copley and Legal Sea Foods Prudential are separate venues."""
    existing = ["legal sea foods copley"]
    assert ve.match_existing("Legal Sea Foods Prudential", existing) is None


def test_chain_root_ambiguous_no_match():
    """Legal Sea Foods without suffix should NOT match a branched entry."""
    existing = ["legal sea foods copley"]
    assert ve.match_existing("Legal Sea Foods", existing) is None


def test_alias_map_woods_hill_pier():
    existing = ["woods hill pier 4"]
    assert ve.match_existing("Woods Hill Pier", existing) == "woods hill pier 4"


def test_no_match_returns_none():
    existing = ["neptune oyster"]
    assert ve.match_existing("Row 34", existing) is None
```

- [ ] **Step 2: Run, expect failure (functions not yet defined)**

Run: `/Users/brian/python-projects/myenv/bin/pytest tests/test_venue_normalizer.py -v`
Expected: `AttributeError: module 'boston_finder.venue_extractor' has no attribute 'normalize'`

- [ ] **Step 3: Append normalize + match_existing + alias map to `venue_extractor.py`**

Append to `boston_finder/venue_extractor.py`:

```python
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
    import re
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
```

- [ ] **Step 4: Run tests**

Run: `/Users/brian/python-projects/myenv/bin/pytest tests/test_venue_normalizer.py -v`
Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add boston_finder/venue_extractor.py tests/test_venue_normalizer.py
git commit -m "feat(venue_extractor): add normalization + alias handling

match_existing() handles exact match, alias map, and
prefix-with-neighborhood suffix collapse. Chain branches like
'Legal Sea Foods Copley' stay distinct from 'Legal Sea Foods
Prudential' (non-neighborhood suffix).

Part 4 of oyster pipeline simplification plan."
```

---

## Task 5: `oyster_verify` — price + hours extractors

**Files:**
- Modify: `oyster_verify.py` (add `extract_price`, `extract_hours`)
- Create: `tests/test_oyster_verify_extractors.py`

The multi-window hours case (`Sun-Thu 9-11 PM; Fri-Sat 10 PM-12 AM`) needs care: split on `;` or newline first, then parse each window.

- [ ] **Step 1: Write failing extractor tests**

Create `tests/test_oyster_verify_extractors.py`:

```python
import oyster_verify as ov


# ── price ─────────────────────────────────────────────────────────────────────
def test_price_simple():
    assert ov.extract_price("$1 oysters") == "$1"


def test_price_decimal():
    assert ov.extract_price("$1.50 each oyster") == "$1.50"


def test_price_range():
    assert ov.extract_price("$1 - $2 oysters") == "$1-$2"


def test_price_range_en_dash():
    assert ov.extract_price("$1–$2 oysters") == "$1-$2"


def test_price_variety_between():
    assert ov.extract_price("$1 Duxbury oysters") == "$1"


def test_price_variety_between_decimal():
    assert ov.extract_price("$1.50 Island Creek oysters") == "$1.50"


def test_price_half():
    assert ov.extract_price("half-price oysters") == "half-price"


def test_price_half_space():
    assert ov.extract_price("half price raw bar") == "half-price"


def test_price_bogo():
    assert ov.extract_price("BOGO oysters Sunday") == "BOGO"


def test_price_two_for_one():
    assert ov.extract_price("2 for 1 oysters until close") == "2-for-1"


def test_price_dollar_word():
    assert ov.extract_price("dollar oysters 4-6pm") == "dollar"


def test_price_buck_a_shuck():
    assert ov.extract_price("buck a shuck Wednesdays") == "buck-a-shuck"


def test_price_no_oyster_context_returns_none():
    assert ov.extract_price("$5 cocktails") is None


# ── hours ─────────────────────────────────────────────────────────────────────
def test_hours_simple_range():
    result = ov.extract_hours("Mon-Wed 5-6pm")
    assert result == {"windows": [{"days": ["Mon", "Tue", "Wed"], "start": "17:00", "end": "18:00"}]}


def test_hours_en_dash():
    result = ov.extract_hours("Mon–Wed 5–6pm")
    assert result == {"windows": [{"days": ["Mon", "Tue", "Wed"], "start": "17:00", "end": "18:00"}]}


def test_hours_explicit_day_list():
    result = ov.extract_hours("Tue Wed Thu 4-6")
    assert result == {"windows": [{"days": ["Tue", "Wed", "Thu"], "start": "16:00", "end": "18:00"}]}


def test_hours_single_day_plural():
    result = ov.extract_hours("Mondays 9-10pm")
    assert result == {"windows": [{"days": ["Mon"], "start": "21:00", "end": "22:00"}]}


def test_hours_daily():
    result = ov.extract_hours("daily 3-6pm")
    assert result == {"windows": [{"days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                                    "start": "15:00", "end": "18:00"}]}


def test_hours_open_ended_until_sold_out():
    result = ov.extract_hours("Mondays 4 PM until sold out")
    assert result == {"windows": [{"days": ["Mon"], "start": "16:00", "end": None}]}


def test_hours_open_ended_starting_at():
    result = ov.extract_hours("Daily starting at 5 PM")
    assert result == {"windows": [{"days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                                    "start": "17:00", "end": None}]}


def test_hours_multi_window():
    result = ov.extract_hours("Sun-Thu 9-11 PM; Fri-Sat 10 PM-12 AM")
    assert len(result["windows"]) == 2
    assert result["windows"][0]["days"] == ["Sun", "Mon", "Tue", "Wed", "Thu"]
    assert result["windows"][1]["days"] == ["Fri", "Sat"]


def test_hours_no_match():
    assert ov.extract_hours("tickets available at the door") is None
```

- [ ] **Step 2: Run, expect failure (functions not yet defined)**

Run: `/Users/brian/python-projects/myenv/bin/pytest tests/test_oyster_verify_extractors.py -v`
Expected: `AttributeError: module 'oyster_verify' has no attribute 'extract_price'`

- [ ] **Step 3: Implement `extract_price` in `oyster_verify.py`**

Append to `oyster_verify.py`:

```python
# ── deal extractors ────────────────────────────────────────────────────────────

import re

_PRICE_PATTERNS = [
    # ranges: $1 - $2 oysters (with optional variety name and en/em dashes)
    (r"\$(\d+(?:\.\d+)?)\s*[-–—]\s*\$(\d+(?:\.\d+)?)\s+(?:\w+\s+)?oysters?",
     lambda m: f"${m.group(1)}-${m.group(2)}"),
    # simple: $1 oysters or $1 Duxbury oysters (one optional variety word)
    (r"\$(\d+(?:\.\d+)?)\s+(?:[A-Z]\w+\s+)?oysters?",
     lambda m: f"${m.group(1)}"),
    # half-price oysters / half price raw bar
    (r"(?i)half[- ]?price\s+(?:[A-Z]\w+\s+)?(?:oysters?|raw\s+bar)",
     lambda m: "half-price"),
    # BOGO
    (r"(?i)\bBOGO\s+(?:[A-Z]\w+\s+)?oysters?",
     lambda m: "BOGO"),
    # 2 for 1
    (r"(?i)\b2[- ]?for[- ]?1\s+(?:[A-Z]\w+\s+)?oysters?",
     lambda m: "2-for-1"),
    # dollar oysters
    (r"(?i)\bdollar\s+oysters?",
     lambda m: "dollar"),
    # buck a shuck
    (r"(?i)\bbuck[- ]?a[- ]?shuck\b",
     lambda m: "buck-a-shuck"),
]


def extract_price(text: str) -> str | None:
    """Return a normalized price label from oyster-deal text, or None."""
    for pattern, formatter in _PRICE_PATTERNS:
        m = re.search(pattern, text)
        if m:
            return formatter(m)
    return None
```

- [ ] **Step 4: Run price tests, expect pass**

Run: `/Users/brian/python-projects/myenv/bin/pytest tests/test_oyster_verify_extractors.py -v -k price`
Expected: 13 price tests pass.

- [ ] **Step 5: Implement `extract_hours` in `oyster_verify.py`**

Append:

```python
_DAY_ABBR = {
    "mon": "Mon", "monday": "Mon", "mondays": "Mon",
    "tue": "Tue", "tues": "Tue", "tuesday": "Tue", "tuesdays": "Tue",
    "wed": "Wed", "weds": "Wed", "wednesday": "Wed", "wednesdays": "Wed",
    "thu": "Thu", "thur": "Thu", "thurs": "Thu", "thursday": "Thu", "thursdays": "Thu",
    "fri": "Fri", "friday": "Fri", "fridays": "Fri",
    "sat": "Sat", "saturday": "Sat", "saturdays": "Sat",
    "sun": "Sun", "sunday": "Sun", "sundays": "Sun",
}
_DAY_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_ALL_DAYS = list(_DAY_ORDER)


def _expand_day_range(start: str, end: str) -> list[str]:
    s, e = _DAY_ABBR[start.lower()], _DAY_ABBR[end.lower()]
    si, ei = _DAY_ORDER.index(s), _DAY_ORDER.index(e)
    if si <= ei:
        return _DAY_ORDER[si : ei + 1]
    return _DAY_ORDER[si:] + _DAY_ORDER[: ei + 1]


def _parse_time(time_str: str) -> str | None:
    """Parse '5pm' / '5 PM' / '9:30pm' / '17:00' → 'HH:MM' 24h."""
    m = re.match(r"\s*(\d{1,2})(?::(\d{2}))?\s*([apAP]\.?[mM]\.?)?\s*$", time_str)
    if not m:
        return None
    hour = int(m.group(1))
    minute = int(m.group(2) or "0")
    ampm = (m.group(3) or "").lower().replace(".", "")
    if ampm == "pm" and hour < 12:
        hour += 12
    elif ampm == "am" and hour == 12:
        hour = 0
    return f"{hour:02d}:{minute:02d}"


# Recognize day tokens separated by ' ', '-', '–', or '—'
_DAY_TOKEN = r"(?:mon|tues?|tue|wed(?:nes)?|thur?s?|fri|sat|sun)(?:day)?(?:s)?"
_TIME_TOKEN = r"\d{1,2}(?::\d{2})?\s*[apAP]?\.?[mM]?\.?"

_RANGE_RE = re.compile(
    rf"(?i)({_DAY_TOKEN})\s*[-–—to]+\s*({_DAY_TOKEN})\s+({_TIME_TOKEN})\s*[-–—]\s*({_TIME_TOKEN})"
)
_LIST_RE = re.compile(
    rf"(?i)({_DAY_TOKEN})\s+({_DAY_TOKEN})\s+({_DAY_TOKEN})\s+({_TIME_TOKEN})\s*[-–—]\s*({_TIME_TOKEN})"
)
_SINGLE_RE = re.compile(
    rf"(?i)({_DAY_TOKEN})\s+({_TIME_TOKEN})\s*[-–—]\s*({_TIME_TOKEN})"
)
_DAILY_RE = re.compile(rf"(?i)\bdaily\s+({_TIME_TOKEN})\s*[-–—]\s*({_TIME_TOKEN})")
_OPEN_SOLDOUT_RE = re.compile(
    rf"(?i)({_DAY_TOKEN})\s+({_TIME_TOKEN})\s+until\s+sold\s+out"
)
_DAILY_STARTING_RE = re.compile(rf"(?i)\bdaily\s+starting\s+at\s+({_TIME_TOKEN})")


def _parse_window(text: str) -> dict | None:
    """Attempt to parse a single window. Return {days, start, end} or None."""
    m = _RANGE_RE.search(text)
    if m:
        days = _expand_day_range(m.group(1), m.group(2))
        return {"days": days, "start": _parse_time(m.group(3)), "end": _parse_time(m.group(4))}

    m = _LIST_RE.search(text)
    if m:
        days = [_DAY_ABBR[m.group(i).lower()] for i in range(1, 4)]
        return {"days": days, "start": _parse_time(m.group(4)), "end": _parse_time(m.group(5))}

    m = _DAILY_RE.search(text)
    if m:
        return {"days": list(_ALL_DAYS), "start": _parse_time(m.group(1)), "end": _parse_time(m.group(2))}

    m = _DAILY_STARTING_RE.search(text)
    if m:
        return {"days": list(_ALL_DAYS), "start": _parse_time(m.group(1)), "end": None}

    m = _OPEN_SOLDOUT_RE.search(text)
    if m:
        return {"days": [_DAY_ABBR[m.group(1).lower()]], "start": _parse_time(m.group(2)), "end": None}

    m = _SINGLE_RE.search(text)
    if m:
        return {"days": [_DAY_ABBR[m.group(1).lower()]], "start": _parse_time(m.group(2)), "end": _parse_time(m.group(3))}

    return None


def extract_hours(text: str) -> dict | None:
    """Return {'windows': [...]} or None if no window found."""
    segments = re.split(r"[;\n]", text)
    windows = []
    for seg in segments:
        w = _parse_window(seg)
        if w and w["start"]:
            windows.append(w)
    return {"windows": windows} if windows else None
```

- [ ] **Step 6: Run all extractor tests**

Run: `/Users/brian/python-projects/myenv/bin/pytest tests/test_oyster_verify_extractors.py -v`
Expected: 22 passed.

If any fail, iterate on the regex — the patterns above are a first pass. Add debugging prints if needed, then remove them before commit.

- [ ] **Step 7: Commit**

```bash
git add oyster_verify.py tests/test_oyster_verify_extractors.py
git commit -m "feat(oyster_verify): add price + hours regex extractors

extract_price handles ranges, varieties between price and oysters,
en dashes, half-price, BOGO, 2-for-1, dollar, buck-a-shuck.
extract_hours handles ranges, explicit day lists, daily, single-day
plural, open-ended (until sold out / starting at), multi-window.

Part 5 of oyster pipeline simplification plan."
```

---

## Task 6: Refactor `verify_venue` to accept event dicts

**Files:**
- Modify: `oyster_verify.py` (extend `verify_venue` signature; store price/hours in result)

Today `verify_venue(venue, force)` takes an `OYSTER_VENUES` record. After this change, it also works for event dicts (which have `name`/`url` but not `specials_url`).

- [ ] **Step 1: Write failing test for event-dict verification**

Append to `tests/test_oyster_verify_extractors.py`:

```python
def test_verify_event_dict(monkeypatch):
    """Verify an event dict that has url but no specials_url."""
    event = {
        "name": "Dollar Oysters at Tradesman Charlestown",
        "url": "https://fake.example/tradesman",
        "venue": "Tradesman Charlestown",
    }

    def fake_fetch(url, headers=None, timeout=10):
        class FakeResp:
            status_code = 200
            text = "<html><body>$1 oysters Mon-Wed 5-6pm at Tradesman</body></html>"
        return FakeResp()

    monkeypatch.setattr(ov.requests, "get", fake_fetch)
    # point status file to tmp dir via monkeypatch to avoid polluting real file
    import tempfile, os
    monkeypatch.setattr(ov, "STATUS_FILE", os.path.join(tempfile.mkdtemp(), "status.json"))

    result = ov.verify_event(event, force=True)
    assert result["price"] == "$1"
    assert result["hours"]["windows"][0]["start"] == "17:00"
    assert result["status"].startswith("✅")
```

- [ ] **Step 2: Run, expect failure (verify_event not defined)**

Run: `/Users/brian/python-projects/myenv/bin/pytest tests/test_oyster_verify_extractors.py::test_verify_event_dict -v`
Expected: AttributeError.

- [ ] **Step 3: Add `verify_event` function in `oyster_verify.py`**

```python
def verify_event(event: dict, force: bool = False) -> dict:
    """
    Verify an event-derived candidate by scraping its URL and extracting price/hours.

    Parallel to verify_venue() but accepts event dicts (no specials_url).
    Writes into the same STATUS_FILE keyed by event URL.
    """
    name = event.get("venue") or event.get("name") or ""
    url = event.get("url", "")
    status = load_status()
    key = f"event:{url}"

    if not force and key in status:
        entry = status[key]
        verified_at = datetime.fromisoformat(entry["verified_at"])
        if datetime.now() - verified_at < timedelta(days=VERIFY_TTL):
            return entry

    maps_url = maps_link(name, "")

    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
    except Exception as ex:
        result = {
            "status": "⚠️ Unverified",
            "verified_at": datetime.now().isoformat(),
            "price": None,
            "hours": None,
            "closed": False,
            "source_url": url,
            "maps_url": maps_url,
            "notes": f"fetch failed: {ex}",
        }
        status[key] = result
        save_status(status)
        return result

    if r.status_code != 200:
        result = {
            "status": "⚠️ Unverified",
            "verified_at": datetime.now().isoformat(),
            "price": None,
            "hours": None,
            "closed": False,
            "source_url": url,
            "maps_url": maps_url,
            "notes": f"HTTP {r.status_code}",
        }
        status[key] = result
        save_status(status)
        return result

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(r.text, "html.parser")
    page_text = soup.get_text(separator=" ")

    # combine with event text so extractors see both
    combined = " ".join([
        event.get("name", ""),
        event.get("description", ""),
        page_text[:5000],
    ])

    price = extract_price(combined)
    hours = extract_hours(combined)
    closed = any(sig in page_text.lower() for sig in CLOSED_SIGNALS)

    if closed:
        status_label = "❌ closed"
    elif price:
        status_label = "✅ verified"
    else:
        status_label = "⚠️ Unverified"

    result = {
        "status": status_label,
        "verified_at": datetime.now().isoformat(),
        "price": price,
        "hours": hours,
        "closed": closed,
        "source_url": url,
        "maps_url": maps_url,
        "notes": "",
    }
    status[key] = result
    save_status(status)
    return result
```

- [ ] **Step 4: Also extend `verify_venue` result to include `price`/`hours`**

Find the existing `verify_venue` in `oyster_verify.py`. Where it currently returns the result dict, augment it by running the same extractors on `r.text`:

```python
# inside existing verify_venue, after soup + page_text are computed:
price = extract_price(page_text)
hours = extract_hours(page_text)
# add to result dict:
result["price"] = price
result["hours"] = hours
```

Keep the existing keys (`status`, `verified_at`, `found_keywords`, `maps_url`, `notes`) intact so downstream consumers don't break. Just add `price` + `hours`.

- [ ] **Step 5: Run all oyster_verify tests**

Run: `/Users/brian/python-projects/myenv/bin/pytest tests/test_oyster_verify_extractors.py -v`
Expected: 23 passed (22 from Task 5 + 1 new).

- [ ] **Step 6: Commit**

```bash
git add oyster_verify.py tests/test_oyster_verify_extractors.py
git commit -m "feat(oyster_verify): add verify_event() + extend verify_venue result

verify_event() accepts event dicts (no specials_url needed), scrapes
the event URL, runs price/hours extractors, and caches the result
keyed by 'event:<url>'. Existing verify_venue() also returns
price/hours now.

Part 6 of oyster pipeline simplification plan."
```

---

## Task 7: `oyster_discoveries` — read/write discoveries log

**Files:**
- Create: `boston_finder/oyster_discoveries.py`
- Create: `tests/test_oyster_discoveries.py`

Persists discovered venues across weekly runs. Upsert semantics: first sighting creates record with `first_seen = last_seen = today`; subsequent sightings update `last_seen`, append to `sources_seen`/`event_urls`/`event_titles`, bump `event_count`.

- [ ] **Step 1: Write failing discoveries tests**

Create `tests/test_oyster_discoveries.py`:

```python
import json
from datetime import datetime

from boston_finder import oyster_discoveries as od


def test_upsert_new_venue(tmp_path, monkeypatch):
    monkeypatch.setattr(od, "DISCOVERIES_FILE", str(tmp_path / "d.json"))

    od.upsert(
        venue_canonical="Tradesman Charlestown",
        venue_normalized="tradesman charlestown",
        event={"name": "DOLLAR OYSTERS BUCK A SHUCK TRADESMAN CHARLESTOWN",
               "url": "https://bc.example/1",
               "source": "thebostoncalendar.com"},
        verify_result={"status": "✅ verified", "price": "$1"},
        extraction_strategy="trailing_caps",
    )

    records = od.load_all()
    assert "tradesman charlestown" in records
    rec = records["tradesman charlestown"]
    assert rec["name_canonical"] == "Tradesman Charlestown"
    assert rec["event_count"] == 1
    assert rec["first_seen"] == rec["last_seen"]
    assert rec["status"] == "tentative"


def test_upsert_existing_venue_bumps_count(tmp_path, monkeypatch):
    monkeypatch.setattr(od, "DISCOVERIES_FILE", str(tmp_path / "d.json"))

    for i in range(3):
        od.upsert(
            venue_canonical="Tradesman Charlestown",
            venue_normalized="tradesman charlestown",
            event={"name": f"event {i}", "url": f"https://bc.example/{i}", "source": "x"},
            verify_result={"status": "✅ verified"},
            extraction_strategy="trailing_caps",
        )

    rec = od.load_all()["tradesman charlestown"]
    assert rec["event_count"] == 3
    assert len(rec["event_urls"]) == 3


def test_upgrade_canonical_on_longer_form(tmp_path, monkeypatch):
    """If the first sighting was 'Tradesman' and the second is
    'Tradesman Charlestown', upgrade the canonical name."""
    monkeypatch.setattr(od, "DISCOVERIES_FILE", str(tmp_path / "d.json"))

    od.upsert("Tradesman", "tradesman", {"url": "u1", "name": "n1"}, {}, "trailing_caps")
    # second sighting with longer canonical matches the shorter record and upgrades
    od.upsert_with_match("Tradesman Charlestown", "tradesman charlestown", "tradesman",
                         {"url": "u2", "name": "n2"}, {}, "trailing_caps")

    records = od.load_all()
    rec = records["tradesman"]  # keyed by original normalized form
    assert rec["name_canonical"] == "Tradesman Charlestown"
    assert "Tradesman" in rec["aliases_seen"]


def test_load_all_empty_file(tmp_path, monkeypatch):
    monkeypatch.setattr(od, "DISCOVERIES_FILE", str(tmp_path / "nonexistent.json"))
    assert od.load_all() == {}
```

- [ ] **Step 2: Run, expect failure (module missing)**

Run: `/Users/brian/python-projects/myenv/bin/pytest tests/test_oyster_discoveries.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Implement `boston_finder/oyster_discoveries.py`**

```python
"""
Discoveries log — venues surfaced from event feeds that aren't in OYSTER_VENUES.

Persisted to ~/boston_finder_oyster_discoveries.json. Keyed by normalized
venue name. Each record tracks sighting history + latest verify result.
"""

import json
import os
from datetime import datetime
from pathlib import Path

DISCOVERIES_FILE = os.path.expanduser("~/boston_finder_oyster_discoveries.json")


def load_all() -> dict:
    if not os.path.exists(DISCOVERIES_FILE):
        return {}
    try:
        return json.loads(Path(DISCOVERIES_FILE).read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data: dict) -> None:
    Path(DISCOVERIES_FILE).write_text(json.dumps(data, indent=2))


def upsert(
    venue_canonical: str,
    venue_normalized: str,
    event: dict,
    verify_result: dict,
    extraction_strategy: str,
) -> None:
    """
    Create or update the discovery record keyed by venue_normalized.
    """
    data = load_all()
    today = datetime.now().date().isoformat()

    existing = data.get(venue_normalized)
    if existing is None:
        data[venue_normalized] = {
            "name_canonical": venue_canonical,
            "name_normalized": venue_normalized,
            "aliases_seen": [venue_canonical],
            "neighborhood": "",
            "first_seen": today,
            "last_seen": today,
            "sources_seen": [event.get("source", "")],
            "event_urls": [event.get("url", "")],
            "event_titles": [event.get("name", "")],
            "extraction_strategy": extraction_strategy,
            "verify_result": verify_result,
            "event_count": 1,
            "status": "tentative",
        }
    else:
        existing["last_seen"] = today
        if event.get("source") and event["source"] not in existing["sources_seen"]:
            existing["sources_seen"].append(event["source"])
        if event.get("url") and event["url"] not in existing["event_urls"]:
            existing["event_urls"].append(event["url"])
        if event.get("name") and event["name"] not in existing["event_titles"]:
            existing["event_titles"].append(event["name"])
        if venue_canonical not in existing["aliases_seen"]:
            existing["aliases_seen"].append(venue_canonical)
        existing["verify_result"] = verify_result  # latest wins
        existing["event_count"] += 1

    _save(data)


def upsert_with_match(
    venue_canonical: str,
    venue_normalized: str,
    matched_key: str,
    event: dict,
    verify_result: dict,
    extraction_strategy: str,
) -> None:
    """
    Upsert where incoming name matched an existing record via normalization
    rules (prefix + neighborhood, alias map). Upgrades canonical to longer form.
    """
    data = load_all()
    existing = data.get(matched_key)
    today = datetime.now().date().isoformat()

    if existing is None:
        # fall through to a plain upsert under incoming normalized key
        upsert(venue_canonical, venue_normalized, event, verify_result, extraction_strategy)
        return

    # upgrade canonical if incoming is longer / more specific
    if len(venue_canonical) > len(existing["name_canonical"]):
        existing["aliases_seen"].append(existing["name_canonical"])
        existing["name_canonical"] = venue_canonical

    if venue_canonical not in existing["aliases_seen"]:
        existing["aliases_seen"].append(venue_canonical)

    existing["last_seen"] = today
    if event.get("source") and event["source"] not in existing["sources_seen"]:
        existing["sources_seen"].append(event["source"])
    if event.get("url") and event["url"] not in existing["event_urls"]:
        existing["event_urls"].append(event["url"])
    if event.get("name") and event["name"] not in existing["event_titles"]:
        existing["event_titles"].append(event["name"])
    existing["verify_result"] = verify_result
    existing["event_count"] += 1

    _save(data)
```

- [ ] **Step 4: Run tests**

Run: `/Users/brian/python-projects/myenv/bin/pytest tests/test_oyster_discoveries.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add boston_finder/oyster_discoveries.py tests/test_oyster_discoveries.py
git commit -m "feat(oyster_discoveries): persistent log of event-feed venues

Keyed by normalized venue name. Tracks first/last seen, source list,
event URLs, verify result, and aliases. upsert_with_match handles
the case where incoming name resolves to an existing record via
normalization rules, and upgrades the canonical form when the new
sighting is longer/more specific.

Part 7 of oyster pipeline simplification plan."
```

---

## Task 8: Wire `event_store` write into `boston_events.py`

**Files:**
- Modify: `boston_events.py`

Add the event persistence call at the end of `fetch_shared()` so the weekly oyster run has data to read.

- [ ] **Step 1: Read the current `fetch_shared` function**

Run: `/Users/brian/python-projects/myenv/bin/python3 -c "
import re
with open('boston_events.py') as f: text = f.read()
m = re.search(r'def fetch_shared.*?(?=\ndef )', text, re.DOTALL)
print(m.group(0))
"`

Confirm the function returns `all_events` at the end.

- [ ] **Step 2: Add `event_store.write_events()` call**

In `boston_events.py`, import at top:

```python
from boston_finder import event_store
```

At the end of `fetch_shared()`, before the `return all_events` line:

```python
    try:
        event_store.write_events(all_events, fetched_at=datetime.now())
        print(f"  → persisted {len(all_events)} events to event store")
    except Exception as ex:
        print(f"  ⚠️  event_store.write_events failed: {ex}")
    return all_events
```

(Wrapped in try/except so an IO error doesn't abort the persona runs that follow.)

- [ ] **Step 3: Smoke-test the daily pipeline writes the file**

Run (in the repo dir, SAFE mode so no deploy):

```bash
BOSTON_FINDER_SAFE_TEST=1 BOSTON_FINDER_DISABLE_OPEN=1 /Users/brian/python-projects/myenv/bin/python3 boston_events.py --persona brian --days 7
```

Expected: console output includes `→ persisted N events to event store`. Verify file exists:

```bash
ls -la ~/boston_finder_events.json
```

- [ ] **Step 4: Sanity-check event store contents**

Run:

```bash
/Users/brian/python-projects/myenv/bin/python3 -c "
from boston_finder import event_store
events = event_store.read_events()
print(f'{len(events)} events')
bc = [e for e in events if 'thebostoncalendar' in e.get('url','')]
print(f'{len(bc)} Boston Calendar events')
oyster = [e for e in bc if 'oyster' in e.get('name','').lower()]
print(f'{len(oyster)} with oyster in name')
for e in oyster[:3]: print('  -', e['name'][:70])
"
```

Expected: at least a few oyster-related Boston Calendar events listed.

- [ ] **Step 5: Commit**

```bash
git add boston_events.py
git commit -m "feat(boston_events): persist fetched events to event store

Calls event_store.write_events() at end of fetch_shared() so the
weekly oyster run has access to the day's event stream without
re-scraping.

Part 8 of oyster pipeline simplification plan."
```

---

## Task 9: Rewrite `oyster_deals.py` pipeline — drop AI scoring, use new modules

**Files:**
- Modify: `oyster_deals.py`

Replace the AI scoring path with: read from event_store → binary filter → extract venue → normalize/dedupe → verify (event or known venue) → merge → render.

This is the load-bearing integration task.

- [ ] **Step 1: Inspect current `oyster_deals.py` structure**

Read the file end-to-end. Identify:
- Where `score()` is called (the Haiku scoring — this comes out)
- Where `get_oyster_candidates()` is called (this gets joined with event-feed candidates)
- Where display/sort/output is called (preserve these)

- [ ] **Step 2: Add new helper `collect_event_feed_candidates()` to `oyster_deals.py`**

Near the top of the file (after imports), add:

```python
from boston_finder import event_store, oyster_filter, venue_extractor, oyster_discoveries
from boston_finder.oyster_sources import OYSTER_VENUES


def collect_event_feed_candidates() -> list[dict]:
    """
    Read the daily event store, apply binary oyster filter, extract venue
    for each candidate, dedupe against OYSTER_VENUES + discoveries log,
    run verify on each unique venue, log to discoveries.

    Returns: list of candidate deal records in the same shape oyster_sources
    produces (source, name, description, url, start, venue, address).
    """
    try:
        events = event_store.read_events(max_age_hours=48)
    except event_store.EventStoreError as ex:
        print(f"  event store read failed — skipping event-feed candidates: {ex}")
        return []

    oyster_events = [e for e in events if oyster_filter.is_oyster_candidate(e)]
    print(f"  {len(oyster_events)} oyster candidates from event store")

    # build set of known-venue normalized names (OYSTER_VENUES)
    known_normalized = {venue_extractor.normalize(v["name"]) for v in OYSTER_VENUES}

    # prior discoveries
    discoveries = oyster_discoveries.load_all()
    discovered_normalized = set(discoveries.keys())

    import oyster_verify

    candidates = []
    for evt in oyster_events:
        venue = venue_extractor.extract_venue(evt, use_llm_fallback=True)
        if not venue:
            # drop with a note — will surface as Needs Review via the verify layer
            # when we pass the event anyway. For now, skip venueless events.
            continue

        normalized = venue_extractor.normalize(venue)

        # known-venue match → skip (already covered by OYSTER_VENUES scrape)
        if normalized in known_normalized:
            continue

        # try to match existing discovery (alias / prefix rules)
        matched = venue_extractor.match_existing(venue, list(discovered_normalized) + list(known_normalized))

        if matched in known_normalized:
            continue

        verify_result = oyster_verify.verify_event(evt, force=False)

        if matched and matched in discovered_normalized:
            oyster_discoveries.upsert_with_match(
                venue_canonical=venue,
                venue_normalized=normalized,
                matched_key=matched,
                event=evt,
                verify_result=verify_result,
                extraction_strategy="mixed",
            )
        else:
            oyster_discoveries.upsert(
                venue_canonical=venue,
                venue_normalized=normalized,
                event=evt,
                verify_result=verify_result,
                extraction_strategy="mixed",
            )
            discovered_normalized.add(normalized)

        if verify_result.get("price"):
            candidates.append({
                "source": f"discovery:{evt.get('source', '')}",
                "name": f"{venue} — {verify_result['price']} oysters",
                "description": evt.get("name", ""),
                "url": evt.get("url", ""),
                "start": evt.get("start", ""),
                "venue": venue,
                "address": "",
                "verify_status": verify_result.get("status", ""),
                "price": verify_result.get("price"),
                "hours": verify_result.get("hours"),
                "_tentative": True,
            })
        else:
            # verify couldn't extract price → render as "Needs Review"
            candidates.append({
                "source": f"discovery:{evt.get('source', '')}",
                "name": f"{venue} — oysters mentioned, verify manually",
                "description": evt.get("name", ""),
                "url": evt.get("url", ""),
                "start": evt.get("start", ""),
                "venue": venue,
                "address": "",
                "verify_status": verify_result.get("status", "⚠️ Unverified"),
                "price": None,
                "hours": None,
                "_tentative": True,
                "_needs_review": True,
            })

    return candidates
```

- [ ] **Step 3: Wire new helper into `run()` / main flow, remove AI scoring**

Find the block in `oyster_deals.py` that calls `score(oyster_events, prompt, min_score=..., persona=...)`. Replace that block so it:

1. Gets known-venue candidates via `get_oyster_candidates()` (existing behavior).
2. Gets event-feed candidates via `collect_event_feed_candidates()` (new).
3. Concatenates the two lists.
4. Skips the `score()` call entirely.
5. Passes the combined list to the existing proximity sort / display flow.

The exact function name may be `run_persona()` or similar. Sketch:

```python
# OLD:
# deals, _, _ = score(oyster_events, prompt, min_score=min_score, persona=persona_name)

# NEW:
known = get_oyster_candidates()  # existing
event_feed = collect_event_feed_candidates()
deals = known + event_feed
```

Remove imports of `score`, `get_oyster_prompt`, `get_min_score` if they're no longer used anywhere else in this file.

- [ ] **Step 4: Run the existing smoke test to make sure nothing crashes**

```bash
BOSTON_FINDER_SAFE_TEST=1 /Users/brian/python-projects/myenv/bin/python3 oyster_deals.py --persona brian
```

Expected: completes without error. Output contains:
- existing known-venue lines (Rochambeau, Legal Sea Foods, Sonsie)
- new discoveries (if the event store has oyster events) tagged as tentative
- NO Park 9 Dog Bar (it fails the binary filter)

- [ ] **Step 5: Commit**

```bash
git add oyster_deals.py
git commit -m "refactor(oyster_deals): drop AI scoring; wire event-store pipeline

collect_event_feed_candidates() reads the daily event store, applies
the rule-based oyster filter, extracts venue via 5-strategy extractor,
dedupes against OYSTER_VENUES + discoveries log, runs verify, and
persists sightings. Known-venue path unchanged.

Park 9 Dog Bar no longer surfaces — it lacks any oyster keyword and
the binary filter drops it before verify.

Part 9 of oyster pipeline simplification plan."
```

---

## Task 10: Drop `oyster_prompt` from personas (cleanup)

**Files:**
- Modify: `boston_finder/personas.py`

Now unused.

- [ ] **Step 1: Grep for remaining usages**

Run: `/Users/brian/python-projects/myenv/bin/python3 -c "
import subprocess
out = subprocess.run(['grep', '-rn', 'oyster_prompt\\|get_oyster_prompt\\|get_min_score', '--include=*.py', '.'], capture_output=True, text=True)
print(out.stdout)
"`

Expected: only references in `boston_finder/personas.py` itself (the definitions) and maybe a tracking/diffs file. No runtime callers.

- [ ] **Step 2: Remove `oyster_prompt` field from each persona in `boston_finder/personas.py`**

For each of the 4 personas (brian, dates, kirk, chloe), delete the entire `oyster_prompt": """..."""` block (the triple-quoted string that scores oysters).

- [ ] **Step 3: Remove `get_oyster_prompt()` helper**

Delete the function `get_oyster_prompt(name)` from the bottom of `personas.py`.

- [ ] **Step 4: Leave `get_min_score()` if still used by event finder**

Check: if `boston_events.py` or `ai_filter.py` still calls `get_min_score()`, keep it. Otherwise remove.

- [ ] **Step 5: Smoke-test both pipelines**

```bash
BOSTON_FINDER_SAFE_TEST=1 /Users/brian/python-projects/myenv/bin/python3 boston_events.py --persona brian --days 1
BOSTON_FINDER_SAFE_TEST=1 /Users/brian/python-projects/myenv/bin/python3 oyster_deals.py --persona brian
```

Expected: both run cleanly, no ImportError or AttributeError.

- [ ] **Step 6: Commit**

```bash
git add boston_finder/personas.py
git commit -m "chore(personas): remove obsolete oyster_prompt fields

Oyster pipeline no longer AI-scores events; the per-persona
oyster_prompt blocks and get_oyster_prompt() helper are unused.

Part 10 of oyster pipeline simplification plan."
```

---

## Task 11: HTML output — 3-state rendering (verified / tentative / needs review)

**Files:**
- Modify: `boston_finder/html_output.py`

Add:
- "new" badge on tentative discoveries
- "⚠️ Needs Review" strip at the bottom of the oyster section

Data flow: `oyster_deals.py` writes the `oyster_deals_<persona>` cache key (existing). Each record now optionally carries `_tentative: True` and/or `_needs_review: True`. `html_output.py` reads these flags and renders accordingly.

- [ ] **Step 1: Read current oyster rendering JS in html_output.py**

Find the string block `renderOysterDay(...)` or similar. Read surrounding 30 lines.

- [ ] **Step 2: Add tentative badge + needs-review partition**

Modify the oyster render so:
- Deals with `_needs_review === true` go into a separate "Needs Review" strip rendered below the main list.
- Deals with `_tentative === true` (but not needs_review) get a small `"🆕 new"` badge next to the venue name.

Sketch (adjust to match existing rendering idiom):

```javascript
function renderOysterDay(dow) {
  const all = oysterData.filter(d => matchesDayFilter(d, dow));
  const needsReview = all.filter(d => d._needs_review);
  const display = all.filter(d => !d._needs_review);

  let html = display.map(d => {
    const badge = d._tentative ? ' <span class="new-badge">🆕 new</span>' : '';
    return `<div class="oyster-row">
      <div class="oyster-name">${esc(d.venue)}${badge}</div>
      ...
    </div>`;
  }).join('');

  if (needsReview.length) {
    html += '<div class="needs-review-strip"><div class="nr-title">⚠️ Needs Review — oyster keyword found, price unclear</div>';
    html += needsReview.map(d => `<a href="${esc(d.url)}" target="_blank">${esc(d.venue)}: ${esc(d.description)}</a>`).join('<br>');
    html += '</div>';
  }

  return html;
}
```

Add minimal CSS for the badge + strip near the existing oyster styles:

```css
.new-badge { font-size: 0.65rem; color: #fff; background: #3a7; padding: 1px 5px; border-radius: 3px; margin-left: 5px; }
.needs-review-strip { margin-top: 12px; padding: 10px; background: rgba(255,180,60,0.08); border-left: 3px solid #e0a040; border-radius: 4px; font-size: 0.75rem; }
.needs-review-strip .nr-title { font-weight: 600; margin-bottom: 6px; color: #c0802d; }
.needs-review-strip a { color: #aaa; text-decoration: none; }
.needs-review-strip a:hover { color: #eee; text-decoration: underline; }
```

- [ ] **Step 3: Rebuild the site locally (safe mode) and eyeball in browser**

```bash
BOSTON_FINDER_SAFE_TEST=1 /Users/brian/python-projects/myenv/bin/python3 boston_events.py --persona brian --days 7
BOSTON_FINDER_SAFE_TEST=1 /Users/brian/python-projects/myenv/bin/python3 oyster_deals.py --persona brian
open docs/index.html
```

(Safe mode prevents deploy per feedback memory.)

**Visual checks:**
1. Existing venues (Rochambeau, Legal Sea Foods, Sonsie) render as before.
2. Any discovered venue shows `🆕 new` badge next to the name.
3. If any candidates have `_needs_review`, a ⚠️ strip appears at the bottom of the oyster section with linked event URLs.
4. Park 9 Dog Bar is gone.

- [ ] **Step 4: Commit**

```bash
git add boston_finder/html_output.py
git commit -m "feat(html_output): 3-state oyster rendering

Verified venues render as before. Tentative discoveries get a
🆕 badge. Events where verify couldn't extract a price surface
in a ⚠️ Needs Review strip at the bottom with manual-check links.

Part 11 of oyster pipeline simplification plan."
```

---

## Task 12: Integration fixtures — Park 9 drops, Tradesman captures

**Files:**
- Create: `tests/test_oyster_pipeline_integration.py`

End-to-end proof the two failure modes in the spec are addressed.

- [ ] **Step 1: Write integration tests**

Create `tests/test_oyster_pipeline_integration.py`:

```python
"""
End-to-end fixtures:
- Park 9 Dog Bar 'Everett Happy Hour' → filter drops it, never reaches verify.
- Tradesman Charlestown oyster event → filter passes, venue extracted from
  title, verify runs, discovery logged.
"""

from datetime import datetime
from unittest.mock import patch

from boston_finder import event_store, oyster_filter, venue_extractor, oyster_discoveries


PARK_9_EVENT = {
    "source": "do617:food-drink",
    "name": "Everett Happy Hour",
    "description": "",
    "url": "https://do617.com/events/2026/4/24/everett-happy-hour-tickets",
    "start": "2026-04-24T17:00",
    "venue": "Park 9 Dog Bar",
}

TRADESMAN_EVENT = {
    "source": "thebostoncalendar.com",
    "name": "DOLLAR OYSTERS BUCK A SHUCK TRADESMAN CHARLESTOWN",
    "description": "",
    "url": "https://www.thebostoncalendar.com/events/dollar-oysters-buck-a-shuck-tradesman-charlestown--30",
    "start": "",
    "venue": "",
}


def test_park_9_filtered_out():
    assert oyster_filter.is_oyster_candidate(PARK_9_EVENT) is False


def test_tradesman_passes_filter():
    assert oyster_filter.is_oyster_candidate(TRADESMAN_EVENT) is True


def test_tradesman_venue_extracted_from_title():
    venue = venue_extractor.extract_venue(TRADESMAN_EVENT, use_llm_fallback=False)
    assert venue == "Tradesman Charlestown"


def test_event_store_ignores_oyster_deals_cache_key(tmp_path, monkeypatch):
    """Polluted cache keys (like oyster_deals_*) would not end up in the event store
    because write_events writes a list, not the heterogeneous cache. Verify the
    read side refuses to treat non-event payloads as events."""
    import json
    bad_file = tmp_path / "events.json"
    # payload shaped like the main cache — missing 'events' key
    bad_file.write_text(json.dumps({"oyster_deals_brian": [{"name": "x"}]}))
    monkeypatch.setattr(event_store, "EVENTS_FILE", str(bad_file))

    import pytest
    with pytest.raises(event_store.EventStoreError, match="schema"):
        event_store.read_events()


def test_alias_collision_tradesman_then_longer(tmp_path, monkeypatch):
    """Ingest 'Tradesman' alone first; later 'Tradesman Charlestown' upgrades canonical."""
    monkeypatch.setattr(oyster_discoveries, "DISCOVERIES_FILE", str(tmp_path / "d.json"))

    oyster_discoveries.upsert(
        "Tradesman", "tradesman",
        {"url": "u1", "name": "n1", "source": "s1"},
        {"status": "⚠️ Unverified", "price": None},
        "trailing_caps",
    )
    # second ingest — incoming matches via prefix+neighborhood rule
    matched = venue_extractor.match_existing(
        "Tradesman Charlestown", list(oyster_discoveries.load_all().keys())
    )
    assert matched == "tradesman"

    oyster_discoveries.upsert_with_match(
        "Tradesman Charlestown", "tradesman charlestown", matched,
        {"url": "u2", "name": "n2", "source": "s2"},
        {"status": "✅ verified", "price": "$1"},
        "trailing_caps",
    )

    rec = oyster_discoveries.load_all()["tradesman"]
    assert rec["name_canonical"] == "Tradesman Charlestown"
    assert "Tradesman" in rec["aliases_seen"]
    assert rec["event_count"] == 2
```

- [ ] **Step 2: Run integration tests**

Run: `/Users/brian/python-projects/myenv/bin/pytest tests/test_oyster_pipeline_integration.py -v`
Expected: 5 passed.

- [ ] **Step 3: Run the FULL test suite once**

Run: `/Users/brian/python-projects/myenv/bin/pytest tests/ -v`
Expected: all tests pass (counts from earlier tasks).

- [ ] **Step 4: Commit**

```bash
git add tests/test_oyster_pipeline_integration.py
git commit -m "test(oyster_pipeline): integration fixtures for spec's two bugs

Park 9 Dog Bar (binary filter drop) and Tradesman Charlestown (title
venue extraction + discovery log) — both bugs from spec are covered
end-to-end.

Part 12 of oyster pipeline simplification plan."
```

---

## Task 13: Full manual pipeline run + visual verification

**Files:** none (manual verification step)

- [ ] **Step 1: Run daily event pipeline (safe mode)**

```bash
BOSTON_FINDER_SAFE_TEST=1 BOSTON_FINDER_DISABLE_OPEN=1 \
  /Users/brian/python-projects/myenv/bin/python3 boston_events.py --persona all --days 7
```

**Check:** console output includes `→ persisted N events to event store` and `~/boston_finder_events.json` was just updated:

```bash
stat -f "%Sm %N" ~/boston_finder_events.json
```

- [ ] **Step 2: Run weekly oyster pipeline (safe mode)**

```bash
BOSTON_FINDER_SAFE_TEST=1 /Users/brian/python-projects/myenv/bin/python3 oyster_deals.py --persona all
```

**Check:**
- No "Everett Happy Hour" in the output.
- Event-feed discoveries (if any) appear in the output with `🆕` or tentative markers.
- Console lists the number of candidates coming from each source.

- [ ] **Step 3: Inspect discoveries log**

```bash
/Users/brian/python-projects/myenv/bin/python3 -c "
import json
d = json.load(open('/Users/brian/boston_finder_oyster_discoveries.json'))
print(f'{len(d)} discoveries:')
for k, v in d.items():
    print(f'  {v[\"name_canonical\"]:45} status={v[\"status\"]} verify={v[\"verify_result\"].get(\"status\", \"?\")} price={v[\"verify_result\"].get(\"price\") or \"-\"}')
"
```

- [ ] **Step 4: Open the generated HTML in a browser and eyeball**

```bash
open docs/index.html
```

Walk through the oyster section:
- Known venues render with times/prices (Rochambeau, Legal Sea Foods, Sonsie).
- Discoveries show with 🆕 badge.
- "⚠️ Needs Review" strip is present if any candidate failed price extraction — click through at least one link and confirm it opens the event page.
- Park 9 Dog Bar is gone.

- [ ] **Step 5: If the visual check passes, clean up `oyster_triage.json`**

The triage file is now obsolete (AI-scored side-channel). Safe to remove — new pipeline writes to `oyster_discoveries.json` instead.

```bash
rm ~/oyster_triage.json
```

(Optional — can keep around for comparison during the first few runs; just flag as deprecated.)

- [ ] **Step 6: Update `tracking/SESSION_RESUME.md` with completion status**

Append a section noting:
- Oyster pipeline simplification done (plan at `tracking/plans/2026-04-19-oyster-pipeline-unification.md`, commit range from Task 0 through this commit).
- Deferred: Phase 2 (shared tagging) + Phase 3 (auto-promotion).
- Watch list: regex miss rate, LLM fallback cost in `costs.py`, discoveries log growth.

Commit:

```bash
git add tracking/SESSION_RESUME.md
git commit -m "docs: mark oyster pipeline simplification complete

All 13 tasks in 2026-04-19-oyster-pipeline-unification.md landed.
Phase 2 and Phase 3 explicitly deferred."
```

---

## Rollback plan

If a task in 9–11 proves untenable during integration, revert the oyster_deals/html_output commits and the pipeline reverts to the current AI-scoring behavior. The new modules (event_store, oyster_filter, venue_extractor, oyster_discoveries, verify extractors) are additive and don't break anything even if unused.

```bash
git revert <oyster_deals-commit> <html_output-commit>
```

---

## Self-review (pre-flight)

- **Spec coverage:** ✅ every spec component has a dedicated task:
  - §1 Daily event persistence → Task 1 (module) + Task 8 (wire into boston_events)
  - §2 Binary filter → Task 2
  - §3 Extended verify → Task 5 (extractors) + Task 6 (verify_event refactor)
  - §4 Venue extraction + normalization + discoveries → Tasks 3, 3b, 4, 7
  - §5 Display 3-state → Task 11
  - §6 Removed code → Task 10 (personas) + Task 9 (oyster_deals)
  - §7 Unchanged code → untouched by plan (OYSTER_VENUES, research.txt, proximity, schedule)

- **Placeholder scan:** ✅ no TBDs. One acknowledged stub (Strategy 5 returns None in Task 3, wired in Task 3b). Every step has concrete code or concrete commands.

- **Type consistency:** ✅ function signatures match across tasks: `is_oyster_candidate(event) → bool`, `extract_venue(event, use_llm_fallback=True) → str | None`, `verify_event(event, force=False) → dict`, `normalize(name) → str`, `match_existing(incoming, existing_list) → str | None`, `upsert(...)` / `upsert_with_match(...)`.

- **Testing:** ✅ each module has a test file; integration test covers both spec bugs + polluted-cache + alias-collision edge cases.
