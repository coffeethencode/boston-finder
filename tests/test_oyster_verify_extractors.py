import oyster_verify as ov


# ── price ─────────────────────────────────────────────────────────────────────
def test_price_simple():
    assert ov.extract_price("$1 oysters") == "$1"


def test_price_decimal():
    assert ov.extract_price("$1.50 each oyster") == "$1.50"


def test_price_range():
    assert ov.extract_price("$1 - $2 oysters") == "$1-$2"


def test_price_range_en_dash():
    assert ov.extract_price("$1–$2 oysters") == "$1-$2"


def test_price_variety_between():
    assert ov.extract_price("$1 Duxbury oysters") == "$1"


def test_price_variety_between_decimal():
    assert ov.extract_price("$1.50 Island Creek oysters") == "$1.50"


def test_price_half():
    assert ov.extract_price("half-price oysters") == "half-price"


def test_price_half_space():
    assert ov.extract_price("half price raw bar") == "half-price"


def test_price_bogo():
    assert ov.extract_price("BOGO oysters Sunday") == "BOGO"


def test_price_two_for_one():
    assert ov.extract_price("2 for 1 oysters until close") == "2-for-1"


def test_price_dollar_word():
    assert ov.extract_price("dollar oysters 4-6pm") == "dollar"


def test_price_buck_a_shuck():
    assert ov.extract_price("buck a shuck Wednesdays") == "buck-a-shuck"


def test_price_no_oyster_context_returns_none():
    assert ov.extract_price("$5 cocktails") is None


# ── hours ─────────────────────────────────────────────────────────────────────
def test_hours_simple_range():
    result = ov.extract_hours("Mon-Wed 5-6pm")
    assert result == {"windows": [{"days": ["Mon", "Tue", "Wed"], "start": "17:00", "end": "18:00"}]}


def test_hours_en_dash():
    result = ov.extract_hours("Mon–Wed 5–6pm")
    assert result == {"windows": [{"days": ["Mon", "Tue", "Wed"], "start": "17:00", "end": "18:00"}]}


def test_hours_explicit_day_list():
    result = ov.extract_hours("Tue Wed Thu 4-6")
    assert result == {"windows": [{"days": ["Tue", "Wed", "Thu"], "start": "16:00", "end": "18:00"}]}


def test_hours_single_day_plural():
    result = ov.extract_hours("Mondays 9-10pm")
    assert result == {"windows": [{"days": ["Mon"], "start": "21:00", "end": "22:00"}]}


def test_hours_daily():
    result = ov.extract_hours("daily 3-6pm")
    assert result == {"windows": [{"days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                                    "start": "15:00", "end": "18:00"}]}


def test_hours_open_ended_until_sold_out():
    result = ov.extract_hours("Mondays 4 PM until sold out")
    assert result == {"windows": [{"days": ["Mon"], "start": "16:00", "end": None}]}


def test_hours_open_ended_starting_at():
    result = ov.extract_hours("Daily starting at 5 PM")
    assert result == {"windows": [{"days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                                    "start": "17:00", "end": None}]}


def test_hours_multi_window():
    result = ov.extract_hours("Sun-Thu 9-11 PM; Fri-Sat 10 PM-12 AM")
    assert len(result["windows"]) == 2
    assert result["windows"][0]["days"] == ["Sun", "Mon", "Tue", "Wed", "Thu"]
    assert result["windows"][1]["days"] == ["Fri", "Sat"]


def test_hours_no_match():
    assert ov.extract_hours("tickets available at the door") is None
