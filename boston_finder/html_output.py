"""
Generates an HTML digest of events and opens it in the browser.
Much more reliable than macOS notifications.
"""

import os
import subprocess
from datetime import datetime, timedelta

OUTPUT_FILE  = os.path.expanduser("~/boston_events.html")
DEPLOY_DIR   = os.path.expanduser("~/boston_events_site")
DEPLOY_FILE  = os.path.join(DEPLOY_DIR, "index.html")


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


def _oyster_html() -> str:
    try:
        from boston_finder.cache import get, age
        deals = get("oyster_deals")
        if not deals:
            return ""
        checked = age("oyster_deals")
        top = sorted(deals, key=lambda x: -x.get("score", 0))[:12]
        items = ""
        for d in top:
            deal = d.get("deal", "")
            name = d.get("name", "")
            items += f'<span class="oyster-item"><b>{name}</b>{(" — " + deal) if deal else ""}</span>'
        return f"""<div class="oyster-bar">
          <div class="oyster-title">🦪 Oyster Deals <span style="font-weight:400;color:#555;font-size:0.72rem">(last checked {checked})</span></div>
          {items}
        </div>"""
    except Exception:
        return ""


def _extra_events_html(today: datetime, end_date: datetime) -> str:
    """Show events scored 1-4 behind a toggle button."""
    try:
        from boston_finder.cache import _load_scored
        import json, os
        scored = _load_scored()
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
  .footer      {{ margin-top: 40px; font-size: 0.75rem; color: #555; }}
  .oyster-bar  {{ background: #0a1a0a; border: 1px solid #1a3a1a; border-radius: 8px;
                  padding: 14px 16px; margin-bottom: 24px; }}
  .oyster-title {{ font-size: 0.9rem; font-weight: 700; color: #7fff7f; margin-bottom: 8px; }}
  .oyster-item {{ display: inline-block; background: #111; border: 1px solid #1e3a1e;
                  border-radius: 6px; padding: 4px 10px; margin: 3px; font-size: 0.75rem; color: #aaa; }}
  .oyster-item b {{ color: #7fff7f; }}
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
  {_oyster_html()}
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

    with open(OUTPUT_FILE, "w") as f:
        f.write(html)

    subprocess.run(["open", OUTPUT_FILE])
    _git_deploy(html, persona=persona)
