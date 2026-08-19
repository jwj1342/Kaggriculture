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


def gate_m3m4(args):
    """M3: multi-head policy math, the AUTO-biased start, snapshot/export
    parity. M4: env specs, device hand mask == CPU mask, train smoke."""
    import tempfile

    import numpy as np
    from torchrl.envs.utils import check_env_specs

    import obs as O
    from trl_env import FrozenPolicyOpponent, KGTensorEnv, hand_task_mask_t
    from trl_policy import (ActorNet, MultiActorNet, MultiHeadMasked,
                            MultiResidualActor)

    torch.manual_seed(4)
    B = 6
    net = MultiActorNet(O.OBS_DIM, A.N_FARMER, A.N_MARKET, 32, 16,
                        A.MAX_HANDS, A.N_HAND_TASK)
    x = torch.randn(B, O.OBS_DIM)
    fl, ml, hl = net(x)
    fm = torch.rand(B, A.N_FARMER) < 0.5
    fm[:, 0] = True
    mm = torch.rand(B, A.N_MARKET) < 0.5
    mm[:, 0] = True
    hm = torch.rand(B, A.MAX_HANDS, A.N_HAND_TASK) < 0.5
    hm[..., 1] = True
    dist = MultiHeadMasked(fl, ml, hl, fm, mm, hm)
    a = dist.sample()
    assert a.shape == (B, 2 + A.MAX_HANDS)
    flp = torch.log_softmax(fl.masked_fill(~fm, -1e9), -1)
    mlp = torch.log_softmax(ml.masked_fill(~mm, -1e9), -1)
    hlp = torch.log_softmax(hl.masked_fill(~hm, -1e9), -1)
    want = (flp.gather(-1, a[:, :1]).squeeze(-1)
            + mlp.gather(-1, a[:, 1:2]).squeeze(-1)
            + hlp.gather(-1, a[:, 2:].unsqueeze(-1)).squeeze(-1).sum(-1))
    assert torch.equal(dist.log_prob(a), want)
    ent = (-(flp.exp() * flp).sum(-1) - (mlp.exp() * mlp).sum(-1)
           - (hlp.exp() * hlp).sum((-1, -2)))
    assert torch.equal(dist.entropy(), ent)
    hm_all = torch.ones(B, A.MAX_HANDS, A.N_HAND_TASK, dtype=torch.bool)
    assert bool((MultiHeadMasked(fl, ml, hl, fm, mm, hm_all)
                 .mode[:, 2:] == 0).all()), "fresh hand heads must argmax AUTO"
    print("M3: MultiHeadMasked math exact; fresh hand heads argmax to AUTO")

    with tempfile.TemporaryDirectory() as tmp:
        torch.manual_seed(5)
        prior = ActorNet(O.OBS_DIM, A.N_FARMER, A.N_MARKET, 32, 16)
        prior_npz = os.path.join(tmp, "prior.npz")
        prior.export_npz(prior_npz)
        res = MultiResidualActor(prior_npz, O.OBS_DIM, A.N_FARMER, A.N_MARKET,
                                 24, 12, A.MAX_HANDS, A.N_HAND_TASK)
        with torch.no_grad():
            res.delta.hands.weight.mul_(1000.0)
            tf, tm, th = res(x)
        opp = FrozenPolicyOpponent.from_state_np(res.state_np(), "cpu")
        assert opp.provides_hands
        with torch.no_grad():
            ff, fmm = opp._logits(x)
            fh = opp._hand_logits(x)
        assert torch.allclose(ff, tf, atol=1e-5)
        assert torch.allclose(fmm, tm, atol=1e-5)
        assert torch.allclose(fh, th, atol=1e-5)
        W = res.state_np()
        xn = x[0].numpy()  # the export template's numpy math, line for line
        h = np.maximum(0.0, W["l1w"] @ xn + W["l1b"])
        h = np.maximum(0.0, W["l2w"] @ h + W["l2b"])
        f, m = W["fw"] @ h + W["fb"], W["mw"] @ h + W["mb"]
        h = np.maximum(0.0, W["d_l1w"] @ xn + W["d_l1b"])
        h = np.maximum(0.0, W["d_l2w"] @ h + W["d_l2b"])
        f = f + W["d_fw"] @ h + W["d_fb"]
        m = m + W["d_mw"] @ h + W["d_mb"]
        hh = W["d_hw"] @ h + W["d_hb"]
        assert np.allclose(f, tf[0].numpy(), atol=1e-4)
        assert np.allclose(m, tm[0].numpy(), atol=1e-4)
        assert np.allclose(hh.reshape(A.MAX_HANDS, A.N_HAND_TASK),
                           th[0].numpy(), atol=1e-4)
    print("M3: snapshot & export math honour the hand heads (residual-multi)")

    check_env_specs(KGTensorEnv(2, device="cpu", episode_steps=26,
                                multi_head=True))
    ep = engine_t.EpisodeT([71_311, 71_344], episode_steps=720, device="cpu")
    gen = torch.Generator(device="cpu").manual_seed(55)
    for _ in range(180):
        fi = torch.randint(0, A.N_FARMER, (2, 2), generator=gen)
        mi = torch.randint(0, A.N_MARKET, (2, 2), generator=gen)
        ep.step_idx(fi, mi)
    for player in range(2):
        dev_mask = hand_task_mask_t(ep, player, A.MAX_HANDS)
        for lane in range(2):
            cpu_mask = A.hand_task_mask(_np_obs(_SnapObs(ep, lane), player))
            assert dev_mask[lane].tolist() == cpu_mask, (lane, player)
    print("M4: check_env_specs + device hand mask == CPU hand_task_mask")

    sys.path.insert(0, _RL)
    import train as trl_train
    with tempfile.TemporaryDirectory() as tmp:
        torch.manual_seed(6)
        prior = ActorNet(O.OBS_DIM, A.N_FARMER, A.N_MARKET, 32, 16)
        prior_npz = os.path.join(tmp, "prior.npz")
        prior.export_npz(prior_npz)
        an = None
        for tag, extra in (("plain", []),
                           ("residual", ["--residual-base", prior_npz])):
            save = os.path.join(tmp, tag, "latest.pt")
            argv = ["--device", "cpu", "--B", "4", "--iters", "2",
                    "--steps", "96", "--seed", "5", "--threads", "2",
                    "--quiet", "--multi-head", "--opponents", "starter",
                    "--league", "--snapshot-every", "1", "--save", save]
            (an, _cn), recs = trl_train.train(
                trl_train.parse_args(argv + extra), log_fn=lambda s: None)
            assert len(recs) == 2, (tag, len(recs))
        opp2 = FrozenPolicyOpponent.from_state_np(an.state_np(), "cpu")
        assert opp2.provides_hands, "a multi snapshot must play its hands"
    print("M4: --multi-head train smoke (plain + residual), snapshots carry "
          "the hand heads")
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
    if not gate_m3m4(args):
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
