#!/usr/bin/env python
"""Barnyard-tensor gate: two checks per step, full episodes, zero tolerance.

G1 (decisions): barnyard_t.compute(ep, 1) rendered to dict form must equal
    agents/barnyard.py's agent(obs) verbatim, every lane, every step -- the
    obs rebuilt from ep.snapshot exactly as test_b4a does for the starter.
G2 (application): a twin EpisodeT advanced with step_raw fed the SAME raw
    dicts (learner's decoded macro action, reference barnyard) must match
    the override-path episode snapshot-for-snapshot -- proving the
    step_idx override applies raw encodings exactly as step_raw parses
    dicts, and (with override absent effects) that the seam is sound.

    python rl/tensor_env/test_barn.py [--steps 720] [--lanes 2] [--seed0 31000]

Ends BARN-PASS / BARN-FAIL.
"""

import argparse
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_RL = os.path.dirname(_HERE)
for p in (_HERE, _RL):
    if p not in sys.path:
        sys.path.insert(0, p)

import torch

import actions as A
import barnyard_t
import engine_t
import engine_t_idx  # noqa: F401
import verify
from verify_t import lane_obs

import barnyard as BY  # barnyard_t put agents/ on sys.path



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=720)
    ap.add_argument("--lanes", type=int, default=2)
    ap.add_argument("--seed0", type=int, default=31000)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--progress", type=int, default=120)
    args = ap.parse_args()

    seeds = [args.seed0 + 13 * i for i in range(args.lanes)]
    ep = engine_t.EpisodeT(seeds, episode_steps=args.steps, device=args.device)
    ep2 = engine_t.EpisodeT(seeds, episode_steps=args.steps, device=args.device)
    gen = torch.Generator(device="cpu").manual_seed(777)

    n = 0
    while not ep.done:
        ops, dicts = barnyard_t.compute(ep, 1, want_dicts=True)
        refs = []
        for lane in range(args.lanes):
            obs1 = lane_obs(ep, lane, 1)
            ref = BY.agent(obs1)
            if ref != dicts[lane]:
                print(f"G1 mismatch lane {lane} step {n}:")
                for k in ("farmer", "hands", "market"):
                    if ref.get(k) != dicts[lane].get(k):
                        print(f"  {k}:\n    ref  {ref.get(k)}\n"
                              f"    tens {dicts[lane].get(k)}")
                print("BARN-FAIL")
                return 1
            refs.append(ref)

        p0 = []
        fi_l, mi_l = [], []
        for lane in range(args.lanes):
            obs0 = lane_obs(ep, lane, 0)
            fm, mm = A.farmer_mask(obs0), A.market_mask(obs0)
            fi = int(torch.multinomial(torch.tensor(fm, dtype=torch.float), 1,
                                       generator=gen))
            mi = int(torch.multinomial(torch.tensor(mm, dtype=torch.float), 1,
                                       generator=gen))
            p0.append(A.decode(obs0, fi, mi))
            fi_l.append([fi, 0])
            mi_l.append([mi, 0])

        ep.step_idx(torch.tensor(fi_l), torch.tensor(mi_l), override=(1, ops))
        ep2.step_raw([[p0[lane], refs[lane]] for lane in range(args.lanes)])
        for lane in range(args.lanes):
            d = verify.first_diff(ep.snapshot(lane), ep2.snapshot(lane))
            if d:
                print(f"G2 state diff lane {lane} after step {n}: {d}")
                print("BARN-FAIL")
                return 1
        n += 1
        if args.progress and n % args.progress == 0:
            money = [f"{float(ep.money[l, 1]):,.0f}" for l in range(args.lanes)]
            print(f"  step {n}: identical; barnyard money {money}", flush=True)

    money = [float(ep.money[lane, 1]) for lane in range(args.lanes)]
    print(f"{n} steps x {args.lanes} lanes: decisions and state identical; "
          f"barnyard final money {[f'{m:,.0f}' for m in money]}")
    print("BARN-PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
