"""Shared helpers for the training pipeline. Standard library only."""
import datetime as dt
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN_JSON = ROOT / "plan" / "plan.json"
RULES_JSON = ROOT / "rules.json"
DATA = ROOT / "data"
TZ_OFFSET = dt.timedelta(hours=10)  # Australia/Brisbane, no DST

SPORT_MAP = {
    "Ride": "Bike", "VirtualRide": "Bike", "GravelRide": "Bike", "MountainBikeRide": "Bike", "EBikeRide": "Bike",
    "Run": "Run", "VirtualRun": "Run", "TrailRun": "Run", "Walk": "Walk",
    "Swim": "Swim", "OpenWaterSwim": "Swim",
    "WeightTraining": "Strength", "Workout": "Strength", "Crossfit": "Strength",
}


def today_local():
    return (dt.datetime.utcnow() + TZ_OFFSET).date()


def parse_date(s):
    return dt.date.fromisoformat(str(s)[:10])


def week_start(d):
    return d - dt.timedelta(days=d.weekday())


def load_json(p, default=None):
    p = Path(p)
    if not p.exists():
        return default
    with open(p) as f:
        return json.load(f)


def save_json(p, obj):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False, sort_keys=False)
        f.write("\n")


def load_plan():
    return load_json(PLAN_JSON)


def load_rules():
    return load_json(RULES_JSON, {})


def plan_sessions_on(plan, d):
    return [s for s in plan["sessions"] if s["date"] == d.isoformat()]


def plan_week_of(plan, d):
    ws = week_start(d).isoformat()
    for w in plan["weeks"]:
        if w["start"] == ws:
            return w
    return None


def activities_between(a, b):
    """All synced activities with local date in [a, b]."""
    out = []
    d = a
    while d <= b:
        out += load_json(DATA / "activities" / f"{d.isoformat()}.json", []) or []
        d += dt.timedelta(days=1)
    return out


def act_sport(a):
    return SPORT_MAP.get(a.get("type"), a.get("type") or "Other")


def act_date(a):
    return parse_date(a.get("start_date_local"))


# ---------- target parsing from plan text ----------
def power_band(text):
    m = re.search(r"(\d{2,3})–(\d{2,3})W", text or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


def hr_band(text):
    t = text or ""
    m = re.search(r"HR (\d{2,3})–(\d{2,3})", t)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    m = re.search(r"HR [<≤](\d{2,3})", t)
    if m:
        return (0, int(m.group(1)))
    m = re.search(r"hard cap (\d{2,3})", t)
    if m:
        return (0, int(m.group(1)))
    return None


def pace_band(text):
    """Swim pace band in sec/100m, e.g. 'Z2 1:42–1:48/100m' -> (102, 108)."""
    t = text or ""
    m = re.search(r"(\d):(\d\d)–(\d):(\d\d)/100m", t)
    if m:
        return (int(m.group(1)) * 60 + int(m.group(2)), int(m.group(3)) * 60 + int(m.group(4)))
    m = re.search(r"≥(\d):(\d\d)/100m", t)
    if m:
        return (int(m.group(1)) * 60 + int(m.group(2)), 999)
    return None


def planned_reps(details):
    m = re.search(r"MS (\d+)×(\d+)'", details or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


def fmt_min(sec):
    if sec is None:
        return "—"
    m = int(round(sec / 60))
    return f"{m // 60}h{m % 60:02d}" if m >= 60 else f"{m}'"


def pace_str(sec):
    if not sec:
        return "—"
    sec = int(round(sec))
    return f"{sec // 60}:{sec % 60:02d}"
