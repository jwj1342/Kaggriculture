#!/usr/bin/env python
"""Behaviour-clone a *stronger* teacher: barnyard drives our seat as an
oracle, its raw actions execute verbatim (authentic trajectories), and each
step is reverse-mapped to the nearest macro intent as a training label.

    python rl/collect_bc_barn.py --episodes 8 --coverage-only   # gate first
    python rl/collect_bc_barn.py --episodes 200 --jobs 28

Gate (README §8, TODO #5): if fewer than --min-coverage of farmer steps map
exactly onto a macro decode, this route is dead -- measure before building.

Labels: farmer head = the legal macro whose decode reproduces barnyard's
farmer action exactly (PASS rows are kept but downweighted at train time);
market head = the macro whose emitted orders share op+item with barnyard's
first order (barnyard fires up to 10 orders; ours emit compounds), else NOOP.
"""

import argparse
import os
import sys
from multiprocessing import Pool

import numpy as np

_RL = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_RL)
sys.path.insert(0, _RL)

OPPONENTS = [("starter", 0.3),
             (os.path.join(_REPO, "agents", "ghosts", "ghost-89825016-0.py"), 0.3),
             (os.path.join(_REPO, "agents", "enhanced", "main.py"), 0.4)]


def _load_oracle():
    from export_agent import get_last_callable
    return get_last_callable(os.path.join(_REPO, "agents", "barnyard.py"))


def _map_step(obs, raw, A):
    """(farmer_label, farmer_exact, market_label, market_matched)."""
    fmask, mmask = A.farmer_mask(obs), A.market_mask(obs)
    rawf = raw.get("farmer", ["PASS"])
    f_label, f_exact = A._F_IDX["PASS"], False
    for fi in np.flatnonzero(fmask):
        if A._farmer_action(obs, A.FARMER_ACTIONS[fi], A._scan(obs)) == rawf:
            f_label, f_exact = int(fi), True
            break
    m_label, m_match = A._M_IDX["NOOP"], False
    orders = [o for o in (raw.get("market") or [])
              if isinstance(o, list) and o]
    # Teacher combos bury their SELL orders behind hires/buys; matching only
    # the first order labelled every selling turn NOOP and produced a clone
    # that spends to $0 and never sells. Prefer any SELL in the combo, then
    # fall back to first-order matching.
    target = next((o for o in orders if o[0] == "SELL"), orders[0] if orders else None)
    if target is not None:
        for mi in np.flatnonzero(mmask):
            ours = A._market_action(obs, A.MARKET_ACTIONS[mi])
            if ours and ours[0][0] == target[0] \
                    and (len(target) < 2 or len(ours[0]) < 2 or ours[0][1] == target[1]):
                m_label, m_match = int(mi), True
                break
    return f_label, f_exact, m_label, m_match


def _run_chunk(job):
    wid, n_eps, out_dir, coverage_only = job
    import actions as A
    import obs as O
    from kg_env import KGEnv

    oracle = _load_oracle()
    rng = np.random.default_rng(4321 + wid * 7919)
    names, weights = zip(*OPPONENTS)
    p = np.asarray(weights) / sum(weights)
    xs, fms, mms, fas, mas, fexs = [], [], [], [], [], []
    n_steps = n_fex = n_mm = 0
    finals = []
    for _ in range(n_eps):
        opp = names[int(rng.choice(len(names), p=p))]
        env = KGEnv(opponent=opp, seat=int(rng.integers(0, 2)))
        raw_obs = env.reset(seed=int(rng.integers(0, 10_000)))
        done = False
        while not done:
            try:
                act = oracle(raw_obs)
            except TypeError:
                act = oracle(raw_obs, None)
            if not isinstance(act, dict):
                act = {"farmer": ["PASS"], "hands": [], "market": []}
            f, fex, m, mmatch = _map_step(raw_obs, act, A)
            n_steps += 1
            n_fex += fex
            n_mm += mmatch
            if not coverage_only:
                xs.append(O.encode(raw_obs).astype(np.float16))
                fms.append(A.farmer_mask(raw_obs))
                mms.append(A.market_mask(raw_obs))
                fas.append(f)
                mas.append(m)
                fexs.append(fex)
            raw_obs, done = env.step(act)
        finals.append(env.final_money()[0])
    if not coverage_only:
        np.savez_compressed(
            os.path.join(out_dir, f"barn-{wid:02d}.npz"),
            obs=np.stack(xs), fmask=np.stack(fms), mmask=np.stack(mms),
            fa=np.asarray(fas, dtype=np.int16), ma=np.asarray(mas, dtype=np.int16),
            fex=np.asarray(fexs, dtype=bool))
    return wid, n_steps, n_fex, n_mm, float(np.mean(finals))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=200)
    ap.add_argument("--jobs", type=int, default=28)
    ap.add_argument("--out", default=os.path.join(_RL, "runs", "bcbarn", "data"))
    ap.add_argument("--coverage-only", action="store_true")
    ap.add_argument("--min-coverage", type=float, default=0.60)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    per = max(1, args.episodes // args.jobs)
    jobs = [(w, per, args.out, args.coverage_only) for w in range(args.jobs)]
    tot = fex = mm = 0
    money = []
    with Pool(args.jobs) as pool:
        for wid, n, nf, nm, mean_m in pool.imap_unordered(_run_chunk, jobs):
            tot += n
            fex += nf
            mm += nm
            money.append(mean_m)
            print(f"chunk {wid:02d}: {n} steps, farmer exact {nf / n:.2f}, "
                  f"market matched {nm / n:.2f}, teacher money {mean_m:,.0f}",
                  flush=True)
    fcov = fex / max(1, tot)
    print(f"TOTAL: {tot:,} steps  farmer coverage {fcov:.3f}  "
          f"market coverage {mm / max(1, tot):.3f}  "
          f"teacher money mean {np.mean(money):,.0f}")
    print("COVERAGE-PASS" if fcov >= args.min_coverage else "COVERAGE-FAIL")


if __name__ == "__main__":
    main()
