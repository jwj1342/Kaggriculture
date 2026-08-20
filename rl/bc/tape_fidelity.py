#!/usr/bin/env python
"""State-level fidelity of the action heads against top-ladder tapes.

TODO #4's second gate. The op-level number (88.8% of hand work is in the
FEED-era vocabulary) says the VOCABULARY fits; this measures whether the
GREEDY EXECUTORS reproduce the recorded decisions on the recorded states:
for every step of a reconstructed episode, does some farmer index decode
to the recorded farmer action, does some market index decode to the
recorded order list, and is each recorded hand WORK action reachable as
"a task whose family owns that tile"?

Reconstruction needs no downloads for episodes whose BOTH seats are in
the library (32 of 339): engine + seed + both tapes is deterministic,
and each replay is accepted only if both final scores match the library
metadata to the dollar (the tracelib verify bar).

    source setup_env.sh
    python rl/bc/tape_fidelity.py --episodes 6          # pilot
    python rl/bc/tape_fidelity.py --episodes 32 -q      # the full free set

CPU, ~3 s per episode. Prints per-head fidelity and the miss breakdown.
"""

import argparse
import base64
import collections
import gzip
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_RL = os.path.dirname(_HERE)
_REPO = os.path.dirname(_RL)
for p in (_RL, _REPO):
    if p not in sys.path:
        sys.path.insert(0, p)

import actions as A  # noqa: E402

LIB = os.path.join(_REPO, "dist", "tracelib.json.xz")

_TPL = ('import json,gzip,base64\n'
        '_T=json.loads(gzip.decompress(base64.b64decode("{b}")).decode())\n'
        '_P={{"farmer":["PASS"],"hands":[],"market":[]}}\n'
        'def agent(obs):\n'
        '    try:\n'
        '        i=int(obs.get("step",0) or 0)\n'
        '        return _T[i] if 0<=i<len(_T) else _P\n'
        '    except Exception: return _P\n')

_WORK_FAM = {"HARVEST": "harvest", "WATER": "unwatered", "CARE": "uncared",
             "COLLECT_FERTILIZER": "fert_ready", "DIG": "weeds",
             "FEED": "unfed"}


def _load_pairs():
    import lzma
    with lzma.open(LIB) as f:
        lines = json.load(f)["lines"]
    by_ep = collections.defaultdict(dict)
    for v in lines.values():
        by_ep[v["episode"]][v["seat"]] = v
    return {e: s for e, s in by_ep.items() if set(s) == {0, 1}}


def _replay(pair, tmp):
    from kaggle_environments import make
    paths = []
    for seat in (0, 1):
        path = os.path.join(tmp, f"tape{seat}.py")
        with open(path, "w") as f:
            f.write(_TPL.format(b=pair[seat]["turns"]))
        paths.append(path)
    env = make("kaggriculture",
               configuration={"episodeSteps": 720, "seed": pair[0]["seed"]})
    env.run(paths)
    scores = [env.steps[-1][s].reward for s in (0, 1)]
    want = {0: pair[0]["best_score"], 1: pair[1]["best_score"]}
    if not all(abs(scores[s] - want[s]) < 1.0 for s in (0, 1)):
        return None, scores, want
    return env.steps, scores, want


def _fidelity(steps, seat, agg):
    for i in range(len(steps) - 1):
        obs = steps[i][seat].observation
        rec = steps[i + 1][seat].action or {}
        obs = dict(obs)  # kaggle Struct -> plain dict for actions.py
        s = A._scan(obs)
        # farmer: does any macro index decode to the recorded action?
        rf = rec.get("farmer") or ["PASS"]
        hit = False
        for idx, name in enumerate(A.FARMER_ACTIONS):
            if (A._farmer_action(obs, name, s) or ["PASS"]) == list(rf):
                hit = True
                break
        agg["farmer_n"] += 1
        agg["farmer_hit"] += hit
        if not hit:
            agg["farmer_miss"][rf[0]] += 1
        # market: exact order-list match under any head index
        rm = [list(o) for o in (rec.get("market") or [])]
        mhit = False
        for idx, name in enumerate(A.MARKET_ACTIONS):
            if [list(o) for o in A._market_action(obs, name)] == rm:
                mhit = True
                break
        agg["mkt_n"] += 1
        agg["mkt_hit"] += mhit
        if not mhit:
            agg["mkt_miss"][min(len(rm), 5)] += 1
        # hands: each recorded WORK op must be reachable as "a task whose
        # family owns that tile" (moves/PASS/DROP are executor detail and
        # counted separately; PICKUP WHEAT is the FEED leg)
        hands = obs["farms"][seat].get("hands", [])
        for h_i, act in enumerate(rec.get("hands") or []):
            if not act or h_i >= len(hands):
                continue
            op = act[0]
            if op in ("NORTH", "SOUTH", "EAST", "WEST", "PASS", "DROP"):
                agg["hand_soft"] += 1
                continue
            agg["hand_n"] += 1
            if op == "PICKUP":
                ok = len(act) > 1 and act[1] == "WHEAT"
            elif op in _WORK_FAM:
                hx, hy = hands[h_i][0], hands[h_i][1]
                ok = (hx, hy) in set(s[_WORK_FAM[op]])
            else:
                ok = False
            agg["hand_hit"] += ok
            if not ok:
                agg["hand_miss"][op] += 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=6)
    ap.add_argument("-q", "--quiet", action="store_true")
    args = ap.parse_args()
    os.environ.setdefault("KG_FAST_ENV", "1")

    pairs = _load_pairs()
    tmp = os.path.join(os.environ.get("CLAUDE_JOB_TMP", "/tmp"),
                       f"tapefid-{os.getpid()}")
    os.makedirs(tmp, exist_ok=True)
    agg = collections.Counter()
    agg["farmer_miss"] = collections.Counter()
    agg["mkt_miss"] = collections.Counter()
    agg["hand_miss"] = collections.Counter()
    done = bad = 0
    for ep_id in sorted(pairs)[:args.episodes]:
        steps, scores, want = _replay(pairs[ep_id], tmp)
        if steps is None:
            bad += 1
            if not args.quiet:
                print(f"episode {ep_id}: reconstruction MISMATCH "
                      f"{scores} vs {want} -- skipped")
            continue
        for seat in (0, 1):
            _fidelity(steps, seat, agg)
        done += 1
        if not args.quiet:
            print(f"episode {ep_id}: reconstructed to the dollar "
                  f"({scores[0]:,.0f} / {scores[1]:,.0f})")
    print(f"\nepisodes reconstructed {done}, mismatched {bad}")
    if agg["farmer_n"]:
        print(f"farmer decode fidelity: {agg['farmer_hit']}/{agg['farmer_n']} "
              f"= {100 * agg['farmer_hit'] / agg['farmer_n']:.1f}%  "
              f"misses: {dict(agg['farmer_miss'].most_common(8))}")
    if agg["mkt_n"]:
        print(f"market decode fidelity: {agg['mkt_hit']}/{agg['mkt_n']} "
              f"= {100 * agg['mkt_hit'] / agg['mkt_n']:.1f}%  "
              f"misses by #orders: {dict(sorted(agg['mkt_miss'].items()))}")
    if agg["hand_n"]:
        print(f"hand work-op reachability: {agg['hand_hit']}/{agg['hand_n']} "
              f"= {100 * agg['hand_hit'] / agg['hand_n']:.1f}%  "
              f"(+{agg['hand_soft']} moves/PASS/DROP not scored)  "
              f"misses: {dict(agg['hand_miss'].most_common(8))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
