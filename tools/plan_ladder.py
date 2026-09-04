#!/usr/bin/env python
"""Rank mined plans by the *ladder scores of the teams that play them*.

    python tools/plan_ladder.py --top 20

Every local ruler this project has calibrated is measured-unusable at the top of
the field.  `docs/VALIDATING.md`'s 2026-09-02 section: on the 13 candidates below
900 the 20-opponent full-field win rate is ρ=+0.880 and orders 23/23 resolvable
pairs correctly, but on the one resolvable pair at the top -- k01 (2302.2) vs k06
(2035.9) -- *five of five* rulers, money included, rank them backwards.  Picking a
top-tier plan by local simulation therefore has no measured support.

So this ruler does not simulate at all.  A mined plan is an action log lifted off
a real ladder episode, and the trace library records which teams were seen
playing it.  Those teams have public ladder scores.  Reading the plan's quality
off its players' scores is the ladder's own revealed preference, and it is valid
exactly where the local rulers fail: at the top.

What it cannot do, stated up front:

* **Popularity is not strength.**  A widely-copied public notebook shows up on
  many teams of every rank.  That is why the headline is the score *distribution*
  of the players, never the sighting count -- and why `--min-teams` exists.
* **A team's score is not this plan's score.**  Teams submit more than once
  (`SubmissionCount` is in the CSV) and a team seen playing a plan may have
  scored with a different one.  The reading is an upper envelope on the cohort,
  not an estimate of the plan.
* **It says nothing about how a plan behaves under *our* wrapper**, which is the
  thing we would actually submit.  It ranks plans; the wrapper's contribution is
  a separate, paired measurement.

Ladder noise floor is +/-145 (`closercleo-term714`, same file, 1363.7 -> 1218.6
in one day), so cohort gaps under that are not readings.
"""
import argparse, csv, io, json, os, statistics, sys, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_board(path):
    """team name -> (rank, score).  Accepts the zip Kaggle hands back, or a csv."""
    if path.endswith(".zip"):
        z = zipfile.ZipFile(path)
        names = [n for n in z.namelist() if n.endswith(".csv")]
        if not names:
            sys.exit(f"no csv inside {path}")
        raw = z.read(names[0]).decode("utf-8-sig")
        stamp = names[0]
    else:
        raw = open(path, encoding="utf-8-sig").read()
        stamp = os.path.basename(path)
    board = {}
    for row in csv.DictReader(io.StringIO(raw)):
        row = {k.lstrip("﻿"): v for k, v in row.items()}
        board[row["TeamName"]] = (int(row["Rank"]), float(row["Score"]),
                                  int(row["SubmissionCount"]))
    return board, stamp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", default="data/tracelib/index.json")
    ap.add_argument("--board", default="data/ladder/kaggriculture.zip")
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--min-teams", type=int, default=2,
                    help="a plan seen on only one team is one team's private line, "
                         "and its cohort statistics are that one number")
    ap.add_argument("--by", choices=("best", "median", "count"), default="best",
                    help="best = highest-scoring team that plays it (an envelope); "
                         "median = the cohort's middle; count = sightings")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    board, stamp = load_board(os.path.join(ROOT, args.board))
    idx = json.load(open(os.path.join(ROOT, args.index)))
    print(f"  board {stamp}: {len(board)} teams, "
          f"top {max(s for _, s, _ in board.values()):,.1f}")

    rows = []
    unmatched = set()
    for lid, v in idx["lines"].items():
        scores, ranks, named = [], [], []
        for t in v["teams"]:
            if t in board:
                r, s, _ = board[t]
                scores.append(s); ranks.append(r); named.append((s, t))
            else:
                unmatched.add(t)
        if len(scores) < args.min_teams:
            continue
        named.sort(reverse=True)
        rows.append(dict(line=lid, seen=v["count"], nteams=len(v["teams"]),
                         matched=len(scores), best=max(scores),
                         median=statistics.median(scores), best_rank=min(ranks),
                         best_team=named[0][1], money=v["best_score"],
                         date=v["day"] if "day" in v else v.get("date", "?"),
                         episode=v["episode"], seat=v["seat"], seed=v.get("seed")))

    key = {"best": lambda r: -r["best"], "median": lambda r: -r["median"],
           "count": lambda r: -r["seen"]}[args.by]
    rows.sort(key=key)
    print(f"  {len(rows)} plans with >={args.min_teams} teams on the board "
          f"({len(idx['lines'])} total, {len(unmatched)} team names unmatched)\n")
    print(f"  {'line':<14}{'seen':>5}{'teams':>6}{'best LB':>9}{'rank':>6}"
          f"{'median':>8}{'best $':>10}  best-scoring team")
    for r in rows[:args.top]:
        print(f"  {r['line'][:12]:<14}{r['seen']:>5}{r['matched']:>6}"
              f"{r['best']:>9.1f}{r['best_rank']:>6}{r['median']:>8.1f}"
              f"{r['money']:>10,.0f}  {r['best_team'][:28]}")
    if args.json:
        json.dump(rows, open(args.json, "w"), indent=1)
        print(f"\n  -> {args.json}  ({len(rows)} rows)")


main()
