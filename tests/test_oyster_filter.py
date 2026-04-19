from boston_finder import oyster_filter


def _evt(name="", description=""):
    return {"name": name, "description": description}


# primary keyword positives
def test_oyster_in_name_passes():
    assert oyster_filter.is_oyster_candidate(_evt(name="$1 Oyster Brunch")) is True

def test_oysters_plural_passes():
    assert oyster_filter.is_oyster_candidate(_evt(name="Oysters at Lincoln Tavern")) is True

def test_raw_bar_passes():
    assert oyster_filter.is_oyster_candidate(_evt(description="Raw Bar Happy Hour all night")) is True

def test_shuck_passes():
    assert oyster_filter.is_oyster_candidate(_evt(name="Shuck & Sip Thursday")) is True

def test_buck_a_shuck_passes():
    assert oyster_filter.is_oyster_candidate(_evt(name="DOLLAR OYSTERS BUCK A SHUCK TRADESMAN CHARLESTOWN")) is True

# secondary keyword positives
def test_bivalves_passes():
    assert oyster_filter.is_oyster_candidate(_evt(description="bivalves tasting night")) is True

def test_wellfleet_passes():
    assert oyster_filter.is_oyster_candidate(_evt(name="Wellfleets $1 Monday")) is True

def test_duxbury_passes():
    assert oyster_filter.is_oyster_candidate(_evt(description="$1 Duxbury oysters 5-6pm")) is True

def test_shellfish_happy_hour_passes():
    assert oyster_filter.is_oyster_candidate(_evt(name="Shellfish Happy Hour at Island Creek")) is True

# negatives
def test_everett_happy_hour_fails():
    assert oyster_filter.is_oyster_candidate(_evt(name="Everett Happy Hour", description="")) is False

def test_wine_tasting_fails():
    assert oyster_filter.is_oyster_candidate(_evt(name="Wine Tasting", description="")) is False

def test_bare_happy_hour_fails():
    assert oyster_filter.is_oyster_candidate(_evt(name="Happy Hour", description="")) is False

def test_dollar_beer_fails():
    assert oyster_filter.is_oyster_candidate(_evt(name="$1 Beer Tuesday", description="")) is False

# deliberate passthrough (acknowledged false positive — verify step drops it)
def test_oyster_mushroom_passes_but_verify_will_drop():
    """The word 'oyster' in 'oyster mushroom' passes this filter by design;
    the verify step's price extractor near oyster-food context will drop it."""
    assert oyster_filter.is_oyster_candidate(_evt(name="Oyster Mushroom Workshop")) is True

# case insensitive
def test_case_insensitive():
    assert oyster_filter.is_oyster_candidate(_evt(name="oYsTeR FeSt")) is True
