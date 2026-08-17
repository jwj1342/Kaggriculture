#!/usr/bin/env python
"""B4a gate: tensor-state starter must equal the reference starter, action by
action, on live full episodes.

Setup: one EpisodeT batch (B lanes, distinct seeds). Player 0 plays random-
legal macro actions (masks_t + seeded torch sampling, decoded per lane);
player 1 is the starter. Every step, for every lane, we compute BOTH
`opponents_t.starter_actions(ep, 1)` and the reference
`starter_agent(snapshot-rebuilt obs)` and require dict equality before
stepping with the (p0, tensor-starter) pair. 720 steps x B lanes, zero
tolerance. Ends B4A-PASS / B4A-FAIL.

    python rl/tensor_env/test_b4a.py [--steps 720] [--lanes 3] [--device cpu]
"""

import argparse
import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_RL = os.path.dirname(_HERE)
_REPO = os.path.dirname(_RL)
for p in (_HERE, _RL):
    if p not in sys.path:
        sys.path.insert(0, p)

import torch

import actions as A
import engine_t
import engine_t_idx  # noqa: F401
import features_t
import opponents_t
from verify_t import _np_obs


def _load_reference_starter():
    ref = os.path.join(_REPO, "reference", "engine", "kaggriculture.py")
    spec = importlib.util.spec_from_file_location("kg_reference_engine", ref)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.agents["starter"]


class _SnapObs:
    """Duck-type verify_t._np_obs onto EpisodeT lanes."""

    def __init__(self, ep, lane):
        self.ep, self.lane = ep, lane
        self._step = ep._step

    def snapshot(self):
        return self.ep.snapshot(self.lane)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=720)
    ap.add_argument("--lanes", type=int, default=3)
    ap.add_argument("--device", default="cpu")
    args = ap.parse_args()

    starter_ref = _load_reference_starter()
    ep = engine_t.EpisodeT([95_000 + 17 * i for i in range(args.lanes)],
                           episode_steps=args.steps, device=args.device)
    gen = torch.Generator(device="cpu").manual_seed(4242)

    n = 0
    while not ep.done:
        # tensor starter vs reference starter, every lane
        tens = opponents_t.starter_actions(ep, 1)
        for lane in range(args.lanes):
            obs1 = _np_obs(_SnapObs(ep, lane), 1)
            ref = starter_ref(obs1)
            if ref != tens[lane]:
                print(f"B4A mismatch lane {lane} step {n}:\n  ref  {ref}\n  tens {tens[lane]}")
                print("B4A-FAIL")
                return 1
        # p0: random-legal macro actions decoded per lane
        p0 = []
        for lane in range(args.lanes):
            obs0 = _np_obs(_SnapObs(ep, lane), 0)
            fm, mm = A.farmer_mask(obs0), A.market_mask(obs0)
            fi = int(torch.multinomial(torch.tensor(fm, dtype=torch.float), 1, generator=gen))
            mi = int(torch.multinomial(torch.tensor(mm, dtype=torch.float), 1, generator=gen))
            p0.append(A.decode(obs0, fi, mi))
        ep.step_raw([[p0[lane], tens[lane]] for lane in range(args.lanes)])
        n += 1
    print(f"{n} steps x {args.lanes} lanes: tensor starter identical everywhere")
    print("B4A-PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
