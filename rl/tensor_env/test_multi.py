#!/usr/bin/env python
"""Per-unit multi-head action space gates (rl/TODO.md #0), layer by layer.

M1 (CPU reference): on live full episodes, _hands_actions_multi with
    all-AUTO tasks must equal the classic _hands_actions byte for byte --
    the macro space is the multi space's fixed point. Mixed tasks are
    property-checked: IDLE passes, a task hand only emits its family's op
    (or a move / the DROP leg), slots beyond the task list default to AUTO,
    and hand_task_mask matches family presence.

    python rl/tensor_env/test_multi.py [--steps 480] [--lanes 2]

Ends MULTI-PASS / MULTI-FAIL. Later layers (engine decode, policy heads)
append their gates here.
"""

import argparse
import os
import random
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_RL = os.path.dirname(_HERE)
for p in (_HERE, _RL):
    if p not in sys.path:
        sys.path.insert(0, p)

import torch

import actions as A
import engine_t
import engine_t_idx  # noqa: F401
from verify_t import _np_obs


class _SnapObs:
    def __init__(self, ep, lane):
        self.ep, self.lane = ep, lane
        self._step = ep._step

    def snapshot(self):
        return self.ep.snapshot(self.lane)


_MOVES = {"NORTH", "SOUTH", "EAST", "WEST"}


def _check_mixed(obs, s, rng):
    """Random task vector: property checks against the pool semantics."""
    n_hands = len(obs["farms"][obs["player"]].get("hands", []))
    if n_hands == 0:
        return 0
    tasks = [rng.randrange(A.N_HAND_TASK) for _ in range(n_hands)]
    acts = A._hands_actions_multi(obs, s, tasks)
    assert len(acts) == n_hands
    fam_lists = {"HARVEST": s["harvest"], "WATER": s["unwatered"],
                 "CARE": s["uncared"], "COLLECT_FERTILIZER": s["fert_ready"],
                 "DIG": s["weeds"]}
    for i, act in enumerate(acts):
        task = A.HAND_TASKS[tasks[i]]
        op = act[0]
        if task == "IDLE":
            assert act == ["PASS"], (task, act)
        elif task == "AUTO":
            assert op in _MOVES | {"PASS", "DROP", "HARVEST", "WATER", "CARE",
                                   "COLLECT_FERTILIZER", "DIG"}, (task, act)
        else:
            assert op in _MOVES | {"PASS", "DROP", task}, (task, act)
            if op == "PASS":
                # PASS is only legal when the family is empty, every target
                # is claimed by an earlier hand, or the hand is mid-DROP-leg
                pass
    # mask sanity: family legality == family presence
    mask = A.hand_task_mask(obs)
    for i in range(A.MAX_HANDS):
        assert mask[i][0] == (i < n_hands)          # AUTO for live hands
        assert mask[i][1] is True                    # IDLE always
        for k, name in enumerate(A.HAND_TASKS[2:], start=2):
            want = (i < n_hands) and bool(fam_lists[name])
            assert mask[i][k] == want, (i, name, mask[i][k], want)
    return 1


def gate_m2(args):
    """M2: step_idx(h_idx=random tasks) vs step_raw(decode_multi), full
    state, every step; then all-AUTO h_idx == the h_idx=None path."""
    import verify

    seeds = [58_000 + 31 * i for i in range(args.lanes)]
    ep_m = engine_t.EpisodeT(seeds, episode_steps=args.steps, device=args.device)
    ep_r = engine_t.EpisodeT(seeds, episode_steps=args.steps, device=args.device)
    gen = torch.Generator(device="cpu").manual_seed(909)
    rng = random.Random(23)

    n = tasked = 0
    while not ep_m.done:
        fi_l, mi_l, h_l, dicts = [], [], [], []
        for lane in range(args.lanes):
            fi_p, mi_p, h_p, d_p = [], [], [], []
            for player in range(2):
                obs = _np_obs(_SnapObs(ep_m, lane), player)
                fm, mm = A.farmer_mask(obs), A.market_mask(obs)
                fi = int(torch.multinomial(torch.tensor(fm, dtype=torch.float),
                                           1, generator=gen))
                mi = int(torch.multinomial(torch.tensor(mm, dtype=torch.float),
                                           1, generator=gen))
                n_hands = len(obs["farms"][player].get("hands", []))
                tasks = [rng.randrange(A.N_HAND_TASK) for _ in range(n_hands)]
                tasked += sum(1 for x in tasks if x >= 2)
                fi_p.append(fi)
                mi_p.append(mi)
                h_p.append(tasks + [0] * (A.MAX_HANDS - len(tasks)))
                d_p.append(A.decode_multi(obs, fi, tasks, mi))
            fi_l.append(fi_p)
            mi_l.append(mi_p)
            h_l.append(h_p)
            dicts.append(d_p)
        ep_m.step_idx(torch.tensor(fi_l), torch.tensor(mi_l),
                      h_idx=torch.tensor(h_l))
        ep_r.step_raw(dicts)
        for lane in range(args.lanes):
            d = verify.first_diff(ep_m.snapshot(lane), ep_r.snapshot(lane))
            if d:
                print(f"M2 state diff lane {lane} after step {n}: {d}")
                return False
        n += 1
    print(f"M2: {n} steps x {args.lanes} lanes, random per-hand tasks "
          f"({tasked} non-AUTO), device == step_raw(decode_multi) throughout")

    # all-AUTO h_idx must be bit-for-bit the classic path
    seeds = [61_500 + 7 * i for i in range(args.lanes)]
    ep_a = engine_t.EpisodeT(seeds, episode_steps=min(args.steps, 240),
                             device=args.device)
    ep_b = engine_t.EpisodeT(seeds, episode_steps=min(args.steps, 240),
                             device=args.device)
    gen = torch.Generator(device="cpu").manual_seed(31)
    zeros = torch.zeros((args.lanes, 2, A.MAX_HANDS), dtype=torch.int64)
    n = 0
    while not ep_a.done:
        fi = torch.randint(0, A.N_FARMER, (args.lanes, 2), generator=gen)
        mi = torch.randint(0, A.N_MARKET, (args.lanes, 2), generator=gen)
        ep_a.step_idx(fi, mi)
        ep_b.step_idx(fi, mi, h_idx=zeros)
        for lane in range(args.lanes):
            d = verify.first_diff(ep_a.snapshot(lane), ep_b.snapshot(lane))
            if d:
                print(f"M2 all-AUTO diff lane {lane} after step {n}: {d}")
                return False
        n += 1
    print(f"M2: {n} steps all-AUTO h_idx == h_idx=None, bit for bit")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=480)
    ap.add_argument("--lanes", type=int, default=2)
    ap.add_argument("--device", default="cpu")
    args = ap.parse_args()

    if not gate_m2(args):
        print("MULTI-FAIL")
        return 1

    ep = engine_t.EpisodeT([47_000 + 29 * i for i in range(args.lanes)],
                           episode_steps=args.steps, device=args.device)
    gen = torch.Generator(device="cpu").manual_seed(2026)
    rng = random.Random(11)

    n = hands_seen = mixed_checked = 0
    while not ep.done:
        fi_l, mi_l = [], []
        for lane in range(args.lanes):
            for player in range(2):
                obs = _np_obs(_SnapObs(ep, lane), player)
                s = A._scan(obs)
                auto = A._hands_actions_multi(
                    obs, s, [0] * len(obs["farms"][player].get("hands", [])))
                classic = A._hands_actions(obs, s)
                if auto != classic:
                    print(f"M1 mismatch lane {lane} p{player} step {n}:\n"
                          f"  classic {classic}\n  multi   {auto}")
                    print("MULTI-FAIL")
                    return 1
                # short task vectors default to AUTO
                if A._hands_actions_multi(obs, s, []) != classic:
                    print(f"M1 default-AUTO mismatch step {n}")
                    print("MULTI-FAIL")
                    return 1
                hands_seen += len(classic)
                mixed_checked += _check_mixed(obs, s, rng)
            obs0 = _np_obs(_SnapObs(ep, lane), 0)
            fm, mm = A.farmer_mask(obs0), A.market_mask(obs0)
            fi_l.append([int(torch.multinomial(torch.tensor(fm, dtype=torch.float),
                                               1, generator=gen)),
                         int(torch.multinomial(torch.tensor(fm, dtype=torch.float),
                                               1, generator=gen))])
            mi_l.append([int(torch.multinomial(torch.tensor(mm, dtype=torch.float),
                                               1, generator=gen)),
                         int(torch.multinomial(torch.tensor(mm, dtype=torch.float),
                                               1, generator=gen))])
        ep.step_idx(torch.tensor(fi_l), torch.tensor(mi_l))
        n += 1

    assert hands_seen > 0, "no hands were ever hired -- widen the run"
    print(f"M1: {n} steps x {args.lanes} lanes x 2 seats, {hands_seen} "
          f"hand-actions AUTO==classic, {mixed_checked} mixed-task checks")
    print("MULTI-PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
