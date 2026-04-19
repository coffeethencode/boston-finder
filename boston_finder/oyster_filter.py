"""
Binary oyster-event classifier. Pure keyword rules, no AI.

Called per event from the cached event store. Events passing this filter
are candidates for venue extraction + verify.
"""

PRIMARY_KEYWORDS = (
    "oyster", "oysters",
    "raw bar",
    "shuck", "shucked", "shucking",
    "buck a shuck", "buck-a-shuck",
)

SECONDARY_KEYWORDS = (
    "bivalve", "bivalves",
    "wellfleet", "wellfleets",
    "duxbury", "duxburys",
    "shellfish happy hour",
    "raw bar happy hour",
)

_ALL_KEYWORDS = PRIMARY_KEYWORDS + SECONDARY_KEYWORDS


def is_oyster_candidate(event: dict) -> bool:
    """
    Return True if the event's title or description mentions oysters.

    Deliberately loose — verify step handles price/deal confirmation.
    Missed events (no keyword in any field) are acceptable per spec policy.
    """
    haystack = f"{event.get('name', '')} {event.get('description', '')}".lower()
    return any(kw in haystack for kw in _ALL_KEYWORDS)
