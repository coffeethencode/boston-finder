# Boston Oyster Deals — Venue Registry

**Run `python3 oyster_verify.py` weekly to update status.**
Last verified: 2026-04-18 23:13

## Status Legend
| Symbol | Meaning |
|--------|---------|
| ✅ Active | Deal keywords found on venue website within last 30 days |
| ⚠️ Unverified | Not checked recently — deal may have changed |
| ❌ Inactive | Deal no longer listed or venue closed |

---

## Hike (Farther away)

| Venue | Neighborhood | Known Deal | Days / Hours | Status | Maps |
|-------|-------------|-----------|-------------|--------|------|
| Row 34 | Fort Point | Dollar oysters Mon–Wed 5–6pm | Mon–Wed 5–6pm | ⚠️ Unverified | [📍](https://maps.google.com/?q=Row%2034%20Fort%20Point%20Boston%20MA) |

---

## How to Add a Venue

1. Add entry to `boston_finder/oyster_sources.py` → `OYSTER_VENUES`
2. Run `python3 oyster_verify.py` — checks the site and rebuilds this file
3. Confirmed deal → status becomes ✅ Active automatically

## How to Mark a Deal Inactive

Set `"known_deal": None` in `oyster_sources.py` OR wait for verify to mark it ❌.
