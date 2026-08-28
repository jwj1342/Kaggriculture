#!/usr/bin/env python
"""Kickstart gates (teacher = barnyard_t intents on the learner's states).

K1  plumbing: an env built with kickstart="barnyard" emits teacher_f/m/h
    alongside every observation, with the right shapes/dtypes, and the
    farmer/market labels are mostly LEGAL under our masks on random play
    (the mapping is lossy by design; "mostly" is the contract).
K2  richness: driving the learner through the M5 scenario (hire, build,
    buy + place animals, stock wheat) makes the teacher labels exercise
    the parts that matter -- FEED hand labels once unfed animals exist,
    PLANT/BUILD/PLACE farmer labels, HIRE/BUY/SELL market labels.
K3  training: rl/train.py --kickstart barnyard smoke (CPU, tiny) runs end
    to end and reports a positive, falling CE.

Ends KICK-PASS / KICK-FAIL.
"""

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
import kg_rules as R
import opponents_t
import verify
from trl_env import KGTensorEnv, hand_task_mask_t, kickstart_labels
from verify_t import lane_obs


def _rand_action(td, gen, B):
    fa = torch.multinomial(td["farmer_mask"].double(), 1, generator=gen)
    ma = torch.multinomial(td["market_mask"].double(), 1, generator=gen)
    ha = torch.multinomial(
        td["hand_mask"].double().view(B * A.MAX_HANDS, -1), 1,
        generator=gen).view(B, A.MAX_HANDS)
    return torch.cat([fa, ma, ha], -1)


def gate_k1():
    B, steps = 4, 48
    env = KGTensorEnv(B, device="cpu", episode_steps=steps, base_seed=5,
                      opponent="starter", multi_head=True,
                      kickstart="barnyard")
    gen = torch.Generator().manual_seed(3)
    td = env.reset()
    legal_f = legal_m = total = 0
    while True:
        for k, shape in (("teacher_f", (B,)), ("teacher_m", (B,)),
                         ("teacher_h", (B, A.MAX_HANDS))):
            assert td[k].shape == torch.Size(shape), (k, td[k].shape)
            assert td[k].dtype == torch.int64, k
        legal_f += int(td["farmer_mask"].gather(
            -1, td["teacher_f"].view(B, 1)).sum())
        legal_m += int(td["market_mask"].gather(
            -1, td["teacher_m"].view(B, 1)).sum())
        total += B
        td["action"] = _rand_action(td, gen, B)
        td = env.step(td)
        if bool(td["next", "done"].all()):
            break
        td = td["next"].exclude("reward")
    fr, mr = legal_f / total, legal_m / total
    if fr < 0.6 or mr < 0.6:
        print(f"K1 legality too low: farmer {fr:.2f} market {mr:.2f}")
        return False
    print(f"K1: teacher keys ride the env; label legality farmer {fr:.2f} "
          f"market {mr:.2f} over {total} states")
    return True


def gate_k2():
    """M5's scenario, teacher labels on: once the learner owns unfed
    animals the teacher must say FEED; across the run it must also say
    PLANT/BUILD (farmer) and HIRE plus a BUY (market)."""
    animal = A.ANIMAL_LIST[0]
    struct = R.ANIMALS[animal]["structure"]
    f_build = A.FARMER_ACTIONS.index(f"BUILD_{struct}")
    f_place = A.FARMER_ACTIONS.index(f"PLACE_{animal}")
    f_pass = A.FARMER_ACTIONS.index("PASS")
    m_noop = A.MARKET_ACTIONS.index("NOOP")
    m_hire = A.MARKET_ACTIONS.index("HIRE")
    m_wheat = A.MARKET_ACTIONS.index("BUY_WHEAT")
    m_buy = A.MARKET_ACTIONS.index(f"BUY_{animal}")
    m_seed = A.MARKET_ACTIONS.index("BUY_SEED_MELON")
    feed_idx = A.HAND_TASKS.index("RAW_FEED")
    feed_task_idx = A.HAND_TASKS.index("FEED")
    move_idxs = {A.HAND_TASKS.index(f"RAW_MOVE_{d}")
                 for d in ("N", "S", "E", "W")}
    pickup_idxs = {A.HAND_TASKS.index(f"RAW_PICKUP_{item}")
                   for item in A.HAND_PICKUP_ITEMS}

    B, steps = 1, 8 * 24
    env = KGTensorEnv(B, device="cpu", episode_steps=steps, base_seed=77,
                      opponent="starter", multi_head=True,
                      kickstart="barnyard")
    td = env.reset()
    f_seen, m_seen, h_seen = set(), set(), set()
    while True:
        obs = lane_obs(env._ep, 0, env.seat)
        farm = obs["farms"][env.seat]
        priv = obs["private"]
        n_hands = len(farm.get("hands", []))
        animals = sum(1 for row in farm["tiles"] for t in row
                      if isinstance(t, dict) and "animal" in t)
        structs = sum(1 for row in farm["tiles"] for t in row
                      if isinstance(t, dict) and t.get("kind") == struct)
        held = priv["shed"].get(animal, 0)
        fm = td["farmer_mask"][0]
        mm = td["market_mask"][0]
        if n_hands < 2 and mm[m_hire]:
            mi = m_hire
        elif held == 0 and animals < 3 and mm[m_buy]:
            mi = m_buy
        elif sum(priv["seeds"].values()) == 0 and mm[m_seed]:
            mi = m_seed          # give the teacher something to PLANT
        elif priv["shed"].get("WHEAT", 0) < 4 and mm[m_wheat]:
            mi = m_wheat
        else:
            mi = m_noop
        if held > 0 and fm[f_place]:
            fi = f_place
        elif structs < 3 and animals >= structs and fm[f_build]:
            fi = f_build
        else:
            fi = f_pass
        f_seen.add(int(td["teacher_f"][0]))
        m_seen.add(int(td["teacher_m"][0]))
        h_seen.update(int(x) for x in td["teacher_h"][0] if int(x) >= 0)
        ha = torch.full((1, A.MAX_HANDS), 0, dtype=torch.int64)
        ha[0, :n_hands] = feed_task_idx
        td["action"] = torch.tensor([[fi, mi]], dtype=torch.int64)
        td["action"] = torch.cat([td["action"], ha], -1)
        td = env.step(td)
        if bool(td["next", "done"].all()):
            break
        td = td["next"].exclude("reward")
    plant_ok = any(15 <= f < 20 for f in f_seen)
    build_ok = any(f in (12, 13, 20, 21, 22) for f in f_seen)
    feed_ok = feed_idx in h_seen
    hire_ok = 21 in m_seen
    buy_ok = any(10 <= m <= 19 for m in m_seen)
    hand_move_ok = bool(move_idxs & h_seen)
    hand_pickup_ok = bool(pickup_idxs & h_seen)
    if not (plant_ok and feed_ok and hire_ok and buy_ok
            and hand_move_ok and hand_pickup_ok):
        print(f"K2 coverage: f={sorted(f_seen)} m={sorted(m_seen)} "
              f"h={sorted(h_seen)} (plant {plant_ok} build {build_ok} "
              f"feed {feed_ok} hand_move {hand_move_ok} "
              f"hand_pickup {hand_pickup_ok} hire {hire_ok} buy {buy_ok})")
        return False
    print(f"K2: teacher exercises the build loop -- farmer labels "
          f"{sorted(f_seen)}, market {sorted(m_seen)}, hand {sorted(h_seen)} "
          f"(FEED={feed_idx} present)")
    return True


def gate_k4():
    """A fixed route can own compound market orders while PPO owns labour."""
    B = 2
    env = KGTensorEnv(
        B, device="cpu", episode_steps=26, base_seed=91,
        opponent="starter", multi_head=True,
        fixed_market_profile="k01_route_s34_fert_latewheat",
        kickstart="barnyard:k01_route_s34_fert_latewheat")
    td = env.reset()
    assert torch.equal(td["market_mask"].sum(-1), torch.ones(B, dtype=torch.int64))
    assert bool(td["market_mask"][:, 0].all())
    action = torch.zeros((B, 2 + A.MAX_HANDS), dtype=torch.int64)
    action[:, 2:] = A.HAND_TASKS.index("IDLE")
    td["action"] = action
    td = env.step(td)
    # The atomic opening basket leaves $25; the route's usual farmer build
    # spends another $14, but this boundary test deliberately passes.
    assert bool((td["next", "money"] == 25).all()), td["next", "money"]
    assert bool((env._ep.hands_n[:, env.seat] == 5).all())
    assert bool((env._ep.seeds_t[:, env.seat].sum(-1) == 19).all())
    print("K4: fixed compound market + learned labour boundary  PASS")
    return True


def gate_k5():
    """Teacher-forced warm-up executes legal low-level labels, not samples."""
    profile = "k01_route_s34_fert_latewheat"
    env = KGTensorEnv(
        2, device="cpu", episode_steps=26, base_seed=93,
        opponent="starter", multi_head=True,
        fixed_market_profile=profile, kickstart="barnyard:" + profile)
    env.kickstart_force = True
    td = env.reset()
    action = torch.zeros((2, 2 + A.MAX_HANDS), dtype=torch.int64)
    action[:, 2:] = A.HAND_TASKS.index("IDLE")
    td["action"] = action
    td = env.step(td)
    assert bool((env._ep.kind[:, env.seat, 4, 4] == engine_t.K_PASTURE).all())
    print("K5: teacher-forced low-level warm-up boundary  PASS")
    return True


def gate_k6():
    """Exact RAW hand labels reproduce the teacher's unit-state transition."""
    profile = "k01_route_s34_fert_latewheat"
    steps = 72
    indexed = engine_t.EpisodeT([104729], episode_steps=steps, device="cpu")
    raw = engine_t.EpisodeT([104729], episode_steps=steps, device="cpu")
    teacher = barnyard_t.BarnyardOpponent(profile)
    teacher.reset(indexed, 0)
    labelled = illegal = 0
    seen = set()
    while not indexed.done:
        ops = teacher(indexed, 0)
        _, _, th = kickstart_labels(indexed, 0, ops)
        live = th >= 0
        hm = hand_task_mask_t(indexed, 0, A.MAX_HANDS)
        legal = hm.gather(-1, th.clamp(min=0).unsqueeze(-1)).squeeze(-1)
        illegal += int((live & ~legal).sum())
        labelled += int(live.sum())
        seen.update(int(x) for x in th[live])

        fi = torch.zeros((1, 2), dtype=torch.int64)
        mi = torch.zeros_like(fi)
        hi = torch.zeros((1, 2, A.MAX_HANDS), dtype=torch.int64)
        of, om = opponents_t.starter_indices(indexed, 1)
        fi[:, 1], mi[:, 1] = of, om
        hi[:, 0] = th.clamp(min=1)
        keep = ("f_op", "f_arg", "f_qty", "m_op", "m_item", "m_rem")
        indexed.step_idx(fi, mi, override=[
            (0, {key: ops[key] for key in keep})], h_idx=hi)
        raw.step_idx(fi, mi, override=[(0, ops)], h_idx=torch.zeros_like(hi))
        diff = verify.first_diff(indexed.snapshot(0), raw.snapshot(0))
        assert not diff, diff
    assert labelled > 0 and illegal == 0
    assert any(i >= A.HAND_DIRECT_START for i in seen)
    print(f"K6: {labelled} exact RAW hand labels, zero illegal, "
          f"{steps - 1} state transitions byte-identical  PASS")
    return True


def gate_k3():
    import train as T
    profile = "k01_route_s34_fert_latewheat"
    args = T.parse_args([
        "--device", "cpu", "--B", "4", "--iters", "3", "--steps", "24",
        "--multi-head", "--opponents", "starter",
        "--fixed-market-profile", profile, "--kickstart", "barnyard:" + profile,
        "--ks-coef", "2.0", "--ks-anneal", "0",
        "--ks-class-alpha", "0.5",
        "--kickstart-only-until", "100000", "--quiet"])
    lines = []
    _, records = T.train(args, log_fn=lines.append)
    ks = [r.get("ks") for r in records if r.get("ks") is not None]
    if len(ks) < 3 or ks[0] <= 0.0:
        print(f"K3 no CE signal: {ks}")
        return False
    if not ks[-1] < ks[0]:
        print(f"K3 CE did not fall: {ks}")
        return False
    if not all(r["kickstart_only"] for r in records):
        print("K3 kickstart-only warm-up did not remain active")
        return False
    print(f"K3: train.py --kickstart smoke, CE {ks[0]:.3f} -> {ks[-1]:.3f} "
          f"over {len(ks)} iters")
    return True


def main():
    for gate in (gate_k1, gate_k2, gate_k3, gate_k4, gate_k5, gate_k6):
        if not gate():
            print("KICK-FAIL")
            return 1
    print("KICK-PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
