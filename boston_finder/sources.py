"""
SOURCE REGISTRY
───────────────
Add a source here once — all programs that share a tag will use it.
Same source list for all personas — scoring prompt handles what's relevant for each person.

Tags:
  "events"  — daily event finder
  "food"    — oyster/food deals finder
  "civic"   — public records, open meeting law alerts

Types:
  "eventbrite_search"   — searches Eventbrite by keyword in Boston (web scrape, blocked)
  "eventbrite_api"      — searches Eventbrite via v3 REST API (EVENTBRITE_TOKEN in Keychain)
  "do617_category"      — scrapes a do617.com category page by date
  "scrape_url"          — fetches a URL, AI extracts events from text
  "allevents_category"  — parses allevents.in/boston/<path> via JSON-LD
  "luma"                — parses lu.ma/<slug> via __NEXT_DATA__ JSON
  "ticketmaster"        — Ticketmaster Discovery API (TICKETMASTER_API_KEY required)
  "jsonld_url"          — fetches a URL, extracts schema.org Event/MusicEvent JSON-LD (no AI, no tokens)
  "microdata_url"       — fetches a URL, extracts schema.org Event microdata/itemprop (no AI, no tokens)
  "instagram"           — fetches recent posts from a public IG profile via headless browser (no login needed)
  "meetup"              — queries Meetup GraphQL API by category (no auth needed)

To add a source: copy any entry below, set enabled: True.
"""

SOURCES = [
    # ── Eventbrite: food & drink ───────────────────────────────────────────────
    {"name": "Eventbrite: oyster",               "type": "eventbrite_search", "term": "oyster",               "tags": ["events", "food"], "enabled": False},  # Eventbrite blocks scraping (405 Human Verification) — disabled until fixed
    {"name": "Eventbrite: happy hour",           "type": "eventbrite_search", "term": "happy+hour",           "tags": ["events", "food"], "enabled": False},
    {"name": "Eventbrite: wine dinner",          "type": "eventbrite_search", "term": "wine+dinner",          "tags": ["events", "food"], "enabled": False},
    {"name": "Eventbrite: tasting",              "type": "eventbrite_search", "term": "tasting",              "tags": ["events", "food"], "enabled": False},
    {"name": "Eventbrite: cocktail",             "type": "eventbrite_search", "term": "cocktail",             "tags": ["events", "food"], "enabled": False},
    {"name": "Eventbrite: food festival",        "type": "eventbrite_search", "term": "food+festival",        "tags": ["events", "food"], "enabled": False},
    {"name": "Eventbrite: chef",                 "type": "eventbrite_search", "term": "chef",                 "tags": ["events", "food"], "enabled": False},
    {"name": "Eventbrite: brunch",               "type": "eventbrite_search", "term": "brunch",               "tags": ["events", "food"], "enabled": False},

    # ── Eventbrite: upscale social ────────────────────────────────────────────
    {"name": "Eventbrite: gala",                 "type": "eventbrite_search", "term": "gala",                 "tags": ["events"],         "enabled": True},
    {"name": "Eventbrite: fundraiser",           "type": "eventbrite_search", "term": "fundraiser",           "tags": ["events"],         "enabled": False},
    {"name": "Eventbrite: charity benefit",      "type": "eventbrite_search", "term": "charity+benefit",      "tags": ["events"],         "enabled": False},
    {"name": "Eventbrite: benefit dinner",       "type": "eventbrite_search", "term": "benefit+dinner",       "tags": ["events"],         "enabled": False},
    {"name": "Eventbrite: reception",            "type": "eventbrite_search", "term": "reception",            "tags": ["events"],         "enabled": True},
    {"name": "Eventbrite: award ceremony",       "type": "eventbrite_search", "term": "award+ceremony",       "tags": ["events"],         "enabled": False},
    {"name": "Eventbrite: auction",              "type": "eventbrite_search", "term": "auction",              "tags": ["events"],         "enabled": False},
    {"name": "Eventbrite: networking reception", "type": "eventbrite_search", "term": "networking+reception", "tags": ["events"],         "enabled": False},
    {"name": "Eventbrite: launch party",         "type": "eventbrite_search", "term": "launch+party",         "tags": ["events"],         "enabled": True},
    {"name": "Eventbrite: rooftop",              "type": "eventbrite_search", "term": "rooftop",              "tags": ["events"],         "enabled": False},
    {"name": "Eventbrite: vip",                  "type": "eventbrite_search", "term": "vip",                  "tags": ["events"],         "enabled": False},
    {"name": "Eventbrite: exclusive",            "type": "eventbrite_search", "term": "exclusive",            "tags": ["events"],         "enabled": False},
    {"name": "Eventbrite: boat cruise",          "type": "eventbrite_search", "term": "boat+cruise",          "tags": ["events"],         "enabled": True},
    {"name": "Eventbrite: yacht party",          "type": "eventbrite_search", "term": "yacht+party",          "tags": ["events"],         "enabled": True},
    {"name": "Eventbrite: night cruise",         "type": "eventbrite_search", "term": "night+cruise",         "tags": ["events"],         "enabled": False},
    {"name": "Eventbrite: model showcase",       "type": "eventbrite_search", "term": "model+showcase",       "tags": ["events"],         "enabled": True},
    {"name": "Eventbrite: Royale Boston",        "type": "eventbrite_search", "term": "royale+boston",         "tags": ["events"],         "enabled": True},
    {"name": "Eventbrite: VENU Boston",          "type": "eventbrite_search", "term": "venu+boston",           "tags": ["events"],         "enabled": True},
    {"name": "Eventbrite: Cactus Club Boston",   "type": "eventbrite_search", "term": "cactus+club+boston",    "tags": ["events"],         "enabled": True},

    # ── Eventbrite: arts & culture ────────────────────────────────────────────
    {"name": "Eventbrite: art opening",          "type": "eventbrite_search", "term": "art+opening",          "tags": ["events"],         "enabled": True},
    {"name": "Eventbrite: gallery opening",      "type": "eventbrite_search", "term": "gallery+opening",      "tags": ["events"],         "enabled": True},
    {"name": "Eventbrite: opening reception",    "type": "eventbrite_search", "term": "opening+reception",    "tags": ["events"],         "enabled": True},
    {"name": "Eventbrite: museum reception",     "type": "eventbrite_search", "term": "museum+reception",     "tags": ["events"],         "enabled": True},
    {"name": "Eventbrite: gallery",              "type": "eventbrite_search", "term": "gallery",              "tags": ["events"],         "enabled": False},
    {"name": "Eventbrite: fashion",              "type": "eventbrite_search", "term": "fashion",              "tags": ["events"],         "enabled": False},
    {"name": "Eventbrite: fashion show",         "type": "eventbrite_search", "term": "fashion+show",         "tags": ["events"],         "enabled": True},
    {"name": "Eventbrite: runway show",          "type": "eventbrite_search", "term": "runway+show",          "tags": ["events"],         "enabled": True},
    {"name": "Eventbrite: swimwear",             "type": "eventbrite_search", "term": "swimwear",             "tags": ["events"],         "enabled": True},
    {"name": "Eventbrite: lingerie",             "type": "eventbrite_search", "term": "lingerie",             "tags": ["events"],         "enabled": False},
    {"name": "Eventbrite: trunk show",           "type": "eventbrite_search", "term": "trunk+show",           "tags": ["events"],         "enabled": False},
    {"name": "Eventbrite: brand activation",     "type": "eventbrite_search", "term": "brand+activation",     "tags": ["events"],         "enabled": False},
    {"name": "Eventbrite: film screening",       "type": "eventbrite_search", "term": "film+screening",       "tags": ["events"],         "enabled": False},
    {"name": "Eventbrite: photography",          "type": "eventbrite_search", "term": "photography",          "tags": ["events"],         "enabled": False},
    {"name": "Eventbrite: design",               "type": "eventbrite_search", "term": "design",               "tags": ["events"],         "enabled": False},
    {"name": "Eventbrite: pop-up",               "type": "eventbrite_search", "term": "pop-up",               "tags": ["events"],         "enabled": False},

    # ── Eventbrite: civic & professional (disabled — 405 bot detection) ───────
    {"name": "Eventbrite: civic",                "type": "eventbrite_search", "term": "civic",                "tags": ["events", "civic"],"enabled": False},
    {"name": "Eventbrite: panel",                "type": "eventbrite_search", "term": "panel",                "tags": ["events", "civic"],"enabled": False},
    {"name": "Eventbrite: advocacy",             "type": "eventbrite_search", "term": "advocacy",             "tags": ["events", "civic"],"enabled": False},
    {"name": "Eventbrite: open government",      "type": "eventbrite_search", "term": "open+government",      "tags": ["events", "civic"],"enabled": False},
    {"name": "Eventbrite: public records",       "type": "eventbrite_search", "term": "public+records",       "tags": ["events", "civic"],"enabled": False},
    {"name": "Eventbrite: press",                "type": "eventbrite_search", "term": "press+event",          "tags": ["events"],         "enabled": False},
    {"name": "Eventbrite: media",                "type": "eventbrite_search", "term": "media+event",          "tags": ["events"],         "enabled": False},
    {"name": "Eventbrite: journalism",           "type": "eventbrite_search", "term": "journalism",           "tags": ["events", "civic"],"enabled": False},

    # ── Eventbrite API v3 (uses EVENTBRITE_TOKEN from Keychain — not web scraping) ─
    # NOTE: /events/search/ was shut down by Eventbrite in Dec 2019. No public search endpoint exists.
    # These are disabled until a valid alternative endpoint is confirmed.
    # Re-enable once Eventbrite account review is complete and a working endpoint is found.
    {"name": "Eventbrite API: food & drink",  "type": "eventbrite_api", "term": "food drink",       "tags": ["events", "food"], "enabled": False},
    {"name": "Eventbrite API: oyster",        "type": "eventbrite_api", "term": "oyster",            "tags": ["events", "food"], "enabled": False},
    {"name": "Eventbrite API: happy hour",    "type": "eventbrite_api", "term": "happy hour",        "tags": ["events", "food"], "enabled": False},
    {"name": "Eventbrite API: wine tasting",  "type": "eventbrite_api", "term": "wine tasting",      "tags": ["events", "food"], "enabled": False},
    {"name": "Eventbrite API: cocktail",      "type": "eventbrite_api", "term": "cocktail",          "tags": ["events", "food"], "enabled": False},
    {"name": "Eventbrite API: gala",          "type": "eventbrite_api", "term": "gala",              "tags": ["events"],         "enabled": False},
    {"name": "Eventbrite API: fundraiser",    "type": "eventbrite_api", "term": "fundraiser",        "tags": ["events"],         "enabled": False},
    {"name": "Eventbrite API: art opening",   "type": "eventbrite_api", "term": "art opening",       "tags": ["events"],         "enabled": False},
    {"name": "Eventbrite API: fashion",       "type": "eventbrite_api", "term": "fashion",           "tags": ["events"],         "enabled": False},
    {"name": "Eventbrite API: networking",    "type": "eventbrite_api", "term": "networking",        "tags": ["events", "civic"],"enabled": False},
    {"name": "Eventbrite API: panel",         "type": "eventbrite_api", "term": "panel discussion",  "tags": ["events", "civic"],"enabled": False},
    {"name": "Eventbrite API: boat cruise",   "type": "eventbrite_api", "term": "boat cruise",       "tags": ["events"],         "enabled": False},

    # ── do617 categories ──────────────────────────────────────────────────────
    {"name": "do617: Food & Drink",              "type": "do617_category",    "path": "food-drink",                    "tags": ["events", "food"], "enabled": True},
    {"name": "do617: Film/Theatre/Arts",         "type": "do617_category",    "path": "film-theatre-performing-arts",  "tags": ["events"],         "enabled": True},
    {"name": "do617: Concerts",                  "type": "do617_category",    "path": "concerts",                      "tags": ["events"],         "enabled": True},
    {"name": "do617: Comedy",                    "type": "do617_category",    "path": "comedy",                        "tags": ["events"],         "enabled": True},
    {"name": "do617: DJ/Dance Nights",           "type": "do617_category",    "path": "dj-sets-dance-nights",          "tags": ["events"],         "enabled": True},

    # ── Scrape URL: civic/arts orgs ────────────────────────────────────────────
    {"name": "ACLU MA",          "type": "scrape_url", "url": "https://www.aclum.org/en/events",                     "tags": ["events", "civic"], "enabled": True},
    {"name": "Boston Bar Assoc", "type": "scrape_url", "url": "https://www.bostonbar.org/events/",                   "tags": ["events", "civic"], "enabled": True},
    {"name": "Artsboston",       "type": "scrape_url", "url": "https://artsboston.org/events/",                      "tags": ["events"],          "enabled": True},
    {"name": "WBUR Events",      "type": "scrape_url", "url": "https://www.wbur.org/events",                         "tags": ["events", "civic"], "enabled": True},
    {"name": "MFA Boston",       "type": "scrape_url", "url": "https://www.mfa.org/programs",                        "tags": ["events"],          "enabled": True},
    {"name": "ICA Boston",       "type": "scrape_url", "url": "https://www.icaboston.org/events",                    "tags": ["events"],          "enabled": True},
    {"name": "BSO Events",       "type": "scrape_url", "url": "https://www.bso.org/events",                          "tags": ["events"],          "enabled": True},
    {"name": "Gardner Museum",   "type": "scrape_url", "url": "https://www.gardnermuseum.org/calendar",              "tags": ["events"],          "enabled": True},
    {"name": "Harvard Art Museums","type": "scrape_url","url": "https://harvardartmuseums.org/calendar",             "tags": ["events"],          "enabled": False},  # JS-rendered, no static events
    {"name": "Harvard Arts calendar","type": "scrape_url","url": "https://arts.harvard.edu/events",                  "tags": ["events"],          "enabled": True},   # Harvard Office for the Arts — performances, openings
    {"name": "Harvard Gazette events","type": "scrape_url","url": "https://news.harvard.edu/gazette/section/events-arts/","tags": ["events"],       "enabled": True},   # covers Harvard public cultural events
    {"name": "MIT List Visual Arts", "type": "scrape_url","url": "https://listart.mit.edu/events-programs",          "tags": ["events"],          "enabled": True},   # MIT contemporary art gallery
    {"name": "Boston Athenæum",  "type": "scrape_url", "url": "https://bostonathenaeum.org/calendar/",               "tags": ["events"],          "enabled": True},   # private library/gallery, member events + public
    {"name": "Cambridge Arts",   "type": "scrape_url", "url": "https://www.cambridgeartscouncil.org/events/",        "tags": ["events"],          "enabled": True},   # Cambridge Arts Council gallery + events
    {"name": "SoWa Boston",      "type": "scrape_url", "url": "https://www.sowaboston.com/events/",                  "tags": ["events"],          "enabled": True},
    {"name": "MIT Events",       "type": "scrape_url", "url": "https://events.mit.edu/",                             "tags": ["events"],          "enabled": True},
    {"name": "Harvard Kennedy School","type": "scrape_url","url": "https://www.hks.harvard.edu/events",              "tags": ["events", "civic"], "enabled": True},
    {"name": "Boston Public Library","type": "scrape_url","url": "https://www.bpl.org/events/",                      "tags": ["events"],          "enabled": True},

    # ── Scrape URL: fashion / nightlife / model events ─────────────────────────
    {"name": "Liberty Hotel events",    "type": "scrape_url", "url": "https://libertyhotel.com/liberty-affairs/fashionably-late/",  "tags": ["events"],          "enabled": True},
    {"name": "Boston Fashion Week",     "type": "scrape_url", "url": "https://www.bostonfashionweek.com/",                          "tags": ["events"],          "enabled": True},
    {"name": "Mass Fashion Week",       "type": "scrape_url", "url": "https://www.massfashionweek.com/",                            "tags": ["events"],          "enabled": True},
    {"name": "Boston Fashion Awards",   "type": "scrape_url", "url": "https://bostonfashionawards.com/",                            "tags": ["events"],          "enabled": True},
    {"name": "Booty by Brabants",       "type": "scrape_url", "url": "https://www.bootybybrabants.com/pages/events",                "tags": ["events"],          "enabled": True},
    {"name": "Harpoon Brewery events",  "type": "scrape_url", "url": "https://harpoonbrewery.com/events/",                          "tags": ["events", "food"],  "enabled": True},
    {"name": "Boston En Vogue",         "type": "scrape_url", "url": "https://www.eventbrite.com/o/boston-en-vogue-2309710585",     "tags": ["events"],          "enabled": True},
    {"name": "Boston Calendar",         "type": "microdata_url", "url": "https://www.thebostoncalendar.com/events",                 "tags": ["events"],          "enabled": True},

    # ── Nightlife venues / boat cruises (JS-rendered — use Eventbrite search terms instead) ──
    {"name": "Royale Boston",           "type": "scrape_url", "url": "https://royaleboston.com/events/",                            "tags": ["events"],          "enabled": True},
    {"name": "VENU Boston",             "type": "scrape_url", "url": "https://www.venuboston.com/events/",                          "tags": ["events"],          "enabled": True},
    {"name": "Cactus Club Boston",      "type": "scrape_url", "url": "https://www.cactusclubcafe.com/locations/boston-back-bay/",   "tags": ["events", "food"],  "enabled": True},   # new upscale bar 500 Boylston Back Bay
    {"name": "Boston Harbor Cruises",   "type": "scrape_url", "url": "https://www.bostonharborcruises.com/entertainment-cruises/", "tags": ["events"],          "enabled": True},
    {"name": "Mass Bay Lines",          "type": "scrape_url", "url": "https://www.massbaylines.com/calendar/",                      "tags": ["events"],          "enabled": True},
    {"name": "Boston Harbor Distillery","type": "scrape_url", "url": "https://bostonharbordistillery.com/events/",                  "tags": ["events", "food"],  "enabled": True},   # SwimBoston venue
    {"name": "Lolita Cocina events",    "type": "scrape_url", "url": "https://www.lolitacocina.com/events",                         "tags": ["events", "food"],  "enabled": True},
    {"name": "6ONE7 Productions",       "type": "scrape_url", "url": "https://www.eventbrite.com/o/6one7-productions-1459894222",   "tags": ["events"],          "enabled": True},   # Eventbrite org page
    {"name": "Dope Entertainment",      "type": "scrape_url", "url": "https://www.eventbrite.com/o/dope-entertainment-18760244852", "tags": ["events"],          "enabled": True},   # VENU/ICON promoter
    {"name": "SwimBoston",              "type": "scrape_url", "url": "https://www.swimboston.com/",                                  "tags": ["events"],          "enabled": True},

    # ── Lifestyle / upscale event aggregators ─────────────────────────────────
    {"name": "Guest of a Guest Boston", "type": "scrape_url", "url": "https://guestofaguest.com/boston/events",                     "tags": ["events"],          "enabled": False},  # JS-rendered
    {"name": "Fever Boston",            "type": "scrape_url", "url": "https://feverup.com/boston/experiences",                      "tags": ["events"],          "enabled": False},  # JS-rendered
    {"name": "Boston.com events",       "type": "scrape_url", "url": "https://www.boston.com/things-to-do/events/",                 "tags": ["events"],          "enabled": True},   # worth trying
    {"name": "Thrillist Boston",        "type": "scrape_url", "url": "https://www.thrillist.com/events/boston",                     "tags": ["events", "food"],  "enabled": True},

    # ── Meetup (GraphQL, no auth needed) ─────────────────────────────────────
    # Category IDs: 546=Tech, 292=Career/Business, 633=Science/Ed, 242=Social, 582=Arts
    {"name": "Meetup: Tech Boston",        "type": "meetup", "category_id": "546", "tags": ["events"],         "enabled": True},
    {"name": "Meetup: Career/Business",    "type": "meetup", "category_id": "292", "tags": ["events"],         "enabled": True},
    {"name": "Meetup: Science/Education",  "type": "meetup", "category_id": "633", "tags": ["events"],         "enabled": True},
    {"name": "Meetup: Social",             "type": "meetup", "category_id": "242", "tags": ["events"],         "enabled": True},
    {"name": "Meetup: Arts/Culture",       "type": "meetup", "category_id": "582", "tags": ["events"],         "enabled": True},

    # ── Instagram profiles (headless browser, no login needed for public accounts) ─
    {"name": "IG: Royale Boston",        "type": "instagram", "username": "royaleboston",       "tags": ["events"], "enabled": True},
    {"name": "IG: VENU Boston",          "type": "instagram", "username": "venuboston",          "tags": ["events"], "enabled": True},
    {"name": "IG: Cactus Club Boston",   "type": "instagram", "username": "cactusclubcafe",      "tags": ["events"], "enabled": True},
    {"name": "IG: Boston Calendar",      "type": "instagram", "username": "thebostoncal",         "tags": ["events"], "enabled": True},
    {"name": "IG: Liberty Hotel",        "type": "instagram", "username": "libertyhotelboston",   "tags": ["events"], "enabled": True},
    {"name": "IG: 6ONE7 Productions",    "type": "instagram", "username": "6one7productions",     "tags": ["events"], "enabled": True},
    # Museums & cultural venues — good for openings/receptions that aren't on event aggregators
    {"name": "IG: Harvard Art Museums",  "type": "instagram", "username": "harvardartmuseums",    "tags": ["events"], "enabled": True},
    {"name": "IG: Gardner Museum",       "type": "instagram", "username": "gardnermuseum",         "tags": ["events"], "enabled": True},
    {"name": "IG: MFA Boston",           "type": "instagram", "username": "mfaboston",             "tags": ["events"], "enabled": True},
    {"name": "IG: ICA Boston",           "type": "instagram", "username": "icaboston",             "tags": ["events"], "enabled": True},
    {"name": "IG: SoWa Boston",          "type": "instagram", "username": "sowaboston",            "tags": ["events"], "enabled": True},

    # ── lu.ma ──────────────────────────────────────────────────────────────────
    {"name": "lu.ma Boston",   "type": "luma", "slug": "boston",    "tags": ["events"], "enabled": True},
    {"name": "lu.ma Cambridge","type": "luma", "slug": "cambridge", "tags": ["events"], "enabled": True},

    # ── allevents.in Boston categories ────────────────────────────────────────
    {"name": "allevents: Food & Drink",  "type": "allevents_category", "path": "food-and-drink",  "tags": ["events", "food"], "enabled": True},
    {"name": "allevents: Arts",          "type": "allevents_category", "path": "arts",             "tags": ["events"],         "enabled": True},
    {"name": "allevents: Social",        "type": "allevents_category", "path": "social",           "tags": ["events"],         "enabled": True},
    {"name": "allevents: Business",      "type": "allevents_category", "path": "business",         "tags": ["events"],         "enabled": True},
    {"name": "allevents: Fashion",       "type": "allevents_category", "path": "fashion",          "tags": ["events"],         "enabled": True},
    {"name": "allevents: Nightlife",     "type": "allevents_category", "path": "nightlife",        "tags": ["events"],         "enabled": True},

    # ── Ticketmaster Discovery API (set TICKETMASTER_API_KEY env var) ─────────
    {"name": "Ticketmaster Boston",  "type": "ticketmaster", "tags": ["events"], "enabled": True},

    # ── JSON-LD sources (structured data, no AI extraction needed) ────────────
    {"name": "Boston Hassle",      "type": "jsonld_url", "url": "https://bostonhassle.com/calendar/",       "tags": ["events"], "enabled": True},
    {"name": "Concertful Boston",  "type": "jsonld_url", "url": "https://concertful.com/concerts/boston-ma","tags": ["events"], "enabled": True},

    # ── Additional scrape_url sources ─────────────────────────────────────────
    {"name": "Boston Magazine",    "type": "scrape_url", "url": "https://www.bostonmagazine.com/things-to-do/", "tags": ["events"], "enabled": True},
    {"name": "Resident Advisor",   "type": "scrape_url", "url": "https://ra.co/events/us/boston",   "tags": ["events"], "enabled": False},  # 403 — blocks scrapers
    {"name": "Dice.fm Boston",     "type": "scrape_url", "url": "https://dice.fm/browse/boston",    "tags": ["events"], "enabled": False},  # 404 on this path
    {"name": "TimeOut Boston",     "type": "scrape_url", "url": "https://www.timeout.com/boston/things-to-do/things-to-do-in-boston-this-weekend", "tags": ["events"], "enabled": False},  # 400

    # ── Hardware / deep tech events (for Kirk) ────────────────────────────────
    {"name": "Eventbrite: robotics Boston",    "type": "eventbrite_search", "term": "robotics+boston",       "tags": ["events"], "enabled": True},
    {"name": "Eventbrite: semiconductor",      "type": "eventbrite_search", "term": "semiconductor+boston",  "tags": ["events"], "enabled": True},
    {"name": "Eventbrite: embedded systems",   "type": "eventbrite_search", "term": "embedded+systems",      "tags": ["events"], "enabled": True},
    {"name": "Eventbrite: hardware startup",   "type": "eventbrite_search", "term": "hardware+startup",      "tags": ["events"], "enabled": True},
    {"name": "Eventbrite: machine vision",     "type": "eventbrite_search", "term": "machine+vision",        "tags": ["events"], "enabled": True},
    {"name": "Eventbrite: defense tech",       "type": "eventbrite_search", "term": "defense+tech",          "tags": ["events"], "enabled": True},
    {"name": "Eventbrite: IoT Boston",         "type": "eventbrite_search", "term": "IoT+boston",            "tags": ["events"], "enabled": True},
    {"name": "MassRobotics events",            "type": "scrape_url", "url": "https://www.massrobotics.org/events/",          "tags": ["events"], "enabled": True},
    {"name": "IEEE Boston events",             "type": "scrape_url", "url": "https://ieee-boston.org/events/",               "tags": ["events"], "enabled": True},
    {"name": "Artisan's Asylum events",        "type": "scrape_url", "url": "https://artisansasylum.com/calendar/",          "tags": ["events"], "enabled": True},
    {"name": "IG: MassRobotics",              "type": "instagram",  "username": "massrobotics",              "tags": ["events"], "enabled": True},

    # ── SoftBank / Vision Fund portfolio events (for Kirk) ────────────────────
    # SoftBank Vision Fund portfolio: Mapbox, ARM, DoorDash, Coupang, ByteDance,
    # Grab, WeWork (defunct), Compass, OpenDoor, OYO — Boston-area tech events
    {"name": "Eventbrite: SoftBank",          "type": "eventbrite_search", "term": "softbank",             "tags": ["events"], "enabled": True},
    {"name": "Eventbrite: Vision Fund",        "type": "eventbrite_search", "term": "vision+fund",          "tags": ["events"], "enabled": True},
    {"name": "Eventbrite: Mapbox",             "type": "eventbrite_search", "term": "mapbox",               "tags": ["events"], "enabled": True},
    {"name": "Eventbrite: ARM tech",           "type": "eventbrite_search", "term": "ARM+semiconductor",    "tags": ["events"], "enabled": True},
    {"name": "Eventbrite: presales SE",        "type": "eventbrite_search", "term": "presales+engineer",    "tags": ["events"], "enabled": True},
    {"name": "Eventbrite: sales engineer",     "type": "eventbrite_search", "term": "sales+engineer",       "tags": ["events"], "enabled": True},
    {"name": "Eventbrite: Pavilion",           "type": "eventbrite_search", "term": "pavilion+revenue",     "tags": ["events"], "enabled": True},
    {"name": "Eventbrite: MassChallenge",      "type": "eventbrite_search", "term": "masschallenge",        "tags": ["events"], "enabled": True},
    {"name": "Eventbrite: demo day Boston",    "type": "eventbrite_search", "term": "demo+day+boston",      "tags": ["events"], "enabled": True},
    {"name": "Eventbrite: VC Boston",          "type": "eventbrite_search", "term": "venture+capital+boston","tags": ["events"], "enabled": True},
    {"name": "MassChallenge events",           "type": "scrape_url", "url": "https://masschallenge.org/events/", "tags": ["events"], "enabled": True},
    {"name": "Greentown Labs events",          "type": "scrape_url", "url": "https://greentownlabs.com/events/", "tags": ["events"], "enabled": True},
    {"name": "Venture Lane events",            "type": "scrape_url", "url": "https://www.venturelane.co/events", "tags": ["events"], "enabled": True},
    {"name": "lu.ma Providence",              "type": "luma", "slug": "providence", "tags": ["events"], "enabled": True},

    # ── Disabled / to try ─────────────────────────────────────────────────────
    # {"name": "Island Creek Oysters", "type": "scrape_url", "url": "https://islandcreekoysters.com/pages/events", "tags": ["food"], "enabled": False},
    # {"name": "Row 34 events",        "type": "scrape_url", "url": "https://www.row34.com/events",               "tags": ["food"], "enabled": False},
    # {"name": "Eventbrite: model",    "type": "eventbrite_search", "term": "model",                              "tags": ["events"],  "enabled": False},
]


def get_sources(tag: str) -> list[dict]:
    """Return enabled sources matching a given tag."""
    return [s for s in SOURCES if s["enabled"] and tag in s.get("tags", [])]
