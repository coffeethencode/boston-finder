# Runtime wiring notes

How the daily digest actually runs, and the footguns that have bitten.

## Execution path

```
LaunchAgent (~/Library/LaunchAgents/com.brian.bostonevents.plist)
  → ~/python-projects/run_boston_events.sh        (live wrapper)
  → ./run_boston_events.sh                         (repo wrapper — cds into repo)
  → python3 boston_events.py                       (repo entry)
  → boston_finder.html_output.generate(...)        (writes + deploys)
  → git commit + git push                          (triggers Netlify)
```

- Scheduled: daily at 8:07 AM (`Hour=8, Minute=7`)
- `launchctl print gui/501/com.brian.bostonevents` to inspect
- `launchctl list | grep boston` to confirm loaded

## The stale-copy trap (fixed April 18, 2026)

Before commit `b6acd14`, two things silently diverged:

1. The live LaunchAgent wrapper at `~/python-projects/run_boston_events.sh` ran `~/python-projects/boston_events.py` — a standalone copy *outside* the repo.
2. The repo's own `boston_events.py` / `dates_events.py` / `kirk_events.py` / `pull_feedback.py` did `sys.path.insert(0, "/Users/brian/python-projects")` at the top, so even a manual `python3 boston_events.py` from inside the repo imported `boston_finder/*` from the stale outside-the-repo copy.

Net effect: edits inside the repo had no runtime effect. A crash-on-every-run bug (`UnboundLocalError` in `generate()`, introduced April 12 in commit `0a57613`) caused six days of failed deploys with no visible signal — the site just looked stale.

**Rule:** changes to `boston_finder/*` must land in the repo *and* the repo must actually be the one being imported. If touching this pipeline, run `python3 -c "import boston_finder.html_output; print(boston_finder.html_output.__file__)"` to confirm the path resolves inside the repo.

## `generate()` side effects — test safely

`boston_finder.html_output.generate()` is not pure. It:

1. Writes `~/boston_events.html` (or `$BOSTON_FINDER_OUTPUT_FILE`)
2. Runs `open` to launch the browser
3. Calls `_git_deploy()` → `git add` + `git commit` + `git push` on the live repo → triggers Netlify deploy

**Do not call `generate()` with test data unless you've disabled deploy.** Use the env flags added in `html_output.py` (commit `b6acd14`):

```bash
BOSTON_FINDER_SAFE_TEST=1 \
BOSTON_FINDER_DISABLE_OPEN=1 \
BOSTON_FINDER_DISABLE_DEPLOY=1 \
BOSTON_FINDER_OUTPUT_FILE=/tmp/boston_events_test.html \
python3 boston_events.py
```

`BOSTON_FINDER_SAFE_TEST=1` turns on all three disables at once.

Deploy guard (`_placeholder_hits`) also rejects any event list containing `name="Test Event*"`, `url` with `example.com/`, or `venue="Test Venue"` — so the April 12 placeholder accident can't recur via normal code paths.

## History

- `0a57613` (Apr 12) — unify personas; introduced `UnboundLocalError` in `generate()`
- `842fdb2` (Apr 12, earlier) — last "successful" deploy; already contained placeholder `Test Event` data from an untracked manual invocation
- `dc6a6a9` (Apr 18) — fix `UnboundLocalError` (landed in repo but wasn't the loaded copy)
- `b6acd14` (Apr 18) — fix repo runtime wiring, add safe-test env flags and deploy guard
- `e6e90ec` (Apr 18) — first real deploy after the fix; 68 real events
