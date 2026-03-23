"""
User preferences for event filtering.
Edit this file to tune what surfaces and what gets filtered out.

HARD_SKIP    — always drop these, no AI needed, fast keyword filter
SOFT_RULES   — nuanced guidance injected into the AI scoring prompt
"""

# ── Hard skips — drop any event matching these keywords ───────────────────────
# These are unambiguous. No need to waste AI tokens on them.
HARD_SKIP_KEYWORDS = [
    "pickleball",
    "bowling league",
    "dodgeball",
    "kickball",
    "softball",
    "5k run",
    "10k run",
    "fun run",
    "road race",
    "triathlon",
    "swim meet",
    "marathon training",
    "youth sports",
    "little league",
]

# ── Soft rules — injected into the AI prompt for nuanced filtering ─────────────
# Write these as plain English instructions to Claude/Gemini.
SOFT_RULES = """
User preferences — apply these carefully:

SKIP these types of events:
- Pickleball, bowling, dodgeball, kickball, or any recreational sports leagues
- Professional networking events explicitly for a specific racial or ethnic identity group
  (e.g. "Latino Professional Networking Mixer", "Black Business Network", "Asian American
  Professionals mixer"). These are communities hosting events for their own members —
  the user would be an outsider and is not the intended audience.
  EXCEPTION: General cultural events from those communities are fine — salsa nights,
  Latin music, food festivals, art shows, cultural panels are all welcome.
- Events clearly aimed at college students or recent grads (graduation parties, campus mixers)
- MLM / pyramid scheme "business opportunity" events
- Basic chain restaurant trivia nights

KEEP these even if they seem niche:
- Any upscale food or drink event regardless of cultural origin
- Civic, government, journalism, or public records events of any kind
- Fashion, art, or cultural events open to the public
- Charity galas and fundraisers regardless of the cause
- Any panel or forum where expertise in law, media, or government would be valued
"""


def hard_skip_filter(events: list[dict]) -> list[dict]:
    """Drop events that match hard-skip keywords — no AI needed."""
    kw = [k.lower() for k in HARD_SKIP_KEYWORDS]
    out = []
    for e in events:
        text = (e.get("name", "") + " " + e.get("description", "")).lower()
        if not any(k in text for k in kw):
            out.append(e)
    return out
