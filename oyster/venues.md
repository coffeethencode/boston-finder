# Boston Oyster Deals — Venue Registry

**Run `python3 oyster_verify.py` weekly to update status.**
Last verified: *not yet run*

## Status Legend
| Symbol | Meaning |
|--------|---------|
| ✅ Active | Deal keywords found on venue website within last 30 days |
| ⚠️ Unverified | Not checked recently — deal may have changed |
| ❌ Inactive | Deal no longer listed or venue closed |

---

## Nearby (South End / Back Bay)

| Venue | Neighborhood | Known Deal | Days / Hours | Status | Maps |
|-------|-------------|-----------|-------------|--------|------|
| B&G Oysters | South End | Unknown | — | ⚠️ Unverified | [📍](https://maps.google.com/?q=B%26G+Oysters+Boston+MA) |
| Saltie Girl | Back Bay | Unknown | — | ⚠️ Unverified | [📍](https://maps.google.com/?q=Saltie+Girl+Boston+MA) |
| Ostra | Back Bay | Unknown | — | ⚠️ Unverified | [📍](https://maps.google.com/?q=Ostra+Boston+MA) |
| Eventide | Back Bay | Unknown | — | ⚠️ Unverified | [📍](https://maps.google.com/?q=Eventide+Boston+MA) |
| Legal Sea Foods Prudential | Back Bay | $1 oysters daily 3–6pm (bar only) | Daily 3–6pm | ⚠️ Unverified | [📍](https://maps.google.com/?q=Legal+Sea+Foods+Prudential+Boston+MA) |
| Legal Sea Foods Copley | Back Bay | $1 oysters daily 3–6pm (bar only) | Daily 3–6pm | ⚠️ Unverified | [📍](https://maps.google.com/?q=Legal+Sea+Foods+Copley+Boston+MA) |

## Easy (North End / Fenway / Downtown)

| Venue | Neighborhood | Known Deal | Days / Hours | Status | Maps |
|-------|-------------|-----------|-------------|--------|------|
| Neptune Oyster | North End | No standing happy hour — excellent raw bar | — | ⚠️ Unverified | [📍](https://maps.google.com/?q=Neptune+Oyster+Boston+MA) |
| Legal Sea Foods Long Wharf | Downtown/Waterfront | $1 oysters daily 3–6pm (bar only) | Daily 3–6pm | ⚠️ Unverified | [📍](https://maps.google.com/?q=Legal+Sea+Foods+Long+Wharf+Boston+MA) |

## Doable (Seaport / Kenmore)

| Venue | Neighborhood | Known Deal | Days / Hours | Status | Maps |
|-------|-------------|-----------|-------------|--------|------|
| Island Creek Oyster Bar | Kenmore | $1 oysters at bar, select hours | — | ⚠️ Unverified | [📍](https://maps.google.com/?q=Island+Creek+Oyster+Bar+Boston+MA) |
| Row 34 | Fort Point | Dollar oysters Mon–Wed 5–6pm | Mon–Wed 5–6pm | ⚠️ Unverified | [📍](https://maps.google.com/?q=Row+34+Boston+MA) |
| Woods Hill Pier 4 | Seaport | Dollar oysters Mon–Wed 5–6pm | Mon–Wed 5–6pm | ⚠️ Unverified | [📍](https://maps.google.com/?q=Woods+Hill+Pier+4+Boston+MA) |
| Legal Harborside | Seaport | $1 oysters daily 3–6pm (bar only) | Daily 3–6pm | ⚠️ Unverified | [📍](https://maps.google.com/?q=Legal+Harborside+Boston+MA) |

## Hike (Cambridge)

| Venue | Neighborhood | Known Deal | Days / Hours | Status | Maps |
|-------|-------------|-----------|-------------|--------|------|
| Russell House Tavern | Harvard Square | $1 oysters 9–10pm Sun & Mon | Sun & Mon 9–10pm | ⚠️ Unverified | [📍](https://maps.google.com/?q=Russell+House+Tavern+Cambridge+MA) |

---

## How to Add a Venue

1. Add an entry to `boston_finder/oyster_sources.py` → `OYSTER_VENUES`
2. Run `python3 oyster_verify.py` — it will check the site and rebuild this file
3. If the deal is confirmed, status will update to ✅ Active automatically

## How to Mark a Deal Inactive

Set `"known_deal": None` in `oyster_sources.py` and delete from this file, OR
just run `oyster_verify.py` — if no keywords are found the status becomes ❌ Inactive.
