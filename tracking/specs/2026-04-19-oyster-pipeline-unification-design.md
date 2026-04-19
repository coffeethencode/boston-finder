# Oyster Pipeline Simplification + Discovery

**Date:** 2026-04-19
**Status:** Draft — awaiting review
**Author:** Brian + Claude (brainstormed)

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

### 1. Shared fetch

`oyster_deals.py` reads events from `boston_finder_cache.json` — the same cache populated by the daily event finder run. No duplicate scraping. Cache TTL is already 168h (7d), which covers the weekly oyster Monday cadence.

**Implementation note:** `boston_finder/cache.py` already exposes `get(key)` / `set(key, value)`. The event finder writes keyed by source name; the oyster run iterates over the cached events and applies the binary filter.

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
- `oyster`, `oysters`
- `raw bar`
- `shuck`, `shucked`, `shucking`
- `buck a shuck`, `buck-a-shuck`

Case-insensitive substring match. **No price/deal keyword required at this stage** — the verify step extracts pricing. This is deliberate: we'd rather let an "Oyster Fest" event through to verify (which then confirms or drops it) than apply a second filter here that could silently drop legitimate deals.

**Why no AI:** Deterministic behavior. You can look at any event and explain why it passed or failed without reading a model's mind. Cost goes to zero for classification.

### 3. Extended verify

**Refactor:** `oyster_verify.py` currently accepts only `OYSTER_VENUES` records. After this change it accepts `(name, url, optional_event_text)` tuples — works for both registered venues and discovered events.

**New extractors:**

```python
def extract_price(text: str) -> str | None:
    """Return e.g. '$1', '$2.50', 'half-price', 'BOGO', or None."""

def extract_hours(text: str) -> dict | None:
    """Return {'days': [...], 'start': '17:00', 'end': '18:00'} or None."""
```

Regex patterns (starting set — refine from real data):
- Price: `\$\d+(?:\.\d+)?(?=\s*(?:oyster|each|per))`, `half[- ]?price`, `BOGO`, `2[- ]for[- ]1`, `dollar\s+oyster`, `buck[- ]a[- ]shuck`
- Hours: `(Mon|Tue|Wed|Thu|Fri|Sat|Sun)(?:day)?(?:s)?[\s\-to]*(Mon|Tue|...)?`, `\d{1,2}(?::\d{2})?(?:\s?[ap]m)?\s?[-–to]\s?\d{1,2}(?::\d{2})?(?:\s?[ap]m)?`
- Closed signals: existing list in `oyster_verify.py` (keep)

Extractors apply to the venue's specials page AND the event description (whichever has content). First successful extraction wins.

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

### 4. Discoveries log

**New file:** `~/boston_finder_oyster_discoveries.json`

Per-venue record for events where `venue ∉ OYSTER_VENUES` (after normalization):

```json
{
  "tradesman-charlestown": {
    "name_raw": "Tradesman Charlestown",
    "name_normalized": "tradesman charlestown",
    "neighborhood": "Charlestown",
    "first_seen": "2026-04-17",
    "last_seen": "2026-04-19",
    "sources_seen": ["thebostoncalendar.com", "do617"],
    "event_urls": ["https://www.thebostoncalendar.com/events/dollar-oysters-buck-a-shuck-tradesman-charlestown--84"],
    "event_titles": ["Dollar Oysters Buck A Shuck Tradesman Charlestown"],
    "verify_result": { ... },
    "event_count": 2,
    "status": "tentative"
  }
}
```

`status` ∈ `{tentative, promoted, dormant}`:
- `tentative` — default for new discoveries
- `promoted` — manually moved into `OYSTER_VENUES` (stays in log for history)
- `dormant` — hasn't been seen in N weeks (decision on N deferred to Phase 3)

**Venue name normalization:**
- Lowercase
- Strip punctuation except dashes/spaces
- Collapse whitespace
- Do NOT strip neighborhood suffixes — "Legal Sea Foods Copley" vs "Legal Sea Foods Prudential" are distinct venues

**Dedup order:** check against `OYSTER_VENUES` (by normalized name) first; if no match, check `discoveries.json`; if no match, create new record.

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
│  fetches all sources → boston_finder_cache.json          │
│  scores with persona prompts → scored.json → HTML/deploy │
└──────────────────────────────────────────────────────────┘
                         │
                         ▼  (cache populated, fresh for 7 days)
┌──────────────────────────────────────────────────────────┐
│  WEEKLY MONDAY (8:12 AM) — oyster run                    │
│                                                          │
│  1. Read cache (shared) + OYSTER_VENUES + research.txt   │
│  2. Binary filter — is_oyster_candidate()                │
│  3. Normalize venue names, dedupe against OYSTER_VENUES  │
│  4. For candidates: verify (extract price/hours)         │
│  5. Update boston_finder_oyster_status.json              │
│  6. Update boston_finder_oyster_discoveries.json         │
│  7. Merge verified + tentative + manual-check sets       │
│  8. Proximity filter per persona                         │
│  9. Write HTML oyster section → deploy                   │
└──────────────────────────────────────────────────────────┘
```

## Files touched

| File | Change |
|------|--------|
| `boston_finder/oyster_filter.py` | **NEW** — binary classifier |
| `boston_finder/oyster_sources.py` | Read from cache + discoveries.json; keep OYSTER_VENUES + research.txt paths |
| `oyster_verify.py` | Refactor to accept event dicts; add `extract_price`, `extract_hours` |
| `oyster_deals.py` | Remove `score()` call on oyster path; use binary filter + verify output |
| `boston_finder/personas.py` | Remove `oyster_prompt` from all 4 personas |
| `boston_finder/html_output.py` | Add "Needs Review" strip; render tentative "new" badge |
| `tests/test_oyster_filter.py` | **NEW** — filter keyword matching |
| `tests/test_oyster_verify_extractors.py` | **NEW** — price/hours regex |
| `tests/test_oyster_venue_normalization.py` | **NEW** — name dedup |

## Testing

**Unit:**
- Filter positive cases: "$1 Oyster Brunch", "Dollar Oysters Buck A Shuck", "Raw Bar Happy Hour", "Oyster Fest".
- Filter negative cases: "Everett Happy Hour" (no keyword), "Wine Tasting" (no keyword), "Happy Hour" (no oyster keyword).
- Price regex: `$1 oysters`, `$1.50 each`, `half-price oysters`, `half price raw bar`, `BOGO oysters`, `dollar oysters`, `buck a shuck`, and the negative case of a random `$5` not near oyster text.
- Hours regex: `Mon-Wed 5-6pm`, `daily 3–6pm`, `Mondays 9–10pm`, `Tue Wed Thu 4-6`, `every weekday 5pm-7pm`.
- Venue normalization: "Tradesman Charlestown" vs "Tradesman, Charlestown" vs "TRADESMAN  Charlestown" → same ID. "Legal Sea Foods Copley" vs "Legal Sea Foods Prudential" → distinct IDs.

**Integration fixtures:**
- Seed cache with Park 9 Dog Bar "Everett Happy Hour" event → assert: filtered out at step 2, never reaches verify, not in output.
- Seed cache with Tradesman Charlestown "$1 Oyster Brunch" event → assert: passes filter, verify runs, logged in discoveries.json, appears in HTML.

**Manual:**
- Run full weekly pipeline locally. Visual check: known venues render unchanged; any discoveries appear in tentative + "new" badge; verify-failed items appear in "Needs Review" strip.
- Use `BOSTON_FINDER_SAFE_TEST=1` to prevent deploy during testing (per existing project convention).

## Migration

No data migration needed:
- `boston_finder_oyster_status.json` schema extends backward-compatibly (new fields nullable on existing records; verify re-run fills them in).
- `OYSTER_VENUES` untouched.
- `oyster_triage.json` becomes obsolete — safe to leave in place but unused (or delete after one clean run verifies output parity).

## Risks

- **Regex miss rate.** Real deal text is messy ("Shuck Happy on select weekdays — ask your server"). Initial miss rate could be high. Mitigation: failed extractions land in "Needs Review" strip, not dropped, so nothing is lost. We observe the strip for a few weeks and refine regex or add a narrow AI parsing fallback.
- **Cache freshness.** If the daily event finder run fails for multiple days, the oyster run may read stale data. Acceptable — cache TTL already handles this, and the event finder has its own monitoring.
- **Name normalization collisions.** "Legal" alone would over-collapse Legal Sea Foods branches. Mitigation: preserve full venue name including neighborhood in normalization.
- **Discovery noise.** One-off events (e.g. "Valentine's Oyster Dinner") will appear as tentative discoveries. Acceptable for Phase 1 — user reviews manually, demotes as needed. Phase 3 will add auto-promotion rules to handle this.

## Open questions

None blocking. Deferred to future phases:
- What triggers tentative → dormant? (Phase 3)
- Multi-label tagging pass to eliminate event-finder Haiku duplication? (Phase 2)
- Should discoveries.json support tags (`seasonal`, `restaurant-week-only`, etc.) for human annotation? (Phase 3)
