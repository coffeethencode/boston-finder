# Unification progress log

**Plan:** [tracking/2026-04-18-codebase-unification.md](2026-04-18-codebase-unification.md)
**Branch:** `codebase-unification` (all Phase 0-5 work)
**Canonical status doc:** this file. Every AI/session must update this before ending.

## How to pick up where the last session left off

1. `git -C /Users/brian/python-projects/boston-finder-repo fetch --all --tags` (always do this first).
2. `git checkout codebase-unification` (unless you're in Phase 6/7 — see below).
3. Read the plan file. Find the first `- [ ]` in a Phase that isn't marked `- [x]` below. That's where work continues.
4. Read the **latest session log entry** at the bottom of this file for any gotchas / context the previous session flagged.
5. Do the work. When you stop: update phase checkboxes below, append a new session log entry, commit+push this file.

**Phase-to-branch mapping:**
- Phases 0-5 → branch `codebase-unification`
- Phase 6 → branch `main` (the merge happens in Phase 6)
- Phase 7 → branch `main` (one-week waiting period, then cleanup)

**Rollback tags** (set at end of each phase):
- `pre-unification-backup` — snapshot of main before any work
- `unification-phase0` through `unification-phase7` — end of each phase

## Phase checklist

- [x] Phase 0 — Safety net & branch setup
- [x] Phase 1 — Full diff & decision matrix
- [x] Phase 2 — Merge package files bottom-up
- [x] Phase 2b — Port stale's JSON-push feature (deferred from 2.13; see merge-decisions.md)
- [ ] Phase 3 — Port top-level scripts
- [ ] Phase 4 — Rewire LaunchAgent wrappers
- [ ] Phase 5 — Integration tests
- [ ] Phase 6 — Merge to main + production deploy
- [ ] Phase 7 — Deprecate & hard-delete stale

## Session log (append-only, newest at bottom)

| Date | Tool/model | Phase | Last task done | Branch state | Notes for next session |
|------|------------|-------|----------------|--------------|------------------------|
| 2026-04-18 | Claude Opus 4.7 (Claude Code) | Phase 0 complete | 0.3 (tag) | `codebase-unification` at `af6d4da` + tracker commit | Phase 1 starts with `tracking/diffs/` generation. The merge-decisions template is in the plan — fill it in by reading each diff. |
| 2026-04-18 | Claude Opus 4.7 (Claude Code) | Phase 1 complete | 1.3 (tag) | `codebase-unification` at `e5d6f0c` | Decision matrix at `tracking/merge-decisions.md`. **Key finding:** repo's April 12 "unify" commit dropped major features (Luma/Ticketmaster/Meetup/Instagram fetchers, Netlify/efficiency tracking, Providence venues, extracted cache). Merge strategy = keep repo architecture + restore stale features. Revised Phase 2 order: personas.py BEFORE location.py because location.py now depends on personas.get_proximity. |
| 2026-04-18 | Claude Opus 4.7 (Claude Code) | Phase 2 complete | 2.13 (tag) | `codebase-unification` at `379d6c1`, tag `unification-phase2` | All 12 package files merged. Integration smoke test passed (164 sources, all 11 types dispatchable, Kirk Providence=10 via persona proximity, default PROXIMITY has Providence=2). **Phase 2.13 deferred `build_json`/`_git_push_json`/`_sources_html` to new Phase 2b session** — documented in merge-decisions.md. **Phase 3 next (port oyster_deals.py/oyster_verify.py/oyster_triage.py).** See plan file for Phase 3 task template. **Note for Phase 3 oyster_deals.py port:** stale uses `persona["label"]` — repo schema uses `persona["nav_label"]` instead. Replace both references when porting. Also use `get_oyster_prompt()`/`get_min_score()` helpers added in Phase 2.8. |
| 2026-04-18 | Claude Opus 4.7 (Claude Code) | Phase 2b complete | tag | `codebase-unification` at `4d3b052`, tag `unification-phase2b` | Ported `build_json` + `_git_push_json` + `_sources_html` into repo `html_output.py`; added DATA_REPO / PERSONA_PATHS constants and .sources-bar / .src-pill CSS; wired `_git_push_json(build_json(...))` into generate() gated by DISABLE_DEPLOY/SAFE_TEST. Verified build_json produces valid payload; generate() smoke test renders sources bar correctly and respects placeholder+test gating. **Phase 3 still next (port oyster_deals.py/oyster_verify.py/oyster_triage.py).** |
