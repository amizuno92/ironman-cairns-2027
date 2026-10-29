"""Pull activities, intervals and wellness from intervals.icu into data/.

Env: INTERVALS_API_KEY (Settings → Developer Settings on intervals.icu)
     INTERVALS_ATHLETE_ID (e.g. i123456)
Usage: python scripts/sync_intervals.py [--days 3] [--oldest YYYY-MM-DD --newest YYYY-MM-DD]
"""
import argparse
import base64
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
from common import DATA, SPORT_MAP, load_json, save_json, today_local  # noqa: E402

API = "https://intervals.icu/api/v1"

# Keep the fields the pipeline and the reviewer use; drop chart blobs and huge arrays.
KEEP = [
    "id", "name", "type", "start_date_local", "start_date", "moving_time", "elapsed_time", "distance",
    "icu_average_watts", "icu_weighted_avg_watts", "icu_intensity", "icu_ftp", "icu_training_load",
    "average_heartrate", "max_heartrate", "average_cadence", "average_speed", "pace", "decoupling",
    "icu_efficiency_factor", "icu_variability_index", "icu_zone_times", "icu_hr_zone_times", "icu_hr_zones",
    "icu_power_zones", "pace_zone_times", "interval_summary", "icu_rpe", "feel", "session_rpe", "description",
    "device_name", "trainer", "source", "total_elevation_gain", "carbs_ingested", "carbs_used", "calories",
    "icu_ctl", "icu_atl", "icu_weight", "icu_lap_count", "polarization_index", "lthr", "athlete_max_hr",
]


def get(path, params=None):
    key = os.environ.get("INTERVALS_API_KEY")
    if not key:
        sys.exit("INTERVALS_API_KEY is not set (add it as a GitHub Actions secret).")
    url = f"{API}{path}" + ("?" + urllib.parse.urlencode(params) if params else "")
    auth = base64.b64encode(f"API_KEY:{key}".encode()).decode()
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}", "Accept": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < 2:
                time.sleep(5 * (attempt + 1))
                continue
            raise SystemExit(f"intervals.icu {e.code} on {path}: {e.read()[:200]!r}")
        except urllib.error.URLError as e:
            if attempt < 2:
                time.sleep(5)
                continue
            raise SystemExit(f"Network error on {path}: {e}")


def trim(a):
    return {k: a.get(k) for k in KEEP if a.get(k) is not None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=3, help="re-sync this many days back (catches late uploads)")
    ap.add_argument("--oldest")
    ap.add_argument("--newest")
    a = ap.parse_args()
    ath = os.environ.get("INTERVALS_ATHLETE_ID")
    if not ath:
        sys.exit("INTERVALS_ATHLETE_ID is not set (add it as a GitHub Actions secret).")
    newest = dt.date.fromisoformat(a.newest) if a.newest else today_local()
    oldest = dt.date.fromisoformat(a.oldest) if a.oldest else newest - dt.timedelta(days=a.days - 1)

    acts = get(f"/athlete/{ath}/activities", {"oldest": oldest.isoformat(), "newest": newest.isoformat()}) or []
    by_day = {}
    for act in acts:
        if act.get("_note") or not act.get("type"):  # Strava-only stubs come back without data
            continue
        t = trim(act)
        by_day.setdefault(t["start_date_local"][:10], []).append(t)
        if SPORT_MAP.get(t.get("type")) in ("Bike", "Run", "Swim"):
            ivl = get(f"/activity/{t['id']}/intervals")
            if ivl:
                save_json(DATA / "intervals" / f"{t['id']}.json", {
                    "id": t["id"],
                    "icu_intervals": [{k: v for k, v in i.items() if k in (
                        "type", "start_index", "end_index", "elapsed_time", "moving_time", "distance", "average_watts",
                        "weighted_average_watts", "average_heartrate", "max_heartrate", "average_cadence",
                        "average_speed", "group_id", "zone", "intensity", "decoupling", "label")}
                        for i in (ivl.get("icu_intervals") or [])],
                })

    d = oldest
    changed = 0
    while d <= newest:
        key = d.isoformat()
        rows = sorted(by_day.get(key, []), key=lambda x: x["start_date_local"])
        path = DATA / "activities" / f"{key}.json"
        if rows or path.exists():
            if load_json(path) != rows:
                save_json(path, rows)
                changed += 1
        d += dt.timedelta(days=1)

    wellness = get(f"/athlete/{ath}/wellness", {"oldest": oldest.isoformat(), "newest": newest.isoformat()}) or []
    for w in wellness:
        keep = {k: w.get(k) for k in ("id", "restingHR", "hrv", "hrvSDNN", "sleepSecs", "sleepScore", "sleepQuality",
                                     "weight", "ctl", "atl", "rampRate", "soreness", "fatigue", "stress", "mood",
                                     "motivation", "injury", "comments", "spO2", "steps", "vo2max") if w.get(k) is not None}
        if keep.get("id"):
            path = DATA / "wellness" / f"{keep['id']}.json"
            if load_json(path) != keep:
                save_json(path, keep)
                changed += 1
    print(f"Synced {oldest}..{newest}: {len(acts)} activities, {len(wellness)} wellness rows, {changed} files changed")


if __name__ == "__main__":
    main()
