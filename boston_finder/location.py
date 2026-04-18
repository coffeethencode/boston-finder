"""
Location-based proximity scoring from South End home base.
Higher score = easier to get to = surfaces higher in rankings.

To adjust: just change the numbers below.
Anything not listed defaults to 3 (far/unknown).
"""

PROXIMITY: dict[str, int] = {
    "South End":              10,
    "Back Bay":                9,
    "Beacon Hill":             8,
    "Downtown":                8,
    "Financial District":      8,
    "West End":                7,
    "North End":               7,
    "Fenway":                  7,
    "Kenmore":                 6,
    "Seaport":                 5,
    "South Boston":            5,
    "Southie":                 5,
    "Cambridge":               5,
    "Brookline":               5,
    "Somerville":              4,
    "Charlestown":             4,
    "Allston":                 3,
    "Brighton":                3,
    "Dorchester":              3,
    "Jamaica Plain":           4,
    "Roxbury":                 5,
    "Mission Hill":            6,
    "Medford":                 2,
    "Quincy":                  1,
    "Providence":              2,
    "Rhode Island":            2,
    "Watertown":               3,
    "Newton":                  2,
    "Waltham":                 2,
    "Lynn":                    1,
    "Everett":                 2,
    "Winchester":              2,
    "Woburn":                  2,
    "Malden":                  2,
    "Revere":                  2,
    "Dedham":                  2,
    "Needham":                 2,
    "Chestnut Hill":           2,
    "Wellesley":               1,
    "Natick":                  1,
    "Framingham":              1,
}

DEFAULT_SCORE = 3  # anything not listed — assume inner city unknown neighborhood

# Minimum AI event score required to survive each proximity tier.
# Far away = needs to be more impressive to be worth the trip.
MIN_SCORE_BY_PROXIMITY = {
    10: 5,   # South End — anything above threshold
    9:  5,   # Back Bay
    8:  5,   # Beacon Hill / Downtown
    7:  5,   # North End / Fenway
    6:  5,   # Kenmore / Mission Hill
    5:  6,   # Seaport / Cambridge / Brookline — slightly harder
    4:  7,   # Somerville / JP / Charlestown — needs to be worth it
    3:  7,   # Allston / Dorchester / unknown — hike tier
    2:  8,   # Medford / Newton / Winchester / Quincy — expedition, must be great
    1:  9,   # Quincy / Lynn / Wellesley — only if truly epic
}


def score(neighborhood: str, prox_table: dict = None) -> int:
    """Return proximity score for a neighborhood string."""
    if not neighborhood:
        return DEFAULT_SCORE
    table = prox_table if prox_table is not None else PROXIMITY
    n = neighborhood.lower()
    for key, val in table.items():
        if key.lower() in n:
            return val
    return DEFAULT_SCORE


def label(s: int) -> str:
    if s >= 9:  return "nearby"
    if s >= 7:  return "easy"
    if s >= 5:  return "doable"
    if s >= 3:  return "hike"
    return "expedition"



def _price_penalty(price_str: str, prox: int) -> int:
    """
    Add to the required score when an event is both far and expensive.
    Close events: price doesn't matter much.
    Far events: expensive + far = needs to be truly worth it.
    """
    if prox >= 6 or not price_str:
        return 0  # nearby or no price info — no penalty
    try:
        # parse "$50" or "$25–$75" → take the low price
        digits = price_str.replace("$", "").split("–")[0].strip()
        price = float(digits)
    except Exception:
        return 0
    if prox <= 2:  # expedition tier
        if price > 150: return 2
        if price > 75:  return 1
    elif prox <= 4:  # hike tier
        if price > 200: return 1
    return 0


def location_filter(events: list[dict], persona: str = "brian") -> list[dict]:
    """
    Drop events that aren't worth the trip.
    Formula: distance + ticket cost vs event score.
    - Nearby: almost anything goes
    - Hike tier (Allston/Somerville): needs score ≥ 7, or be cheap/free
    - Expedition (Winchester/Quincy): needs score ≥ 8, high price pushes to 9+
    - World class (score 9-10): always keep regardless of distance or price
    Events with no location info pass through (benefit of the doubt).
    """
    from boston_finder.personas import get_proximity
    prox_table = get_proximity(persona) or PROXIMITY
    kept, dropped = [], []
    for e in events:
        address = (e.get("venue", "") + " " + e.get("address", "")).strip()
        prox = score(address, prox_table)
        event_score = e.get("score", 0)

        # world class events always make the cut
        if event_score >= 9:
            e["_proximity"] = prox
            kept.append(e)
            continue

        # no location — give benefit of the doubt
        if not address:
            kept.append(e)
            continue

        base_required = MIN_SCORE_BY_PROXIMITY.get(prox, 5)
        price_bump    = _price_penalty(e.get("price", ""), prox)
        min_required  = base_required + price_bump

        if event_score >= min_required:
            e["_proximity"] = prox
            kept.append(e)
        else:
            dropped.append((e["name"], address, prox, event_score, min_required, e.get("price", "")))

    if dropped:
        print(f"  [location] dropped {len(dropped)} events (too far / too expensive for score):")
        for name, addr, prox, escore, req, price in dropped[:5]:
            price_str = f" · {price}" if price else ""
            print(f"    ✗ {name[:48]} — {label(prox)}{price_str} (score {escore}, needed {req})")
        if len(dropped) > 5:
            print(f"    ... and {len(dropped)-5} more")

    return kept
