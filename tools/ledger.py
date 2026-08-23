#!/usr/bin/env python
"""Receipts against outlays, per farm, from the money series itself.

Why this exists (docs/RUNS.md 2026-08-23). Every diagnosis this project has made
about the money gap has been a REVENUE diagnosis -- the demand ledger, the pool
capture rates, "our deficit is output not selection". Measuring the two sides
separately says otherwise: against k06 our net's receipts are within 21% but its
outlays are 79% higher, so most of the gap is spending, not earning.

That was not visible from any earlier tool because they all read the ACTION
stream, and it cannot be read from there:

  - Order quantities are not executions. Illegal actions are silent no-ops, so an
    agent that submits SELL FERTILIZER x40 every turn with an empty shed shows up
    in the action stream as a huge seller. k06 "sold" 1,671 fertiliser by order
    count while the market inventory rose only 316 across BOTH farms. Pricing the
    order stream credited it 100,777 of fertiliser revenue that never happened,
    which is the criterion (h) trap in its most expensive form.
  - The market inventory is SHARED, so even executed volume cannot be split
    between the farms from the inventory series alone.

Money can be read, and it is per-farm. So: walk the money series, sum the
positive deltas as receipts and the negative as outlays, and bucket each outlay
by what the agent submitted on that turn. The buckets are approximate at the
margin -- a turn that both hires and buys feed lands in one bucket -- but the
receipts/outlays split itself is exact, and it is the split that carries the
finding.

    python tools/ledger.py <agent.py> [--opp agents/champ/k06.py] [--seeds 4]

Prints per-farm receipts, outlays, the outlay buckets, and the seed mix, since
the seed mix is what explains the feed bill: an animal eats 1 WHEAT a day from
its OWN shed (engine `_inv_take(inv, "WHEAT", 1)` under op == "FEED"), so a farm
that plants no wheat buys its feed at a market price that both farms are pushing
up all game.
"""

import argparse
import collections
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def one(agent, opp, seed, steps=720):
    from kaggle_environments import make
    env = make("kaggriculture",
               configuration={"episodeSteps": steps, "seed": seed}, debug=False)
    env.run([agent, opp])
    out = {}
    for p in (0, 1):
        rec = pay = 0.0
        buckets = collections.Counter()
        seeds = collections.Counter()
        prev = env.steps[0][p].observation["farms"][p]["money"]
        for st in env.steps[1:]:
            f = st[p].observation["farms"][p]
            dm = f["money"] - prev
            prev = f["money"]
            a = st[p].action
            orders = ([o for o in ((a or {}).get("market") or []) if o]
                      if isinstance(a, dict) else [])
            for o in orders:
                if o[0] == "BUY_SEED" and len(o) > 2:
                    seeds[o[1]] += o[2]
            if dm > 0:
                rec += dm
                continue
            pay += -dm
            kinds = {o[0] for o in orders}
            if not orders:
                buckets["standing (wages/upkeep)"] += -dm
            elif "BUY_PRODUCT" in kinds:
                buckets["buying product (feed)"] += -dm
            elif "HIRE" in kinds:
                buckets["hiring"] += -dm
            elif kinds <= {"SELL"}:
                buckets["sell-only turns"] += -dm
            else:
                buckets["seed / animal / land"] += -dm
        out[p] = {"rec": rec, "pay": pay, "final": prev,
                  "buckets": buckets, "seeds": seeds}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("agent")
    ap.add_argument("--opp", default=f"{ROOT}/agents/champ/k06.py")
    ap.add_argument("--seeds", type=int, default=4)
    a = ap.parse_args()

    acc = {p: {"rec": 0.0, "pay": 0.0, "final": 0.0,
               "buckets": collections.Counter(), "seeds": collections.Counter()}
           for p in (0, 1)}
    for i in range(a.seeds):
        r = one(a.agent, a.opp, 10_000 + 977 * i)
        for p in (0, 1):
            for k in ("rec", "pay", "final"):
                acc[p][k] += r[p][k] / a.seeds
            for k, v in r[p]["buckets"].items():
                acc[p]["buckets"][k] += v / a.seeds
            for k, v in r[p]["seeds"].items():
                acc[p]["seeds"][k] += v / a.seeds

    names = (os.path.basename(os.path.dirname(a.agent)) or a.agent,
             os.path.basename(a.opp))
    print(f"\n  {a.seeds} seeds, {names[0]} against {names[1]}\n")
    for p in (0, 1):
        d = acc[p]
        print(f"  == {names[p]}")
        print(f"     receipts {d['rec']:>10,.0f}   outlays {d['pay']:>10,.0f}"
              f"   final {d['final']:>9,.0f}")
        for k, v in d["buckets"].most_common():
            print(f"       {k:<28}{v:>10,.0f}{v / max(d['pay'], 1) * 100:>7.1f}%")
        mix = "  ".join(f"{k} {v:.0f}" for k, v in d["seeds"].most_common())
        print(f"     seed mix: {mix or '(none)'}")
    g = acc[1]["final"] - acc[0]["final"]
    dr = acc[1]["rec"] - acc[0]["rec"]
    dp = acc[0]["pay"] - acc[1]["pay"]
    print(f"\n  gap {g:>+10,.0f}   of which receipts {dr:>+9,.0f}"
          f"  outlays {dp:>+9,.0f}  ({dp / max(abs(g), 1) * 100:.0f}% is spending)")
    print("LEDGER-DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
