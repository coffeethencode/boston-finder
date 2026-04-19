# Per-file merge decisions

For each file: strategy, what to preserve from stale, what to preserve from repo, any notes. This is the specification Phase 2 will execute.

**Source of truth on disk:**
- Stale: `/Users/brian/python-projects/boston_finder/`
- Repo: `/Users/brian/python-projects/boston-finder-repo/boston_finder/`
- Diffs captured: `tracking/diffs/*.diff` (at Phase 1)

**Overall observation:** Repo's April 12 "unify personas" commit (`0a57613`) made architectural progress (persona-aware pipeline, cleaner HTML rendering, proximity moved to personas module) but regressed multiple feature sets (Luma/Ticketmaster/Meetup/Instagram fetchers, efficiency/Netlify tracking, Providence venues, extracted-events cache). Merge strategy: **keep repo's newer architecture + restore stale's dropped features**.

---

## boston_finder/__init__.py
- **Strategy:** IDENTICAL
- **Action:** None. Skip to verification in Phase 2 template.

## boston_finder/ai_filter.py
- **Strategy:** MERGE-ADDITIVE
- **Preserve from stale:** `_normalize_name(name: str) -> str` helper, `_extract_raw_events(raw_pages: list[dict]) -> list[dict]` function (AI extraction for `_raw` scraped pages).
- **Preserve from repo:** `score()` (current signature `(events, prompt_role, min_score, persona) -> tuple[list, int, int]`), `deduplicate()`, `_keyword_fallback()`, `SPORTS_EXCLUDE`, `sports_filter()`, MODEL constant, prompt-cache-enabled API call.
- **Notes:** stale's score() signature is `(events, prompt) -> list` (no tuple). Do NOT regress repo's tuple. The `_extract_raw_events` flow may need integration into `score()` — check if it's called separately in stale oyster_deals.py.

## boston_finder/cache.py
- **Strategy:** MERGE-ADDITIVE
- **Preserve from stale:** `EXTRACTED_CACHE_FILE = ~/boston_finder_extracted.json`, `EXTRACTED_TTL_HOURS = 12`, `_load_extracted()`, `_save_extracted()`, `get_extracted(source_url)`, `save_extracted(source_url, events)`.
- **Preserve from repo:** current `get`/`set`/`age`/`_load`/`_save`/`get_scored`/`save_scored`/`prune_scored` — unchanged.
- **Notes:** Add stale's extracted-events cache immediately after the scored-events cache section. No conflict.

## boston_finder/costs.py
- **Strategy:** MERGE-ADDITIVE
- **Preserve from stale:** `_netlify_credits() -> str`, `netlify_credits_snapshot() -> dict`, `efficiency_check(events_cached, events_scored, cost_usd, recent_runs) -> dict`. Extended `log_run(start_ts, events_total, events_cached, events_scored, deploy_why="", persona="", source_counts=None)` signature including `by_stage` breakdown + `netlify` + `efficiency` fields in stored run entries.
- **Preserve from repo:** base `log_call()`, `get_stats()`, `get_recent_runs()`, `get_week_total()`, `get_month_total()`. Keep `_load()`, `_save()` for cost log.
- **Notes:** Callers of `log_run()` must pass new kwargs — but they're optional with defaults. Backward-compatible. Dashboard in html_output.py can be updated in Phase 2 Task 2.12 to display new fields, but is not required.

## boston_finder/fetchers.py
- **Strategy:** MERGE-ADDITIVE (largest merge)
- **Preserve from stale:** `fetch_luma()`, `fetch_allevents_category()`, `_keychain_get()`, `fetch_ticketmaster()`, `fetch_eventbrite_api()`, `fetch_meetup()`, `fetch_instagram()`, `fetch_microdata_url()`, `fetch_jsonld_url()` — entire functions. Plus any `fetch_source()` dispatcher updates that route to new types.
- **Preserve from repo:** `fetch_do617_category()` (has today's `strptime(%I:%M%p)` fix — must NOT regress), `fetch_eventbrite()`, `enrich_events()`, `fetch_scrape_url()`, `HEADERS`.
- **Notes:** Use stale as the base, port repo's do617 time-parse fix into stale's version. `fetch_source(source, start, end)` dispatcher likely exists in stale — verify it handles every `type:` value in `sources.py`.

## boston_finder/html_output.py
- **Strategy:** REPO-NEWER at Phase 2, MERGE-ADDITIVE at Phase 2b.
- **Preserve from repo:** persona-aware `_oyster_html(persona)` with JS rendering, `generate(events, today, days, persona)` pipeline, `_cost_html()`, `_extra_events_html()`, `_git_deploy(html, persona)`, `SAFE_TEST_ENV` / `DISABLE_OPEN_ENV` / `DISABLE_DEPLOY_ENV` / `OUTPUT_FILE_ENV` env flags, `_placeholder_hits()` deploy guard.
- **Phase 2b (2026-04-18, commit `4d3b052`, tag `unification-phase2b`) — DONE:**
  1. ✅ Ported `build_json(events, today, days, persona)` — JSON serialization of events. (`html_output.py:416-515`)
  2. ✅ Ported `_git_push_json(json_str, persona)` — pushes `data/<persona>.json` to separate `data` branch of `coffeethencode/boston-finder` (clone at `~/boston-finder-data/`). Avoids Netlify build credit burn on pure data updates. (`html_output.py:518-554`)
  3. ✅ Ported `_sources_html(events)` — source count pill bar. Rendered between `{_cost_html()}` and `{_oyster_html(persona)}` in the template (`html_output.py:614`).
  4. ✅ Added `DATA_REPO` + `PERSONA_PATHS` constants next to `GITHUB_REPO`. **Did NOT add `NETLIFY_URL`** — `boston_finder.personas.SITE_BASE` already holds the same value, so duplication was unnecessary.
  5. ✅ Wired `_git_push_json(build_json(...), persona)` into `generate()` right before `_git_deploy(...)`, gated by the existing `BOSTON_FINDER_DISABLE_DEPLOY` / SAFE_TEST / placeholder_hits early-return (`html_output.py:737-741`).
  6. ✅ Added `.sources-bar` + `.src-pill` + `.src-pill b` CSS after `.cost-model` in the main CSS block (`html_output.py:545-550`).
- **Verification:** import smoke, `build_json` unit test on fake events, `generate()` smoke with placeholder + real URLs, full `boston_events.py --persona brian --days 7` in Phase 5.2 (113 events, sources bar rendered, 0 "Date unknown", SAFE_TEST gating confirmed).
- **See** `tracking/code-review-context.md` §"Phase 2b" for rationale per decision and open questions for reviewer.

## boston_finder/location.py
- **Strategy:** MERGE-ADDITIVE (small)
- **Preserve from stale:** `"Providence": 2` and `"Rhode Island": 2` entries in `PROXIMITY` table.
- **Preserve from repo:** everything else. Specifically, keep repo's `location_filter()` using `get_proximity(persona)` from personas module — do NOT revert to inline CHLOE_PROXIMITY/KIRK_PROXIMITY tables.
- **Notes:** The CHLOE/KIRK tables that stale has inline MUST be migrated to personas.py (Task 2.13) via `get_proximity()`. Otherwise `location_filter()` will fail for non-default personas.

## boston_finder/notify.py
- **Strategy:** IDENTICAL
- **Action:** None.

## boston_finder/oyster_sources.py
- **Strategy:** MERGE-ADDITIVE
- **Preserve from stale:** 5 Providence venue entries in `OYSTER_VENUES` list: Providence Oyster Bar, Mill's Tavern, Pizzico Oyster Bar, Federal Taphouse, Hemenway's. Each has `city: "Providence"` field. Also preserve `"city": v.get("city", "Boston")` emission in the `get_all()` generator.
- **Preserve from repo:** all existing Boston/Cambridge venues.
- **Notes:** Trivial additive merge.

## boston_finder/personas.py
- **Strategy:** MERGE-SCHEMA (most complex single-file merge)
- **Preserve from repo:** entire new schema with `active`, `title`, `nav_label`, `accent`, `url_path`, `deploy_file`, `proximity`, `prompt`. Keep `PERSONAS` dict layout + helper functions (`get_persona`, `nav_html`, `active_personas`).
- **Additions required (Phase 2.8 — DONE at commit `f9e35b4`):**
  1. ✅ Added `oyster_prompt` (optional string) per persona. Text ported from stale.
  2. ✅ Added `min_score` (optional int, default 5) per persona.
  3. ❌ Did NOT add a `label` alias to `nav_label`. Instead, Phase 3.1 updated the one stale consumer (`oyster_deals.py`) to use `persona["nav_label"]` directly. Rationale: keeping one canonical label key is cleaner than carrying an alias indefinitely. See `tracking/code-review-context.md` §"Phase 3.1" for details.
  4. ✅ Added `get_proximity(name) -> dict | None` (`personas.py:290-295`). Per-persona proximity tables embedded as `proximity: dict | None` on each persona record (brian=None→default, chloe/kirk have custom dicts). Also added `get_oyster_prompt(name)` (`personas.py:284-287`) and `get_min_score(name, default=5)` (`personas.py:298-301`) helper functions — consumed by `oyster_deals.py` in Phase 3.1.
- **Notes:** `location.py` imports `get_proximity` from personas → Phase 2.8 was executed BEFORE Phase 2.9 (location.py). Plan order was updated at Phase 1 to reflect this; actual order on disk reflects the revised order.

## boston_finder/preferences.py
- **Strategy:** REPO-NEWER (deliberate policy change)
- **Preserve from repo:** all of it.
- **Notes:** Stale and repo differ in **policy language** about whether to skip ethnic-affinity networking events. Repo's newer language excludes them; stale's older language was more inclusive. This was a deliberate edit, not a regression. Keep repo. **Flag to user after Phase 5 integration test**: if the user wants stale's language back, that's a separate decision.

## boston_finder/ratings.py
- **Strategy:** IDENTICAL
- **Action:** None.

## boston_finder/sources.py
- **Strategy:** MERGE-ADDITIVE
- **Preserve from stale:** SOURCES list entries using fetcher types not in repo (`luma_search`, `allevents_category`, `ticketmaster`, `eventbrite_api`, `meetup`, `instagram`, `microdata_url`, `jsonld_url`). Each entry has `enabled: True/False` — keep stale's values.
- **Preserve from repo:** all existing entries (Eventbrite keyword searches, do617 categories, scrape_url entries).
- **Notes:** New source types only work AFTER fetchers.py Task 2.5 is merged. Source entries referencing unimplemented types will fail silently in `fetch_source()` dispatcher (should log a warning, not crash).

---

## Revised Phase 2 execution order

Original order had location.py (2.6) before personas.py (2.13). The `get_proximity()` dependency flips that. New order:

1. `__init__.py` (2.1) — IDENTICAL
2. `notify.py` (2.2) — IDENTICAL
3. `ratings.py` (2.3) — IDENTICAL
4. `costs.py` (2.4) — no internal deps
5. `preferences.py` (2.5) — no internal deps
6. `cache.py` (2.6) — no internal deps
7. `oyster_sources.py` (2.7) — no internal deps
8. **`personas.py` (2.8) — now MOVED EARLIER**, defines `get_proximity()` that location.py depends on
9. `location.py` (2.9) — depends on personas.get_proximity
10. `sources.py` (2.10) — registry, no code dep on fetchers
11. `ai_filter.py` (2.11) — depends on costs, preferences, cache
12. `fetchers.py` (2.12) — depends on cache; merges repo's do617 fix with stale's additional fetcher types
13. `html_output.py` (2.13) — depends on costs, cache, personas; small touch-up only
