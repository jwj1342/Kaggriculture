#!/usr/bin/env python
"""Sweep module-level tunables of an agent file.

Generates a variant of the agent per configuration by rewriting `NAME = value`
lines, plays it against a fixed opponent over several seeds, and reports the
mean/median final money.

    python tools/sweep.py agents/barnyard.py -n 3 -j 8 \
        --set HAND_CAP=8,10,12,14 --set TARGET_COWS=10,12,16

Each --set is swept independently against the file's current defaults (a
coordinate sweep, not a full grid) unless --grid is passed.
"""

import argparse
import itertools
import os
import re
import statistics
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor


def _variant(src_text, overrides, out_dir, tag):
    text = src_text
    for name, value in overrides.items():
        pat = re.compile(rf"^{re.escape(name)}\s*=\s*[^\n#]+", re.M)
        if not pat.search(text):
            raise SystemExit(f"tunable {name!r} not found at module level")
        text = pat.sub(f"{name} = {value}", text, count=1)
    path = os.path.join(out_dir, f"v_{tag}.py")
    with open(path, "w") as f:
        f.write(text)
    return path


def _play(job):
    path, opp, seed, steps = job
    from kaggle_environments import make

    env = make("kaggriculture", configuration={"episodeSteps": steps, "seed": seed})
    env.run([path, opp])
    final = env.steps[-1]
    return float(final[0].reward or 0), float(final[1].reward or 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("agent")
    ap.add_argument("--opponent", default="starter")
    ap.add_argument("--set", action="append", default=[], metavar="NAME=v1,v2")
    ap.add_argument("--grid", action="store_true", help="full cartesian product")
    ap.add_argument("-n", "--games", type=int, default=3)
    ap.add_argument("-j", "--jobs", type=int, default=4)
    ap.add_argument("-s", "--steps", type=int, default=720)
    ap.add_argument("--seed0", type=int, default=1000)
    args = ap.parse_args()

    with open(args.agent) as f:
        src = f.read()

    axes = []
    for spec in args.set:
        name, _, values = spec.partition("=")
        axes.append((name.strip(), [v.strip() for v in values.split(",")]))

    configs = [{}]
    if args.grid:
        configs = [dict(zip([a[0] for a in axes], combo))
                   for combo in itertools.product(*[a[1] for a in axes])]
    else:
        configs = []
        for name, values in axes:
            for v in values:
                configs.append({name: v})

    tmp = tempfile.mkdtemp(prefix="kgsweep_")
    jobs, index = [], []
    for ci, cfg in enumerate(configs):
        tag = "_".join(f"{k}{v}" for k, v in cfg.items()) or "base"
        tag = re.sub(r"[^A-Za-z0-9_]", "", tag)
        path = _variant(src, cfg, tmp, f"{ci}_{tag}")
        for g in range(args.games):
            jobs.append((path, args.opponent, args.seed0 + g, args.steps))
            index.append(ci)

    with ProcessPoolExecutor(max_workers=args.jobs) as ex:
        results = list(ex.map(_play, jobs))

    by_cfg = {}
    for ci, (a, b) in zip(index, results):
        by_cfg.setdefault(ci, []).append((a, b))

    rows = []
    for ci, cfg in enumerate(configs):
        vals = by_cfg.get(ci, [])
        mine = [a for a, _ in vals]
        wins = sum(1 for a, b in vals if a > b)
        rows.append((statistics.median(mine), statistics.mean(mine), wins, len(vals), cfg))
    rows.sort(key=lambda r: r[0], reverse=True)

    print(f"{'median':>10} {'mean':>10} {'W/N':>7}  config")
    for med, mean, wins, n, cfg in rows:
        label = ", ".join(f"{k}={v}" for k, v in cfg.items()) or "(defaults)"
        print(f"{med:>10,.0f} {mean:>10,.0f} {wins:>3}/{n:<3}  {label}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
