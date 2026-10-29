"""Smoke tests: every bike session builds a valid Zwift file of the planned length,
and compliance runs on the real week-3 fixtures. Run: python tests/test_pipeline.py"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import xml.dom.minidom
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import make_workouts as M  # noqa: E402
from common import load_plan  # noqa: E402

fail = 0
n = 0
for s in load_plan()["sessions"]:
    if s["sport"] != "Bike":
        continue
    steps, note = M.steps_for(s)
    if not steps:
        continue
    n += 1
    x = "".join(steps)
    tot = sum(int(v) for v in re.findall(r'<(?:SteadyState|Warmup|Cooldown) Duration="(\d+)"', x))
    tot += sum(int(r) * (int(a) + int(b)) for r, a, b in re.findall(r'Repeat="(\d+)" OnDuration="(\d+)" OffDuration="(\d+)"', x))
    xml.dom.minidom.parseString(M.zwo(s, steps, note))
    if abs(tot / 60 - s["duration_min"]) > 2 or re.search(r'Duration="-', x):
        print("FAIL zwo", s["id"], s["duration_min"], round(tot / 60, 1))
        fail += 1
print(f"zwo: {n} files checked")

# compliance on fixtures in a temp copy of the repo (skipped where fixtures aren't shipped)
if not (ROOT / "tests" / "fixtures" / "activities").exists():
    print("compliance: fixtures not present, skipped")
    print("OK" if not fail else f"{fail} failures")
    sys.exit(1 if fail else 0)
tmp = Path(tempfile.mkdtemp())
shutil.copytree(ROOT, tmp / "repo", ignore=shutil.ignore_patterns(".git"))
repo = tmp / "repo"
for sub in ("activities", "wellness", "intervals"):
    shutil.rmtree(repo / "data" / sub, ignore_errors=True)
    shutil.copytree(repo / "tests" / "fixtures" / sub, repo / "data" / sub)
subprocess.run([sys.executable, "scripts/compliance.py", "--date", "2026-10-27"], cwd=repo, check=True)
c = json.loads((repo / "data" / "compliance" / "2026-10-27.json").read_text())
bike = [s for s in c["sessions"] if s.get("kind") == "bike_intervals"]
if not bike or bike[0]["reps"]["done_reps"] != 5 or abs(bike[0]["reps"]["avg_rep_w"] - 269.4) > 0.5:
    print("FAIL compliance: VO2 reps not detected", bike)
    fail += 1
shutil.rmtree(tmp)
print("OK" if not fail else f"{fail} failures")
sys.exit(1 if fail else 0)
