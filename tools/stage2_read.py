#!/usr/bin/env python
"""Read a macro_audit candidate screen: each candidate MINUS the base, paired.

Why this exists. macro_audit reports every candidate against its own
FOLLOW_POLICY lane, so its `delta` answers "is this option better than the frozen
net" -- which is not the stage 2 question. Stage 2 asks "is this candidate better
than the base candidate we already validated", and the archive's own lesson is
that the answer must be a PAIRED difference on identical seeds, seats and
opponents, because unbalanced comparisons have reversed conclusions in this
repository at least once.

The base and the candidate share the same baseline lane by construction (same
frozen checkpoint, same seed, same opponent), so differencing the intervention
arm is equivalent to differencing the deltas and avoids compounding two noisy
quantities.

Acceptance, applied here exactly as pre-registered: the seed-clustered 95%
bootstrap interval of the difference must exclude zero AND every
opponent-by-seat cell must carry the same sign. A candidate that passes only the
interval is reported as such and does NOT count -- an interval alone has already
produced a reversed ordering here.

    python tools/stage2_read.py rl/runs/stage2-ofat/result.json [more...]
                               [--base barnyard_prefix:k01_route_s34_fert:720]
                               [--metric margin] [--boot 20000]

Multiple files are pooled, and the base is required to appear in each so its
margin can be cross-checked between jobs; a mismatch means the pairing
assumption is broken and is reported instead of averaged over.
"""

import argparse
import json
import os
import random
import sys
from collections import defaultdict

DEFAULT_BASE = "barnyard_prefix:k01_route_s34_fert:720"


def load(paths, metric):
    """-> {option: {(file, opponent, seat): {seed: value}}}, and win counts."""
    per = defaultdict(lambda: defaultdict(dict))
    wins = defaultdict(lambda: [0, 0])
    for path in paths:
        tag = os.path.basename(os.path.dirname(path))
        with open(path) as fh:
            doc = json.load(fh)
        for cell in doc["cells"]:
            key = (tag, cell["opponent"], cell["seat"])
            for rec in cell["records"]:
                if not rec.get("triggered"):
                    continue
                arm = rec.get("intervention") or {}
                if metric not in arm:
                    continue
                per[cell["option"]][key][rec["seed"]] = arm[metric]
                w = arm.get("win")
                if w is not None:
                    wins[cell["option"]][0] += int(w > 0)
                    wins[cell["option"]][1] += 1
    return per, wins


def boot_ci(values, n_boot, rng):
    """Percentile bootstrap over the CLUSTER units passed in (one per seed)."""
    if not values:
        return float("nan"), float("nan")
    means = []
    k = len(values)
    for _ in range(n_boot):
        means.append(sum(values[rng.randrange(k)] for _ in range(k)) / k)
    means.sort()
    return means[int(0.025 * n_boot)], means[int(0.975 * n_boot)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results", nargs="+")
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--metric", default="margin")
    ap.add_argument("--boot", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=17)
    a = ap.parse_args()

    per, wins = load(a.results, a.metric)
    if a.base not in per:
        print(f"base option {a.base!r} not in results; options are:")
        for o in sorted(per):
            print(f"  {o}")
        return 2
    rng = random.Random(a.seed)
    base = per[a.base]

    # Cross-job consistency: the same base must read the same in every file.
    by_file = defaultdict(list)
    for (tag, _opp, _seat), seeds in base.items():
        by_file[tag] += list(seeds.values())
    if len(by_file) > 1:
        print("\n  base cross-job check (the same spec, so these must agree):")
        for tag, vals in sorted(by_file.items()):
            print(f"    {tag:<16} n={len(vals):<4} mean {sum(vals)/len(vals):>12,.0f}")
        spread = max(sum(v) / len(v) for v in by_file.values()) - \
            min(sum(v) / len(v) for v in by_file.values())
        note = ("consistent" if abs(spread) < 1e-6 else
                f"DIFFER by {spread:,.0f} -- pairing assumption is broken")
        print(f"    -> {note}")

    base_all = [v for seeds in base.values() for v in seeds.values()]
    print(f"\n  metric = {a.metric}; base {a.base}")
    print(f"  base absolute: n={len(base_all)} mean {sum(base_all)/len(base_all):,.0f}")
    print(f"\n  {'candidate':<52}{'n':>4}{'diff vs base':>14}"
          f"{'95% CI':>26}{'cells +/-':>11}{'verdict':>10}")

    rows = []
    for option, cells in per.items():
        if option == a.base:
            continue
        # Cluster unit is the seed: one mean difference per seed, pooled over the
        # cells that seed appears in, so a seed cannot vote four times.
        by_seed = defaultdict(list)
        cell_sign = []
        for key, seeds in cells.items():
            if key not in base:
                continue
            diffs = [v - base[key][s] for s, v in seeds.items() if s in base[key]]
            if diffs:
                cell_sign.append(sum(diffs) / len(diffs))
            for s, v in seeds.items():
                if s in base[key]:
                    by_seed[s].append(v - base[key][s])
        units = [sum(v) / len(v) for v in by_seed.values()]
        if not units:
            continue
        mean = sum(units) / len(units)
        lo, hi = boot_ci(units, a.boot, rng)
        pos = sum(1 for c in cell_sign if c > 0)
        neg = len(cell_sign) - pos
        excludes = (lo > 0 and hi > 0) or (lo < 0 and hi < 0)
        same_sign = pos == len(cell_sign) or neg == len(cell_sign)
        if excludes and same_sign:
            verdict = "PASS" if mean > 0 else "worse"
        elif excludes:
            verdict = "CI-only"
        else:
            verdict = "flat"
        rows.append((mean, option, len(units), lo, hi, pos, neg, verdict))

    for mean, option, n, lo, hi, pos, neg, verdict in sorted(rows, reverse=True):
        short = option.replace("barnyard_prefix:", "").replace(":720", "")
        print(f"  {short:<52}{n:>4}{mean:>14,.0f}"
              f"{f'[{lo:,.0f}, {hi:,.0f}]':>26}{f'{pos}/{neg}':>11}{verdict:>10}")

    print(f"\n  verdict key: PASS = interval excludes 0 AND every "
          f"opponent-by-seat cell agrees in sign (the pre-registered gate).")
    print(f"  CI-only = interval excludes 0 but the cells disagree -- does NOT "
          f"count; an interval alone has reversed an ordering here before.")
    npass = sum(1 for r in rows if r[7] == "PASS")
    print(f"\n  {npass} of {len(rows)} candidates pass the pre-registered gate")
    if wins:
        strong = [(o, w) for o, w in wins.items() if w[0]]
        print(f"  candidates with any win: {len(strong)} of {len(wins)}")
    print("STAGE2-READ-DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
