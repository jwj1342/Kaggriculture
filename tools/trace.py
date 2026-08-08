#!/usr/bin/env python
"""Play one episode and print a day-by-day trace of one player's farm.

    python tools/inspect.py agents/barnyard.py starter
"""

import argparse
import sys
from collections import Counter


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("agent_a")
    ap.add_argument("agent_b", nargs="?", default="starter")
    ap.add_argument("-p", "--player", type=int, default=0)
    ap.add_argument("-s", "--steps", type=int, default=720)
    ap.add_argument("--seed", type=int, default=1000)
    args = ap.parse_args()

    from kaggle_environments import make

    env = make("kaggriculture", configuration={"episodeSteps": args.steps, "seed": args.seed}, debug=True)
    env.run([args.agent_a, args.agent_b])

    p = args.player
    print(f"{'day':>3} {'money':>9} {'hands':>5} {'land':>4} | {'tiles':<34} | "
          f"{'shed':<30} | prices")
    for step_idx in range(8, len(env.steps), 24):   # hour 8: hands are live
        st = env.steps[step_idx]
        obs = st[p].observation
        farm = obs["farms"][p]
        priv = obs["private"]
        crops, animals, structs, weeds, empty = Counter(), Counter(), Counter(), 0, 0
        for row in farm["tiles"]:
            for t in row:
                if t is None:
                    empty += 1
                elif isinstance(t, dict):
                    if t.get("kind") == "PLANT":
                        crops[t["crop"][:2]] += 1
                    elif t.get("kind") == "WEED":
                        weeds += 1
                    elif "animal" in t:
                        animals[t["animal"][:2]] += 1
                    else:
                        structs[t["kind"][:2]] += 1
        tile_s = " ".join(f"{k}{v}" for k, v in sorted(crops.items()))
        tile_s += " | " + " ".join(f"{k}{v}" for k, v in sorted(animals.items()))
        if structs:
            tile_s += " s:" + " ".join(f"{k}{v}" for k, v in sorted(structs.items()))
        tile_s += f" w{weeds} e{empty}"
        shed = {k: v for k, v in priv["shed"].items() if v}
        shed_s = " ".join(f"{k[:2]}{v}" for k, v in sorted(shed.items()))
        pr = obs["market"]["prices"]
        pr_s = " ".join(f"{k[:2]}{pr[k]}" for k in ("MELON", "MILK", "WOOL", "FERTILIZER", "WHEAT", "EGG"))
        print(f"{step_idx // 24:>3} {farm['money']:>9,.0f} {len(farm['hands']):>5} "
              f"{len(farm['unlocked_quadrants']):>4} | {tile_s:<34} | {shed_s:<30} | {pr_s}")

    final = env.steps[-1]
    print()
    for i, s in enumerate(final):
        print(f"Player {i}: reward={s.reward:,.0f} status={s.status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
