"""Planned vs actual for one day, plus week-to-date totals and flags.

Matching works across the whole plan week, so sessions you moved to another day
(e.g. on the week board) still match their planned session.

Usage: python scripts/compliance.py [--date YYYY-MM-DD]
Writes data/compliance/<date>.json
"""
import argparse
import datetime as dt
import os
import re
import statistics
import sys

sys.path.insert(0, os.path.dirname(__file__))
from common import (DATA, act_date, act_sport, activities_between, fmt_min, hr_band, load_json, load_plan,  # noqa: E402
                    load_rules, pace_band, pace_str, plan_week_of, planned_reps, power_band, save_json, today_local,
                    week_start)

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def kind(session):
    t = session["title"].lower()
    if session["sport"] == "Bike":
        if "intervals" in t:
            return "bike_intervals"
        if "test" in t:
            return "test"
        if "recovery" in t:
            return "bike_recovery"
        if "long" in t:
            return "bike_long"
        return "bike_endurance"
    if session["sport"] == "Run":
        if "walk-run" in t:
            return "walk_run"
        if "cruise" in t:
            return "run_intervals"
        if "brick" in t:
            return "brick"
        if "long" in t:
            return "run_long"
        return "run_easy"
    if session["sport"] == "Swim":
        if "css" in t:
            return "swim_css"
        if "test" in t:
            return "test"
        if "open water" in t:
            return "swim_ows"
        if "recovery" in t:
            return "swim_recovery"
        return "swim_aerobic"
    return session["sport"].lower()


def match_week(planned, actual):
    """Greedy match: same sport, prefer same day and closest duration."""
    pairs, used = {}, set()
    cand = []
    for a in actual:
        sp = act_sport(a)
        mins = (a.get("moving_time") or 0) / 60
        for p in planned:
            if p["sport"] != sp:
                continue
            dd = abs((act_date(a) - dt.date.fromisoformat(p["date"])).days)
            score = dd * 0.6 + abs(mins - p["duration_min"]) / max(p["duration_min"], 1)
            # walk-run/brick prefer short runs, long run prefers long
            cand.append((score, a["id"], p["id"]))
    for score, aid, pid in sorted(cand):
        if aid in pairs or pid in used or score > 3.0:
            continue
        pairs[aid] = pid
        used.add(pid)
    return pairs


def rep_check(a, p):
    ivl = load_json(DATA / "intervals" / f"{a['id']}.json")
    planned = planned_reps(p["details"])
    band = power_band(p["target"])
    if not ivl or not planned or not band:
        return None
    work = [i for i in ivl.get("icu_intervals", []) if i.get("type") == "WORK" and (i.get("elapsed_time") or 0) >= 30]
    reps = [{"secs": i.get("elapsed_time"), "watts": i.get("average_watts"), "hr": i.get("average_heartrate")} for i in work]
    return {"planned_reps": planned[0], "planned_rep_min": planned[1], "done_reps": len(reps), "band_w": band,
            "reps": reps, "avg_rep_w": round(statistics.mean([r["watts"] for r in reps if r["watts"]]), 1) if reps else None}


def assess(a, p, rules, plan):
    """Return metrics + flags for one matched pair."""
    k = kind(p)
    mins = (a.get("moving_time") or 0) / 60
    ratio = mins / p["duration_min"] if p["duration_min"] else None
    hr = a.get("average_heartrate") or None
    m = {"activity_id": a["id"], "name": a.get("name"), "actual_date": a["start_date_local"][:10],
         "planned_date": p["date"], "moved": a["start_date_local"][:10] != p["date"], "kind": k,
         "planned_min": p["duration_min"], "actual_min": round(mins, 1), "duration_ratio": round(ratio, 2) if ratio else None,
         "avg_hr": hr, "max_hr": a.get("max_heartrate") or None, "load": a.get("icu_training_load"),
         "rpe": a.get("icu_rpe"), "feel": a.get("feel"), "notes": a.get("description")}
    flags = []

    if ratio and ratio > 1 + rules["duration_over_pct"] and k not in ("test",):
        flags.append({"level": "warn", "code": "too_long", "msg": f"{fmt_min(mins * 60)} vs {p['duration_min']}' planned ({int(round((ratio - 1) * 100))}% over)"})
    if ratio and ratio < 1 - rules["duration_under_pct"]:
        flags.append({"level": "info", "code": "short", "msg": f"{fmt_min(mins * 60)} vs {p['duration_min']}' planned"})

    hb = hr_band(p["target"])
    if hr and hb and k not in ("bike_intervals", "run_intervals", "swim_css", "test") and hr > hb[1] + rules["hr_over_bpm"]:
        flags.append({"level": "warn", "code": "hr_high", "msg": f"avg HR {hr} above the {hb[1]} cap"})

    if p["sport"] == "Bike":
        m.update({"avg_w": a.get("icu_average_watts"), "np_w": a.get("icu_weighted_avg_watts"),
                  "if": round(a["icu_intensity"] / 100, 2) if a.get("icu_intensity") else None,
                  "decoupling_pct": round(a["decoupling"], 1) if a.get("decoupling") is not None else None,
                  "zone_secs": {z["id"]: z["secs"] for z in (a.get("icu_zone_times") or []) if isinstance(z, dict)}})
        if not hr:
            flags.append({"level": "info", "code": "no_hr", "msg": "no heart-rate data (strap not paired?)"})
        if k == "bike_intervals":
            rc = rep_check(a, p)
            m["reps"] = rc
            if rc:
                if rc["done_reps"] < rc["planned_reps"]:
                    flags.append({"level": "warn", "code": "reps_missed", "msg": f"{rc['done_reps']}/{rc['planned_reps']} reps completed"})
                if rc["avg_rep_w"] and rc["avg_rep_w"] < rc["band_w"][0] - rules["power_under_w"]:
                    flags.append({"level": "info", "code": "reps_under", "msg": f"reps averaged {rc['avg_rep_w']}W, below {rc['band_w'][0]}–{rc['band_w'][1]}W"})
                if rc["avg_rep_w"] and rc["avg_rep_w"] > rc["band_w"][1] + rules["power_over_w"]:
                    flags.append({"level": "info", "code": "reps_over", "msg": f"reps averaged {rc['avg_rep_w']}W, above {rc['band_w'][0]}–{rc['band_w'][1]}W"})
        elif k in ("bike_endurance", "bike_long", "bike_recovery"):
            band = power_band(p["target"]) or (0, 133)
            ref = m["np_w"] or m["avg_w"]
            if k == "bike_recovery":
                band = (0, 133)
            if ref and ref > band[1] + rules["power_over_w"]:
                flags.append({"level": "warn", "code": "too_hard", "msg": f"NP {ref}W above the {band[1]}W ceiling for this ride"})
            z = m["zone_secs"]
            hard = sum(z.get(x, 0) for x in ("Z4", "Z5", "Z6", "Z7"))
            if hard > 5 * 60 and k != "bike_long":
                flags.append({"level": "info", "code": "z4plus", "msg": f"{fmt_min(hard)} at Z4+ in an easy ride"})
            dc = m["decoupling_pct"]
            if dc is not None and mins >= rules["decoupling_min_duration_min"] and dc > rules["decoupling_flag_pct"]:
                flags.append({"level": "info", "code": "decoupling", "msg": f"HR/power decoupling {dc}% (aerobic durability limit)"})

    if p["sport"] == "Swim":
        dist = a.get("distance") or 0
        sec100 = (a.get("moving_time") or 0) / (dist / 100) if dist else None
        m.update({"distance_m": dist, "pace_s_per_100m": round(sec100, 1) if sec100 else None, "pace": pace_str(sec100)})
        pb = pace_band(p["target"])
        if sec100 and pb and k in ("swim_aerobic", "swim_recovery"):
            if sec100 < pb[0] - rules["swim_pace_fast_s"]:
                flags.append({"level": "info", "code": "swim_fast", "msg": f"averaged {pace_str(sec100)}/100m, faster than the {pace_str(pb[0])}–{pace_str(pb[1]) if pb[1] < 999 else ''} aerobic band"})
        if a.get("type") == "OpenWaterSwim" and k not in ("swim_ows",):
            m["note_pool_as_ows"] = "Watch logged this as open water; pace includes rests."

    if p["sport"] == "Run":
        dist = a.get("distance") or 0
        m.update({"distance_km": round(dist / 1000, 2), "pace_s_per_km": round((a.get("moving_time") or 0) / (dist / 1000), 0) if dist else None})

    text = " ".join(str(x) for x in (a.get("description"), a.get("name")) if x).lower()
    if any(re.search(rf"\b{w}", text) for w in rules["pain_words"]):
        flags.append({"level": "stop", "code": "pain_note", "msg": "your notes mention pain/soreness. Review before the next run"})
    m["flags"] = flags
    return m


def wellness_flags(day, rules):
    rows = []
    for i in range(0, 14):
        w = load_json(DATA / "wellness" / f"{(day - dt.timedelta(days=i)).isoformat()}.json")
        rows.append(w or {})
    out, info = [], {}
    rhr = [r.get("restingHR") for r in rows if r.get("restingHR")]
    hrv = [r.get("hrvSDNN") or r.get("hrv") for r in rows if (r.get("hrvSDNN") or r.get("hrv"))]
    if len(rhr) >= 5:
        base = statistics.median(rhr[2:]) if len(rhr) > 4 else statistics.median(rhr)
        recent = [r.get("restingHR") for r in rows[:rules["fatigue_days_in_row"]]]
        info["resting_hr_baseline"] = base
        info["resting_hr_recent"] = recent
        if all(x and x >= base + rules["resting_hr_rise_bpm"] for x in recent):
            out.append({"level": "warn", "code": "rhr_up", "msg": f"resting HR {recent} vs baseline {base} for {len(recent)} days"})
    if len(hrv) >= 5:
        base = statistics.median(hrv[2:])
        recent = [r.get("hrvSDNN") or r.get("hrv") for r in rows[:rules["fatigue_days_in_row"]]]
        info["hrv_baseline"] = base
        info["hrv_recent"] = recent
        if all(x and x <= base * (1 - rules["hrv_drop_pct"]) for x in recent):
            out.append({"level": "warn", "code": "hrv_down", "msg": f"HRV {recent} vs baseline {base} for {len(recent)} days"})
    today = rows[0]
    for k in ("ctl", "atl"):
        if today.get(k) is not None:
            info[k] = round(today[k], 1)
    if today.get("ctl") is not None and today.get("atl") is not None:
        info["tsb"] = round(today["ctl"] - today["atl"], 1)
    return info, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    args = ap.parse_args()
    day = dt.date.fromisoformat(args.date) if args.date else today_local()
    plan, rules = load_plan(), load_rules()
    ws = week_start(day)
    week = plan_week_of(plan, day)
    planned_week = [s for s in plan["sessions"] if ws.isoformat() <= s["date"] <= (ws + dt.timedelta(days=6)).isoformat()]
    actual_wtd = [a for a in activities_between(ws, day) if act_sport(a) in ("Bike", "Run", "Swim", "Strength")]
    pairs = match_week(planned_week, actual_wtd)
    by_pid = {p["id"]: p for p in planned_week}

    sessions = []
    for a in actual_wtd:
        if a["start_date_local"][:10] != day.isoformat():
            continue
        pid = pairs.get(a["id"])
        if pid:
            row = assess(a, by_pid[pid], rules, plan)
            row["planned_id"] = pid
            row["planned_title"] = by_pid[pid]["title"]
        else:
            row = {"activity_id": a["id"], "name": a.get("name"), "sport": act_sport(a), "unplanned": True,
                   "actual_min": round((a.get("moving_time") or 0) / 60, 1), "load": a.get("icu_training_load"),
                   "flags": [{"level": "info", "code": "unplanned", "msg": "not in the plan for this week"}]}
        row["sport"] = act_sport(a)
        sessions.append(row)

    matched = set(pairs.values())
    missed = [{"id": p["id"], "date": p["date"], "sport": p["sport"], "title": p["title"], "duration_min": p["duration_min"]}
              for p in planned_week if p["id"] not in matched and p["date"] <= day.isoformat()]
    remaining = [{"id": p["id"], "date": p["date"], "sport": p["sport"], "title": p["title"], "duration_min": p["duration_min"]}
                 for p in planned_week if p["id"] not in matched and p["date"] > day.isoformat()]

    # week-to-date totals
    def hours(rows, key):
        return round(sum(r[key] for r in rows) / 60, 2)
    act_min = {}
    for a in actual_wtd:
        act_min[act_sport(a)] = act_min.get(act_sport(a), 0) + (a.get("moving_time") or 0) / 60
    run_km = sum((a.get("distance") or 0) for a in actual_wtd if act_sport(a) == "Run") / 1000
    plan_min = {}
    for p in planned_week:
        plan_min[p["sport"]] = plan_min.get(p["sport"], 0) + p["duration_min"]
    planned_to_date = sum(p["duration_min"] for p in planned_week if p["date"] <= day.isoformat())
    swims = sum(1 for a in actual_wtd if act_sport(a) == "Swim")

    # previous week run km for the 10% cap
    prev = [a for a in activities_between(ws - dt.timedelta(days=7), ws - dt.timedelta(days=1)) if act_sport(a) == "Run"]
    prev_run_km = sum((a.get("distance") or 0) for a in prev) / 1000

    week_flags = []
    if swims > rules["max_swims_per_week"]:
        week_flags.append({"level": "info", "code": "swims", "msg": f"{swims} swims this week (max {rules['max_swims_per_week']})"})
    if week and week["week"] > rules["walk_run_until_week"] and prev_run_km > 0 and run_km > prev_run_km * (1 + rules["weekly_run_km_increase_max"]):
        week_flags.append({"level": "warn", "code": "run_km_jump", "msg": f"run {run_km:.1f} km vs {prev_run_km:.1f} km last week (>10%)"})
    run_days = sorted({act_date(a) for a in actual_wtd if act_sport(a) == "Run"})
    if week and week["week"] <= rules["walk_run_until_week"]:
        for d1, d2 in zip(run_days, run_days[1:]):
            if (d2 - d1).days == 1:
                week_flags.append({"level": "warn", "code": "runs_back_to_back", "msg": f"runs on {d1} and {d2}: walk-run phase needs a day between"})
    daily_min = {}
    for a in actual_wtd:
        daily_min[a["start_date_local"][:10]] = daily_min.get(a["start_date_local"][:10], 0) + (a.get("moving_time") or 0) / 60
    for dstr, mins in daily_min.items():
        wd = dt.date.fromisoformat(dstr).weekday()
        cap = rules["weekend_max_min"] if wd >= 5 else rules["weekday_max_min"]
        if mins > cap + 10:
            week_flags.append({"level": "info", "code": "day_over_cap", "msg": f"{dstr}: {fmt_min(mins * 60)} trained vs {cap // 60}h limit"})

    info, wflags = wellness_flags(day, rules)
    out = {
        "date": day.isoformat(), "weekday": DAYS[day.weekday()], "plan_week": week["week"] if week else None,
        "phase": week["phase"] if week else None, "week_kind": week["kind"] if week else None,
        "sessions": sessions, "missed_so_far_this_week": missed, "still_to_do_this_week": remaining,
        "week_to_date": {
            "actual_hours": round(sum(act_min.values()) / 60, 2),
            "planned_hours_to_date": round(planned_to_date / 60, 2),
            "planned_hours_week": round(sum(plan_min.values()) / 60, 2),
            "by_sport_actual_h": {k: round(v / 60, 2) for k, v in act_min.items()},
            "by_sport_planned_h": {k: round(v / 60, 2) for k, v in plan_min.items()},
            "run_km": round(run_km, 2), "prev_week_run_km": round(prev_run_km, 2), "swims": swims,
        },
        "wellness": info,
        "flags": [f for s in sessions for f in s.get("flags", [])] + week_flags + wflags,
    }
    save_json(DATA / "compliance" / f"{day.isoformat()}.json", out)
    print(f"{day}: {len(sessions)} sessions, {len(out['flags'])} flags, {len(missed)} missed so far this week")


if __name__ == "__main__":
    main()
