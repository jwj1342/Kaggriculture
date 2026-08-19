#!/usr/bin/env python
"""M0 smoke test: a random-legal policy plays full episodes through the whole
rl/ stack (KGEnv -> encode -> masks -> decode). Green means the scaffolding
holds for 720 steps; it says nothing about strength.

    source setup_env.sh
    python rl/rollout.py --episodes 1 --opponent starter --seed 1000

Checks, each fatal if violated:
  * every step encodes to a finite OBS_DIM vector
  * both masks always leave at least one legal option
  * the episode reaches DONE with both statuses clean
Prints the money curve, the shaped-return vs final-money ledger, and the
action-usage histogram (the boredom check: all-PASS means the masks broke).
"""

import argparse
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

import actions as A
import obs as O
from kg_env import KGEnv


def run_episode(env, seed, rng, verbose=True):
    raw = env.reset(seed=seed)
    prev_worth = O.net_worth(raw)
    shaped_return = 0.0
    steps = 0
    fhist, mhist = Counter(), Counter()

    while True:
        vec = O.encode(raw)
        assert vec.shape == (O.OBS_DIM,), f"obs shape {vec.shape}"
        assert np.isfinite(vec).all(), f"non-finite obs at step {steps}"

        fm, mm = A.farmer_mask(raw), A.market_mask(raw)
        assert fm.any() and mm.any(), f"empty mask at step {steps}"
        f_idx = int(rng.choice(np.flatnonzero(fm)))
        m_idx = int(rng.choice(np.flatnonzero(mm)))
        fhist[A.FARMER_ACTIONS[f_idx]] += 1
        mhist[A.MARKET_ACTIONS[m_idx]] += 1

        raw, done = env.step(A.decode(raw, f_idx, m_idx))
        steps += 1

        worth = O.net_worth(raw)
        shaped_return += worth - prev_worth
        prev_worth = worth

        if verbose and steps % 72 == 0:
            me = raw["player"]
            print(f"  step {steps:>3}  day {raw['day']:>2}  "
                  f"money {raw['farms'][me]['money']:>9,.0f}  "
                  f"net_worth {worth:>9,.0f}")
        if done:
            break

    mine, theirs = env.final_money()
    statuses = env.statuses()
    ok = steps >= env.steps - 2 and all(s == "DONE" for s in statuses)
    return {"steps": steps, "mine": mine, "theirs": theirs,
            "statuses": statuses, "shaped_return": shaped_return,
            "fhist": fhist, "mhist": mhist, "ok": ok}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=1)
    ap.add_argument("--opponent", default="starter")
    ap.add_argument("--seed", type=int, default=1000)
    ap.add_argument("--seat", type=int, default=0, choices=(0, 1))
    ap.add_argument("--policy-seed", type=int, default=0)
    args = ap.parse_args()

    env = KGEnv(opponent=args.opponent, seat=args.seat)
    rng = np.random.default_rng(args.policy_seed)
    print(f"obs dim {O.OBS_DIM}  farmer head {A.N_FARMER}  market head {A.N_MARKET}")

    failures = 0
    for ep in range(args.episodes):
        seed = args.seed + ep
        print(f"\nepisode {ep}  seed {seed}  vs {args.opponent}  seat {args.seat}")
        r = run_episode(env, seed, rng)
        print(f"  finished: {r['steps']} steps  statuses {r['statuses']}")
        print(f"  final money  me {r['mine']:,.0f}  opp {r['theirs']:,.0f}  "
              f"({'WIN' if r['mine'] > r['theirs'] else 'LOSS' if r['mine'] < r['theirs'] else 'TIE'})")
        print(f"  shaped return {r['shaped_return']:,.0f} "
              f"(should be near final net_worth minus 3,000)")
        top_f = ", ".join(f"{k}:{v}" for k, v in r["fhist"].most_common(6))
        top_m = ", ".join(f"{k}:{v}" for k, v in r["mhist"].most_common(6))
        print(f"  farmer head: {top_f}")
        print(f"  market head: {top_m}")
        if not r["ok"]:
            failures += 1
            print("  !! FAILED")

    print(f"\n{args.episodes - failures}/{args.episodes} episodes clean")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
