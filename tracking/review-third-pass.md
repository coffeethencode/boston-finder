# Third-pass review — runtime reproduction + static analysis

**Date:** 2026-04-19
**Purpose:** verify Codex + Gemini bug claims by actually triggering them; complement the human reviewers with static analysis that neither ran.

---

## Runtime reproductions

### ✅ BUG 1 — `--persona all` crash on archived chloe (REPRODUCED)

Command: `python3 oyster_deals.py --persona all`

Observed behavior: brian + dates + kirk ran successfully (cached paths, total 46 deals across the three). Loop reached chloe. Crash:

```
Traceback (most recent call last):
  File "oyster_deals.py", line 207, in <module>
    main()
  File "oyster_deals.py", line 203, in main
    run_persona(persona_name, all_events, force=args.force)
  File "oyster_deals.py", line 119, in run_persona
    persona = get_persona(persona_name)
  File "boston_finder/personas.py", line 274, in get_persona
    raise RuntimeError(f"persona '{name}' is archived — ...")
RuntimeError: persona 'chloe' is archived — flip active=True in personas.py to restore
```

Key observation: partial success BEFORE crash. The active personas finish (and may emit desktop notifications via `notify.send(...)` + write their caches) before the archived one aborts the process. Cron's LaunchAgent sees non-zero exit and marks the run as failed — the user would see a red run status despite 3/4 personas having completed.

### ✅ BUG 3 — Triage reads dead cache key (REPRODUCED)

Cache state before running:
```
oyster_deals       key items: 0
oyster_deals_brian key items: 16
oyster_deals_dates key items: 18
oyster_deals_kirk  key items: 46
```

Command: `ANTHROPIC_API_KEY="" python3 oyster_triage.py` (no `--rank`, API key cleared to avoid spend)

Output:
```
No cached oyster deals. Run oyster_deals.py first.
```

Exit code: 1. Silent failure — the script does not try the persona-scoped keys as fallback. Confirmed: Codex's claim that "once any legacy `oyster_deals` cache is gone, the triage research path will report no cached deals" matches observed behavior exactly.

### ⚠️ BUG 4 — `_git_push_json` write-then-pull order (inspected only, not triggered)

Reason: the current `~/boston-finder-data` state is `On branch data, up to date with 'origin/data', nothing to commit`. The divergent-upstream condition required to trigger the failure mode does not exist. Reproducing it would require synthetic remote drift (git-reset the origin), which is more contrived than code inspection.

Code inspection confirms Codex's order claim (`html_output.py:535-541`):
```python
with open(fpath, "w") as f:    # write first
    f.write(json_str)

subprocess.run([..., "pull", "--ff-only", "--quiet"], check=False)  # then pull, silently
subprocess.run([..., "add", f"data/{persona}.json"], check=True)
```

The bug is conditional on upstream drift touching the same file. Under happy-path state (current observation) it is invisible. Fix is still warranted (defensive).

---

## Static analysis — `ruff check`

Ran `ruff 0.15.11` against the four files the refactor touched:
- `boston_finder/html_output.py`
- `oyster_deals.py`
- `oyster_verify.py`
- `oyster_triage.py`

Total: 26 errors across 5 rule categories:
- **E402** × 15 — module import not at top of file
- **F401** × 6 — unused imports
- **E701** × 2 — multiple statements on one line
- **F541** × 2 — f-string without placeholders
- **E401** × 1 — multiple imports on one line (`import json, os`)

9 of them are auto-fixable with `ruff check --fix`.

### Triage: introduced-by-refactor vs pre-existing

#### Introduced by the refactor (1 finding, 1 file)

| File:line | Rule | Finding | Fix |
|---|---|---|---|
| `oyster_deals.py:30` | F401 | `location_filter` imported but unused | Remove from import line (refactor-side typo; I added `PROXIMITY` but kept `location_filter` from stale's line even though we don't call it) |

#### Pre-existing from stale (inherited; this refactor did not create them)

| File:line | Rule | Finding |
|---|---|---|
| `html_output.py:349` | E401, F401×2 | Inner-scope `import json, os` in `_extra_events_html` — both `json` and `os` already imported at module top. Pre-existing. |
| `oyster_verify.py:38` | F401×2 | `label as proximity_label`, `PROXIMITY` imported but unused — straight stale copy |
| `oyster_triage.py:19` | F401 | `bs4.BeautifulSoup` imported but unused — straight stale copy |
| `oyster_deals.py:179` | F541 | `print(f"\n[oyster_deals] ...")` — stale's extraneous f-string |
| `oyster_verify.py:183` | F541 | `f"**Run ..."` — stale's extraneous f-string |
| `oyster_triage.py:96-97` | E701×2 | `try: return ...` / `except ...: return ...` single-line style from stale |

#### Expected and accepted

| File:line | Rule | Note |
|---|---|---|
| All 4 files top-of-file | E402×15 | Module imports appear after the `ROOT = Path(__file__).parent` + `sys.path.insert(...)` block — that's the deliberate pattern for making the scripts work from any clone location. Suppressing this rule (or adding `# noqa: E402`) is the accepted resolution. |

### Verdict on static analysis

**Clean bill of health on the refactor surface.** One unused-import typo I introduced (`location_filter`), seven inherited-from-stale lint items that were pre-existing and not a regression this session. The refactor didn't add any real lint debt.

E402 is the only rule class where the score is "noisy by design" — every script needs `sys.path.insert` before the package imports, so every script trips E402. Adding `# ruff: noqa: E402` at the top of each script is a clean way to document the intent without sprinkling inline noqa annotations.

---

## Combined fix list (updated after third pass)

No change to the fix priorities from `tracking/review-gemini.md`, plus one new item:

| Priority | Source | Fix | File |
|---|---|---|---|
| 1 | Codex + runtime repro | Filter `main()` loop via `active_personas()` — crash confirmed | `oyster_deals.py:177` |
| 1 | Codex | Restore `oyster/venues.md` from stale | `oyster/venues.md` |
| 1 | Codex + runtime repro | `oyster_triage.py` cache-key mismatch — confirmed silent failure | `oyster_triage.py:190` |
| 2 | Both AIs | `html.escape(src)` in `_sources_html` | `html_output.py:564` |
| 2 | Codex | `_git_push_json`: pull before write; print stderr on failure | `html_output.py:535` |
| 2 | Codex | Delete `PERSONA_PATHS` (dead, schema-stale) | `html_output.py:377` |
| 3 | Both AIs | `get_proximity(...) is not None else PROXIMITY` | `oyster_deals.py:55`, `boston_finder/location.py:125` |
| 3 | Both AIs | Log (don't pass) in `build_json` fallbacks | `html_output.py:420-512` |
| 4 | Gemini | Promote `_load_scored` to public wrapper | `boston_finder/cache.py`, `html_output.py` |
| 4 | Gemini | Comment the sort key `(inactive, -prox, ai_score)` | `oyster_deals.py:63` |
| 5 | **Third pass — ruff** | Remove unused `location_filter` import | `oyster_deals.py:30` |
| 5 | **Third pass — ruff** | Add `# ruff: noqa: E402` at top of 3 top-level scripts OR add `# noqa: E402` per-line | `oyster_deals.py`, `oyster_verify.py`, `oyster_triage.py` |

### Things NOT in the fix list

- E402 is a stylistic rule conflicting with a required pattern — add noqa, don't restructure.
- F401/F541/E701 in pre-existing stale-origin code — not regressions from this refactor. Could be cleaned up opportunistically but not part of the refactor's fix budget.

---

## Separately filed

- GitHub issue **#1** "Complete chloe → dates persona transition: remove live artifacts" — tracks the residual live-site / data-branch / UI cleanup that is orthogonal to the refactor. Not a Phase 6 blocker.

## Time spent on third pass

- Runtime reproductions: ~2 minutes of wall clock, $0.02 of Haiku spend (from the partial `--persona all` run that scored 8 fresh events).
- Static analysis: `brew install ruff` + one ruff invocation. Free.
- This doc + triage: inline.

## Recommendation

Both AI reviewers' verdicts stand: branch is ready for Phase 6 after the P1 fixes. The third pass did not surface any new high-severity issues — only confirmed the existing findings and caught one cosmetic unused-import I introduced.
