#!/usr/bin/env python
"""What does our net actually ORDER, next to what the tier orders?

The tape counts in this session were read off `_TRACE` entries, i.e. ORDERED
quantities. The framework records each player's submitted action in
env.steps[i][p].action, so the same unit is available for any agent file --
no digest field, no reconstruction. Reading the digest `sold` column as
executed volume was an error earlier today; this avoids the question by
counting orders on both sides.

The number this exists to check: k06 orders 1,671 FERTILIZER, its largest
single line, more than its 1,060 WHEAT. Every tape sells fertilizer (208-445).
COLLECT_FERTILIZER is in HAND_TASKS and SELL_FERTILIZER is in MARKET_ACTIONS,
so the vocabulary can do it. Does the net?

    python tools/order_mix.py <agent.py> [opponent] [--seeds N]

Set KG_FAST_ENV=1 (verified-identical 17% faster) and OMP_NUM_THREADS=1.
"""

import argparse
import collections
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_one(agent, opp, seed, steps=720):
    from kaggle_environments import make
    env = make("kaggriculture",
               configuration={"episodeSteps": steps, "seed": seed},
               debug=False)
    env.run([agent, opp])
    mkt = collections.Counter()
    hands = collections.Counter()
    farmer = collections.Counter()
    sell_qty = collections.Counter()
    buy_qty = collections.Counter()
    for st in env.steps:
        act = st[0].action
        if not isinstance(act, dict):
            continue
        f = act.get("farmer")
        if f:
            farmer[f[0]] += 1
        for h in (act.get("hands") or []):
            if h:
                hands[h[0]] += 1
        for o in (act.get("market") or []):
            if not o:
                continue
            mkt[o[0]] += 1
            if o[0] == "SELL" and len(o) > 2:
                sell_qty[o[1]] += o[2]
            elif o[0].startswith("BUY") and len(o) > 2:
                buy_qty[f"{o[0][4:]}:{o[1]}"] += o[2]
    money = env.steps[-1][0].observation["farms"][0]["money"]
    return money, mkt, hands, farmer, sell_qty, buy_qty


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("agent")
    ap.add_argument("opponent", nargs="?",
                    default=f"{ROOT}/agents/bench3/closer_cleo.py")
    ap.add_argument("--seeds", type=int, default=3)
    a = ap.parse_args()

    tot_s, tot_b, tot_h, tot_f = (collections.Counter() for _ in range(4))
    monies = []
    for i in range(a.seeds):
        seed = 10_000 + 977 * i
        m, mkt, hands, farmer, sq, bq = run_one(a.agent, a.opponent, seed)
        monies.append(m)
        tot_s.update(sq)
        tot_b.update(bq)
        tot_h.update(hands)
        tot_f.update(farmer)
        print(f"  seed {seed}: money {m:,.0f}")
    n = max(1, a.seeds)
    print(f"\n{os.path.basename(os.path.dirname(a.agent)) or a.agent} "
          f"vs {os.path.basename(a.opponent)}, "
          f"{a.seeds} seeds, mean money {sum(monies)/n:,.0f}")
    print(f"  sold (orders, per episode): "
          f"{ {k: round(v/n) for k, v in tot_s.most_common(9)} }")
    print(f"  bought (orders, per ep)   : "
          f"{ {k: round(v/n) for k, v in tot_b.most_common(9)} }")
    print(f"  hand ops (per ep)         : "
          f"{ {k: round(v/n) for k, v in tot_h.most_common(14)} }")
    for key in ("WATER", "PLANT", "FERTILIZE", "HARVEST",
                "COLLECT_FERTILIZER", "FEED"):
        print(f"      {key:<20}{tot_h[key]/n:>8.0f}")
    print(f"  farmer ops (per ep)       : "
          f"{ {k: round(v/n) for k, v in tot_f.most_common(6)} }")
    print("ORDER-MIX-DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
