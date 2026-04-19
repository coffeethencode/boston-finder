# Venue Status Probe — Phase 2 Spec

**Date:** 2026-04-19
**Status:** Draft — placeholder, needs brainstorming pass before implementation
**Parent:** `2026-04-19-oyster-pipeline-unification-design.md` (Phase 1 shipped on branch `oyster-pipeline-simplify`)

## Problem

The oyster pipeline's known-venue list (`boston_finder/oyster_sources.py::OYSTER_VENUES`) is hand-curated. Venues close or get hijacked (B&G Oysters: permanently closed per Google Maps; its domain now serves a crypto-scam page that still contains the word "oyster", which the keyword scraper trips on). With AI scoring removed in Phase 1, weak matches on junk content render as deals until someone notices and manually edits the list.

Three classes of failure the Phase 1 pipeline can't detect on its own:
1. **Permanent closure** — business shut down, domain may or may not still resolve.
2. **Domain hijack** — same domain now serves unrelated content that happens to match keywords.
3. **Temporary closure** — renovation, seasonal, pandemic-style — legitimate but not currently bookable.

## Approach

Add a weekly headless-browser probe that queries Google (search or maps) per venue and reads the knowledge-panel `business_status` signal:

- `OPERATIONAL` → no change
- `CLOSED_TEMPORARILY` → mark `_inactive=True`, show with badge
- `CLOSED_PERMANENTLY` → mark `_inactive=True` + `_removed_candidate=True`, surface in a "should we delete?" review strip
- `UNKNOWN` (Google returns nothing structured) → leave alone, don't guess

Playwright is already a project dep (used by `fetchers.py` for Instagram profiles), so no new runtime infrastructure.

## Open design questions (for brainstorming)

1. **Query target.** Google search knowledge panel vs. Google Maps direct URL vs. Google Places API. Headless-browser on search is free + flexible but fragile to UI changes. Places API is structured + stable but costs ~$0.017/call and requires a Google Cloud project.

2. **Cadence.** Weekly is likely overkill (venues don't close that fast). 30-day TTL per venue feels right for probe cost; 7-day TTL for verify-status file stays independent.

3. **Scope of probe.** Just `business_status`, or also pull hours/address to cross-check against `OYSTER_VENUES` metadata? The richer the probe, the more maintenance burden if Google changes the UI.

4. **False-positive protection.** Google occasionally shows "Permanently closed" for businesses that just rebranded. Do we need a human-in-the-loop step before deleting from OYSTER_VENUES, or is auto-flagging sufficient?

5. **Rate limiting.** Google can serve CAPTCHAs for automated traffic. 80 venues once per 30 days is ~3/day — trivial volume, but needs the right User-Agent + spacing.

6. **Interaction with discoveries log.** A venue in `oyster_discoveries.json` going closed should also be reflected in its verify_result so Phase 1's display states degrade gracefully.

## Rough shape (do not implement until brainstormed)

```
boston_finder/venue_status_probe.py       # new: check_venue_status(name, neighborhood) → dict
boston_finder/venue_status_cache.py       # or reuse existing cache module with new key
oyster_verify.py                           # hook: run probe per venue, fold into status record
boston_finder/html_output.py               # render "⛔ closed" badge / "should remove" strip
tests/test_venue_status_probe.py
```

## Not in this spec

- Auto-deletion from `OYSTER_VENUES` (manual-review only in Phase 2; automation in Phase 3 if needed).
- Cross-checking via Yelp / TripAdvisor (one source is enough).
- Backfilling historical status — probe runs going forward only.

## Next step

Run `superpowers:brainstorming` on this spec to harden the design choices (especially questions 1 and 4) before writing an implementation plan.
