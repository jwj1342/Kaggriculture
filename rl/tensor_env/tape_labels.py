#!/usr/bin/env python
"""Top-tier tapes as a *teacher*, and the one measurement that says whether
our action vocabulary can reach the top tier at all.

Every generation of this project has trained against the 150k tapes as
opponents. None has ever imitated them. The kickstart teacher we do have is
`barnyard` -- a scripted agent that earns about 40k -- which is the wrong
teacher for a 2000-point target. AlphaStar, VPT and OpenAI Five all start
from supervised imitation of expert data and only then run RL; we have seven
expert trajectories sitting in `agents/bench3/` and `agents/wrapped/`.

Why the labels need no state. A tape is open loop: its action at step t is
the same on every lane. So the teacher is a per-step lookup table, exactly
like `tape_t`'s override tables -- O(T) to build, free to use.

Intent lookahead. Roughly 40% of a tape's farmer actions are single walking
steps toward a target. Our options are goto-and-do macros, so the correct
label during a walk is the action the walk is *for*: the next terminal
(non-move) op in the trace. Labelling the walk itself would teach the policy
to emit MOVE_N, which our vocabulary treats as a bare step and which throws
away the macro.

    python rl/tensor_env/tape_labels.py            # coverage + the drive test

THE DRIVE TEST feeds the labels through *our own* decode and reports the
money. READ IT NARROWLY -- it is not a verdict on the vocabulary, and the
first version of this docstring said it was. Two confounds, both measured
(docs/RUNS.md 2026-08-22):

  * our BUY_* options carry their own quantities (HIRE takes a burst of 10,
    BUY_WHEAT scales with the herd), so replaying a tape's 275 small wheat
    orders as 275 of our bulk options buys the farm into bankruptcy;
  * the market head has one slot per turn against the tape's 1.05-1.64
    orders, so queueing the remainder backs up (peak 127) and starves the
    build orders behind a wall of stale sells.

Our own trained policies earn 40-65k through these same options, so a drive
ratio of 0.7% is a statement about this labelling scheme, not about the
action space. What the arms DO establish is narrower and real: the tape's
division of labour is inexpressible here -- it places animals and builds
pastures with its HANDS, and HAND_TASKS has neither, so arm B reaches day 29
with zero animals while the tape has fourteen.

Ends LABELS-PASS / LABELS-FAIL.
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

_MOVES = {"NORTH", "SOUTH", "EAST", "WEST"}

# trace op -> FARMER_ACTIONS name (None: not expressible)
_F_OP = {
    "PASS": "PASS", "WATER": "WATER", "HARVEST": "HARVEST", "FEED": "FEED",
    "CARE": "CARE", "COLLECT_FERTILIZER": "COLLECT_FERT",
    "FERTILIZE": "FERTILIZE", "DIG": "DIG_WEED", "BUILD_COOP": "BUILD_COOP",
    "BUILD_PASTURE": "BUILD_PASTURE", "DROP": "DROP",
}
# trace op -> HAND_TASKS name
_H_OP = {
    "HARVEST": "HARVEST", "WATER": "WATER", "CARE": "CARE",
    "COLLECT_FERTILIZER": "COLLECT_FERTILIZER", "DIG": "DIG", "FEED": "FEED",
    "PLANT": "PLANT", "FERTILIZE": "FERTILIZE", "PASS": "IDLE",
}

MAX_LOOKAHEAD = 40


def _f_label(act):
    """One trace farmer entry -> FARMER_ACTIONS index, or -1."""
    if not act:
        return A.FARMER_ACTIONS.index("PASS")
    op = act[0]
    if op == "PLANT" and len(act) > 1:
        name = f"PLANT_{act[1]}"
    elif op == "PLACE" and len(act) > 1 and act[1] in A.ANIMAL_LIST:
        name = f"PLACE_{act[1]}"
    else:
        name = _F_OP.get(op)
    if name is None or name not in A.FARMER_ACTIONS:
        return -1
    return A.FARMER_ACTIONS.index(name)


def _h_label(act):
    if not act:
        return A.HAND_TASKS.index("IDLE")
    name = _H_OP.get(act[0])
    if name is None or name not in A.HAND_TASKS:
        return -1
    return A.HAND_TASKS.index(name)


def _m_name(o):
    """One trace order -> a MARKET_ACTIONS name, or None if inexpressible."""
    op = o[0]
    if op == "SELL" and len(o) > 1:
        return f"SELL_{o[1]}"
    if op == "BUY_SEED" and len(o) > 1:
        return f"BUY_SEED_{o[1]}"
    if op == "BUY_PRODUCT" and len(o) > 1:
        return {"WHEAT": "BUY_WHEAT", "FERTILIZER": "BUY_FERT"}.get(o[1])
    if op == "BUY_ANIMAL" and len(o) > 1:
        return f"BUY_{o[1]}"
    if op == "BUY_LAND":
        return "BUY_LAND"
    if op == "HIRE":
        return "HIRE"
    return None


# The market head emits ONE option per turn; a tape turn can carry up to
# ten orders. Dropping the losers is fatal, not lossy: the first version of
# this file ranked HIRE above BUY_SEED, so the one turn where cleo buys its
# seeds alongside a hire lost the seeds -- and the tape never repeats an
# order, so the farm reached day 30 with zero seeds and every PLANT label
# decoded to a no-op. The tape is idle in 60-70% of turns, so the orders
# fit if they are QUEUED into the gaps instead.
_M_RANK = {"BUY_SEED": 0, "BUY_ANIMAL": 1, "BUY_LAND": 2, "HIRE": 3,
           "BUY_PRODUCT": 4, "SELL": 5}
QUEUE_STALE = 48          # two days; an order older than this is dropped


def build_labels(agent_path, n_hands=A.MAX_HANDS):
    """-> dict with f (T,), m (T,), h (T, n_hands) int64 label tables."""
    trace = tape_t.load_trace(agent_path)
    T = len(trace)
    f = torch.full((T,), -1, dtype=torch.int64)
    m = torch.full((T,), -1, dtype=torch.int64)
    h = torch.full((T, n_hands), -1, dtype=torch.int64)
    stats = collections.Counter()
    queue = collections.deque()

    def intent(get, t):
        """The next terminal (non-move) entry for this unit at or after t."""
        for k in range(t, min(T, t + MAX_LOOKAHEAD)):
            a = get(k)
            if a and a[0] in _MOVES:
                continue
            return a
        return None

    for t in range(T):
        act = trace[t]
        fa = act.get("farmer")
        if fa and fa[0] in _MOVES:
            fa = intent(lambda k: trace[k].get("farmer"), t)
            stats["farmer_walk"] += 1
        f[t] = _f_label(fa)
        stats["farmer_covered" if f[t] >= 0 else "farmer_uncovered"] += 1

        # market: push this turn's orders onto the queue (build-critical
        # first), drop anything stale, then spend the single slot on the head
        for o in sorted((o for o in (act.get("market") or []) if o),
                        key=lambda o: _M_RANK.get(o[0], 9)):
            stats["market_orders"] += 1
            name = _m_name(o)
            if name and name in A.MARKET_ACTIONS:
                queue.append((t, A.MARKET_ACTIONS.index(name)))
                stats["market_covered"] += 1
            else:
                stats["market_uncovered"] += 1
        while queue and t - queue[0][0] > QUEUE_STALE:
            queue.popleft()
            stats["market_stale"] += 1
        if queue:
            m[t] = queue.popleft()[1]
            stats["market_emitted"] += 1
        else:
            m[t] = A.MARKET_ACTIONS.index("NOOP")
        stats["market_backlog_peak"] = max(stats["market_backlog_peak"],
                                           len(queue))

        hs = act.get("hands") or []
        for u in range(min(n_hands, len(hs))):
            ha = hs[u]
            if ha and ha[0] in _MOVES:
                ha = intent(
                    lambda k, u=u: (trace[k].get("hands") or [None] * (u + 1))
                    [u] if len(trace[k].get("hands") or []) > u else None, t)
                stats["hand_walk"] += 1
            h[t, u] = _h_label(ha)
            stats["hand_covered" if h[t, u] >= 0 else "hand_uncovered"] += 1
    return {"f": f, "m": m, "h": h, "T": T, "stats": stats,
            "name": os.path.basename(agent_path)}


class TapeTeacher:
    """Per-step label provider in head-index vocabulary (open loop)."""

    def __init__(self, agent_path, device="cpu", n_hands=A.MAX_HANDS):
        lab = build_labels(agent_path, n_hands)
        self.f = lab["f"].to(device)
        self.m = lab["m"].to(device)
        self.h = lab["h"].to(device)
        self.T = lab["T"]
        self.name = lab["name"]
        self.stats = lab["stats"]

    def labels(self, ep, player=None):
        """(B,), (B,), (B, n_hands) -- the same row broadcast to every lane."""
        t = min(ep._step, self.T - 1)
        B = ep.B
        return (self.f[t].expand(B).clone(), self.m[t].expand(B).clone(),
                self.h[t].unsqueeze(0).expand(B, -1).clone())


def drive(agent_path, seed=424_242, steps=720, opponent="starter",
          verbose=False):
    """Execute the labels through OUR decode. Returns (money, tape_money)."""
    teach = TapeTeacher(agent_path)
    tape = tape_t.TapeOpponent(agent_path)

    # arm A: our own action layer driven by the labels
    ep = ET.EpisodeT([seed], episode_steps=steps, device="cpu")
    zero = torch.zeros((1, 2), dtype=torch.int64)
    while not ep.done:
        fl, ml, hl = teach.labels(ep)
        f_idx = zero.clone()
        m_idx = zero.clone()
        h_idx = torch.zeros((1, 2, A.MAX_HANDS), dtype=torch.int64)
        # -1 means "no label": fall back to PASS / NOOP / AUTO so the turn
        # is still legal. AUTO is the honest fallback for a hand -- it is
        # what the policy itself would emit with no opinion.
        f_idx[:, 0] = torch.where(fl >= 0, fl, torch.zeros_like(fl))
        m_idx[:, 0] = torch.where(ml >= 0, ml, torch.zeros_like(ml))
        h_idx[:, 0] = torch.where(hl >= 0, hl, torch.zeros_like(hl))
        oi, omi = opponents_t.starter_indices(ep, 1)
        f_idx[:, 1] = oi
        m_idx[:, 1] = omi
        ep.step_idx(f_idx, m_idx, h_idx=h_idx)
    ours = float(ep.money[0, 0])

    # arm B: the tape itself, same seed, same opponent
    ep2 = ET.EpisodeT([seed], episode_steps=steps, device="cpu")
    while not ep2.done:
        oi, omi = opponents_t.starter_indices(ep2, 1)
        f_idx = zero.clone()
        m_idx = zero.clone()
        f_idx[:, 1] = oi
        m_idx[:, 1] = omi
        ep2.step_idx(f_idx, m_idx, override=[(0, tape(ep2, 0))])
    theirs = float(ep2.money[0, 0])
    return ours, theirs


def ablate(agent_path, seed=424_242, steps=720):
    """Which HALF of our action space is the ceiling?

    Four arms on one seed, identical opponent (the scripted starter):
      A  everything ours     : macro decode driven by the tape's intent
      B  tape market only    : our farmer+hands, the tape's raw orders
      C  tape farm only      : the tape's farmer+hands, our market option
      D  everything the tape : the reference number

    The point of B and C is that arm A alone cannot say *where* it lost the
    money. If B recovers most of D, the single-order-per-turn market head is
    the ceiling; if C does, the farm side is.
    """
    teach = TapeTeacher(agent_path)
    tape = tape_t.TapeOpponent(agent_path)
    out = {}
    for arm in ("A", "B", "C", "D"):
        ep = ET.EpisodeT([seed], episode_steps=steps, device="cpu")
        zero = torch.zeros((1, 2), dtype=torch.int64)
        while not ep.done:
            fl, ml, hl = teach.labels(ep)
            f_idx = zero.clone()
            m_idx = zero.clone()
            h_idx = torch.zeros((1, 2, A.MAX_HANDS), dtype=torch.int64)
            f_idx[:, 0] = torch.where(fl >= 0, fl, torch.zeros_like(fl))
            m_idx[:, 0] = torch.where(ml >= 0, ml, torch.zeros_like(ml))
            h_idx[:, 0] = torch.where(hl >= 0, hl, torch.zeros_like(hl))
            oi, omi = opponents_t.starter_indices(ep, 1)
            f_idx[:, 1] = oi
            m_idx[:, 1] = omi
            ov = None
            if arm != "A":
                raw = tape(ep, 0)
                keep = {"B": ("m_op", "m_item", "m_rem"),
                        "C": ("f_op", "f_arg", "f_qty", "h_op", "h_arg",
                              "h_qty"),
                        "D": tuple(raw)}[arm]
                ov = [(0, {k: raw[k] for k in keep})]
            ep.step_idx(f_idx, m_idx, override=ov, h_idx=h_idx)
        out[arm] = float(ep.money[0, 0])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ablate", action="store_true",
                    help="run the four-arm A/B/C/D localisation instead")
    ap.add_argument("tapes", nargs="*")
    ap.add_argument("--seed", type=int, default=424_242)
    ap.add_argument("--steps", type=int, default=720)
    a = ap.parse_args()
    tapes = a.tapes or [
        os.path.join(_ROOT, "agents", "bench3", "closer_cleo.py"),
        os.path.join(_ROOT, "agents", "bench3", "ledger_lena.py"),
        os.path.join(_ROOT, "agents", "bench3", "broker_bea.py"),
        os.path.join(_ROOT, "agents", "wrapped", "w49.py"),
        os.path.join(_ROOT, "agents", "champ", "k06.py"),
    ]
    if a.ablate:
        print(f"{'tape':<20}{'A ours':>11}{'B +tape mkt':>13}"
              f"{'C +tape farm':>14}{'D all tape':>12}"
              f"{'   B/D':>8}{'   C/D':>8}")
        for tp in tapes:
            if not os.path.exists(tp):
                continue
            r = ablate(tp, seed=a.seed, steps=a.steps)
            d = r["D"] or 1.0
            print(f"{os.path.basename(tp):<20}{r['A']:>11,.0f}{r['B']:>13,.0f}"
                  f"{r['C']:>14,.0f}{r['D']:>12,.0f}"
                  f"{r['B']/d*100:>7.1f}%{r['C']/d*100:>7.1f}%")
        print("LABELS-PASS")
        return 0

    rows = []
    ok = True
    for tp in tapes:
        if not os.path.exists(tp):
            print(f"  (missing {tp})")
            continue
        lab = build_labels(tp)
        st = lab["stats"]
        fc = st["farmer_covered"] / max(1, lab["T"])
        hc = st["hand_covered"] / max(1, st["hand_covered"]
                                     + st["hand_uncovered"])
        mc = st["market_covered"] / max(1, st["market_orders"])
        ours, theirs = drive(tp, seed=a.seed, steps=a.steps)
        ratio = ours / theirs if theirs else 0.0
        rows.append((lab["name"], fc, mc, hc, ours, theirs, ratio))
        print(f"\n=== {lab['name']}")
        print(f"  labels : farmer {fc*100:5.1f}% covered  market "
              f"{mc*100:5.1f}% of {st['market_orders']} orders  hands "
              f"{hc*100:5.1f}%   (walks relabelled: farmer "
              f"{st['farmer_walk']}, hand {st['hand_walk']}; market queue "
              f"emitted {st['market_emitted']}, peak backlog "
              f"{st['market_backlog_peak']}, dropped stale "
              f"{st['market_stale']})")
        print(f"  DRIVE  : our decode on the tape's intent earns "
              f"{ours:,.0f}; the tape itself earns {theirs:,.0f}  "
              f"-> {ratio*100:.1f}%")

    if rows:
        print("\n=== summary (the DRIVE ratio is the vocabulary verdict)")
        print(f"{'tape':<20}{'farmer':>8}{'market':>8}{'hands':>8}"
              f"{'drive $':>12}{'tape $':>12}{'ratio':>8}")
        for n, fc, mc, hc, o, t2, r in rows:
            print(f"{n:<20}{fc*100:>7.1f}%{mc*100:>7.1f}%{hc*100:>7.1f}%"
                  f"{o:>12,.0f}{t2:>12,.0f}{r*100:>7.1f}%")
        best = max(r[6] for r in rows)
        print(f"\n  best drive ratio {best*100:.1f}%")
        if best < 0.30:
            print("  READING: the vocabulary/action layer is the ceiling. "
                  "Reward and compute cannot cross it.")
        elif best < 0.70:
            print("  READING: partially expressible -- BC is worth doing, but "
                  "the uncovered ops above are a real cap.")
        else:
            print("  READING: the vocabulary is sufficient. The gap is "
                  "learning, so imitation-then-RL is the right investment.")
    print("LABELS-PASS" if ok else "LABELS-FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
