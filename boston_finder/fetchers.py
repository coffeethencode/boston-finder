"""
Data fetchers — one function per source type.
All return the same dict shape so callers don't care about the source.
"""

import json
import time
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

EVENT_SHAPE = {
    "source": "",
    "name": "",
    "description": "",
    "url": "",
    "start": "",      # ISO date or datetime string
    "venue": "",
    "address": "",
}


def fetch_source(source: dict, start_date: datetime, end_date: datetime) -> list[dict]:
    """Route a source config entry to the right fetcher."""
    t = source["type"]
    if t == "eventbrite_search":
        return fetch_eventbrite(source["term"], start_date, end_date)
    if t == "do617_category":
        return fetch_do617_category(source["path"], start_date, end_date)
    if t == "scrape_url":
        return fetch_scrape_url(source["name"], source["url"])
    print(f"  [fetchers] unknown type: {t}")
    return []


# ── Eventbrite ─────────────────────────────────────────────────────────────────
def fetch_eventbrite(term: str, start_date: datetime, end_date: datetime) -> list[dict]:
    events = []
    seen: set[str] = set()
    url = f"https://www.eventbrite.com/d/ma--boston/{term}/"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                for item in data.get("itemListElement", []):
                    e = item.get("item", {})
                    event_url = e.get("url", "")
                    if event_url in seen:
                        continue
                    raw_start = e.get("startDate", "")
                    try:
                        edate = datetime.fromisoformat(raw_start[:10])
                        if not (start_date <= edate <= end_date):
                            continue
                    except Exception:
                        continue
                    seen.add(event_url)
                    loc = e.get("location", {})
                    addr = loc.get("address", {})
                    events.append({
                        "source": f"Eventbrite:{term}",
                        "name": e.get("name", ""),
                        "description": e.get("description", "")[:300],
                        "url": event_url,
                        "start": raw_start,
                        "venue": loc.get("name", ""),
                        "address": f"{addr.get('streetAddress', '')}, {addr.get('addressLocality', '')}".strip(", "),
                    })
            except Exception:
                continue
    except Exception as ex:
        print(f"  [eventbrite:{term}] {ex}")
    return events


# ── do617 ──────────────────────────────────────────────────────────────────────
def fetch_do617_category(path: str, start_date: datetime, end_date: datetime) -> list[dict]:
    events = []
    seen: set[str] = set()
    current = start_date
    while current <= end_date:
        url = f"https://do617.com/events/{path}/{current.year}/{current.month}/{current.day}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                for link in soup.select(f"a[href*='/events/{current.year}/']"):
                    href = link["href"]
                    if href in seen or href.endswith(("/today", "/tomorrow", "/new")):
                        continue
                    name = link.get_text(strip=True)
                    if not name or len(name) < 4:
                        continue
                    seen.add(href)
                    parent = link.find_parent("article") or link.find_parent("li") or link.parent
                    venue_el = parent.select_one(".venue, .location, [class*=venue]") if parent else None
                    time_el  = parent.select_one(".time, [class*=time]") if parent else None
                    time_suffix = ""
                    if time_el:
                        raw_time = time_el.get_text(strip=True)
                        try:
                            parsed = datetime.strptime(raw_time, "%I:%M%p")
                            time_suffix = f"T{parsed.strftime('%H:%M:%S')}"
                        except Exception:
                            pass
                    events.append({
                        "source": f"do617:{path}",
                        "name": name,
                        "description": "",
                        "url": "https://do617.com" + href if href.startswith("/") else href,
                        "start": current.strftime("%Y-%m-%d") + time_suffix,
                        "venue": venue_el.get_text(strip=True) if venue_el else "",
                        "address": "",
                    })
        except Exception as ex:
            print(f"  [do617:{path}:{current.date()}] {ex}")
        current += timedelta(days=1)
        time.sleep(0.2)
    return events


# ── Detail enrichment (time + ticket price) ────────────────────────────────────
def enrich_events(events: list[dict]) -> list[dict]:
    """
    For events missing start-time or price, fetch their detail page.
    Results are cached so each URL is only fetched once.
    Modifies events in-place; returns the same list.
    """
    from . import cache as _cache
    needs = [e for e in events if not e.get("price") and e.get("url")]
    for e in needs:
        url = e["url"]
        cached = _cache.get(f"enrich:{url}")
        if cached:
            if cached.get("time") and "T" not in e.get("start", ""):
                e["start"] = e["start"].split("T")[0] + "T" + cached["time"]
            if cached.get("price"):
                e["price"] = cached["price"]
            continue
        try:
            r = requests.get(url, headers=HEADERS, timeout=8)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, "html.parser")
            enriched: dict = {}

            if "do617.com" in url:
                t = soup.select_one(".ds-event-time")
                if t:
                    raw_time = t.get_text(strip=True).split("-")[0].strip()  # "6:00PM-9:00PM" → "6:00PM"
                    enriched["time"] = raw_time
                    if "T" not in e.get("start", ""):
                        try:
                            parsed = datetime.strptime(raw_time, "%I:%M%p")
                            e["start"] = e["start"].split("T")[0] + f"T{parsed.strftime('%H:%M:%S')}"
                        except Exception:
                            pass
            elif "eventbrite.com" in url:
                for script in soup.find_all("script", type="application/ld+json"):
                    try:
                        d = json.loads(script.string or "")
                        if isinstance(d, dict):
                            offers = d.get("offers", [])
                            if isinstance(offers, list) and offers:
                                low = offers[0].get("lowPrice", "")
                                high = offers[0].get("highPrice", "")
                                if low:
                                    enriched["price"] = f"${float(low):.0f}" if low == high else f"${float(low):.0f}–${float(high):.0f}"
                    except Exception:
                        continue

            if enriched.get("price"):
                e["price"] = enriched["price"]
            _cache.set(f"enrich:{url}", enriched, ttl_hours=72)
        except Exception as ex:
            print(f"  [enrich] {url[:60]} — {ex}")
        time.sleep(0.15)
    return events


# ── Generic URL scrape ─────────────────────────────────────────────────────────
def fetch_scrape_url(name: str, url: str) -> list[dict]:
    """Fetch a page and return its text as a single pseudo-event for AI extraction."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(separator="\n")[:4000]
        return [{
            "source": name,
            "name": f"[PAGE] {name}",
            "description": text,
            "url": url,
            "start": "",
            "venue": "",
            "address": "",
            "_raw": True,
        }]
    except Exception as ex:
        print(f"  [{name}] {ex}")
        return []
