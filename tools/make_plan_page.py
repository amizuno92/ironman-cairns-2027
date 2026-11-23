"""Build a read-only plan page (boards/plan.html) from plan/plan.json.

Usage: python tools/make_plan_page.py
Republish boards/plan.html to the pinned "Cairns 2027 Plan" artifact after any plan change.
"""
import datetime as dt
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
WHEN = {"AM": 0, "Midday": 1, "Midday / any": 1, "Straight after ride": 2, "PM": 3, "PM (after run)": 4}
SPORT = {"Swim": "swim", "Bike": "bike", "Run": "run", "Strength": "str", "Race": "race", "Brick": "bike"}
EVENTS = {"2027-03-21": "Gold Coast T100", "2027-04-25": "London Marathon (Z2)", "2027-06-13": "IRONMAN Cairns"}

e = html.escape


def fmt_min(m):
    h, mm = divmod(int(m), 60)
    return f"{h}:{mm:02d}" if h else f"{mm}′"


def main():
    p = json.loads((ROOT / "plan" / "plan.json").read_text())
    weeks, sessions = p["weeks"], p["sessions"]
    rules = json.loads((ROOT / "rules.json").read_text())
    ftp_w = {c["week"]: c["target_w"] for c in rules.get("ftp_checkpoints", [])}
    maxh = max(w["planned_hours"] for w in weeks)

    # weekly hours chart (SVG, one bar per week, to scale)
    W, H, pad_l, pad_b, pad_t = 720, 170, 30, 22, 10
    bw = (W - pad_l) / len(weeks)
    top = 20 if maxh <= 20 else int(maxh) + 1
    y = lambda v: pad_t + (H - pad_t - pad_b) * (1 - v / top)
    bars = []
    for t in (5, 10, 15, 20):
        if t <= top:
            bars.append(f'<line x1="{pad_l}" x2="{W}" y1="{y(t):.1f}" y2="{y(t):.1f}" class="grid"/>'
                        f'<text x="{pad_l-6}" y="{y(t)+4:.1f}" class="ax" text-anchor="end">{t}h</text>')
    for i, w in enumerate(weeks):
        x = pad_l + i * bw + 1.5
        cls = {"recovery": "rec", "taper": "tap", "race": "race", "travel": "rec"}.get(w["kind"], "load")
        bars.append(f'<a href="#w{w["week"]}"><rect x="{x:.1f}" y="{y(w["planned_hours"]):.1f}" width="{bw-3:.1f}" '
                    f'height="{y(0)-y(w["planned_hours"]):.1f}" class="b {cls}" data-wk="{w["week"]}">'
                    f'<title>Week {w["week"]} · {w["phase"]} · {w["planned_hours"]}h</title></rect></a>')
        if w["week"] % 5 == 0 or w["week"] == 1:
            bars.append(f'<text x="{x+(bw-3)/2:.1f}" y="{H-6}" class="ax" text-anchor="middle">{w["week"]}</text>')
    chart = f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Planned hours per week">{"".join(bars)}</svg>'

    # phase strip
    phases = []
    for w in weeks:
        if phases and phases[-1][0] == w["phase"]:
            phases[-1][1] += 1
        else:
            phases.append([w["phase"], 1, w["week"]])
    strip = "".join(f'<div class="ph" style="flex:{n}" title="{e(ph)} · weeks {s}–{s+n-1}"><span>{e(ph)}</span></div>'
                    for ph, n, s in phases)

    # weeks
    blocks = []
    for w in weeks:
        start = dt.date.fromisoformat(w["start"])
        end = start + dt.timedelta(days=6)
        ss = sorted([s for s in sessions if s["week"] == w["week"] and s["sport"] != "Rest"],
                    key=lambda s: (DAYS.index(s["day"]), WHEN.get(s.get("when", ""), 2)))
        rows, lastday = [], None
        for s in ss:
            d = start + dt.timedelta(days=DAYS.index(s["day"]))
            day = f'<span class="dn">{s["day"]}</span> <span class="dd">{d.day}</span>' if s["day"] != lastday else ""
            lastday = s["day"]
            ev = EVENTS.get(d.isoformat())
            dist = f' · {s["distance_km"]} km' if s.get("distance_km") else ""
            fuel = f'<div class="fu">Fuel: {e(s["fuel"])}</div>' if s.get("fuel") else ""
            rows.append(
                f'<tr class="{SPORT.get(s["sport"], "oth")}{" ev" if ev else ""}"><td class="day">{day}</td>'
                f'<td class="when">{e(s.get("when", ""))}</td>'
                f'<td class="ses"><div class="t"><i class="chip">{e(s["sport"])}</i>{e(s["title"])}'
                f'<span class="dur">{fmt_min(s["duration_min"])}{dist}</span></div>'
                f'<div class="tg">{e(s["target"])}</div><div class="dt">{e(s["details"])}</div>{fuel}</td></tr>')
        days_used = {s["day"] for s in ss}
        rest = [dd for dd in DAYS if dd not in days_used]
        rest_s = f'<p class="rest">Rest: {", ".join(rest)}</p>' if rest else ""
        tag = {"recovery": "Recovery", "taper": "Taper", "race": "Race week", "reduced": "Reduced", "travel": "Travel", "load_short": "Cut short"}.get(w["kind"], "")
        tag_s = f'<span class="tag {w["kind"]}">{tag}</span>' if tag else ""
        ftp_s = f'<span class="tag test">FTP checkpoint {ftp_w[w["week"]]} W</span>' if w["week"] in ftp_w else ""
        rng = f"{start.day} {start:%b} – {end.day} {end:%b}"
        blocks.append(
            f'<details class="wk" id="w{w["week"]}" data-start="{w["start"]}" data-end="{end.isoformat()}">'
            f'<summary><span class="wn">Wk {w["week"]}</span><span class="wr">{rng}</span>'
            f'<span class="wp">{e(w["phase"])}</span>{tag_s}{ftp_s}<span class="wh">{w["planned_hours"]:.1f} h</span></summary>'
            f'<p class="focus">{e(w["focus"])}</p>{rest_s}'
            f'<div class="tw"><table>{"".join(rows)}</table></div></details>')

    total = sum(w["planned_hours"] for w in weeks)
    css = p["css_sec_per_100m"]
    gen = dt.date.today().strftime("%-d %b %Y")
    out = TEMPLATE.format(
        chart=chart, strip=strip, weeks="".join(blocks), nweeks=len(weeks), total=f"{total:.0f}",
        ftp=p["ftp_w"], css=f"{css//60}:{css%60:02d}", lthr=p["run_lthr"], blthr=p["bike_lthr"],
        maxh=f"{maxh:.1f}", gen=gen, nsess=len([s for s in sessions if s["sport"] != "Rest"]))
    (ROOT / "boards" / "plan.html").write_text(out)
    print(f"boards/plan.html: {len(weeks)} weeks, {total:.0f} h")


TEMPLATE = """<title>Cairns 2027 Plan</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@500&display=swap">
<style>
/* Layout: masthead with key numbers, season chart + phase strip, then 35 collapsible weeks (current week opens). Same tokens as the week boards. */
:root{{
  --bg:#f3f5f8; --surface:#ffffff; --ink:#16202c; --muted:#5d6b7c; --line:#d9dfe7; --soft:#e9edf2;
  --accent:#0f6e8c;
  --swim:#1479a8; --swim-bg:#e3f1f8; --bike:#3a8a3f; --bike-bg:#e6f3e4;
  --run:#c2611f; --run-bg:#fbebdf; --str:#6b4fb3; --str-bg:#eee9f8;
  --rec:#9fb0c2; --tap:#c9a227; --race:#b3261e; --race-bg:#fbe6e4;
  --display:"Barlow Condensed","Arial Narrow",system-ui,sans-serif;
  --body:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,Menlo,monospace;
}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{
  --bg:#0f141b; --surface:#171e27; --ink:#e6ebf1; --muted:#97a3b2; --line:#2a3441; --soft:#1f2833; --accent:#4fb3d4;
  --swim:#5bb8e4; --swim-bg:#16303d; --bike:#7cc77f; --bike-bg:#1a3220; --run:#f0955a; --run-bg:#3a2516;
  --str:#a993ec; --str-bg:#2a2340; --rec:#56677a; --tap:#e0bf4f; --race:#f2766c; --race-bg:#3d1c1a; color-scheme:dark}}}}
:root[data-theme="dark"]{{
  --bg:#0f141b; --surface:#171e27; --ink:#e6ebf1; --muted:#97a3b2; --line:#2a3441; --soft:#1f2833; --accent:#4fb3d4;
  --swim:#5bb8e4; --swim-bg:#16303d; --bike:#7cc77f; --bike-bg:#1a3220; --run:#f0955a; --run-bg:#3a2516;
  --str:#a993ec; --str-bg:#2a2340; --rec:#56677a; --tap:#e0bf4f; --race:#f2766c; --race-bg:#3d1c1a; color-scheme:dark}}
html,body{{background:var(--bg);color:var(--ink)}}
body{{font-family:var(--body);font-size:14px;line-height:1.45;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:20px 40px}}
.wrap{{max-width:980px;margin:0 auto;display:grid;grid-template-columns:minmax(0,1fr);gap:18px}}
.eyebrow{{font:600 12px var(--body);letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}}
h1{{font:700 clamp(30px,6vw,44px)/1 var(--display);margin:4px 0 0;text-wrap:balance}}
.facts{{display:flex;flex-wrap:wrap;gap:8px 22px;margin-top:10px;font-variant-numeric:tabular-nums}}
.facts div{{display:grid}} .facts b{{font:700 22px/1.1 var(--display)}} .facts span{{font-size:12px;color:var(--muted)}}
.panel{{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:14px}}
.panel h2{{font:700 18px var(--display);margin:0 0 8px;letter-spacing:.02em}}
svg{{width:100%;height:auto;display:block}}
.grid{{stroke:var(--line);stroke-width:1}} .ax{{fill:var(--muted);font:500 10px var(--mono)}}
.b{{fill:var(--accent)}} .b.rec{{fill:var(--rec)}} .b.tap{{fill:var(--tap)}} .b.race{{fill:var(--race)}} .b.now{{stroke:var(--ink);stroke-width:2}}
.strip{{display:flex;gap:2px;margin-top:6px}}
.ph{{background:var(--soft);border-radius:3px;min-width:0;padding:4px 4px;font-size:11px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.legend{{display:flex;flex-wrap:wrap;gap:12px;font-size:12px;color:var(--muted);margin-top:8px}}
.legend i{{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px;vertical-align:-1px}}
.tools{{display:flex;flex-wrap:wrap;gap:8px;align-items:center}}
button{{font:500 13px var(--body);background:var(--surface);color:var(--ink);border:1px solid var(--line);border-radius:6px;padding:6px 10px;cursor:pointer}}
button:hover{{border-color:var(--accent)}} button:focus-visible,summary:focus-visible{{outline:2px solid var(--accent);outline-offset:2px}}
.wk{{background:var(--surface);border:1px solid var(--line);border-radius:10px}}
.wk.now{{border-color:var(--accent);box-shadow:0 0 0 1px var(--accent)}}
summary{{display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 12px;padding:10px 14px;cursor:pointer;list-style:none;font-variant-numeric:tabular-nums}}
summary::-webkit-details-marker{{display:none}}
summary::before{{content:"▸";color:var(--muted);transition:transform .15s}} details[open]>summary::before{{transform:rotate(90deg)}}
.wn{{font:700 19px var(--display);min-width:48px}} .wr{{color:var(--muted)}} .wp{{font-weight:500}}
.wh{{margin-left:auto;font:500 13px var(--mono)}}
.tag{{font-size:11px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;padding:2px 7px;border-radius:999px;background:var(--soft);color:var(--muted)}}
.tag.taper{{color:var(--tap)}} .tag.race{{color:var(--race);background:var(--race-bg)}} .tag.test{{color:var(--accent)}}
.tag.now{{background:var(--accent);color:var(--surface)}}
.focus{{margin:0 14px 6px;color:var(--ink)}} .rest{{margin:0 14px 8px;font-size:12px;color:var(--muted)}}
.tw{{overflow-x:auto;padding:0 6px 10px}}
table{{border-collapse:collapse;width:100%}}
td{{vertical-align:top;padding:8px 8px;border-top:1px solid var(--soft)}}
td.day{{width:52px;white-space:nowrap}} .dn{{font-weight:600}} .dd{{color:var(--muted);font-variant-numeric:tabular-nums}}
td.when{{width:64px;font-size:12px;color:var(--muted);white-space:nowrap}}
td.ses{{min-width:0}}
.t{{font-weight:600;display:flex;flex-wrap:wrap;gap:4px 8px;align-items:baseline}}
.dur{{margin-left:auto;font:500 12px var(--mono);color:var(--muted);white-space:nowrap}}
.chip{{font-style:normal;font-size:11px;font-weight:600;padding:1px 7px;border-radius:4px}}
tr.swim .chip{{background:var(--swim-bg);color:var(--swim)}} tr.bike .chip{{background:var(--bike-bg);color:var(--bike)}}
tr.run .chip{{background:var(--run-bg);color:var(--run)}} tr.str .chip{{background:var(--str-bg);color:var(--str)}}
tr.race .chip,tr.ev .chip{{background:var(--race-bg);color:var(--race)}}
.tg{{font:500 12px var(--mono);color:var(--accent);margin-top:3px}}
.dt{{color:var(--muted);margin-top:3px;font-size:13px}} .fu{{font-size:12px;color:var(--muted);margin-top:2px}}
.foot{{font-size:12px;color:var(--muted)}}
@media (max-width:560px){{td.when{{display:none}} td.day{{width:40px}} .wh{{margin-left:0}}}}
@media (prefers-reduced-motion:reduce){{summary::before{{transition:none}}}}
</style>
<div class="wrap">
  <header>
    <div class="eyebrow">Andrew Mizuno · 80/20 polarized · read-only</div>
    <h1>IRONMAN Cairns · 13 June 2027</h1>
    <div class="facts">
      <div><b>{nweeks}</b><span>weeks</span></div>
      <div><b>{total} h</b><span>planned total</span></div>
      <div><b>{maxh} h</b><span>biggest week</span></div>
      <div><b>{ftp} W</b><span>FTP</span></div>
      <div><b>{css}</b><span>CSS /100 m</span></div>
      <div><b>{blthr} / {lthr}</b><span>LTHR bike / run</span></div>
      <div><b id="cd">–</b><span>days to race</span></div>
    </div>
  </header>
  <section class="panel">
    <h2>Season load</h2>
    {chart}
    <div class="strip">{strip}</div>
    <div class="legend"><span><i style="background:var(--accent)"></i>Load</span><span><i style="background:var(--rec)"></i>Recovery</span><span><i style="background:var(--tap)"></i>Taper</span><span><i style="background:var(--race)"></i>Race</span><span>Key dates: T100 21 Mar · London 25 Apr · Cairns 13 Jun</span></div>
  </section>
  <div class="tools"><button id="now" type="button">Jump to this week</button><button id="all" type="button">Expand all</button><button id="none" type="button">Collapse all</button></div>
  {weeks}
  <p class="foot">{nsess} sessions, built from plan/plan.json on {gen}. Changes go through the plan pull request, then this page is rebuilt.</p>
</div>
<script>
(function(){{
  var today=new Date(); var iso=today.getFullYear()+"-"+String(today.getMonth()+1).padStart(2,"0")+"-"+String(today.getDate()).padStart(2,"0");
  var race=new Date(2027,5,13); var d=Math.ceil((race-new Date(today.getFullYear(),today.getMonth(),today.getDate()))/864e5);
  document.getElementById("cd").textContent=d>0?d:"Race done";
  var cur=null;
  document.querySelectorAll(".wk").forEach(function(w){{ if(iso>=w.dataset.start&&iso<=w.dataset.end){{cur=w;}} }});
  if(cur){{ cur.open=true; cur.classList.add("now"); var t=document.createElement("span"); t.className="tag now"; t.textContent="This week"; cur.querySelector("summary").insertBefore(t,cur.querySelector(".wh"));
    var r=document.querySelector('rect[data-wk="'+cur.id.slice(1)+'"]'); if(r) r.classList.add("now"); }}
  else {{ document.querySelector(".wk").open=true; }}
  document.getElementById("now").onclick=function(){{ if(cur){{cur.open=true;cur.scrollIntoView({{behavior:"smooth",block:"start"}});}} }};
  document.getElementById("all").onclick=function(){{ document.querySelectorAll(".wk").forEach(function(w){{w.open=true;}}); }};
  document.getElementById("none").onclick=function(){{ document.querySelectorAll(".wk").forEach(function(w){{w.open=false;}}); }};
  document.querySelectorAll("svg a").forEach(function(a){{ a.addEventListener("click",function(ev){{ var w=document.querySelector(a.getAttribute("href")); if(w){{ev.preventDefault(); w.open=true; w.scrollIntoView({{behavior:"smooth",block:"start"}});}} }}); }});
}})();
</script>
"""

if __name__ == "__main__":
    main()
