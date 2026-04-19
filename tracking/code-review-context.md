# Code review context — Phases 2b through 5

**Purpose:** This doc is written FOR an AI reviewer to study the code and flag
bugs. It explains **what** each change does, **why** it was chosen, **how it
was verified**, and **what remains untested**. Pair this with `git log
--stat codebase-unification` and the diffs per commit.

**Reviewer, please focus on:**
1. Whether the WHY answers below actually match what the code does.
2. The untested code paths listed at the bottom of each section.
3. The "targeted questions for review" at the end.

**Repo:** `coffeethencode/boston-finder`
**Branch:** `codebase-unification` (tip `161a866`)
**Range to review:** `unification-phase2..unification-phase5` (6 code commits + 3 tracker commits)
**Previous plan docs:**
- `tracking/2026-04-18-codebase-unification.md` — original plan
- `tracking/merge-decisions.md` — per-file merge strategy (the spec this session implemented)
- `tracking/unification-status.md` — session log (WHAT was done)

---

## Phase 2b — JSON-push port into `boston_finder/html_output.py`

**Commit:** `4d3b052` — "Phase 2b: port stale JSON-push feature into repo html_output.py"
**Tag:** `unification-phase2b`

### Background

The old fork (`/Users/brian/python-projects/boston_finder/html_output.py`) had
three functions + four constants that let runs push a JSON payload of events
to a separate `data` branch of the same repo (cloned locally at
`~/boston-finder-data/`). That branch is NOT watched by Netlify, so pure data
updates burn 0 build credits. The repo's html_output.py (post the April 12
"unify personas" commit) dropped that logic. Phase 2b restores it.

### What was added

1. **Constants (near existing `GITHUB_REPO` line, `html_output.py:376-381`):**
   ```python
   DATA_REPO    = os.path.expanduser("~/boston-finder-data")  # clone of data branch
   PERSONA_PATHS = {
       "brian": "/",
       "chloe": "/chloe",
       "kirk":  "/kirk",
   }
   ```
   - **Why here, not at the top of the file?** The repo already kept
     `GITHUB_REPO` next to `_git_deploy()` instead of at the top; I followed
     that pattern so deploy-related constants stay co-located with deploy
     functions.
   - **Why keep `PERSONA_PATHS` even though `generate()` doesn't use it?**
     `merge-decisions.md` lists it as a required port, and it's cheap to keep
     for downstream consumers of the module. If a reviewer considers it dead
     code today they can flag it.
   - **Why NOT port stale's `NETLIFY_URL`?** Repo's `boston_finder/personas.py:263`
     already exports `SITE_BASE = "https://highendeventfinder.netlify.app"`
     (same value). Duplicating was strictly redundant.

2. **`build_json(events, today, days, persona)`** (`html_output.py:416-515`) —
   serializes the payload to JSON. Port matches stale's stale:132-235 almost
   verbatim; the only intentional diffs from stale:
   - Top-level `import os as _os` inside the hot-restaurants block was dropped;
     the file already `import os` at line 7.
   - Style-only whitespace in the final `payload` dict.
   - **Inline imports kept on purpose.** `from boston_finder.cache import get as _cache_get`,
     `from boston_finder.sources import SOURCES as _SOURCES`, and
     `from boston_finder.personas import get_persona as _gp` are imported INSIDE
     the function. Moving them to module-top would create circular imports
     because cache/personas import from html_output indirectly via shared
     modules. Keeping them inline matches stale's working pattern.

3. **`_git_push_json(json_str, persona)`** (`html_output.py:518-554`) —
   file-write + `git add` + `git commit` + `git push` loop against `DATA_REPO`.
   Port verbatim from stale:238-275. Notable behaviors a reviewer should
   double-check:
   - **Skips if `DATA_REPO` dir doesn't exist** (line 519-521). This is a
     defensive check because on a fresh machine the sibling clone won't be set
     up. Silent skip is deliberate.
   - **Skips if the new JSON is identical to what's on disk** (line 526-529).
     Prevents empty commits and redundant Netlify-unrelated pushes.
   - **`git pull --ff-only --quiet` with `check=False`** (line 534). Silent
     pull is intentional so a local no-op doesn't error when there's nothing
     to pull. **Potential issue for review:** if upstream has non-FF commits,
     the subsequent `git push` WILL fail; the outer `except Exception as ex`
     at line 552 will catch it and print "push failed: {ex}" but will NOT
     abort the HTML deploy that follows. That's the stale pattern; flag if
     you think it should abort instead.
   - **`check=True` on commit + push**, wrapped by the outer `except`, so any
     git error here is caught and printed, not raised. Intentional.

4. **`_sources_html(events)`** (`html_output.py:557-566`) — Counter over
   `e.get("source", "unknown").split(":")[0]`, renders a `<span class="src-pill">`
   per source. **XSS note for reviewer:** source names are baked into HTML
   without escaping. Source names today are all controlled by
   `boston_finder/sources.py` (not user input), so the risk is low. But if
   `sources.py` ever grows a user-configurable entry, this becomes XSS-able.

5. **CSS (`html_output.py:545-550`):** `.sources-bar`, `.src-pill`, `.src-pill b`
   styles added right after the `.cost-model` block in the main CSS block.
   - **Why that location?** Visual neighbor of `.cost-bar` — both are thin
     info bars in the header region. Keeps the CSS block organized by
     UI-section rather than by insert-time.

6. **Template insertion (`html_output.py:614`):** `{_sources_html(events)}`
   is rendered in the `<body>` between `{_cost_html()}` and `{_oyster_html(persona)}`.
   - **Why that position?** Matches stale's position in its template
     (stale:447-449). The reasoning: costs → sources → oyster form a visual
     "stats header" above the main day pills / event cards. The reviewer
     should confirm the ordering reads well on the live page.

7. **Generate wiring (`html_output.py:737-740`):**
   ```python
   if disable_deploy:
       print("  [deploy] skipped by test mode")
       return

   _git_push_json(build_json(events, today, days, persona), persona)
   _git_deploy(html, persona=persona)
   ```
   - **Why gate BOTH on `disable_deploy`?** JSON push and HTML deploy are
     both "production side effects" from the POV of tests. SAFE_TEST /
     DISABLE_DEPLOY should block both consistently.
   - **Why place the push BEFORE `_git_deploy`?** Data should be fresh when
     the static site is published, so if `_git_deploy` succeeds and Netlify
     builds, the data branch is already up-to-date and the site loads a
     consistent snapshot. Stale did it in the same order.
   - **Placeholder guard (`html_output.py:727-732`) covers both.** If
     `_placeholder_hits` is non-empty the function returns early, so the
     blocker applies to JSON push too, not just HTML deploy. Reviewer should
     confirm that's desired (I believe yes — don't push placeholder JSON).

### Verification (what I tested)

- **Import smoke:** `python3 -c "from boston_finder import html_output; print(html_output.DATA_REPO, html_output.PERSONA_PATHS, html_output.build_json, html_output._git_push_json, html_output._sources_html)"` — all symbols present.
- **`build_json()` unit test** with two fake events. Parsed the returned JSON; verified `persona`, `events[]`, `source_stats`, `sources`, `source_urls`, `hot_restaurants` keys present. Source splitting on `":"` confirmed (`"allevents:art"` → `"allevents"`).
- **`generate()` smoke with placeholder URLs** (`example.com/*`): placeholder guard fired, deploy + JSON push both correctly blocked via early return. Sources bar rendered in HTML.
- **`generate()` smoke with real-looking URLs + SAFE_TEST**: `[deploy] skipped by test mode` — disable_deploy gate correctly blocked both push and deploy. Sources bar rendered (2 src-pill spans for 2 fake events).
- **Phase 5.2 full pipeline run** (`boston_events.py --persona brian --days 7` under SAFE_TEST): 113 events rendered, sources bar showed real source counts (Boston Calendar 39, do617 31, HKS 10, IG 9, VENU 8, ...). `var oysters` JSON block populated with real data. Title = today. 0 "Date unknown".

### What was NOT tested (targeted questions for reviewer)

- **`_git_push_json` live push** — the full push path to `~/boston-finder-data` was never exercised. I deliberately avoided triggering a live commit+push. The data repo exists (`~/boston-finder-data/.git` present, `data/` dir present), so the "repo not found" short-circuit isn't triggered. Reviewer should trace: if SAFE_TEST is unset and placeholder_hits is empty, does `_git_push_json` behave correctly when the JSON is fresh vs. identical?
- **Non-fast-forward pull during `_git_push_json`** — untested. If the data branch has diverged, the `pull --ff-only --quiet` silently fails, then `git push` fails, then the outer try/except prints and returns, then `_git_deploy` still runs. Is that desired recovery behavior?
- **Concurrent runs** — if two runs overlap (unlikely since LaunchAgent runs sequentially), `_git_push_json`'s pull/push race could cause the second one to fail. Stale had the same property; not a regression.

---

## Phase 3.1 — Port `oyster_deals.py` (top-level script)

**Commit:** `8668419` — "Phase 3: promote stale oyster_deals.py into repo, adapted to unified personas schema"

### Background

Stale `/Users/brian/python-projects/oyster_deals.py` (204 lines, per-persona,
rich proximity sort + verify-status attach) was much richer than repo's
pre-session version (127 lines, single-persona, no proximity sort). The port
REPLACES repo's file with the stale version, adapted to the new unified
personas schema.

### What changed vs. stale's oyster_deals.py

1. **Path fix (`oyster_deals.py:13-19`):**
   ```python
   from pathlib import Path

   ROOT = Path(__file__).resolve().parent
   if str(ROOT) not in sys.path:
       sys.path.insert(0, str(ROOT))
   ```
   Replaces stale's hardcoded `sys.path.insert(0, "/Users/brian/python-projects")`.
   - **Why:** stale assumed a specific absolute path for the parent dir; the
     repo-relative form lets the script work from any clone of
     `boston-finder-repo` (e.g. CI runners or a fresh machine).

2. **Import additions (`oyster_deals.py:25-26`):**
   ```python
   from boston_finder.location       import score as proximity_score, label as proximity_label, location_filter, PROXIMITY
   from boston_finder.personas       import get_persona, PERSONAS, get_proximity, get_oyster_prompt, get_min_score
   ```
   - Added `PROXIMITY` (default proximity table) so `sort_by_proximity` can
     fall back to it when a persona has no custom proximity.
   - Added `get_proximity, get_oyster_prompt, get_min_score` — the Phase 2.8
     helpers now defined on the personas module.

3. **`sort_by_proximity` (`oyster_deals.py:51-64`) — proximity lookup refactor:**

   Stale:
   ```python
   from boston_finder.location import CHLOE_PROXIMITY, KIRK_PROXIMITY, PROXIMITY
   prox_table = CHLOE_PROXIMITY if persona == "chloe" else KIRK_PROXIMITY if persona == "kirk" else PROXIMITY
   ```
   Ported:
   ```python
   prox_table = get_proximity(persona) or PROXIMITY
   ```
   - **Why:** per `merge-decisions.md` §`location.py` and §`personas.py`, the
     CHLOE/KIRK tables moved out of `location.py` onto the persona records.
     `get_proximity(name)` (`personas.py:290`) returns the per-persona dict
     or `None`; the `or PROXIMITY` fallback picks up the default when no
     custom table is set.
   - **Review note:** `None or PROXIMITY` → `PROXIMITY`. An *empty* dict
     `{} or PROXIMITY` → also `PROXIMITY` (empty dicts are falsy). Today
     that's fine because no persona sets `proximity: {}` — they either set a
     real dict or leave it as `None`. If someone adds a persona with
     `proximity: {}` as a sentinel for "strict no-proximity-bonus", the
     fallback would silently skip it. Flagged for review.

4. **`run_persona` (`oyster_deals.py:118-123`) — schema helpers:**

   Stale:
   ```python
   label    = persona["label"]
   prompt   = persona.get("oyster_prompt", persona["prompt"])
   min_score = persona.get("min_score", 5)
   ```
   Ported:
   ```python
   label    = persona["nav_label"]
   prompt   = get_oyster_prompt(persona_name)
   min_score = get_min_score(persona_name)
   ```
   - **Why `nav_label`:** repo schema renamed `label` → `nav_label`. Every
     persona record has this key (`personas.py:16, 51, 106, 207`).
   - **Why the helpers vs. inline `persona.get(..., default)`:** the helpers
     (`personas.py:284, 298`) encapsulate the fallback logic (oyster_prompt
     falls back to `prompt`, min_score defaults to 5). Using helpers avoids
     duplicating that policy in every caller.
   - **Raw indexing `persona["nav_label"]` (not `.get`)** is a deliberate
     fail-fast: if a persona dict is missing `nav_label`, surface the
     KeyError at run_persona start rather than emit a label-less digest.
     Stale also used `persona["label"]` raw indexing.

5. **Behavior preserved (not re-ported, present in the stale-copy body):**
   - `CACHE_KEY_BASE = "oyster_deals"`, cache key per persona (e.g.
     `oyster_deals_brian`).
   - TTL 168h (7 days).
   - `load_verify_status()` reads `~/boston_finder_oyster_status.json` and
     attaches `verify_status`, `maps_url`, `_inactive` to each deal.
   - Sort key `(inactive, -prox, -score)` — active first, then closest
     proximity, then AI score. This is the stale behavior that the thinner
     repo version didn't have.
   - `costs.print_summary()` at end of `display()`.
   - `send(...)` at end of `run_persona` (notify desktop).

### Verification

- `PYTHONPATH=. python3 /tmp/oyster_deals_staged.py --help` before moving into repo — parses fine.
- `BOSTON_FINDER_SAFE_TEST=1 python3 oyster_deals.py --persona brian` (cached path): rendered 44 cached deals with proximity tiers ("nearby", "easy", "hike") — proves `sort_by_proximity` + `load_verify_status` ran.
- **Phase 5.1 force run** cleared `oyster_deals_*` keys, ran `--force`: 16 fresh deals cached with `_proximity`, `_proximity_label`, `verify_status` fields populated. This proves the schema-swap code (all 3: `nav_label`, `get_oyster_prompt`, `get_min_score`, `get_proximity`) executes on the hot path (they run before the cache check).

### What was NOT tested

- `--persona chloe` and `--persona kirk` — these two personas have custom
  `proximity` dicts (`personas.py:55-70, 110-146, 211-226`) so they exercise
  a different branch of `get_proximity(persona) or PROXIMITY`. I only ran
  `brian` (whose `proximity: None` hits the fallback). **Reviewer should
  confirm** that running chloe/kirk picks up their custom tables.
- `--persona all` — the default multi-persona loop. Each iteration calls
  `run_persona`, which uses cached data if present. Safe but untested this
  session.

---

## Phase 3.2 — Port `oyster_verify.py` + `oyster/venues.md`

**Commit:** `7bddc68` — "Phase 3: port oyster_verify.py and oyster/venues.md into repo"

### What changed vs. stale

Only adaptation: the `sys.path` block. No schema changes — this script only
imports `OYSTER_VENUES` and `location` primitives, both of which are stable
across the merge.

```python
# stale
sys.path.insert(0, "/Users/brian/python-projects")

# ported (oyster_verify.py:30-34)
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
```

`VENUES_MD = os.path.join(os.path.dirname(__file__), "oyster", "venues.md")`
(`oyster_verify.py:39`) is unchanged — it was always repo-root-relative via
`__file__`, so just moving the script into the repo made it resolve to
`boston-finder-repo/oyster/venues.md` automatically.

`oyster/venues.md` itself is a straight copy of stale's file.

### Verification

- `python3 oyster_verify.py --help` — parses.
- `python3 oyster_verify.py --venue "Row 34"`: script fetched Row 34's
  specials page (got HTTP 404, which is a real site issue, not my bug —
  the venue's page URL needs updating), wrote `~/boston_finder_oyster_status.json`
  with keys `status`, `verified_at`, `found_keywords`, `maps_url`, `notes`.
- Confirmed status file `row_34` entry has `status = "⚠️ Unverified"`,
  `maps_url = "https://maps.google.com/?q=Row%2034%20Fort%20Point%20Boston%20MA"`,
  `verified_at = "2026-04-18T23:13:07..."`.

### What was NOT tested

- **Full run** (no `--venue`) across all venues in `OYSTER_VENUES`. Would
  issue N HTTP requests (~20 venues). No functional reason to suspect
  failure but untested.
- **Writing to `oyster/venues.md`** — the script writes a human-readable
  registry with every venue's status. Only briefly confirmed the
  "→ Wrote ... venues.md" line appeared; did not diff the content against
  prior runs.

---

## Phase 3.3 — Port `oyster_triage.py`

**Commit:** `00f9218` — "Phase 3: port oyster_triage.py into repo"

### What changed vs. stale

Only the `sys.path` block, identical pattern to 3.1 and 3.2. No schema
changes — the script imports `cache.get`, `location.score`, `location.label`,
`ratings.score`, `ratings.is_skipped`, `ratings.summary`, `costs`. All of
those exist and are stable in the repo's `boston_finder/` package
(verified via grep).

### Verification

- `python3 oyster_triage.py --help` — parses.
- `python3 oyster_triage.py --rank` (repeat during Phase 5.4): printed the
  cached ranked list with proximity tier headers ("NEARBY / EASY") and a
  final personal-ratings summary from `ratings.summary()`. No traceback.

### What was NOT tested

- **Full research run** (without `--rank`): would call Claude API to
  research every venue — real AI spend + real web fetches. Skipped for
  cost reasons. Reviewer should trace that `research_venue()`
  (`oyster_triage.py:41+`) correctly handles the `ANTHROPIC_API_KEY=""`
  fallback (it returns a neutral default stub, confirmed by reading the
  code).

---

## Phase 4 — Wrapper verification

**No code changes.** Just verified `run_boston_events.sh` and
`run_oyster_deals.sh` already use `SCRIPT_DIR`-relative paths + are +x.

Grep confirmed **no LaunchAgent plist or user crontab references
`oyster_verify`**, so skipped creating a wrapper for it. If a reviewer adds
a cron for oyster_verify later, they'll need to add `run_oyster_verify.sh`.

Tag: `unification-phase4`.

---

## Phase 5 — Integration tests

**No code changes.** Ran the 4 end-to-end checks (oyster_deals --force,
boston_events full, oyster_verify single-venue, oyster_triage --rank) under
SAFE_TEST / DISABLE_DEPLOY. All passed. See `tracking/unification-status.md`
Phase 5 row for exact output markers.

Tag: `unification-phase5`.

---

## Targeted questions for the reviewer

If the reviewer is spending 10-15 minutes, focus here:

1. **`_git_push_json` failure semantics** (`html_output.py:533-554`): if the
   push fails (non-FF, auth issue), we silently log and continue to
   `_git_deploy`. Should we abort the HTML deploy when the JSON push fails,
   so the live site never shows mismatched data? Stale's pattern was to
   continue; merge-decisions didn't specify; this is the inherited behavior
   but is worth re-examining now.

2. **`get_proximity(persona) or PROXIMITY` edge case** (`oyster_deals.py:55`
   and `location.py` call sites): `None or PROXIMITY` and `{} or PROXIMITY`
   both fall back. If a persona is intentionally set to `proximity: {}` as
   "no custom boundaries, don't apply any bonus", the code treats that as
   "use default". Is that correct? Or should we use
   `get_proximity(persona) if get_proximity(persona) is not None else PROXIMITY`?

3. **`_sources_html` XSS risk** (`html_output.py:557-566`): source names go
   into HTML unescaped. Safe today because all sources are defined in
   `boston_finder/sources.py`, but if config-driven sources are added later
   (user-supplied strings), this becomes a vector. Flag or add html.escape()?

4. **Inline imports inside `build_json`** (`html_output.py:420-423`, `440`,
   `468`): every sub-block wraps imports + logic in a `try/except Exception:`
   that silently falls back to empty defaults. If a downstream module moves
   or renames (e.g. `cache._load_scored` becomes `cache.load_scored`), the
   JSON payload silently drops `extra_events` instead of raising. Is the
   robustness worth the silent-failure risk?

5. **`persona["nav_label"]` raw indexing** in `oyster_deals.py:119`,
   `html_output.py:404, 484`, and `personas.py:319, 330`: fails hard with
   KeyError if a persona is missing `nav_label`. Today every persona has
   the key; this is defensible fail-fast. Reviewer should confirm they're
   OK with that stance across the codebase.

6. **CSS placement** (`html_output.py:545-550`): `.sources-bar` +
   `.src-pill` styles live between `.cost-model` and `.footer`. Visually
   renders fine in Phase 5.2 output. Reviewer may want to check
   `/tmp/unification_test.html` in a browser to confirm the sources bar
   sits visually where it should (between cost bar and oyster bar).

7. **Commit order of Phase 2b within `generate()`** (`html_output.py:737-741`):
   `_git_push_json(...)` runs BEFORE `_git_deploy(...)`. That means a
   successful JSON push + failed HTML deploy leaves the data branch
   ahead of the live site for ~1 build cycle until the next run catches
   up. Desired or should it be reversed?

---

## Files changed this session (quick index)

| File | Phase | Change type | LOC delta |
|---|---|---|---|
| `boston_finder/html_output.py` | 2b | MERGE-ADDITIVE | +167 |
| `oyster_deals.py` | 3.1 | REPLACE (stale → repo, adapted) | +138 / -58 |
| `oyster_verify.py` | 3.2 | NEW (copy + path fix) | +317 |
| `oyster/venues.md` | 3.2 | NEW (straight copy) | +31 |
| `oyster_triage.py` | 3.3 | NEW (copy + path fix) | +227 |
| `tracking/unification-status.md` | all | tracker appends | +5 rows |
| `tracking/code-review-context.md` | review | NEW (this doc) | — |

Tags: `unification-phase2b`, `unification-phase3`, `unification-phase4`, `unification-phase5`.
