#!/usr/bin/env python
"""The four acceptance numbers for an arm, measured the same way every time.

A roster JSON carries money and shop draws, not behaviour. But the money moves
LAST -- penner's actions fired (hand PLACE 0 -> 4, BUILD 2 -> 25) while its herd
fell from 6 to 4 and its median sat inside the band. So each arm is read on
behaviour as well, and this exists so those numbers come out of one code path
rather than a fresh throwaway script per arm.

The four, with the baselines they are judged against (docs/RUNS.md 2026-08-22):

  land          unlocked quadrants at day 18. Baseline 2.0, the ladder tier 3.0.
  crew          hands per turn, averaged over the episode. Baseline 7.9; the
                tier runs 8.4-8.6 and the fibonacci break-even is 8.
  seeds         seeds bought in a whole game. Baseline 47, k06 207. This is the
                measured deficit the seedsman / bulkhead arms attack.
  bare tiles    empty UNLOCKED tiles at day 18 and day 28. Baseline 18 and 27,
                k06 2 and 5 -- it never leaves land idle, we hold it bare.
  margin        our final money minus the opponent's, over a FULL game from day
                0. This is the ruler for every curriculum arm (d0-chisel,
                d0-d12, backplay-d8): it must beat chisel's -54,849.

Also reported because they are cheap and were load-bearing tonight: standing
crops and animals at day 18 (penner's herd regression showed up here first), and
the melon/strawberry seed split, since croftr's --demand-cap is expected to move
melon down specifically.

NOT reported: WATER / HARVEST / units-sold counts. They track tile count, so
their absolute values are a consequence rather than a cause -- reading them as a
cause is how the withdrawn --dry-risk arm got built.

    python tools/arm_behaviour.py <agent.py> [more agents...] [--seeds N]
                                 [--opp agents/bench3/closer_cleo.py]
"""

import argparse
import collections
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def measure(agent, opp, seed, steps=720):
    from kaggle_environments import make
    env = make("kaggriculture",
               configuration={"episodeSteps": steps, "seed": seed},
               debug=False)
    env.run([agent, opp])
    tpd = 24
    out = {}
    seeds_bought = collections.Counter()
    hands = []
    for i, st in enumerate(env.steps):
        act = st[0].action
        if isinstance(act, dict):
            for o in (act.get("market") or []):
                if o and o[0] == "BUY_SEED" and len(o) > 2:
                    seeds_bought[o[1]] += o[2]
        farm = st[0].observation["farms"][0]
        h = farm.get("hands")
        if h is not None:
            hands.append(len(h))

    def snap(day):
        st = env.steps[min(day * tpd + 8, len(env.steps) - 1)]
        farm = st[0].observation["farms"][0]
        crop = animal = bare = 0
        for row in farm["tiles"]:
            for t in row:
                if t is None:
                    bare += 1
                elif isinstance(t, dict):
                    if t.get("kind") == "PLANT":
                        crop += 1
                    elif "animal" in t:
                        animal += 1
        return {"land": len(farm["unlocked_quadrants"]), "crop": crop,
                "animal": animal, "bare": bare}

    out["d18"] = snap(18)
    out["d28"] = snap(28)
    out["crew"] = sum(hands) / max(len(hands), 1)
    out["seeds"] = sum(seeds_bought.values())
    out["melon"] = seeds_bought.get("MELON", 0)
    out["straw"] = seeds_bought.get("STRAWBERRY", 0)
    ours = env.steps[-1][0].observation["farms"][0]["money"]
    theirs = env.steps[-1][1].observation["farms"][1]["money"]
    out["money"] = ours
    # the day-0 FULL-GAME margin, which is the acceptance ruler for every
    # curriculum arm (d0-chisel, d0-d12, backplay-d8): it must beat chisel's
    # -54,849. Reported here so it is not re-derived ad hoc per arm.
    out["margin"] = ours - theirs
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("agents", nargs="+")
    ap.add_argument("--opp", default=f"{ROOT}/agents/bench3/closer_cleo.py")
    ap.add_argument("--seeds", type=int, default=2)
    a = ap.parse_args()

    print(f"\nvs {os.path.basename(a.opp)}, {a.seeds} seeds\n")
    print(f"  {'agent':<26}{'land':>5}{'crew':>6}{'seeds':>7}{'melon':>6}"
          f"{'straw':>6}{'bare d18':>9}{'bare d28':>9}{'crop':>6}{'herd':>6}"
          f"{'money':>10}{'margin':>11}")
    for ag in a.agents:
        name = os.path.basename(os.path.dirname(ag)) or os.path.basename(ag)
        acc = collections.defaultdict(float)
        for i in range(a.seeds):
            m = measure(ag, a.opp, 10_000 + 977 * i)
            acc["land"] += m["d18"]["land"] / a.seeds
            acc["crew"] += m["crew"] / a.seeds
            acc["seeds"] += m["seeds"] / a.seeds
            acc["melon"] += m["melon"] / a.seeds
            acc["straw"] += m["straw"] / a.seeds
            acc["b18"] += m["d18"]["bare"] / a.seeds
            acc["b28"] += m["d28"]["bare"] / a.seeds
            acc["crop"] += m["d18"]["crop"] / a.seeds
            acc["herd"] += m["d18"]["animal"] / a.seeds
            acc["money"] += m["money"] / a.seeds
            acc["margin"] += m["margin"] / a.seeds
        print(f"  {name[:26]:<26}{acc['land']:>5.1f}{acc['crew']:>6.2f}"
              f"{acc['seeds']:>7.0f}{acc['melon']:>6.0f}{acc['straw']:>6.0f}"
              f"{acc['b18']:>9.0f}{acc['b28']:>9.0f}{acc['crop']:>6.0f}"
              f"{acc['herd']:>6.0f}{acc['money']:>10,.0f}"
              f"{acc['margin']:>+11,.0f}")
    print(f"\n  baselines: land 2.0 (tier 3.0) | crew 7.9 (tier 8.4-8.6) | "
          f"seeds 47 (k06 207)")
    print(f"             bare d18 18 / d28 27 (k06 2 / 5) | herd 6 (tier 14)")
    print(f"             day-0 full-game MARGIN must beat chisel's -54,849 "
          f"(the curriculum arms' ruler)")
    print("ARM-BEHAVIOUR-DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
