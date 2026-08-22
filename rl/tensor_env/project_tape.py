#!/usr/bin/env python
"""Can our action vocabulary even *express* what the top tier does?

Every generation so far asked "why does the policy not build like them".
Before answering that with more reward engineering, this measures the prior
question: replay a top tape in the tensor engine, and at each of the 719
steps ask whether ANY option in our vocabulary reproduces the action the
tape actually took, in the state the tape was actually in.

The tape's `_TRACE` entries and `actions._farmer_action` return the same
python action lists (["PLANT", "WHEAT"], ["MOVE_N"], ...), so the
comparison is exact -- no tensor plumbing and no approximate matching.

What the three numbers mean:

  farmer coverage   fraction of steps where some FARMER_ACTIONS option
                    produces the tape's exact farmer action. A miss is a
                    thing the policy cannot do at all, at any temperature.
  market coverage   our market head emits ONE option per turn; a tape turn
                    can carry up to 10 orders. Reported both ways: can one
                    option reproduce the whole order list, and can it
                    reproduce the first order.
  hands coverage    per hand-action, whether HAND_TASKS can express its op.

Also the point of it: the uncovered actions are printed with counts, so
the output is a work-list for the vocabulary, not just a score.

    python rl/tensor_env/project_tape.py [--steps N] [--seed S] [tape.py ...]

Ends PROJECT-DONE.
"""

import argparse
import collections
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_RL = os.path.dirname(_HERE)
_ROOT = os.path.dirname(_RL)
for p in (_HERE, _RL):
    if p not in sys.path:
        sys.path.insert(0, p)

import torch

import actions as A
import engine_t as ET
import engine_t_idx  # noqa: F401
import opponents_t
import tape_t
from verify_t import lane_obs

# HAND_TASKS carry an op each; AUTO/IDLE are scheduling, not ops.
_HAND_OPS = {
    "HARVEST": "HARVEST", "WATER": "WATER", "CARE": "CARE",
    "COLLECT_FERTILIZER": "COLLECT_FERTILIZER", "DIG": "DIG",
    "FEED": "FEED", "PLANT": "PLANT", "FERTILIZE": "FERTILIZE",
}
# a hand walking toward a chore is expressible: every chore task emits the
# same greedy step. Treat movement and PASS as covered by construction.
# The engine names moves by direction, not MOVE_*; getting this wrong made
# the first run report 51% hand coverage when the real figure is far higher.
_FREE = {"NORTH", "SOUTH", "EAST", "WEST", "PASS"}


def _norm(act):
    """A trace entry -> a comparable tuple ('PASS' for nothing)."""
    if not act:
        return ("PASS",)
    return tuple(act)


def _orders(lst):
    return tuple(tuple(o) for o in (lst or []) if o)


def project(agent_path, seed=424_242, steps=720, verbose=False):
    trace = tape_t.load_trace(agent_path)
    ep = ET.EpisodeT([seed], episode_steps=steps, device="cpu")
    opp = tape_t.TapeOpponent(agent_path)
    zero = torch.zeros((1, 2), dtype=torch.int64)

    f_hit = f_tot = 0
    f_miss = collections.Counter()
    f_used = collections.Counter()
    m_all = m_first = m_tot = 0
    m_orders = 0
    m_miss = collections.Counter()
    h_hit = h_tot = 0
    h_miss = collections.Counter()
    hands_seen = []

    while not ep.done and ep._step < len(trace):
        t = ep._step
        obs = lane_obs(ep, 0, 0)
        s = A._scan(obs)
        act = trace[t]

        # ---- farmer
        want = _norm(act.get("farmer"))
        f_tot += 1
        got = None
        for name in A.FARMER_ACTIONS:
            try:
                cand = A._farmer_action(obs, name, s)
            except Exception:
                cand = None
            if _norm(cand) == want:
                got = name
                break
        if got is not None:
            f_hit += 1
            f_used[got] += 1
        else:
            f_miss[want[0] if want else "PASS"] += 1

        # ---- market
        want_m = _orders(act.get("market"))
        m_tot += 1
        m_orders += len(want_m)
        hit_all = hit_first = False
        for name in A.MARKET_ACTIONS:
            try:
                cand = _orders(A._market_action(obs, name))
            except Exception:
                cand = ()
            if cand == want_m:
                hit_all = True
            if want_m and cand and cand[0] == want_m[0]:
                hit_first = True
            if hit_all:
                break
        if hit_all:
            m_all += 1
        if hit_first or not want_m:
            m_first += 1
        if want_m and not hit_first:
            m_miss[want_m[0][0]] += 1

        # ---- hands (vocabulary question only: can the op be named)
        hs = act.get("hands") or []
        hands_seen.append(len(hs))
        for ha in hs:
            h_tot += 1
            op = (ha[0] if ha else "PASS")
            if op in _FREE or op in _HAND_OPS:
                h_hit += 1
            else:
                h_miss[op] += 1

        fi, mi = opponents_t.starter_indices(ep, 1)
        f_idx = zero.clone()
        m_idx = zero.clone()
        f_idx[:, 1] = fi
        m_idx[:, 1] = mi
        ep.step_idx(f_idx, m_idx, override=[(0, opp(ep, 0))])

    return {
        "name": os.path.basename(agent_path),
        "money": float(ep.money[0, 0]),
        "steps": f_tot,
        "farmer_cov": f_hit / max(1, f_tot),
        "farmer_miss": f_miss,
        "farmer_used": f_used,
        "market_all": m_all / max(1, m_tot),
        "market_first": m_first / max(1, m_tot),
        "market_orders_per_turn": m_orders / max(1, m_tot),
        "market_miss": m_miss,
        "hands_cov": h_hit / max(1, h_tot),
        "hands_total": h_tot,
        "hands_miss": h_miss,
        "hands_per_turn": sum(hands_seen) / max(1, len(hands_seen)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tapes", nargs="*")
    ap.add_argument("--steps", type=int, default=720)
    ap.add_argument("--seed", type=int, default=424_242)
    a = ap.parse_args()
    tapes = a.tapes or [
        os.path.join(_ROOT, "agents", "bench3", "closer_cleo.py"),
        os.path.join(_ROOT, "agents", "bench3", "ledger_lena.py"),
        os.path.join(_ROOT, "agents", "bench3", "broker_bea.py"),
        os.path.join(_ROOT, "agents", "wrapped", "w49.py"),
        os.path.join(_ROOT, "agents", "champ", "k06.py"),
    ]
    rows = []
    for tp in tapes:
        if not os.path.exists(tp):
            print(f"  (missing {tp})")
            continue
        r = project(tp, seed=a.seed, steps=a.steps)
        rows.append(r)
        print(f"\n=== {r['name']}  ({r['steps']} steps, replay money "
              f"{r['money']:,.0f})")
        print(f"  farmer : {r['farmer_cov']*100:5.1f}% of steps reproducible "
              f"by some FARMER_ACTIONS option")
        if r["farmer_miss"]:
            top = ", ".join(f"{k} x{v}" for k, v in
                            r["farmer_miss"].most_common(8))
            print(f"           uncovered: {top}")
        print(f"  market : {r['market_all']*100:5.1f}% whole-list, "
              f"{r['market_first']*100:5.1f}% first-order; the tape issues "
              f"{r['market_orders_per_turn']:.2f} orders/turn")
        if r["market_miss"]:
            top = ", ".join(f"{k} x{v}" for k, v in
                            r["market_miss"].most_common(8))
            print(f"           uncovered first-orders: {top}")
        print(f"  hands  : {r['hands_cov']*100:5.1f}% of {r['hands_total']:,} "
              f"hand-actions nameable in HAND_TASKS "
              f"({r['hands_per_turn']:.2f} hands/turn)")
        if r["hands_miss"]:
            top = ", ".join(f"{k} x{v}" for k, v in
                            r["hands_miss"].most_common(8))
            print(f"           uncovered: {top}")
        busy = ", ".join(f"{k} {v}" for k, v in r["farmer_used"].most_common(6))
        print(f"  the tape's farmer, in our option names: {busy}")

    if len(rows) > 1:
        print("\n=== summary")
        print(f"{'tape':<20}{'farmer':>9}{'mkt-all':>9}{'mkt-1st':>9}"
              f"{'ord/turn':>10}{'hands':>8}{'hand/turn':>11}")
        for r in rows:
            print(f"{r['name']:<20}{r['farmer_cov']*100:>8.1f}%"
                  f"{r['market_all']*100:>8.1f}%{r['market_first']*100:>8.1f}%"
                  f"{r['market_orders_per_turn']:>10.2f}"
                  f"{r['hands_cov']*100:>7.1f}%{r['hands_per_turn']:>11.2f}")
    print("PROJECT-DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
