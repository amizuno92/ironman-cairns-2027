"""Copy the shareable parts of this repo into a public showcase folder.

Never copies data/, reports/, workouts/, tests/fixtures/ or anything personal.
Usage: python scripts/export_showcase.py <target_dir> [--generic-injury]
"""
import argparse
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INCLUDE = ["scripts", "plan/plan.py", "plan/build.py", "plan/plan.json", "rules.json", "RULES.md",
           ".github/workflows", "tests/test_pipeline.py", "boards/week1.html", "boards/week2.html",
           "boards/week3.html", "boards/liftlog.html", ".gitignore"]
SKIP_NAMES = {"__pycache__", "export_showcase.py"}

README = """# Ironman training pipeline

An automated, coach-style training system for a first full IRONMAN (Cairns, June 2027), built with Claude.

**What it does**
- **35-week periodised plan** (Base → Build → Peak → Taper) on 80/20 polarized principles, generated in Python (`plan/plan.py`) with hard rules enforced on every change (`scripts/check_plan.py`): ≤10% weekly increases, max 3 swims, daily time limits, graded return to run.
- **Daily sync** (GitHub Actions): pulls activities, interval data and wellness from intervals.icu.
- **Planned vs actual** (`scripts/compliance.py`): matches each session to the plan, even when moved to another day, and checks duration, power bands, interval reps, HR caps, swim pace, decoupling and recovery markers (resting HR, HRV).
- **Tomorrow's workout**: generates Zwift `.zwo` files (power as % FTP) and swim sets automatically.
- **AI coaching reviews**: a scheduled Claude session reads the numbers every evening, writes a daily report and sends a push notification; on Sundays it reviews the week and proposes plan changes **as a pull request** that has to pass the rule checks.
- **Interactive week boards and a lift log** (`boards/`) for rearranging sessions and tracking strength.

Personal training data, reports and credentials live in a separate private repo; this copy has the code, plan and rules only.

## Run it yourself
1. Add `INTERVALS_API_KEY` and `INTERVALS_ATHLETE_ID` as Actions secrets.
2. Edit `plan/plan.py` (athlete numbers at the top), then `python scripts/export_plan.py && python scripts/check_plan.py`.
3. Run the **Daily sync** workflow.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--generic-injury", action="store_true", help="replace injury specifics with generic wording")
    a = ap.parse_args()
    dst = Path(a.target)
    for item in INCLUDE:
        src = ROOT / item
        if not src.exists():
            continue
        out = dst / item
        if src.is_dir():
            if out.exists():
                shutil.rmtree(out)
            shutil.copytree(src, out, ignore=lambda d, names: [n for n in names if n in SKIP_NAMES])
        else:
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, out)
    (dst / "README.md").write_text(README)
    # The showcase has no secrets: disable the scheduled runs so it never tries to sync.
    for wf in (dst / ".github" / "workflows").glob("*.yml"):
        txt = wf.read_text()
        txt = re.sub(r"  schedule:\n(    - cron: .*\n)+", "", txt)
        wf.write_text(txt)
    if a.generic_injury:
        for p in dst.rglob("*"):
            if p.is_file() and p.suffix in (".py", ".json", ".md", ".html"):
                t = p.read_text()
                t2 = re.sub(r"tibia(l)? stress fracture", "previous running injury", t, flags=re.I)
                t2 = re.sub(r"\btibia\b", "injury", t2, flags=re.I)
                if t2 != t:
                    p.write_text(t2)
    print(f"Showcase exported to {dst}")


if __name__ == "__main__":
    main()
