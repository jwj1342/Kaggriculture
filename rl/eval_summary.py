#!/usr/bin/env python
"""Goal scorecard from rl/runs/<run>/eval/*.json (written by slurm/rl_eval.sh).

    python rl/eval_summary.py --run m2

Beaten = Wilson 95% interval entirely above 50%. Lost = entirely below.
Anything straddling 50% is unresolved -- more seeds, not more adjectives.
"""

import argparse
import glob
import json
import os

RECORDINGS = {"w49", "w100", "w88", "w50"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="m2")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "runs", args.run, "eval", "*.json")))
    if not files:
        print("no eval results yet")
        return

    beaten, lost, unresolved = [], [], []
    print(f"{'opponent':<16} {'games':>5} {'win':>7} {'95% CI':>16} {'margin':>10}")
    for f in files:
        d = json.load(open(f))
        s = d["summary"]
        name = os.path.basename(f)[:-5]
        lo, hi = (c / 100.0 for c in s["ci"])  # tools/stats.wilson returns percentages
        verdict = "BEATEN" if lo > 0.5 else ("LOST" if hi < 0.5 else "unresolved")
        (beaten if lo > 0.5 else lost if hi < 0.5 else unresolved).append(name)
        print(f"{name:<16} {s['n']:>5} {s['winrate']:>6.1%} "
              f"[{lo:>5.1%},{hi:>5.1%}] {s['margin']:>+10,.0f}  {verdict}")

    n = len(files)
    rec_beaten = [b for b in beaten if b in RECORDINGS]
    print(f"\nbeaten {len(beaten)}/{n}: {', '.join(beaten) or '-'}")
    print(f"recordings beaten: {', '.join(rec_beaten) or 'none'}")
    goal = len(beaten) >= (n + 1) // 2 and rec_beaten
    print(f"GOAL {'MET' if goal else 'NOT MET'} "
          f"(need >={(n + 1) // 2}/{n} beaten incl. one recording)")


if __name__ == "__main__":
    main()
