# Codex code review — codebase-unification @ 57c971a

**Date:** 2026-04-18
**Reviewer:** Codex (OpenAI)
**Context:** review of Phases 2b-5 refactor. Prompt: see `tracking/code-review-context.md` and the human's review prompt.

---

## Codex findings (verbatim)

### Inline annotations (P1 = highest severity)

- **[P1] Default oyster run includes archived persona**
  - **File/line:** `oyster_deals.py:177`
  - **Body:** The all-persona path expands over every PERSONAS key, including inactive chloe. `run_persona` then calls `get_persona`, which raises for archived personas, so the default script path will eventually fail.
  - **Confidence:** 0.97

- **[P1] Single-venue verify clobbers registry**
  - **File/line:** `oyster_verify.py:251-286`
  - **Body:** When `--venue` is used, venues is narrowed to that subset and `generate_md` writes `oyster/venues.md` from only those results. That already produced a committed registry containing only Row 34, contrary to the claimed straight copy from stale.
  - **Confidence:** 0.96

- **[P2] Triage reads obsolete cache key**
  - **File/line:** `oyster_triage.py:190`
  - **Body:** The triage full run only reads `oyster_deals`, but the refactored `oyster_deals` script writes persona-scoped keys such as `oyster_deals_brian`. Once any legacy base cache is gone, the normal triage research path will report no cached deals.
  - **Confidence:** 0.94

- **[P2] Data push can fail after local write**
  - **File/line:** `boston_finder/html_output.py:537-541`
  - **Body:** The JSON file is written before git pull runs, and the pull result is ignored. A behind data clone can therefore fail to fast-forward because of the local write, then continue toward HTML deploy with only a generic "push failed" message.
  - **Confidence:** 0.86

- **[P3] Source pills are unescaped**
  - **File/line:** `boston_finder/html_output.py:564-568`
  - **Body:** Source names are interpolated directly into HTML. They are repo-controlled today, but this becomes unsafe if source names ever become config-driven or external.
  - **Confidence:** 0.82

### Summary table

| Severity | Location | Issue | Evidence | Recommendation |
|---|---|---|---|---|
| **BUG** | `oyster_deals.py:177` | Introduced by refactor: default `--persona all` includes archived `chloe` and fails. | `PERSONAS.keys()` = `['brian','dates','kirk','chloe']`; `active_personas()` omits `chloe`; direct `run_persona("chloe", [], False)` raises `RuntimeError`. | Use `active_personas()` for `all`, add parser choices, validate before fetching. |
| **BUG** | `oyster_verify.py:251`, `oyster/venues.md:15` | Inherited stale behavior, introduced to repo: `--venue` overwrites the full registry with only the selected venue. Claim that `venues.md` is a straight stale copy is false. | Diff against stale shows repo file lost multi-venue registry and now only has Row 34. | Restore stale registry; make single-venue verification update status without regenerating subset-only markdown. |
| **BUG** | `oyster_triage.py:190`, `oyster_deals.py:164` | Introduced by refactor: triage full run reads `oyster_deals`, but oyster refresh now writes only `oyster_deals_{persona}`. | Phase 5 only tested `--rank`, so this path was missed. | Add `--persona` to triage or default to `oyster_deals_brian`, with fallback logic. |
| **LATENT** | `oyster_deals.py:179` | Cached runs still fetch all food sources before checking persona cache or validating persona. | `main()` fetches+dedupes before `run_persona()` checks `cache_get(cache_key)`. | Validate persona and check cache before network fetches. |
| **LATENT** | `html_output.py:537` | Data-branch push is fragile; failures are under-reported. | Writes JSON, then runs unchecked `git pull`, then catches `CalledProcessError` without stderr and deploy continues. | Pull before writing, use `check=True`, print stderr, decide whether data failure should abort HTML deploy. |
| **SMELL** | `html_output.py:377` | `PERSONA_PATHS` is dead and stale: has `chloe` but not active `dates`. | No code references it except docs/tracking. | Remove or derive from `PERSONAS`. |
| **SMELL** | `oyster_deals.py:53`, `location.py:125` | `get_proximity(persona) or PROXIMITY` collapses `{}` into default. | Not a current runtime bug. | Use `is not None` fallback. |

### Codex's responses to my targeted questions

1. `_git_push_json` failure: **would NOT silently continue.** At minimum loud stderr, preferably abort HTML deploy if consistency matters.
2. `get_proximity(...) or PROXIMITY`: works today, switch to `is not None` for future empty-dict semantics.
3. `_sources_html` XSS: low risk today, but `html.escape()` is cheap — add it.
4. Inline imports + broad fallbacks in `build_json`: imports are fine; silent `except Exception` too quiet for schema drift; log warnings on non-optional failures.
5. Raw `nav_label` indexing: fine for internal fail-fast. The real issue is CLI paths not filtering inactive personas first.
6. CSS placement: rendered output looks structurally correct.
7. Push-before-deploy: data-first reasonable only if data-push success gates deploy. Current successful-data/failed-HTML leaves data ahead, but failed-data/successful-HTML is worse.

### Claim-check verdict (Codex)

- **Correct WHY claims:** SAFE_TEST gates JSON push and deploy; placeholder guard returns before both; sources bar order matches; schema `label`→`nav_label` rename caught in `oyster_deals.py`.
- **False/incomplete claims:** `oyster/venues.md` is NOT a straight stale copy; `--persona all` is NOT safe; cached oyster runs still do network fetches before cache use; doc metadata tip is stale (`161a866` in doc vs actual checkout `57c971a`).

Codex did NOT run `--force` or the full pipeline. Safe checks only: help/imports, SAFE_TEST `generate()` smoke to `/tmp/review_generate.html`, stale-vs-repo diffs, greps of `/tmp/unification_test.html`.

---

## My triage of Codex's findings

### Verified (I confirmed against the code on 2026-04-18 before Gemini ran)

1. ✅ **BUG 1 (chloe crash):** `personas.py:205` has `chloe: "active": False`; `get_persona` at `personas.py:272-274` raises for archived; `oyster_deals.py:177` passes `list(PERSONAS.keys())` unfiltered. **Real regression** — stale's personas module presumably didn't enforce an active-gate, so `--persona all` was safe there and isn't here. Fix: `active_personas()` gate in `main()`.

2. ✅ **BUG 2 (venues.md clobber):** Stale = 59 lines with B&G / Saltie Girl / Ostra / Eventide / Legal Sea Foods Pru+Copley etc.; repo @ `7bddc68` = 31 lines with only Row 34. The loss happened during my Phase 3.2 smoke test (`oyster_verify.py --venue "Row 34"` overwrote the file repo-side between the `cp` step and the `git add`). My commit captured the post-overwrite state. **Fix:** restore the file from stale and re-commit. Separately, fix the single-venue `generate_md` narrowing behavior (scope creep — could be a follow-up).

3. ✅ **BUG 3 (triage reads dead key):** `oyster_triage.py:190` reads `cache_get("oyster_deals")`; `oyster_deals.py:164` writes `oyster_deals_{persona}`. Phase 5.4 only hit `--rank`, missed this path. **Fix:** triage needs a `--persona` arg or a default to `oyster_deals_brian` with fallback to `oyster_deals` for legacy data.

4. ✅ **BUG 4 (push after write):** `html_output.py:537-541` writes then pulls with `check=False`. Order is pre-existing stale pattern but the diagnostics are weak. **Fix:** pull → write → add → commit → push; upgrade error surface.

### Partial agreement

5. ⚠️ **LATENT oyster_deals.py:179 (fetch-before-cache):** I think Codex is technically right but I'd push back on fixing this in THIS refactor. Moving the cache check to `main()` is a structural change that wasn't part of the port. Worth filing as a follow-up issue, not a Phase 6 blocker.

### Smells I'd fix while touching the files

6. ✅ **PERSONA_PATHS dead + missing `dates`:** Delete it or derive from `PERSONAS`. My Phase 2b commit shipped a constant that was redundant with `SITE_BASE` + persona `url_path`. Delete is the cleaner move.

7. ✅ **`get_proximity(...) or PROXIMITY`:** Low-risk future bug; one-line change to `is not None`. Do it.

8. ✅ **`_sources_html` XSS:** `html.escape(src)` inline. Cheap insurance.

### Suggested fix order (deferred until after both reviews)

1. Restore `oyster/venues.md` from stale (data-loss fix; no logic).
2. `oyster_deals.py` — filter `main()` loop via `active_personas()`, keep raw-index `nav_label` fail-fast.
3. `oyster_triage.py` — add `--persona brian` default; read `oyster_deals_{persona}` with legacy fallback.
4. `html_output.py` — swap pull/write order, `html.escape` on `_sources_html`, delete `PERSONA_PATHS`.
5. `oyster_deals.py` — `get_proximity(p) if ... is not None else PROXIMITY`.

Codex's remaining items (log-don't-pass on build_json fallbacks, abort-deploy-on-data-failure) are policy calls I'd rather resolve with the human than pattern-match on.
