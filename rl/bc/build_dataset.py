#!/usr/bin/env python
"""Replays -> a multi-head BC dataset, with the fidelity ledger attached.

For every step of every seat in data/ilreplays/*.json.gz (current-balance
top-ladder games; both seats are ~3.1k players), emit

  obs      (719, OBS_DIM) float16   -- rl/obs.py encoding
  farmer   (719,) int16             -- head index whose decode reproduces
                                       the recorded farmer action, else -1
  market   (719,) int16             -- ditto for the recorded order list
  hands    (719, MAX_HANDS) int16   -- per-hand task labels: the recorded
                                       WORK op's family when that hand's
                                       tile is in the family's target set
                                       (FEED's wheat PICKUP leg included);
                                       IDLE for recorded PASS, AUTO (0)
                                       for moves/DROP, -1 = dead slot or
                                       not expressible

into data/bcdata/<episode>-s<seat>.npz. -1 labels are skipped by the CE
loss downstream; the printed ledger is the state-level fidelity number
TODO #4 asked for. Rerunnable; skips shards already on disk.

    source setup_env.sh
    python rl/bc/build_dataset.py --limit 4     # pilot
    python rl/bc/build_dataset.py               # everything pulled so far
"""

import argparse
import collections
import glob
import gzip
import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_RL = os.path.dirname(_HERE)
_REPO = os.path.dirname(_RL)
for p in (_RL,):
    if p not in sys.path:
        sys.path.insert(0, p)

import actions as A  # noqa: E402
import obs as O      # noqa: E402

SRC = os.path.join(_REPO, "data", "ilreplays")
OUT = os.path.join(_REPO, "data", "bcdata")

_MOVES = {"NORTH", "SOUTH", "EAST", "WEST"}
_WORK_FAM = {"HARVEST": "harvest", "WATER": "unwatered", "CARE": "uncared",
             "COLLECT_FERTILIZER": "fert_ready", "DIG": "weeds",
             "FEED": "unfed"}
_IDLE = A.HAND_TASKS.index("IDLE")
_FEED = A.HAND_TASKS.index("FEED")


def _label_step(obs_d, rec, agg):
    s = A._scan(obs_d)
    # farmer
    rf = list(rec.get("farmer") or ["PASS"])
    f_lab = -1
    for idx, name in enumerate(A.FARMER_ACTIONS):
        if (A._farmer_action(obs_d, name, s) or ["PASS"]) == rf:
            f_lab = idx
            break
    agg["f_n"] += 1
    agg["f_hit"] += f_lab >= 0
    if f_lab < 0:
        agg["f_miss"][rf[0]] += 1
    # market
    rm = [list(o) for o in (rec.get("market") or [])]
    m_lab = -1
    for idx, name in enumerate(A.MARKET_ACTIONS):
        if [list(o) for o in A._market_action(obs_d, name)] == rm:
            m_lab = idx
            break
    agg["m_n"] += 1
    agg["m_hit"] += m_lab >= 0
    if m_lab < 0:
        agg["m_miss"][min(len(rm), 5)] += 1
    # hands
    seat = obs_d["player"]
    hands = obs_d["farms"][seat].get("hands", [])
    h_lab = np.full(A.MAX_HANDS, -1, dtype=np.int16)
    for h_i, act in enumerate(rec.get("hands") or []):
        if not act or h_i >= min(len(hands), A.MAX_HANDS):
            continue
        op = act[0]
        if op == "PASS":
            h_lab[h_i] = _IDLE
        elif op in _MOVES or op == "DROP":
            h_lab[h_i] = 0                     # AUTO: executor detail
        elif op == "PICKUP" and len(act) > 1 and act[1] == "WHEAT":
            h_lab[h_i] = _FEED
            agg["h_n"] += 1
            agg["h_hit"] += 1
        elif op in _WORK_FAM:
            agg["h_n"] += 1
            hx, hy = hands[h_i][0], hands[h_i][1]
            if (hx, hy) in set(s[_WORK_FAM[op]]):
                h_lab[h_i] = A.HAND_TASKS.index(op)
                agg["h_hit"] += 1
            else:
                agg["h_miss"][op] += 1
        else:
            agg["h_n"] += 1
            agg["h_miss"][op] += 1
    return f_lab, m_lab, h_lab


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="episodes; 0 = all")
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    files = sorted(glob.glob(os.path.join(SRC, "*.json.gz")))
    if args.limit:
        files = files[:args.limit]
    agg = collections.Counter()
    for k in ("f_miss", "m_miss", "h_miss"):
        agg[k] = collections.Counter()
    built = skipped = 0
    for path in files:
        ep_id = os.path.basename(path).split(".")[0]
        outs = [os.path.join(OUT, f"{ep_id}-s{s}.npz") for s in (0, 1)]
        if all(os.path.exists(o) for o in outs):
            skipped += 1
            continue
        steps = json.load(gzip.open(path))["steps"]
        for seat in (0, 1):
            T = len(steps) - 1
            X = np.zeros((T, O.OBS_DIM), dtype=np.float16)
            F = np.full(T, -1, dtype=np.int16)
            M = np.full(T, -1, dtype=np.int16)
            H = np.full((T, A.MAX_HANDS), -1, dtype=np.int16)
            for i in range(T):
                obs_d = dict(steps[i][seat]["observation"])
                rec = steps[i + 1][seat].get("action") or {}
                X[i] = O.encode(obs_d).astype(np.float16)
                F[i], M[i], H[i] = _label_step(obs_d, rec, agg)
            np.savez_compressed(outs[seat], obs=X, farmer=F, market=M,
                                hands=H)
        built += 1
        print(f"{ep_id}: shards written", flush=True)
    print(f"\nepisodes built {built}, skipped {skipped}")
    for head, n, hit, miss in (("farmer", "f_n", "f_hit", "f_miss"),
                               ("market", "m_n", "m_hit", "m_miss"),
                               ("hand-work", "h_n", "h_hit", "h_miss")):
        if agg[n]:
            print(f"{head}: {agg[hit]}/{agg[n]} = "
                  f"{100 * agg[hit] / agg[n]:.1f}%  "
                  f"misses {dict(agg[miss].most_common(6))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
