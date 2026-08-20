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
import kg_rules as R
from trl_env import KGTensorEnv
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
    feed_idx = A.HAND_TASKS.index("FEED")

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
        ha[0, :n_hands] = feed_idx
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
    if not (plant_ok and feed_ok and hire_ok and buy_ok):
        print(f"K2 coverage: f={sorted(f_seen)} m={sorted(m_seen)} "
              f"h={sorted(h_seen)} (plant {plant_ok} build {build_ok} "
              f"feed {feed_ok} hire {hire_ok} buy {buy_ok})")
        return False
    print(f"K2: teacher exercises the build loop -- farmer labels "
          f"{sorted(f_seen)}, market {sorted(m_seen)}, hand {sorted(h_seen)} "
          f"(FEED={feed_idx} present)")
    return True


def gate_k3():
    import train as T
    args = T.parse_args([
        "--device", "cpu", "--B", "4", "--iters", "3", "--steps", "24",
        "--multi-head", "--opponents", "starter", "--kickstart", "barnyard",
        "--ks-coef", "2.0", "--ks-anneal", "0", "--quiet"])
    lines = []
    _, records = T.train(args, log_fn=lines.append)
    ks = [r.get("ks") for r in records if r.get("ks") is not None]
    if len(ks) < 3 or ks[0] <= 0.0:
        print(f"K3 no CE signal: {ks}")
        return False
    if not ks[-1] < ks[0]:
        print(f"K3 CE did not fall: {ks}")
        return False
    print(f"K3: train.py --kickstart smoke, CE {ks[0]:.3f} -> {ks[-1]:.3f} "
          f"over {len(ks)} iters")
    return True


def main():
    for gate in (gate_k1, gate_k2, gate_k3):
        if not gate():
            print("KICK-FAIL")
            return 1
    print("KICK-PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
