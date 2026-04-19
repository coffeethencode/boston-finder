from boston_finder import venue_extractor


# Strategy 1: event.venue populated
def test_strategy1_venue_field_populated():
    evt = {"name": "$1 Oysters", "venue": "Neptune Oyster"}
    assert venue_extractor.extract_venue(evt) == "Neptune Oyster"


def test_strategy1_venue_field_empty_falls_through():
    evt = {"name": "$1 Oysters at Lincoln Tavern & Restaurant", "venue": ""}
    assert venue_extractor.extract_venue(evt) == "Lincoln Tavern & Restaurant"


# Strategy 2: "at X" pattern
def test_strategy2_at_venue():
    evt = {"name": "$1 Oysters at Lincoln Tavern & Restaurant", "venue": None}
    assert venue_extractor.extract_venue(evt) == "Lincoln Tavern & Restaurant"


def test_strategy2_at_venue_with_dash_suffix():
    evt = {"name": "$1 Oyster Brunch at Grays Hall — Sunday Special", "venue": None}
    assert venue_extractor.extract_venue(evt) == "Grays Hall"


def test_strategy2_hosted_at():
    evt = {"name": "Oyster night hosted at Ostra", "venue": None}
    assert venue_extractor.extract_venue(evt) == "Ostra"


# Strategy 3: trailing caps
def test_strategy3_trailing_caps_tradesman():
    evt = {"name": "DOLLAR OYSTERS BUCK A SHUCK TRADESMAN CHARLESTOWN", "venue": None}
    result = venue_extractor.extract_venue(evt)
    # title-case correction applied
    assert result == "Tradesman Charlestown"


def test_strategy3_trailing_caps_single_word():
    evt = {"name": "$1 OYSTERS NEPTUNE", "venue": None}
    assert venue_extractor.extract_venue(evt) == "Neptune"


# Strategy 4: URL slug parse
def test_strategy4_url_slug():
    evt = {
        "name": "$1 Oysters",  # too generic for strategies 2/3
        "venue": None,
        "url": "https://www.thebostoncalendar.com/events/dollar-oysters-buck-a-shuck-tradesman-charlestown--30",
    }
    assert venue_extractor.extract_venue(evt) == "Tradesman Charlestown"


# No match — returns None (strategy 5 LLM tested separately with mock)
def test_no_match_returns_none():
    evt = {"name": "$1 Oyster Night", "venue": None, "url": "https://example.com/events/123"}
    # no strategy can extract a venue here
    assert venue_extractor.extract_venue(evt, use_llm_fallback=False) is None


# Strategy 3 stopword handling — avoids picking up "SUNDAY SPECIAL"
def test_strategy3_rejects_stopword_only_result():
    evt = {"name": "RAW BAR HAPPY HOUR SUNDAY SPECIAL", "venue": None}
    assert venue_extractor.extract_venue(evt, use_llm_fallback=False) is None


# Strategy 5: LLM fallback
def test_strategy5_llm_returns_venue(monkeypatch, tmp_path):
    # URL slug is all stopwords so strategy 4 returns None, strategy 5 fires.
    evt = {"name": "$1 Oyster Night", "venue": None, "url": "https://example.com/oyster-happy-hour"}

    def fake_haiku(prompt: str) -> str:
        return "Neptune Oyster"

    monkeypatch.setattr(venue_extractor, "_call_haiku_for_venue", fake_haiku)
    monkeypatch.setattr(venue_extractor, "_CACHE_FILE", str(tmp_path / "cache.json"))
    assert venue_extractor.extract_venue(evt) == "Neptune Oyster"


def test_strategy5_llm_unknown_returns_none(monkeypatch, tmp_path):
    # URL slug is all stopwords so strategy 4 returns None, strategy 5 fires.
    evt = {"name": "$1 Oyster Night", "venue": None, "url": "https://example.com/oyster-happy-hour"}

    monkeypatch.setattr(
        venue_extractor, "_call_haiku_for_venue", lambda prompt: "UNKNOWN"
    )
    monkeypatch.setattr(venue_extractor, "_CACHE_FILE", str(tmp_path / "cache.json"))
    assert venue_extractor.extract_venue(evt) is None


def test_strategy5_llm_cached_per_url(monkeypatch, tmp_path):
    # URL slug is all stopwords so strategy 4 returns None, strategy 5 fires.
    evt = {"name": "$1 Oyster Night", "venue": None, "url": "https://example.com/oyster-happy-hour"}

    calls = []

    def counting_haiku(prompt: str) -> str:
        calls.append(prompt)
        return "Somewhere Bar"

    monkeypatch.setattr(venue_extractor, "_call_haiku_for_venue", counting_haiku)
    monkeypatch.setattr(venue_extractor, "_CACHE_FILE", str(tmp_path / "cache.json"))

    assert venue_extractor.extract_venue(evt) == "Somewhere Bar"
    assert venue_extractor.extract_venue(evt) == "Somewhere Bar"
    assert len(calls) == 1  # second call hit the cache


def test_strategy5_uses_fetched_page_text_when_description_is_thin(monkeypatch, tmp_path):
    """When metadata is thin, strategy 5 should fetch the page and give its text to Haiku."""
    monkeypatch.setattr(venue_extractor, "_CACHE_FILE", str(tmp_path / "cache.json"))

    evt = {
        "name": "$1 OYSTER BRUNCH",
        "description": "",
        "venue": None,
        "url": "https://example.com/events/1-oyster-brunch--29",
    }

    captured_desc = []

    def fake_fetch(url, max_chars=3000):
        assert url == evt["url"]
        return "Join us at Tradesman Charlestown! Every Saturday 11am-3pm. $1 Buck a Shuck Oyster Brunch."

    def fake_haiku(prompt):
        # verify the page text reached the prompt
        captured_desc.append(prompt)
        assert "Tradesman Charlestown" in prompt
        return "Tradesman Charlestown"

    monkeypatch.setattr(venue_extractor, "_fetch_page_text", fake_fetch)
    monkeypatch.setattr(venue_extractor, "_call_haiku_for_venue", fake_haiku)

    assert venue_extractor.extract_venue(evt) == "Tradesman Charlestown"
    assert len(captured_desc) == 1


def test_strategy5_skips_fetch_when_description_is_substantial(monkeypatch, tmp_path):
    """If the event's own description is already substantial, skip the HTTP fetch."""
    monkeypatch.setattr(venue_extractor, "_CACHE_FILE", str(tmp_path / "cache.json"))

    evt = {
        "name": "$1 OYSTER BRUNCH",
        "description": "A wonderful oyster brunch at Neptune Oyster with live music and a full raw bar every weekend starting at 11am" * 3,
        "venue": None,
        "url": "https://example.com/x",
    }

    def fetch_should_not_run(url, max_chars=3000):
        raise AssertionError("fetch should not run when description is substantial")

    monkeypatch.setattr(venue_extractor, "_fetch_page_text", fetch_should_not_run)
    monkeypatch.setattr(venue_extractor, "_call_haiku_for_venue", lambda p: "Neptune Oyster")

    assert venue_extractor.extract_venue(evt) == "Neptune Oyster"


def test_strategy5_fetch_failure_falls_back_to_metadata(monkeypatch, tmp_path):
    """If page fetch fails, strategy 5 still calls Haiku with just metadata."""
    monkeypatch.setattr(venue_extractor, "_CACHE_FILE", str(tmp_path / "cache.json"))

    evt = {"name": "$1 Oyster Night", "description": "", "venue": None, "url": "https://down.example/x"}

    monkeypatch.setattr(venue_extractor, "_fetch_page_text", lambda *a, **kw: None)
    monkeypatch.setattr(venue_extractor, "_call_haiku_for_venue", lambda p: "UNKNOWN")

    assert venue_extractor.extract_venue(evt) is None  # UNKNOWN returned → None
