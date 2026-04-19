# Oyster Pipeline Simplification + Discovery

**Date:** 2026-04-19
**Status:** Draft v2 — revised after Codex review
**Author:** Brian + Claude (brainstormed)

**Revisions (2026-04-19):**
- **Blocker fix (Codex #1):** shared fetch via existing cache was a false assumption. `boston_finder_cache.json` only contains `enrich:*` and `oyster_deals_*` keys — no iterable event records. Event persistence is now an explicit Phase 1 deliverable.
- **Blocker fix (Codex #2):** Boston Calendar events in `scored.json` have empty `venue` and `description` fields (e.g., "DOLLAR OYSTERS BUCK A SHUCK TRADESMAN CHARLESTOWN" — venue only in title). Added dedicated venue extraction step with multiple strategies + LLM fallback.
- Expanded keyword list (bivalves, wellfleets, duxburys, shellfish happy hour) and made "missed events" explicit policy rather than silent drops.
- Normalization revised to handle aliases (Tradesman vs Tradesman Charlestown, Woods Hill Pier vs Woods Hill Pier 4).
- Expanded regex fixtures for dashes, ranges, open-ended hours, multi-window deals.
- Added tests for polluted cache keys, alias collisions, empty-venue discoveries.

## Problem

Two observed bugs in the current oyster pipeline — both rooted in the same structural mismatch.

### Bug 1 — false positives from loose AI scoring

`oyster_deals.py` runs every event in `get_sources("food")` (do617 Food & Drink, allevents Food & Drink, Thrillist, Harpoon, Boston Magazine, etc.) through an AI oyster-scoring prompt. The oyster prompt is a **ranking** prompt ("how good is this oyster deal?"), not a **classification** prompt ("is this an oyster deal at all?"). With `min_score` at 5 (the default across personas), low-information events anchor at the threshold and leak through.

Concrete example: `do617.com/events/2026/4/24/everett-happy-hour-tickets` — title "Everett Happy Hour", description empty, venue "Park 9 Dog Bar". Haiku returns score 5 with reason *"Happy hour in Everett — decent deal potential, but location is far from South End and no venue/vibe details provided. Scores at minimum threshold without more information."* It renders in the oyster HTML under "HIKE" with no time field (the record has `start: "2026-04-24T17:00"` but no end time, and the oyster template only renders time ranges). User cannot manually verify any oyster presence at Park 9.

### Bug 2 — event-feed discoveries are invisible to the oyster tracker

The event finder (daily run) fetches from ~50 sources including `thebostoncalendar.com/events`, which surfaces real oyster deals like "Dollar Oysters Buck A Shuck Tradesman Charlestown" and "$1 Oyster Brunch" at venues not in `OYSTER_VENUES`. These appear on `highendeventfinder.netlify.app` via the daily event finder's HTML output.

But `oyster_deals.py` does **not** pull from these sources for its weekly registry view — it reads only the hardcoded `OYSTER_VENUES` list (~15 Boston + Providence) and the pasted `~/oyster_research.txt`. So the Tradesman discovery is visible once, in the daily feed, then forgotten. The venue is never added to the standing registry that gets scraped weekly for future deals.

### Root cause (shared by both bugs)

The oyster tracker treats "oyster deal" as an AI-judgment problem when it's fundamentally a rules problem with a verification step. The distinguishing feature of a deal is **price** — a quantity you can extract from text, not a quality you need to rank.

## Approach

Replace AI oyster scoring with a rule-based binary filter + an extended verify step that extracts price and hours. Share the fetch cache with the event finder so the oyster pipeline sees every source. Log venues not in the registry as discoveries for manual promotion.

**Key insight:** The user reframed mid-brainstorm — *"we hardly need to score oysters. it's binary. it exists or not. it's just a distance filter."* and *"do we pull the prices as part of verify process and just say how much they are?"* The design follows that simplification.

## Scope of this spec

**In scope (Phase 1):**
- Shared fetch via existing `boston_finder_cache.json`
- Binary oyster filter (keyword match)
- Extended `oyster_verify.py` with price + hours extractors
- Discoveries log with manual-promotion flow
- Removal of oyster AI scoring code path

**Out of scope (future phases):**
- Phase 2 — unified tagging pass on the event-finder side (eliminate duplicate Haiku scoring for overlapping events)
- Phase 3 — auto-promote tentative → active based on accumulated data (secondary-source probes, Instagram verification, repeat-event signal, confidence score)

The phased order was a deliberate choice: ship data collection first, design promotion rules after we've seen what the tentative venue stream actually looks like. Venue patterns are seasonal (*"off season for a place usually when not busy, so they will go for months at a time then stop"*), so designing confidence rules before observing that pattern risks premature optimization.

## Design

### 1. Daily event persistence (new plumbing)

**Current state:** `boston_events.py::fetch_shared()` fetches all sources and returns a deduped event list in-memory. The list dies at end of run. `boston_finder_cache.json` contains only `enrich:*` per-URL snippets + 3 `oyster_deals_*` entries — no iterable event stream.

**Change:** after `fetch_shared()` completes in `boston_events.py`, write the deduped event list to a new file:

**File:** `~/boston_finder_events.json`

```json
{
  "fetched_at": "2026-04-19T08:07:00",
  "event_count": 1423,
  "events": [
    {"name": "...", "url": "...", "start": "...", "venue": "...",
     "address": "...", "description": "...", "source": "..."},
    ...
  ]
}
```

Overwritten daily — single source of truth, always freshest. Event finder run is the only writer; no TTL needed because the file is regenerated every 24h.

**New module:** `boston_finder/event_store.py`

```python
def write_events(events: list[dict], fetched_at: datetime) -> None:
    """Persist deduped event list. Called at end of fetch_shared()."""

def read_events(max_age_hours: int = 48) -> list[dict]:
    """
    Return events from the last fetch. Raise StaleEventsError if older
    than max_age_hours. 48h default: weekly run on Monday 8:12 AM reads
    data written daily at 8:07 AM, well under 48h.
    """
```

`oyster_deals.py` calls `read_events()` instead of re-running `fetch_shared()`.

**Why not reuse `cache.py`:** that module is keyed by string, values are arbitrary. Adding a dedicated event store keeps the event list schema explicit and iterable without polluting the generic cache with 1400+ keys.

**Explicit non-goal:** no filtering or cache-key exclusions inside the store. It's a write-the-output-of-fetch-shared file. Filter application happens in the oyster filter step.

### 2. Binary oyster filter

**New module:** `boston_finder/oyster_filter.py`

```python
def is_oyster_candidate(event: dict) -> bool:
    """
    Return True if the event text mentions oysters.
    Pure rules — no AI call. Price/hours/verify come later.
    """
```

Rule: `title.lower()` or `description.lower()` contains any of:

**Primary (direct oyster references):**
- `oyster`, `oysters`
- `raw bar`
- `shuck`, `shucked`, `shucking`
- `buck a shuck`, `buck-a-shuck`

**Secondary (varieties + adjacent terms) — added after Codex noted these legitimate variants:**
- `bivalves`, `bivalve`
- `wellfleet`, `wellfleets` (common Massachusetts oyster variety)
- `duxbury`, `duxburys` (common Massachusetts oyster variety)
- `shellfish happy hour`
- `raw bar happy hour`

Case-insensitive substring match. **No price/deal keyword required at this stage** — the verify step extracts pricing. This is deliberate: we'd rather let an "Oyster Fest" event through to verify (which then confirms or drops it) than apply a second filter here that could silently drop legitimate deals.

**Policy on missed events:** the keyword set won't catch everything (e.g., a deal described only on a linked menu, or phrased as "shellfish Monday"). Accept this explicitly: misses don't surface, they aren't silent failures. As we observe what lands in the Needs Review strip and what we learn about from other channels, we expand the keyword list iteratively. Phase 3 adds AI classification as a fallback if rule-based misses prove material.

**Why no AI here:** Deterministic behavior. You can look at any event and explain why it passed or failed without reading a model's mind. Cost goes to zero for classification. The AI budget, if any, is reserved for venue extraction (§4) where deterministic parsing genuinely fails.

### 3. Extended verify

**Refactor:** `oyster_verify.py` currently accepts only `OYSTER_VENUES` records. After this change it accepts `(name, url, optional_event_text)` tuples — works for both registered venues and discovered events.

**New extractors:**

```python
def extract_price(text: str) -> str | None:
    """Return e.g. '$1', '$2.50', 'half-price', 'BOGO', or None."""

def extract_hours(text: str) -> dict | None:
    """Return {'days': [...], 'start': '17:00', 'end': '18:00'} or None."""
```

Regex patterns (starting set — refined from Codex-observed real-data patterns):

**Price** must handle:
- Simple: `$1 oysters`, `$1.50 per oyster`, `dollar oysters`
- Ranges: `$1 - $2 oysters`, `$1–$2 oysters` (en dash)
- Variety name between price and "oysters": `$1 Duxbury oysters`, `$1.50 Island Creek oysters`
- Deal phrases: `half price`, `half-price`, `BOGO`, `2 for 1`, `2-for-1`, `buck a shuck`

Pattern set:
```python
PRICE_PATTERNS = [
    r"\$\d+(?:\.\d+)?\s*[-–]\s*\$\d+(?:\.\d+)?\s+(?:\w+\s+)?oysters?",  # ranges
    r"\$\d+(?:\.\d+)?\s+(?:\w+\s+)?oysters?",                          # simple + variety
    r"(?i)half[- ]?price\s+(?:\w+\s+)?oysters?",
    r"(?i)BOGO\s+(?:\w+\s+)?oysters?",
    r"(?i)2[- ]?for[- ]?1\s+(?:\w+\s+)?oysters?",
    r"(?i)dollar\s+oysters?",
    r"(?i)buck[- ]?a[- ]?shuck",
]
```

**Hours** must handle:
- Ranges: `Mon-Wed 5-6pm`, `Mon–Wed 5–6pm` (en dash), `Tue Wed Thu 4-6`, `daily 3-6pm`
- Single-day: `Mondays 9-10pm`, `every Monday 5pm-7pm`
- Open-ended: `Mondays 4 PM until sold out`, `Daily starting at 5 PM`
- Multi-window: `Sun-Thu 9-11 PM; Fri-Sat 10 PM-12 AM`

Approach: parse into list of windows rather than single `{days, start, end}`. Schema:
```python
{"windows": [
    {"days": ["Sun","Mon","Tue","Wed","Thu"], "start": "21:00", "end": "23:00"},
    {"days": ["Fri","Sat"], "start": "22:00", "end": "00:00"}
]}
```
Multi-window split on `;` or newline before parsing each window. Open-ended ("until sold out", "starting at") stored as `{"start": "21:00", "end": None}`.

**Closed signals:** existing list in `oyster_verify.py` (keep).

Extractors apply to the venue's specials page, the event description, AND the event title. First successful extraction wins. Store extraction source on the verify record for debuggability.

**Verify record grows:**

```json
{
  "status": "✅ verified" | "⚠️ Unverified" | "❌ closed",
  "verified_at": "2026-04-19T08:12:00",
  "price": "$1",
  "hours": {"days": ["Mon", "Tue", "Wed"], "start": "17:00", "end": "18:00"},
  "closed": false,
  "maps_url": "...",
  "source_url": "https://...",
  "notes": ""
}
```

TTL stays 7 days in `~/boston_finder_oyster_status.json` (existing file, extended schema).

### 4. Venue extraction + discoveries log

Boston Calendar events in the real data have `venue: ""` and `description: ""` — the venue is embedded in the event name (e.g., `"DOLLAR OYSTERS BUCK A SHUCK TRADESMAN CHARLESTOWN"` → venue "Tradesman Charlestown"; `"$1 Oysters at Lincoln Tavern & Restaurant"` → venue "Lincoln Tavern & Restaurant"). Venue extraction is therefore non-trivial and gets its own layered strategy.

**New module:** `boston_finder/venue_extractor.py`

#### Extraction strategy (first match wins)

**Strategy 1 — event.venue field**
If non-empty after stripping, use it.

**Strategy 2 — "at <venue>" pattern in title**
Regex: `(?i)\b(?:at|@|hosted at|held at)\s+(.+?)(?:\s*[—–|,\-]|\s*$)`
Handles: "$1 Oysters at Lincoln Tavern & Restaurant", "$1 Oyster Brunch at Fairsted Kitchen".

**Strategy 3 — trailing capitalized words in title**
Strip known oyster/deal prefix tokens (`$1`, `dollar`, `buck`, `a`, `shuck`, `oysters`, `raw`, `bar`, `happy`, `hour`, case-insensitive) from both ends. Remaining contiguous capitalized-word run is the venue candidate.
Handles: "DOLLAR OYSTERS BUCK A SHUCK TRADESMAN CHARLESTOWN" → "TRADESMAN CHARLESTOWN".

**Strategy 4 — URL slug parse**
For Boston Calendar and similar, the URL slug often contains the venue:
`.../dollar-oysters-buck-a-shuck-tradesman-charlestown--30` → after stripping prefix deal keywords and trailing `--NN` counter, "tradesman charlestown".
Use as confirmation of strategy 3, or as primary when strategy 3 yields nothing.

**Strategy 5 — LLM fallback (narrow, one-shot Haiku call)**
Only invoked when strategies 1–4 all return empty or ambiguous result. Prompt shape:
```
Given this event title, description, and URL, return ONLY the venue name
(restaurant / bar / shop / building). No extra text. If unclear, return "UNKNOWN".
Title: ...
Description: ...
URL: ...
```
Result "UNKNOWN" → venue field stays empty, event goes to Needs Review strip with manual check required.

Budget: LLM fallback fires at most once per unique (title, url) pair. Cached in extraction status so subsequent runs don't repay. Expect <5 calls per week based on current data shape (most events either have venue populated or match strategies 2–4).

#### Venue name normalization + alias handling

Same venue often appears under multiple names:
- "Tradesman" vs "Tradesman Charlestown" (chain branch implicit vs explicit)
- "Woods Hill Pier" vs "Woods Hill Pier 4" (same place, different formality)
- "Legal Sea Foods Copley" vs "Legal Sea Foods Prudential" (**distinct branches** — must NOT collapse)

**Normalization steps:**
1. Lowercase
2. Strip punctuation except spaces and digits (keep "4" in "Pier 4", strip "&"/apostrophes)
3. Collapse whitespace
4. Trim

**Dedup rule (ordered):**
1. Exact normalized match → same venue.
2. Prefix match where longer form adds a recognized neighborhood token (from a curated list of Boston/Cambridge neighborhoods: `charlestown, cambridge, back bay, south end, north end, fort point, seaport, fenway, allston, brighton, somerville, providence, kendall, harvard square, beacon hill, jamaica plain, ...`) → same venue, upgrade canonical form to the longer one.
3. Prefix match where longer form adds a *non*-neighborhood modifier (numbers, branded suffixes like "Copley", "Prudential") → **distinct venues**. Branded branches of the same chain are separate records.
4. No match → new venue record.

**Curated alias map** for known collapses that normalization can't auto-detect:
```python
ALIASES = {
    "woods hill pier": "woods hill pier 4",
    # add more as observed
}
```
Alias map is a deliberate manual override — the cost of maintaining it is low, and correctness beats cleverness for a small controlled set.

#### Discoveries log

**New file:** `~/boston_finder_oyster_discoveries.json`

Per-venue record for events where the extracted venue ∉ `OYSTER_VENUES` (after normalization + alias resolution):

```json
{
  "tradesman-charlestown": {
    "name_canonical": "Tradesman Charlestown",
    "name_normalized": "tradesman charlestown",
    "aliases_seen": ["Tradesman", "TRADESMAN CHARLESTOWN"],
    "neighborhood": "Charlestown",
    "first_seen": "2026-04-17",
    "last_seen": "2026-04-19",
    "sources_seen": ["thebostoncalendar.com", "do617"],
    "event_urls": ["https://www.thebostoncalendar.com/events/dollar-oysters-buck-a-shuck-tradesman-charlestown--84"],
    "event_titles": ["Dollar Oysters Buck A Shuck Tradesman Charlestown"],
    "extraction_strategy": "trailing_caps",
    "verify_result": { ... },
    "event_count": 2,
    "status": "tentative"
  }
}
```

`status` ∈ `{tentative, promoted, dormant}`:
- `tentative` — default for new discoveries.
- `promoted` — manually moved into `OYSTER_VENUES`; stays in log for history and dormancy tracking.
- `dormant` — hasn't been seen in N weeks. Decision on N + auto-transitions deferred to Phase 3.

**Dedup order during ingest:**
1. Check against `OYSTER_VENUES` (by normalized name + alias map).
2. If no match, check `discoveries.json`.
3. If no match, create new record.

### 5. Display states

Existing HTML oyster section (`boston_finder/html_output.py`) renders three states per venue:

1. **Verified with deal** (current behavior for known venues) — price + hours, proximity-labeled.
2. **Tentative (discovery, verify passed)** — same layout + a "new" badge. Uses verify result's extracted price/hours.
3. **Needs manual check** (verify failed, no price extracted) — surfaced in a new "⚠️ Needs Review" strip at the bottom of the oyster section. Each entry shows event title, venue, source URL, and a link to open the event page for human verification. User can then manually promote to `OYSTER_VENUES` or mark as not-an-oyster.

The "Needs Review" strip is a discovery vector — over time, patterns in what lands there inform what heuristics could automate the promotion decision (Phase 3).

### 6. What gets removed

- `oyster_prompt` fields in all 4 personas (`boston_finder/personas.py`).
- `get_oyster_prompt()` function.
- `min_score` check on the oyster path (keep for event finder).
- Haiku `score()` call in `oyster_deals.py`'s pipeline. Oyster-run cost drops to ~$0 (verify still makes HTTP calls; no LLM calls on this path).

### 7. What stays the same

- `OYSTER_VENUES` hardcoded list (authoritative active set).
- `~/oyster_research.txt` ingestion (`get_all()` continues to parse the tab-delimited paste).
- Proximity filtering by persona (`location.py`).
- Weekly Monday 8:12 AM cadence (LaunchAgent unchanged).
- HTML oyster section structure — only the data feeding it changes.

## Data flow

```
┌──────────────────────────────────────────────────────────┐
│  DAILY (8:07 AM) — event finder                          │
│  fetch_shared() → all event sources → deduped list       │
│  NEW: event_store.write_events() → ~/boston_finder_events.json │
│  score() per persona → scored.json → HTML/deploy         │
└──────────────────────────────────────────────────────────┘
                         │
                         ▼  (events file freshly written daily)
┌──────────────────────────────────────────────────────────┐
│  WEEKLY MONDAY (8:12 AM) — oyster run                    │
│                                                          │
│  1. event_store.read_events(max_age_hours=48)            │
│  2. Binary filter — is_oyster_candidate() per event      │
│  3. Venue extraction (5-strategy) for each candidate     │
│  4. Normalize + alias-resolve venue names                │
│  5. Dedupe against OYSTER_VENUES + discoveries.json      │
│  6. For each unique venue: verify                        │
│     → scrape venue page or event URL                     │
│     → extract price (ranges, varieties, deal phrases)    │
│     → extract hours (multi-window, open-ended)           │
│  7. Update boston_finder_oyster_status.json              │
│  8. Update boston_finder_oyster_discoveries.json         │
│  9. Partition: verified | tentative | needs_review       │
│ 10. Proximity filter per persona                         │
│ 11. Write HTML oyster section (3-state rendering)        │
│ 12. Deploy                                                │
└──────────────────────────────────────────────────────────┘
```

**Stale event store behavior:** if `read_events()` raises `StaleEventsError`, the oyster run logs a warning and proceeds with just `OYSTER_VENUES` + `research.txt` — same output as today. No crash, no silent regression.

## Files touched

| File | Change |
|------|--------|
| `boston_finder/event_store.py` | **NEW** — write_events / read_events for daily persistence |
| `boston_finder/oyster_filter.py` | **NEW** — binary classifier |
| `boston_finder/venue_extractor.py` | **NEW** — layered venue extraction (5 strategies + LLM fallback) |
| `boston_events.py` | Call `event_store.write_events()` after `fetch_shared()` |
| `boston_finder/oyster_sources.py` | Read from event store + discoveries.json; keep OYSTER_VENUES + research.txt paths |
| `oyster_verify.py` | Refactor to accept event dicts; add `extract_price`, `extract_hours` with multi-window support |
| `oyster_deals.py` | Remove `score()` call on oyster path; use binary filter + verify output |
| `boston_finder/personas.py` | Remove `oyster_prompt` from all 4 personas |
| `boston_finder/html_output.py` | Add "Needs Review" strip; render tentative "new" badge |
| `tests/test_event_store.py` | **NEW** — write/read roundtrip, staleness error |
| `tests/test_oyster_filter.py` | **NEW** — filter keyword matching (positive + negative) |
| `tests/test_venue_extractor.py` | **NEW** — each of 5 strategies, edge cases |
| `tests/test_oyster_verify_extractors.py` | **NEW** — price/hours regex, multi-window |
| `tests/test_oyster_venue_normalization.py` | **NEW** — alias handling, chain-branch distinction |

## Testing

**Unit — event store:**
- Roundtrip: write 1000-event list, read back, assert same count + order.
- Staleness: write file with old `fetched_at`, `read_events(max_age_hours=48)` raises `StaleEventsError`.
- Schema: reading a file without `events` key raises clear error.

**Unit — oyster filter:**
- Positive: "$1 Oyster Brunch", "Dollar Oysters Buck A Shuck Tradesman Charlestown", "Raw Bar Happy Hour", "Oyster Fest", "bivalves tasting", "Wellfleets $1 Monday", "shellfish happy hour at Island Creek".
- Negative: "Everett Happy Hour" (no keyword), "Wine Tasting", "Happy Hour", "$1 Beer Tuesday", "Oyster Mushroom Workshop" (→ note: this would pass current rule. Acceptable — verify step will drop if no price extracted near an oyster-food context. Add as a deliberate-passthrough test.)

**Unit — venue extractor:**
- Strategy 1 (venue field): non-empty field passes through.
- Strategy 2 ("at X"): "$1 Oysters at Lincoln Tavern & Restaurant" → "Lincoln Tavern & Restaurant".
- Strategy 3 (trailing caps): "DOLLAR OYSTERS BUCK A SHUCK TRADESMAN CHARLESTOWN" → "Tradesman Charlestown" (also test title-case correction).
- Strategy 4 (URL slug): `/dollar-oysters-buck-a-shuck-tradesman-charlestown--30` → "tradesman charlestown".
- Strategy 5 (LLM fallback): mock Haiku returning "Tradesman Charlestown" for ambiguous title; ensure cached after first call.
- Negative: event with only `$1 Oyster Night` in all fields → extractor returns None → event goes to Needs Review.

**Unit — price regex:**
- Simple: `$1 oysters` → "$1". `$1.50 each oyster` → "$1.50".
- Range: `$1 - $2 oysters` → "$1-$2". `$1–$2 oysters` (en dash) → "$1–$2".
- Variety between: `$1 Duxbury oysters` → "$1". `$1.50 Island Creek oysters` → "$1.50".
- Phrases: `half-price oysters`, `half price raw bar`, `BOGO oysters`, `2 for 1 oysters`, `dollar oysters`, `buck a shuck`.
- Negative: random `$5 cocktail` not near oyster text → None.

**Unit — hours regex:**
- Simple: `Mon-Wed 5-6pm` → one window.
- En dash: `Mon–Wed 5–6pm` → one window.
- Multi-day list: `Tue Wed Thu 4-6` → one window with 3 days.
- Single day: `Mondays 9-10pm` → one window.
- Open-ended: `Mondays 4 PM until sold out` → `{days:["Mon"], start:"16:00", end:null}`.
- Open-ended 2: `Daily starting at 5 PM` → `{days:[all], start:"17:00", end:null}`.
- Multi-window: `Sun-Thu 9-11 PM; Fri-Sat 10 PM-12 AM` → two windows.

**Unit — venue normalization + aliases:**
- "Tradesman Charlestown" vs "Tradesman, Charlestown" vs "TRADESMAN  Charlestown" → same canonical.
- "Tradesman" (alone) + "Tradesman Charlestown" → prefix + neighborhood suffix → **same venue**, canonical = longer form.
- "Woods Hill Pier" + "Woods Hill Pier 4" → alias map collapses to "Woods Hill Pier 4".
- "Legal Sea Foods Copley" + "Legal Sea Foods Prudential" → same chain root but non-neighborhood suffix → **distinct venues**.
- "Legal Sea Foods" (no suffix) + "Legal Sea Foods Copley" → prefix without neighborhood → **distinct** (branded branch ambiguity — refuse to auto-merge).

**Integration fixtures:**
- Park 9 Dog Bar "Everett Happy Hour" in event store → filter drops it → verify never runs → not in output.
- Tradesman Charlestown "DOLLAR OYSTERS BUCK A SHUCK TRADESMAN CHARLESTOWN" in event store, empty venue field → extractor strategy 3 yields "Tradesman Charlestown" → filter passes → verify runs against the event URL → discoveries.json gets record → appears in HTML under tentative strip.
- Polluted cache: event store with 1000 valid events + a ghost `oyster_deals_brian` string accidentally present → read_events ignores non-event payloads cleanly (schema guards).
- Empty-venue Boston Calendar event with no name/description match → extractor LLM fallback returns "UNKNOWN" → event surfaces in Needs Review with manual-check link, NOT dropped silently.
- Alias collision: ingest "Tradesman — $1 Duxbury oysters" (from deep_research) BEFORE seeing the Boston Calendar "TRADESMAN CHARLESTOWN" event → second ingest recognizes as same venue, upgrades canonical form to "Tradesman Charlestown".

**Manual:**
- Run full weekly pipeline locally. Visual check: known venues render unchanged; any discoveries appear in tentative + "new" badge; verify-failed items appear in "Needs Review" strip with event-URL link.
- Use `BOSTON_FINDER_SAFE_TEST=1` to prevent deploy during testing (per existing project convention).

## Migration

No data migration needed:
- `boston_finder_oyster_status.json` schema extends backward-compatibly (new fields nullable on existing records; verify re-run fills them in).
- `OYSTER_VENUES` untouched.
- `oyster_triage.json` becomes obsolete — safe to leave in place but unused (or delete after one clean run verifies output parity).

## Risks

- **Regex miss rate.** Real deal text is messy ("Shuck Happy on select weekdays — ask your server"). Initial miss rate could be high. Mitigation: failed extractions land in "Needs Review" strip, not dropped, so nothing is lost. We observe the strip for a few weeks and refine regex or add a narrow AI parsing fallback.
- **Event store staleness.** If the daily event finder run fails for multiple days, `read_events()` raises `StaleEventsError`. The oyster run logs the failure and continues with just `OYSTER_VENUES` + research.txt (same behavior as today). No regression; just no new discoveries that week.
- **Venue extraction misclassification.** Strategy 3 (trailing caps) could pick up non-venue words. E.g., "Raw Bar Happy Hour — SUNDAY SPECIAL" → "Sunday Special". Mitigation: prefix/suffix stopword list includes day-of-week and generic event modifiers. LLM fallback (strategy 5) corrects when rule-based strategies return suspect output (stopword-only result).
- **LLM fallback cost.** Strategy 5 fires only when 1–4 fail. Caching on (title, url) prevents re-payment. Based on sampled data, expect <5 calls/week → pennies. Monitor via `costs.py`.
- **Name normalization — chain-branch collapse.** "Legal Sea Foods" alone merging with "Legal Sea Foods Copley" would lose resolution. Mitigation: the prefix-with-neighborhood-suffix rule (§4) only merges when the suffix is in the curated neighborhood list. Branded suffixes (Copley, Prudential) keep branches distinct by default.
- **Prefix-match tricky cases.** If the shorter name is seen *first* (e.g., "Tradesman") and later we see "Tradesman Charlestown", we need to upgrade the canonical form without losing history. Integration test covers this.
- **Discovery noise.** One-off events (e.g. "Valentine's Oyster Dinner") will appear as tentative discoveries. Acceptable for Phase 1 — user reviews manually, demotes as needed. Phase 3 will add auto-promotion rules to handle this.
- **Keyword miss policy.** Some legitimate oyster deals won't use any primary/secondary keyword (e.g., "shellfish Monday" without "happy hour"). These are silently missed. Explicit accept: the cost of a broader filter is more junk in Needs Review. Track missed deals seen from external channels (friend mentions, Instagram) and expand the keyword list quarterly.

## Open questions

None blocking. Deferred to future phases:
- What triggers tentative → dormant? (Phase 3)
- Multi-label tagging pass to eliminate event-finder Haiku duplication? (Phase 2)
- Should discoveries.json support tags (`seasonal`, `restaurant-week-only`, etc.) for human annotation? (Phase 3)

## Codex review resolution (v2)

| Finding | Severity | Resolution |
|---------|----------|------------|
| #1 Shared cache assumption false | blocker | Resolved — new `event_store.py` module + explicit "Daily event persistence" section; `boston_events.py` writes to it after `fetch_shared()` |
| #2 Tradesman venue extraction | blocker | Resolved — new `venue_extractor.py` with 5-strategy extraction including title-parsing + URL-slug + LLM fallback |
| #3 Park 9 test needs cache-iterator fixture | consider | Resolved — integration fixture now exercises event_store path with Park 9 record |
| #4 Normalization under-collapses aliases | consider | Resolved — prefix-with-neighborhood rule + curated alias map for exceptional cases like "Woods Hill Pier" |
| #5 Regex patterns too narrow | consider | Resolved — expanded price patterns for ranges/varieties/en-dash; multi-window hours; open-ended hours |
| #6 Removed AI drops weak-worded deals | consider | Resolved — expanded keyword set (bivalves, wellfleet, duxbury, shellfish happy hour); explicit policy that misses aren't silent failures |
| #7 Shared fetch plumbing missing | minor | Resolved — event store is now explicit Phase 1 deliverable, not "free" infra |
| #8 Test gaps | minor | Resolved — added fixtures for polluted cache keys, empty-venue discoveries, alias collisions, multi-window hours |
