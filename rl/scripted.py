#!/usr/bin/env python
"""A scripted expert *inside the macro action space* (same heads the policy
picks from). Two jobs:

1. Ceiling check: the best RL policy cannot out-earn what this action space
   physically supports. If the script cannot clear ~30k, the action space is
   the bottleneck and no amount of PPO fixes it -- measure before training
   harder (README §11.1).
2. Optional behaviour-cloning teacher for the policy net init.

    python rl/scripted.py --episodes 2 --opponent starter

Returns (f_idx, m_idx) through the exact mask/decode path the learner uses.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np

import actions as A
import kg_rules as R
from actions import _F_IDX, _M_IDX, _me, _scan
from kg_rules import _fib
from kg_env import KGEnv

CROP_LIST = list(R.CROPS)


def scripted_action(obs):
    """(f_idx, m_idx) for the current state. Mask-consistent by construction:
    everything chosen here is mechanically possible.

    Shape of the strategy (all lessons from the first traced attempt, which
    deadlocked at $148 with a dead sell threshold and a rigid hire floor):
    cash flow first -- sell continuously, never let money starve the loop;
    hire while the next fib cost fits a % of cash (barnyard's rule); animals
    over crops in the long run; plant only what the workforce can water.
    """
    farm, priv, inv, pos = _me(obs)
    s = _scan(obs)
    day = obs.get("day", 0)
    money = farm["money"]
    shed = priv["shed"]
    seeds = priv["seeds"]
    prices = obs["market"]["prices"]
    n_hands = len(farm.get("hands", []))
    workforce = 1 + n_hands

    n_goose = n_cow = n_sheep = 0
    for row in farm["tiles"]:
        for t in row:
            if isinstance(t, dict) and "animal" in t:
                a = t["animal"]
                n_goose += a == "GOOSE"
                n_cow += a == "COW"
                n_sheep += a == "SHEEP"
    n_animals = n_goose + n_cow + n_sheep

    def has(item):
        return shed.get(item, 0) + inv.get(item, 0)

    wheat_stock = has("WHEAT")
    feed_reserve = 0 if day >= R.LIQUIDATE_DAY else 2 * n_animals
    sellable = [p for p in A.PRODUCT_LIST
                if shed.get(p, 0) > (feed_reserve if p == "WHEAT" else 0)]

    def best_sale():
        return "SELL_" + max(sellable, key=lambda p: shed[p] * prices[p])

    # ---- market head -----------------------------------------------------
    m = "NOOP"
    quads = len(farm["unlocked_quadrants"])
    # Cash gate before buying the next quadrant ($1000/$2000/$4000): keep a
    # working float after the purchase.
    land_gate = [2000, 3600, 6500][quads - 1] if quads < 4 else None
    next_hire = _fib(farm.get("hires_today", 0))
    want_seeds = (day <= 24
                  and sum(seeds.values()) < min(4 + workforce, len(s["empty"]))
                  and len(s["unwatered"]) < workforce * 3)

    if day >= R.LIQUIDATE_DAY:
        m = best_sale() if sellable else "NOOP"
    elif money < 250 and sellable:
        m = best_sale()
    elif n_hands < A.MAX_HANDS and day >= 1 and next_hire <= max(4, 0.05 * money):
        m = "HIRE"
    elif land_gate is not None and money >= land_gate and day <= 24:
        m = "BUY_LAND"
    elif n_animals and wheat_stock < 2 * n_animals \
            and money >= prices["WHEAT"] * 5 + 150:
        m = "BUY_WHEAT"
    elif s["coop_free"] and money >= 500 and not has("GOOSE"):
        m = "BUY_GOOSE"
    elif s["pasture_free"] and money >= 700 and not (has("COW") or has("SHEEP")):
        m = "BUY_COW" if n_cow <= n_sheep else "BUY_SHEEP"
    elif want_seeds and 3 <= day <= 18 and money >= 600:
        m = "BUY_SEED_MELON"
    elif want_seeds and money >= 300:
        m = "BUY_SEED_CARROT" if day <= 25 else "NOOP"
    elif sellable and (max(shed.get(p, 0) for p in sellable) >= 8
                       or money < 1000):
        m = best_sale()

    # ---- farmer head -----------------------------------------------------
    f = "PASS"
    plantable = [c for c in CROP_LIST
                 if seeds.get(c, 0) > 0 and day <= R.LAST_PLANT_DAY[c]]
    can_water = len(s["unwatered"]) < workforce * 3
    if s["unfed"] and wheat_stock > 0:
        f = "FEED"
    elif has("GOOSE") and s["coop_free"]:
        f = "PLACE_GOOSE"
    elif has("COW") and s["pasture_free"]:
        f = "PLACE_COW"
    elif has("SHEEP") and s["pasture_free"]:
        f = "PLACE_SHEEP"
    elif plantable and s["empty"] and can_water:
        f = f"PLANT_{max(plantable, key=lambda c: seeds[c])}"
    elif (s["empty"] and day <= 23 and money >= 400
          and not s["coop_free"] and not s["pasture_free"]
          and (has("GOOSE") or has("COW") or has("SHEEP") or money >= 800)):
        # planting is covered; expand animal capacity
        f = "BUILD_COOP" if n_goose <= n_cow + n_sheep else "BUILD_PASTURE"
    elif day >= R.LIQUIDATE_DAY and s["harvest"]:
        f = "HARVEST"
    elif s["unwatered"] and n_hands < 3:
        f = "WATER"
    elif s["harvest"] and n_hands < 3:
        f = "HARVEST"
    elif s["uncared"] and n_hands < 3:
        f = "CARE"
    elif s["fert_ready"] and n_hands < 3:
        f = "COLLECT_FERT"
    elif sum(inv.values()) >= 6:
        f = "DROP"
    elif money >= 350 and s["empty"] and day <= 23 and not s["coop_free"]:
        f = "BUILD_COOP"

    fm, mm = A.farmer_mask(obs), A.market_mask(obs)
    fi, mi = _F_IDX[f], _M_IDX[m]
    if not fm[fi]:
        fi = _F_IDX["PASS"]
    if not mm[mi]:
        mi = _M_IDX["NOOP"]
    return fi, mi


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=2)
    ap.add_argument("--opponent", default="starter")
    ap.add_argument("--seed", type=int, default=5000)
    ap.add_argument("--trace", action="store_true")
    args = ap.parse_args()

    for ep in range(args.episodes):
        env = KGEnv(opponent=args.opponent, seat=ep % 2)
        raw = env.reset(seed=args.seed + ep)
        done = False
        step = 0
        while not done:
            fi, mi = scripted_action(raw)
            raw, done = env.step(A.decode(raw, fi, mi))
            step += 1
            if args.trace and step % 24 == 8:
                farm, priv, inv, _ = _me(raw)
                s = _scan(raw)
                animals = crops = 0
                for row in farm["tiles"]:
                    for t in row:
                        if isinstance(t, dict):
                            if "animal" in t:
                                animals += 1
                            elif t.get("kind") == "PLANT":
                                crops += 1
                shed_s = {k[:2]: v for k, v in priv["shed"].items() if v}
                print(f"  d{raw['day']:>2} ${farm['money']:>7,.0f} hands {len(farm.get('hands', [])):>2} "
                      f"land {len(farm['unlocked_quadrants'])} crops {crops:>2} animals {animals} "
                      f"empty {len(s['empty']):>2} seeds {sum(priv['seeds'].values()):>2} shed {shed_s}")
        mine, theirs = env.final_money()
        print(f"seed {args.seed + ep} seat {ep % 2}: me {mine:,.0f}  "
              f"opp({args.opponent}) {theirs:,.0f}  "
              f"{'WIN' if mine > theirs else 'LOSS'}")


if __name__ == "__main__":
    main()
