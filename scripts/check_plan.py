"""Check plan/plan.json against rules.json. Exits 1 if any hard rule is broken (used on every plan PR)."""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from common import load_plan, load_rules  # noqa: E402


def main():
    plan, r = load_plan(), load_rules()
    weeks = {w["week"]: w for w in plan["weeks"]}
    errors, warns = [], []
    hours, run_km, swims, day_min, day_swims = defaultdict(float), defaultdict(float), defaultdict(int), defaultdict(int), defaultdict(int)
    race_days = {s["date"] for s in plan["sessions"] if s["sport"] == "Race"}
    for s in plan["sessions"]:
        hours[s["week"]] += s["duration_min"] / 60
        day_min[(s["date"], s["day"])] += s["duration_min"]
        if s["sport"] == "Run":
            run_km[s["week"]] += s["distance_km"] or 0
        if s["sport"] == "Swim":
            swims[s["week"]] += 1
            day_swims[s["date"]] += 1
    prev_h = prev_km = None
    for n in sorted(weeks):
        w = weeks[n]
        if w["kind"] == "load":
            if prev_h and hours[n] > prev_h * (1 + r["weekly_hours_increase_max"]) + 0.01:
                errors.append(f"Week {n}: {hours[n]:.2f}h is >{int(r['weekly_hours_increase_max'] * 100)}% above the last load week ({prev_h:.2f}h)")
            if n > 9 and prev_km and run_km[n] > prev_km * (1 + r["weekly_run_km_increase_max"]) + 0.05:
                errors.append(f"Week {n}: run {run_km[n]:.1f} km is >10% above the last load week ({prev_km:.1f} km)")
            prev_h = hours[n]
            if n >= 9:
                prev_km = run_km[n]
        if swims[n] > r["max_swims_per_week"]:
            errors.append(f"Week {n}: {swims[n]} swims (max {r['max_swims_per_week']})")
    for (date, day), m in day_min.items():
        if date in race_days:
            continue
        cap = r["weekend_max_min"] if day in ("Sat", "Sun") else r["weekday_max_min"]
        if m > cap:
            errors.append(f"{date} ({day}): {m} min planned, limit {cap}")
    for date, n in day_swims.items():
        if n > 1:
            errors.append(f"{date}: {n} swims on one day (midday slot only)")
    peak = max(hours.values())
    if peak > 20:
        warns.append(f"Peak week {peak:.1f}h is above the 20h availability limit")
    for w in warns:
        print("WARN:", w)
    for e in errors:
        print("ERROR:", e)
    print(f"Checked {len(weeks)} weeks: {len(errors)} errors, {len(warns)} warnings. Peak {peak:.1f}h.")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
