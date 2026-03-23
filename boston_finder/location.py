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
    "Watertown":               3,
    "Newton":                  2,
    "Waltham":                 2,
    "Lynn":                    1,
    "Everett":                 2,
}

DEFAULT_SCORE = 3  # anything not listed


def score(neighborhood: str) -> int:
    """Return proximity score for a neighborhood string."""
    if not neighborhood:
        return DEFAULT_SCORE
    # fuzzy match — check if any key appears in the address/neighborhood string
    n = neighborhood.lower()
    for key, val in PROXIMITY.items():
        if key.lower() in n:
            return val
    return DEFAULT_SCORE


def label(s: int) -> str:
    if s >= 9:  return "nearby"
    if s >= 7:  return "easy"
    if s >= 5:  return "doable"
    if s >= 3:  return "hike"
    return "expedition"
