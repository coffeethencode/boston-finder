# Boston Finder

> **🚧 Active multi-session project in progress: codebase unification.**
> Any AI tool (Claude Code, Codex, Gemini CLI) picking up work here should:
> 1. Read **[tracking/unification-status.md](tracking/unification-status.md)** — the canonical progress log.
> 2. Read the plan: **[tracking/2026-04-18-codebase-unification.md](tracking/2026-04-18-codebase-unification.md)**.
> 3. Work on branch `codebase-unification` (Phases 0-5) or `main` (Phases 6-7) per the status file.
> 4. Update `tracking/unification-status.md` when you stop.

Daily Boston event digest. Runs every morning, finds high-status events for the next 7 days, scores them with AI, and opens an HTML digest in your browser.

## What it finds
- Oyster happy hours, wine dinners, tastings
- Galas, fundraisers, charity benefits, receptions
- Civic events: public records, open meeting law, FOIA, government transparency
- Fashion/model events, press events, media events
- High-status networking, panels, policy forums

## How it works

```
Sources (Eventbrite + do617)
  → hard keyword filter (pickleball, bowling, etc.)
  → AI scoring via Claude Haiku (cached per URL, 14-day TTL)
  → time + price enrichment from event detail pages
  → HTML digest opened in browser + deployed to Netlify
```

Cost per run: ~$0.00 when cache is warm, ~$0.15 on first cold run.

## Setup

```bash
pip install requests beautifulsoup4
export ANTHROPIC_API_KEY=your_key_here
python3 boston_events.py
```

## Files

| File | Purpose |
|------|---------|
| `boston_events.py` | Daily runner |
| `oyster_deals.py` | Weekly oyster deal finder |
| `oyster_triage.py` | Monthly venue quality research |
| `rate_venue.py` | CLI to rate venues personally |
| `boston_finder/sources.py` | Source registry (Eventbrite, do617) |
| `boston_finder/fetchers.py` | Scrapers + detail page enrichment |
| `boston_finder/ai_filter.py` | Claude Haiku scoring with cache |
| `boston_finder/costs.py` | Per-call and per-run cost tracking |
| `boston_finder/preferences.py` | Hard-skip keywords + AI soft rules |
| `boston_finder/html_output.py` | HTML digest generator |
| `boston_finder/location.py` | Proximity scoring from South End |
| `boston_finder/ratings.py` | Personal venue ratings |
| `boston_finder/cache.py` | JSON cache with TTL |

## Scheduling (macOS)

LaunchAgent runs daily at 8:07am via `~/Library/LaunchAgents/com.brian.bostonevents.plist`.
