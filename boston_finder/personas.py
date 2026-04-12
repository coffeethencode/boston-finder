"""
Persona registry — all persona config lives here.

To archive someone: set active=False. Their full profile stays intact.
To bring them back: set active=True. Everything reconnects.
"""

from boston_finder.location import PROXIMITY

# ── Registry ────────────────────────────────────────────────────────

PERSONAS: dict[str, dict] = {
    "brian": {
        "active": True,
        "title": "Boston Events",
        "nav_label": "Brian",
        "accent": "#f0a500",
        "url_path": "/",              # index.html
        "deploy_file": "index.html",
        "proximity": None,            # uses default PROXIMITY table
        "prompt": (
            "You are filtering Boston events for someone who wants high-status, "
            "interesting things to attend:\n"
            "- Oyster happy hours or upscale food/drink (wine dinners, tastings, chef's tables)\n"
            "- Galas, fundraisers, charity benefits, receptions, award ceremonies\n"
            "- Events where they can attend as a subject matter expert: public records law, "
            "open meeting law, FOIA, government transparency, civic accountability, journalism\n"
            "- High-status professional networking, panels, policy forums\n"
            "- Fashion/model events, press events, media events, bikini/swimwear shows, "
            "fitness model showcases, promotional model events\n"
            "- Recurring upscale nightlife events, scene-y bar/club nights, influencer events\n"
            "- Anything exclusive, influential, or scene-y\n\n"
            "NOT wanted: pure sports games, road races, youth sports, basic trivia nights at chains."
        ),
    },
    "dates": {
        "active": True,
        "title": "Date Ideas",
        "nav_label": "Dates",
        "accent": "#c084fc",
        "url_path": "/dates",
        "deploy_file": "dates.html",
        "proximity": {
            **PROXIMITY,
            # dates persona uses Back Bay as home base
            "Back Bay":        10,
            "South End":        9,
            "Beacon Hill":      9,
            "Newbury Street":  10,
            "Fenway":           8,
            "Kenmore":          8,
            "Downtown":         8,
            "Seaport":          6,
            "Cambridge":        5,
            "Brookline":        6,
            "Chestnut Hill":    3,
        },
        "prompt": (
            "You are filtering Boston events for date ideas — things two people "
            "would enjoy doing together.\n\n"
            "Great date events:\n"
            "- Food & drink: wine tastings, prix fixe dinners, cocktail classes, "
            "food festivals, tasting menus, new restaurant openings\n"
            "- Arts & culture: gallery openings, museum exhibits, live music, jazz, "
            "comedy shows, theater, film screenings\n"
            "- Experiences: cooking classes, pottery, dance lessons, sunset cruises, "
            "rooftop events, seasonal markets\n"
            "- Outdoor: scenic walks, garden events, waterfront activities, bike tours\n"
            "- Nightlife: speakeasy events, live DJ sets, themed parties, rooftop bars\n\n"
            "Lower priority:\n"
            "- Kids/family-focused events\n"
            "- Pure networking or professional events\n"
            "- Large-scale sports (unless it's a unique experience like courtside)\n"
            "- Conferences, lectures, or panels with no social component\n\n"
            "Score 0-10. Only return events with score >= 5."
        ),
    },
    "kirk": {
        "active": True,
        "title": "Kirk's Boston",
        "nav_label": "Kirk",
        "accent": "#38bdf8",
        "url_path": "/kirk",
        "deploy_file": "kirk.html",
        "proximity": {
            **PROXIMITY,
            # Kirk has a car — wider range, Cambridge/Somerville are easy
            "Cambridge":        8,
            "Somerville":       7,
            "Charlestown":      7,
            "Allston":          6,
            "Brighton":         5,
            "Medford":          5,
            "Brookline":        6,
            # Providence is handled by source inclusion, not proximity
        },
        "prompt": (
            "You are filtering Boston-area events for Kirk, a sales engineer "
            "(ex-Mapbox/SoftBank, now at Bit Flow) finishing his master's degree. "
            "He has a car and will travel for quality events.\n\n"
            "High priority:\n"
            "- VC & startup events: demo days, pitch nights, founder dinners, "
            "investor panels, accelerator showcases\n"
            "- Tech meetups: engineering talks, product launches, AI/ML events, "
            "developer conferences, hackathons\n"
            "- Sales engineering / presales community events, SE meetups, "
            "technical sales panels\n"
            "- Professional networking with high-caliber attendees: "
            "C-suite mixers, industry dinners, alumni events at top firms\n"
            "- Career & grad school events relevant to tech/business\n\n"
            "Medium priority:\n"
            "- General tech/startup happy hours and social events\n"
            "- Business conferences with good speaker lineups\n"
            "- Upscale social events where professionals gather\n\n"
            "Lower priority:\n"
            "- Pure arts/culture events with no networking angle\n"
            "- Basic bar trivia or casual meetups\n"
            "- Kids/family events\n"
            "- Sports games\n\n"
            "Score 0-10. Event caliber > location — high-company-quality events "
            "score highest regardless of distance. Only return events with score >= 5."
        ),
    },
    "chloe": {
        "active": False,
        "title": "Chloe's Boston",
        "nav_label": "Chloe",
        "accent": "#c084fc",
        "url_path": "/chloe",
        "deploy_file": "chloe.html",
        "proximity": {
            **PROXIMITY,
            # Chloe was in Back Bay
            "Back Bay":        10,
            "South End":        9,
            "Beacon Hill":      9,
            "Newbury Street":  10,
            "Fenway":           8,
            "Kenmore":          8,
            "Downtown":         8,
            "Seaport":          6,
            "Cambridge":        5,
            "Brookline":        6,
            "Chestnut Hill":    3,
        },
        "prompt": (
            "You are filtering Boston events for Chloe, who wants upscale, "
            "interesting things to do in Boston.\n"
            "She loves:\n"
            "- Art: gallery openings, museum events, art shows, artist talks, "
            "art fairs, photography exhibits, sculpture\n"
            "- Food & drink: wine tastings, wine dinners, chef's table experiences, "
            "cocktail classes, food festivals, upscale restaurant events, mixology\n"
            "- Fancy experiences: galas, benefit dinners, charity auctions, cultural "
            "receptions, film premieres, theater openings\n"
            "- Design, fashion, and aesthetics — runway shows, design events, "
            "interior/architecture tours\n"
            "- Wellness and beauty events that are upscale (spa launches, product "
            "launches, brand events)\n"
            "- Anything cultured, beautiful, or scene-y\n\n"
            "Lower priority for her:\n"
            "- Pure civic/government/policy events (unless they're glamorous)\n"
            "- Sports\n"
            "- Basic networking mixers with no food/drink/art angle\n\n"
            "Score 0-10. Only return events with score >= 5."
        ),
    },
}

SITE_BASE = "https://highendeventfinder.netlify.app"


# ── Public API ──────────────────────────────────────────────────────

def get_persona(name: str) -> dict:
    """Return persona config. Raises RuntimeError if archived or unknown."""
    p = PERSONAS.get(name)
    if p is None:
        raise RuntimeError(f"unknown persona: {name}")
    if not p["active"]:
        raise RuntimeError(f"persona '{name}' is archived — flip active=True in personas.py to restore")
    return p


def get_prompt(name: str) -> str:
    """Return the scoring prompt for a persona."""
    p = PERSONAS.get(name, {})
    return p.get("prompt", "")


def get_proximity(name: str) -> dict | None:
    """Return proximity table for a persona, or None for default."""
    p = PERSONAS.get(name)
    if p is None:
        return None
    return p.get("proximity")


def active_personas() -> list[dict]:
    """Return all active personas in display order."""
    return [
        {"name": k, **v}
        for k, v in PERSONAS.items()
        if v["active"]
    ]


def nav_html(current: str) -> str:
    """Build nav bar markup for the current persona."""
    links = []
    for p in active_personas():
        url = f"{SITE_BASE}{p['url_path']}"
        cls = "nav-active" if p["name"] == current else "nav-link"
        links.append(f'<a href="{url}" class="{cls}">{p["nav_label"]}</a>')
    return "\n    ".join(links)


def feedback_buttons_html(active: list[dict] = None) -> str:
    """Return JS template for feedback buttons using active persona names."""
    if active is None:
        active = active_personas()
    buttons = []
    for p in active:
        name = p["name"]
        label = p["nav_label"]
        buttons.append(
            f"'<button class=\"fb-btn\" data-p=\"{name}\" data-v=\"up\">"
            f"\uD83D\uDC4D {label}</button>'"
        )
        buttons.append(
            f"'<button class=\"fb-btn\" data-p=\"{name}\" data-v=\"down\">"
            f"\uD83D\uDC4E {label}</button>'"
        )
    return " +\n        ".join(buttons)
