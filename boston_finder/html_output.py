"""
Generates an HTML digest of events and opens it in the browser.
Much more reliable than macOS notifications.
"""

import json
import os
import subprocess
from datetime import datetime, timedelta

OUTPUT_FILE  = os.path.expanduser("~/boston_events.html")
DEPLOY_DIR   = os.path.expanduser("~/boston_events_site")
DEPLOY_FILE  = os.path.join(DEPLOY_DIR, "index.html")

SAFE_TEST_ENV = "BOSTON_FINDER_SAFE_TEST"
DISABLE_OPEN_ENV = "BOSTON_FINDER_DISABLE_OPEN"
DISABLE_DEPLOY_ENV = "BOSTON_FINDER_DISABLE_DEPLOY"
OUTPUT_FILE_ENV = "BOSTON_FINDER_OUTPUT_FILE"


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _resolved_output_file() -> str:
    return os.environ.get(OUTPUT_FILE_ENV, OUTPUT_FILE)


def _placeholder_hits(events: list[dict]) -> list[str]:
    hits: list[str] = []
    for event in events:
        name = (event.get("name") or "").strip()
        url = (event.get("url") or "").strip().lower()
        venue = (event.get("venue") or "").strip()
        if name.startswith("Test Event"):
            hits.append(f"name={name}")
        elif "example.com/" in url:
            hits.append(f"url={event.get('url', '')}")
        elif venue == "Test Venue":
            hits.append(f"venue={venue}")
    return hits


def _cost_html() -> str:
    try:
        from boston_finder.costs import get_stats, get_recent_runs
        s = get_stats()
        runs = get_recent_runs(5)

        run_rows = ""
        for i, r in enumerate(reversed(runs)):
            ts      = datetime.fromisoformat(r["ts"]).strftime("%-m/%-d %-I:%M %p")
            cached  = r.get("events_cached", 0)
            scored  = r.get("events_scored", 0)
            cost    = r.get("cost_usd", 0.0)
            dur_s   = r.get("duration_ms", 0) / 1000
            models  = r.get("models", {})
            model_str = ", ".join(f"{m} ${c:.4f}" for m, c in models.items()) if models else "—"
            is_latest = (i == 0)
            row_style = ' style="background:#1e2a1e"' if is_latest else ""
            label = " <b style='color:#7fff7f;font-size:0.65rem'>LATEST</b>" if is_latest else ""
            run_rows += f"""
              <tr{row_style}>
                <td>{ts}{label}</td>
                <td style="color:#aaa">{cached} cached / {scored} scored</td>
                <td style="color:#aaa">{model_str}</td>
                <td style="color:#e8e8e8;font-weight:600">${cost:.4f}</td>
                <td style="color:#666">{dur_s:.1f}s</td>
              </tr>"""

        return f"""<div class="cost-bar">
          <div style="display:flex;gap:20px;margin-bottom:10px">
            <span class="cost-item">Week: <b>${s['week']['total_cost']:.4f}</b></span>
            <span class="cost-item">Month: <b>${s['month']['total_cost']:.4f}</b></span>
            <span class="cost-item">Total: <b>${s['total']['total_cost']:.4f}</b></span>
          </div>
          <table style="width:100%;border-collapse:collapse;font-size:0.75rem;color:#888">
            <thead>
              <tr style="color:#555;text-align:left;border-bottom:1px solid #222">
                <th style="padding:4px 8px 4px 0">Run</th>
                <th style="padding:4px 8px">Events</th>
                <th style="padding:4px 8px">Model</th>
                <th style="padding:4px 8px">Cost</th>
                <th style="padding:4px 8px">Time</th>
              </tr>
            </thead>
            <tbody>{run_rows}
            </tbody>
          </table>
        </div>"""
    except Exception:
        return ""


def _oyster_html(persona: str = "brian") -> str:
    try:
        from boston_finder.cache import get, age
        cache_key = f"oyster_deals_{persona}" if get(f"oyster_deals_{persona}") else "oyster_deals"
        deals = get(cache_key)
        if not deals:
            return ""
        checked = age(cache_key)
        default_hood = {
            "brian": "South End",
            "dates": "Back Bay",
            "kirk": "Cambridge",
        }.get(persona)
        deals_json = json.dumps(deals).replace("</", "<\\/")
        checked_json = json.dumps(checked)
        default_hood_json = json.dumps(default_hood)
        show_providence = "true" if persona == "kirk" else "false"
        return f"""<div class="oyster-bar" id="oyster-bar"></div>
<script>
(function() {{
  var oysterBar = document.getElementById('oyster-bar');
  if (!oysterBar) return;

  var oysters = {deals_json};
  if (!oysters.length) {{
    oysterBar.style.display = 'none';
    return;
  }}

  var checkedLabel = {checked_json};
  var currentHood = {default_hood_json};
  var showProvidence = {show_providence};
  var hidePast = true;
  var DAY_NAMES = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
  var DAY_FULL = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
  var todayDow = new Date().getDay();
  var activeDow = todayDow;
  var HOODS = ['South End','Back Bay','Cambridge','North End','Seaport','Beacon Hill','Fenway','Somerville','South Boston'];
  var HOOD_PROXIMITY = {{
    'South End':     {{'South End':10,'Back Bay':9,'Beacon Hill':8,'Downtown':8,'Financial District':8,'West End':7,'North End':7,'Fenway':7,'Kenmore':6,'Mission Hill':6,'Seaport':5,'South Boston':5,'Southie':5,'Cambridge':5,'Brookline':5,'Roxbury':5,'Somerville':4,'Charlestown':4,'Jamaica Plain':4,'Allston':3,'Brighton':3,'Dorchester':3}},
    'Back Bay':      {{'Back Bay':10,'Newbury Street':10,'South End':9,'Beacon Hill':9,'Fenway':8,'Kenmore':8,'Downtown':8,'Financial District':7,'North End':7,'West End':7,'Mission Hill':7,'Seaport':6,'Cambridge':5,'Brookline':6,'South Boston':5,'Somerville':4,'Charlestown':4,'Jamaica Plain':5,'Allston':4}},
    'Cambridge':     {{'Cambridge':10,'Somerville':8,'Charlestown':7,'North End':7,'West End':6,'Beacon Hill':6,'Downtown':6,'Financial District':6,'Back Bay':5,'South End':5,'Fenway':5,'Allston':5,'Medford':5,'Brookline':4,'Seaport':4,'South Boston':4,'Jamaica Plain':4}},
    'North End':     {{'North End':10,'West End':9,'Charlestown':8,'Beacon Hill':8,'Downtown':8,'Financial District':8,'Cambridge':6,'Back Bay':6,'Seaport':5,'South End':5,'Fenway':5,'Somerville':5}},
    'Seaport':       {{'Seaport':10,'Financial District':8,'Downtown':8,'South Boston':7,'Southie':7,'South End':6,'Back Bay':5,'North End':5,'Beacon Hill':5,'Cambridge':4,'Fenway':4}},
    'Beacon Hill':   {{'Beacon Hill':10,'West End':9,'Downtown':9,'Financial District':8,'Back Bay':8,'North End':7,'South End':7,'Cambridge':6,'Fenway':6,'Charlestown':6,'Seaport':5}},
    'Fenway':        {{'Fenway':10,'Kenmore':10,'Back Bay':8,'Brookline':7,'South End':7,'Mission Hill':8,'Allston':6,'Cambridge':5,'Beacon Hill':6,'Jamaica Plain':6,'Downtown':6}},
    'Somerville':    {{'Somerville':10,'Cambridge':8,'Medford':7,'Charlestown':7,'North End':6,'West End':5,'Beacon Hill':5,'Downtown':5,'Allston':5,'Back Bay':4,'Fenway':4,'South End':3}},
    'South Boston':  {{'South Boston':10,'Southie':10,'Seaport':8,'Financial District':6,'Downtown':6,'South End':5,'Back Bay':4,'North End':4,'Beacon Hill':4,'Cambridge':3}}
  }};

  function esc(s) {{
    return String(s || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }}

  function oysterDays(o) {{
    var desc = ((o.description || '') + ' ' + (o.reason || '')).toLowerCase();
    var name = (o.name || '').toLowerCase();
    if (/daily|every day|all week/i.test(desc + name)) return [0,1,2,3,4,5,6];
    var days = [];
    var map = {{sun:0,mon:1,tue:2,wed:3,thu:4,fri:5,sat:6,sunday:0,monday:1,tuesday:2,wednesday:3,thursday:4,friday:5,saturday:6}};
    Object.keys(map).forEach(function(k) {{
      if (desc.indexOf(k) !== -1) days.push(map[k]);
    }});
    var rangeMatch = desc.match(/([a-z]+)[–\\-]([a-z]+)/);
    if (rangeMatch) {{
      var start = map[rangeMatch[1]];
      var end = map[rangeMatch[2]];
      if (start !== undefined && end !== undefined) {{
        days = [];
        for (var d = start; d <= end; d++) days.push(d);
      }}
    }}
    return days.length ? days : [0,1,2,3,4,5,6];
  }}

  function oysterHours(o) {{
    var match = (o.description || '').match(/(\\d+(?::\\d+)?\\s*(?:AM|PM|am|pm)[^.,$]*)/i);
    return match ? match[1].trim() : '';
  }}

  function bostonHour() {{
    var fmt = new Intl.DateTimeFormat('en-US', {{timeZone: 'America/New_York', hour: 'numeric', hour12: false}});
    return parseInt(fmt.format(new Date()), 10);
  }}

  function parseEndHour24(hoursStr) {{
    if (!hoursStr) return null;
    var s = hoursStr.toLowerCase();
    var rangeMatch = s.match(/[–\\-]\\s*(\\d+)(?::\\d+)?\\s*(am|pm)/);
    if (rangeMatch) {{
      var h = parseInt(rangeMatch[1], 10);
      if (rangeMatch[2] === 'pm' && h !== 12) h += 12;
      if (rangeMatch[2] === 'am' && h === 12) h = 0;
      return h;
    }}
    var singleMatch = s.match(/(\\d+)(?::\\d+)?\\s*(am|pm)/);
    if (!singleMatch) return null;
    var singleHour = parseInt(singleMatch[1], 10);
    if (singleMatch[2] === 'pm' && singleHour !== 12) singleHour += 12;
    if (singleMatch[2] === 'am' && singleHour === 12) singleHour = 0;
    return singleHour;
  }}

  function proxScore(o) {{
    if (!currentHood) return Number(o._proximity || 3);
    var table = HOOD_PROXIMITY[currentHood] || {{}};
    var addr = ((o.address || '') + ' ' + (o.venue || '')).toLowerCase();
    var best = 3;
    Object.keys(table).forEach(function(key) {{
      if (addr.indexOf(key.toLowerCase()) !== -1) best = Math.max(best, table[key]);
    }});
    return best;
  }}

  function renderItem(o) {{
    var venueName = esc(o.venue || String(o.name || '').split('—')[0].trim());
    var badge = (o._tentative && !o._needs_review) ? ' <span class="new-badge">\U0001F195 new</span>' : '';
    var hood = esc(o.address || '');
    var hours = esc(oysterHours(o));
    var parts = String(o.name || '').split('—');
    var deal = esc(parts.length > 1 ? parts[1] : (o.reason || ''));
    var left = '<div><b>' + venueName + '</b>' + badge + (hood ? '<div class="oyster-meta">' + hood + (deal ? ' · ' + deal : '') + '</div>' : '') + '</div>';
    var right = hours ? '<span class="oyster-hours">' + hours + '</span>' : '';
    var inner = left + right;
    return o.url
      ? '<a class="oyster-item" href="' + esc(o.url) + '" target="_blank" style="text-decoration:none">' + inner + '</a>'
      : '<div class="oyster-item">' + inner + '</div>';
  }}

  function renderOysterDay(dow) {{
    var isToday = dow === todayDow;
    var currentHour = isToday ? bostonHour() : -1;
    var allBostonItems = oysters.filter(function(o) {{
      return oysterDays(o).indexOf(dow) !== -1 && (o.city || 'Boston') !== 'Providence';
    }});
    var needsReviewItems = allBostonItems.filter(function(o) {{ return !!o._needs_review; }});
    var items = allBostonItems.filter(function(o) {{ return !o._needs_review; }});
    var pvdItems = oysters.filter(function(o) {{
      return oysterDays(o).indexOf(dow) !== -1 && o.city === 'Providence';
    }});
    var pastItems = [];
    if (isToday && hidePast) {{
      var futureItems = [];
      items.forEach(function(o) {{
        var endHour = parseEndHour24(oysterHours(o));
        if (endHour !== null && endHour <= currentHour) pastItems.push(o);
        else futureItems.push(o);
      }});
      items = futureItems;
    }}

    items.sort(function(a, b) {{
      return proxScore(b) - proxScore(a);
    }});

    if (!items.length && !pastItems.length && !needsReviewItems.length) {{
      return '<div style="color:#444;font-size:0.8rem;padding:8px 0">No deals on ' + DAY_FULL[dow] + '</div>';
    }}
    if (!items.length && isToday && !needsReviewItems.length) {{
      return '<div style="color:#556;font-size:0.8rem;padding:8px 0">All deals for today have ended. ' +
        (pastItems.length ? pastItems.length + ' hidden.' : '') +
        '</div>';
    }}

    var html = '';
    if (currentHood) {{
      [
        {{label:'Nearby', min:9}},
        {{label:'Easy', min:7}},
        {{label:'Doable', min:5}},
        {{label:'Hike', min:0}}
      ].forEach(function(tier) {{
        var tierItems = items.filter(function(o) {{
          var score = proxScore(o);
          if (tier.min === 9) return score >= 9;
          if (tier.min === 7) return score >= 7 && score < 9;
          if (tier.min === 5) return score >= 5 && score < 7;
          return score < 5;
        }});
        if (!tierItems.length) return;
        html += '<div class="oyster-tier">' + tier.label + '</div>';
        html += '<div class="oyster-list" style="margin-bottom:8px">' + tierItems.map(renderItem).join('') + '</div>';
      }});
    }} else {{
      html = '<div class="oyster-list">' + items.map(renderItem).join('') + '</div>';
    }}

    html = '<div class="oyster-scroll">' + html + '</div>';
    if (isToday && pastItems.length > 0) {{
      html += '<div style="font-size:0.72rem;color:#445;margin-top:6px;padding:4px 0">' +
        pastItems.length + ' deal' + (pastItems.length > 1 ? 's' : '') +
        ' ended today — <button onclick="togglePastOysters()" style="background:none;border:none;color:#557;font-size:0.72rem;cursor:pointer;padding:0">show all</button></div>';
    }}
    if (pvdItems.length) {{
      pvdItems.sort(function(a, b) {{ return (b.score || 0) - (a.score || 0); }});
      html += '<div style="margin-top:10px;border-top:1px solid #1a2e3a;padding-top:8px">' +
        '<button onclick="toggleProvidence()" style="background:none;border:none;color:' + (showProvidence ? '#93c5fd' : '#2a4a6a') + ';font-size:0.72rem;cursor:pointer;padding:0;letter-spacing:0.04em">' +
        (showProvidence ? '▼' : '▶') + ' Providence RI (' + pvdItems.length + ' deals)</button>' +
        (showProvidence ? '<div class="oyster-list" style="margin-top:6px">' + pvdItems.map(renderItem).join('') + '</div>' : '') +
        '</div>';
    }}
    if (needsReviewItems.length) {{
      html += '<div class="needs-review-strip"><div class="nr-title">\u26a0\ufe0f Needs Review \u2014 oyster keyword found, price unclear</div>' +
        needsReviewItems.map(function(d) {{
          return '<a href="' + esc(d.url || '') + '" target="_blank">' + esc(d.venue || d.name || '') + ': ' + esc(d.description || '') + '</a>';
        }}).join('<br>') +
        '</div>';
    }}
    return html;
  }}

  function buildOyster() {{
    var tabs = '<div class="oyster-days">' + DAY_NAMES.map(function(dayName, idx) {{
      var cls = 'oday-btn' + (idx === activeDow ? ' active' : '');
      var todayMark = idx === todayDow ? ' ●' : '';
      return '<button class="' + cls + '" onclick="setOysterDay(' + idx + ')">' + dayName + todayMark + '</button>';
    }}).join('') + '</div>';

    var hoodLabel = currentHood ? "I'm near:" : 'Filter by area:';
    var hoodBtns = '<div class="oyster-location"><span>' + hoodLabel + '</span>' +
      HOODS.map(function(hood) {{
        var cls = 'ohood-btn' + (hood === currentHood ? ' active' : '');
        return '<button class="' + cls + '" onclick="setOysterHood(' + JSON.stringify(hood) + ')">' + hood + '</button>';
      }}).join('') +
      (currentHood ? ' <button class="ohood-btn" onclick="setOysterHood(null)" style="opacity:0.5">× clear</button>' : '') +
      '</div>';

    oysterBar.innerHTML =
      '<div class="oyster-title">🦪 Oyster Deals <span style="font-weight:400;color:#555;font-size:0.72rem">(last checked ' + esc(checkedLabel) + ')</span></div>' +
      tabs + hoodBtns + renderOysterDay(activeDow);
  }}

  window.setOysterDay = function(dow) {{
    activeDow = dow;
    buildOyster();
  }};
  window.setOysterHood = function(hood) {{
    currentHood = hood;
    buildOyster();
  }};
  window.togglePastOysters = function() {{
    hidePast = !hidePast;
    buildOyster();
  }};
  window.toggleProvidence = function() {{
    showProvidence = !showProvidence;
    buildOyster();
  }};

  buildOyster();
}})();
</script>"""
    except Exception:
        return ""


def _extra_events_html(today: datetime, end_date: datetime) -> str:
    """Show events scored 1-4 behind a toggle button."""
    try:
        from boston_finder.cache import get_all_scored
        scored = get_all_scored()
        low = [(url, v) for url, v in scored.items() if 1 <= v.get("score", 0) <= 4]
        if not low:
            return ""

        cards = ""
        for url, v in sorted(low, key=lambda x: -x[1].get("score", 0)):
            reason = v.get("reason", "")
            score = v.get("score", "")
            reason_html = f'<div class="reason" style="color:#555">→ {reason}</div>' if reason else ""
            name = v.get("name") or url.split("/")[-1].replace("-tickets", "").replace("-", " ").title()[:60]
            cards += f"""
            <div class="card" style="opacity:0.6">
              <div class="card-title" style="color:#888">{name} <span class="score" style="background:#333;color:#666">{score}</span></div>
              {reason_html}
              <a class="link" href="{url}" target="_blank">{url}</a>
            </div>"""

        label = f"▼ Show {len(low)} lower-priority events (scored 1–4)"
        return f"""<button class="show-more-btn" id="extra-btn" onclick="toggleExtra()" data-label="{label}">{label}</button>
        <div id="extra-events">{cards}</div>"""
    except Exception:
        return ""


GITHUB_REPO  = os.path.expanduser("~/python-projects/boston-finder-repo")
DATA_REPO    = os.path.expanduser("~/boston-finder-data")  # clone of data branch


def _git_deploy(html: str, persona: str = "brian"):
    """Write HTML to the GitHub repo's docs/ folder and push — Netlify auto-deploys from there."""
    from boston_finder.personas import PERSONAS, SITE_BASE
    p = PERSONAS.get(persona, PERSONAS["brian"])
    deploy_file = p["deploy_file"]

    docs_dir = os.path.join(GITHUB_REPO, "docs")
    if not os.path.isdir(docs_dir):
        return  # repo not set up locally — skip silently
    try:
        with open(os.path.join(docs_dir, deploy_file), "w") as f:
            f.write(html)
        subprocess.run(["git", "-C", GITHUB_REPO, "add", f"docs/{deploy_file}"], check=True)
        result = subprocess.run(
            ["git", "-C", GITHUB_REPO, "diff", "--cached", "--quiet"],
            capture_output=True
        )
        if result.returncode != 0:  # there are staged changes
            from datetime import datetime
            ts = datetime.now().strftime("%Y-%m-%d %-I:%M %p")
            label = p.get("nav_label", persona)
            subprocess.run(
                ["git", "-C", GITHUB_REPO, "commit", "-m", f"Deploy: {label} events {ts}"],
                check=True, capture_output=True
            )
            subprocess.run(["git", "-C", GITHUB_REPO, "push"], check=True, capture_output=True)
            print(f"  [deploy] → {SITE_BASE}{p['url_path']}")
        else:
            print("  [deploy] no changes to push")
    except Exception as ex:
        print(f"  [deploy] failed: {ex}")


def build_json(events: list[dict], today: datetime, days: int, persona: str = "brian") -> str:
    """Serialize events + metadata to JSON for the data branch."""
    import sys as _sys
    from collections import Counter
    from boston_finder import costs as _costs
    from boston_finder.cache import get as _cache_get, get_all_scored as _get_all_scored

    def _warn(section: str, ex: Exception):
        _sys.stderr.write(f"  [build_json] {section} fallback: {type(ex).__name__}: {ex}\n")

    # extra (low-priority) events from score cache
    try:
        all_scored = _get_all_scored()
        key_prefix = f"{persona}:"
        extra = [
            {"name": v["name"], "score": v["score"], "reason": v.get("reason", ""), "url": k[len(key_prefix):]}
            for k, v in all_scored.items()
            if k.startswith(key_prefix) and 1 <= v.get("score", 0) <= 4 and v.get("name")
        ]
        extra.sort(key=lambda x: -x["score"])
    except Exception as ex:
        _warn("extra_events", ex)
        extra = []

    # oyster deals
    try:
        oyster = _cache_get(f"oyster_deals_{persona}") or _cache_get("oyster_deals") or []
    except Exception as ex:
        _warn("oyster_deals", ex)
        oyster = []

    # cost data
    try:
        s = _costs.get_stats()
        runs = _costs.get_recent_runs(5)
        netlify_credits = _costs._netlify_credits().strip().replace("🌐 Netlify: ", "")
        cost_data = {
            "week":    round(s["week"]["total_cost"], 4),
            "month":   round(s["month"]["total_cost"], 4),
            "total":   round(s["total"]["total_cost"], 4),
            "runs":    runs,
            "netlify": netlify_credits,
        }
    except Exception as ex:
        _warn("cost_data", ex)
        cost_data = {}

    sources_shown = dict(Counter(e.get("source", "unknown").split(":")[0] for e in events))
    sources = sources_shown  # backward compat

    # source URL map for clickable pills in downstream UIs
    try:
        from boston_finder.sources import SOURCES as _SOURCES
        _src_url_map: dict[str, str] = {}
        for _s in _SOURCES:
            if not _s.get("enabled"):
                continue
            _t = _s["type"]
            if _t == "do617_category":
                _src_url_map.setdefault("do617", f"https://do617.com/events/{_s['path']}")
            elif _t == "luma":
                _src_url_map.setdefault("luma", f"https://lu.ma/{_s['slug']}")
            elif _t == "allevents_category":
                _src_url_map.setdefault("allevents", f"https://allevents.in/boston/{_s['path']}")
            elif _t == "ticketmaster":
                _src_url_map["ticketmaster"] = "https://www.ticketmaster.com/discover/concerts/boston"
            elif _t in ("scrape_url", "jsonld_url"):
                _src_url_map[_s["name"]] = _s["url"]
            elif _t == "eventbrite_api":
                _src_url_map.setdefault("eventbrite", "https://www.eventbrite.com/d/ma--boston/all-events/")
        source_url_map = _src_url_map
    except Exception as ex:
        _warn("source_url_map", ex)
        source_url_map = {}

    try:
        from boston_finder.personas import get_persona as _gp
        _p = _gp(persona)
        persona_prompt = _p.get("prompt", "")
    except Exception as ex:
        _warn("persona_prompt", ex)
        persona_prompt = ""

    # hot restaurants cache (shared across personas)
    try:
        _hr_path = os.path.expanduser("~/boston_hot_restaurants.json")
        hot_restaurants = json.load(open(_hr_path)) if os.path.exists(_hr_path) else {}
    except Exception as ex:
        _warn("hot_restaurants", ex)
        hot_restaurants = {}

    payload = {
        "generated_at":   datetime.now().isoformat(),
        "today":          today.strftime("%Y-%m-%d"),
        "days":           days,
        "persona":        persona,
        "persona_prompt": persona_prompt,
        "events": [
            {k: v for k, v in e.items() if not k.startswith("_") or k in ("_proximity",)}
            for e in events
        ],
        "extra_events":    extra[:50],
        "oyster_deals":    oyster,
        "hot_restaurants": hot_restaurants,
        "costs":           cost_data,
        "sources":         sources,
        "source_urls":     source_url_map,
        "source_stats":    sources_shown,
    }
    return json.dumps(payload, indent=2, default=str)


def _git_push_json(json_str: str, persona: str = "brian"):
    """Push persona.json to the data branch. No Netlify build triggered — zero credits.

    A failure here never aborts the HTML deploy that follows — the data branch
    is an optimization, the primary path is the docs/ push in _git_deploy().
    But we surface stderr so a reviewer skimming logs can tell when the data
    branch has drifted instead of seeing a bare "push failed".
    """
    if not os.path.isdir(DATA_REPO):
        print(f"  [data] data repo not found at {DATA_REPO} — skipping push")
        return

    data_dir = os.path.join(DATA_REPO, "data")
    fpath = os.path.join(data_dir, f"{persona}.json")

    # pull FIRST so disk reflects origin — a stale clone where somebody pushed
    # from another machine shouldn't fool the short-circuit below.
    pull = subprocess.run(
        ["git", "-C", DATA_REPO, "pull", "--ff-only", "--quiet"],
        capture_output=True, text=True,
    )
    if pull.returncode != 0:
        print(f"  [data] pull failed ({pull.returncode}); pushing anyway may fail")
        if pull.stderr.strip():
            print(f"  [data] pull stderr: {pull.stderr.strip()}")

    # Short-circuit AFTER pull: payload matches disk AND no unpushed local
    # commits waiting to go out. The ahead-check covers the scenario where a
    # prior run committed locally but the push failed.
    try:
        ahead = subprocess.run(
            ["git", "-C", DATA_REPO, "rev-list", "--count", "@{u}..HEAD"],
            capture_output=True, text=True,
        ).stdout.strip() or "0"
        if ahead == "0" and os.path.exists(fpath) and open(fpath).read() == json_str:
            print(f"  [data] {persona}.json unchanged — skipping push")
            return
    except OSError:
        pass  # unreadable file means we'll overwrite anyway

    try:
        os.makedirs(data_dir, exist_ok=True)
        with open(fpath, "w") as f:
            f.write(json_str)

        subprocess.run(["git", "-C", DATA_REPO, "add", f"data/{persona}.json"], check=True)
        diff = subprocess.run(
            ["git", "-C", DATA_REPO, "diff", "--cached", "--quiet"],
            capture_output=True,
        )
        if diff.returncode == 0:
            print(f"  [data] {persona}.json no diff after write")
            return

        ts = datetime.now().strftime("%Y-%m-%d %-I:%M %p")
        subprocess.run(
            ["git", "-C", DATA_REPO, "commit", "-m", f"data: {persona} {ts}"],
            check=True, capture_output=True,
        )
        push = subprocess.run(
            ["git", "-C", DATA_REPO, "push"],
            capture_output=True, text=True,
        )
        if push.returncode != 0:
            print(f"  [data] push failed ({push.returncode}) — HTML deploy will still run")
            if push.stderr.strip():
                print(f"  [data] push stderr: {push.stderr.strip()}")
            return
        print(f"  [data] pushed {persona}.json → data branch (0 deploy credits)")
    except subprocess.CalledProcessError as ex:
        stderr = ex.stderr.decode("utf-8", "replace").strip() if ex.stderr else ""
        print(f"  [data] git command failed: {ex.cmd} exit={ex.returncode}")
        if stderr:
            print(f"  [data] stderr: {stderr}")
    except Exception as ex:
        print(f"  [data] unexpected error: {ex!r}")


def _sources_html(events: list[dict]) -> str:
    from collections import Counter
    from html import escape as _esc
    counts = Counter(e.get("source", "unknown").split(":")[0] for e in events)
    if not counts:
        return ""
    items = "".join(
        f'<span class="src-pill">{_esc(src)} <b>{n}</b></span>'
        for src, n in counts.most_common()
    )
    return f'<div class="sources-bar">Sources: {items}</div>'


def generate(events: list[dict], today: datetime, days: int, persona: str = "brian"):
    from boston_finder.personas import PERSONAS, nav_html, active_personas
    p = PERSONAS.get(persona, PERSONAS["brian"])
    title_str = p["title"]
    accent    = p["accent"]
    nav_markup = nav_html(persona)
    active = active_personas()

    end_date = today + timedelta(days=days - 1)

    # group by date, sorted chronologically with today first
    by_date: dict[str, list] = {}
    date_order: list[str] = []
    date_key: dict[str, datetime] = {}
    for e in events:
        raw = e.get("start", "")
        try:
            if "T" in raw:
                dt = datetime.fromisoformat(raw.replace("Z", ""))
                d  = dt.strftime("%A, %B %-d")
                t  = dt.strftime("%-I:%M %p")
            else:
                dt = datetime.strptime(raw[:10], "%Y-%m-%d")
                d  = dt.strftime("%A, %B %-d")
                t  = ""
        except Exception:
            dt = datetime.max
            d, t = "Date unknown", ""
        e["_day"] = d
        e["_time"] = t
        if d not in by_date:
            date_order.append(d)
            date_key[d] = dt
        by_date.setdefault(d, []).append(e)

    date_order.sort(key=lambda d: date_key.get(d, datetime.max))

    # today label for highlighting
    today_label = today.strftime("%A, %B %-d")

    # build day filter pills
    day_pills = ""
    for i, day in enumerate(date_order):
        is_today = (day == today_label)
        short = date_key.get(day, datetime.max).strftime("%a %-m/%-d") if date_key.get(day) != datetime.max else day[:10]
        count = len(by_date[day])
        today_cls = " day-pill-today" if is_today else ""
        day_pills += f'<button class="day-pill{today_cls}" data-day="day-{i}" onclick="toggleDay(this)">{short} <span class="pill-count">{count}</span></button>'

    # build HTML
    sections = ""
    for i, day in enumerate(date_order):
        day_events = by_date[day]
        day_events.sort(key=lambda x: -x.get("score", 0))
        is_today = (day == today_label)
        cards = ""
        for e in day_events:
            score = e.get("score", "")
            time_venue = " &nbsp;|&nbsp; ".join(
                p for p in [e.get("_time"), e.get("price"), e.get("venue"), e.get("address")] if p
            )
            reason = f'<div class="reason">→ {e["reason"]}</div>' if e.get("reason") else ""
            url = e.get("url", "")
            link = f'<a class="link" href="{url}" target="_blank">{url}</a>' if url else ""
            score_badge = f'<span class="score" title="Relevance score 1-10">{score}</span>' if score else ""
            eid = url.replace("https://", "").replace("/", "_").replace(".", "_")[:40]
            safe_name = e['name'].replace("'", "")
            fb_buttons = ""
            for ap in active:
                n, lb = ap["name"], ap["nav_label"]
                fb_buttons += f"""
                <button class="fb-btn" onclick="sendFeedback(this,'{n}','up','{url}','{safe_name}')">👍 {lb}</button>"""
            for ap in active:
                n, lb = ap["name"], ap["nav_label"]
                fb_buttons += f"""
                <button class="fb-btn" onclick="sendFeedback(this,'{n}','down','{url}','{safe_name}')">👎 {lb}</button>"""
            feedback = f'<div class="feedback" id="fb_{eid}">{fb_buttons}\n            </div>' if url else ""
            cards += f"""
            <div class="card">
                <div class="card-title">{e['name']} {score_badge}</div>
                <div class="meta">{time_venue}</div>
                {reason}
                {link}
                {feedback}
            </div>"""
        today_tag = ' <span class="today-tag">TODAY</span>' if is_today else ""
        sections += f"""
        <div class="day-section" id="day-{i}">
            <div class="day-header" onclick="toggleDaySection(this)">{day}{today_tag} <span class="day-toggle">▼</span></div>
            <div class="day-cards">
            {cards}
            </div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title_str} — {today.strftime('%B %-d, %Y')}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          background: #0f0f0f; color: #e8e8e8; margin: 0; padding: 24px; }}
  h1   {{ font-size: 1.4rem; font-weight: 600; color: #fff; margin: 0 0 4px; }}
  .sub {{ color: #888; font-size: 0.85rem; margin-bottom: 28px; }}
  .day-section {{ margin-bottom: 32px; }}
  .day-header  {{ font-size: 1rem; font-weight: 700; color: {accent};
                  text-transform: uppercase; letter-spacing: 0.05em;
                  border-bottom: 1px solid #333; padding-bottom: 6px; margin-bottom: 12px; }}
  .card        {{ background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 8px;
                  padding: 14px 16px; margin-bottom: 10px; }}
  .card:hover  {{ border-color: #444; }}
  .card-title  {{ font-size: 1rem; font-weight: 600; color: #fff; margin-bottom: 4px; }}
  .score       {{ background: {accent}; color: #000; font-size: 0.7rem; font-weight: 700;
                  padding: 2px 7px; border-radius: 99px; margin-left: 8px;
                  vertical-align: middle; }}
  .meta        {{ font-size: 0.82rem; color: #888; margin-bottom: 4px; }}
  .reason      {{ font-size: 0.82rem; color: #aaa; margin: 4px 0; }}
  .link        {{ font-size: 0.78rem; color: #4a9eff; word-break: break-all;
                  text-decoration: none; }}
  .link:hover  {{ text-decoration: underline; }}
  .today-tag   {{ background: #2a6e2a; color: #7fff7f; font-size: 0.65rem; font-weight: 700;
                  padding: 2px 8px; border-radius: 99px; margin-left: 10px;
                  vertical-align: middle; letter-spacing: 0.05em; }}
  .legend      {{ background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 8px;
                  padding: 12px 16px; margin-bottom: 28px; font-size: 0.78rem; color: #888; }}
  .legend b    {{ color: {accent}; }}
  .cost-bar    {{ background: #111; border: 1px solid #222; border-radius: 8px;
                  padding: 10px 16px; margin-bottom: 20px; font-size: 0.78rem; color: #666; }}
  .cost-item   {{ margin-right: 4px; }}
  .cost-item b {{ color: #e8e8e8; }}
  .cost-sep    {{ margin: 0 8px; color: #333; }}
  .cost-models {{ margin-top: 6px; display: flex; flex-wrap: wrap; gap: 8px; }}
  .cost-model  {{ background: #1e1e1e; border: 1px solid #2a2a2a; border-radius: 4px;
                  padding: 2px 8px; font-size: 0.72rem; color: #666; }}
  .sources-bar {{ font-size: 0.75rem; color: #555; margin-bottom: 20px;
                  display: flex; flex-wrap: wrap; gap: 4px; align-items: center; }}
  .src-pill    {{ background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 4px;
                  padding: 2px 8px; }}
  .src-pill b  {{ color: #888; }}
  .footer      {{ margin-top: 40px; font-size: 0.75rem; color: #555; }}
  .oyster-bar  {{ background: #0a1a0a; border: 1px solid #1a3a1a; border-radius: 8px;
                  padding: 14px 16px; margin-bottom: 24px; }}
  .oyster-title {{ font-size: 0.9rem; font-weight: 700; color: #7fff7f; margin-bottom: 10px; }}
  .oyster-days  {{ display: flex; gap: 4px; flex-wrap: wrap; margin-bottom: 8px; }}
  .oday-btn     {{ padding: 3px 10px; border-radius: 99px; border: 1px solid #1e3a1e;
                   background: #0d200d; color: #4a8a4a; font-size: 0.72rem; cursor: pointer; }}
  .oday-btn.active {{ background: #1a3a1a; color: #7fff7f; border-color: #3a6a3a; font-weight: 700; }}
  .oyster-location {{ display: flex; align-items: center; gap: 4px; flex-wrap: wrap; margin-bottom: 12px; font-size: 0.7rem; color: #3a5a3a; }}
  .ohood-btn   {{ padding: 2px 8px; border-radius: 99px; border: 1px solid #1a2e1a;
                  background: #080f08; color: #3a6a3a; font-size: 0.7rem; cursor: pointer; }}
  .ohood-btn.active {{ background: #1a3020; color: #afffaf; border-color: #2a5a3a; font-weight: 700; }}
  .oyster-tier {{ font-size: 0.68rem; color: #3a5a3a; padding: 4px 0 2px; letter-spacing: 0.05em; text-transform: uppercase; }}
  .oyster-list {{ display: flex; flex-direction: column; gap: 6px; }}
  .oyster-item {{ display: flex; justify-content: space-between; align-items: baseline;
                  background: #0d1a0d; border: 1px solid #1a2e1a; border-radius: 6px;
                  padding: 7px 11px; font-size: 0.78rem; color: #aaa; }}
  .oyster-item b {{ color: #7fff7f; font-size: 0.82rem; }}
  .oyster-meta {{ font-size: 0.72rem; color: #556; margin-top: 2px; }}
  .oyster-hours {{ font-size: 0.75rem; color: #7fff7f; opacity: 0.7; white-space: nowrap; margin-left: 12px; }}
  .oyster-scroll {{ max-height: 300px; overflow-y: auto; padding-right: 2px; }}
  .new-badge {{ font-size: 0.65rem; color: #fff; background: #3a7; padding: 1px 5px; border-radius: 3px; margin-left: 5px; }}
  .needs-review-strip {{ margin-top: 12px; padding: 10px; background: rgba(255,180,60,0.08); border-left: 3px solid #e0a040; border-radius: 4px; font-size: 0.75rem; }}
  .needs-review-strip .nr-title {{ font-weight: 600; margin-bottom: 6px; color: #c0802d; }}
  .needs-review-strip a {{ color: #aaa; text-decoration: none; }}
  .needs-review-strip a:hover {{ color: #eee; text-decoration: underline; }}
  .show-more-btn {{ background: #1a1a1a; border: 1px solid #333; border-radius: 6px;
                    padding: 8px 16px; color: #888; font-size: 0.8rem; cursor: pointer;
                    margin-bottom: 24px; display: block; width: 100%; text-align: left; }}
  .show-more-btn:hover {{ border-color: #555; color: #ccc; }}
  #extra-events {{ display: none; }}
  .extra-label  {{ font-size: 0.72rem; color: #555; font-style: italic; margin-left: 6px; }}
  .nav          {{ display: flex; gap: 4px; margin-bottom: 20px; border-bottom: 1px solid #222; padding-bottom: 12px; }}
  .nav-link     {{ padding: 6px 16px; border-radius: 6px; font-size: 0.85rem; color: #666;
                   text-decoration: none; border: 1px solid transparent; }}
  .nav-link:hover {{ color: #aaa; border-color: #333; }}
  .nav-active   {{ padding: 6px 16px; border-radius: 6px; font-size: 0.85rem; font-weight: 600;
                   color: {accent}; border: 1px solid {accent}33; background: {accent}11;
                   text-decoration: none; }}
  .day-filter   {{ position: sticky; top: 0; z-index: 10; background: #0f0f0f;
                   padding: 10px 0 8px; display: flex; gap: 6px; flex-wrap: wrap;
                   border-bottom: 1px solid #222; margin-bottom: 16px; }}
  .day-pill     {{ background: #1a1a1a; border: 1px solid #333; border-radius: 99px;
                   padding: 5px 12px; font-size: 0.78rem; color: #aaa; cursor: pointer;
                   transition: all 0.15s; white-space: nowrap; }}
  .day-pill:hover {{ border-color: #555; color: #fff; }}
  .day-pill-today {{ border-color: #2a6e2a; }}
  .day-pill.hidden {{ background: #0f0f0f; border-color: #222; color: #444;
                      text-decoration: line-through; }}
  .pill-count   {{ font-size: 0.65rem; color: #555; margin-left: 2px; }}
  .day-toggle   {{ font-size: 0.65rem; color: #555; margin-left: 6px; cursor: pointer;
                   transition: transform 0.15s; display: inline-block; }}
  .day-section.collapsed .day-cards {{ display: none; }}
  .day-section.collapsed .day-toggle {{ transform: rotate(-90deg); }}
  .day-section.hidden-by-filter {{ display: none; }}
  .day-header   {{ cursor: pointer; user-select: none; }}
  .feedback     {{ margin-top: 8px; display: flex; gap: 6px; flex-wrap: wrap; }}
  .fb-btn       {{ background: none; border: 1px solid #2a2a2a; border-radius: 99px;
                   padding: 3px 10px; font-size: 0.7rem; color: #555; cursor: pointer; }}
  .fb-btn:hover {{ border-color: #555; color: #aaa; }}
  .fb-btn.done  {{ border-color: #444; color: #7fff7f; }}
  .fb-btn.skip  {{ border-color: #444; color: #ff7070; }}
</style>
</head>
<body>
  <nav class="nav">
    {nav_markup}
  </nav>
  <h1>{title_str}</h1>
  <div class="sub">{today.strftime('%B %-d')} – {end_date.strftime('%B %-d, %Y')} &nbsp;·&nbsp; {len(events)} events</div>
  {_cost_html()}
  {_sources_html(events)}
  {_oyster_html(persona)}
  <div class="day-filter">
    {day_pills}
  </div>
  <div class="legend">
    <b>Score 1–10</b> — how relevant this event is for you &nbsp;|&nbsp;
    <b>8–10</b> must consider &nbsp;·&nbsp;
    <b>5–7</b> worth knowing &nbsp;·&nbsp;
    <b>1–4</b> low priority
  </div>
  {sections}
  {_extra_events_html(today, end_date)}
  <!-- Netlify form (hidden) — required for Netlify to detect and activate the form -->
  <form name="event-feedback" netlify netlify-honeypot="bot-field" hidden>
    <input name="bot-field">
    <input name="persona"><input name="vote"><input name="event_url"><input name="event_name">
  </form>

  <div class="footer">Generated {datetime.now().strftime('%B %-d, %Y at %-I:%M %p')}</div>
<script>
  function toggleDay(pill) {{
    var dayId = pill.dataset.day;
    var section = document.getElementById(dayId);
    pill.classList.toggle('hidden');
    section.classList.toggle('hidden-by-filter');
  }}

  function toggleDaySection(header) {{
    header.parentElement.classList.toggle('collapsed');
  }}

  function toggleExtra() {{
    var el = document.getElementById('extra-events');
    var btn = document.getElementById('extra-btn');
    if (el.style.display === 'none' || !el.style.display) {{
      el.style.display = 'block';
      btn.textContent = '▲ Hide lower-priority events';
    }} else {{
      el.style.display = 'none';
      btn.textContent = btn.dataset.label;
    }}
  }}

  function sendFeedback(btn, persona, vote, url, name) {{
    var cls = vote === 'up' ? 'done' : 'skip';
    btn.classList.add(cls);
    btn.disabled = true;
    var body = new URLSearchParams({{
      'form-name': 'event-feedback',
      'persona': persona,
      'vote': vote,
      'event_url': url,
      'event_name': name
    }});
    fetch('https://highendeventfinder.netlify.app/', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
      body: body.toString()
    }}).catch(function() {{
      btn.classList.remove(cls);
      btn.disabled = false;
    }});
  }}
</script>
</body>
</html>"""

    output_file = _resolved_output_file()
    with open(output_file, "w") as f:
        f.write(html)

    safe_test = _env_flag(SAFE_TEST_ENV)
    disable_open = safe_test or _env_flag(DISABLE_OPEN_ENV)
    disable_deploy = safe_test or _env_flag(DISABLE_DEPLOY_ENV)

    if disable_open:
        print(f"  [open] skipped ({output_file})")
    else:
        subprocess.run(["open", output_file], check=False)

    placeholder_hits = _placeholder_hits(events)
    if placeholder_hits:
        sample = "; ".join(placeholder_hits[:3])
        print(f"  [deploy] blocked suspicious placeholder events: {sample}")
        return

    if disable_deploy:
        print("  [deploy] skipped by test mode")
        return

    _git_push_json(build_json(events, today, days, persona), persona)
    _git_deploy(html, persona=persona)
