#!/usr/bin/env python
"""Gates for the TorchRL unification layer (pattern of test_b4c.py).

    python rl/tensor_env/test_trl.py            # CPU, ~2 minutes

 (i)   policy parity: TwoHeadMasked log_prob / entropy and CriticNet values
       equal PolicyT.evaluate / .value bit for bit under shared weights.
 (ii)  env parity: KGTensorEnv through the public EnvBase API replays a
       direct EpisodeT loop bit for bit (rewards, final money), same seeds,
       same deterministic legal-action picker on both sides.
 (iii) GAE parity: torchrl's vectorised GAE equals train_t.gae on random
       fixed-length batches (allclose; the vectorised form reorders floats).
 (iv)  check_env_specs, then a 2-iteration train smoke for --algo ppo and
       --algo a2c: finite losses, records shaped as promised.
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_RL = os.path.dirname(_HERE)
for _p in (_HERE, _RL):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import torch

import actions as A
import obs as O
from policy_t import PolicyT
from trl_policy import (ActorNet, CriticNet, TwoHeadMasked,
                        load_merged_state_dict, merged_state_dict)


def gate_policy_parity(B=64, seed=3):
    torch.manual_seed(seed)
    ref = PolicyT(O.OBS_DIM, A.N_FARMER, A.N_MARKET)
    actor = ActorNet(O.OBS_DIM, A.N_FARMER, A.N_MARKET)
    critic = CriticNet(O.OBS_DIM)
    load_merged_state_dict(actor, critic, ref.state_dict())
    assert merged_state_dict(actor, critic).keys() == ref.state_dict().keys()

    x = torch.randn(B, O.OBS_DIM)
    fm = torch.rand(B, A.N_FARMER) < 0.5
    mm = torch.rand(B, A.N_MARKET) < 0.5
    fm[:, 0] = True  # PASS / NOOP are always legal in real masks
    mm[:, 0] = True
    fa = torch.randint(0, A.N_FARMER, (B,))
    ma = torch.randint(0, A.N_MARKET, (B,))
    fa[~fm.gather(1, fa.view(-1, 1)).view(-1)] = 0  # evaluate on legal picks
    ma[~mm.gather(1, ma.view(-1, 1)).view(-1)] = 0

    with torch.no_grad():
        ref_logp, ref_ent = ref.evaluate(x, fm, mm, fa, ma)
        ref_val = ref.value(x)
        fl, ml = actor(x)
        dist = TwoHeadMasked(fl, ml, fm, mm)
        logp = dist.log_prob(torch.stack([fa, ma], -1))
        ent = dist.entropy()
        val = critic(x).squeeze(-1)
    assert torch.equal(logp, ref_logp), (logp - ref_logp).abs().max()
    assert torch.equal(ent, ref_ent), (ent - ref_ent).abs().max()
    assert torch.equal(val, ref_val), (val - ref_val).abs().max()
    # mode == the export path's masked argmax
    assert torch.equal(dist.mode[:, 0], fl.masked_fill(~fm, -1e9).argmax(-1))
    print("gate (i)   policy parity: bit-exact logp / entropy / value  PASS")


def _pick_legal(mask, t):
    """Deterministic legal pick: the ((7 t + lane) mod n_legal)-th legal
    index per lane. Same function drives both sides of gate (ii)."""
    B = mask.shape[0]
    out = torch.empty(B, dtype=torch.int64)
    for i in range(B):
        legal = mask[i].nonzero(as_tuple=True)[0]
        out[i] = legal[(7 * t + i) % len(legal)]
    return out


def gate_env_parity(B=4, steps=240, base_seed=7, win_bonus=3.0):
    import engine_t
    import engine_t_idx  # noqa: F401
    import features_t
    import opponents_t
    import potential_t
    from trl_env import KGTensorEnv

    # reference: the train_t.collect loop, deterministic picker on seat 0
    seeds = [base_seed * 1_000_003 + i for i in range(B)]
    ep = engine_t.EpisodeT(seeds, episode_steps=steps, device="cpu")
    prev_w = potential_t.net_worth_t(ep, 0)
    ref_rewards = []
    t = 0
    while not ep.done:
        fm, mm = features_t.masks_t(ep, 0)
        fa, ma = _pick_legal(fm, t), _pick_legal(mm, t)
        ofa, oma = opponents_t.starter_indices(ep, 1)
        ep.step_idx(torch.stack([fa, ofa], 1), torch.stack([ma, oma], 1))
        w = potential_t.net_worth_t(ep, 0)
        r = (w - prev_w) * (1.0 / 3000.0)
        prev_w = w
        if ep.done:
            win = ((ep.money[:, 0] > ep.money[:, 1]).to(torch.float64)
                   - (ep.money[:, 0] < ep.money[:, 1]).to(torch.float64))
            r = r + win_bonus * win
        ref_rewards.append(r.to(torch.float32))
        t += 1
    ref_money = ep.money.clone()

    # candidate: the same episodes through the public EnvBase API (the engine
    # terminates at episode_steps - 2, so we loop on the env's done flag)
    env = KGTensorEnv(B, device="cpu", seat=0, episode_steps=steps,
                      base_seed=base_seed, win_bonus=win_bonus)
    td = env.reset()
    t = 0
    while True:
        td["action"] = torch.stack(
            [_pick_legal(td["farmer_mask"], t), _pick_legal(td["market_mask"], t)], -1)
        td = env.step(td)
        assert torch.equal(td["next", "reward"].squeeze(-1), ref_rewards[t]), \
            f"reward diverges at step {t}"
        if bool(td["next", "done"].all()):
            break
        td = td["next"].exclude("reward")
        t += 1
    # done is flagged while executing action index steps - 2, so a complete
    # episode is steps - 1 actions (the ep_len contract rl/train.py relies on)
    assert t == len(ref_rewards) - 1 == steps - 2, (t, len(ref_rewards))
    final = td["next"]
    assert torch.equal(final["money"], ref_money[:, 0])
    assert torch.equal(final["opp_money"], ref_money[:, 1])
    print(f"gate (ii)  env parity: {t + 1} steps x {B} lanes bit-exact  PASS")


def gate_gae_parity(T=48, B=16, gamma=0.999, lam=0.95, seed=11):
    from torchrl.objectives.value.functional import (
        vec_generalized_advantage_estimate)
    from train_t import gae as hand_gae

    torch.manual_seed(seed)
    rew_tb = torch.randn(T, B)
    val_tb = torch.randn(T, B)
    adv_ref, ret_ref = hand_gae(rew_tb, val_tb, gamma, lam)

    # torchrl layout: [B, T, 1], time_dim=-2; zero bootstrap via terminated
    val = val_tb.t().unsqueeze(-1)
    nxt = torch.cat([val_tb[1:], torch.zeros(1, B)]).t().unsqueeze(-1)
    rew = rew_tb.t().unsqueeze(-1)
    done = torch.zeros(B, T, 1, dtype=torch.bool)
    done[:, -1] = True
    adv, ret = vec_generalized_advantage_estimate(
        gamma, lam, val, nxt, rew, done, done)
    assert torch.allclose(adv.squeeze(-1).t(), adv_ref, atol=1e-4), \
        (adv.squeeze(-1).t() - adv_ref).abs().max()
    assert torch.allclose(ret.squeeze(-1).t(), ret_ref, atol=1e-4)
    print(f"gate (iii) GAE parity: torchrl vec GAE == train_t.gae (T={T}, B={B})  PASS")


def gate_train_smoke():
    from torchrl.envs.utils import check_env_specs
    from trl_env import KGTensorEnv
    check_env_specs(KGTensorEnv(2, device="cpu", episode_steps=26))
    print("gate (iv)  check_env_specs  PASS")

    sys.path.insert(0, _RL)
    import train as trl_train
    for algo in ("ppo", "a2c"):
        args = trl_train.build_parser().parse_args(
            ["--algo", algo, "--device", "cpu", "--B", "8", "--iters", "2",
             "--steps", "96", "--seed", "5", "--threads", "2", "--quiet"])
        _, records = trl_train.train(args, log_fn=lambda s: None)
        assert len(records) == 2, records
        for r in records:
            for k in ("pg", "vf", "ent", "win", "money"):
                assert r[k] == r[k], (algo, k, r)  # NaN check
        print(f"gate (iv)  train smoke --algo {algo}: 2 iters, "
              f"final money {records[-1]['money']:,.0f}, "
              f"win {records[-1]['win']:.2f}  PASS")


if __name__ == "__main__":
    torch.set_num_threads(int(os.environ.get("OMP_NUM_THREADS", "2") or 2))
    gate_policy_parity()
    gate_gae_parity()
    gate_env_parity()
    gate_train_smoke()
    print("test_trl: all gates PASS")
