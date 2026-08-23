#!/usr/bin/env python
"""Does the LADDER-CALIBRATED ruler order k01 above k06, where the panel got it backwards?

Tonight's verdict (docs/RUNS.md 2026-08-23) falsified the local panel metric: it
gave kawashigi-k06 98.5% over 1,920 episodes and 60.8% over a 768-episode direct
head-to-head against topline/k01, and the converged ladder says k06 2035.9 against
topline 2302.2 -- backwards by 266 points.

That leaves one other local instrument: the rho table calibrated against 18 real
ladder scores, whose top predictor is hands@20 at rho = +0.96, ahead of strawberry
+0.88, herd@20 +0.84 and money +0.73. Those two recordings are both local files
(agents/champ/k01.py = topline = 55484175 = 2302.2, agents/champ/k06.py =
kawashigi-k06 = 55489160 = 2035.9), so the ruler can be tested on exactly the case
the panel failed.

PRE-REGISTERED, before running: the ladder ordering is topline > k06. If hands@20
ranks k06 >= k01, the rho table fails the same test the panel failed and NOTHING
local is currently known to order ladder strength -- which would mean bzt's
nine-opponent median cannot answer whether bzt is closer to 2000. If hands@20 puts
k01 above k06, it is the one instrument with demonstrated ladder-ordering validity
on the hardest available case, and it becomes the primary readout for bzt.

Both are open-loop replays of fixed episodes under the same MIT market layer, so
their behaviour is nearly deterministic given the seed; a handful of seeds suffices
and the seed-to-seed spread warning in docs/VALIDATING.md applies to STRATEGY
comparisons, not to reading a fixed recording's own build curve.

hands@20 is HELD CREW -- len(farm["hands"]) -- not intended hires. The tape records
intent and illegal actions are silent no-ops (docs/RUNS.md), so the count must come
off the observation, which is why byday.py's act["hands"] reader is not reused here.

    python probe_k01k06.py [--seeds 4] [--opp agents/bench3/closer_cleo.py]
"""

import argparse
import os
import sys

ROOT = "/scratch/jwj/Kaggriculture"
os.environ.setdefault("KG_FAST_ENV", "1")
sys.path.insert(0, ROOT)

TPD = 24          # turns per day
DAYS = 30


def run_one(agent, opp, seed, steps=720):
    """Per-day held crew / herd / standing crops / money, plus strawberry sold."""
    from kaggle_environments import make
    env = make("kaggriculture",
               configuration={"episodeSteps": steps, "seed": seed},
               debug=False)
    env.run([agent, opp])

    crew = [0] * (DAYS + 1)
    herd = [0] * (DAYS + 1)
    crops = [0] * (DAYS + 1)
    # 0, not None: 720 steps covers days 0..29, so day 30 is never written and a
    # None there breaks the cross-seed accumulator.
    money = [0] * (DAYS + 1)
    seen = [False] * (DAYS + 1)
    straw_orders = 0

    for i, st in enumerate(env.steps):
        d = min(DAYS, i // TPD)
        act = st[0].action
        if isinstance(act, dict):
            for o in (act.get("market") or []):
                # SELL of STRAWBERRY: orders, NOT settled volume -- the archive
                # records that `sold` is order count and only ~22% of fertiliser
                # orders ever cleared, so this is "wanted to sell", by design.
                if o and o[0] == "SELL" and len(o) > 1 and o[1] == "STRAWBERRY":
                    straw_orders += (o[2] if len(o) > 2 else 1)
        obs = st[0].observation
        farm = obs["farms"][0]
        crew[d] = max(crew[d], len(farm.get("hands") or []))
        if not seen[d]:
            seen[d] = True
            money[d] = farm["money"]
            na = nc = 0
            for row in farm["tiles"]:
                for t in row:
                    if isinstance(t, dict):
                        if "animal" in t:
                            na += 1
                        elif t.get("kind") == "PLANT":
                            nc += 1
            herd[d], crops[d] = na, nc
    final = env.steps[-1][0].observation["farms"][0]["money"]
    return crew, herd, crops, money, straw_orders, final


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=4)
    ap.add_argument("--opp", default="agents/bench3/closer_cleo.py")
    a = ap.parse_args()

    arms = [("topline/k01 (ladder 2302.2)", "agents/champ/k01.py"),
            ("kawashigi-k06 (ladder 2035.9)", "agents/champ/k06.py")]
    opp = os.path.join(ROOT, a.opp)

    print(f"opponent {a.opp}, {a.seeds} seeds")
    print("PRE-REGISTERED: ladder order is topline > k06 (2302.2 > 2035.9).")
    print("  hands@20 ranking k06 >= k01 => the rho table fails too, and no local")
    print("  instrument is known to order ladder strength.\n")

    rows = {}
    for label, rel in arms:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            sys.exit(f"missing {path}")
        acc = None
        for s in range(a.seeds):
            crew, herd, crops, money, straw, final = run_one(path, opp, 1000 + s)
            if acc is None:
                acc = [list(crew), list(herd), list(crops), list(money),
                       [straw], [final]]
            else:
                for k, v in enumerate((crew, herd, crops, money)):
                    for d in range(DAYS + 1):
                        acc[k][d] += v[d] or 0
                acc[4].append(straw)
                acc[5].append(final)
        n = a.seeds
        rows[label] = dict(
            crew=[c / n for c in acc[0]], herd=[h / n for h in acc[1]],
            crops=[c / n for c in acc[2]], money=[m / n for m in acc[3]],
            straw=sum(acc[4]) / n, final=sum(acc[5]) / n)

    names = [l for l, _ in arms]
    print(f"{'metric':<22}" + "".join(f"{n[:26]:>28}" for n in names))
    for key, day in (("crew", 20), ("herd", 20), ("crops", 20),
                     ("crew", 28), ("money", 20)):
        line = f"{key + '@' + str(day):<22}"
        for n in names:
            line += f"{rows[n][key][day]:>28,.1f}"
        print(line)
    for key in ("straw", "final"):
        line = f"{key:<22}"
        for n in names:
            line += f"{rows[n][key]:>28,.1f}"
        print(line)

    k01, k06 = names[0], names[1]
    h1, h6 = rows[k01]["crew"][20], rows[k06]["crew"][20]
    print(f"\nhands@20: k01 {h1:.2f} vs k06 {h6:.2f}")
    if h1 > h6:
        print("VERDICT: the rho table's top predictor ORDERS THEM AS THE LADDER DOES.")
    elif h1 == h6:
        print("VERDICT: TIED -- hands@20 cannot separate them; no ordering claim.")
    else:
        print("VERDICT: hands@20 ORDERS THEM BACKWARDS, same failure as the panel.")
    print("PROBE-DONE")


main()
