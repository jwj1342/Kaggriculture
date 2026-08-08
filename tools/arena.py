#!/usr/bin/env python
"""Local Kaggriculture arena.

Run head-to-head matches between agents and report win rate + final money.
Agents are given either as a builtin name ("pass", "random", "starter") or a
path to a .py file.

    python tools/arena.py agents/barnyard.py starter -n 6
    python tools/arena.py agents/barnyard.py agents/baseline_v0.py -n 10 -j 8

Seats are swapped every other game so a seat advantage cannot hide in the
result. Use -j to fan out across cores (do this inside a Slurm allocation,
never on the login node).
"""

import argparse
import json
import os
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor


def _play(args):
    a, b, seed, steps, swap = args
    from kaggle_environments import make

    env = make("kaggriculture", configuration={"episodeSteps": steps, "seed": seed})
    left, right = (b, a) if swap else (a, b)
    env.run([left, right])
    final = env.steps[-1]
    money = [float(s.reward or 0) for s in final]
    status = [s.status for s in final]
    if swap:
        money = money[::-1]
        status = status[::-1]
    return {"seed": seed, "swap": swap, "money": money, "status": status}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("agent_a")
    ap.add_argument("agent_b")
    ap.add_argument("-n", "--games", type=int, default=4)
    ap.add_argument("-s", "--steps", type=int, default=720)
    ap.add_argument("-j", "--jobs", type=int, default=1)
    ap.add_argument("--seed0", type=int, default=1000)
    ap.add_argument("-o", "--out", default=None, help="write per-game JSON here")
    args = ap.parse_args()

    jobs = [
        (args.agent_a, args.agent_b, args.seed0 + i, args.steps, i % 2 == 1)
        for i in range(args.games)
    ]

    t0 = time.time()
    if args.jobs > 1:
        with ProcessPoolExecutor(max_workers=args.jobs) as ex:
            results = list(ex.map(_play, jobs))
    else:
        results = [_play(j) for j in jobs]
    elapsed = time.time() - t0

    wins = losses = ties = 0
    a_money, b_money = [], []
    for r in results:
        ma, mb = r["money"]
        a_money.append(ma)
        b_money.append(mb)
        if ma > mb:
            wins += 1
        elif ma < mb:
            losses += 1
        else:
            ties += 1
        print(f"  seed {r['seed']:>5}  A={ma:>12,.0f}  B={mb:>12,.0f}  "
              f"{'WIN ' if ma > mb else 'LOSS' if ma < mb else 'TIE '}  {r['status']}")

    n = len(results)
    print()
    print(f"A = {args.agent_a}")
    print(f"B = {args.agent_b}")
    print(f"{n} games in {elapsed:.1f}s ({elapsed / max(1, n):.1f}s/game)")
    print(f"A record: {wins}W {losses}L {ties}T   winrate {wins / n:.1%}")
    print(f"A money : median {statistics.median(a_money):>12,.0f}  mean {statistics.mean(a_money):>12,.0f}  max {max(a_money):>12,.0f}")
    print(f"B money : median {statistics.median(b_money):>12,.0f}  mean {statistics.mean(b_money):>12,.0f}  max {max(b_money):>12,.0f}")

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w") as f:
            json.dump({"a": args.agent_a, "b": args.agent_b, "games": results}, f, indent=2)
        print(f"wrote {args.out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
