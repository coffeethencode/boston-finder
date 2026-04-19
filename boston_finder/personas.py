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
        "min_score": 5,
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
        "oyster_prompt": """Score Boston oyster deals for Brian, who lives in the South End.
Priorities:
- Value: dollar oysters or half-price deals score highest (9–10)
- Location: South End > Back Bay > Fort Point/North End > Seaport > Cambridge
- Vibe: he likes buzzy bar scenes, not quiet fine dining rooms
- Known great venues: B&G Oysters (his neighborhood), Row 34, Island Creek, Neptune
- Skip: tourist traps, chains with no vibe, anything in Cambridge unless extraordinary

Score 9–10: $1 oysters at a great scene-y bar within walking distance of South End
Score 5–6: decent deal at a good venue but a trip required or deal is modest
Score 1–4: tourist chain, no deal, or requires an Uber""",
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
        "min_score": 5,
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
        # Dates persona inherits Brian's oyster_prompt style — date-appropriate oyster venues.
        "oyster_prompt": """Score Boston oyster deals for someone looking for date-night oyster spots.
Priorities:
- Atmosphere: beautiful rooms, great wine lists, romantic vibe (9–10)
- Location: Back Bay > South End > North End/Beacon Hill > Seaport > Cambridge
- Prefers: upscale but approachable — not intimidating fine dining
- Known great venues: Neptune Oyster (iconic), Eventide, Saltie Girl, Ostra, B&G
- Skip: noisy sports bars, chains, anything too casual for a date

Score 9–10: oysters at a beautiful/upscale venue perfect for a date
Score 5–6: decent deal at a good-enough venue, not a destination
Score 1–4: chain restaurant, no atmosphere, or a dive bar vibe""",
    },
    "kirk": {
        "active": True,
        "title": "Kirk's Boston",
        "nav_label": "Kirk",
        "accent": "#38bdf8",
        "url_path": "/kirk",
        "deploy_file": "kirk.html",
        "proximity": {
            # Kirk is in southern RI — Providence is home base, Boston is a trip worth making for quality.
            # Providence / RI scores highest. Boston/Cambridge scores high but requires a great event.
            # min_score is set to 7 so only genuinely good events surface.
            "Providence":          10,
            "Rhode Island":        10,
            "Brown University":    10,
            "Quonset":              8,
            "Warwick":              8,
            # Boston area — worth the drive for quality
            "Cambridge":            9,
            "Kendall":              9,
            "MIT":                  9,
            "Somerville":           8,
            "Central Square":       9,
            "Boston":               8,
            "Seaport":              8,  # major tech/startup hub
            "Financial District":   8,
            "Downtown":             8,
            "Beacon Hill":          7,
            "Back Bay":             7,
            "South End":            7,
            "North End":            7,
            "Fenway":               7,
            "Charlestown":          7,
            "Allston":              7,
            "South Boston":         6,
            "Brighton":             6,
            "Brookline":            6,
            "Medford":              6,
            "Watertown":            5,
            "Newton":                5,
            "Waltham":               5,
            "Burlington":            4,
            # Everything else defaults to 5
        },
        "min_score": 7,  # higher bar — Kirk is in southern RI, only surface genuinely great events
        "prompt": (
            "You are filtering Boston, Cambridge, and Providence RI events for Kirk Brown.\n\n"
            "Kirk's background:\n"
            "- Senior Sales Engineer — sells and demos complex technical products to technical buyers\n"
            "- SE at Mapbox (SoftBank-backed geo/spatial tech) and Bit Flow (machine vision / industrial hardware)\n"
            "- Deep hands-on expertise: hardware engineering, software engineering, and technical sales\n"
            "- Finishing his master's degree\n"
            "- Domain expertise: geo/spatial tech, machine vision, industrial automation, semiconductors, data infrastructure\n\n"
            "Kirk needs events where a senior technical sales person is VALUED — not events aimed at founders pitching VCs, "
            "and not job fairs that attract mostly junior candidates. The ideal room has:\n"
            "- VCs, CTOs, and technical founders who need someone like Kirk to help sell or evaluate products\n"
            "- Senior operators at startups (not entry-level), people building and shipping real products\n"
            "- Events where deep product knowledge and demo skills matter\n\n"
            "What Kirk wants:\n"
            "- Deep tech product launches and demos: hardware, robotics, embedded systems, IoT, machine vision, "
            "industrial tech, semiconductors — events where the product is the star and technical sales people belong\n"
            "- GTM & revenue leadership: CRO panels, VP Sales roundtables, technical sales strategy, B2B go-to-market\n"
            "- Sales Engineer / presales community: SE community events, Pavilion SE chapter, SE Collective, PreSales Collective\n"
            "- Defense & deep tech: defense tech startups, dual-use hardware, MIT Lincoln Lab adjacent, Draper Lab, MITRE\n"
            "- VC-hosted portfolio events: ecosystem mixers (not pitch competitions)\n"
            "- Partner ecosystem events: Salesforce/HubSpot ecosystem events where SEs network with other SEs\n"
            "- University research-to-industry: MIT, Harvard, Brown, Northeastern, WPI — hardware/robotics/EE events\n"
            "- Geographic range: Boston, Cambridge, Somerville, Providence RI — has a car, will travel for quality\n\n"
            "SCORE 9-10 (must attend):\n"
            "- Hardware/deep tech product demo events (Greentown Labs showcases, MassRobotics demos, MIT hardware)\n"
            "- Semiconductor or chip design events with industry networking (ARM, Analog Devices, MIT MTL, IEEE Boston)\n"
            "- Sales Engineer or presales community events (Pavilion SE chapter, SE Collective, PreSales Collective)\n"
            "- Defense tech or dual-use hardware events open to industry (Draper, MITRE, DIU)\n"
            "- GTM/revenue leadership panels with VP+ speakers — technical sales focus\n"
            "- VC portfolio company mixers or deep tech ecosystem events (not pitch competitions)\n"
            "- Robotics showcases with real industry participation (MassRobotics, Boston Dynamics adjacent)\n\n"
            "SCORE 5-7 (worth knowing):\n"
            "- Senior tech networking with solid company mix — startups with real products, not just ideas\n"
            "- University EE/CS/robotics showcases with industry crossover\n"
            "- CTO or engineering leadership panels at companies in Kirk's domains\n"
            "- SaaS or hardware product launches in relevant sectors\n"
            "- Maker/hardware community events (Artisan's Asylum) if the crowd skews professional\n\n"
            "LOWER PRIORITY (score ≤ 4):\n"
            "- Pitch nights and demo days aimed at founders pitching investors (Kirk isn't pitching)\n"
            "- Job fairs, career fairs, or 'hiring mixer' events (attract too many junior candidates)\n"
            "- Generic startup networking or 'founder meetups' with no technical depth\n"
            "- Events clearly targeted at undergrads or early-career with no senior presence\n"
            "- Pure academic lectures with no networking or industry angle\n"
            "- Sports, arts-only, food/drink without tech angle\n"
            "- Basic networking mixers with no engineering or sales focus"
        ),
        "oyster_prompt": """Score Boston/Cambridge oyster deals for Kirk, based in Cambridge.
Priorities:
- Any good bar scene near Cambridge/Kendall/Central is ideal
- He's social and fine with a trip into Boston proper for a great deal
- Providence RI is acceptable if extraordinary (he goes there occasionally)
- Skip: tourist traps, quiet fine dining rooms

Score 9–10: dollar or half-price oysters at a buzzy bar in Cambridge or Boston
Score 5–6: decent deal at a solid venue, worth the trip
Score 1–4: no deal, overpriced, or too far""",
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
        "min_score": 5,
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
        "oyster_prompt": """Score Boston oyster deals for Chloe, who is based in Back Bay and wants upscale experiences.
Priorities:
- Atmosphere matters more than deal size — she'll pay $3 for oysters somewhere beautiful
- Location: Back Bay > South End > North End/Beacon Hill > Seaport > Kenmore
- Prefers: beautiful rooms, great wine lists, scene-y/upscale crowds
- Top picks: Saltie Girl (stunning wine bar), Neptune Oyster (iconic North End), Ostra, Eventide
- Acceptable: deals at high-quality seafood-focused restaurants
- Skip: noisy sports bars, chains, anything that feels casual or touristy

Score 9–10: oysters at a beautiful/upscale venue she'd be proud to bring someone to
Score 5–6: decent deal at a good-enough venue, not a destination
Score 1–4: chain restaurant, no atmosphere, or a dive bar vibe""",
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


def get_oyster_prompt(name: str) -> str:
    """Return the oyster-specific scoring prompt for a persona, falling back to event prompt."""
    p = PERSONAS.get(name, {})
    return p.get("oyster_prompt") or p.get("prompt", "")


def get_proximity(name: str) -> dict | None:
    """Return proximity table for a persona, or None for default."""
    p = PERSONAS.get(name)
    if p is None:
        return None
    return p.get("proximity")


def get_min_score(name: str, default: int = 5) -> int:
    """Return the minimum score threshold for a persona."""
    p = PERSONAS.get(name, {})
    return p.get("min_score", default)


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
