"""Create a manual activity in intervals.icu (e.g. a session recorded without the watch).

Env: INTERVALS_API_KEY, INTERVALS_ATHLETE_ID
Usage: python scripts/add_manual_activity.py --start 2026-11-02T12:00:00 --type Swim --minutes 44 \
           --distance-m 2500 --name "Swim (no watch)" [--description ...] [--load 50] [--rpe 4]
Writes the result to data/manual_activities.log (committed by the workflow).
"""
import argparse
import base64
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
from common import DATA  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--start", required=True, help="local start, YYYY-MM-DDTHH:MM:SS")
ap.add_argument("--type", required=True)
ap.add_argument("--minutes", type=float, required=True)
ap.add_argument("--distance-m", type=float, default=0)
ap.add_argument("--name", required=True)
ap.add_argument("--description", default="")
ap.add_argument("--load", type=float)
ap.add_argument("--rpe", type=int)
a = ap.parse_args()

body = {"start_date_local": a.start, "type": a.type, "name": a.name, "description": a.description,
        "moving_time": int(round(a.minutes * 60)), "elapsed_time": int(round(a.minutes * 60))}
if a.distance_m:
    body["distance"] = a.distance_m
if a.load is not None:
    body["icu_training_load"] = a.load
if a.rpe:
    body["icu_rpe"] = a.rpe

key, ath = os.environ["INTERVALS_API_KEY"], os.environ["INTERVALS_ATHLETE_ID"]
req = urllib.request.Request(
    f"https://intervals.icu/api/v1/athlete/{ath}/activities/manual", data=json.dumps(body).encode(), method="POST",
    headers={"Authorization": "Basic " + base64.b64encode(f"API_KEY:{key}".encode()).decode(),
             "Content-Type": "application/json", "Accept": "application/json",
             "User-Agent": "ironman-cairns-2027-sync/1.0 (+https://github.com/amizuno92/ironman-cairns-2027)"})
stamp = dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        res = json.loads(r.read().decode() or "{}")
        line = {"at": stamp, "ok": True, "id": res.get("id"), "request": body}
        ok = True
except urllib.error.HTTPError as e:
    line = {"at": stamp, "ok": False, "status": e.code, "error": e.read()[:300].decode(errors="replace"), "request": body}
    ok = False
with open(DATA / "manual_activities.log", "a") as f:
    f.write(json.dumps(line) + "\n")
print(json.dumps(line))
sys.exit(0 if ok else 1)
