"""Ironman Cairns 2027 plan generator — Andrew Mizuno.
Produces SESSIONS (list of dicts) and WEEKS (meta)."""
import datetime as dt

START = dt.date(2026, 10, 12)  # Monday, week 1
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

FTP, BIKE_LTHR, RUN_LTHR, SWIM_LTHR, CSS = 259, 161, 167, 152, 90  # CSS sec/100m


def W(lo, hi):
    return f"{round(FTP*lo)}–{round(FTP*hi)}W ({int(lo*100)}–{int(hi*100)}% FTP)"


def w(p):
    return round(FTP * p)


Z2W = f"{w(.62)}–{w(.72)}W"          # Z2 band
IMW = f"{w(.66)}–{w(.71)}W"          # base IM power
IMW_SUB11 = f"{w(.70)}–{w(.75)}W"    # sub-11 IM power (from wk 15)
T100W = f"{w(.74)}–{w(.78)}W"        # T100 bike power


def pace(s):
    return f"{s//60}:{s % 60:02d}"


# ---------------- target strings ----------------
SW_Z1 = f"Z1 ≥{pace(CSS+18)}/100m · RPE 2"
SW_Z2 = f"Z2 {pace(CSS+8)}–{pace(CSS+14)}/100m (IM pace {pace(CSS+10)}) · RPE 3–4"
SW_Z4 = f"Z4 CSS {pace(CSS-2)}–{pace(CSS+2)}/100m · RPE 7"
SW_Z5 = f"Z5 ≤{pace(CSS-4)}/100m · RPE 8–9"
BK_Z1 = f"Z1 <{w(.55)}W (<55%) · HR <130 · RPE 1–2"
BK_Z2 = f"Z2 {Z2W} (62–72%) · HR 130–143 · RPE 3–4"
BK_IM = f"IM power {IMW} (66–71%) · HR ≤143 · RPE 4"
RN_Z1 = "Z1 HR ≤141 · RPE 2–3"
RN_Z2 = "Z1–Z2 HR 135–149 (hard cap 149) · RPE 3–4"
RN_Z4 = "Z4 HR 159–165 · RPE 7"

BONE = "Bone rule: pain ≤2/10 during, none next morning — else stop, 2 days off, drop back one stage."

SESSIONS, WEEKS = [], {}


def fuel_for(sport, mins):
    if sport in ("Strength", "Rest", "Swim"):
        return ""
    if mins < 75:
        return "Water/electrolytes only"
    if mins < 120:
        return "40–60 g carbs/h + electrolytes"
    return None  # set by caller for long sessions


def S(sport, title, dur, details, target, rpe, high=0, dist=None, fuel=None, note=""):
    return dict(sport=sport, title=title, dur=int(dur), details=details, target=target, rpe=rpe,
                high=int(high), dist=dist, fuel=fuel if fuel is not None else (fuel_for(sport, dur) or ""),
                note=note)


# ---------------- SWIM ----------------
def r100(x):
    return int(round(x / 100.0) * 100)


def swim_aero(mins, ph="base"):
    d = r100(mins * 50)
    main = d - 700
    n, rem = divmod(main, 400)
    tool = "pull buoy" if ph == "base" else "pull buoy + paddles"
    ms = f"{n}×400 @ {pace(CSS+8)}–{pace(CSS+14)}/100m, 20s rest (every 2nd rep with {tool})"
    if rem:
        ms += f" + {rem} steady pull"
    det = f"WU 300 easy + 4×50 build /15s. MS {ms}. CD 200 easy. All reps ≥50m (Watch-safe)."
    return S("Swim", "Aerobic endurance", mins, det, SW_Z2, "3–4", 0, d / 1000)


def P(o):  # pace at CSS + o seconds
    return pace(CSS + o)


CSS_SETS = {
    "base1": (f"{{n}}×100 @ CSS {P(-2)}–{P(2)} /15s + 4×50 @ ≤{P(-4)} /20s", 1.0),
    "base2": (f"{{n}}×100 @ CSS {P(-2)}–{P(2)} /12s + 6×50 @ ≤{P(-6)} /20s", 1.0),
    "base3": (f"5×200 @ {P(-1)}–{P(2)} /20s + {{n}}×100 @ {P(-3)}–{P(0)} /15s", 1.0),
    "build": (f"4×300 @ {P(0)}–{P(2)} /20s + {{n}}×100 @ {P(-4)}–{P(-1)} /15s", 1.0),
    "peak":  (f"2×(4×200 @ {P(-1)}–{P(1)} /20s), 100 easy between + {{n}}×50 @ ≤{P(-6)} /15s", 1.0),
    "taper": (f"6×100 @ {P(-2)}–{P(1)} /20s + 4×50 fast/easy", 1.0),
}
CSS_FIXED = {"base1": 200, "base2": 300, "base3": 1000, "build": 1200, "peak": 1700, "taper": 0}


def swim_css(mins, key):
    d = r100(mins * 47)
    fixed = CSS_FIXED[key]
    n = max(4, (d - 800 - fixed) // 100) if key != "taper" else 0
    if key == "peak":
        n = max(4, (d - 800 - fixed - 100) // 50)
    ms = CSS_SETS[key][0].format(n=n)
    det = f"WU 400 + 4×50 build /15s. MS {ms}. CD 200 easy (+200 pull if time)."
    work = (d - 600) * CSS / 100 / 60
    return S("Swim", "CSS / threshold", mins, det, f"{SW_Z4}; 50s {SW_Z5}", "7–8", work * 0.85, d / 1000)


def swim_end(mins, ph="base"):
    d = r100(mins * 50)
    if d >= 4600 and ph in ("peak",):
        ip = CSS + 10
        ck = lambda m: f"{int(m * ip / 100 // 60)}:{int(m * ip / 100 % 60):02d}"
        det = (f"WU 400 easy. MS 3800 CONTINUOUS @ IM pace {pace(ip)}/100m — clock checks: 1000 @{ck(1000)}, "
               f"2000 @{ck(2000)}, 3000 @{ck(3000)}, 3800 @{ck(3800)}. CD 200. Sight every 6th stroke (head-up) to rehearse.")
        return S("Swim", "IM-distance swim (3.8km)", mins, det, SW_Z2, "4", 0, 4.4)
    main = d - 600
    if ph == "base":
        n = main // 500
        ms = f"{n}×500 @ {pace(CSS+8)}–{pace(CSS+14)}/100m /30s" + (f" + {main-n*500} easy" if main - n*500 else "")
    else:
        n = main // 1000
        ms = f"{n}×1000 @ IM pace {P(8)}–{P(12)}/100m /30s" + (f" + {main-n*1000} pull" if main - n*1000 else "")
    det = f"WU 400 easy. MS {ms}. CD 200. Hold pace — the goal is aerobic durability, not speed."
    return S("Swim", "Long aerobic swim", mins, det, SW_Z2, "3–4", 0, d / 1000)


def swim_ows(mins):
    det = ("Open water (wetsuit once you own one; do some non-wetsuit swims too). 10' easy + sighting every 6–9 strokes; "
           "4×20 hard strokes then settle (mass-start rehearsal); 3×(8' @ IM effort / 2' easy); practise drafting/turning "
           "at a marker; 5' easy. Swim with a buddy/group.")
    return S("Swim", "Open water skills", mins, det, f"RPE 3–4 at IM effort (≈{pace(CSS+10)}/100m pool equiv.)", "3–4",
             mins * 0.1, r100(mins * 45) / 1000)


def swim_easy(mins):
    d = r100(mins * 45)
    det = f"Easy {d}m: 200s & 400s, mix free/pull, 20s rest. Long, smooth strokes."
    return S("Swim", "Recovery swim", mins, det, SW_Z1, "2", 0, d / 1000)


def swim_test():
    det = ("CSS TEST. WU 400 easy + 4×50 build. 400m time trial (max even effort). 300 easy (~5'). "
           "200m time trial. CD 200. CSS/100m = (T400 − T200) ÷ 2. Update the Zones tab.")
    return S("Swim", "TEST: CSS 400/200", 45, det, "Max sustainable · RPE 9", "9", 10, 1.8)


# ---------------- BIKE ----------------
Q_BIKE = {
    1: ("4×3' @ {} /3' easy", (1.05, 1.12), 12),
    3: ("5×3' @ {} /3' easy", (1.10, 1.16), 15),
    4: ("6×3' @ {} /3' easy", (1.10, 1.16), 18),
    5: ("5×4' @ {} /3' easy", (1.07, 1.13), 20),
    7: ("6×4' @ {} /3' easy", (1.07, 1.13), 24),
    8: ("5×5' @ {} /3' easy", (1.05, 1.10), 25),
    9: ("6×5' @ {} /3' easy", (1.05, 1.10), 30),
    10: ("5×6' @ {} /3' easy", (1.05, 1.09), 30),
    11: ("4×8' @ {} /4' easy", (0.97, 1.03), 32),
    12: ("3×12' @ {} /5' easy", (0.95, 1.01), 36),
    13: ("4×10' @ {} /4' easy", (0.95, 1.01), 40),
    15: ("3×15' @ {} /5' easy", (0.93, 0.99), 45),
    16: ("2×20' @ {} /5' easy", (0.93, 0.99), 40),
    17: ("3×15' @ {} /4' easy", (0.94, 1.00), 45),
    19: ("5×5' @ {} /3' easy", (1.06, 1.12), 25),
    20: ("6×5' @ {} /3' easy", (1.06, 1.12), 30),
    21: ("2×20' @ {} /5' easy", (0.94, 1.00), 40),
    25: ("5×6' @ {} /3' easy", (1.03, 1.08), 30),
    26: ("3×12' @ {} /4' easy", (0.95, 1.01), 36),
    27: ("2×12' @ {} /5' easy", (0.95, 1.00), 24),
    31: ("5×5' @ {} /3' easy", (1.05, 1.10), 25),
    32: ("3×12' @ {} /4' easy", (0.95, 1.00), 36),
    33: ("4×6' @ {} /3' easy", (1.00, 1.05), 24),
    34: ("3×5' @ {} /3' easy", (0.98, 1.03), 15),
}


def bike_q(mins, wk):
    fmt, (lo, hi), work = Q_BIKE[wk]
    ms = fmt.format(W(lo, hi))
    zone = "Z5 VO2max" if lo >= 1.05 else "Z4 threshold"
    det = (f"Zwift structured. WU 15' Z1→Z2 incl. 3×30s @ 100+rpm. MS {ms}. Remaining time Z2 ({w(.62)}–{w(.70)}W). "
           f"CD 5–10' easy. Cadence 85–100 on efforts.")
    return S("Bike", f"Intervals — {zone}", mins, det, f"{zone}: {W(lo, hi)} · easy between {BK_Z1}",
             "8–9" if lo >= 1.05 else "7–8", work, round(mins / 60 * 30, 0))


def bike_z2(mins, im_blocks=None, heat=False, gym=False):
    if gym:
        det = (f"Gym bike / Wattbike (no road bike in London). Ride by HR, not watts: 10' easy, then "
               f"{mins-15}' Z2 HR 130–143" + (f" incl. {im_blocks} at top of Z2 (HR 140–143) to touch IM effort" if im_blocks else "") +
               ", 5' easy. If no bike available, swap for an extra 45' aerobic swim.")
        return S("Bike", "Gym bike endurance", mins, det, "Z2 HR 130–143 · RPE 3–4", "3–4", 0, None)
    det = f"Outdoors (Zwift if weather is bad). Ride by HR 130–143. 10' WU {w(.50)}→{w(.62)}W, {mins-15}' steady @ {Z2W}, cadence 85–95, 5' easy."
    if im_blocks:
        det += f" Include {im_blocks} @ IM power {IMW} in aero position."
    if heat:
        det += " HEAT ACCLIMATION: no fan / one extra layer, drink to thirst + 1g sodium/L; stop if HR >150 or you feel unwell."
    return S("Bike", "Endurance ride" + (" (heat)" if heat else ""), mins, det, BK_Z2, "3–4", 0, round(mins / 60 * 30, 0))


def bike_long(mins, wk, ph):
    hrs = mins / 60
    if ph == "base":
        extra = f"Last 20' @ IM power {IMW}." if wk >= 9 else "Smooth, steady, seated."
        g = "60–70" if wk < 9 else "70–80"
    elif ph == "build":
        n = 3 if mins < 290 else 2
        blk = 30 if mins < 270 else (40 if mins < 300 else 60)
        extra = f"Include {n}×{blk}' @ IM power {IMW} in aero, 10' Z2 between."
        g = "80–90"
    else:  # peak
        imh = min(int((hrs - 1.5) * 2) / 2, 4.0)
        extra = f"Middle {imh:g}h continuous @ IM power {IMW} in aero (race rehearsal: kit, bottles, nutrition)."
        g = "90–100"
    det = (f"Long ride {mins//60}h{mins%60:02d}. First 20' Z1–low Z2, then Z2 {Z2W}. {extra} "
           "Outdoors: flat, low-traffic roads, IM blocks in aero on the Speedmax. Ride Z2 by HR 130–143 (power is a guide if the bike has a meter); "
           "HR wins if they disagree.")
    return S("Bike", "Long ride", mins, det, f"{BK_Z2}; blocks {BK_IM}", "3–4", 0, round(hrs * 30, 0),
             fuel=f"{g} g carbs/h from minute 20 · 500–800mg sodium/h · 500–750ml fluid/h (gut training)")


def bike_easy(mins, note=""):
    det = f"Easy spin, {mins}' at high cadence (90–100 rpm). " + note
    return S("Bike", "Recovery spin", mins, det, BK_Z1, "1–2", 0, round(mins / 60 * 27, 0))


def bike_test():
    det = ("Zwift RAMP TEST (FTP = 75% of best 1-min power). 10' WU easy, ramp to failure, 10' CD. "
           "Update FTP in Zwift + Zones tab; log in Strava as 'FTP SET: [W]'. Fresh legs — easy day before.")
    return S("Bike", "TEST: FTP ramp", 45, det, "To failure · RPE 10", "10", 8, 18)


def bike_openers(mins):
    det = f"{mins}' easy with 3×2' @ IM power ({w(.685)}W) and 3×30s @ {w(1.03)}W, full recovery. Check gears/brakes."
    return S("Bike", "Openers", mins, det, f"{BK_Z2}; efforts as listed", "3–5", 5, round(mins / 60 * 30))


# ---------------- RUN ----------------
def km(mins):
    return round(mins / 6.0, 1)


STAGES = {
    1: ("6×(1' run / 1' walk)", 20, 6),
    2: ("6×(2' run / 1' walk)", 25, 12),
    3: ("5×(4' run / 1' walk)", 30, 20),
    4: ("3×(8' run / 1' walk)", 30, 24),
}


def run_wr(stage):
    reps, dur, runm = STAGES[stage]
    det = (f"RETURN-TO-RUN stage {stage}: 5' brisk walk, {reps}, finish with walk. Flat, soft surface (grass/path), "
           f"short quick steps (cadence +5%). Alternate days only. {BONE}")
    return S("Run", f"Walk-run (stage {stage})", dur, det, RN_Z1, "2–3", 0, km(runm))


def run_easy(mins, strides=False, cont_first=False):
    det = f"Easy continuous {mins}'." + (" First continuous runs — flat & soft surface." if cont_first else "")
    if strides:
        det += " Finish with 6×20s relaxed strides (not sprints), walk back recovery."
    det += " " + BONE
    return S("Run", "Easy run" + (" + strides" if strides else ""), mins, det, RN_Z2, "3–4",
             2 if strides else 0, km(mins))


RQ = {
    16: ("4×4' @ Z4 /2' jog", 16), 17: ("5×4' @ Z4 /2' jog", 20), 19: ("4×6' @ Z4 /2' jog", 24),
    20: ("3×8' @ Z4 /2' jog", 24), 21: ("4×7' @ Z4 /2' jog", 28), 25: ("3×10' @ Z4 /3' jog", 30),
    26: ("2×12' @ Z4 /3' jog", 24), 31: ("4×5' @ Z4 /2' jog", 20), 32: ("3×8' @ Z4 /2' jog", 24),
}


def run_q(mins, wk):
    ms, work = RQ[wk]
    det = (f"15' easy + 4 strides. MS {ms} (cruise intervals, ≈4:45–5:00/km but run by HR). Easy to finish. "
           f"Only if tibia fully quiet — otherwise run it all easy. {BONE}")
    return S("Run", "Cruise intervals", mins, det, f"{RN_Z4}; jogs {RN_Z1}", "7", work, km(mins))


def run_long(mins, ph, marathon_prep=False):
    det = f"Long run {mins}' (≈{km(mins):g} km). Even effort, flat route, HR capped at 149."
    if marathon_prep:
        det += " London prep: practise 60–90 g carbs/h exactly as planned for race day."
    elif ph in ("build", "peak"):
        det += " Last 20' at IM run feel (≈5:40–5:55/km, HR ≤149). Practise IM run fuelling."
    det += " " + BONE
    f = "60–90 g carbs/h (you've handled 90 g/h) + electrolytes" if mins >= 75 else "Water"
    return S("Run", "Long run", mins, det, RN_Z2, "3–4", 0, km(mins), fuel=f)


def run_brick(mins, ph):
    det = (f"BRICK — run straight off the bike (<5' transition). {mins}': first 5' settle with quick cadence, "
           "then IM run effort HR 140–149." + (" Treadmill fine." if ph == "london" else "") + " " + BONE)
    return S("Run", "Brick run", mins, det, RN_Z2, "4", 0, km(mins))


# ---------------- STRENGTH ----------------
STR = {
    # Andrew's own routine (from his Lift Log, wk 3) + the three tibia exercises in A.
    ("A", "base"): "Lower + pull: back squat 4×6, Bulgarian split squat 3×8/leg, Romanian DL 3×6, pull-ups 3×8, "
                   "calf raise 3×12, bicep curl 3×10, side plank 3×30s. TIBIA (keep): seated soleus raise 3×12 heavy, "
                   "tibialis raise 3×15, pogo hops 3×20 (single-leg hops from wk 8 if pain-free).",
    ("B", "base"): "Hips + push: hip thrust 3×10, step-ups 3×8/leg, single-leg RDL 3×8/leg, DB overhead press 3×8, "
                   "lateral raise 3×12, tricep pushdown 3×12, Pallof press 3×12.",
    ("A", "build"): "Lower + pull, maintenance (heavy, low volume): back squat 3×5, Bulgarian split squat 2×6/leg, Romanian DL 2×6, "
                    "pull-ups 3×6, bicep curl 2×10, side plank 2×30s. TIBIA (keep): seated soleus raise 3×10 heavy, "
                    "tibialis raise 2×15, single-leg hops 3×10/leg.",
    ("B", "build"): "Hips + push, light legs (long ride tomorrow): hip thrust 2×10 moderate, step-ups 2×8/leg light, "
                    "single-leg RDL 2×8 light, DB overhead press 3×8, lateral raise 3×12, tricep pushdown 3×12, Pallof press 3×10.",
    ("A", "peak"): "Short maintenance: back squat 2×5, Romanian DL 2×5, pull-ups 2×6, side plank 2×30s. "
                   "TIBIA (keep): seated soleus raise 2×10, single-leg hops 2×10/leg.",
    ("B", "peak"): "Upper/core & mobility: DB overhead press 2×8, lateral raise 2×12, tricep pushdown 2×12, Pallof press 2×10, hip mobility flow.",
}


def strength(k, ph, mins):
    p = ph if ph in ("base", "build", "peak") else "peak"
    return S("Strength", f"Strength {k} — {p}", mins, STR[(k, p)] + " See Strength tab.",
             "RPE 7–8 on main lifts, 1–3 reps in reserve", "7–8", 0)


def rest(text="Rest day — sleep, walk, mobility."):
    return S("Rest", "Rest", 0, text, "—", "—", 0)


def misc(sport, title, mins, det, target="RPE 2–3", rpe="2–3", high=0, dist=None, fuel=None):
    return S(sport, title, mins, det, target, rpe, high, dist, fuel)


def race(title, mins, det, target, fuel, dist, high):
    return S("Race", title, mins, det, target, "see plan", high, dist, fuel)


# ---------------- WEEK DEFINITIONS ----------------
def week(n, phase, kind, focus, days):
    start = START + dt.timedelta(days=7 * (n - 1))
    WEEKS[n] = dict(n=n, start=start, phase=phase, kind=kind, focus=focus)
    for i, day in enumerate(DAYS):
        for s in days.get(day, []):
            s.update(wk=n, date=start + dt.timedelta(days=i), day=day, phase=phase)
            SESSIONS.append(s)


B, BL, PK = "base", "build", "peak"

week(1, "Transition", "load", "Post-holiday rebuild; swim & bike only (tibia still healing).", {
    "Mon": [swim_aero(50), strength("A", B, 40)], "Tue": [bike_q(60, 1)], "Wed": [swim_css(50, "base1")],
    "Thu": [bike_z2(60), strength("B", B, 35)], "Fri": [swim_end(45)], "Sat": [bike_long(80, 1, B)],
    "Sun": [swim_easy(40)]})
week(2, "Transition", "reduced", "Wedding week — light & fresh. Fri–Sat off; easy ride Sun.", {
    "Mon": [swim_aero(45), strength("A", B, 30)], "Tue": [bike_z2(60)], "Wed": [swim_css(45, "base1")],
    "Thu": [bike_easy(45, "Keep it light.")], "Fri": [rest("Wedding day 🎉")], "Sat": [rest()], "Sun": [bike_z2(60)]})
week(3, "Base 1", "load", "Run returns (walk-run stage 1, alternate days). Aerobic swim/bike base, VO2 touch on the bike.", {
    "Mon": [swim_aero(45), strength("A", B, 40)], "Tue": [bike_q(60, 3), run_wr(1)], "Wed": [swim_css(50, "base1")],
    "Thu": [bike_z2(45), strength("B", B, 35), run_wr(1)], "Fri": [swim_end(45)], "Sat": [bike_long(90, 3, B)],
    "Sun": [run_wr(1)]})
week(4, "Base 1", "load", "Walk-run stage 2.", {
    "Mon": [swim_aero(50), strength("A", B, 40)], "Tue": [bike_q(60, 4), run_wr(2)], "Wed": [swim_css(50, "base1")],
    "Thu": [bike_z2(50), strength("B", B, 35), run_wr(2)], "Fri": [swim_end(50)], "Sat": [bike_long(100, 4, B)],
    "Sun": [run_wr(2)]})
week(5, "Base 1", "load", "Walk-run stage 3. Biggest base-1 week.", {
    "Mon": [swim_aero(55), strength("A", B, 40)], "Tue": [bike_q(60, 5), run_wr(3)], "Wed": [swim_css(55, "base1")],
    "Thu": [bike_z2(50), strength("B", B, 35), run_wr(3)], "Fri": [swim_end(55)], "Sat": [bike_long(120, 5, B)],
    "Sun": [run_wr(3)]})
week(6, "Base 1", "recovery", "Recovery + tests (CSS Wed, FTP ramp Sat). Hold walk-run stage 3.", {
    "Mon": [swim_aero(45), strength("A", B, 30)], "Tue": [bike_z2(45), run_wr(3)], "Wed": [swim_test()],
    "Thu": [bike_easy(40), strength("B", B, 30), run_wr(3)], "Fri": [swim_easy(40)], "Sat": [bike_test()],
    "Sun": [run_wr(3)]})
week(7, "Base 2", "load", "Walk-run stage 4, then continuous running next week.", {
    "Mon": [swim_aero(55), strength("A", B, 45)], "Tue": [bike_q(70, 7), run_wr(4)], "Wed": [swim_css(55, "base2")],
    "Thu": [bike_z2(50), strength("B", B, 40), run_wr(4)], "Fri": [swim_end(55)], "Sat": [bike_long(130, 7, B)],
    "Sun": [run_wr(4), swim_easy(25)]})
week(8, "Base 2", "load", "First continuous runs (25–30'). Long ride 2h45.", {
    "Mon": [swim_aero(60), strength("A", B, 45)], "Tue": [bike_q(70, 8), run_easy(25, cont_first=True)],
    "Wed": [swim_css(60, "base2")], "Thu": [bike_z2(50), strength("B", B, 40), run_easy(30)], "Fri": [swim_end(60)],
    "Sat": [bike_long(165, 8, B)], "Sun": [run_easy(30), swim_easy(35)]})
week(9, "Base 2", "load", "Continuous running established (4 runs incl. first brick). Run volume now capped at +10%/wk.", {
    "Mon": [swim_aero(60), strength("A", B, 45)], "Tue": [bike_q(75, 9), run_easy(30)], "Wed": [swim_css(60, "base2")],
    "Thu": [bike_z2(50), strength("B", B, 40), run_easy(30)], "Fri": [swim_end(60)],
    "Sat": [bike_long(180, 9, B), run_brick(10, B)], "Sun": [run_long(40, B), swim_easy(40)]})
# Week 10 was a recovery week; Andrew asked for a load week (23 Nov 2026). The trip (weeks 14–15) is the next easy block.
week(10, "Base 2", "load", "Load week (was recovery). Longest VO2 reps so far. Watch resting HR/HRV: 7 hard weeks run into the trip.", {
    "Mon": [swim_aero(60), strength("A", B, 45)], "Tue": [bike_q(75, 10), run_easy(30)], "Wed": [swim_css(60, "base2")],
    "Thu": [bike_z2(55), strength("B", B, 40), run_easy(30)], "Fri": [swim_end(60)],
    "Sat": [bike_long(185, 10, B), run_brick(10, B)], "Sun": [run_long(44, B), swim_easy(40)]})
week(11, "Base 3", "load", "Christmas week — Fri is optional/easy. Threshold work begins on the bike. Bumped (Andrew has time): long ride 3h45.", {
    "Mon": [swim_aero(60), strength("A", B, 45)], "Tue": [bike_q(75, 11), run_easy(30)], "Wed": [swim_css(65, "base3")],
    "Thu": [bike_z2(80), strength("B", B, 40)], "Fri": [run_easy(30, strides=True)],
    "Sat": [bike_long(225, 11, B), run_brick(10, B)], "Sun": [run_long(48, B), swim_end(45)]})
week(12, "Base 3", "load", "Strides added. Long ride 3h55 (bumped with week 11).", {
    "Mon": [swim_aero(60), strength("A", B, 45)], "Tue": [bike_q(75, 12), run_easy(35)],
    "Wed": [swim_css(60, "base3"), run_easy(30, strides=True)], "Thu": [bike_z2(80), strength("B", B, 40)],
    "Fri": [swim_end(60)], "Sat": [bike_long(235, 12, B), run_brick(10, B)], "Sun": [run_long(54, B), swim_easy(30)]})
week(13, "Base 3", "load", "Biggest base week.", {
    "Mon": [swim_aero(60), strength("A", B, 45)], "Tue": [bike_q(75, 13), run_easy(35)],
    "Wed": [swim_css(65, "base3"), run_easy(35, strides=True)], "Thu": [bike_z2(70), strength("B", B, 40)],
    "Fri": [swim_end(65)], "Sat": [bike_long(210, 13, B), run_brick(10, B)], "Sun": [run_long(60, B), swim_easy(35)]})
week(14, "Base 3", "recovery",
     "Recovery + tests. CHECKPOINT: tibia symptom-free on all runs since wk 8? If yes → London stays on & run intensity unlocks from wk 16. If not → see a sports doctor; drop London to the Olympic/T100 plan only.", {
    "Mon": [swim_aero(45), strength("A", B, 30)], "Tue": [bike_test(), run_easy(30)], "Wed": [swim_test()],
    "Thu": [bike_z2(60), strength("B", B, 30), run_easy(30, strides=True)], "Fri": [swim_easy(40)],
    "Sat": [bike_long(150, 14, B)], "Sun": [run_long(50, B)]})
week(15, "Build 1", "load", "Build begins: threshold bike, IM-power blocks on long rides, open water from wk 17.", {
    "Mon": [swim_aero(60, BL), strength("A", BL, 40)], "Tue": [bike_q(75, 15), run_easy(35)],
    "Wed": [swim_css(60, "build"), run_easy(30, strides=True)], "Thu": [bike_z2(75, "2×15'")],
    "Fri": [swim_end(65, BL), strength("B", BL, 30)], "Sat": [bike_long(225, 15, BL), run_brick(15, BL)],
    "Sun": [run_long(72, BL), swim_easy(35)]})
week(16, "Build 1", "load", "First run quality (cruise intervals) — only if wk 14 checkpoint passed.", {
    "Mon": [swim_aero(60, BL), strength("A", BL, 40)], "Tue": [bike_q(75, 16), run_q(40, 16)],
    "Wed": [swim_css(65, "build"), run_easy(30, strides=True)], "Thu": [bike_z2(80, "2×15'")],
    "Fri": [swim_end(65, BL), strength("B", BL, 30)], "Sat": [bike_long(240, 16, BL), run_brick(15, BL)],
    "Sun": [run_long(78, BL), swim_easy(35)]})
week(17, "Build 1", "load", "Open-water swims start Sundays. Get the wetsuit before this week.", {
    "Mon": [swim_aero(65, BL), strength("A", BL, 40)], "Tue": [bike_q(75, 17), run_q(40, 17)],
    "Wed": [swim_css(65, "build"), run_easy(30, strides=True)], "Thu": [bike_z2(85, "2×20'")],
    "Fri": [swim_end(70, BL), strength("B", BL, 30)], "Sat": [bike_long(255, 17, BL), run_brick(20, BL)],
    "Sun": [run_long(84, BL), swim_ows(40)]})
week(18, "Build 1", "recovery", "Recovery + CSS retest.", {
    "Mon": [swim_aero(45, BL), strength("A", BL, 30)], "Tue": [bike_z2(60), run_easy(35)], "Wed": [swim_test()],
    "Thu": [bike_z2(60), run_easy(35, strides=True)], "Fri": [swim_easy(45), strength("B", BL, 25)],
    "Sat": [bike_long(165, 18, B), run_brick(10, BL)], "Sun": [run_long(65, BL), swim_ows(30)]})
week(19, "Build 2", "load", "Optional: a local sprint tri on Sun 21 Feb for transition practice (swap for Sun long run).", {
    "Mon": [swim_aero(65, BL), strength("A", BL, 40)], "Tue": [bike_q(75, 19), run_q(40, 19)],
    "Wed": [swim_css(65, "build")], "Thu": [bike_z2(85, "2×20'"), run_easy(30, strides=True)],
    "Fri": [swim_end(70, BL), strength("B", BL, 30)], "Sat": [bike_long(270, 19, BL), run_brick(20, BL)],
    "Sun": [run_long(96, BL), swim_ows(40)]})
week(20, "Build 2", "load", "Long ride 5h.", {
    "Mon": [swim_aero(65, BL), strength("A", BL, 40)], "Tue": [bike_q(75, 20), run_q(45, 20)],
    "Wed": [swim_css(70, "build")], "Thu": [bike_z2(80, "2×20'"), run_easy(35, strides=True)],
    "Fri": [swim_end(75, BL), strength("B", BL, 30)], "Sat": [bike_long(300, 20, BL), run_brick(20, BL)],
    "Sun": [run_long(102, BL), swim_ows(45)]})
week(21, "Build 2", "load", "Peak build week before T100.", {
    "Mon": [swim_aero(65, BL), strength("A", BL, 40)], "Tue": [bike_q(75, 21), run_q(45, 21)],
    "Wed": [swim_css(70, "build")], "Thu": [bike_z2(80, "2×20'"), run_easy(40, strides=True)],
    "Fri": [swim_end(75, BL), strength("B", BL, 30)], "Sat": [bike_long(320, 21, BL), run_brick(25, BL)],
    "Sun": [run_long(110, BL), swim_ows(45)]})
week(22, "Build 2", "recovery", "Recovery + FTP retest. Set T100 race targets from new FTP.", {
    "Mon": [swim_aero(50, BL), strength("A", BL, 30)], "Tue": [bike_test(), run_easy(35)],
    "Wed": [swim_css(55, "build"), run_easy(35)], "Thu": [bike_z2(60, "2×10'"), run_easy(35, strides=True)],
    "Fri": [swim_easy(45), strength("B", BL, 25)], "Sat": [bike_long(180, 22, BL), run_brick(15, BL)],
    "Sun": [run_long(80, BL), swim_ows(40)]})
week(23, "Race: T100", "race", "Gold Coast T100 (2km/80km/18km) Sun 21 Mar — controlled IM-rehearsal effort, not all-out (London in 5 weeks).", {
    "Mon": [swim_aero(50, BL), strength("A", PK, 25)],
    "Tue": [misc("Bike", "Race-pace touch", 60, f"15' WU; 3×8' @ T100 power {T100W} (74–78%) /4'; rest Z2.",
                 f"T100 power {T100W} · HR ≤150", "5–6", 24, 30), run_easy(30, strides=True)],
    "Wed": [swim_css(45, "taper"), run_easy(25)],
    "Thu": [bike_openers(50), swim_ows(30)], "Fri": [swim_easy(25)],
    "Sat": [bike_openers(30), misc("Run", "Shakeout", 15, "15' easy jog + 4 strides. Rack bike, check gear.", RN_Z1, "2", 1, 2.5)],
    "Sun": [race("RACE — Gold Coast T100 (2/80/18)", 300,
                 "Swim 2km steady (1:40–1:44/100m). " f"Bike 80km @ {T100W} (74–78% FTP), HR ≤150, aero. Run 18km: HR 142–149 for 12km, "
                 "may float to ≤155 last 6km only if tibia + legs feel great. Rehearse IM nutrition. Practise transitions.",
                 f"Swim Z2–Z3 · Bike {T100W} · Run HR ≤149 then ≤155", "90 g carbs/h on bike, 60–90 g/h on run, 800mg sodium/h", 100, 60)]})
week(24, "Build 3", "recovery", "Post-race recovery; rebuild by Saturday.", {
    "Mon": [swim_easy(40)], "Tue": [bike_easy(45)], "Wed": [swim_aero(50, BL), strength("A", BL, 30)],
    "Thu": [bike_z2(60), run_easy(30)], "Fri": [swim_end(60, BL), strength("B", BL, 25), run_easy(30)],
    "Sat": [bike_long(180, 24, BL)], "Sun": [run_long(90, BL, marathon_prep=True), swim_ows(35)]})
week(25, "Build 3", "load", "Big block: London long run + IM long ride.", {
    "Mon": [swim_aero(65, PK), strength("A", BL, 40)], "Tue": [bike_q(75, 25), run_q(45, 25)],
    "Wed": [swim_css(70, "peak")], "Thu": [bike_z2(80, "2×20'"), run_easy(40, strides=True)],
    "Fri": [swim_end(75, BL), strength("B", BL, 30)], "Sat": [bike_long(330, 25, PK), run_brick(25, PK)],
    "Sun": [run_long(130, PK, marathon_prep=True), swim_ows(40)]})
week(26, "Build 3", "load", "Peak pre-London week: 6h ride + 27.5km long run (Z2).", {
    "Mon": [swim_aero(65, PK), strength("A", BL, 40)], "Tue": [bike_q(75, 26), run_q(45, 26)],
    "Wed": [swim_css(70, "peak")], "Thu": [bike_z2(80, "2×20'"), run_easy(40, strides=True)],
    "Fri": [swim_end(80, PK), strength("B", BL, 30)], "Sat": [bike_long(360, 26, PK), run_brick(15, PK)],
    "Sun": [run_long(163, PK, marathon_prep=True), swim_ows(40)]})
week(27, "Build 3", "reduced", "London mini-taper (run −30%); last long ride before the 19-day bike gap.", {
    "Mon": [swim_aero(60, PK), strength("A", PK, 30)], "Tue": [bike_q(75, 27), run_easy(40, strides=True)],
    "Wed": [swim_css(60, "peak"), run_easy(40)], "Thu": [bike_z2(75, "2×20'"), run_easy(35)],
    "Fri": [swim_end(60, BL), strength("B", PK, 25)], "Sat": [bike_long(240, 27, BL)],
    "Sun": [run_long(96, PK, marathon_prep=True), swim_easy(30)]})
week(28, "London", "race", "London Marathon Sun 25 Apr at Z2. Fly Wed 21 Apr (last ride Tue).", {
    "Mon": [swim_easy(40), bike_z2(60, "3×5'")], "Tue": [bike_easy(45, "Last ride until 10 May."), run_easy(30, strides=True)],
    "Wed": [rest("Travel day ✈️ — walk the aisle hourly, compression socks, hydrate.")],
    "Thu": [misc("Run", "Shakeout", 30, "30' very easy to shake off the flight + 15' mobility.", RN_Z1, "2", 0, 5)],
    "Fri": [swim_easy(30)],
    "Sat": [misc("Run", "Shakeout", 20, "20' easy + 4 strides. Lay out kit & gels.", RN_Z1, "2", 1, 3.5)],
    "Sun": [race("RACE — London Marathon (Z2 training run)", 245,
                 "Training day, not a PB. Run by HR: cap 149 (top of Z2), ≈5:35–5:50/km. If HR drifts above 149 after 30km, walk "
                 "the aid stations. Rehearse IM run nutrition. Stop immediately with any focal shin pain.",
                 "HR ≤149 · RPE 4–5", "60–90 g carbs/h from 20' + fluids/electrolytes at stations", 42.2, 0)]})
week(29, "London", "recovery", "Post-marathon recovery in London. No running Mon–Fri; no road bike.", {
    "Mon": [rest("Rest — walk 30–45'.")], "Tue": [swim_easy(30)],
    "Wed": [misc("Strength", "Mobility + upper/core", 30, "Upper body, core, hip mobility. No leg loading.", "RPE 5", "5")],
    "Thu": [swim_easy(40)], "Fri": [bike_z2(40, gym=True)],
    "Sat": [swim_easy(40), misc("Run", "First run back", 25, "25' easy only if no shin/bone pain hopping 20×. " + BONE, RN_Z1, "2", 0, 4)],
    "Sun": [swim_aero(45, BL)]})
week(30, "London", "reduced", "Rebuild in London: swim, run, gym — gym bike / Wattbike if available (by HR).", {
    "Mon": [swim_aero(55, BL), strength("A", BL, 35)], "Tue": [bike_z2(60, "3×8'", gym=True), run_easy(35)],
    "Wed": [swim_css(55, "build"), run_easy(35)], "Thu": [bike_z2(60, gym=True), strength("B", BL, 25)],
    "Fri": [swim_end(60, BL), run_easy(30, strides=True)],
    "Sat": [bike_z2(75, "2×15'", gym=True), run_brick(20, "london")], "Sun": [run_long(75, BL)]})
week(31, "Peak", "load", "Back on the bike — IM-specific block. Heat acclimation starts (Thu).", {
    "Mon": [swim_aero(50, PK), strength("A", PK, 30)], "Tue": [bike_q(75, 31), run_easy(40)],
    "Wed": [swim_css(65, "peak"), run_easy(40)], "Thu": [bike_z2(75, "2×20'", heat=True), run_easy(40, strides=True)],
    "Fri": [swim_end(75, PK), strength("B", PK, 25)], "Sat": [bike_long(270, 31, PK), run_brick(30, PK)],
    "Sun": [run_long(125, PK), swim_ows(40)]})
week(32, "Peak", "load", "Biggest IM-specific week: 5h15 ride (3.5h @ IM power) + 45' brick; 3.8km continuous swim.", {
    "Mon": [swim_aero(60, PK), strength("A", PK, 30)], "Tue": [bike_q(75, 32), run_q(45, 32)],
    "Wed": [swim_css(65, "peak"), run_easy(40)], "Thu": [bike_z2(75, "2×20'", heat=True), run_easy(40, strides=True)],
    "Fri": [swim_end(95, PK), strength("B", PK, 20)], "Sat": [bike_long(315, 32, PK), run_brick(45, PK)],
    "Sun": [run_long(120, PK), swim_ows(45)]})
week(33, "Peak", "reduced", "Last big weekend (2 weeks out), then taper begins.", {
    "Mon": [swim_aero(60, PK), strength("A", PK, 25)], "Tue": [bike_q(70, 33), run_easy(40, strides=True)],
    "Wed": [swim_css(60, "peak"), run_easy(40)], "Thu": [bike_z2(70, "2×15'", heat=True), run_easy(35)],
    "Fri": [swim_end(70, PK), strength("B", PK, 20)], "Sat": [bike_long(240, 33, PK), run_brick(20, PK)],
    "Sun": [run_long(95, PK), swim_ows(40)]})
week(34, "Taper", "taper", "Taper (~60%): keep intensity, cut volume. Last strength session Mon.", {
    "Mon": [swim_aero(45, PK), strength("A", PK, 20)], "Tue": [bike_q(60, 34), run_easy(35, strides=True)],
    "Wed": [swim_css(50, "taper"), run_easy(30)], "Thu": [bike_z2(60, "2×10'", heat=True)],
    "Fri": [swim_ows(40)], "Sat": [bike_long(150, 34, PK), run_brick(15, PK)], "Sun": [run_long(60, PK), swim_easy(30)]})
week(35, "Taper", "race", "Race week — travel to Cairns, sleep, carb-load Fri–Sat (8–10 g/kg ≈ 640–800 g/day).", {
    "Mon": [swim_easy(35), run_easy(25, strides=True)], "Tue": [bike_openers(60)],
    "Wed": [swim_css(35, "taper"), misc("Run", "Easy + strides", 20, "20' easy + 4×20s strides.", RN_Z2, "3", 1, 3.3)],
    "Thu": [bike_openers(40), rest("Travel to Cairns if not already there.")],
    "Fri": [swim_ows(25), misc("Run", "Shakeout", 15, "15' easy on part of the run course.", RN_Z1, "2", 0, 2.5)],
    "Sat": [bike_openers(25), swim_easy(15), rest("Bike check-in. Feet up.")],
    "Sun": [race("RACE — IRONMAN Cairns 🏁", 735,
                 f"Swim 3.8km @ {pace(CSS+10)}–{pace(CSS+14)}/100m (~{round((CSS+12)*38/60)}'). Bike 180km @ 70–75% FTP NP "
                 f"({IMW_SUB11} at {FTP}W; ~188–201W if FTP reaches 268W), HR ≤145, cap {w(.88)}W on rises. Set the final number from the wk-22 FTP test and T100. "
                 "Run 42.2km: HR 140–149 first 30km (≈5:50–6:15/km), walk aid stations from km 1, then empty the tank. See Race Day tab.",
                 "Swim Z2 · Bike 70–75% FTP · Run HR ≤149", "Bike 90–100 g carbs/h, Run 60–90 g/h, 700–1000mg sodium/h", 226, 0)]})

# ---------------- 3-swim cap (athlete preference: max 3 swims/week) ----------------
def _swap(s, new):
    keep = {k: s[k] for k in ("wk", "date", "day", "phase")}
    s.clear(); s.update(new); s.update(keep)


def cap_swims():
    global SESSIONS
    drop = set()
    for w in WEEKS:
        sw = [s for s in SESSIONS if s["wk"] == w and s["sport"] == "Swim"]
        if len(sw) <= 3:
            continue
        sun_rec = [s for s in sw if s["day"] == "Sun" and s["title"] == "Recovery swim"]
        if sun_rec:
            s = sun_rec[0]
            _swap(s, bike_easy(s["dur"], "Replaces a 4th swim — keeps the legs moving after Saturday's long ride."))
        elif w == 35:
            drop.add(id([s for s in sw if s["day"] == "Sat"][0]))
        elif w == 23:
            drop.add(id([s for s in sw if s["day"] == "Fri"][0]))
        elif w == 24:
            drop.add(id([s for s in sw if s["day"] == "Mon"][0]))
        elif w == 29:
            s = [x for x in sw if x["day"] == "Tue"][0]
            _swap(s, bike_z2(s["dur"], gym=True))
        else:  # Sunday open-water week: Monday pool swim becomes a recovery spin
            s = [x for x in sw if x["day"] == "Mon"][0]
            _swap(s, bike_easy(min(s["dur"], 45), "Replaces the Monday pool swim (Sunday open water is the 3rd swim). Flushes legs after the long run."))
    SESSIONS = [s for s in SESSIONS if id(s) not in drop]
    # days left empty become rest days
    for w in WEEKS:
        for d in DAYS:
            if not any(s["wk"] == w and s["day"] == d for s in SESSIONS):
                r = rest("Rest day."); r.update(wk=w, day=d, phase=WEEKS[w]["phase"],
                                               date=WEEKS[w]["start"] + dt.timedelta(days=DAYS.index(d)))
                SESSIONS.append(r)


cap_swims()

# ---------------- stack Strength A on the bike-interval day (hard days hard, easy days easy) ----------------
def _place(s, day, w):
    s["day"] = day
    s["date"] = WEEKS[w]["start"] + dt.timedelta(days=DAYS.index(day))


# Athlete removed the 2 h weekday cap on 23 Nov 2026 (weekend days stay <= 8 h).
WEEKDAY_CAP = 24 * 60


def _mins(w, d):
    return sum(x["dur"] for x in SESSIONS if x["wk"] == w and x["day"] == d)


def stack_strength():
    global SESSIONS
    for w in WEEKS:
        wk = [s for s in SESSIONS if s["wk"] == w]
        sa = [s for s in wk if s["sport"] == "Strength" and s["title"].startswith("Strength A")]
        bq = [s for s in wk if s["sport"] == "Bike" and s["title"].startswith("Intervals")]
        if not sa or not bq or sa[0]["day"] == bq[0]["day"]:
            continue
        qday = bq[0]["day"]
        s = sa[0]
        s["details"] = "Do this AFTER the bike intervals — ideally 6h+ later (bike AM, gym PM). " + s["details"]
        _place(s, qday, w)
        # walk-run weeks: keep runs on alternate days, away from the stacked day -> Mon / Wed / Fri
        wr = [x for x in wk if x["sport"] == "Run" and x["title"].startswith("Walk-run")]
        if wr:
            for x, d in zip(sorted(wr, key=lambda x: x["date"]), ["Mon", "Wed", "Fri"]):
                _place(x, d, w)
        elif _mins(w, qday) > WEEKDAY_CAP:
            runs = [x for x in wk if x["sport"] == "Run" and x["day"] == qday]
            for r in runs:
                if r["title"] == "Cruise intervals":
                    # run quality moves to Wed with the CSS swim (stacked hard day); Wed's easy run goes to Mon
                    for e in [x for x in wk if x["sport"] == "Run" and x["day"] == "Wed"]:
                        _place(e, "Mon", w)
                    _place(r, "Wed", w)
                else:
                    _place(r, "Mon", w)
    # drop rest placeholders on days that now have training, add them to days left empty
    SESSIONS = [x for x in SESSIONS if not (x["sport"] == "Rest" and x["title"] == "Rest" and x["details"] == "Rest day."
                and any(y is not x and y["wk"] == x["wk"] and y["day"] == x["day"] for y in SESSIONS))]
    for w in WEEKS:
        for d in DAYS:
            if not any(x["wk"] == w and x["day"] == d for x in SESSIONS):
                r = rest("Rest day."); r.update(wk=w, day=d, phase=WEEKS[w]["phase"],
                                               date=WEEKS[w]["start"] + dt.timedelta(days=DAYS.index(d)))
                SESSIONS.append(r)


stack_strength()

# ---------------- one full rest day a week (athlete request, 23 Nov 2026) ----------------
# Week 7: Sunday's recovery spin is dropped (Sunday rest). From week 8, Monday is the rest day in any week
# that has none: recovery sessions are dropped, everything else moves to the best day that keeps the rules
# (max 3 swims, swims midday, one run a day).
REST_LOG = []


def _day(w, d):
    return [x for x in SESSIONS if x["wk"] == w and x["day"] == d and x["sport"] != "Rest"]


def _move(s, d, w):
    s["day"] = d
    s["date"] = WEEKS[w]["start"] + dt.timedelta(days=DAYS.index(d))


def _load(w, d, drop=()):
    return sum(x["dur"] for x in _day(w, d) if id(x) not in drop)


def _place_run(s, w, drop):
    """Move a Monday run to a weekday with no run, preferring days with no run either side (bone load).
    If the only blocker is room, shift that day's strength session to another weekday that has room."""
    runs = lambda d: any(x["sport"] in ("Run", "Race") for x in _day(w, d) if id(x) not in drop)
    real = lambda d: any(x["sport"] in ("Run", "Race") and x["title"] != "Brick run" for x in _day(w, d) if id(x) not in drop)
    days = [d for d in ("Tue", "Wed", "Thu", "Fri") if not runs(d)]
    spaced = lambda d: not any(real(n) for n in (DAYS[DAYS.index(d) - 1], DAYS[(DAYS.index(d) + 1) % 7]) if n != "Mon")
    str_days = lambda: [x["day"] for x in SESSIONS if x["wk"] == w and x["sport"] == "Strength" and id(x) not in drop]
    near = lambda d, other: abs(DAYS.index(d) - DAYS.index(other)) <= 1
    cands = [d for d in days if spaced(d)] + ([] if w <= 8 else [d for d in days if not spaced(d)])
    for d in cands:
        if _load(w, d, drop) + s["dur"] <= WEEKDAY_CAP:
            _move(s, d, w); REST_LOG.append((w, s["title"], d)); return True
        st = [x for x in _day(w, d) if x["sport"] == "Strength"]
        if st and _load(w, d, drop) - st[0]["dur"] + s["dur"] <= WEEKDAY_CAP:
            for d2 in ("Tue", "Wed", "Thu", "Fri"):
                others = [o for o in str_days() if o != d]
                if (d2 != d and not any(x["sport"] == "Strength" for x in _day(w, d2)) and _load(w, d2, drop) + st[0]["dur"] <= WEEKDAY_CAP
                        and not any(near(d2, o) for o in others)):
                    _move(st[0], d2, w); _move(s, d, w)
                    REST_LOG.append((w, s["title"], f"{d} ({st[0]['title']} → {d2})")); return True
        # last resort: also move the other strength session so the two stay a day apart
        if w < 20 and st and _load(w, d, drop) - st[0]["dur"] + s["dur"] <= WEEKDAY_CAP:
            other = [x for x in SESSIONS if x["wk"] == w and x["sport"] == "Strength" and x is not st[0] and id(x) not in drop]
            for d2 in ("Tue", "Wed", "Thu", "Fri"):
                for d3 in ("Tue", "Wed", "Thu", "Fri", "Sun"):
                    if (other and d2 not in (d, d3) and d3 != d and not near(d2, d3)
                            and _load(w, d2, drop) + st[0]["dur"] <= WEEKDAY_CAP
                            and (d3 == other[0]["day"] or _load(w, d3, drop) + other[0]["dur"] <= (480 if d3 == "Sun" else WEEKDAY_CAP))
                            and not any(x["sport"] == "Strength" for x in _day(w, d2))):
                        if d3 != other[0]["day"]:
                            _move(other[0], d3, w)
                        _move(st[0], d2, w); _move(s, d, w)
                        REST_LOG.append((w, s["title"], f"{d} ({st[0]['title']} → {d2}, {other[0]['title']} → {d3})")); return True
    return False


def rest_day():
    global SESSIONS
    drop = set()
    sun7 = [x for x in _day(7, "Sun") if x["title"] == "Recovery spin"]
    for x in sun7:
        drop.add(id(x)); REST_LOG.append((7, x["title"], "dropped (Sunday rest)"))
    for w in WEEKS:
        if w < 8:
            continue
        if any(not _day(w, d) for d in DAYS):
            continue  # already has a rest day
        for s in sorted(_day(w, "Mon"), key=lambda x: x["sport"] != "Swim"):
            if s["title"].startswith("Recovery"):
                drop.add(id(s)); REST_LOG.append((w, s["title"], "dropped")); continue
            if s["sport"] == "Swim":
                sun = _day(w, "Sun")
                spin = [x for x in sun if x["title"] == "Recovery spin"]
                if spin:
                    drop.add(id(spin[0])); _move(s, "Sun", w); REST_LOG.append((w, s["title"], "Sun (replaces spin)")); continue
                if not any(x["sport"] in ("Swim", "Race") for x in sun):
                    _move(s, "Sun", w); REST_LOG.append((w, s["title"], "Sun")); continue
                order = ["Thu", "Tue", "Wed", "Fri"]
                ok = lambda d: not any(x["sport"] == "Swim" for x in _day(w, d))
            elif s["sport"] == "Run":
                if _place_run(s, w, drop):
                    continue
                drop.add(id(s)); REST_LOG.append((w, s["title"], "dropped (no room)")); continue
            else:
                order = ["Tue", "Wed", "Thu", "Fri", "Sun"]
                ok = lambda d: not any(x["sport"] in ("Strength", "Race") for x in _day(w, d))
            for d in order:
                cap = 480 if d in ("Sat", "Sun") else WEEKDAY_CAP
                if ok(d) and _load(w, d, drop) + s["dur"] <= cap:
                    _move(s, d, w); REST_LOG.append((w, s["title"], d)); break
            else:
                drop.add(id(s)); REST_LOG.append((w, s["title"], "dropped (no room)"))
    SESSIONS = [x for x in SESSIONS if id(x) not in drop and x["sport"] != "Rest"]
    for w in WEEKS:
        for d in DAYS:
            if not _day(w, d):
                r = rest("Rest day."); r.update(wk=w, day=d, phase=WEEKS[w]["phase"],
                                               date=WEEKS[w]["start"] + dt.timedelta(days=DAYS.index(d)))
                SESSIONS.append(r)


rest_day()

# ---------------- strength midweek only (athlete request, 23 Nov 2026) ----------------
# No gym on Fri/Sat/Sun: legs stay fresh for the weekend long ride and long run.
# From week 7: Strength A on the bike-interval day (normally Tue), Strength B on Thu.
def strength_midweek():
    global SESSIONS
    for w in WEEKS:
        if w < 7:
            continue
        st = [x for x in SESSIONS if x["wk"] == w and x["sport"] == "Strength"]
        a = [x for x in st if x["title"].startswith("Strength A")]
        b = [x for x in st if x["title"].startswith("Strength B")]
        q = [x["day"] for x in SESSIONS if x["wk"] == w and x["sport"] == "Bike" and x["title"].startswith(("Intervals", "TEST"))]
        aday = q[0] if q and q[0] in ("Tue", "Wed") else "Tue"
        for x in a:
            if x["day"] != aday:
                _move(x, aday, w)
        for x in b:
            if x["day"] != "Thu":
                _move(x, "Thu", w)
        # rest placeholders: drop where training landed, add where a day emptied
        SESSIONS = [x for x in SESSIONS if not (x["sport"] == "Rest" and x["wk"] == w and any(
            y["wk"] == w and y["day"] == x["day"] and y["sport"] != "Rest" for y in SESSIONS))]
        for d in DAYS:
            if not _day(w, d) and not any(x["wk"] == w and x["day"] == d for x in SESSIONS):
                r = rest("Rest day."); r.update(wk=w, day=d, phase=WEEKS[w]["phase"],
                                               date=WEEKS[w]["start"] + dt.timedelta(days=DAYS.index(d)))
                SESSIONS.append(r)


strength_midweek()


def spread_runs():
    """With no weekday cap, easy runs stay on the interval day (Tue). Where that leaves easy runs on Tue and Wed
    back to back, move Wednesday's easy run to Thursday so weekday runs stay a day apart."""
    for w in WEEKS:
        if w < 9:
            continue
        r = lambda d: [x for x in _day(w, d) if x["sport"] == "Run"]
        if r("Tue") and r("Wed") and not r("Thu") and all(x["title"].startswith("Easy") for x in r("Wed")):
            for x in r("Wed"):
                _move(x, "Thu", w)
                REST_LOG.append((w, x["title"], "Thu (spaced from Tue run)"))


spread_runs()

# ---------------- Indonesia surf trip, Fri 8 – Tue 26 Jan 2027 (athlete, 23 Nov 2026) ----------------
# Surfing 2–4 h a day, gym with strength, treadmill and stationary bike; no swimming apart from surfing;
# gym-bike watts unknown, so bike sessions run on HR/RPE. Training allowed on the morning of 8 Jan.
# Week 13 is a shortened load week; weeks 14–15 are travel weeks (hours rule skips them; runs continue so
# they count for run km);
# week 16 is re-entry; FTP test moves to week 17; week-17 long ride 4h (was 4h15) and brick 15' to stay within 10%.
TRIP = (dt.date(2027, 1, 8), dt.date(2027, 1, 26))
SURF = "Surfing counts as the swim work this week. "


def gym_bike_int(mins):
    det = ("Gym stationary bike, by HR and feel (watts if the bike shows them, but gym watts read differently from your trainer). "
           "WU 15' easy → steady incl. 3×30s fast cadence. MS 5×4' HARD (RPE 8, HR climbing into 155–165 by the end of each rep) "
           f"/3' easy. Remaining time easy Z2 (HR 130–143). Ride early, before surfing, with a fan if there is one.")
    return S("Bike", "Gym bike intervals", mins, det, "Reps RPE 8 · HR 155–165 by rep end · easy HR <130", "8", 20, None)


def gym_bike_z2(mins, long=False):
    det = (f"Gym stationary bike: 10' easy, then {mins-15}' Z2 HR 130–143 (RPE 3–4), cadence 85–95, 5' easy. "
           "Heat pushes HR up: keep HR in range even if it feels easy. 500–750 ml fluid/h + electrolytes."
           + (" Longest ride of the week. Shorter than the plan at home — 2 h+ on a gym bike after surfing is not worth it." if long else ""))
    return S("Bike", "Gym bike long" if long else "Gym bike endurance", mins, det, "Z2 HR 130–143 · RPE 3–4", "3–4", 0, None,
             fuel="40–60 g carbs/h" if long else None)


def _add(w, d, sess):
    sess.update(wk=w, day=d, phase=WEEKS[w]["phase"], date=WEEKS[w]["start"] + dt.timedelta(days=DAYS.index(d)))
    SESSIONS.append(sess)
    return sess


def _rm(w, d, pred=lambda x: True):
    global SESSIONS
    SESSIONS = [x for x in SESSIONS if not (x["wk"] == w and x["day"] == d and pred(x))]


def trip_note(x):
    x["details"] = "INDONESIA. " + x["details"] + (" Heat: run early or on a treadmill; HR cap still applies." if x["sport"] == "Run" else "")


def indonesia():
    global SESSIONS
    # week 13: a load week cut short (Andrew, 23 Nov 2026). Long ride Thu, long run Fri morning before the
    # afternoon flight; Sat surf; Sun easy run in Indonesia. Counts as load in content, but its shortened hours
    # don't set the 10% baseline (kind "load_short").
    SESSIONS = [x for x in SESSIONS if x["wk"] != 13]
    WEEKS[13]["kind"] = "load_short"
    WEEKS[13]["focus"] = ("Load week, cut short by the trip: long ride Thu, long run Fri morning, fly Fri afternoon. "
                          "Sat surf, Sun easy run in Indonesia.")
    _add(13, "Tue", bike_q(75, 13)); _add(13, "Tue", run_easy(35)); _add(13, "Tue", strength("A", B, 45))
    _add(13, "Wed", swim_css(65, "base3")); _add(13, "Wed", strength("B", B, 40))
    _add(13, "Thu", bike_long(210, 13, B)); _add(13, "Thu", run_brick(10, B))
    lr = _add(13, "Fri", run_long(60, B)); lr["details"] = "Early, before the airport. " + lr["details"]
    sw = _add(13, "Fri", swim_end(45, "base")); sw["details"] = "Optional, if there's time before the airport (AM is fine today). " + sw["details"]
    ez = _add(13, "Sun", run_easy(30)); trip_note(ez)
    # weeks 14 and 15: travel weeks
    for w in (14, 15):
        WEEKS[w]["kind"] = "travel"
        WEEKS[w]["focus"] = ("INDONESIA surf trip (8–26 Jan). " + SURF + "Gym: bike Tue/Thu/Sat by HR, runs as planned "
                             "(early or treadmill — heat), strength Tue/Thu. Tests move to after the trip.")
        _rm(w, "Tue", lambda x: x["sport"] == "Bike"); _add(w, "Tue", gym_bike_int(60))
        _rm(w, "Wed")
        _rm(w, "Thu", lambda x: x["sport"] == "Bike"); _add(w, "Thu", gym_bike_z2(60))
        _rm(w, "Fri")
        _rm(w, "Sat", lambda x: x["sport"] == "Bike"); _add(w, "Sat", gym_bike_z2(90, long=True))
        _rm(w, "Sun", lambda x: x["sport"] == "Swim")
        for x in SESSIONS:
            if x["wk"] == w and x["sport"] in ("Run", "Strength"):
                trip_note(x)
                if x["sport"] == "Strength":
                    x["details"] += " Surfing is heavy pulling: drop pull-ups and lateral raises this week; keep legs, core and tibia work."
    WEEKS[14]["focus"] += (" CHECKPOINT (runs continue on the trip): tibia symptom-free on all runs since wk 8? If yes → London stays on "
                           "& run intensity unlocks from wk 17. If not → see a sports doctor.")
    # week 16: home Tue 26 Jan; re-entry week
    WEEKS[16]["kind"] = "travel"  # return week: lighter, counted like the trip weeks
    WEEKS[16]["focus"] = ("Back from Indonesia (home Tue 26 Jan). Re-entry: easy swims, shorter long ride. "
                          "No run quality yet — cruise intervals start wk 17.")
    _rm(16, "Tue")
    for x in _day(16, "Wed"):
        if x["sport"] == "Swim":
            x.update(swim_easy(45)); x["details"] = "First swim in 2½ weeks: easy, feel the water. " + x["details"]
    _add(16, "Wed", strength("A", "build", 40))
    trip_run = _add(16, "Wed", run_easy(35)); trip_run["details"] = "Back on home roads. " + trip_run["details"]
    _rm(16, "Thu", lambda x: x["sport"] == "Strength")
    for x in _day(16, "Sat"):
        if x["title"] == "Long ride":
            x.update(bike_long(180, 16, "build")); x["title"] = "Long ride"
    # week 17: FTP test replaces the Tuesday intervals; long ride capped so the return is <= +10%
    for x in _day(17, "Tue"):
        if x["sport"] == "Bike":
            x.update(bike_test())
    for x in _day(17, "Sat"):
        if x["title"] == "Long ride":
            x.update(bike_long(240, 17, "build")); x["title"] = "Long ride"
        if x["title"] == "Brick run":
            x.update(run_brick(15, "build"))
    WEEKS[17]["focus"] = "FTP ramp test Tue (moved from wk 14). " + WEEKS[17]["focus"]
    SESSIONS = [x for x in SESSIONS if x["sport"] != "Rest"]
    for w in (13, 14, 15, 16, 17):
        for d in DAYS:
            if not _day(w, d):
                r = rest("Rest day." if not (TRIP[0] <= WEEKS[w]["start"] + dt.timedelta(days=DAYS.index(d)) <= TRIP[1])
                         else "Indonesia: surf day, no structured training."); r.update(wk=w, day=d, phase=WEEKS[w]["phase"],
                                               date=WEEKS[w]["start"] + dt.timedelta(days=DAYS.index(d)))
                SESSIONS.append(r)
    for w in WEEKS:
        for d in DAYS:
            if not any(x["wk"] == w and x["day"] == d for x in SESSIONS):
                r = rest("Rest day."); r.update(wk=w, day=d, phase=WEEKS[w]["phase"],
                                               date=WEEKS[w]["start"] + dt.timedelta(days=DAYS.index(d)))
                SESSIONS.append(r)


indonesia()

# ---------------- sub-11 bike targets (from Build 1, wk 15) ----------------
def sub11_bike():
    for s in SESSIONS:
        if s["sport"] == "Bike" and s["wk"] >= 15:
            for k in ("details", "target"):
                s[k] = (s[k].replace(f"IM power {IMW} (66–71%) · HR ≤143", f"IM power {IMW_SUB11} (70–75% FTP) · HR ≤145")
                            .replace(f"IM power {IMW}", f"IM power {IMW_SUB11} (70–75% FTP)")
                            .replace(f"@ IM power ({w(.685)}W)", f"@ IM power ({w(.725)}W)"))


sub11_bike()

# ---------------- time of day (athlete swims at midday only) ----------------
def set_when():
    for s in SESSIONS:
        same = [x for x in SESSIONS if x["wk"] == s["wk"] and x["day"] == s["day"] and x is not s]
        sp = s["sport"]
        if sp == "Swim":
            s["when"] = "Midday" if s["day"] not in ("Sat", "Sun") else "Midday / any"
        elif sp == "Bike":
            s["when"] = "AM"
        elif sp == "Run":
            if s["title"] == "Brick run":
                s["when"] = "Straight after ride"
            elif s["day"] in ("Sat", "Sun"):
                s["when"] = "AM"
            elif any(x["sport"] == "Bike" for x in same):
                s["when"] = "PM"
            else:
                s["when"] = "AM"
        elif sp == "Strength":
            s["when"] = "PM (after run)" if any(x["sport"] == "Run" and x.get("when") == "PM" for x in same) else "PM"
        elif sp == "Race":
            s["when"] = "Race"
        else:
            s["when"] = ""


set_when()
set_when()  # second pass so strength sees run times

SESSIONS.sort(key=lambda s: (s["date"], ["Swim", "Bike", "Run", "Strength", "Race", "Rest"].index(s["sport"])))
