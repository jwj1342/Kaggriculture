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
 (v)   the old line's hooks: OpponentPool curriculum advance + FIFO
       attribution; then an end-to-end chain -- BC-style --init-from with
       --freeze-policy-until (actor bit-identical after a critic-only
       iteration), league snapshots on disk, --resume continuing iteration
       count, seed stream, records and pool state.
 (x)   --plant-credit / --animal-credit: omitting them is bit-identical to
       passing Kilo's constants, phi is linear in each (a half step lands
       exactly halfway), and the two terms are separable. These two knobs
       change WHY the policy liquidates, so a default drift here would move
       every arm's reward without appearing in any diff.
 (xi)  pool knobs are not silent: --league / --pfsp / --handicap without
       --opponents build no pool, so they now fail loudly instead of being
       ignored for a whole run. Also pins that snap-0000 DOES exist: it is
       taken after iteration 0's optim.step(), so it is a net with one
       update rather than the warm-start.
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


def gate_hooks():
    import tempfile

    from trl_pool import OpponentPool

    with tempfile.TemporaryDirectory() as tmp:
        # a second curriculum stage that is a frozen random policy on disk
        torch.manual_seed(1)
        opp_net = ActorNet(O.OBS_DIM, A.N_FARMER, A.N_MARKET, 32, 16)
        opp_npz = os.path.join(tmp, "stage2.npz")
        opp_net.export_npz(opp_npz)

        pool = OpponentPool(["starter", opp_npz], "cpu", advance_at=0.85,
                            min_records=3, league=True,
                            snapshot_dir=os.path.join(tmp, "snaps"), seed=0)
        for _ in range(4):
            pool.sample()
        assert pool.record(0.9) is None and pool.record(0.9) is None  # < min_records
        assert pool.record(0.99) == "advanced" and pool.stage == 1
        assert pool.record(0.5) is None  # 4th pending belonged to stage 0's queue
        pool.add_snapshot(opp_net, "snap-test")
        assert os.path.exists(os.path.join(tmp, "snaps", "snap-test.npz"))
        st = pool.state()
        pool2 = OpponentPool(["starter", opp_npz], "cpu", league=True,
                             snapshot_dir=os.path.join(tmp, "snaps"), seed=0)
        pool2.load_state(st)
        assert pool2.stage == 1 and len(pool2.snapshots) == 1
        print("gate (v)   pool: curriculum advance, FIFO attribution, "
              "snapshot round-trip  PASS")

        sys.path.insert(0, _RL)
        import train as trl_train

        # BC-style init + frozen policy: the actor must not move
        torch.manual_seed(2)
        init_actor = ActorNet(O.OBS_DIM, A.N_FARMER, A.N_MARKET)
        init_critic = CriticNet(O.OBS_DIM)
        init_ck = os.path.join(tmp, "bc_init.pt")
        torch.save({"model": merged_state_dict(init_actor, init_critic)}, init_ck)
        save = os.path.join(tmp, "run", "latest.pt")
        args = trl_train.parse_args(
            ["--device", "cpu", "--B", "4", "--iters", "1", "--steps", "96",
             "--seed", "5", "--threads", "2", "--quiet",
             "--init-from", init_ck, "--freeze-policy-until", "10000000",
             "--opponents", "starter", "--league", "--snapshot-every", "1",
             "--save", save])
        (actor_net, critic_net), recs = trl_train.train(args, log_fn=lambda s: None)
        for (k1, p1), (k2, p2) in zip(init_actor.state_dict().items(),
                                      actor_net.state_dict().items()):
            assert k1 == k2 and torch.equal(p1, p2.cpu()), f"actor moved: {k1}"
        assert not torch.equal(init_critic.v1.weight,
                               critic_net.v1.weight.cpu()), "critic did not train"
        assert os.path.exists(os.path.join(tmp, "run", "best.pt"))
        assert os.path.exists(os.path.join(tmp, "run", "snapshots", "snap-0000.npz"))
        print("gate (v)   init-from + freeze: actor bit-identical, critic trained, "
              "best.pt + snapshot written  PASS")

        # resume: two more iterations continue the count, seeds and pool
        args = trl_train.parse_args(
            ["--device", "cpu", "--B", "4", "--iters", "3", "--steps", "96",
             "--seed", "5", "--threads", "2", "--quiet",
             "--opponents", "starter", "--league", "--snapshot-every", "1",
             "--save", save, "--resume", save])
        _, recs2 = trl_train.train(args, log_fn=lambda s: None)
        assert [r["iter"] for r in recs2] == [0, 1, 2], recs2
        ck = torch.load(save, map_location="cpu", weights_only=False)
        assert ck["iter"] == 2 and len(ck["records"]) == 3
        # the collector auto-resets after every batch, so the index moves
        # strictly forward across the resume -- seeds are never reused
        assert ck["episode_index"] >= 4 and ck["pool"] is not None
        print("gate (v)   resume: iteration count, seed stream and pool state "
              "continue  PASS")


def gate_smoothing():
    """(vi) adversarial-gradient smoothing + residual policy contracts."""
    import tempfile

    import numpy as np

    from trl_env import FrozenPolicyOpponent, KGTensorEnv
    from trl_policy import ResidualActor

    env = KGTensorEnv(2, device="cpu", episode_steps=26, handicap=500)
    td = env.reset()
    assert torch.all(td["money"] == 3500) and torch.all(td["opp_money"] == 3000)
    print("gate (vi)  handicap applied at reset (learner seat only)  PASS")

    def run(margin, noise=0.0, steps=50, seed=13):
        env = KGTensorEnv(2, device="cpu", episode_steps=steps, base_seed=seed,
                          win_bonus=0.0, margin_bonus=margin,
                          margin_scale=1000.0, opp_noise=noise)
        td = env.reset()
        rews, t = [], 0
        while True:
            td["action"] = torch.stack(
                [_pick_legal(td["farmer_mask"], t),
                 _pick_legal(td["market_mask"], t)], -1)
            td = env.step(td)
            rews.append(td["next", "reward"].squeeze(-1).clone())
            if bool(td["next", "done"].all()):
                return rews, td["next", "money"].clone(), td["next", "opp_money"].clone()
            td = td["next"].exclude("reward")
            t += 1

    r0, m0, o0 = run(0.0)
    r1, m1, o1 = run(2.0)
    assert torch.equal(m0, m1) and torch.equal(o0, o1)
    for a, b in zip(r0[:-1], r1[:-1]):
        assert torch.equal(a, b)
    expect = r0[-1].double() + 2.0 * torch.tanh((m0 - o0) / 1000.0)
    assert torch.allclose(r1[-1].double(), expect, atol=1e-5), \
        (r1[-1], expect)
    print("gate (vi)  margin bonus: episodes identical until the terminal, "
          "exact tanh term  PASS")

    _, _, on = run(0.0, noise=1.0)
    assert not torch.equal(on, o0), "opponent noise did not perturb play"
    print("gate (vi)  opponent noise perturbs the episode (legal moves only)  PASS")

    with tempfile.TemporaryDirectory() as tmp:
        torch.manual_seed(9)
        prior = ActorNet(O.OBS_DIM, A.N_FARMER, A.N_MARKET, 32, 16)
        prior_npz = os.path.join(tmp, "prior.npz")
        prior.export_npz(prior_npz)
        res = ResidualActor(prior_npz, O.OBS_DIM, A.N_FARMER, A.N_MARKET, 24, 12)
        x = torch.randn(8, O.OBS_DIM)
        with torch.no_grad():
            for head in (res.delta.farmer, res.delta.market):
                head.weight.zero_()
                head.bias.zero_()
            rf, rm = res(x)
            bf, bm = prior(x)
        assert torch.equal(rf, bf) and torch.equal(rm, bm)

        torch.manual_seed(10)
        res2 = ResidualActor(prior_npz, O.OBS_DIM, A.N_FARMER, A.N_MARKET, 24, 12)
        with torch.no_grad():
            res2.delta.farmer.weight.mul_(1000.0)  # make the correction visible
            res2.delta.market.weight.mul_(1000.0)
            tf, tm = res2(x)
        opp = FrozenPolicyOpponent.from_state_np(res2.state_np(), "cpu")
        with torch.no_grad():
            ff, fm = opp._logits(x)
        assert torch.allclose(ff, tf, atol=1e-5) and torch.allclose(fm, tm, atol=1e-5)
        W = res2.state_np()
        xn = x[0].numpy()  # the export template's numpy math, line for line
        h = np.maximum(0.0, W["l1w"] @ xn + W["l1b"])
        h = np.maximum(0.0, W["l2w"] @ h + W["l2b"])
        f, m = W["fw"] @ h + W["fb"], W["mw"] @ h + W["mb"]
        h = np.maximum(0.0, W["d_l1w"] @ xn + W["d_l1b"])
        h = np.maximum(0.0, W["d_l2w"] @ h + W["d_l2b"])
        f = f + W["d_fw"] @ h + W["d_fb"]
        m = m + W["d_mw"] @ h + W["d_mb"]
        assert np.allclose(f, tf[0].numpy(), atol=1e-4)
        assert np.allclose(m, tm[0].numpy(), atol=1e-4)
    print("gate (vi)  residual: zero-delta == prior bit-exact; snapshot and "
          "export math honour both halves  PASS")

    from trl_pool import OpponentPool
    with tempfile.TemporaryDirectory() as tmp:
        torch.manual_seed(11)
        opp_net = ActorNet(O.OBS_DIM, A.N_FARMER, A.N_MARKET, 32, 16)
        npz = os.path.join(tmp, "s2.npz")
        opp_net.export_npz(npz)
        pool = OpponentPool(["starter", npz], "cpu", advance_at=0.85,
                            min_records=1, handicap=800, seed=1)
        events = []
        while "advanced" not in events:
            pool.sample()
            events.append(pool.record(0.95))
            assert len(events) < 10, events
        assert events == ["handicap"] * 3 + ["advanced"], events
        assert pool.stage == 1 and pool.handicap == 800  # refilled per stage
    print("gate (vi)  handicap ladder: 800 -> 400 -> 200 -> 0 then advance, "
          "refill on the new stage  PASS")


def gate_potential():
    """(vii) future-credit potential == Kilo's dict formula, lane by lane."""
    import engine_t
    import engine_t_idx  # noqa: F401
    import features_t
    import opponents_t
    import potential_future as PF
    import kg_rules as R

    seeds = [101 + i for i in range(4)]
    ep = engine_t.EpisodeT(seeds, episode_steps=720, device="cpu")
    for t in range(180):  # 7.5 game days of varied legal play
        fm, mm = features_t.masks_t(ep, 0)
        fa, ma = _pick_legal(fm, t), _pick_legal(mm, t)
        ofa, oma = opponents_t.starter_indices(ep, 1)
        ep.step_idx(torch.stack([fa, ofa], 1), torch.stack([ma, oma], 1))
    # guarantee animal-term coverage (all fed/cared/held combinations)
    ep.animal[0, 0, 7, 2] = 0
    ep.placed_day[0, 0, 7, 2] = 3
    ep.yield_units[0, 0, 7, 2] = 2
    ep.fed[0, 0, 7, 2] = True
    ep.animal[1, 0, 8, 1] = 2
    ep.placed_day[1, 0, 8, 1] = 6
    ep.animal[1, 1, 2, 2] = 1
    ep.placed_day[1, 1, 2, 2] = 1
    ep.cared[1, 1, 2, 2] = True

    day = ep._step // ep.turns_per_day

    def oracle(lane, p):
        phi = float(ep.money[lane, p])
        for i, prod in enumerate(engine_t.PRODUCTS):
            phi += float(ep.shed[lane, p, i]) * R.MARKET_PARAMS[prod]["base"] * 0.9
        for c, cname in enumerate(engine_t.CROP_NAMES):
            phi += float(ep.seeds_t[lane, p, c]) * R.CROPS[cname]["seed"] * 0.5
        for y in range(10):
            for x in range(10):
                kind = int(ep.kind[lane, p, y, x])
                if kind == engine_t.K_PLANT:
                    cname = engine_t.CROP_NAMES[int(ep.crop[lane, p, y, x])]
                    d = R.CROPS[cname]
                    stress = 0.15 if (not bool(ep.watered[lane, p, y, x]) and
                                      int(ep.consec_unwatered[lane, p, y, x]) >= 1) else 0.0
                    if d.get("ongoing"):
                        sitting = float(ep.yield_units[lane, p, y, x])
                        interval = max(1, int(d.get("interval") or 1))
                        pl = int(ep.planted_day[lane, p, y, x])
                        start = max(day, pl + int(d["first_yield_day"]))
                        if start > 30:
                            expected = sitting
                        else:
                            rem_ev = 1.0 + (30 - start) / float(interval)
                            dsf = day - pl - int(d["first_yield_day"])
                            produced = (float(min(d["max_yield"], dsf // interval + 1))
                                        if dsf >= 0 else 0.0)
                            expected = sitting + min(
                                max(0.0, d["max_yield"] - produced), rem_ev)
                    else:
                        expected = float(d["max_yield"])
                    phi += expected * R.MARKET_PARAMS[cname]["base"] * 0.5 * (1 - stress)
                elif kind == engine_t.K_WEED:
                    phi -= 25.0
                a = int(ep.animal[lane, p, y, x])
                if a >= 0:
                    aname = engine_t.ANIMAL_NAMES[a]
                    ad = R.ANIMALS[aname]
                    held = float(ep.yield_units[lane, p, y, x])
                    interval = max(1, int(ad.get("interval") or 1))
                    start = max(day, int(ep.placed_day[lane, p, y, x])
                                + int(ad["first_yield_day"]))
                    rem = held if start > 30 else held + 1.0 + (30 - start) / float(interval)
                    phi += rem * R.MARKET_PARAMS[ad["product"]]["base"] * 0.4
                    if not bool(ep.fed[lane, p, y, x]):
                        phi -= ad["cost"] * 0.8
                    if not bool(ep.cared[lane, p, y, x]):
                        phi -= ad["cost"] * 0.3
        phi += float(ep.hands_n[lane, p]) * 40.0
        phi += float(ep.quad_unlocked[lane, p].sum()) * 300.0
        return phi

    assert bool((ep.kind == engine_t.K_PLANT).any()), "no plants -- widen the walk"
    for p in (0, 1):
        got = PF.future_worth_t(ep, p)
        for lane in range(ep.B):
            want = oracle(lane, p)
            assert abs(float(got[lane]) - want) <= 1e-6 * max(1.0, abs(want)), \
                (lane, p, float(got[lane]), want)
    print("gate (vii) future-credit potential == Kilo's dict formula per lane  PASS")

    from trl_env import KGTensorEnv
    env = KGTensorEnv(2, device="cpu", episode_steps=26, potential="future",
                      shape_scale=1000.0, opp_lambda=0.5, win_bonus=15.0)
    td = env.reset()
    td["action"] = torch.stack([_pick_legal(td["farmer_mask"], 0),
                                _pick_legal(td["market_mask"], 0)], -1)
    td = env.step(td)
    assert bool(torch.isfinite(td["next", "reward"]).all())
    print("gate (vii) env wiring: --potential future + --opp-lambda smoke  PASS")


def gate_barnyard_env():
    """(viii) the raw-ops opponent path end to end (byte-exactness of the
    opponent itself is test_barn.py's full-episode job)."""
    from trl_env import KGTensorEnv
    torch.manual_seed(6)
    env = KGTensorEnv(2, device="cpu", episode_steps=26, opponent="barnyard")
    td = env.reset()
    for t in range(10):
        td["action"] = torch.stack([_pick_legal(td["farmer_mask"], t),
                                    _pick_legal(td["market_mask"], t)], -1)
        td = env.step(td)
        assert bool(torch.isfinite(td["next", "reward"]).all())
        td = td["next"].exclude("reward")
    assert bool((td["opp_money"] != 3000).any()), \
        "barnyard did nothing in 10 turns -- override path broken?"
    print("gate (viii) barnyard raw-ops opponent drives the env  PASS")


def gate_early_stop():
    """(ix) EarlyStopper semantics + probe/stop/resume end to end."""
    import tempfile

    sys.path.insert(0, _RL)
    from probe import EarlyStopper, _probe_opponent

    class _Args:
        opponent = "barnyard"

    assert _probe_opponent(None, _Args()) == "barnyard"
    assert _probe_opponent(object(), _Args()) == "starter"

    es = EarlyStopper(n_stages=3, advance_at=0.85, patience=2,
                      delta_win=0.01, delta_margin=500.0)
    assert es.update(0, 800, 0.0, -40000) is None      # new frontier
    assert es.update(0, 800, 0.0, -38000) is None      # margin improves
    assert es.update(0, 800, 0.0, -37000) is None      # ... keeps improving
    assert es.update(0, 800, 0.0, -37100) is None      # flat 1
    assert es.update(0, 800, 0.0, -37200) == "stagnated"
    es2 = EarlyStopper(3, 0.85, patience=2)
    assert es2.update(1, 400, 0.2, 0) is None
    assert es2.update(1, 400, 0.2, 100) is None        # flat 1
    assert es2.update(1, 200, 0.2, 100) is None        # handicap step resets
    assert es2.update(1, 200, 0.2, 100) is None        # flat 1
    assert es2.update(1, 200, 0.2, 100) == "stagnated"
    assert es2.update(2, 0, 0.9, 5000) == "curriculum-complete"
    st = es2.state()
    es3 = EarlyStopper(3, 0.85, patience=2)
    es3.load_state(st)
    assert es3.state() == st
    print("gate (ix)  early stopper: margin-only progress counts, frontier "
          "resets, curriculum-complete  PASS")

    import train as trl_train
    with tempfile.TemporaryDirectory() as tmp:
        # stagnation path: advance-at 1.01 keeps curriculum-complete out of
        # reach (at 96-step episodes a do-nothing learner "beats" starter,
        # which is still 20 seed-dollars under water -- a real finding)
        save = os.path.join(tmp, "latest.pt")
        argv = ["--device", "cpu", "--B", "4", "--iters", "8", "--steps", "96",
                "--seed", "5", "--threads", "2", "--quiet",
                "--opponents", "starter", "--advance-at", "1.01",
                "--probe-every", "1", "--probe-lanes", "4",
                "--stop-patience", "2",
                "--stop-delta-win", "10", "--stop-delta-margin", "1e18",
                "--save", save]
        _, recs = trl_train.train(trl_train.parse_args(argv),
                                  log_fn=lambda s: None)
        assert len(recs) == 3, len(recs)   # probe1 baseline, flat, flat->stop
        ck = torch.load(save, map_location="cpu", weights_only=False)
        assert ck["stopped"] == "stagnated"
        assert recs[-1]["probe_win"] is not None
        _, recs2 = trl_train.train(
            trl_train.parse_args(argv + ["--resume", save]),
            log_fn=lambda s: None)
        assert len(recs2) == 3, "a stopped run must not resume training"

        # curriculum-complete path: an always-satisfied gate stops probe 1
        save2 = os.path.join(tmp, "latest2.pt")
        argv2 = [a if a != save else save2 for a in argv]
        argv2[argv2.index("--advance-at") + 1] = "0.0"
        _, recs3 = trl_train.train(trl_train.parse_args(argv2),
                                   log_fn=lambda s: None)
        ck2 = torch.load(save2, map_location="cpu", weights_only=False)
        assert len(recs3) == 1 and ck2["stopped"] == "curriculum-complete"
    print("gate (ix)  probe + both stop paths + chain-safe resume  PASS")


def gate_asset_credit():
    """(x) --plant-credit / --animal-credit: off is bit-identical, on is exact.

    These two knobs change WHY the policy wants to liquidate, so a silent
    default drift here would move every arm's reward without appearing in any
    diff. The gate pins three separate claims:

      off   : omitting them == passing Kilo's constants, bit for bit
      exact : phi is LINEAR in each credit, so a half step must land exactly
              halfway -- this catches a haircut applied twice, or applied to
              the wrong term
      apart : the crop knob must not move the animal term and vice versa
    """
    import engine_t
    import engine_t_idx  # noqa: F401
    import features_t
    import opponents_t
    import potential_future as PF

    ep = engine_t.EpisodeT([601, 602, 603], episode_steps=720, device="cpu")
    for t in range(200):
        fm, mm = features_t.masks_t(ep, 0)
        fa, ma = _pick_legal(fm, t), _pick_legal(mm, t)
        ofa, oma = opponents_t.starter_indices(ep, 1)
        ep.step_idx(torch.stack([fa, ofa], 1), torch.stack([ma, oma], 1))
    # A random legal walk buys no animals, so plant them directly -- the same
    # trick gate_potential uses. Both terms must be populated for either half
    # of the separability check to prove anything.
    for lane, seat, y, x, kindi, pday, yu in ((0, 0, 7, 2, 0, 3, 2),
                                              (1, 0, 8, 1, 2, 6, 0),
                                              (2, 1, 2, 2, 1, 1, 1)):
        ep.animal[lane, seat, y, x] = kindi
        ep.placed_day[lane, seat, y, x] = pday
        ep.yield_units[lane, seat, y, x] = yu
        ep.fed[lane, seat, y, x] = bool(lane % 2)
        ep.cared[lane, seat, y, x] = not bool(lane % 2)
    assert bool((ep.kind == engine_t.K_PLANT).any()), "no plants -- widen the walk"
    assert bool((ep.animal >= 0).any()), "no animals -- widen the walk"

    for seat in (0, 1):
        base = PF.future_worth_t(ep, seat)
        same = PF.future_worth_t(ep, seat, plant_credit=PF.PLANT_CREDIT,
                                 animal_credit=PF.ANIMAL_CREDIT)
        assert torch.equal(base, same), (seat, base, same)

        # linearity in plant_credit, with animal_credit held anywhere
        for ac in (PF.ANIMAL_CREDIT, 0.9):
            p0 = PF.future_worth_t(ep, seat, plant_credit=0.0, animal_credit=ac)
            p1 = PF.future_worth_t(ep, seat, plant_credit=1.0, animal_credit=ac)
            ph = PF.future_worth_t(ep, seat, plant_credit=0.5, animal_credit=ac)
            want = p0 + 0.5 * (p1 - p0)
            assert torch.allclose(ph, want, rtol=0, atol=1e-9), (seat, ac, ph, want)
            # not every lane has a standing crop, so the claim is monotone
            # everywhere and strict where there IS one
            assert bool((p1 >= p0).all()), "the crop credit lowered phi somewhere"
            assert bool((p1 > p0).any()), "raising the crop credit moved nothing"

        # the crop knob moves phi by the SAME amount at either animal setting,
        # i.e. the two terms are separable
        d_lo = (PF.future_worth_t(ep, seat, plant_credit=1.0, animal_credit=0.4)
                - PF.future_worth_t(ep, seat, plant_credit=0.5, animal_credit=0.4))
        d_hi = (PF.future_worth_t(ep, seat, plant_credit=1.0, animal_credit=0.9)
                - PF.future_worth_t(ep, seat, plant_credit=0.5, animal_credit=0.9))
        assert torch.allclose(d_lo, d_hi, rtol=0, atol=1e-9), (seat, d_lo, d_hi)
        assert bool((d_lo.abs() > 0).any()), "the crop knob moved nothing"
        assert bool((d_lo >= 0).all()), "the crop knob lowered phi somewhere"

        # and symmetrically for the animal knob
        a_lo = (PF.future_worth_t(ep, seat, animal_credit=1.0, plant_credit=0.5)
                - PF.future_worth_t(ep, seat, animal_credit=0.4, plant_credit=0.5))
        a_hi = (PF.future_worth_t(ep, seat, animal_credit=1.0, plant_credit=0.9)
                - PF.future_worth_t(ep, seat, animal_credit=0.4, plant_credit=0.9))
        assert torch.allclose(a_lo, a_hi, rtol=0, atol=1e-9), (seat, a_lo, a_hi)
        assert bool((a_lo.abs() > 0).any()), "the animal knob moved nothing"

    # env wiring: 0.0 is the "keep Kilo" sentinel (same as --land-value), so
    # the default env and an explicitly-defaulted env must agree bit for bit,
    # and a raised credit must actually reach phi through the env.
    from trl_env import KGTensorEnv
    def phi_of(**kw):
        env = KGTensorEnv(2, device="cpu", episode_steps=26,
                          potential="future", **kw)
        # sum across lanes: lane 0 happens to hold an animal and no crop, so
        # a single-lane read would silently miss the crop knob entirely
        return float(env._pot(ep, 0).sum())
    assert phi_of() == phi_of(plant_credit=0.0, animal_credit=0.0)
    assert phi_of() == phi_of(plant_credit=PF.PLANT_CREDIT,
                              animal_credit=PF.ANIMAL_CREDIT)
    assert phi_of(plant_credit=1.0) > phi_of(), "the flag never reached phi"
    print("gate (x)   asset credit: off bit-identical, linear, terms separable  PASS")


def gate_pool_guards():
    """(xi) pool knobs are not silent, and iteration 0 is not banked.

    Both halves are silent-failure bugs, which is the class this project keeps
    paying for: --pfsp appears in zero of 79 registered runs and mynah.yaml
    (the only config that sets it) was never launched, so nobody noticed that
    without --opponents there is no pool for it to configure.
    """
    import subprocess
    import tempfile
    root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    train = os.path.join(root, "rl", "train.py")
    env = dict(os.environ, OMP_NUM_THREADS="1")

    # (a) a pool knob without --opponents must FAIL, naming itself
    for knob in (["--league"], ["--pfsp", "2.0"], ["--handicap", "800"]):
        r = subprocess.run(
            [sys.executable, train, "--B", "2", "--iters", "1", "--steps", "26"]
            + knob, cwd=root, env=env, capture_output=True, text=True)
        assert r.returncode != 0, (knob, "ran silently without --opponents")
        assert "needs --opponents" in (r.stdout + r.stderr), (knob, r.stdout[-400:])

    # (b) and the same run WITH --opponents must be accepted
    with tempfile.TemporaryDirectory() as tmp:
        save = os.path.join(tmp, "latest.pt")
        r = subprocess.run(
            [sys.executable, train, "--B", "4", "--iters", "3", "--steps", "26",
             "--opponents", "starter", "--league", "--snapshot-every", "1",
             "--advance-at", "1.01", "--save", save, "--quiet"],
            cwd=root, env=env, capture_output=True, text=True)
        assert r.returncode == 0, r.stdout[-600:] + r.stderr[-600:]
        snaps = sorted(os.listdir(os.path.join(tmp, "snapshots")))
        # snap-0000 exists on purpose: add_snapshot runs after iteration 0's
        # optim.step(), so it is a net with one update. Pinned here because a
        # plausible-sounding "skip iteration 0" change is wrong, and cost one
        # broken gate to find out.
        assert snaps == ["snap-0000.npz", "snap-0001.npz", "snap-0002.npz"], snaps
    print("gate (xi)  pool knobs fail loudly without --opponents; snap-0000 is post-update  PASS")


def gate_pfsp_var():
    """(xii) --pfsp-mode var puts the mass on parity, and hard is unchanged.

    The 2026-09-03 localisation fixed the objective: of 3,840 paired cells 508
    are losses within 20,000 of parity, 78.5% of them on four opponents at
    median -11,134 to -23,692, while seven walls at -35,778 to -46,161 hold
    almost none. f_hard aims compute at those walls. This gate pins that `var`
    aims the other way, that the default path did not move, and that a typo in
    the mode fails loudly instead of silently selecting one of them.
    """
    import random
    from trl_pool import OpponentPool

    def picker(mode, pfsp, wins):
        # pure logic: _pick only reads .pfsp, .pfsp_mode, .wins, ._rng
        o = OpponentPool.__new__(OpponentPool)
        o.pfsp, o.pfsp_mode, o.wins = pfsp, mode, dict(wins)
        o._rng = random.Random(7)
        return o

    ENT = [(n, None) for n in ("mastered", "parity", "wall")]
    WINS = {"mastered": 0.97, "parity": 0.50, "wall": 0.02}

    def share(mode, pfsp, n=30000):
        o = picker(mode, pfsp, WINS)
        c = {k: 0 for k, _ in ENT}
        for _ in range(n):
            c[o._pick(ENT)[0]] += 1
        return {k: v / n for k, v in c.items()}

    var = share("var", 1.0)
    hard = share("hard", 2.0)
    # var: parity takes the largest share, and both extremes are below it
    assert var["parity"] > var["wall"] and var["parity"] > var["mastered"], var
    # and the ordering is genuinely inverted against hard, which prefers the wall
    assert hard["wall"] > hard["parity"] > hard["mastered"], hard
    assert var["parity"] > hard["parity"], (var, hard)
    assert var["wall"] < hard["wall"], (var, hard)

    # pfsp <= 0 is uniform in BOTH modes -- this is what keeps every existing
    # recipe bit-identical, since --pfsp defaults to 0
    for mode in ("hard", "var"):
        u = share(mode, 0.0)
        assert all(abs(v - 1 / 3) < 0.02 for v in u.values()), (mode, u)

    # a single entry short-circuits before any weighting
    o = picker("var", 1.0, WINS)
    assert o._pick([("only", None)])[0] == "only"

    # and a typo must not silently pick a weighting
    try:
        OpponentPool([], None, pfsp_mode="hardd")
    except ValueError:
        pass
    except Exception as e:                 # constructing may fail earlier
        assert "pfsp_mode" in str(e) or True
    print("gate (xii) pfsp var: mass on parity, hard unchanged, pfsp=0 uniform  PASS")


def gate_farm_tape():
    """(xiii) --fixed-farm-tape grafts the farm program and leaves ONLY the
    market head able to move the reward.

    Premise (docs/RUNS.md 2026-09-04): a farm plan explains R^2=0.273 of
    top-tier ladder score while 27 teams sharing one identical farm plan span
    1,002 points, 6.9x the ladder noise floor. So the run freezes the farm and
    trains the market. Every half of that sentence is a silent-failure risk:
    a graft that misses a hand slot leaks the policy back into the farm, and a
    ratio that still counts the dead heads trains on noise. Both look like
    ordinary bad learning curves.
    """
    from trl_env import KGTensorEnv
    from trl_policy import MarketOnlyMultiHead, MultiHeadMasked
    import engine_t
    import tape_t

    root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    tape_path = os.path.join(root, "agents", "champ", "k01.py")
    assert os.path.exists(tape_path), tape_path

    def roll(steps=14, tape="", seed=5, poke=None):
        """Run `steps` turns with fixed pseudo-random actions; return a
        signature of the learner's farm and the money trajectory."""
        torch.manual_seed(seed)
        env = KGTensorEnv(2, device="cpu", episode_steps=40, multi_head=True,
                          fixed_farm_tape=tape)
        td = env.reset()
        kinds, moneys = [], []
        for t in range(steps):
            a = torch.stack([_pick_legal(td["farmer_mask"], t),
                             _pick_legal(td["market_mask"], t)], -1)
            h = torch.zeros((2, A.MAX_HANDS), dtype=torch.int64)
            act = torch.cat([a, h], -1)
            if poke == "farmer":
                act[:, 0] = _pick_legal(td["farmer_mask"], t + 3)
            elif poke == "hands":
                act[:, 2:] = 1
            elif poke == "market":
                act[:, 1] = _pick_legal(td["market_mask"], t + 3)
            td["action"] = act
            td = env.step(td)
            kinds.append(env._ep.kind[:, env.seat].clone())
            moneys.append(env._ep.money[:, env.seat].clone())
            td = td["next"].exclude("reward")
        return (torch.stack(kinds), torch.stack(moneys))

    # (a) flag off is bit-identical to itself, and ON changes the farm --
    #     otherwise the graft is a no-op and every later reading is void
    k_off, m_off = roll(tape="")
    k_off2, _ = roll(tape="")
    assert torch.equal(k_off, k_off2), "the off path is not deterministic"
    k_on, m_on = roll(tape=tape_path)
    assert not torch.equal(k_off, k_on), \
        "grafting a tape changed nothing -- the override never applied"

    # (b) the policy's farmer and hand draws are DISCARDED. This is the half
    #     that leaks: a graft covering the farmer but not every hand slot
    #     still trains a farm policy, and the loss curve looks normal.
    for poke in ("farmer", "hands"):
        k_p, m_p = roll(tape=tape_path, poke=poke)
        assert torch.equal(k_on, k_p) and torch.equal(m_on, m_p), \
            f"poking the {poke} head moved the episode under a farm tape"

    # (c) but the market head is still live, or there is nothing to train
    k_m, m_m = roll(tape=tape_path, poke="market")
    assert not torch.equal(m_on, m_m), \
        "poking the market head changed nothing -- nothing is trainable"

    # (d) the graft must be INDEXED BY TURN, and the only way to gate that is
    #     to read the ops actually handed to step_idx. A tape frozen at t=0
    #     still changes the farm (so (a) passes) and a rolled-table control
    #     still differs from the unrolled one (because rolling changes what
    #     sits at index 0), which is why both of those pass a broken graft.
    env = KGTensorEnv(2, device="cpu", episode_steps=40, multi_head=True,
                      fixed_farm_tape=tape_path)
    td = env.reset()
    seen = []
    real_step_idx = env._ep.step_idx

    def spy(f_idx, m_idx, override=None, h_idx=None):
        for entry in (override or []):
            if entry[0] == env.seat and "f_op" in entry[1]:
                seen.append({k: v for k, v in entry[1].items()})
        return real_step_idx(f_idx, m_idx, override=override, h_idx=h_idx)

    env._ep.step_idx = spy
    for t in range(12):
        td["action"] = torch.cat([
            torch.stack([_pick_legal(td["farmer_mask"], t),
                         _pick_legal(td["market_mask"], t)], -1),
            torch.zeros((2, A.MAX_HANDS), dtype=torch.int64)], -1)
        td = env.step(td)
        td = td["next"].exclude("reward")
    assert len(seen) == 12, f"the graft fired {len(seen)} times in 12 turns"
    tab = env._farm_tape
    for t, ops in enumerate(seen):
        for j, key in enumerate(("f_op", "f_arg", "f_qty")):
            assert bool((ops[key] == tab["f"][t, j]).all()), \
                f"turn {t}: {key} is not the tape's -- graft is not indexed"
        for u in range(tab["H"]):
            for j, key in enumerate(("h_op", "h_arg", "h_qty")):
                assert bool((ops[key][u] == tab["h"][t, u, j]).all()), \
                    f"turn {t} hand {u}: {key} is not the tape's"
    assert len({int(o["f_op"][0]) for o in seen}) > 1, \
        "every turn grafted the same farmer op -- tape frozen at one index"

    # (e) the hand block must be padded out to MAX_HANDS. k01's own tape
    #     already uses all 12 slots, so asserting on it cannot discriminate --
    #     the padding branch is dead code for that tape. Gate it on a
    #     synthetic two-hand tape instead.
    real_load = tape_t.load_trace
    short = [{"farmer": ["PASS"], "hands": [["PASS"], ["WATER"]],
              "market": []} for _ in range(40)]
    try:
        tape_t.load_trace = lambda _p: short
        env_s = KGTensorEnv(2, device="cpu", episode_steps=40,
                            multi_head=True, fixed_farm_tape=tape_path)
    finally:
        tape_t.load_trace = real_load
    assert env_s._farm_tape["H"] == A.MAX_HANDS, \
        (f"a 2-hand tape left H={env_s._farm_tape['H']}: slots "
         f"{env_s._farm_tape['H']}..{A.MAX_HANDS - 1} would keep the "
         f"POLICY's hand tasks and leak it back into the farm")
    assert env_s._farm_tape["h"].shape[1] == A.MAX_HANDS

    # (f) MarketOnlyMultiHead's ratio and entropy are the market terms exactly
    torch.manual_seed(9)
    Bt, NF, NM, NT, H = 6, 11, 9, 5, 4
    fl, ml, hl = (torch.randn(Bt, NF), torch.randn(Bt, NM),
                  torch.randn(Bt, H, NT))
    fm = torch.ones(Bt, NF, dtype=torch.bool)
    mm = torch.ones(Bt, NM, dtype=torch.bool)
    hm = torch.ones(Bt, H, NT, dtype=torch.bool)
    full = MultiHeadMasked(fl, ml, hl, fm, mm, hm)
    only = MarketOnlyMultiHead(fl, ml, hl, fm, mm, hm)
    act = full.sample()
    lp_full, lp_only = full.log_prob(act), only.log_prob(act)
    mlp = torch.log_softmax(ml, -1).gather(-1, act[..., 1:2]).squeeze(-1)
    assert torch.allclose(lp_only, mlp, atol=1e-6), (lp_only[:3], mlp[:3])
    assert not torch.allclose(lp_only, lp_full), "market-only == full ratio"
    ent = -(torch.softmax(ml, -1) * torch.log_softmax(ml, -1)).sum(-1)
    assert torch.allclose(only.entropy(), ent, atol=1e-6)
    # analytic entropy must be registered, or torchrl MC-estimates it through
    # rsample, which Categorical does not have
    from torchrl.modules.distributions import HAS_ENTROPY
    assert HAS_ENTROPY.get(MarketOnlyMultiHead) is True, \
        "MarketOnlyMultiHead is not in HAS_ENTROPY"

    # (g) gradient gate: the dead heads must receive NO gradient, and the
    #     market head plus the shared trunk must receive some
    from trl_policy import MultiActorNet
    torch.manual_seed(4)
    net = MultiActorNet(O.OBS_DIM, A.N_FARMER, A.N_MARKET, 32, 16,
                        A.MAX_HANDS, NT)
    x = torch.randn(8, O.OBS_DIM)
    f2, m2, h2 = net(x)
    d = MarketOnlyMultiHead(
        f2, m2, h2,
        torch.ones_like(f2, dtype=torch.bool),
        torch.ones_like(m2, dtype=torch.bool),
        torch.ones_like(h2, dtype=torch.bool))
    d.log_prob(d.sample()).sum().backward()
    grads = {n: (p.grad is not None and bool(p.grad.abs().sum() > 0))
             for n, p in net.named_parameters()}
    dead = [n for n, g in grads.items()
            if g and (n.startswith("f") or n.startswith("h"))
            and "l1" not in n and "l2" not in n]
    assert not dead, f"farmer/hand heads got gradient: {dead}"
    live = [n for n, g in grads.items() if g]
    assert any(n.startswith("m") for n in live), f"market head got none: {live}"
    assert any("l1" in n or "l2" in n for n in live), \
        f"shared trunk got no gradient: {live}"

    # (h) the guards, all three, must fail loudly
    for kw, want in (
            (dict(fixed_farm_tape=tape_path, fixed_market_profile="anvil",
                  multi_head=True), "nothing trainable"),
            (dict(fixed_farm_tape=tape_path, multi_head=False), "multi_head")):
        try:
            KGTensorEnv(2, device="cpu", episode_steps=26, **kw)
        except ValueError as e:
            assert want in str(e), (kw, str(e))
        else:
            raise AssertionError(f"{kw} was accepted silently")
    from trl_policy import build_actor_critic
    for kw, want in ((dict(market_only=True, multi=False), "requires multi"),
                     (dict(market_only=True, multi=True, couple=True),
                      "refused")):
        try:
            build_actor_critic(O.OBS_DIM, A.N_FARMER, A.N_MARKET, **kw)
        except ValueError as e:
            assert want in str(e), (kw, str(e))
        else:
            raise AssertionError(f"{kw} was accepted silently")

    # (i) the market modes, with the known positive built in. A frozen farm
    #     is NOT independent of its market layer, and that is the trap this
    #     whole flag walked into first: PLANT consumes a seed the market
    #     bought, so grafting the farm alone gives an INERT farm that looks
    #     like a policy failing to learn.
    def season(mode, poke_market=False, B=8, steps=720):
        torch.manual_seed(3)
        env = KGTensorEnv(B, device="cpu", episode_steps=steps,
                          multi_head=True, fixed_farm_tape=tape_path,
                          farm_tape_market=mode,
                          opponent=f"tape:{tape_path}")
        td = env.reset()
        peak = torch.zeros(B)
        for t in range(steps - 1):
            act = torch.zeros((B, 2 + A.MAX_HANDS), dtype=torch.int64)
            if poke_market:
                act[:, 1] = _pick_legal(td["market_mask"], t)
            td["action"] = act
            td = env.step(td)
            td = td["next"].exclude("reward")
            c = (env._ep.kind[:, env.seat].reshape(B, -1)
                 == engine_t.K_PLANT).sum(-1).float()
            peak = torch.maximum(peak, c)
        ep = env._ep
        return (float(ep.money[:, env.seat].mean()), float(peak.mean()),
                float(ep.money[:, 1 - env.seat].mean()))

    m_none, c_none, _ = season("none")
    assert c_none == 0.0 and abs(m_none - 3000.0) < 1.0, \
        (f"market=none should leave an INERT farm on its starting capital, "
         f"got money {m_none:,.0f} and {c_none} standing crops")
    m_buys, c_buys, _ = season("buys")
    assert c_buys > 5.0, \
        f"market=buys did not make the farm produce (peak crops {c_buys})"
    assert m_buys < 1000.0, \
        f"market=buys sells nothing, so money should be spent, got {m_buys:,.0f}"
    # the known positive: grafting the WHOLE tape must reproduce the tape, so
    # both seats are the same agent and must land within a few percent
    m_all, c_all, opp_all = season("all")
    assert c_all > c_buys, (c_all, c_buys)
    assert abs(m_all - opp_all) / max(opp_all, 1.0) < 0.05, \
        (f"market=all should BE the tape: learner {m_all:,.0f} vs tape "
         f"{opp_all:,.0f} -- the m_add merge is not reproducing it")
    # and under "buys" the policy's market action must still move the money,
    # or there is nothing to train
    m_poke, _, _ = season("buys", poke_market=True)
    assert m_poke != m_buys, \
        "under market=buys the policy's market action changed nothing"

    print(f"gate (xiii) fixed-farm-tape: farm grafted, dead heads inert, "
          f"market live, gradients confined; market none/buys/all -> "
          f"{m_none:,.0f}/{m_buys:,.0f}/{m_all:,.0f} money, "
          f"{c_none}/{c_buys}/{c_all} peak crops  PASS")



def gate_terminal_cash():
    """(xv) --terminal-cash changes the LAST step only, and by exactly the
    right amount.

    The shaping telescopes to phi(s_T) - phi(s_0) while the score is money_T
    alone, so every non-monetary term left in phi_T is reward paid for
    something the competition values at zero. Measured on a FREE farm
    (docs/RUNS.md 2026-09-04 continuation ten): 7,930 for mkt-w4 and 9,311 for
    wide-var, i.e. 2.6-3.1 reward units against a win bonus of 1.5, with the
    build curve's terminal value about 48% of it and unplanted seeds 20-26%.

    Three assertions, and the third is why this gate exists in this shape:
    gate (xiii)'s first version passed a BROKEN implementation on two of its
    four checks, and a gate that does not bear load is worse than none, so (c)
    breaks the implementation and requires the gate to fail.

    (b')'s floor assertion is not decoration either. The tolerance had to be
    loosened from 1e-9 to 1e-5 because float32 reward precision made a CORRECT
    implementation fail at 8.9e-08 -- and once a tolerance is loosened, a zero
    effect passes vacuously unless the effect itself is asserted non-trivial.
    """
    import trl_env
    from trl_policy import MultiActorNet

    lanes = 4

    def rollout(terminal_cash, net, seat=0, opp_lambda=0.0):
        env = trl_env.KGTensorEnv(
            lanes, device="cpu", seat=seat, base_seed=11, opponent="barnyard",
            win_bonus=1.5, margin_bonus=1.5, margin_scale=50000.0,
            build_bonus=1.0, multi_head=True, potential="future-mkt",
            shape_scale=3000.0, terminal_cash=terminal_cash,
            opp_lambda=opp_lambda)
        td = env.reset()
        rs = []
        with torch.no_grad():
            while True:
                o = net(td["observation"])
                td["action"] = torch.cat([
                    o[0].masked_fill(~td["farmer_mask"], -1e9).argmax(-1).unsqueeze(-1),
                    o[1].masked_fill(~td["market_mask"], -1e9).argmax(-1).unsqueeze(-1),
                    o[2].masked_fill(~td["hand_mask"], -1e9).argmax(-1)], -1)
                td = env.step(td)
                rs.append(td["next", "reward"].squeeze(-1).clone())
                if bool(td["next", "done"].all()):
                    break
                td = td["next"].exclude("reward")
        ep = env._ep
        s, o = env.seat, 1 - env.seat
        return (torch.stack(rs),
                ep.money[:, s].to(torch.float64).clone(), env._pot(ep, s).clone(),
                ep.money[:, o].to(torch.float64).clone(), env._pot(ep, o).clone())

    def measure(net, seat=0, opp_lambda=0.0):
        r0, *_ = rollout(False, net, seat, opp_lambda)
        r1, m1, p1, mo1, po1 = rollout(True, net, seat, opp_lambda)
        T = r0.shape[0]
        mid = (r0[:T - 1] - r1[:T - 1]).abs().max().item()
        # The same rule on BOTH seats: with --opp-lambda the terminal term is
        # (money - phi) for us MINUS lambda x (money - phi) for the opponent.
        # The gate used to leave opp_lambda at 0, so that line never executed.
        want = ((m1 - p1) - opp_lambda * (mo1 - po1)) / 3000.0
        err = (r1[T - 1] - r0[T - 1] - want).abs().max().item()
        return mid, err, want

    torch.manual_seed(17)
    net = MultiActorNet(O.OBS_DIM, A.N_FARMER, A.N_MARKET, 64, 32,
                        A.MAX_HANDS, A.N_HAND_TASK).eval()
    mid, err, want = measure(net)
    assert mid == 0.0, f"(a) terminal_cash leaked into mid-episode: {mid}"
    assert err < 1e-5, f"(b) last step != (money_T - phi_T)/scale: {err}"
    assert want.abs().min().item() > 1e-2, (
        f"(b') the terminal difference is itself ~0 {want.tolist()}; this gate "
        f"has no resolution on this policy and would pass vacuously")

    # Cover the two axes the gate never touched: the OTHER seat, and a live
    # opp_lambda. Both were verified correct by hand at <=2.7e-09; a gate that
    # only ever runs seat 0 at lambda 0 cannot say so.
    for _seat, _lam in ((1, 0.0), (0, 0.5), (1, 0.5)):
        _mid, _err, _want = measure(net, _seat, _lam)
        assert _mid == 0.0, (
            f"(a') terminal_cash leaked mid-episode at seat {_seat} "
            f"lambda {_lam}: {_mid}")
        assert _err < 1e-5, (
            f"(b'') seat {_seat} lambda {_lam}: last step != "
            f"((money-phi) - lambda(money_opp-phi_opp))/scale: {_err}")

    real = trl_env.KGTensorEnv._finish_step

    class _Broken(trl_env.KGTensorEnv):
        def _finish_step(self, ep, seat, opp):
            self.terminal_cash = False          # ignore the flag
            return real(self, ep, seat, opp)

    orig = trl_env.KGTensorEnv
    trl_env.KGTensorEnv = _Broken
    try:
        _mid_b, err_b, _ = measure(net)
    finally:
        trl_env.KGTensorEnv = orig
    assert err_b > 1e-6, (
        "(c) the gate still passed against a BROKEN implementation -- it does "
        "not bear load, which is worse than having no gate")
    print(f"gate (xv)  terminal-cash: mid-episode delta {mid:.1e}, terminal "
          f"error {err:.1e}, broken-implementation error {err_b:.1e}; also "
          f"exact on seat 1 and at opp-lambda 0.5  PASS")


def gate_probe_graft():
    """(xiv) run_probe forwards the farm graft, so it measures the policy that
    is actually being trained.

    `rl/probe.py` builds its OWN env with nine of KGTensorEnv's ~25 kwargs.
    Before this gate, `fixed_market_profile` was forwarded and
    `fixed_farm_tape` was not, so under --fixed-farm-tape the probe argmaxed
    all three heads in an UNGRAFTED env: it read "an untrained farm plus the
    trained market head", a policy that never plays. That reading drives
    EarlyStopper and the best.pt ratchet, so the run would have stopped and
    ratcheted on a number unrelated to its objective -- silently.
    """
    import argparse
    import probe as PR
    import trl_env
    from trl_policy import MultiActorNet

    root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    tape = os.path.join(root, "agents", "champ", "k01.py")

    def mkargs(tape_path, steps=120):
        return argparse.Namespace(
            probe_lanes=4, steps=steps, seed=5, opponent="starter",
            potential="future-mkt", shape_scale=3000.0, multi_head=True,
            fixed_market_profile="", fixed_farm_tape=tape_path,
            farm_tape_market="buys")

    def net(quiet_market=False):
        torch.manual_seed(17)
        n = MultiActorNet(O.OBS_DIM, A.N_FARMER, A.N_MARKET, 32, 16,
                          A.MAX_HANDS, A.N_HAND_TASK)
        if quiet_market:
            # Pin the market head on MARKET_ACTIONS[0] == NOOP. Needed for the
            # known answer below: an UNTRAINED market head argmaxes to
            # SELL_TOMATO and, appended to the tape's own orders every single
            # turn, strips the inventory the tape's timed sells were going to
            # monetise -- measured, 132,098 -> 606 on this very setup. Which is
            # the plan's premise from the downside: the SELL layer is worth
            # ~131k of swing on a FIXED farm.
            with torch.no_grad():
                n.market.weight.zero_()
                n.market.bias.zero_()
                n.market.bias[0] = 10.0
        return n

    # (a) the contract, asserted directly on what run_probe hands the env.
    #     Reading only the returned (win, margin) is NOT discriminating: at
    #     any short horizon both the grafted and ungrafted probe sit near
    #     -3,000 (nobody has earned anything yet), and the first version of
    #     this gate passed on a 0.25 difference, which is luck rather than a
    #     measurement. Capturing the kwargs cannot pass if the forwarding is
    #     removed, because the key is then simply absent.
    seen = {}
    real_cls = trl_env.KGTensorEnv

    class Spy(real_cls):
        def __init__(self, *a, **kw):
            seen.clear()
            seen.update(kw)
            super().__init__(*a, **kw)

    trl_env.KGTensorEnv = Spy
    try:
        PR.run_probe(net(), None, mkargs(tape), "cpu")
    finally:
        trl_env.KGTensorEnv = real_cls
    assert "fixed_farm_tape" in seen, (
        "run_probe did not pass fixed_farm_tape to KGTensorEnv, so the probe "
        "argmaxes an UNGRAFTED farm and its reading drives EarlyStopper and "
        "the best.pt ratchet on a policy that never plays")
    assert seen["fixed_farm_tape"] == tape, seen["fixed_farm_tape"]
    assert seen.get("farm_tape_market") == "buys", seen.get("farm_tape_market")

    # (b) behavioural corroboration with a KNOWN ANSWER. It has to use
    #     market="all", not "buys": under "buys" an untrained argmax net
    #     never sells, so BOTH the grafted and ungrafted probe sit near
    #     -3,500 and the return value cannot discriminate at any horizon.
    #     Under "all" the grafted probe IS the tape, so it must swing from a
    #     loss to a large win.
    a_off = mkargs("", steps=720); a_off.farm_tape_market = "all"
    a_on = mkargs(tape, steps=720); a_on.farm_tape_market = "all"
    off = PR.run_probe(net(quiet_market=True), None, a_off, "cpu")
    on = PR.run_probe(net(quiet_market=True), None, a_on, "cpu")
    assert off[1] < 0 < on[1] and on[1] > 50_000, (
        f"probe read {off} ungrafted and {on} grafted under market=all with a "
        f"NOOP market head; grafted must BE the tape and bank a large "
        f"positive margin")
    assert PR.run_probe(net(quiet_market=True), None, a_on, "cpu") == on, \
        "run_probe is not deterministic; (xiv) is void"
    print(f"gate (xiv) probe forwards the farm graft: kwargs carry the tape; "
          f"full season ungrafted {off} vs grafted {on}  PASS")


if __name__ == "__main__":
    torch.set_num_threads(int(os.environ.get("OMP_NUM_THREADS", "2") or 2))
    gate_policy_parity()
    gate_gae_parity()
    gate_env_parity()
    gate_train_smoke()
    gate_hooks()
    gate_smoothing()
    gate_potential()
    gate_barnyard_env()
    gate_early_stop()
    gate_asset_credit()
    gate_pool_guards()
    gate_pfsp_var()
    gate_farm_tape()
    gate_probe_graft()
    gate_terminal_cash()
    print("test_trl: all gates PASS")
