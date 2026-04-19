from boston_finder import venue_extractor as ve


def test_normalize_lowercase():
    assert ve.normalize("Tradesman Charlestown") == "tradesman charlestown"


def test_normalize_strips_punctuation():
    assert ve.normalize("Tradesman, Charlestown") == "tradesman charlestown"
    assert ve.normalize("B&G Oysters") == "bg oysters"
    assert ve.normalize("Woods Hill Pier 4") == "woods hill pier 4"


def test_normalize_collapses_whitespace():
    assert ve.normalize("TRADESMAN   Charlestown") == "tradesman charlestown"


def test_same_venue_different_cases_match():
    existing = ["tradesman charlestown"]
    assert ve.match_existing("TRADESMAN  Charlestown", existing) == "tradesman charlestown"


def test_prefix_with_neighborhood_suffix_matches():
    """Tradesman + Tradesman Charlestown → same venue (Charlestown is a known neighborhood)."""
    existing = ["tradesman"]
    # longer form incoming matches shorter existing; caller should upgrade canonical
    assert ve.match_existing("Tradesman Charlestown", existing) == "tradesman"


def test_prefix_with_neighborhood_suffix_reverse_order():
    """Tradesman Charlestown exists; Tradesman ingested second → match."""
    existing = ["tradesman charlestown"]
    assert ve.match_existing("Tradesman", existing) == "tradesman charlestown"


def test_chain_branches_distinct():
    """Legal Sea Foods Copley and Legal Sea Foods Prudential are separate venues."""
    existing = ["legal sea foods copley"]
    assert ve.match_existing("Legal Sea Foods Prudential", existing) is None


def test_chain_root_ambiguous_no_match():
    """Legal Sea Foods without suffix should NOT match a branched entry."""
    existing = ["legal sea foods copley"]
    assert ve.match_existing("Legal Sea Foods", existing) is None


def test_alias_map_woods_hill_pier():
    existing = ["woods hill pier 4"]
    assert ve.match_existing("Woods Hill Pier", existing) == "woods hill pier 4"


def test_no_match_returns_none():
    existing = ["neptune oyster"]
    assert ve.match_existing("Row 34", existing) is None
