# IRONMAN Cairns 2027

Andrew's 35-week plan (12 Oct 2026 → 13 Jun 2027), training data and automated coaching reviews.

## How it runs

| When (Brisbane) | What | How |
|---|---|---|
| Daily ~7:55pm (started by the review; 7:37pm backup timer) | Pull activities, intervals and wellness from intervals.icu; compare with the plan; build tomorrow's Zwift file and swim set | GitHub Action `daily.yml` |
| Daily ~8pm | Coaching review → `reports/daily/`, push notification | Claude scheduled task |
| Sunday ~8:20pm (started by the review; 7:52pm backup timer) | Weekly summary; next week's workouts | GitHub Action `weekly.yml` |
| Sunday ~8:20pm | Weekly review → `reports/weekly/`; plan changes as a pull request | Claude scheduled task |
| Every plan PR | Rule checks (10% cap, swims, daily limits) and workout build tests | GitHub Action `checks.yml` |

## Setup
1. intervals.icu → Settings → Developer Settings → copy the **API key** and your **athlete ID** (`i…`).
2. GitHub repo → Settings → Secrets and variables → Actions → add `INTERVALS_API_KEY` and `INTERVALS_ATHLETE_ID`.
3. Actions tab → **Daily sync** → Run workflow (first run: set days to 30 to backfill).

## Layout
```
plan/        plan.py (source of truth), plan.json (generated), build.py → the .xlsx
rules.json   thresholds; RULES.md explains them
scripts/     sync_intervals, compliance, make_workouts, weekly_summary, export_plan, check_plan
data/        activities/ intervals/ wellness/ compliance/ weekly/ lifts/ tests/
reports/     daily/ weekly/ blocks/
workouts/    zwo/ (Zwift custom workouts) swim/ (sets)
boards/      interactive week boards and lift log (also published as Claude artifacts)
CLAUDE.md    instructions for the review sessions
```

## Using the Zwift files
Download `workouts/zwo/*.zwo` into `~/Documents/Zwift/Workouts/8422202/` and restart Zwift. Power is % of FTP, so it follows your in-game FTP.

## Changing the plan
Edit `plan/plan.py`, then:
```
python scripts/export_plan.py && python scripts/check_plan.py && (cd plan && python build.py)
```

## Zwift auto-sync on the Mac
`tools/mac/` holds a tiny launchd job that copies new or changed `.zwo` files from this repo into Zwift every 30 minutes and at login.
Install once in Terminal: `bash ~/Documents/Zwift/Workouts/.ironman-sync/install.sh` (the scripts live in that folder). Remove with `uninstall.sh`. Log: `~/Documents/Zwift/Workouts/.ironman-sync/sync.log`.
