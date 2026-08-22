#!/usr/bin/env python
"""Is the potential a good proxy for final money, ON STATES THE ENGINE MADE?

The hand-staged tables I built earlier were invalid twice over: they put crops
on LOCKED tiles, and setting quad_unlocked does not unlock them. This probe
never builds a state -- it replays five real tapes in the tensor engine and
reads phi off the states they actually reach, then asks whether phi's ORDERING
of those five trajectories matches their final money.

That is the load-bearing question for the grocer arm. If base-price phi already
ranks the tapes the way money does, re-pricing phi is not the lever. If it
ranks them backwards and transaction prices + the manure stream fix the order,
the arm is founded.

Seat 1 is a fixed deterministic macro policy (lowest legal index) for every
run, so it is a control, not a realistic opponent -- market prices will be
softer than in a real match. The comparison across tapes is what is being
read, not the absolute level.

    python tools/phi_vs_money.py
"""

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (f"{_ROOT}/rl/tensor_env", f"{_ROOT}/rl", f"{_ROOT}/agents"):
    sys.path.insert(0, p)

import torch

import engine_t as ET
import engine_t_idx  # noqa: F401
import features_t
import potential_future as PF
import tape_t

ROOT = _ROOT
TAPES = [
    ("k06", f"{ROOT}/agents/champ/k06.py"),
    ("cleo", f"{ROOT}/agents/bench3/closer_cleo.py"),
    ("lena", f"{ROOT}/agents/bench3/ledger_lena.py"),
    ("bea", f"{ROOT}/agents/bench3/broker_bea.py"),
    ("w49", f"{ROOT}/agents/wrapped/w49.py"),
    # a genuinely WEAK farm, so the money range spans more than the 13% the
    # five tapes cover. This is the ranking phi must get right: strong over
    # weak. None means no override -- seat 0 plays the same lowest-legal-index
    # control as seat 1.
    ("ctrl", None),
]
DAYS = (4, 8, 12, 16, 20, 25)
SEEDS = [424_242, 909_090, 5_150]


def _first_legal(ep):
    fi, mi = [], []
    for p in range(2):
        fm, mm = features_t.masks_t(ep, p)
        fi.append(torch.argmax(fm.long(), dim=-1))
        mi.append(torch.argmax(mm.long(), dim=-1))
    return torch.stack(fi, 1), torch.stack(mi, 1)


def _has_tx():
    """the price dial only exists in trees that carry it (gen31)."""
    import inspect
    return "tx_price" in inspect.signature(PF.future_worth_t).parameters


HAS_TX = _has_tx()


def run(path, seed):
    ep = ET.EpisodeT([seed], episode_steps=720, device="cpu")
    opp = tape_t.TapeOpponent(path) if path else None
    phi_base, phi_tx = {}, {}
    while not ep.done:
        d = int(ep._step // ep.turns_per_day)
        if d in DAYS and d not in phi_base:
            phi_base[d] = float(PF.future_worth_t(
                ep, 0, shed_at_market=True)[0])
            phi_tx[d] = (float(PF.future_worth_t(
                ep, 0, shed_at_market=True, tx_price=1.0)[0])
                if HAS_TX else phi_base[d])
        fi, mi = _first_legal(ep)
        if opp is None:
            ep.step_idx(fi, mi)
        else:
            ep.step_idx(fi, mi, override=(0, opp(ep, 0)))
    return float(ep.money[0, 0]), phi_base, phi_tx


def spearman(xs, ys):
    """rank correlation over a handful of points, ties broken by order."""
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0] * len(v)
        for pos, i in enumerate(order):
            r[i] = pos
        return r
    rx, ry = ranks(xs), ranks(ys)
    n = len(xs)
    d2 = sum((a - b) ** 2 for a, b in zip(rx, ry))
    return 1.0 - 6.0 * d2 / (n * (n * n - 1))


def main():
    for seed in SEEDS:
        print(f"\n=== seed {seed} "
              f"(seat 1 = lowest-legal-index control) ===")
        money, pb, pt = {}, {}, {}
        for name, path in TAPES:
            if path is not None and not os.path.exists(path):
                print(f"  (missing {path})")
                continue
            m, b, t = run(path, seed)
            money[name], pb[name], pt[name] = m, b, t
        names = list(money)
        names.sort(key=lambda n: -money[n])
        hdr = "".join(f"{'d'+str(d):>9}" for d in DAYS)
        print(f"  {'tape':<7}{'money':>10}   base phi{hdr[8:]}")
        for n in names:
            row = "".join(f"{pb[n][d]:>9,.0f}" for d in DAYS if d in pb[n])
            print(f"  {n:<7}{money[n]:>10,.0f}   {row}")
        if not HAS_TX:
            print("  (this tree has no --tx-price dial; the tx columns below "
                  "repeat the base ones)")
        print(f"  {'':<7}{'':>10}   tx phi")
        for n in names:
            row = "".join(f"{pt[n][d]:>9,.0f}" for d in DAYS if d in pt[n])
            print(f"  {n:<7}{money[n]:>10,.0f}   {row}")
        ms = [money[n] for n in names]
        print(f"  {'day':<7}{'rho base':>10}{'rho tx+manure':>16}")
        for d in DAYS:
            if not all(d in pb[n] for n in names):
                continue
            rb = spearman(ms, [pb[n][d] for n in names])
            rt = spearman(ms, [pt[n][d] for n in names])
            print(f"  {d:<7}{rb:>+10.2f}{rt:>+16.2f}")
    print("\nPHI-MONEY-DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
