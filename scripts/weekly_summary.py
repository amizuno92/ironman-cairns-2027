"""Summarise a plan week (Mon–Sun): planned vs actual by sport, intensity split, load, run km, flags.

Usage: python scripts/weekly_summary.py [--week-of YYYY-MM-DD]   (default: the week containing today)
Writes data/weekly/<monday>.json
"""
import argparse
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from common import DATA, act_sport, activities_between, load_json, load_plan, load_rules, plan_week_of, save_json, today_local, week_start  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week-of")
    a = ap.parse_args()
    d = dt.date.fromisoformat(a.week_of) if a.week_of else today_local()
    ws = week_start(d)
    we = ws + dt.timedelta(days=6)
    plan, rules = load_plan(), load_rules()
    wk = plan_week_of(plan, ws)
    planned = [s for s in plan["sessions"] if ws.isoformat() <= s["date"] <= we.isoformat()]
    acts = [x for x in activities_between(ws, min(we, today_local())) if act_sport(x) in ("Bike", "Run", "Swim", "Strength", "HIIT")]

    def by_sport(rows, f):
        out = {}
        for r in rows:
            k, v = f(r)
            out[k] = round(out.get(k, 0) + v, 2)
        return out

    p_h = by_sport(planned, lambda s: (s["sport"], s["duration_min"] / 60))
    a_h = by_sport(acts, lambda x: (act_sport(x), (x.get("moving_time") or 0) / 3600))
    hr_z = [0] * 7
    for x in acts:
        for i, s in enumerate(x.get("icu_hr_zone_times") or []):
            if i < 7:
                hr_z[i] += s
    pw = {}
    for x in acts:
        for z in x.get("icu_zone_times") or []:
            if isinstance(z, dict) and z.get("id", "").startswith("Z"):
                pw[z["id"]] = pw.get(z["id"], 0) + z["secs"]
    endu_secs = sum((x.get("moving_time") or 0) for x in acts if act_sport(x) in ("Bike", "Run", "Swim"))
    hard_secs = sum(pw.get(z, 0) for z in ("Z4", "Z5", "Z6", "Z7"))
    # runs/swims don't have power zones: use HR zones 4+ for them
    for x in acts:
        if act_sport(x) in ("Run", "Swim"):
            hard_secs += sum((x.get("icu_hr_zone_times") or [0] * 7)[3:])
    run_km = sum((x.get("distance") or 0) for x in acts if act_sport(x) == "Run") / 1000
    prev = load_json(DATA / "weekly" / f"{(ws - dt.timedelta(days=7)).isoformat()}.json") or {}

    flags = []
    for i in range(7):
        c = load_json(DATA / "compliance" / f"{(ws + dt.timedelta(days=i)).isoformat()}.json")
        if c:
            flags += [dict(f, date=c["date"]) for f in c.get("flags", [])]
    last = None
    for i in range(6, -1, -1):
        last = load_json(DATA / "compliance" / f"{(ws + dt.timedelta(days=i)).isoformat()}.json")
        if last:
            break
    lifts = [p.name for p in (DATA / "lifts").glob(f"{ws.year}-*.json")
             if ws.isoformat() <= p.name[:10] <= we.isoformat()]
    tests = [load_json(p) for p in (DATA / "tests").glob("*.json") if ws.isoformat() <= p.name[:10] <= we.isoformat()]

    out = {
        "week_start": ws.isoformat(), "plan_week": wk["week"] if wk else None, "phase": wk["phase"] if wk else None,
        "kind": wk["kind"] if wk else None, "focus": wk["focus"] if wk else None,
        "planned_hours": round(sum(p_h.values()), 2), "actual_hours": round(sum(a_h.values()), 2),
        "planned_by_sport_h": p_h, "actual_by_sport_h": a_h,
        "compliance_pct": round(100 * sum(a_h.values()) / sum(p_h.values()), 0) if p_h else None,
        "sessions_planned": len(planned), "sessions_done": len(acts),
        "missed": (last or {}).get("missed_so_far_this_week", []),
        "intensity": {"endurance_hours": round(endu_secs / 3600, 2), "z4plus_min": round(hard_secs / 60),
                      "z4plus_pct": round(100 * hard_secs / endu_secs, 1) if endu_secs else None,
                      "bike_power_zone_min": {k: round(v / 60) for k, v in sorted(pw.items())},
                      "hr_zone_min": [round(s / 60) for s in hr_z]},
        "load": round(sum((x.get("icu_training_load") or 0) for x in acts)),
        "run_km": round(run_km, 2), "prev_week_run_km": prev.get("run_km"),
        "run_km_change_pct": round(100 * (run_km / prev["run_km"] - 1), 1) if prev.get("run_km") else None,
        "swims": sum(1 for x in acts if act_sport(x) == "Swim"),
        "fitness": (last or {}).get("wellness", {}),
        "lift_sessions": lifts, "tests": tests,
        "flags": flags,
        "next_week": plan_week_of(plan, ws + dt.timedelta(days=7)),
    }
    save_json(DATA / "weekly" / f"{ws.isoformat()}.json", out)
    print(f"Week {out['plan_week']} ({ws}): {out['actual_hours']}h of {out['planned_hours']}h, Z4+ {out['intensity']['z4plus_pct']}%, {len(flags)} flags")


if __name__ == "__main__":
    main()
