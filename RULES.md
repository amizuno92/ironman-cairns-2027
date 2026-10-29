# Training rules

Numbers live in `rules.json`; `scripts/check_plan.py` enforces the hard ones on every plan pull request.

| Rule | Value | Why |
|---|---|---|
| Weekly hours (load weeks) | ≤ +10% vs previous load week | Progressive overload without spikes |
| Weekly run km (from wk 9) | ≤ +10% | Bone stress injury history |
| Walk-run phase | weeks 3–8, alternate days only | Graded tibia return |
| Run intensity | from week 16, only if week-14 checkpoint clean | Bone first |
| Tibia stop rule | pain >2/10 during or any next morning → stop, 2 days off, regress one stage | Non-negotiable |
| Swims | max 3/week, midday only | Athlete schedule |
| Daily time | weekdays ≤2 h, weekend days ≤8 h | Availability |
| Intensity split | ~80/20 by time; Z3 kept minimal | Polarized method |
| IM power | 66–71% FTP to wk 14; 70–75% from wk 15 | Sub-11 target |
| Missed sessions | drop, don't cram | Fatigue control |
| Plan changes | pull request only, with reasons; checks must pass | Nothing changes silently |

## Daily flags (from `scripts/compliance.py`)
- **stop**: pain or soreness words in activity notes.
- **warn**: >20% over planned duration, easy ride NP above band, HR above cap, missed interval reps, runs on back-to-back days in walk-run phase, run km jump >10%, resting HR up ≥5 bpm or HRV down ≥20% for 2 days.
- **info**: short session, reps under/over band, decoupling >5% on rides ≥75′, no HR data, swim much faster than aerobic band, unplanned session, day over time limit.

## Sub-11 checkpoints
FTP 252 W (wk 6) → 260 W (wk 14) → 268 W (wk 22). T100 test: 80 km at ~200 W NP, HR ≤150, then a strong 18 km.
