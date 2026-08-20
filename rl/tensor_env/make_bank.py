#!/usr/bin/env python
"""Generate a mid-game state bank: barnyard vs barnyard, forked on a grid.

Backplay (Resnick et al.) needs starting states where a competent economy
already exists on both seats; the learner then inherits a seat and only
has to CONTINUE well -- the win signal gets its first non-zero gradient
long before the policy can build day-0-to-day-29 on its own.

    python rl/tensor_env/make_bank.py --lanes 64 --steps 168,264,360,456
    -> data/banks/barnyard-<steps>.pt   (one bank_t.fork() per grid step)

Each file holds {"step": int, "seeds": [...], "state": fork(ep)} for a
whole lane batch; bank_t.restore() puts any of them back into a fresh
EpisodeT of the same width.
"""

import argparse
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_RL = os.path.dirname(_HERE)
_REPO = os.path.dirname(_RL)
for p in (_HERE, _RL):
    if p not in sys.path:
        sys.path.insert(0, p)

import torch

import bank_t
import barnyard_t
import engine_t
import engine_t_idx  # noqa: F401

OUT = os.path.join(_REPO, "data", "banks")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lanes", type=int, default=64)
    ap.add_argument("--steps", default="168,264,360,456",
                    help="fork points (24 = one day)")
    ap.add_argument("--seed0", type=int, default=430_000)
    ap.add_argument("--device", default="cpu")
    args = ap.parse_args()
    marks = sorted(int(s) for s in args.steps.split(","))
    os.makedirs(OUT, exist_ok=True)

    seeds = [args.seed0 + 7 * i for i in range(args.lanes)]
    ep = engine_t.EpisodeT(seeds, episode_steps=720, device=args.device)
    zero = torch.zeros((args.lanes, 2), dtype=torch.int64, device=args.device)
    for step in range(max(marks) + 1):
        ops = [(p, barnyard_t.compute(ep, p)) for p in (0, 1)]
        ep.step_idx(zero, zero, override=ops)
        if ep._step in marks:
            path = os.path.join(OUT, f"barnyard-{ep._step:04d}.pt")
            torch.save({"step": ep._step, "seeds": seeds,
                        "state": bank_t.fork(ep)}, path)
            money = ep.money.mean(0).tolist()
            print(f"step {ep._step:4d} (day {ep._step // 24:2d}): "
                  f"saved {path}  mean money {money}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
