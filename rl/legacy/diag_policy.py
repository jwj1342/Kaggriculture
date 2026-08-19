#!/usr/bin/env python
"""Diagnose argmax-vs-sampling behaviour of an exported policy dir.

    python rl/diag_policy.py rl/out/groundhog --opponent agents/ghosts/ghost-89825016-0.py
"""

import argparse
import os
import sys
from collections import Counter

import numpy as np

_RL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _RL)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("agent_dir")
    ap.add_argument("--opponent", default="starter")
    ap.add_argument("--seed", type=int, default=12345)
    args = ap.parse_args()

    sys.path.insert(0, args.agent_dir)
    import kg_rl_actions as A
    import kg_rl_obs as O
    from kg_env import KGEnv

    W = dict(np.load(os.path.join(args.agent_dir, "weights.npz")))

    def logits(x):
        h = np.maximum(0, W["l1w"] @ x + W["l1b"])
        h = np.maximum(0, W["l2w"] @ h + W["l2b"])
        return W["fw"] @ h + W["fb"], W["mw"] @ h + W["mb"]

    for mode in ("argmax", "sample"):
        env = KGEnv(opponent=args.opponent, seat=0)
        raw = env.reset(seed=args.seed)
        rng = np.random.default_rng(0)
        fh, mh = Counter(), Counter()
        done = False
        step = 0
        while not done:
            x = O.encode(raw)
            fl, ml = logits(x)
            fl[~A.farmer_mask(raw)] = -1e9
            ml[~A.market_mask(raw)] = -1e9
            if mode == "argmax":
                fi, mi = int(fl.argmax()), int(ml.argmax())
            else:
                def samp(l):
                    p = np.exp(l - l.max())
                    p /= p.sum()
                    return int(rng.choice(len(l), p=p))
                fi, mi = samp(fl), samp(ml)
            fh[A.FARMER_ACTIONS[fi]] += 1
            mh[A.MARKET_ACTIONS[mi]] += 1
            raw, done = env.step(A.decode(raw, fi, mi))
            step += 1
            if step % 240 == 8:
                me = raw["player"]
                print(f"  {mode} step {step} money {raw['farms'][me]['money']:,.0f}")
        mine, theirs = env.final_money()
        print(f"{mode}: me {mine:,.0f} opp {theirs:,.0f}")
        print(f"  farmer: {fh.most_common(6)}")
        print(f"  market: {mh.most_common(6)}")


if __name__ == "__main__":
    main()
