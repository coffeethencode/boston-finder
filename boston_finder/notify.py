"""macOS notification for daily digest."""

import subprocess
import shutil
from datetime import datetime, timedelta


def send(events: list[dict], today: datetime, title: str = "Boston Events"):
    # prefer events today or tomorrow
    highlights = []
    for e in events:
        raw = e.get("start", "")
        try:
            edate = datetime.fromisoformat(raw[:10])
            if edate.date() <= (today + timedelta(days=1)).date():
                highlights.append(e)
        except Exception:
            pass
        if len(highlights) >= 3:
            break
    if not highlights:
        highlights = events[:3]
    if not highlights:
        return

    lines = []
    for e in highlights:
        raw = e.get("start", "")
        try:
            dt = datetime.fromisoformat(raw.replace("Z", ""))
            suffix = f" ({dt.strftime('%a %-I%p')})"
        except Exception:
            suffix = ""
        lines.append(f"• {e['name']}{suffix}")

    message  = "\n".join(lines)
    subtitle = f"{len(events)} events this week"

    # use terminal-notifier if available (shows up in macOS notification settings)
    tn = shutil.which("terminal-notifier")
    if tn:
        subprocess.run([
            tn,
            "-title",    title,
            "-subtitle", subtitle,
            "-message",  message,
            "-sound",    "default",
        ], capture_output=True)
    else:
        # fallback to osascript
        script = f'display notification "{message}" with title "{title}" subtitle "{subtitle}"'
        subprocess.run(["osascript", "-e", script], capture_output=True)
