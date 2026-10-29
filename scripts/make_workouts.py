"""Generate Zwift .zwo files (bike) and swim-set notes for a date or a whole week.

Power is written as a fraction of FTP, so Zwift scales it to whatever FTP is set in-game.
Usage: python scripts/make_workouts.py [--date YYYY-MM-DD] [--week-of YYYY-MM-DD]
       default: tomorrow (Brisbane time)
"""
import argparse
import datetime as dt
import os
import re
import sys
from xml.sax.saxutils import escape

sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, load_plan, today_local, week_start  # noqa: E402

FTP_HINT = 242  # only used in descriptions; Zwift uses its own FTP setting


def pct_band(text):
    m = re.search(r"\((\d{2,3})–(\d{2,3})% FTP\)", text)
    return (int(m.group(1)) / 100, int(m.group(2)) / 100) if m else None


def im_frac(details):
    return 0.725 if "70–75% FTP" in details else 0.685


def steps_for(s):
    """Return (steps, notes) where steps are zwo XML element strings."""
    t, d, mins = s["title"].lower(), s["details"], s["duration_min"]
    total = mins * 60
    st = []

    def ss(sec, p, cad=None):
        st.append(f'<SteadyState Duration="{int(sec)}" Power="{p:.3f}" pace="0"' + (f' Cadence="{cad}"' if cad else "") + "/>")

    def warm(sec, lo=0.45, hi=0.65):
        st.append(f'<Warmup Duration="{int(sec)}" PowerLow="{lo:.3f}" PowerHigh="{hi:.3f}" pace="0"/>')

    def cool(sec, hi=0.60, lo=0.45):
        st.append(f'<Cooldown Duration="{int(sec)}" PowerLow="{hi:.3f}" PowerHigh="{lo:.3f}" pace="0"/>')

    if "test" in t:
        return None, "Use Zwift's built-in Ramp Test (Training → Workouts → FTP Tests)."
    if "intervals" in t:
        m = re.search(r"MS (\d+)×(\d+)' @ .*?/(\d+)' easy", d)
        band = pct_band(d)
        if not m or not band:
            return None, "Couldn't parse the interval set."
        n, on, off = int(m.group(1)), int(m.group(2)) * 60, int(m.group(3)) * 60
        p = round((band[0] + band[1]) / 2, 3)
        main_set = n * (on + off)
        pre = 240                       # steady block before the set; squeezed first if time is short
        cd = 360
        spare = total - (480 + 180 + main_set + cd)
        if spare < pre:                 # long sets (e.g. 3×15'): trim the pre-block, then the cool-down
            pre = max(spare, 0)
            cd = max(min(360, total - (480 + 180 + pre + main_set)), 180)
        warm(480)
        st.append('<IntervalsT Repeat="3" OnDuration="30" OffDuration="30" OnPower="0.70" OffPower="0.55" pace="0" Cadence="105" CadenceResting="90"/>')
        if pre:
            ss(pre, 0.65)
        st.append(f'<IntervalsT Repeat="{n}" OnDuration="{on}" OffDuration="{off}" OnPower="{p:.3f}" OffPower="0.50" pace="0" Cadence="95" CadenceResting="90"/>')
        rest = total - (480 + 180 + pre + main_set + cd)
        if rest > 60:
            ss(rest, 0.65, 90)
        cool(cd)
        return st, f"{n}×{on // 60}' @ {int(p * 100)}% FTP (~{round(FTP_HINT * p)}W at {FTP_HINT}W)."
    if "recovery" in t or "spin" in t:
        warm(180, 0.40, 0.50)
        ss(max(total - 360, 300), 0.50, 95)
        cool(180, 0.50, 0.40)
        return st, "Easy spin, high cadence. Power under 55% FTP."
    if "openers" in t:
        wu = 600 if total >= 2700 else 240
        cd = 300 if total >= 2700 else 180
        st_off, sp_off = (180, 150) if total >= 2700 else (120, 90)
        warm(wu)
        st.append(f'<IntervalsT Repeat="3" OnDuration="120" OffDuration="{st_off}" OnPower="{im_frac(d):.3f}" OffPower="0.55" pace="0"/>')
        st.append(f'<IntervalsT Repeat="3" OnDuration="30" OffDuration="{sp_off}" OnPower="1.03" OffPower="0.50" pace="0" Cadence="100"/>')
        rest = total - wu - 3 * (120 + st_off) - 3 * (30 + sp_off) - cd
        if rest > 60:
            ss(rest, 0.60)
        cool(cd)
        return st, "Openers: 3×2' at IM power, 3×30s ~250W, full recovery."
    if "long ride" in t:
        imp = im_frac(d)
        warm(1200, 0.50, 0.62)
        body = total - 1200 - 600
        m_mid = re.search(r"Middle ([\d.]+)h continuous", d)
        m_blk = re.search(r"Include (\d+)×(\d+)' @ IM power", d)
        m_last = re.search(r"Last (\d+)' @ IM power", d)
        if m_mid:
            blk = int(float(m_mid.group(1)) * 3600)
            pre = (body - blk) // 2
            ss(pre, 0.66, 90); ss(blk, imp, 88); ss(body - pre - blk, 0.65, 90)
            note = f"Middle {m_mid.group(1)}h at IM power ({int(imp * 100)}% FTP)."
        elif m_blk:
            n, b = int(m_blk.group(1)), int(m_blk.group(2)) * 60
            gap = 600
            work = n * b + (n - 1) * gap
            pre = max((body - work) // 2, 300)
            ss(pre, 0.66, 90)
            for i in range(n):
                ss(b, imp, 88)
                if i < n - 1:
                    ss(gap, 0.65, 90)
            ss(max(body - pre - work, 60), 0.65, 90)
            note = f"{n}×{b // 60}' at IM power ({int(imp * 100)}% FTP), 10' Z2 between."
        elif m_last:
            b = int(m_last.group(1)) * 60
            ss(body - b, 0.66, 90); ss(b, imp, 88)
            note = f"Last {b // 60}' at IM power."
        else:
            ss(body, 0.66, 90)
            note = "Steady Z2."
        cool(600, 0.60, 0.45)
        return st, note + " Fuel from minute 20."
    if "endurance" in t or "z2" in t or "race-pace" in t:
        if "Gym bike" in s["title"] or "gym" in t:
            return None, "Gym bike: ride by HR 130–143, no Zwift file."
        imp = im_frac(d)
        warm(600, 0.50, 0.62)
        body = total - 600 - 300
        m_blk = re.search(r"Include (\d+)×(\d+)' @ IM power", d)
        if m_blk:
            n, b = int(m_blk.group(1)), int(m_blk.group(2)) * 60
            gap = max((body - n * b) // (n + 1), 120)
            for _ in range(n):
                ss(gap, 0.66, 90); ss(b, imp, 88)
            ss(max(body - n * (gap + b), 60), 0.66, 90)
            note = f"Z2 with {n}×{b // 60}' at IM power ({int(imp * 100)}% FTP)."
        else:
            ss(body, 0.67, 90)
            note = "Steady Z2 at 67% FTP."
        cool(300)
        return st, note + (" HEAT session: no fan or an extra layer; stop if HR >150." if "HEAT" in d else "")
    return None, "No Zwift file for this session type."


def zwo(s, steps, note):
    name = f"W{s['week']} {s['day']} - {s['title']}"
    desc = f"IM Cairns plan week {s['week']}. {note} Target: {s['target']}. {s['details']}"
    return ("<workout_file>\n    <author>Andrew Mizuno</author>\n"
            f"    <name>{escape(name)}</name>\n    <description>{escape(desc)}</description>\n"
            "    <sportType>bike</sportType>\n    <workout>\n        " + "\n        ".join(steps) +
            "\n    </workout>\n</workout_file>\n")


def slug(s):
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")[:40]


def build(dates):
    plan = load_plan()
    made = []
    for d in dates:
        for s in [x for x in plan["sessions"] if x["date"] == d.isoformat()]:
            if s["sport"] == "Bike":
                steps, note = steps_for(s)
                if not steps:
                    made.append((s["id"], None, note))
                    continue
                total = sum(int(m) for m in re.findall(r'Duration="(\d+)"', "".join(steps)))
                total += sum(int(r) * (int(a) + int(b)) for r, a, b in re.findall(r'Repeat="(\d+)" OnDuration="(\d+)" OffDuration="(\d+)"', "".join(steps)))
                path = ROOT / "workouts" / "zwo" / f"W{s['week']:02d}_{s['day']}_{slug(s['title'])}.zwo"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(zwo(s, steps, note))
                made.append((s["id"], str(path.relative_to(ROOT)), f"{round(total / 60)} min. {note}"))
            elif s["sport"] == "Swim":
                path = ROOT / "workouts" / "swim" / f"{s['date']}_{slug(s['title'])}.md"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f"# {s['title']} · {s['day']} {s['date']} · {s.get('when', '')}\n\n"
                                f"**Target:** {s['target']}\n\n**Set:** {s['details']}\n\n"
                                f"Duration ~{s['duration_min']}' · ~{s['distance_km']} km\n")
                made.append((s["id"], str(path.relative_to(ROOT)), "swim set"))
    return made


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--week-of")
    a = ap.parse_args()
    if a.week_of:
        ws = week_start(dt.date.fromisoformat(a.week_of))
        dates = [ws + dt.timedelta(days=i) for i in range(7)]
    else:
        dates = [dt.date.fromisoformat(a.date) if a.date else today_local() + dt.timedelta(days=1)]
    for sid, path, note in build(dates):
        print(f"{sid}: {path or '(no file)'}  {note}")


if __name__ == "__main__":
    main()
