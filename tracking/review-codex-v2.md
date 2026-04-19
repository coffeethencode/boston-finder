# Codex code review round 2 — codebase-unification @ c4e580a

**Date:** 2026-04-19
**Reviewer:** Codex (OpenAI)
**Context:** post-fix pass. Prompt: `tracking/review-prompt-v2.md`. Range: `unification-phase5..HEAD` (5 fix commits).

---

## Codex findings (verbatim)

### Inline annotations (P1 = highest severity)

- **[P1] Single-venue verify still clobbers registry**
  - **File/line:** `oyster_verify.py:251-287`
  - **Body:** The artifact was restored, but the underlying documented `--venue` path is unchanged: it narrows venues to the match, builds results from only that subset, then writes `oyster/venues.md` from that subset. Running the documented single-venue command will still overwrite the full registry.
  - **Confidence:** 0.96

- **[P2] Unchanged JSON skips before syncing data branch**
  - **File/line:** `boston_finder/html_output.py:539-544`
  - **Body:** `_git_push_json` returns before `git pull` when the local file content equals the new payload. If a previous push failed after writing/committing locally, or the local data clone is stale relative to origin, a later identical payload will never pull or push, leaving the remote data branch stale.
  - **Confidence:** 0.82

- **[P3] Public scored-cache API not used consistently**
  - **File/line:** `boston_finder/html_output.py:347-350`
  - **Body:** `cache.get_all_scored()` was added and `build_json` uses it, but `_extra_events_html` still imports the private `_load_scored` from outside `cache.py`. Not a behavior bug, but it undercuts the new public API boundary.
  - **Confidence:** 0.78

### Summary table

| Severity | Location | Issue | Evidence | Recommendation |
|---|---|---|---|---|
| **BUG** | `oyster_verify.py:251` | BUG 2 is only partially fixed. `oyster/venues.md` now matches stale, but `--venue` still rewrites the registry from a narrowed subset. | Code still filters `venues` before `generate_md(results)`. Did not rerun to avoid clobbering the file again. | Keep restored file, but skip `generate_md` for single-venue runs or regenerate from all venues/status. |
| **LATENT** | `html_output.py:539` | `_git_push_json` still has a pre-pull unchanged short-circuit. | Pull happens only after local file equality check. Can miss unpushed/stale remote state. | Pull/fetch before the equality check, or check clean/up-to-date git state before returning. |
| **SMELL** | `html_output.py:347` | `get_all_scored()` promotion is incomplete. | `build_json` uses the public wrapper; `_extra_events_html` still imports `_load_scored`. | Switch `_extra_events_html` to `get_all_scored()` too. |
| **SMELL** | `oyster_deals.py:33` | Fix left an unused `PERSONAS` import. | `ruff check` still reports F401 for `PERSONAS`; E402 is clean. | Remove unused import when making the next patch. |

### Bug verdicts

- **BUG 1** `--persona all`: fix confirmed. Active list is `['brian', 'dates', 'kirk']`; explicit `chloe` and fake names still fail fast via `get_persona`.
- **BUG 2** venues data loss: **partial**. File restored and matches stale; single-venue clobber behavior remains.
- **BUG 3** triage cache key: fix confirmed. Default/kirk persona keys exist; legacy fallback remains.
- **BUG 4** write-then-pull: **partial**. Write now follows pull, but unchanged skip still happens before sync.
- **BUG 5** proximity fallback: fix confirmed. Grep found no live `get_proximity(...) or PROXIMITY` call sites.

### Other checks

- `_sources_html` escapes `<`, `>`, `&`, and `"`.
- `build_json` warnings include section, exception type, and message.
- Generated `docs/index.html` for April 19 has 93 cards, sources bar, oyster block, and no "Date unknown".
- SAFE_TEST `generate()` smoke also skipped deploy/open cleanly.

### Final verdict

**Not safe to merge to main yet** unless the human explicitly accepts the remaining `oyster_verify --venue` clobber as out of scope.

---

## My triage of Codex round 2

### Verified against the code on 2026-04-19

1. ✅ **P1 — `oyster_verify.py --venue` still clobbers**: confirmed. Lines 251-254 narrow `venues` to the match, line 287 calls `generate_md(results)` on the narrowed `results`. The file restore in `072acd6` fixed the artifact but not the logic. Round 1 already flagged this ("scope creep — could be a follow-up" in `review-codex.md`); Codex is re-surfacing it rather than finding something new.
2. ✅ **P2 — pre-pull unchanged short-circuit**: confirmed. Lines 539-544 return before the pull at line 551. Failure mode is real: a previous run that wrote + committed locally but failed to push leaves the file content equal to the new payload; next invocation returns early and never catches up. Also triggers on a freshly stale clone where somebody pushed to the data branch from another machine.
3. ✅ **P3 — `_extra_events_html` still uses `_load_scored`**: confirmed. Line 348 imports the private symbol. `build_json` got the public-API treatment in `c4e580a`; this call site was missed.
4. ✅ **SMELL — unused `PERSONAS` import**: confirmed. `ruff check oyster_deals.py` reports F401 for `PERSONAS` on line 33. The fix in `5438b28` switched to `active_personas()` but left the import in place.

### Decision matrix for Phase 6

| Finding | Block Phase 6? | Suggested action |
|---|---|---|
| P1 venue clobber | No, if we file an issue | Either fix now (≈3 lines: skip `generate_md` when `args.venue`) or file issue like #1 and accept as out-of-scope for this refactor. **My preference: fix it now** — same file, same function, tiny diff, removes the "unless human accepts" caveat from Codex's verdict. |
| P2 unchanged short-circuit | No, but should fix | Cheapest robust fix: `git fetch` + check `git rev-list @{u}..HEAD` before returning early. Or just drop the short-circuit — the cost of an unnecessary `git pull --ff-only` is ~100ms. |
| P3 `_load_scored` import | No | Cleanup. Do it while touching `html_output.py` for P2. |
| PERSONAS unused import | No | One-line delete. Do it while touching `oyster_deals.py`. |

### Recommended fix order (if we do them)

One more fix commit before Phase 6:
1. `oyster_verify.py` — guard `generate_md(results)` behind `if not args.venue` (or merge with existing registry).
2. `html_output.py:539-544` — drop the content-equality short-circuit, or move it after a `git fetch` + ahead-check.
3. `html_output.py:348` — swap `_load_scored` → `get_all_scored`.
4. `oyster_deals.py:33` — remove `PERSONAS` from the import list.

All four are small, additive, and don't touch logic that round 1/round 2 already signed off on.

### What Codex did NOT flag (worth noting)

- No new bugs in the `_git_push_json` happy path (cwd/quoting/subprocess args).
- The `build_json` `_warn` closure works correctly.
- No third call site for `get_proximity(...) or PROXIMITY` (grep clean).
- Page structure verified via SAFE_TEST generate smoke: 93 cards, all sections present.

### Next step

Give this same round-2 prompt + the current code to a **different AI** (Gemini or Grok) for a third opinion before merge. The question to them: *did Codex miss anything, and would you also block on the `--venue` clobber?*
