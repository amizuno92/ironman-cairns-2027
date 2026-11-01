"""Build an interactive week board (boards/weekN.html) from plan/plan.json, using boards/week3.html as the template.

Usage: python tools/make_board.py <week number>
"""
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def js(o):
    return json.dumps(o, ensure_ascii=False)


def main():
    n = int(sys.argv[1])
    plan = json.loads((ROOT / "plan" / "plan.json").read_text())
    week = next(w for w in plan["weeks"] if w["week"] == n)
    sessions = [s for s in plan["sessions"] if s["week"] == n and s["sport"] not in ("Rest",)]
    start = dt.date.fromisoformat(week["start"])
    dates = {d: (start + dt.timedelta(days=i)) for i, d in enumerate(DAYS)}

    S, order = [], {d: [] for d in DAYS}
    long_id = -1
    for i, s in enumerate(sessions):
        t = s["title"]
        item = {"id": i, "day": s["day"], "sport": s["sport"] if s["sport"] != "Race" else "Bike",
                "when": {"Midday / any": "Midday"}.get(s.get("when", ""), s.get("when", "")),
                "title": t.replace(" — ", ": "), "dur": s["duration_min"], "details": s["details"],
                "target": s["target"], "rpe": s["rpe"], "fuel": s["fuel"] or ""}
        if s.get("distance_km"):
            item["dist"] = s["distance_km"]
        if re.search(r"Intervals|CSS|Cruise|TEST|Race-pace|RACE", t):
            item["hard"] = True
        if s["sport"] == "Strength" and "Mobility" not in t:
            item["legs"] = True
        if s["sport"] == "Run" and "Walk-run" in t:
            item["run"] = True
        if t == "Long ride":
            item["long"] = True
            long_id = i
        S.append(item)
        # list AM first, then Midday, then PM within a day
        order[s["day"]].append(i)
    rank = {"AM": 0, "Midday": 1, "Straight after ride": 2, "PM (after run)": 4, "PM": 3}
    for d in DAYS:
        order[d].sort(key=lambda i: rank.get(S[i]["when"], 2))

    tpl = (ROOT / "boards" / "week3.html").read_text()

    def sub(pattern, repl, count=1):
        nonlocal tpl
        new, k = re.subn(pattern, lambda m: repl, tpl, count=count, flags=re.S)
        if k == 0:
            sys.exit(f"template pattern not found: {pattern[:60]}")
        tpl = new

    plan_js = js(order)
    sub(r"var PLAN=\{.*?\};", f"var PLAN={plan_js};")
    sub(r'(<script type="application/json" id="state">)\{.*?\}(</script>)', '<script type="application/json" id="state">' + js({"order": order, "done": []}) + "</script>")
    sub(r"var DATES=\{.*?\};", "var DATES=" + js({d: f"{dates[d].day} {dates[d]:%b}" for d in DAYS}) + ";")
    sub(r"var ISO=\{.*?\};", "var ISO=" + js({d: dates[d].isoformat() for d in DAYS}) + ";")
    notes = {}
    for d in DAYS:
        if not order[d]:
            notes[d] = "Rest day"
    sub(r"var NOTES=\{.*?\};", "var NOTES=" + js(notes) + ";")
    sub(r"var LONG=-?\d+;", f"var LONG={long_id};")
    sub(r"var S=\[.*?\n\];", "var S=[\n " + ",\n ".join(js(x) for x in S) + "\n];")
    tpl = tpl.replace("Cairns Week 3 Board", f"Cairns Week {n} Board")
    end = dates["Sun"]
    rng = f"{dates['Mon'].day}–{end.day} {end:%B}" if dates["Mon"].month == end.month else f"{dates['Mon'].day} {dates['Mon']:%B} – {end.day} {end:%B}"
    sub(r"IRONMAN Cairns · Week 3 of 35 · Base 1</div><h1>.*?</h1>", f"IRONMAN Cairns · Week {n} of 35 · {week['phase']}</div><h1>{rng}</h1>")
    runs = sum(1 for x in S if x.get("run"))
    sub(r"3 walk-runs · alternate days", f"{runs} walk-runs · alternate days" if runs else "Running per plan")
    focus = week["focus"].replace("<", "&lt;")
    sub(r'<p class="foot">.*?</p>', f'<p class="foot">Week {n} focus: {focus} Planned {week["planned_hours"]}h. Times assume swims at midday, runs and rides in the morning, gym in the evening. Warnings show when a move breaks a rule.</p>')
    tpl = tpl.replace("w3-pending", f"w{n}-pending").replace("w3-layout", f"w{n}-layout")
    out = ROOT / "boards" / f"week{n}.html"
    out.write_text(tpl)
    print(f"{out.relative_to(ROOT)}: {len(S)} sessions, {week['planned_hours']}h")


if __name__ == "__main__":
    main()
