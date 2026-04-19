# Code review prompt — v2 (post-fix pass)

> **Usage:** copy the prompt between the `--- PROMPT START ---` and
> `--- PROMPT END ---` markers and paste into the next AI reviewer.
> The first round found 5 bugs. The fix commits are below. This pass
> checks that the fixes actually fix the bugs, don't introduce
> regressions, and surfaces anything the first two reviewers missed.

---

## Context that belongs in the prompt but too long to re-paste each time

**Branch:** `codebase-unification`
**Range already reviewed:** `unification-phase2..unification-phase5` (tag)
**Range for THIS (v2) review:** `unification-phase5..HEAD`

**Fix commits (in order they landed):**

| Commit | What it does | Bug being fixed |
|---|---|---|
| `5438b28` | `oyster_deals.py` main loop: `active_personas()` gate + remove unused `location_filter` import | P1 — `--persona all` crashed on archived chloe |
| `072acd6` | Restore `oyster/venues.md` from stale (59 lines, full registry) | P1 — my phase 3.2 smoke test had committed a 31-line narrowed version |
| `b76b755` | `oyster_triage.py`: `--persona` arg + read `oyster_deals_{persona}` with legacy fallback | P1 — triage read dead `oyster_deals` key, silent failure |
| `f559e9d` | `html_output.py`: `html.escape(src)` in sources bar; `_git_push_json` pulls before writing and surfaces stderr; delete dead `PERSONA_PATHS` | P2 — XSS latent, write-before-pull, dead schema-stale constant |
| `c4e580a` | `is not None` fallback for `get_proximity`; log-not-pass in `build_json`; new public `cache.get_all_scored`; sort-key comment; `# ruff: noqa: E402` on 3 scripts | P3/P4/P5 — six smaller items flagged by both AIs |

**Existing review context already written:**
- `tracking/code-review-context.md` — original WHY doc, written BEFORE fixes (so it describes the v1 state; the `.md` file has not yet been edited to reflect fixes)
- `tracking/review-codex.md` — Codex's first-pass findings + my triage
- `tracking/review-gemini.md` — Gemini's first-pass findings + my triage
- `tracking/review-third-pass.md` — runtime reproductions + ruff analysis
- `tracking/merge-decisions.md` — per-file merge spec

**External issue already filed:** https://github.com/coffeethencode/boston-finder/issues/1 tracks the chloe → dates transition cleanup (out of scope for refactor review).

---

## --- PROMPT START ---

You are reviewing the SECOND PASS of a Python refactor. A previous AI
reviewer round (Codex + Gemini + a runtime + ruff pass) found 5 bugs and
several code smells. The author has applied fixes, and you're verifying.

### Repo + state

- Local path: `/Users/brian/python-projects/boston-finder-repo/`
- Branch: `codebase-unification`
- Range for review: `git log unification-phase5..HEAD` (5 commits of fixes)

### Where to start

1. `tracking/review-gemini.md` — bottom has the combined fix list the author worked from.
2. `tracking/review-prompt-v2.md` (this file) — commit-by-commit map of what each fix was supposed to do.
3. `git log --stat unification-phase5..HEAD` — actual record of what each commit touched.
4. `git show <sha>` for each of the 5 fix commits to read the diffs.

### What I want you to do

**For each of the 5 bugs the first round flagged**, verify the fix:

#### BUG 1 — `--persona all` crash on archived personas
- Before: `python3 oyster_deals.py --persona all` crashed with `RuntimeError: persona 'chloe' is archived` after running brian + dates + kirk successfully.
- Fix commit: `5438b28`. Author replaced `list(PERSONAS.keys())` with `[p["name"] for p in active_personas()]`.
- **Verify:** does `--persona all` now iterate only active personas? Does `--persona chloe` (explicit) still fail-fast via `get_persona`'s active-gate? Does `--persona fake-name` produce a useful error? Is the old behavior preserved for explicit personas?

#### BUG 2 — `oyster/venues.md` data loss
- Before: repo's `oyster/venues.md` at commit `7bddc68` was a 31-line narrowed version containing only Row 34 (from my smoke test overwrite), NOT the 59-line stale registry the commit message claimed.
- Fix commit: `072acd6`. Author ran `cp /Users/brian/python-projects/oyster/venues.md oyster/venues.md`.
- **Verify:** diff the current repo `oyster/venues.md` against `/Users/brian/python-projects/oyster/venues.md` — should be identical. Do they match the stale tip?

#### BUG 3 — triage reads dead cache key
- Before: `python3 oyster_triage.py` (without `--rank`) read `cache_get("oyster_deals")` which the refactored deals script doesn't write. Silent failure.
- Fix commit: `b76b755`. Author added `--persona brian` default arg and `cache_get(f"oyster_deals_{args.persona}") or cache_get("oyster_deals")` fallback chain.
- **Verify:** does `oyster_triage.py` (no args) now load `oyster_deals_brian`? Does `--persona kirk` load `oyster_deals_kirk`? Does the legacy `oyster_deals` fallback still work? What happens if both are absent?

#### BUG 4 — `_git_push_json` write-then-pull
- Before: file write at `html_output.py:532-533` happened BEFORE `git pull --ff-only --quiet` at line 535, with `check=False` silently swallowing pull failures.
- Fix commit: `f559e9d`. Author reordered: pull happens first, captures `stderr` and prints on non-zero exit. Write + add + commit + push happen AFTER pull. Push also captures stderr.
- **Verify:** in the new `_git_push_json`, can you trace a path where a pull failure is silently ignored without a log line? What happens if the push fails — does `_git_deploy` still run (intended per Gemini) or does it abort (Codex's preference)? Is the "JSON unchanged, skip push" short-circuit still honored?

#### BUG 5 (related P3 smell) — `get_proximity(...) or PROXIMITY` collapse
- Before: `{}` as a persona's proximity would fall back to default. No persona actually does this today.
- Fix commit: `c4e580a`. Two locations updated (`oyster_deals.py:sort_by_proximity`, `boston_finder/location.py:location_filter`) to use `persona_prox if persona_prox is not None else PROXIMITY`.
- **Verify:** both sites use the new form? Any other callers of `get_proximity` still using `or`?

### Also verify these P2-P5 items from the first round

All landed in `f559e9d` + `c4e580a`:

- **`html.escape(src)` in `_sources_html`** (`html_output.py:557-569`): Does it actually escape `<`, `>`, `&`, `"`? Try feeding a source name with those chars.
- **`_load_scored` → `get_all_scored`**: Did the author promote the private cache API cleanly? Does `build_json` actually use the new public function? Is `_load_scored` still available for internal callers?
- **`build_json` log-not-pass**: Each `except Exception` block now calls `_warn(section, ex)` which writes to stderr. Is the section label useful in each case? Does the warning include the exception type and message?
- **Sort-key comment** (`oyster_deals.py:sort_by_proximity`): Does the new 4-line comment actually match the code? The rank tuple is `(inactive, -prox, ai_score)` where `ai_score = -(d.get("score") or 0)` — two negations total, net descending on score. Is the comment correct?
- **`# ruff: noqa: E402`**: Is it really needed on all three top-level scripts (`oyster_deals.py`, `oyster_verify.py`, `oyster_triage.py`)? `ruff check` should show 0 E402 errors now.

### New issues the first round may have missed

Don't just verify fixes — find fresh bugs. Likely hot spots:

1. **The new `_git_push_json` logic** touched a lot of lines. Did the refactor accidentally change the happy path (e.g. wrong `cwd`, broken quoting, misordered subprocess args)?
2. **The `build_json` log-not-pass** block now has a local `_warn` helper that captures `persona` via closure. Does it? Or does it need to re-resolve?
3. **`cache.get_all_scored`** is a thin wrapper. Does anything else in the codebase now prefer the public form? Should other private calls (`_save_scored`, `_load`, `_save`) also get public equivalents?
4. **The `is not None` fallback** is now in two files. Is there a third call site (e.g. any other module importing `get_proximity`) that still uses `or`? Grep everywhere.
5. **Phase 6 readiness:** run `BOSTON_FINDER_SAFE_TEST=1 python3 boston_events.py --persona brian --days 7` and verify the output HTML looks right. Any regression in the page structure?

### What NOT to do

- Don't actually push anything (`git push`, real `_git_push_json` runs against the data branch).
- Don't run `oyster_deals.py --force` without `BOSTON_FINDER_SAFE_TEST=1` unless you want to burn real AI spend.
- Don't fix code — flag issues, the author decides.

### Output format

Same table as first round:

| Severity | Location | Issue | Evidence | Recommendation |

Severity scale: BUG / LATENT / SMELL / QUESTION.

Also give a one-line verdict per bug: "fix confirmed" / "partial" / "broke something else" / "new issue discovered."

And a final line: "branch is safe to merge to main via Phase 6" yes/no, with one sentence.

### --- PROMPT END ---

---

## Running the v2 prompt

Recommend: send to a DIFFERENT AI than the one you used most recently. If
Gemini and Codex did round 1, try Claude or Grok for round 2. Fresh eyes
mean fresh biases.

The actual file copy-paste is between `--- PROMPT START ---` and `--- PROMPT END ---` above.
