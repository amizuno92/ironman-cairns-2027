"""Export plan/plan.py to plan/plan.json (the machine-readable plan every other script uses).

Run after any change to plan.py:  python scripts/export_plan.py
"""
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plan"))
sys.path.insert(0, str(ROOT / "scripts"))

import plan as P  # noqa: E402
from common import save_json  # noqa: E402

counter = defaultdict(int)
sessions = []
for s in P.SESSIONS:
    if s["sport"] == "Rest":
        continue
    key = (s["wk"], s["day"], s["sport"])
    counter[key] += 1
    sid = f"w{s['wk']:02d}-{s['day'].lower()}-{s['sport'].lower()}-{counter[key]}"
    sessions.append({
        "id": sid, "week": s["wk"], "date": s["date"].isoformat(), "day": s["day"], "phase": s["phase"],
        "sport": s["sport"], "title": s["title"], "when": s.get("when", ""), "duration_min": s["dur"],
        "distance_km": s["dist"], "details": s["details"], "target": s["target"], "rpe": s["rpe"],
        "fuel": s["fuel"], "high_min": s["high"],
    })

weeks = [{"week": w["n"], "start": w["start"].isoformat(), "phase": w["phase"], "kind": w["kind"], "focus": w["focus"],
          "planned_hours": round(sum(x["duration_min"] for x in sessions if x["week"] == w["n"]) / 60, 2)}
         for w in sorted(P.WEEKS.values(), key=lambda w: w["n"])]

save_json(ROOT / "plan" / "plan.json", {
    "athlete": "Andrew Mizuno", "race": "IRONMAN Cairns", "race_date": "2027-06-13",
    "ftp_w": P.FTP, "css_sec_per_100m": P.CSS, "run_lthr": P.RUN_LTHR, "bike_lthr": P.BIKE_LTHR,
    "weeks": weeks, "sessions": sessions,
})
print(f"plan.json: {len(weeks)} weeks, {len(sessions)} sessions")
