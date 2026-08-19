#!/usr/bin/env python
"""Collect behaviour-cloning data from the scripted expert (README §8).

    python rl/collect_bc.py --episodes 160 --jobs 28 --out rl/runs/bc/data

Each worker plays full episodes with rl/scripted.py through the exact
mask/decode path the learner uses and appends (obs f16, masks, action indices)
to one npz shard per worker. Opponent mix and seats are randomised; seeds stay
in the training band (< 10_000).
"""

import argparse
import os
import sys
from multiprocessing import Pool

import numpy as np

_RL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _RL)

OPPONENTS = [
    ("starter", 0.5),
    (os.path.join(_RL, "..", "agents", "barnyard.py"), 0.25),
    (os.path.join(_RL, "..", "agents", "wrapped", "w49.py"), 0.25),
]


def _run_chunk(job):
    wid, n_eps, out_dir = job
    import actions as A
    import obs as O
    from kg_env import KGEnv
    from scripted import scripted_action

    rng = np.random.default_rng(1234 + wid * 7919)
    xs, fms, mms, fas, mas = [], [], [], [], []
    finals = []
    names, weights = zip(*OPPONENTS)
    p = np.asarray(weights) / sum(weights)
    for _ in range(n_eps):
        opp = names[int(rng.choice(len(names), p=p))]
        env = KGEnv(opponent=opp, seat=int(rng.integers(0, 2)))
        raw = env.reset(seed=int(rng.integers(0, 10_000)))
        done = False
        while not done:
            fi, mi = scripted_action(raw)
            xs.append(O.encode(raw).astype(np.float16))
            fms.append(A.farmer_mask(raw))
            mms.append(A.market_mask(raw))
            fas.append(fi)
            mas.append(mi)
            raw, done = env.step(A.decode(raw, fi, mi))
        finals.append(env.final_money()[0])
    path = os.path.join(out_dir, f"shard-{wid:02d}.npz")
    np.savez_compressed(
        path,
        obs=np.stack(xs), fmask=np.stack(fms), mmask=np.stack(mms),
        fa=np.asarray(fas, dtype=np.int16), ma=np.asarray(mas, dtype=np.int16))
    return wid, len(xs), float(np.mean(finals)), float(np.min(finals))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=160)
    ap.add_argument("--jobs", type=int, default=28)
    ap.add_argument("--out", default=os.path.join(_RL, "runs", "bc", "data"))
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    per = max(1, args.episodes // args.jobs)
    jobs = [(w, per, args.out) for w in range(args.jobs)]
    with Pool(args.jobs) as pool:
        for wid, n, mean_m, min_m in pool.imap_unordered(_run_chunk, jobs):
            print(f"shard {wid:02d}: {n} samples, teacher money "
                  f"mean {mean_m:,.0f} min {min_m:,.0f}", flush=True)
    print("COLLECT-DONE")


if __name__ == "__main__":
    main()
