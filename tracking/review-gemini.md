# Gemini code review — codebase-unification @ 57c971a

**Date:** 2026-04-18
**Reviewer:** Gemini (Google, CLI)
**Context:** same review prompt as Codex; Gemini ran after Codex.

---

## Gemini findings (verbatim)

### Summary table

| Severity | Location | Issue | Evidence | Recommendation |
|---|---|---|---|---|
| **BUG** | `oyster_deals.py:163` | Crash on `--persona all` | `main()` iterates over all keys in `PERSONAS`, but `run_persona` calls `get_persona()`, which raises `RuntimeError` for archived personas (e.g., Chloe). | Filter `PERSONAS` keys by active status in `main()` before looping. |
| **LATENT** | `html_output.py:563` | XSS Risk in Sources Bar | Source names (`src`) inserted directly into HTML: `f'<span class="src-pill">{src} ...'`. | Wrap `src` in `html.escape()`. |
| **SMELL** | `oyster_deals.py:55` | Ineffective explicit proximity override | `get_proximity(persona) or PROXIMITY` treats empty dict `{}` as falsy, falling back to defaults. | Use `is not None` check to allow explicit empty overrides. |
| **SMELL** | `html_output.py:420-512` | Silent data loss in `build_json` | Excessive `try/except Exception: pass` blocks around imports and logic silently drop data (e.g., `extra_events`) on failure. | Log the exception instead of pass so regressions in `cache.py` or `personas.py` are visible. |
| **SMELL** | `oyster_deals.py:63` | Confusing sort logic | `(inactive, -prox, ai_score)` with ascending sort relies on double-negatives to achieve descending priority. | Add a comment, or use `reverse=True` with an explicit multi-stage sort. |
| **SMELL** | `html_output.py:421` | Private API usage | `build_json` imports `_load_scored` which is marked internal/private in `cache.py`. | Expose a public `get_all_scored()` in `cache.py`, or remove the underscore if meant to be shared. |
| **QUESTION** | (none) | No unresolved human-only blockers. | Remaining choices are policy decisions from targeted questions. | — |

### Gemini's responses to my targeted questions

1. `_git_push_json` failure: **continuing to `_git_deploy` is the correct graceful-degradation path.** Data branch is an optimization; a failure there shouldn't block primary site deployment. *(Note: opposite position to Codex.)*
2. `get_proximity(...) or PROXIMITY`: minor bug; prevents a persona from opting out of all proximity bonuses via `proximity: {}`.
3. `_sources_html` XSS: latent. Current source names trusted; pattern is unsafe. `html.escape()` is cheap insurance.
4. Inline imports in `build_json`: robustness is a double-edged sword; recommend logging the error to stderr at minimum.
5. Raw `nav_label` indexing: agrees with fail-fast stance. `personas.py` is the registry; a missing key is a config error.
6. CSS placement: fine; keeps header-region styles co-located.
7. Push-before-deploy order: correct. HTML site depends on data branch being current.

### Gemini's wiring verification

- Stat header order: Cost → Sources → Oyster (matches intended hierarchy).
- Gating: `disable_deploy` correctly short-circuits both JSON push AND HTML git deploy; local HTML still generated for inspection.
- Placeholder guard: `_placeholder_hits` blocks both production steps on "Test Event" / "example.com".

**Verdict:** "The refactor is high quality and ready for Phase 6, provided the `oyster_deals.py` crash is fixed."

---

## My triage of Gemini's findings

### Intersection with Codex (highest confidence)

- **BUG — `--persona all` crash on chloe:** Both reviewers caught. Same location, same fix. Confirmed and prioritized.
- **LATENT — `_sources_html` XSS:** Both caught. Cheap fix (`html.escape`).
- **SMELL — `or PROXIMITY` fallback:** Both caught. Trivial fix.
- **SMELL — silent `except Exception: pass` in `build_json`:** Both caught (Codex labeled it partly via the "Inline imports" answer). Log-not-pass.

### Unique to Gemini (Codex missed)

- **SMELL — confusing sort logic `(inactive, -prox, ai_score)`:** I agree it's dense but disagree it's worth changing — it's a **direct port** of stale's sort key, and Brian has been reading these outputs for months. Changing to `reverse=True` multi-stage would be a semantic change during a port. File as "add a comment on the sort key" — don't restructure.
- **SMELL — private API usage `_load_scored`:** Agree. Either promote `cache._load_scored` to `cache.load_scored` (cheap), or add a public `get_all_scored()` wrapper. Low priority but worth doing since `build_json` is repo code, not stale.

### What Gemini missed (Codex caught, Gemini did not)

Gemini ran a lighter review and missed four Codex findings. Listing them so they're not forgotten:

1. **`oyster/venues.md` was NOT a straight copy.** Data loss / incorrect claim in my own review-context doc. Critical to fix.
2. **`oyster_triage.py:190` reads the wrong cache key.** `oyster_deals` legacy key vs `oyster_deals_{persona}` new key. Silent failure.
3. **`_git_push_json` writes-then-pulls** (fragile ordering + weak diagnostics).
4. **`PERSONA_PATHS` is dead + schema-stale** (missing the `dates` persona).

If I had only seen Gemini's review, #1 (venues.md data loss) would still be in `main` after Phase 6. That's the highest-value catch from Codex.

### Policy disagreement between reviewers

**`_git_push_json` failure semantics:**
- Codex: loudly fail, ideally abort HTML deploy.
- Gemini: continue to deploy; data branch is an optimization.

I lean Gemini's side: the static-site pipeline shouldn't be blocked on an optimization. But Codex is right that the current diagnostics (generic "push failed" without stderr) are too quiet — you'd miss a persistent data-branch drift without checking manually. **Resolution:** keep the continue-on-failure policy (Gemini) but improve the diagnostics (Codex) — print stderr on failure, flip `check=False` to `check=True` on the pull, `capture_output=True` with a stderr print on exception.

---

## Combined fix plan (after both reviews)

| Priority | Source | Fix | File |
|---|---|---|---|
| 1 | Both | Filter `main()` loop via `active_personas()`; crash-free `--persona all` | `oyster_deals.py` |
| 1 | Codex | Restore `oyster/venues.md` from stale | `oyster/venues.md` (re-commit) |
| 1 | Codex | Fix `oyster_triage.py` cache key + add `--persona` arg | `oyster_triage.py` |
| 2 | Both | `html.escape(src)` in `_sources_html` | `html_output.py` |
| 2 | Codex | `_git_push_json`: pull before write; better error surface | `html_output.py` |
| 2 | Codex | Delete `PERSONA_PATHS` (dead, schema-stale) | `html_output.py` |
| 3 | Both | `get_proximity(...) is not None else PROXIMITY` | `oyster_deals.py`, `location.py` |
| 3 | Both | Log (don't pass) in `build_json` fallbacks | `html_output.py` |
| 4 | Gemini | Promote `_load_scored` to public OR add `get_all_scored()` wrapper | `boston_finder/cache.py`, `html_output.py` |
| 4 | Gemini | Add comment on the sort key `(inactive, -prox, ai_score)` | `oyster_deals.py` |

Deferred (Codex's LATENT finding on fetch-before-cache in `oyster_deals.py:179`) — structural change, not part of port; file as follow-up.

Both reviewers' verdict: branch is ready for Phase 6 **after** the P1 fixes land.
