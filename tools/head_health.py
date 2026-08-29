#!/usr/bin/env python
"""Per-head entropy and per-family probability mass for an exported policy.

Why this exists (docs/RUNS.md 2026-08-23, the ROOT CAUSE verdict). The market
head had collapsed -- P(any BUY_SEED | a seed purchase is legal) with a MEDIAN of
0.02% -- and it survived five generations undetected because ClipPPOLoss applies
one scalar entropy_coeff to the composite distribution's SUMMED entropy over 14
heads (farmer 23 + market 31 + twelve hand heads of 10, ceiling about 34). Twelve
hand heads satisfy the bonus by themselves while the market head dies, and the
training log's aggregate `ent` column reads 6.45-13.49 throughout. A dead head is
neither penalised in the loss nor visible in the log.

So this reads the collapse directly off an export, per head, and prints the
probability mass on the action families that build a farm. It is the proximal
readout the prospect / tutor2 / haymaker pre-registrations refer to, and it costs
one episode (~3 s) instead of a nine-opponent array (hours), so a chain can be
checked at any link instead of only at the end.

Two things it does deliberately:

  - States come from a REAL opponent's episode, not a uniform-random rollout.
    Random play bankrupts both farms, so by day 12 the market mask has exactly
    ONE legal action (NOOP) on every lane -- the first draft of test_eps.py
    passed its gates on exactly those degenerate states, testing a one-action
    distribution. Any probability measured there is meaningless.
  - Every family is conditioned on being LEGAL. An unconditional P(BUY_SEED)
    conflates "the policy will not buy" with "buying is masked out", and those
    have opposite prescriptions.

    python tools/head_health.py <export-dir> [more...] [--opp agents/champ/k06.py]
                               [--seed 10000] [--every 7]

Baselines measured 2026-08-23 on nn-d0-chisel: P(any BUY_SEED | legal) median
0.02% / mean 4.03%, and P(PLANT | legal) per hand median 21.4%. Planting had NOT
collapsed; buying had.
"""

import argparse
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FAMILIES = (
    ("BUY_SEED", lambda n: n.startswith("BUY_SEED")),
    ("BUY_LAND", lambda n: n == "BUY_LAND"),
    ("BUY_ANIMAL", lambda n: n.startswith("BUY_") and n[4:] in
     ("GOOSE", "COW", "SHEEP")),
    ("HIRE", lambda n: n == "HIRE"),
    ("SELL_any", lambda n: n.startswith("SELL")),
    ("BUY_WHEAT", lambda n: n == "BUY_WHEAT"),
)


def _load(d):
    """Import an export's private modules and return (obs, actions, forward)."""
    sys.path.insert(0, d)
    obs_mod = act_mod = None
    for f in sorted(os.listdir(d)):
        if f.startswith("kg_rl_obs_") and f.endswith(".py"):
            obs_mod = __import__(f[:-3])
        elif f.startswith("kg_rl_actions_") and f.endswith(".py"):
            act_mod = __import__(f[:-3])
    if obs_mod is None or act_mod is None:
        raise RuntimeError(f"no private obs/actions modules in {d}")
    W = dict(np.load(os.path.join(d, "weights.npz")))

    def fwd(x):
        h = np.maximum(0.0, W["l1w"] @ x + W["l1b"])
        h = np.maximum(0.0, W["l2w"] @ h + W["l2b"])
        f = W["fw"] @ h + W["fb"]
        m = W["mw"] @ h + W["mb"]
        hl = (W["hw"] @ h + W["hb"]) if "hw" in W else None
        return f, m, hl

    return obs_mod, act_mod, fwd


def _softmax_masked(logits, mask):
    z = np.where(mask, logits, -np.inf)
    z = z - z.max()
    p = np.exp(z)
    p[~mask] = 0.0
    s = p.sum()
    return p / s if s > 0 else p


def _entropy(p):
    q = p[p > 0]
    return float(-(q * np.log(q)).sum())


def probe(d, opp, seed, every):
    from kaggle_environments import make
    obs_mod, act_mod, fwd = _load(d)
    names = [str(n) for n in act_mod.MARKET_ACTIONS]
    HT = [str(t) for t in getattr(act_mod, "HAND_TASKS", [])]
    env = make("kaggriculture",
               configuration={"episodeSteps": 720, "seed": seed}, debug=False)
    env.run([os.path.join(d, "main.py"), opp])

    plant_legal, plant_slots = [0], [0]
    fam_p = {k: [] for k, _ in FAMILIES}
    fam_legal = {k: 0 for k, _ in FAMILIES}
    n_states = 0
    ent_f, ent_m, ent_h = [], [], []
    plant_p = []
    n_legal = []
    for step in range(0, len(env.steps) - 1, every):
        o = env.steps[step][0].observation
        try:
            x = obs_mod.encode(o)
            fl, ml, hl = fwd(x)
            fm = np.asarray(act_mod.farmer_mask(o), dtype=bool)
            mm = np.asarray(act_mod.market_mask(o), dtype=bool)
            if not mm.any():
                continue
            pf = _softmax_masked(fl, fm)
            pm = _softmax_masked(ml, mm)
            ent_f.append(_entropy(pf))
            ent_m.append(_entropy(pm))
            n_legal.append(int(mm.sum()))
            n_states += 1
            for key, pred in FAMILIES:
                idx = [i for i, n in enumerate(names) if pred(n) and mm[i]]
                if idx:                       # conditioned on being LEGAL
                    fam_p[key].append(float(pm[idx].sum()))
                    fam_legal[key] += 1
            if hl is not None and HT:
                hmk = np.asarray(act_mod.hand_task_mask(o), dtype=bool)
                if hmk.size and hmk.ndim == 2 and hmk.shape[0] > 0:
                    hl2 = hl.reshape(hmk.shape)
                    es, ps = [], []
                    pi = HT.index("PLANT") if "PLANT" in HT else -1
                    # 2026-08-28: this tool reported P(PLANT | legal) but never
                    # how OFTEN plant is legal, so checklist (a) was only ever
                    # verified for the market head. e0a90f8 raised BUY_SEED 20x
                    # and PLANT fell 13x, which makes PLANT's legality the next
                    # thing that has to be on the table.
                    for r in range(hmk.shape[0]):
                        if not hmk[r].any():
                            continue
                        q = _softmax_masked(hl2[r], hmk[r])
                        es.append(_entropy(q))
                        if pi >= 0:
                            plant_slots[0] += 1
                            if hmk[r, pi]:
                                plant_legal[0] += 1
                                ps.append(float(q[pi]))
                    if es:
                        ent_h.append(float(np.mean(es)))
                    if ps:
                        plant_p.append(float(np.mean(ps)))
        except Exception:
            continue
    sys.path.pop(0)
    return (fam_p, ent_f, ent_m, ent_h, plant_p, n_legal, fam_legal, n_states,
            plant_legal[0], plant_slots[0])


def _med(v):
    return float(np.median(v)) if v else float("nan")


def by_task(d, opp, seed, every, lo, hi):
    """Per-hand-task probability mass, over live hand slots, in a day window.

    Why (2026-08-29, verdict 8db606f): two independent interventions that
    GUARANTEED the seed supply both pushed P(PLANT|legal) DOWN -- the market
    entropy floor (BUY_SEED 20x up, PLANT 13x down) and the fixed market program
    (10.6% -> 7.0%). So planting is not seed-limited, and the question is which
    tasks hold the mass instead. One number for PLANT cannot answer that.

    Two things this exposes that the PLANT column alone cannot:
      - HAND_TASKS carries BOTH a semantic `PLANT` (which picks the crop itself)
        AND `RAW_PLANT_<crop>` cells. P(PLANT|legal) only ever measured the
        semantic one, so a policy that plants via the RAW cells -- or that has
        them suppressed -- reads identically.
      - `RAW_*` are 27 of the 39 tasks, i.e. the bulk of the 10->39 vocabulary
        expansion whose new rows are exactly what --legacy-new-bias sets. Their
        mass is therefore load-path-sensitive and has to be read, not assumed.

    Restricted to slots where the task is LEGAL, and averaged over live hands
    only, so a small crew does not dilute every number the way head_health's
    MAX_HANDS denominator did (the 9-10% vs 14-27% correction, 9080478).
    """
    from kaggle_environments import make
    obs_mod, act_mod, fwd = _load(d)
    HT = [str(t) for t in getattr(act_mod, "HAND_TASKS", [])]
    env = make("kaggriculture",
               configuration={"episodeSteps": 720, "seed": seed}, debug=False)
    env.run([os.path.join(d, "main.py"), opp])

    p = {t: [] for t in HT}
    legal = {t: 0 for t in HT}
    rows = 0
    for step in range(0, len(env.steps) - 1, every):
        o = env.steps[step][0].observation
        if not (lo <= o.get("day", step // 24) <= hi):
            continue
        try:
            hl = fwd(obs_mod.encode(o))[2]
            if hl is None:
                break
            hmk = np.asarray(act_mod.hand_task_mask(o), dtype=bool)
            if not (hmk.size and hmk.ndim == 2):
                continue
            hl2 = hl.reshape(hmk.shape)
            for r in range(hmk.shape[0]):
                if not hmk[r].any():
                    continue
                q = _softmax_masked(hl2[r], hmk[r])
                rows += 1
                for i, t in enumerate(HT):
                    if hmk[r, i]:
                        legal[t] += 1
                        p[t].append(float(q[i]))
        except Exception:
            continue
    sys.path.pop(0)
    return HT, p, legal, rows


def by_crop(d, opp, seed, every, lo, hi):
    """P(BUY_SEED_<crop> | that crop's seed is legal), per crop, in a day window.

    Why a separate table (2026-08-29, docs/RUNS.md): the family aggregate above
    answers "does it buy seed at all", and 08-23 used it to find the market head
    collapsed. But the board read on day 18-24 shows something the aggregate
    cannot express -- our net holds 5.42 STRAWBERRY seeds and ZERO WHEAT, with 22
    empty tiles, and ordered WHEAT seed ONCE in a season against k01's 580. One
    number over `n.startswith("BUY_SEED")` sums those two facts into a single
    healthy-looking figure.

    The window matters as much as the split. STRAWBERRY has first_yield_day 10,
    so declining to sow it after day 24 is CORRECT; WHEAT maxes in 4 days and is
    the only crop that pays in the late season. A season-wide average therefore
    credits the right refusal and the wrong one to the same account.

    `MARKET_ACTIONS` carries a per-crop `BUY_SEED_<crop>` entry (rl/actions.py:69),
    so this is one index into the head's own categorical -- not a new mechanism.
    """
    from kaggle_environments import make
    obs_mod, act_mod, fwd = _load(d)
    names = [str(n) for n in act_mod.MARKET_ACTIONS]
    crops = [n[len("BUY_SEED_"):] for n in names if n.startswith("BUY_SEED_")]
    idx = {c: names.index(f"BUY_SEED_{c}") for c in crops}
    env = make("kaggriculture",
               configuration={"episodeSteps": 720, "seed": seed}, debug=False)
    env.run([os.path.join(d, "main.py"), opp])

    p = {c: [] for c in crops}
    legal = {c: 0 for c in crops}
    n = 0
    for step in range(0, len(env.steps) - 1, every):
        o = env.steps[step][0].observation
        if not (lo <= o.get("day", step // 24) <= hi):
            continue
        try:
            ml = fwd(obs_mod.encode(o))[1]
            mm = np.asarray(act_mod.market_mask(o), dtype=bool)
            if not mm.any():
                continue
            pm = _softmax_masked(ml, mm)
            n += 1
            for c in crops:
                if mm[idx[c]]:
                    legal[c] += 1
                    p[c].append(float(pm[idx[c]]))
        except Exception:
            continue
    sys.path.pop(0)
    return crops, p, legal, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--opp", default=f"{ROOT}/agents/champ/k06.py")
    ap.add_argument("--seed", type=int, default=10000)
    ap.add_argument("--every", type=int, default=7)
    ap.add_argument("--by-task", metavar="LO-HI", default=None,
                    help="also print per-hand-task probability mass over this "
                         "day window; the PLANT column alone cannot say which "
                         "tasks hold the mass instead, nor separate semantic "
                         "PLANT from the RAW_PLANT_<crop> cells")
    ap.add_argument("--by-crop", metavar="LO-HI", default=None,
                    help="also split P(BUY_SEED|legal) per crop over this day "
                         "window, e.g. 18-24. The family aggregate cannot "
                         "distinguish 'buys the wrong seed' from 'buys none'")
    a = ap.parse_args()

    print(f"\n  states from a real episode against {os.path.basename(a.opp)}, "
          f"seed {a.seed}, every {a.every} steps")
    print(f"  all family numbers are CONDITIONED on that family being LEGAL\n")
    # BOTH median and mean, because they answer different questions and the
    # median alone misreads a spiky action as dead: HIRE has a median of 0.00%
    # yet the crew reaches 7.8, because hiring happens in bursts on 38 of 720
    # turns. "Dead" means both are ~0; "spiky but functional" means median ~0
    # with a real mean.
    hdr = (f"  {'agent':<20}{'H(mkt)':>7}{'ceil':>6}{'n_leg':>6}"
           + "".join(f"{k[:11]:>21}" for k, _ in FAMILIES) + f"{'PLANT':>22}")
    print(hdr)
    print(f"  {'':<20}{'':>7}{'':>6}{'':>6}"
          + "".join(f"{'med/mean/legal%':>21}" for _ in FAMILIES)
          + f"{'med / mean / legal%':>22}")
    for d in a.dirs:
        name = os.path.basename(d.rstrip("/"))
        try:
            (fam, ef, em, eh, pp, nl, flg, ns,
             pl_legal, pl_slots) = probe(d, a.opp, a.seed, a.every)
        except Exception as e:
            print(f"  {name:<22}  ERROR {e}")
            continue
        import math
        ceil = math.log(max(_med(nl), 1.0))
        row = (f"  {name[:20]:<20}{_med(em):>7.2f}{ceil:>6.2f}{_med(nl):>6.0f}")
        for k, _ in FAMILIES:
            v = fam[k]
            mn = float(np.mean(v)) if v else float("nan")
            lg = flg[k] / max(ns, 1)
            row += f"{_med(v)*100:>6.2f}/{mn*100:>6.2f}/{lg*100:>5.0f}%"
        mnp = float(np.mean(pp)) if pp else float("nan")
        pl = pl_legal / max(pl_slots, 1)
        row += f"{_med(pp)*100:>5.1f}/{mnp*100:>6.1f}/{pl*100:>5.0f}%"
        print(row)
    if a.by_task:
        lo, hi = (int(v) for v in a.by_task.split("-"))
        print(f"\n  per-hand-task mass over LIVE hand slots, day {lo}-{hi}")
        got = {}
        for d in a.dirs:
            name = os.path.basename(d.rstrip("/"))
            try:
                HT, p, legal, rows = by_task(d, a.opp, a.seed, a.every, lo, hi)
            except Exception as e:
                print(f"  {name:<22}  ERROR {e}")
                continue
            got[name] = (HT, p, legal, rows)
        if got:
            names = list(got)
            HT = got[names[0]][0]
            print(f"  {'task':<24}" + "".join(f"{n[:18]:>26}" for n in names))
            print(f"  {'':<24}" + "".join(f"{'mean% / legal%':>26}"
                                         for _ in names))
            # Ordered by the FIRST agent's mean so the two columns stay
            # comparable row by row; tasks never legal anywhere are dropped.
            def key(t):
                v = got[names[0]][1][t]
                return -(float(np.mean(v)) if v else 0.0)
            for t in sorted(HT, key=key):
                if not any(got[n][2][t] for n in names):
                    continue
                row = f"  {t:<24}"
                for n in names:
                    _HT, p, legal, rows = got[n]
                    v = p[t]
                    mn = float(np.mean(v)) * 100 if v else 0.0
                    row += f"{mn:>17.2f} /{100*legal[t]/max(rows,1):>6.0f}%"
                print(row)
        print("  legal% is over live hand slots, so a small crew does not "
              "dilute it (cf. the 9-10% vs 14-27% correction in 9080478)")

    if a.by_crop:
        lo, hi = (int(v) for v in a.by_crop.split("-"))
        print(f"\n  P(BUY_SEED_<crop> | that crop is legal), day {lo}-{hi} only")
        print(f"  {'agent':<20}{'states':>7}   "
              + "".join(f"{c[:10]:>22}" for c in
                        ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")))
        print(f"  {'':<20}{'':>7}   "
              + "".join(f"{'med/mean/legal%':>22}" for _ in range(5)))
        for d in a.dirs:
            name = os.path.basename(d.rstrip("/"))
            try:
                crops, p, legal, n = by_crop(d, a.opp, a.seed, a.every, lo, hi)
            except Exception as e:
                print(f"  {name:<22}  ERROR {e}")
                continue
            row = f"  {name[:20]:<20}{n:>7}   "
            for c in ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"):
                if c not in p:
                    row += f"{'-':>22}"
                    continue
                v = p[c]
                mn = float(np.mean(v)) * 100 if v else float("nan")
                row += (f"{_med(v)*100:>6.2f}/{mn:>6.2f}/"
                        f"{100*legal[c]/max(n,1):>5.0f}%")
            print(row)
        print(f"  WHEAT: seed $10, first yield +2 days, maxed in 4 -- the only "
              f"crop that pays after day 18. STRAWBERRY first yields at +10, so "
              f"NOT sowing it late is correct.")

    print(f"\n  reference (nn-d0-chisel, 2026-08-23): P(BUY_SEED|legal) median "
          f"0.02%, P(PLANT|legal) median 21.4%")
    print(f"  H(market) ceiling is ln(n_legal); a COLLAPSED market head reads "
          f"near 0 while the summed `ent` in the training log still looks fine")
    print("HEAD-HEALTH-DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
