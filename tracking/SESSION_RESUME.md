# Session resume — codebase-unification

Last updated: 2026-04-19 (post-fix state)

## Where we are

**Branch:** `codebase-unification` @ `c4e580a` (pushed)
**Tags on branch:** `unification-phase0` through `unification-phase5`
**Fixes since phase-5 tag:** 5 commits, not yet tagged

**Phase status:**
- ✅ Phases 0-5 complete (Phase 5 tag reflects pre-fix state)
- ✅ Code review round 1 complete (Codex + Gemini + runtime + ruff)
- ✅ Fix plan applied — all 5 BUGs and related smells addressed
- 🟡 Code review round 2 **pending** (prompt ready at `tracking/review-prompt-v2.md`)
- 🛑 Phase 6 (merge to main + production deploy) **pending** — needs round-2 signoff
- 🛑 Phase 7 (soft-delete stale) **pending** — one week after Phase 6

## To pick up next session

1. `cd /Users/brian/python-projects/boston-finder-repo && git fetch --all --tags && git checkout codebase-unification`
2. Read this file.
3. Decide: run v2 review first, or skip straight to Phase 6?
   - If v2 review: copy prompt from `tracking/review-prompt-v2.md` into a different AI (Codex/Gemini already used; try Claude or Grok)
   - If skipping: proceed with Phase 6 per `tracking/2026-04-18-codebase-unification.md` §"PHASE 6"

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
