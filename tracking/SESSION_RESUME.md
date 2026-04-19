# Session resume — codebase-unification

Last updated: 2026-04-19 (oyster pipeline simplification landed on feature branch)

## Where we are

**Active feature branch:** `oyster-pipeline-simplify` (15 commits ahead of main). All 13 plan tasks complete, 74 pytest tests passing, ready to merge into `main`.

**Oyster pipeline simplification status:**
- Spec: `tracking/specs/2026-04-19-oyster-pipeline-unification-design.md` (commit `acaf57f`)
- Plan: `tracking/plans/2026-04-19-oyster-pipeline-unification.md` (commit `a00e40d`)
- 15 implementation commits from `1f11df2` through `b93e6a9`
- Both spec bugs fixed end-to-end, verified with live run:
  - Park 9 Dog Bar: no longer appears (binary filter drops "Everett Happy Hour")
  - Tradesman Charlestown + 224 Boston: both discovered via Boston Calendar, venue extracted from title, verified price "dollar", logged in `~/boston_finder_oyster_discoveries.json`
- Phase 2 (unified scoring tagging pass) + Phase 3 (auto-promotion rules) explicitly deferred to later specs
- Watch list post-merge: regex miss rate, LLM fallback cost via `costs.py` (source=`venue_extract`), discoveries log growth

**To merge:** `git checkout main && git merge --no-ff oyster-pipeline-simplify && git push`. First push to main will trigger Netlify deploy — the event finder's daily cron will run against the new code next morning at 8:07 AM.

---

**Branch:** `main` @ `b06c6be` (pushed) — unification merged via `git merge --no-ff`
**Tags:** `unification-phase0` through `unification-phase6`

**Phase status:**
- ✅ Phases 0-5 complete
- ✅ Code review round 1 + round 2 complete (Codex + Gemini)
- ✅ Round-2 residuals patched in `849465d` (P1 venue guard, P2 pull-first short-circuit, P3 public cache API, unused import)
- ✅ Phase 6 complete: merged to main, pushed, production-deployed all 3 personas, live site verified, tagged `unification-phase6`. Net cost $0.0098 (morning cache absorbed most of it).
- 🛑 Phase 7 (soft-delete stale `/Users/brian/python-projects/boston_finder/` + sibling `oyster_*.py`) **pending** — one week after Phase 6 (earliest: 2026-04-26)

## To pick up next session

1. `cd /Users/brian/python-projects/boston-finder-repo && git fetch --all --tags && git checkout main`
2. Read this file.
3. If date ≥ 2026-04-26, execute Phase 7 per `tracking/2026-04-18-codebase-unification.md` §"PHASE 7": `mv /Users/brian/python-projects/{boston_finder,oyster_*.py} /Users/brian/python-projects/_deprecated_boston_finder/` — then delete the `_deprecated_*` directory a week later if nothing has broken.

## If going straight to Phase 6

Commands in order (from plan):
```bash
# Switch to main + pull
git checkout main
git pull --ff-only

# Merge the unification branch (includes all fixes)
git merge --no-ff codebase-unification -m "Unify boston_finder codebase — single source of truth"

# Push main
git push origin main

# Rewire live delegators (outside repo)
cat /Users/brian/python-projects/run_boston_events.sh   # verify already delegates
cat /Users/brian/python-projects/run_oyster_deals.sh    # same check

# Real production deploy (this spends AI money + triggers Netlify build)
cd /Users/brian/python-projects/boston-finder-repo
BOSTON_FINDER_DISABLE_OPEN=1 python3 boston_events.py --persona all 2>&1 | tee /tmp/prod_deploy.log | tail -30

# Verify live site (wait ~60s for Netlify)
curl -s https://highendeventfinder.netlify.app/ -o /tmp/live_post_merge.html
echo "oyster-bar: $(grep -c oyster-bar /tmp/live_post_merge.html)"
echo "sources-bar: $(grep -c sources-bar /tmp/live_post_merge.html)"
grep -oE '<title>[^<]+</title>' /tmp/live_post_merge.html

# Tag
git tag unification-phase6
git push origin unification-phase6
```

## Key context for a fresh AI

- Repo is Python 3, no test framework. "Verification = run the script and grep the output."
- Stale fork at `/Users/brian/python-projects/boston_finder/` and siblings (`oyster_*.py`) still exists — Phase 7 moves them to `_deprecated_boston_finder/` and deletes after a week.
- Data branch clone at `~/boston-finder-data/` — separate branch of same GitHub repo, pushed via `_git_push_json` without triggering Netlify builds.
- Live site: https://highendeventfinder.netlify.app/ (Brian default), `/chloe`, `/kirk`, `/dates`.
- Chloe is archived as of the personas schema refactor. GitHub issue #1 tracks residual live-artifact cleanup — not a Phase 6 blocker.

## Documents in `tracking/` (map)

| File | Purpose |
|---|---|
| `SESSION_RESUME.md` | This file — one-page TL;DR |
| `2026-04-18-codebase-unification.md` | Original plan, checkboxes preserved |
| `unification-status.md` | Session log (what-was-done per run) |
| `merge-decisions.md` | Per-file merge strategy (pre-fix spec) |
| `code-review-context.md` | WHY doc for round-1 review (pre-fix state) |
| `review-codex.md` | Codex review + my triage |
| `review-gemini.md` | Gemini review + my triage |
| `review-third-pass.md` | Runtime reproductions + ruff analysis |
| `review-prompt-v2.md` | Post-fix review prompt, ready to copy-paste |
| `diffs/` | Phase 1 diff snapshots (stale vs repo per file) |
| `runtime_wiring.md` | (pre-existing) |
