"""
API cost tracking.
Logs every API call with token counts, model, and dollar cost.
"""

import json
import os
from datetime import datetime, timedelta

COST_LOG = os.path.expanduser("~/boston_finder_costs.json")
RUN_LOG  = os.path.expanduser("~/boston_finder_runs.json")

# Pricing per million tokens by model
MODEL_PRICING = {
    "claude-haiku-4-5-20251001": {"input": 0.80,  "output": 4.00},
    "claude-haiku-4-5":          {"input": 0.80,  "output": 4.00},
    "gemini-1.5-flash":          {"input": 0.075, "output": 0.30},
    "gemini-2.0-flash":          {"input": 0.10,  "output": 0.40},
    "deepseek-chat":             {"input": 0.014, "output": 0.28},
    "default":                   {"input": 0.80,  "output": 4.00},
}


def _price(model: str) -> dict:
    for key in MODEL_PRICING:
        if key in model:
            return MODEL_PRICING[key]
    return MODEL_PRICING["default"]


def log_call(input_tokens: int, output_tokens: int, source: str = "", model: str = "claude-haiku-4-5-20251001", duration_ms: int = 0):
    """Record one API call and return its dollar cost."""
    p = _price(model)
    cost = (input_tokens / 1_000_000 * p["input"] +
            output_tokens / 1_000_000 * p["output"])
    entry = {
        "ts":            datetime.now().isoformat(),
        "source":        source,
        "model":         model,
        "input_tokens":  input_tokens,
        "output_tokens": output_tokens,
        "cost_usd":      round(cost, 6),
        "duration_ms":   duration_ms,
    }
    log = _load()
    log.append(entry)
    _save(log)
    return cost


def _summarize(entries: list) -> dict:
    by_model = {}
    for e in entries:
        m = e.get("model", "unknown")
        if m not in by_model:
            by_model[m] = {"calls": 0, "input": 0, "output": 0, "cost": 0.0}
        by_model[m]["calls"]  += 1
        by_model[m]["input"]  += e.get("input_tokens", 0)
        by_model[m]["output"] += e.get("output_tokens", 0)
        by_model[m]["cost"]   += e.get("cost_usd", 0)
    return {
        "total_cost":  round(sum(e.get("cost_usd", 0) for e in entries), 4),
        "total_calls": len(entries),
        "by_model":    {m: {**v, "cost": round(v["cost"], 4)} for m, v in by_model.items()},
    }


def get_stats() -> dict:
    log = _load()
    now = datetime.now()
    week_start = now - timedelta(days=now.weekday())

    # last run = entries in the last 2 hours
    last_run_cutoff = now - timedelta(hours=2)

    return {
        "run":   _summarize([e for e in log if datetime.fromisoformat(e["ts"]) >= last_run_cutoff]),
        "week":  _summarize([e for e in log if datetime.fromisoformat(e["ts"]) >= week_start.replace(hour=0, minute=0, second=0)]),
        "month": _summarize([e for e in log
                             if datetime.fromisoformat(e["ts"]).year == now.year
                             and datetime.fromisoformat(e["ts"]).month == now.month]),
        "total": _summarize(log),
    }


def monthly_summary() -> dict:
    return get_stats()["month"]


def print_summary():
    s = get_stats()
    runs = get_recent_runs(1)
    last_run_cost = runs[-1]["cost_usd"] if runs else 0.0
    last_run_scored = runs[-1].get("events_scored", 0) if runs else 0
    print(f"\n  💰 This run: ${last_run_cost:.4f} ({last_run_scored} scored)  |  "
          f"Week: ${s['week']['total_cost']:.4f}  |  "
          f"Month: ${s['month']['total_cost']:.4f}  |  "
          f"Total: ${s['total']['total_cost']:.4f}")


def log_run(start_ts: datetime, events_total: int, events_cached: int, events_scored: int):
    """Record a completed run summary. Call once at end of main()."""
    log = _load()
    run_entries = [e for e in log if datetime.fromisoformat(e["ts"]) >= start_ts]
    run_cost = round(sum(e["cost_usd"] for e in run_entries), 6)
    duration_ms = round(sum(e.get("duration_ms", 0) for e in run_entries))

    by_model: dict[str, float] = {}
    for e in run_entries:
        m = e.get("model", "unknown").split("/")[-1]
        by_model[m] = round(by_model.get(m, 0) + e["cost_usd"], 6)

    runs = _load_runs()
    runs.append({
        "ts":             start_ts.isoformat(),
        "events_total":   events_total,
        "events_cached":  events_cached,
        "events_scored":  events_scored,
        "cost_usd":       run_cost,
        "duration_ms":    duration_ms,
        "models":         by_model,
    })
    _save_runs(runs[-20:])  # keep last 20


def get_recent_runs(n: int = 5) -> list:
    return _load_runs()[-n:]


def _load_runs() -> list:
    if not os.path.exists(RUN_LOG):
        return []
    with open(RUN_LOG) as f:
        return json.load(f)


def _save_runs(data: list):
    with open(RUN_LOG, "w") as f:
        json.dump(data, f, indent=2)


def _load() -> list:
    if not os.path.exists(COST_LOG):
        return []
    with open(COST_LOG) as f:
        return json.load(f)


def _save(data: list):
    with open(COST_LOG, "w") as f:
        json.dump(data, f, indent=2)
