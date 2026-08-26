#!/usr/bin/env python
"""Statistically honest A/B evaluation for Kaggriculture agents.

Why this exists
---------------
The ladder scores on **win/loss only**, and seed-to-seed spread in this
environment is larger than almost any tuning effect. Early sweeps in this repo
produced contradictory orderings on repeat runs at 3-4 seeds. Anything that
reports a single mean over a handful of games is noise.

Three things this harness does that a naive loop does not:

1. **Swaps seats.** Every seed is played twice, once with the candidate as
   player 0 and once as player 1, so a seat advantage cannot masquerade as skill.
2. **Reports intervals, not points.** Win rate gets a Wilson interval; the money
   margin gets a paired bootstrap. If the interval straddles zero, the result is
   "we do not know yet" -- which is usually the truth.
3. **Says how many games you would need.** Every run prints the sample size
   required to resolve the effect you are looking for.

Two caveats specific to this engine, both measured:

* Episodes are deterministic given `(seed, both agents)`, so re-running the same
  pair on the same seed adds no information -- variance lives across seeds only.
* Common random numbers do **not** fully control the environment. `_end_of_day`
  draws weeds and the shop unlock from one shared RNG, and the weed draws
  consume a number of values that depends on how many empty tiles *both* farms
  have. Changing your agent therefore changes which shops unlock. Pairing on
  seed still helps, but it does not cancel environment variance the way it would
  in a normal simulation study.

Modes
-----
    # direct head-to-head: estimate P(A beats B)
    python tools/eval.py h2h agents/v2.py agents/barnyard.py --seeds 64 -j 32

    # both candidates against a common opponent pool (closer to the ladder)
    python tools/eval.py pool agents/v2.py agents/barnyard.py \
        --vs starter --vs agents/barnyard.py --seeds 32 -j 32
"""

import argparse
import json
import math
import os
import random
import statistics
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stats import wilson


# --------------------------------------------------------------------------
# statistics
# --------------------------------------------------------------------------


def bootstrap_mean(xs, iters=5000, alpha=0.05, seed=0):
    if not xs:
        return (0.0, 0.0, 0.0)
    rng = random.Random(seed)
    n = len(xs)
    means = []
    for _ in range(iters):
        means.append(sum(xs[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    lo = means[int(iters * alpha / 2)]
    hi = means[int(iters * (1 - alpha / 2)) - 1]
    return (statistics.mean(xs), lo, hi)


def games_needed(delta_pp, z=1.96):
    """Games to resolve a win-rate delta of `delta_pp` points from 50%."""
    d = delta_pp / 100.0
    if d <= 0:
        return float("inf")
    return math.ceil((z * z * 0.25) / (d * d))


def _interval_winner(lo, hi):
    """Return the resolved side for a Wilson interval expressed in percent."""
    if lo > 50.0:
        return "A"
    if hi < 50.0:
        return "B"
    return None


def _win_score(wins, ties):
    """Competition score contribution: a tie is half a win for each side."""
    return wins + 0.5 * ties


# --------------------------------------------------------------------------
# episode runner
# --------------------------------------------------------------------------

def _play(job):
    left, right, seed, steps, tag = job
    from kaggle_environments import make

    env = make("kaggriculture", configuration={"episodeSteps": steps, "seed": seed})
    env.run([left, right])
    final = env.steps[-1]
    money = [float(s.reward or 0) for s in final]
    status = [str(s.status) for s in final]
    shops = list(env.steps[-1][0].observation["town"]["unlocked_shops"])
    return {"tag": tag, "seed": seed, "money": money, "status": status, "shops": shops}


def run_matches(pairs, jobs):
    if jobs > 1:
        with ProcessPoolExecutor(max_workers=jobs) as ex:
            return list(ex.map(_play, pairs))
    return [_play(p) for p in pairs]


def _summarise(name, records, label=""):
    """records: list of (my_money, their_money, seat)."""
    n = len(records)
    wins = sum(1 for a, b, _ in records if a > b)
    ties = sum(1 for a, b, _ in records if a == b)
    score = _win_score(wins, ties)
    margins = [a - b for a, b, _ in records]
    lo, hi = wilson(score, n)
    p = score / n if n else 0.0
    m, mlo, mhi = bootstrap_mean(margins)
    mine = [a for a, _, _ in records]

    print(f"  {name}{label}")
    print(f"    games      {n}   ({wins}W {n - wins - ties}L {ties}T)")
    print(f"    win rate   {p:6.1%}   95% CI [{lo:.1f}%, {hi:.1f}%]")
    print(f"    margin     {m:+12,.0f}   95% CI [{mlo:+,.0f}, {mhi:+,.0f}]")
    print(f"    own money  median {statistics.median(mine):,.0f}"
          f"   sd {statistics.pstdev(mine):,.0f}"
          f"   range [{min(mine):,.0f}, {max(mine):,.0f}]")
    for seat in (0, 1):
        sub = [(a, b) for a, b, s in records if s == seat]
        if sub:
            w = sum(1 for a, b in sub if a > b)
            t = sum(1 for a, b in sub if a == b)
            score = _win_score(w, t)
            print(f"    as player {seat}: {w}W {len(sub) - w - t}L {t}T "
                  f"= {score / len(sub):.0%}")
    return {"n": n, "wins": wins, "ties": ties, "score": score,
            "winrate": p, "ci": [lo, hi],
            "margin": m, "margin_ci": [mlo, mhi],
            "median_money": statistics.median(mine)}


def _paired_pool_summary(results):
    """Compare pool candidates on matched opponent/seed/seat cells.

    The four observations from one seed are correlated, so confidence
    intervals bootstrap seed-level means rather than pretending every seat
    and opponent is an independent draw.
    """
    cells = defaultdict(dict)
    for record in results:
        candidate, opponent, seat_text = record["tag"].split("|")
        seat = int(seat_text)
        mine, theirs = ((record["money"][0], record["money"][1]) if seat == 0
                        else (record["money"][1], record["money"][0]))
        cells[(int(record["seed"]), opponent, seat)][candidate] = (mine, theirs)

    rows = []
    for (seed, opponent, seat), cell in cells.items():
        if set(cell) != {"0", "1"}:
            raise ValueError(
                f"incomplete candidate pair for seed={seed} opponent={opponent} "
                f"seat={seat}: {sorted(cell)}")
        am, ao = cell["0"]
        bm, bo = cell["1"]
        aw = float(am > ao) + 0.5 * float(am == ao)
        bw = float(bm > bo) + 0.5 * float(bm == bo)
        rows.append({
            "seed": seed,
            "opponent": opponent,
            "seat": seat,
            "margin": (am - ao) - (bm - bo),
            "money": am - bm,
            "opponent_money": ao - bo,
            "win": aw - bw,
        })

    def summarise(subset):
        by_seed = defaultdict(lambda: defaultdict(list))
        for row in subset:
            for metric in ("margin", "money", "opponent_money", "win"):
                by_seed[row["seed"]][metric].append(row[metric])
        out = {"n": len(subset), "seed_clusters": len(by_seed)}
        for metric in ("margin", "money", "opponent_money", "win"):
            cluster_means = [statistics.mean(values[metric])
                             for values in by_seed.values()]
            mean, lo, hi = bootstrap_mean(cluster_means)
            out[metric] = {"mean": mean, "ci95": [lo, hi]}
        return out

    opponents = sorted({row["opponent"] for row in rows})
    return {
        "all": summarise(rows),
        "by_opponent": {
            opponent: summarise([row for row in rows
                                 if row["opponent"] == opponent])
            for opponent in opponents
        },
    }


# --------------------------------------------------------------------------
# modes
# --------------------------------------------------------------------------

def mode_h2h(args):
    pairs = []
    for i in range(args.seeds):
        s = args.seed0 + i
        pairs.append((args.a, args.b, s, args.steps, "A0"))   # A as player 0
        pairs.append((args.b, args.a, s, args.steps, "A1"))   # A as player 1
    res = run_matches(pairs, args.jobs)

    records, errors = [], []
    for r in res:
        if any(st not in ("DONE",) for st in r["status"]):
            errors.append(r)
        if r["tag"] == "A0":
            records.append((r["money"][0], r["money"][1], 0))
        else:
            records.append((r["money"][1], r["money"][0], 1))

    print(f"\nA = {args.a}")
    print(f"B = {args.b}")
    print(f"{args.seeds} seeds x 2 seats = {len(records)} episodes\n")
    if errors:
        print(f"  !! {len(errors)} episodes did not finish cleanly: "
              f"{[e['status'] for e in errors][:4]}\n")
    summary = _summarise("A vs B", records)

    print()
    lo, hi = summary["ci"]
    winner = _interval_winner(lo, hi)
    if winner == "A":
        print("  VERDICT: A is better (interval entirely above 50%).")
    elif winner == "B":
        print("  VERDICT: B is better (interval entirely below 50%).")
    else:
        width = hi - lo
        print(f"  VERDICT: not resolved -- interval is {width:.0f} points wide and "
              f"contains 50%.")
        for d in (10, 5, 3):
            print(f"           to resolve a {d:>2}pp edge you need "
                  f"~{games_needed(d):,} episodes ({games_needed(d)//2:,} seeds)")

    if args.out:
        _dump(args.out, {"mode": "h2h", "a": args.a, "b": args.b,
                         "summary": summary, "episodes": res})
    return summary


def mode_pool(args):
    pool = args.vs or ["starter"]
    pairs = []
    for cand_i, cand in enumerate((args.a, args.b)):
        for opp in pool:
            for i in range(args.seeds):
                s = args.seed0 + i
                pairs.append((cand, opp, s, args.steps, f"{cand_i}|{opp}|0"))
                pairs.append((opp, cand, s, args.steps, f"{cand_i}|{opp}|1"))
    res = run_matches(pairs, args.jobs)

    by_cand = defaultdict(list)
    by_cand_opp = defaultdict(list)
    for r in res:
        ci, opp, seat = r["tag"].split("|")
        seat = int(seat)
        mine, theirs = (r["money"][0], r["money"][1]) if seat == 0 else (r["money"][1], r["money"][0])
        by_cand[ci].append((mine, theirs, seat))
        by_cand_opp[(ci, opp)].append((mine, theirs, seat))

    print(f"\nA = {args.a}")
    print(f"B = {args.b}")
    print(f"pool = {pool}")
    print(f"{args.seeds} seeds x {len(pool)} opponents x 2 seats "
          f"x 2 candidates = {len(res)} episodes\n")

    summaries = {}
    for ci, name in (("0", "A"), ("1", "B")):
        summaries[name] = _summarise(name, by_cand[ci], " vs pool")
        for opp in pool:
            recs = by_cand_opp[(ci, opp)]
            w = sum(1 for a, b, _ in recs if a > b)
            t = sum(1 for a, b, _ in recs if a == b)
            score = _win_score(w, t)
            print(f"       vs {opp:32s} {w}W {len(recs) - w - t}L {t}T "
                  f"= {score / len(recs):.0%}")
        print()

    da = summaries["A"]["winrate"] - summaries["B"]["winrate"]
    print(f"  A - B win rate against the pool: {da:+.1%}")
    print(f"  (CIs: A {summaries['A']['ci'][0]:.1f}%-{summaries['A']['ci'][1]:.1f}%, "
          f"B {summaries['B']['ci'][0]:.1f}%-{summaries['B']['ci'][1]:.1f}%)")
    if summaries["A"]["ci"][0] > summaries["B"]["ci"][1]:
        print("  VERDICT: A is better.")
    elif summaries["B"]["ci"][0] > summaries["A"]["ci"][1]:
        print("  VERDICT: B is better.")
    else:
        print("  VERDICT: intervals overlap -- not resolved.")

    paired = _paired_pool_summary(res)
    summaries["paired"] = paired
    overall = paired["all"]
    margin = overall["margin"]
    money = overall["money"]
    opponent_money = overall["opponent_money"]
    win = overall["win"]
    print(f"\n  Paired A - B over {overall['seed_clusters']} seed clusters:")
    print(f"    margin       {margin['mean']:+12,.0f}   "
          f"95% CI [{margin['ci95'][0]:+,.0f}, {margin['ci95'][1]:+,.0f}]")
    print(f"    own money    {money['mean']:+12,.0f}   "
          f"95% CI [{money['ci95'][0]:+,.0f}, {money['ci95'][1]:+,.0f}]")
    print(f"    opponent     {opponent_money['mean']:+12,.0f}   "
          f"95% CI [{opponent_money['ci95'][0]:+,.0f}, "
          f"{opponent_money['ci95'][1]:+,.0f}]")
    print(f"    win delta    {win['mean']:+12.1%}   "
          f"95% CI [{win['ci95'][0]:+.1%}, {win['ci95'][1]:+.1%}]")
    for opponent, row in paired["by_opponent"].items():
        effect = row["margin"]
        print(f"       vs {opponent:32s} {effect['mean']:+,.0f} "
              f"[{effect['ci95'][0]:+,.0f}, {effect['ci95'][1]:+,.0f}]")

    if args.out:
        _dump(args.out, {"mode": "pool", "a": args.a, "b": args.b, "pool": pool,
                         "summary": summaries, "episodes": res})
    return summaries


def _dump(path, payload):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"\n  wrote {path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["h2h", "pool"])
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--vs", action="append", default=None,
                    help="pool mode: opponent (repeatable)")
    ap.add_argument("--seeds", type=int, default=32)
    ap.add_argument("--seed0", type=int, default=10_000)
    ap.add_argument("-s", "--steps", type=int, default=720)
    ap.add_argument("-j", "--jobs", type=int, default=4)
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args()

    if args.mode == "h2h":
        mode_h2h(args)
    else:
        mode_pool(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
