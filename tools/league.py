#!/usr/bin/env python
"""Local round-robin league for Kaggriculture agents.

Runs every pair of agents against each other over many seeds and both seats,
then fits **Bradley-Terry** strengths by maximum likelihood -- the same
estimator Kaggle uses to produce the final leaderboard. Local BT ratings are
therefore directly comparable in kind to the thing that decides the prize,
unlike a raw mean-money number.

    # four agents, 32 seeds per pair, both seats
    python tools/league.py pass random starter agents/barnyard.py --seeds 32 -j 32

    # auto-generate variants of one agent to probe a tunable
    python tools/league.py agents/barnyard.py starter \
        --variants agents/barnyard.py:TARGET_COWS=6,10,14 --seeds 32 -j 32

Throughput: ~2.7 s per episode per core. On 32 cores that is ~42,000
episodes/hour, so a 6-agent round robin at 64 seeds (~1,900 episodes) takes
about three minutes.

Output
------
* win matrix (row beats column, %)
* Bradley-Terry strengths, rendered on an Elo-like scale
* per-agent money distribution, to separate "wins a lot" from "earns a lot"
* JSON dump of every episode for mining patterns and defects
"""

import argparse
import itertools
import json
import math
import os
import re
import statistics
import sys
import tempfile
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stats import bradley_terry


def _play(job):
    left, right, seed, steps = job
    from kaggle_environments import make

    env = make("kaggriculture", configuration={"episodeSteps": steps, "seed": seed})
    env.run([left, right])
    final = env.steps[-1]
    obs = final[0].observation
    return {
        "left": left, "right": right, "seed": seed,
        "money": [float(s.reward or 0) for s in final],
        "status": [str(s.status) for s in final],
        "shops": list(obs["town"]["unlocked_shops"]),
        "prices": dict(obs["market"]["prices"]),
    }


def make_variants(spec, out_dir):
    """'path:NAME=v1,v2' -> list of generated agent files."""
    path, _, rest = spec.partition(":")
    name, _, values = rest.partition("=")
    with open(path) as f:
        src = f.read()
    pat = re.compile(rf"^{re.escape(name)}\s*=\s*[^\n#]+", re.M)
    if not pat.search(src):
        raise SystemExit(f"tunable {name!r} not found at module level in {path}")
    made = []
    base = os.path.splitext(os.path.basename(path))[0]
    for v in values.split(","):
        v = v.strip()
        text = pat.sub(f"{name} = {v}", src, count=1)
        p = os.path.join(out_dir, f"{base}__{name}_{re.sub(r'[^A-Za-z0-9]', '', v)}.py")
        with open(p, "w") as f:
            f.write(text)
        made.append(p)
    return made


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("agents", nargs="*", help="builtin name or path to a .py agent")
    ap.add_argument("--variants", action="append", default=[],
                    metavar="PATH:NAME=v1,v2", help="auto-generate tunable variants")
    ap.add_argument("--seeds", type=int, default=32, help="seeds per ordered pair")
    ap.add_argument("--seed0", type=int, default=20_000)
    ap.add_argument("-s", "--steps", type=int, default=720)
    ap.add_argument("-j", "--jobs", type=int, default=8)
    ap.add_argument("-o", "--out", default=None, help="write per-episode JSON here")
    args = ap.parse_args()

    tmp = tempfile.mkdtemp(prefix="kgleague_")
    roster = list(args.agents)
    for spec in args.variants:
        roster.extend(make_variants(spec, tmp))
    if len(roster) < 2:
        raise SystemExit("need at least two agents")

    short = {a: (os.path.splitext(os.path.basename(a))[0] if a.endswith(".py") else a)
             for a in roster}

    jobs = []
    for a, b in itertools.combinations(roster, 2):
        for i in range(args.seeds):
            s = args.seed0 + i
            jobs.append((a, b, s, args.steps))   # a as player 0
            jobs.append((b, a, s, args.steps))   # seats swapped
    print(f"{len(roster)} agents, {len(jobs)} episodes "
          f"({len(roster)*(len(roster)-1)//2} pairs x {args.seeds} seeds x 2 seats)")

    with ProcessPoolExecutor(max_workers=args.jobs) as ex:
        results = list(ex.map(_play, jobs))

    wins, games = defaultdict(float), defaultdict(int)
    money = defaultdict(list)
    bad = []
    for r in results:
        L, R = r["left"], r["right"]
        ml, mr = r["money"]
        if any(st != "DONE" for st in r["status"]):
            bad.append(r)
        money[L].append(ml)
        money[R].append(mr)
        games[(L, R)] += 1
        games[(R, L)] += 1
        if ml > mr:
            wins[(L, R)] += 1
        elif mr > ml:
            wins[(R, L)] += 1
        else:
            wins[(L, R)] += 0.5
            wins[(R, L)] += 0.5

    if bad:
        print(f"\n!! {len(bad)} episodes did not finish cleanly "
              f"(e.g. {bad[0]['status']} in {short[bad[0]['left']]} vs {short[bad[0]['right']]})")

    names = roster
    width = max(len(short[a]) for a in names) + 1

    print("\n=== win matrix (row's win rate vs column) ===")
    print(" " * width + "".join(f"{short[c][:9]:>10s}" for c in names))
    for a in names:
        row = f"{short[a]:<{width}s}"
        for b in names:
            if a == b:
                row += f"{'--':>10s}"
            else:
                g = games.get((a, b), 0)
                row += f"{wins.get((a,b),0)/g:>9.0%} " if g else f"{'-':>10s}"
        print(row)

    p = bradley_terry(wins, games, names)
    # Render BT strengths on an Elo-like scale (400 per factor-of-10 odds).
    ref = statistics.median(p.values())
    elo = {n: 400 * math.log10(max(p[n], 1e-12) / ref) for n in names}
    order = sorted(names, key=lambda n: -elo[n])

    print("\n=== Bradley-Terry ranking (same estimator as the official final leaderboard) ===")
    print(f"{'#':>2}  {'agent':<{width}s} {'BT-Elo':>8s} {'strength':>9s} "
          f"{'winrate':>8s} {'median $':>10s} {'sd $':>9s}")
    for i, n in enumerate(order, 1):
        tot_g = sum(games.get((n, m), 0) for m in names if m != n)
        tot_w = sum(wins.get((n, m), 0.0) for m in names if m != n)
        ms = money[n]
        print(f"{i:>2}  {short[n]:<{width}s} {elo[n]:>+8.0f} {p[n]:>9.3f} "
              f"{tot_w/tot_g:>8.1%} {statistics.median(ms):>10,.0f} "
              f"{statistics.pstdev(ms):>9,.0f}")

    print("\n  BT-Elo is relative to the median agent in this pool; +400 means "
          "10:1 odds.")
    print("  A high win rate with a low median $ means the agent wins by denying "
          "the market,\n  not by earning -- worth checking, since the ladder only "
          "counts wins.")

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w") as f:
            json.dump({"roster": roster, "short": short,
                       "bt": {short[n]: p[n] for n in names},
                       "elo": {short[n]: elo[n] for n in names},
                       "episodes": results}, f, indent=1)
        print(f"\n  wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
