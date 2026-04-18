# Boston Finder Codebase Unification Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate the forked `/Users/brian/python-projects/boston_finder/` package (and its stale top-level scripts) by merging every feature back into `/Users/brian/python-projects/boston-finder-repo/`, making the repo the sole source of truth for events + oyster pipelines.

**Architecture:** Work on a dedicated `codebase-unification` branch. Tag a pre-work backup point. Merge bottom-up (leaf modules first → dependents last → top-level scripts) so each commit is testable in isolation. Each phase ends with a git tag so any phase can be rolled back independently. LaunchAgents keep running the stale copy until Phase 6 (merge to main + rewire). Stale files go to `/Users/brian/python-projects/_deprecated_boston_finder/` for one week before hard-delete (Phase 7).

**Tech Stack:** Python 3 (no test framework in place — verification is "run the script and inspect output"), bash wrapper scripts, macOS LaunchAgents, git on `coffeethencode/boston-finder`, Netlify auto-deploy from `docs/index.html`.

**Working directory:** `/Users/brian/python-projects/boston-finder-repo/`

---

## Session Resume Protocol

**At the start of every session:**

1. Open this plan file. Find the first unchecked `- [ ]` — that's where we resume.
2. Verify current branch: `git -C /Users/brian/python-projects/boston-finder-repo branch --show-current` should print `codebase-unification` (Phases 1-5) or `main` (Phases 6-7).
3. Verify clean tree: `git status` should be clean unless the previous session ended mid-task (note in progress log below).
4. Run the tail of the progress log (bottom of this file) to see where the last session stopped.

**At the end of every session:**

1. Commit any in-progress work with a WIP message, or stash if truly partial.
2. Append a one-line entry to the progress log at the bottom: date, last task completed, branch state, any gotchas for next session.
3. Push the branch: `git push -u origin codebase-unification` (first time) or `git push` (subsequent).

**If a phase goes wrong:**

- `git reset --hard <phase-tag>` restores to the start of that phase. Tags are created at the end of each phase.
- LaunchAgent is unaffected during Phases 1-5 (it runs the stale copy). Only Phase 6 changes the wrappers.

---

## Divergence Inventory (from 2026-04-18 analysis)

**Stale package:** `/Users/brian/python-projects/boston_finder/` (13 files)
**Repo package:** `/Users/brian/python-projects/boston-finder-repo/boston_finder/` (13 files)
**All 11 `.py` files in the package differ.** `__init__.py` and `__pycache__/` same or trivial.

**Stale-only top-level scripts:**
- `/Users/brian/python-projects/oyster_deals.py` (204 lines — richer than repo's 127-line version)
- `/Users/brian/python-projects/oyster_verify.py` (313 lines — writes `~/boston_finder_oyster_status.json`)
- `/Users/brian/python-projects/oyster_triage.py` (227 lines — reads cache + ratings, weighted ranking)

**Stale-only assets:**
- `/Users/brian/python-projects/oyster/venues.md` (human-readable venue registry, written by `oyster_verify.py`)

**LaunchAgents pointing at stale:**
- `~/Library/LaunchAgents/com.brian.bostonevents.plist` → `~/python-projects/run_boston_events.sh` (already fixed: delegates to repo wrapper)
- `~/Library/LaunchAgents/com.brian.oysterdeals.plist` → `~/python-projects/run_oyster_deals.sh` (currently runs STALE `oyster_deals.py`; Phase 4 rewires)

**Cache files (shared — both packages read/write the same paths):**
- `~/boston_finder_cache.json` — key-value store (events, oyster deals per persona)
- `~/boston_finder_scored.json` — URL score cache
- `~/boston_finder_costs.json` — per-call API cost log
- `~/boston_finder_runs.json` — per-run summary log
- `~/boston_finder_extracted.json` — (stale-only feature) AI-extracted events per scrape URL
- `~/boston_finder_oyster_status.json` — (written by stale oyster_verify) venue verify status + maps URLs

**Known schema incompatibilities (key blocker):**
- Stale `personas.py` has: `label`, `min_score`, `oyster_prompt`, `prompt`.
- Repo `personas.py` has: `active`, `title`, `nav_label`, `accent`, `url_path`, `deploy_file`, `proximity`, `prompt`.
- Stale `oyster_deals.py` references `persona["label"]`, `persona.get("oyster_prompt", persona["prompt"])`, `persona.get("min_score", 5)` — none exist in repo schema.
- **Reconciliation decision:** extend repo schema with `oyster_prompt` (optional), `min_score` (optional, default 5); treat `nav_label` as the canonical label (rename in stale oyster code when porting).

---

## File Structure

**Files to be created in repo:**
- `oyster_verify.py` (port from stale)
- `oyster_triage.py` (port from stale)
- `oyster/venues.md` (copy from stale)
- `run_oyster_verify.sh` (optional wrapper)
- `tracking/unification-status.md` (progress tracker — append-only log)

**Files to be modified in repo:**
- `boston_finder/__init__.py` (reconcile metadata/version if any)
- `boston_finder/costs.py` (merge stale improvements)
- `boston_finder/preferences.py` (merge)
- `boston_finder/notify.py` (merge)
- `boston_finder/cache.py` (add `get_extracted` / `save_extracted`)
- `boston_finder/location.py` (add Providence / Rhode Island entries)
- `boston_finder/oyster_sources.py` (add Providence venues + any missing stale venues)
- `boston_finder/ratings.py` (merge stale improvements; depended on by `oyster_triage.py`)
- `boston_finder/sources.py` (merge)
- `boston_finder/ai_filter.py` (merge)
- `boston_finder/fetchers.py` (already mostly up-to-date — spot-check for stale improvements)
- `boston_finder/html_output.py` (already mostly up-to-date from 2026-04-18 session — spot-check)
- `boston_finder/personas.py` (add `oyster_prompt` + `min_score` fields per persona)
- `oyster_deals.py` (replace 127-line version with stale's 204-line logic, adapted to new personas schema)
- `run_oyster_deals.sh` (already updated locally; ensure committed)
- `/Users/brian/python-projects/run_oyster_deals.sh` (already updated locally — delegates to repo wrapper)

**Files to be moved (Phase 7):**
- `/Users/brian/python-projects/boston_finder/` → `/Users/brian/python-projects/_deprecated_boston_finder/package/`
- `/Users/brian/python-projects/oyster_deals.py` → `/Users/brian/python-projects/_deprecated_boston_finder/oyster_deals.py`
- `/Users/brian/python-projects/oyster_verify.py` → `/Users/brian/python-projects/_deprecated_boston_finder/oyster_verify.py`
- `/Users/brian/python-projects/oyster_triage.py` → `/Users/brian/python-projects/_deprecated_boston_finder/oyster_triage.py`
- `/Users/brian/python-projects/boston_events.py` → `/Users/brian/python-projects/_deprecated_boston_finder/boston_events.py` (confirmed stale-only sibling — verify no unique features first)

---

# PHASE 0: Safety net & branch setup

**Phase tag at end:** `unification-phase0`

### Task 0.1: Create backup + unification branch

**Files:** git only (no code changes)

- [ ] **Step 1: Verify current branch is `main` and clean**

Run:
```bash
cd /Users/brian/python-projects/boston-finder-repo
git status
git branch --show-current
```
Expected: branch is `main`, no uncommitted changes (my earlier session's `oyster_deals.py` / `run_oyster_deals.sh` edits are **expected** — they go onto the new branch, see Step 3).

- [ ] **Step 2: Tag current main as backup**

Run:
```bash
git tag pre-unification-backup
git push origin pre-unification-backup
```
Expected: tag pushed, visible in `git tag --list`.

- [ ] **Step 3: Create and switch to unification branch, stash-apply in-progress edits**

Run:
```bash
git checkout -b codebase-unification
git status
```
Expected: on branch `codebase-unification`. If `oyster_deals.py` and `run_oyster_deals.sh` show as modified, commit them now:
```bash
git add oyster_deals.py run_oyster_deals.sh
git commit -m "WIP: start of unification — partial oyster_deals.py path fix and repo wrapper"
```

- [ ] **Step 4: Push branch**

Run:
```bash
git push -u origin codebase-unification
```

### Task 0.2: Create progress tracker

**Files:**
- Create: `tracking/unification-status.md`

- [ ] **Step 1: Create the tracker**

Write exactly this content to `tracking/unification-status.md`:

```markdown
# Unification progress log

Append one line per session end. Newest at bottom.

## Phases

- [ ] Phase 0 — Safety net & branch setup
- [ ] Phase 1 — Full diff & decision matrix
- [ ] Phase 2 — Merge package files bottom-up
- [ ] Phase 3 — Port top-level scripts
- [ ] Phase 4 — Rewire LaunchAgent wrappers
- [ ] Phase 5 — Integration tests
- [ ] Phase 6 — Merge to main + production deploy
- [ ] Phase 7 — Deprecate & hard-delete stale

## Session log

(none yet)
```

- [ ] **Step 2: Commit tracker**

```bash
git add tracking/unification-status.md
git commit -m "Add unification progress tracker"
```

### Task 0.3: Tag phase 0 complete

- [ ] **Step 1: Tag and push**

```bash
git tag unification-phase0
git push origin unification-phase0
```

- [ ] **Step 2: Mark Phase 0 complete in tracker**

Edit `tracking/unification-status.md`:
```
- [x] Phase 0 — Safety net & branch setup
```
Commit:
```bash
git commit -am "Phase 0 complete"
```

---

# PHASE 1: Full diff & decision matrix

**Goal:** For each diverged file, produce a concrete merge decision written into `tracking/merge-decisions.md`. This is the specification Phase 2 will implement.

**Phase tag at end:** `unification-phase1`

### Task 1.1: Generate diff report

**Files:**
- Create: `tracking/diffs/` (directory)
- Create: `tracking/diffs/<filename>.diff` per file

- [ ] **Step 1: Create diff directory**

```bash
mkdir -p tracking/diffs
```

- [ ] **Step 2: Dump every diff**

Run (from repo root):
```bash
STALE=/Users/brian/python-projects/boston_finder
REPO=boston_finder
for f in __init__.py ai_filter.py cache.py costs.py fetchers.py html_output.py location.py notify.py oyster_sources.py personas.py preferences.py ratings.py sources.py; do
  diff -u "$STALE/$f" "$REPO/$f" > "tracking/diffs/$f.diff" || true
  echo "$f: $(wc -l < tracking/diffs/$f.diff) lines of diff"
done
```

Expected: 13 `.diff` files created. Each ≥0 lines (0 = files identical). Typical file = 10-100 lines.

- [ ] **Step 3: Dump stale-only top-level scripts for reference**

```bash
cp /Users/brian/python-projects/oyster_deals.py     tracking/diffs/_stale_oyster_deals.py.txt
cp /Users/brian/python-projects/oyster_verify.py    tracking/diffs/_stale_oyster_verify.py.txt
cp /Users/brian/python-projects/oyster_triage.py    tracking/diffs/_stale_oyster_triage.py.txt
cp /Users/brian/python-projects/oyster/venues.md    tracking/diffs/_stale_venues.md.txt
```

- [ ] **Step 4: Commit**

```bash
git add tracking/diffs/
git commit -m "Phase 1: snapshot stale-vs-repo diffs for merge planning"
```

### Task 1.2: Write merge decision doc

**Files:**
- Create: `tracking/merge-decisions.md`

- [ ] **Step 1: Read each diff in `tracking/diffs/` and decide strategy per file**

For each `*.diff`, classify into one of:
- **IDENTICAL** — no changes, skip
- **STALE-NEWER-TRIVIAL** — copy stale over repo verbatim
- **REPO-NEWER-TRIVIAL** — keep repo as-is, discard stale
- **MERGE-ADDITIVE** — cherry-pick stale additions into repo (both have kept forward progress)
- **MERGE-SCHEMA** — reconcile incompatible schemas (currently only `personas.py`)

- [ ] **Step 2: Write the decision doc**

Write exactly this template to `tracking/merge-decisions.md`, filled in from the diffs:

```markdown
# Per-file merge decisions

For each file: strategy, what to preserve from stale, what to preserve from repo, any notes.

## boston_finder/__init__.py
- Strategy: <IDENTICAL | STALE-NEWER | REPO-NEWER | MERGE-ADDITIVE>
- Notes:

## boston_finder/ai_filter.py
- Strategy:
- Notes:

## boston_finder/cache.py
- Strategy: MERGE-ADDITIVE
- Preserve from stale: `get_extracted`, `save_extracted`, `EXTRACTED_CACHE_FILE`, `EXTRACTED_TTL_HOURS`
- Preserve from repo: current `get`/`set`/`age`/`_load`/`_save`/`get_scored`/`save_scored`/`prune_scored`
- Notes: stale's extra functions are additive; no conflict.

## boston_finder/costs.py
- Strategy:
- Notes:

## boston_finder/fetchers.py
- Strategy: REPO-NEWER-TRIVIAL (plus spot-check)
- Notes: repo got today's do617 time-parse fix. Verify stale has no later improvements.

## boston_finder/html_output.py
- Strategy: REPO-NEWER-TRIVIAL (plus spot-check)
- Notes: repo has persona-aware `_oyster_html()` from 2026-04-18 session. Verify stale has no unique rendering features.

## boston_finder/location.py
- Strategy: MERGE-ADDITIVE
- Preserve from stale: Providence and Rhode Island entries in PROXIMITY table.
- Preserve from repo: all existing entries + any new tables (CHLOE_PROXIMITY, KIRK_PROXIMITY).
- Notes:

## boston_finder/notify.py
- Strategy:
- Notes:

## boston_finder/oyster_sources.py
- Strategy: MERGE-ADDITIVE
- Preserve from stale: Providence venues entries.
- Preserve from repo: all existing Boston/Cambridge venues.
- Notes:

## boston_finder/personas.py
- Strategy: MERGE-SCHEMA
- Plan: keep repo schema, ADD `oyster_prompt` (optional string) and `min_score` (optional int, default 5) per persona. Port stale's hand-tuned oyster_prompt text per persona. Stale's `label` maps to repo's `nav_label` (rename at consumers, not here).
- Notes: `oyster_deals.py` (stale) needs these added fields. Adapt oyster_deals.py during Phase 3 to use `nav_label` in place of `label`.

## boston_finder/preferences.py
- Strategy:
- Notes:

## boston_finder/ratings.py
- Strategy:
- Notes: consumed by `oyster_triage.py` — review what functions that script imports.

## boston_finder/sources.py
- Strategy:
- Notes:
```

Fill in each `Strategy:` and `Notes:` line based on actually reading the diff. **Do not leave blanks.** If a diff is empty, mark IDENTICAL.

- [ ] **Step 3: Commit**

```bash
git add tracking/merge-decisions.md
git commit -m "Phase 1: per-file merge decision matrix"
```

### Task 1.3: Tag phase 1 complete

- [ ] **Step 1: Tag, push, mark tracker**

```bash
git tag unification-phase1
git push origin unification-phase1
git push
```
Then update `tracking/unification-status.md`: `- [x] Phase 1 — Full diff & decision matrix`, append a session log line, commit.

---

# PHASE 2: Merge package files bottom-up

**Goal:** Each leaf module reaches its merged target state. After this phase, every file in `boston_finder/` is the union of stale + repo features.

**Phase tag at end:** `unification-phase2`

**Order (bottom-up dependency — merge each file and commit individually):**

1. `__init__.py` (no dependents to break)
2. `costs.py` (no internal deps)
3. `preferences.py` (no internal deps)
4. `notify.py` (no internal deps)
5. `ratings.py` (no internal deps)
6. `location.py` (no internal deps)
7. `oyster_sources.py` (no internal deps)
8. `cache.py` (no internal deps)
9. `sources.py` (imports from nothing)
10. `ai_filter.py` (imports `costs`, `preferences`, `cache`)
11. `fetchers.py` (imports `cache`) — already current; spot-check only
12. `html_output.py` (imports `costs`, `cache`, `personas`) — already current; spot-check only
13. `personas.py` (imports `location`) — schema extension last, after consumers are stable

### Task 2.1 through 2.13: One task per file

**The pattern for every file task is identical. For task 2.N working on file `boston_finder/<F>.py`:**

- [ ] **Step 1: Re-read merge decision**

Open `tracking/merge-decisions.md`, find the entry for `boston_finder/<F>.py`, reconfirm the strategy.

- [ ] **Step 2: If strategy is IDENTICAL — skip to Step 6**
- [ ] **Step 3: If strategy is STALE-NEWER-TRIVIAL:**

```bash
cp /Users/brian/python-projects/boston_finder/<F>.py boston_finder/<F>.py
```

- [ ] **Step 4: If strategy is REPO-NEWER-TRIVIAL — do nothing to the file** (but still finish the verification steps below to confirm)
- [ ] **Step 5: If strategy is MERGE-ADDITIVE or MERGE-SCHEMA — hand-edit:**

Open both files side-by-side (e.g., `code --diff stale/<F>.py repo/<F>.py` or just Read both). For each section in the decision doc's "Preserve from stale" bullet, Edit the repo file to include that section. Follow the decision doc verbatim — it was the spec.

- [ ] **Step 6: Verify module imports cleanly**

Run:
```bash
cd /Users/brian/python-projects/boston-finder-repo
python3 -c "from boston_finder import <F>; print(<F>.__file__)"
```
Expected: prints path inside `boston-finder-repo/boston_finder/`, no import errors.

- [ ] **Step 7: Verify any new public symbol is importable**

For each symbol added from stale (e.g. `get_extracted` in `cache.py`), run:
```bash
python3 -c "from boston_finder.<F> import <symbol>; print(<symbol>)"
```

- [ ] **Step 8: Commit**

```bash
git add boston_finder/<F>.py
git commit -m "Phase 2: unify boston_finder/<F>.py (<strategy>)"
```

**Task-by-task applications:**

- [ ] **Task 2.1** — `__init__.py`
- [ ] **Task 2.2** — `costs.py`
- [ ] **Task 2.3** — `preferences.py`
- [ ] **Task 2.4** — `notify.py`
- [ ] **Task 2.5** — `ratings.py`
- [ ] **Task 2.6** — `location.py`
- [ ] **Task 2.7** — `oyster_sources.py`
- [ ] **Task 2.8** — `cache.py` (MERGE-ADDITIVE: bring in `get_extracted`, `save_extracted`, `EXTRACTED_CACHE_FILE`, `EXTRACTED_TTL_HOURS`)
- [ ] **Task 2.9** — `sources.py`
- [ ] **Task 2.10** — `ai_filter.py`
- [ ] **Task 2.11** — `fetchers.py` (REPO-NEWER; spot-check only)
- [ ] **Task 2.12** — `html_output.py` (REPO-NEWER; spot-check only)

### Task 2.13: personas.py schema extension (MERGE-SCHEMA)

This is the biggest merge task — breaking it out:

**Files:**
- Modify: `boston_finder/personas.py`

- [ ] **Step 1: Read current repo `personas.py`**

Open and note exact structure of the `PERSONAS` dict.

- [ ] **Step 2: Read stale `personas.py` — extract per-persona oyster_prompt strings**

From `/Users/brian/python-projects/boston_finder/personas.py`, copy each persona's `oyster_prompt` string (brian, chloe, kirk, dates if present) into a local clipboard/scratch area.

- [ ] **Step 3: For each persona in repo `PERSONAS`, add two new keys:**

```python
"oyster_prompt": """<paste stale's oyster_prompt text here for this persona>""",
"min_score": 5,
```

If a persona in repo isn't in stale (or vice versa), use `persona["prompt"]` as the `oyster_prompt` fallback and `5` for `min_score`.

- [ ] **Step 4: Verify import and schema**

Run:
```bash
python3 -c "
from boston_finder.personas import PERSONAS
for k, v in PERSONAS.items():
    assert 'oyster_prompt' in v, f'{k} missing oyster_prompt'
    assert 'min_score' in v, f'{k} missing min_score'
    print(k, '->', v.get('min_score'), len(v.get('oyster_prompt', '')), 'chars oyster_prompt')
"
```
Expected: each persona prints a min_score and non-zero oyster_prompt length.

- [ ] **Step 5: Verify events pipeline still works (smoke test only — no deploy)**

```bash
BOSTON_FINDER_SAFE_TEST=1 python3 boston_events.py --persona brian --days 3 2>&1 | tail -10
```
Expected: no tracebacks. May print "no events" depending on sources — that's fine.

- [ ] **Step 6: Commit**

```bash
git add boston_finder/personas.py
git commit -m "Phase 2: extend personas schema with oyster_prompt and min_score"
```

### Task 2.14: Tag phase 2 complete

- [ ] **Step 1: Tag, push, update tracker**

```bash
git tag unification-phase2
git push origin unification-phase2
git push
```
Update `tracking/unification-status.md`, commit.

---

# PHASE 3: Port top-level scripts

**Goal:** `oyster_deals.py`, `oyster_verify.py`, `oyster_triage.py` live in the repo, work against the repo's `boston_finder/` package, and use the new merged personas schema.

**Phase tag at end:** `unification-phase3`

### Task 3.1: Replace repo `oyster_deals.py` with stale version, adapted

**Files:**
- Modify: `oyster_deals.py` (repo)

- [ ] **Step 1: Copy stale to a staging location**

```bash
cp /Users/brian/python-projects/oyster_deals.py /tmp/oyster_deals_staged.py
```

- [ ] **Step 2: Replace the `sys.path.insert` block with repo-relative import**

In `/tmp/oyster_deals_staged.py`, replace:
```python
sys.path.insert(0, "/Users/brian/python-projects")
```
with:
```python
from pathlib import Path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
```

- [ ] **Step 3: Replace `persona["label"]` references with `persona["nav_label"]`**

Grep for `persona["label"]` and `persona.get("label"...)` in the staged file. Replace with `persona["nav_label"]` / `persona.get("nav_label", ...)`.

- [ ] **Step 4: Verify the staged file imports**

```bash
cd /Users/brian/python-projects/boston-finder-repo
PYTHONPATH=. python3 /tmp/oyster_deals_staged.py --help
```
Expected: argparse help message, no tracebacks.

- [ ] **Step 5: Move staged into repo**

```bash
mv /tmp/oyster_deals_staged.py oyster_deals.py
```

- [ ] **Step 6: Safe-test run (cache-only, no AI spend)**

```bash
BOSTON_FINDER_SAFE_TEST=1 python3 oyster_deals.py --persona brian 2>&1 | tail -20
```
Expected: prints oyster deals using cached data from `oyster_deals_brian` (44 items as of April 13). No AI calls (cached). No deploy.

- [ ] **Step 7: Commit**

```bash
git add oyster_deals.py
git commit -m "Phase 3: promote stale oyster_deals.py into repo, adapted to unified personas schema"
```

### Task 3.2: Port `oyster_verify.py`

**Files:**
- Create: `oyster_verify.py` (repo)
- Create: `oyster/venues.md` (repo)

- [ ] **Step 1: Copy venues.md**

```bash
mkdir -p oyster
cp /Users/brian/python-projects/oyster/venues.md oyster/venues.md
```

- [ ] **Step 2: Copy and adapt `oyster_verify.py`**

```bash
cp /Users/brian/python-projects/oyster_verify.py oyster_verify.py
```

Then edit `oyster_verify.py`:
- Replace `sys.path.insert(0, "/Users/brian/python-projects")` with:
  ```python
  from pathlib import Path
  ROOT = Path(__file__).resolve().parent
  if str(ROOT) not in sys.path:
      sys.path.insert(0, str(ROOT))
  ```
- Update `VENUES_MD = os.path.join(os.path.dirname(__file__), "oyster", "venues.md")` — this should still work since `__file__` is now the repo script.

- [ ] **Step 3: Verify imports + help**

```bash
python3 oyster_verify.py --help
```
Expected: argparse help.

- [ ] **Step 4: Single-venue smoke test**

```bash
python3 oyster_verify.py --venue "Row 34" 2>&1 | tail -30
```
Expected: fetches Row 34's page, prints verify result (status + maps URL). Writes to `~/boston_finder_oyster_status.json` — **confirm that file was updated**:
```bash
python3 -c "
import json, os
with open(os.path.expanduser('~/boston_finder_oyster_status.json')) as f: s = json.load(f)
print(list(s.keys())[:5])
print('row_34 entry:', s.get('row_34'))
"
```

- [ ] **Step 5: Commit**

```bash
git add oyster_verify.py oyster/venues.md
git commit -m "Phase 3: port oyster_verify.py and oyster/venues.md into repo"
```

### Task 3.3: Port `oyster_triage.py`

**Files:**
- Create: `oyster_triage.py` (repo)

- [ ] **Step 1: Copy and adapt**

```bash
cp /Users/brian/python-projects/oyster_triage.py oyster_triage.py
```

Edit to replace `sys.path.insert` block as in Task 3.2.

- [ ] **Step 2: Verify imports**

```bash
python3 oyster_triage.py --help
```
Expected: argparse help.

- [ ] **Step 3: Rank-only smoke test (uses cached data, no network)**

```bash
python3 oyster_triage.py --rank 2>&1 | tail -20
```
Expected: prints ranked list from `~/oyster_triage.json` if it exists, or says "no cached data, run without --rank first". Either way no traceback.

- [ ] **Step 4: Commit**

```bash
git add oyster_triage.py
git commit -m "Phase 3: port oyster_triage.py into repo"
```

### Task 3.4: Tag phase 3 complete

- [ ] **Step 1: Tag, push, update tracker**

```bash
git tag unification-phase3
git push origin unification-phase3
git push
```
Update `tracking/unification-status.md`, commit.

---

# PHASE 4: Rewire LaunchAgent wrappers

**Goal:** Live wrappers (`/Users/brian/python-projects/run_*.sh`) delegate to repo wrappers. After Phase 4 + Phase 6 merge, next scheduled runs use only repo code.

**Phase tag at end:** `unification-phase4`

**Note:** work on this branch first (tracks wrapper changes in git). The live wrappers (outside repo) are updated in Phase 6 alongside the merge so the LaunchAgent stays on the stale copy during testing.

### Task 4.1: Verify repo wrappers

- [ ] **Step 1: Ensure `run_boston_events.sh` is correct (should already be)**

```bash
cat run_boston_events.sh
```
Expected: script `cd`s to `$SCRIPT_DIR`, runs repo's `boston_events.py`.

- [ ] **Step 2: Ensure `run_oyster_deals.sh` is correct (from my earlier edits)**

```bash
cat run_oyster_deals.sh
```
Expected: same shape as `run_boston_events.sh`, runs repo's `oyster_deals.py`.

- [ ] **Step 3: chmod +x if needed**

```bash
chmod +x run_boston_events.sh run_oyster_deals.sh
```

### Task 4.2: Create optional wrapper for `oyster_verify.py`

**Decision point:** Is oyster_verify run on a schedule or ad-hoc only?
- Search for existing references: `grep -r oyster_verify ~/Library/LaunchAgents/ /etc/crontab 2>/dev/null`
- If no cron, skip this task.
- If cron, create `run_oyster_verify.sh` mirroring the other two.

- [ ] **Step 1: Check for cron reference**

```bash
grep -r oyster_verify ~/Library/LaunchAgents/ /etc/crontab 2>/dev/null || echo "no scheduled wrapper needed"
```

- [ ] **Step 2: If scheduled — create wrapper**

Create `run_oyster_verify.sh`:
```bash
#!/bin/bash
source ~/.zshrc 2>/dev/null || true
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="/Users/brian/python-projects/myenv/bin/python3"
if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="$(command -v python3)"
fi
cd "$SCRIPT_DIR"
exec "$PYTHON_BIN" "$SCRIPT_DIR/oyster_verify.py" "$@"
```
```bash
chmod +x run_oyster_verify.sh
```

- [ ] **Step 3: Commit (whether or not the wrapper was created)**

If no wrapper, no commit needed. If wrapper created:
```bash
git add run_oyster_verify.sh
git commit -m "Phase 4: add oyster_verify wrapper"
```

### Task 4.3: Tag phase 4 complete

- [ ] **Step 1: Tag, push, update tracker**

```bash
git tag unification-phase4
git push origin unification-phase4
git push
```

---

# PHASE 5: Integration tests

**Goal:** Prove every pipeline works end-to-end against the repo-only code path before the merge to main. ALL tests run with `BOSTON_FINDER_DISABLE_DEPLOY=1` so no production impact.

**Phase tag at end:** `unification-phase5`

### Task 5.1: oyster_deals end-to-end (safe)

- [ ] **Step 1: Clear persona cache to force re-fetch**

```bash
python3 -c "
import json, os
p = os.path.expanduser('~/boston_finder_cache.json')
with open(p) as f: c = json.load(f)
for k in list(c):
    if k.startswith('oyster_deals'):
        c.pop(k)
with open(p, 'w') as f: json.dump(c, f, indent=2)
print('cleared oyster_deals* keys')
"
```

- [ ] **Step 2: Run oyster_deals with force**

```bash
BOSTON_FINDER_SAFE_TEST=1 python3 oyster_deals.py --persona brian --force 2>&1 | tee /tmp/oyster_deals_run.log | tail -30
```
Expected: fetches food sources, scores via Haiku, writes `oyster_deals_brian` cache key with ≥10 deals.

- [ ] **Step 3: Verify cache populated**

```bash
python3 -c "
from boston_finder.cache import get
d = get('oyster_deals_brian')
print('items:', len(d) if d else 0)
if d:
    print('first:', d[0].get('venue') or d[0].get('name'))
"
```
Expected: items ≥ 10, first entry has a venue or name.

### Task 5.2: boston_events end-to-end with oyster bar (safe)

- [ ] **Step 1: Run boston_events safely**

```bash
BOSTON_FINDER_SAFE_TEST=1 \
BOSTON_FINDER_OUTPUT_FILE=/tmp/unification_test.html \
python3 boston_events.py --persona brian --days 7 2>&1 | tail -20
```
Expected: completes, writes `/tmp/unification_test.html`, does NOT deploy.

- [ ] **Step 2: Inspect output HTML**

```bash
grep -c '<div class="oyster-bar"' /tmp/unification_test.html
grep -c '"Date unknown"\|Date unknown' /tmp/unification_test.html
grep -oE '<title>[^<]+</title>' /tmp/unification_test.html
```
Expected: ≥1 oyster-bar div, 0 "Date unknown" occurrences (or very few — not 33 like the broken run), title contains today's date.

- [ ] **Step 3: Spot-check oyster bar has real data**

```bash
grep -oE 'var oysters = \[[^]]*\]' /tmp/unification_test.html | head -c 200
```
Expected: valid JSON array preamble with at least one venue.

### Task 5.3: oyster_verify end-to-end

- [ ] **Step 1: Run on one venue**

```bash
python3 oyster_verify.py --venue "Row 34" 2>&1 | tail -15
```
Expected: prints verify status, writes status file.

- [ ] **Step 2: Verify status file**

```bash
python3 -c "
import json, os
with open(os.path.expanduser('~/boston_finder_oyster_status.json')) as f: s = json.load(f)
print('row_34:', s.get('row_34'))
"
```
Expected: row_34 entry has status and maps_url.

### Task 5.4: oyster_triage smoke test

- [ ] **Step 1: Rank-only**

```bash
python3 oyster_triage.py --rank 2>&1 | tail -10
```
Expected: either ranked list or "run without --rank first" — no traceback.

### Task 5.5: Tag phase 5 complete

- [ ] **Step 1: Tag, push, update tracker**

```bash
git tag unification-phase5
git push origin unification-phase5
git push
```

---

# PHASE 6: Merge to main + production deploy

**Goal:** Production LaunchAgents now run repo-only code. Live site updated with oyster bar.

**Phase tag at end:** `unification-phase6`

### Task 6.1: Merge branch

- [ ] **Step 1: Switch to main + pull**

```bash
git checkout main
git pull --ff-only
```

- [ ] **Step 2: Merge unification branch (no-ff for clean history)**

```bash
git merge --no-ff codebase-unification -m "Unify boston_finder codebase — single source of truth"
```

- [ ] **Step 3: Push main**

```bash
git push origin main
```

### Task 6.2: Rewire live wrappers (outside repo)

- [ ] **Step 1: Update `/Users/brian/python-projects/run_boston_events.sh`**

Should already delegate to repo. Verify:
```bash
cat /Users/brian/python-projects/run_boston_events.sh
```
Expected: final line is `exec /Users/brian/python-projects/boston-finder-repo/run_boston_events.sh "$@"`. If not, write that.

- [ ] **Step 2: Update `/Users/brian/python-projects/run_oyster_deals.sh`**

Same pattern:
```bash
cat > /Users/brian/python-projects/run_oyster_deals.sh <<'EOF'
#!/bin/bash
source ~/.zshrc 2>/dev/null || true
exec /Users/brian/python-projects/boston-finder-repo/run_oyster_deals.sh "$@"
EOF
chmod +x /Users/brian/python-projects/run_oyster_deals.sh
```

### Task 6.3: Trigger real production deploy

- [ ] **Step 1: Run boston_events for real (this deploys)**

```bash
cd /Users/brian/python-projects/boston-finder-repo
BOSTON_FINDER_DISABLE_OPEN=1 python3 boston_events.py --persona all 2>&1 | tee /tmp/prod_deploy.log | tail -30
```
Expected: generates HTML for each persona, git commits + pushes, Netlify triggered.

- [ ] **Step 2: Verify live site**

Wait ~60 seconds for Netlify build, then:
```bash
curl -s https://highendeventfinder.netlify.app/ -o /tmp/live_post_merge.html
echo "oyster-bar: $(grep -c oyster-bar /tmp/live_post_merge.html)"
echo "var oysters: $(grep -c 'var oysters' /tmp/live_post_merge.html)"
echo "Date unknown count: $(grep -c 'Date unknown' /tmp/live_post_merge.html)"
grep -oE '<title>[^<]+</title>' /tmp/live_post_merge.html
```
Expected: ≥2 oyster-bar mentions, 1 `var oysters`, few or no Date unknown entries, title = today.

### Task 6.4: Tag phase 6 complete

- [ ] **Step 1: Tag**

```bash
git tag unification-phase6
git push origin unification-phase6
```

---

# PHASE 7: Deprecate & hard-delete stale

**Goal:** Remove the stale copy from `/Users/brian/python-projects/` so there's only ONE codebase.

**Phase tag at end:** `unification-phase7`

### Task 7.1: Soft-delete stale

- [ ] **Step 1: Create deprecation directory**

```bash
mkdir -p /Users/brian/python-projects/_deprecated_boston_finder
```

- [ ] **Step 2: Move stale package and scripts**

```bash
mv /Users/brian/python-projects/boston_finder     /Users/brian/python-projects/_deprecated_boston_finder/boston_finder
mv /Users/brian/python-projects/oyster_deals.py   /Users/brian/python-projects/_deprecated_boston_finder/oyster_deals.py
mv /Users/brian/python-projects/oyster_verify.py  /Users/brian/python-projects/_deprecated_boston_finder/oyster_verify.py
mv /Users/brian/python-projects/oyster_triage.py  /Users/brian/python-projects/_deprecated_boston_finder/oyster_triage.py
mv /Users/brian/python-projects/boston_events.py  /Users/brian/python-projects/_deprecated_boston_finder/boston_events.py
```

(Confirm `boston_events.py` outside the repo is truly stale first — `diff /Users/brian/python-projects/boston_events.py /Users/brian/python-projects/boston-finder-repo/boston_events.py`. If it has unique logic, port it in Phase 3 rather than delete.)

- [ ] **Step 3: Write a README in the deprecation dir**

Write to `/Users/brian/python-projects/_deprecated_boston_finder/README.md`:
```markdown
# DEPRECATED

All files here are OLD COPIES. The active codebase is at:
`/Users/brian/python-projects/boston-finder-repo/`

Soft-deleted on 2026-04-XX. If no regressions by 2026-05-XX, hard-delete this directory.
```

- [ ] **Step 4: Verify LaunchAgents still work**

```bash
launchctl kickstart -k gui/$(id -u)/com.brian.bostonevents
tail -20 ~/boston_events.log
```
Expected: latest run completes without "module not found" — if it fails, STOP. Move files back out of `_deprecated_boston_finder` and investigate.

- [ ] **Step 5: Commit tracking note in repo**

Update `tracking/unification-status.md`: soft-delete date + reminder for hard-delete one week later.

### Task 7.2: (One week later) Hard-delete

- [ ] **Step 1: Confirm no regressions in LaunchAgent logs**

```bash
tail -50 ~/boston_events.log
tail -50 ~/oyster_deals.log
```
All recent runs must be successful.

- [ ] **Step 2: Hard-delete**

```bash
rm -rf /Users/brian/python-projects/_deprecated_boston_finder
```

- [ ] **Step 3: Tag and record**

```bash
cd /Users/brian/python-projects/boston-finder-repo
git tag unification-phase7
git push origin unification-phase7
```
Update `tracking/unification-status.md` to mark Phase 7 complete.

---

## Rollback Procedures

**Per-phase rollback** (during Phases 0-5, all work on `codebase-unification` branch):
```bash
git reset --hard unification-phase<N-1>
```
Where N is the phase currently in progress.

**Full rollback after Phase 6 merge** (unlikely, but possible):
```bash
git checkout main
git revert -m 1 <merge-commit-sha>
git push
# then restore live wrappers to pre-merge state
cat > /Users/brian/python-projects/run_boston_events.sh <<'EOF'
#!/bin/bash
source ~/.zshrc 2>/dev/null || true
cd /Users/brian/python-projects
/Users/brian/python-projects/myenv/bin/python3 /Users/brian/python-projects/boston_events.py "$@"
EOF
```

**Rollback after Phase 7 hard-delete** (catastrophic):
```bash
git checkout main
git checkout pre-unification-backup -- boston_finder/ oyster_deals.py run_oyster_deals.sh
# hand-recreate stale scripts from git's pre-unification-backup tag — note stale copies
# existed only OUTSIDE git, so stale-only improvements are unrecoverable after hard-delete.
# This is why Phase 7 Task 7.1 keeps the _deprecated dir for one week.
```

---

## Session log (append-only, newest at bottom)

- 2026-04-18: Plan written. Current state on `main`: commit `db45d7d`. Uncommitted: my earlier edits to `oyster_deals.py` and `run_oyster_deals.sh` (intended to land on unification branch per Task 0.1 Step 3).
