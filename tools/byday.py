#!/usr/bin/env python
"""WHERE in the season does our net lose the money? Day by day, on CPU.

Load-bearing for the G1 gate (rl/TODO.md "里程碑门"): G1 asks whether our net, placed
after cleo's opening, does that opening any harm. The pair to compare is therefore
`closer_cleo` continuing itself against `hybrid-cleo12` (cleo's first 12 days, then our
net), on identical seeds against an identical opponent. Because both share the first
288 steps by construction, the per-day money curves must be element-wise EQUAL until
day 12 and only diverge after -- that equality is a built-in check that the
measurement itself is sound, so read it before reading the gap.

Two facts sit in tension. The flat-loss verdict says our net loses ~2,100 a day
regardless of how many days it plays. But the hybrids say hybrid-d12net20
(12 borrowed days) beats hybrid-endgame20 (20 borrowed days), 90,788 to 88,810 --
so the net's own play from day 12 onward is BETTER than closer_cleo's from day 12
onward, and the deficit must be front-loaded.

Both cannot be right in the same sense. This resolves it by reading money and
actions per day off real episodes rather than from either summary.

    python byday.py <agent.py> [more agents...] [--seeds N]
"""

import argparse
import collections
import os
import sys

ROOT = "/scratch/jwj/Kaggriculture"
DAYS = 30


def run_one(agent, opp, seed, steps=720):
    from kaggle_environments import make
    env = make("kaggriculture",
               configuration={"episodeSteps": steps, "seed": seed},
               debug=False)
    env.run([agent, opp])
    tpd = 24
    money = [None] * (DAYS + 1)
    tiles = [0] * (DAYS + 1)
    animals = [0] * (DAYS + 1)
    # per-day action counts for the interesting ops
    ops = [collections.Counter() for _ in range(DAYS + 1)]
    for i, st in enumerate(env.steps):
        d = min(DAYS, i // tpd)
        act = st[0].action
        if isinstance(act, dict):
            f = act.get("farmer")
            if f:
                ops[d][f[0]] += 1
            for h in (act.get("hands") or []):
                if h:
                    ops[d][h[0]] += 1
            for o in (act.get("market") or []):
                if o and o[0] == "BUY_SEED":
                    ops[d]["_SEED"] += (o[2] if len(o) > 2 else 1)
                elif o and o[0] == "SELL":
                    ops[d]["_SELL"] += (o[2] if len(o) > 2 else 1)
        obs = st[0].observation
        farm = obs["farms"][0]
        if money[d] is None:
            money[d] = farm["money"]
            np_, na = 0, 0
            for row in farm["tiles"]:
                for t in row:
                    if isinstance(t, dict):
                        if t.get("kind") == "PLANT":
                            np_ += 1
                        elif "animal" in t:
                            na += 1
            tiles[d], animals[d] = np_, na
    return money, tiles, animals, ops


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("agents", nargs="+")
    ap.add_argument("--opp", default=f"{ROOT}/agents/bench3/closer_cleo.py")
    ap.add_argument("--seeds", type=int, default=2)
    a = ap.parse_args()

    table = {}
    for ag in a.agents:
        name = os.path.basename(os.path.dirname(ag)) or os.path.basename(ag)
        acc_m = [0.0] * (DAYS + 1)
        acc_t = [0.0] * (DAYS + 1)
        acc_a = [0.0] * (DAYS + 1)
        acc_o = [collections.Counter() for _ in range(DAYS + 1)]
        for i in range(a.seeds):
            m, t, an, ops = run_one(ag, a.opp, 10_000 + 977 * i)
            for d in range(DAYS + 1):
                if m[d] is not None:
                    acc_m[d] += m[d] / a.seeds
                acc_t[d] += t[d] / a.seeds
                acc_a[d] += an[d] / a.seeds
                acc_o[d].update(ops[d])
        table[name] = (acc_m, acc_t, acc_a, acc_o)

    names = list(table)
    print(f"\nmoney by day ({a.seeds} seeds, vs "
          f"{os.path.basename(a.opp)}):")
    print(f"  {'day':>4}" + "".join(f"{n[:16]:>18}" for n in names))
    for d in range(0, DAYS + 1, 2):
        row = "".join(f"{table[n][0][d]:>18,.0f}" for n in names)
        print(f"  {d:>4}{row}")

    print(f"\nPLANT tiles standing / animals, by day:")
    print(f"  {'day':>4}" + "".join(f"{n[:16]:>18}" for n in names))
    for d in range(0, DAYS + 1, 3):
        row = "".join(f"{table[n][1][d]:>10,.0f} /{table[n][2][d]:>6,.0f}"
                      for n in names)
        print(f"  {d:>4}{row}")

    for key, label in (("WATER", "WATER actions"), ("_SEED", "seeds bought"),
                       ("PLANT", "PLANT actions"), ("_SELL", "units sold")):
        print(f"\n{label}, by day:")
        print(f"  {'day':>4}" + "".join(f"{n[:16]:>18}" for n in names))
        for d in range(0, DAYS + 1, 3):
            row = "".join(f"{table[n][3][d][key]/a.seeds:>18,.0f}"
                          for n in names)
            print(f"  {d:>4}{row}")

    print("\ncumulative money gap vs the first agent listed:")
    base = table[names[0]][0]
    print(f"  {'day':>4}" + "".join(f"{n[:16]:>18}" for n in names[1:]))
    for d in range(0, DAYS + 1, 2):
        row = "".join(f"{table[n][0][d]-base[d]:>+18,.0f}" for n in names[1:])
        print(f"  {d:>4}{row}")
    print("BYDAY-DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
