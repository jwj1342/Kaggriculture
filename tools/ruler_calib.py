#!/usr/bin/env python
"""Does BT-Elo over a fixed local field predict real ladder score?

The standing acceptance gate does not. docs/VALIDATING.md:59-72 records its
Spearman against the source teams' real ladder ratings as -0.05 (n=100), and it
ranked k01/k06 backwards by 266.3 points. Meanwhile the Kaggle prize is decided
by a single Bradley-Terry fit, which tools/tournament.py already computes -- so
the question is whether using the prize's own estimator, over a field
reconstructed from real ladder replays, actually orders our submissions the way
the ladder ordered them.

We can answer it because 17 submission snapshots on disk have a known real
ladder score (555.4 - 2302.2). This has been done once before for single
behavioural readouts (hands@20 rho +0.96, money only +0.73); it has never been
done for a TOURNAMENT-shaped ruler.

    python tools/ruler_calib.py [--shards data/shards/ruler-bt-v1]

Read this before reading any rho it prints
------------------------------------------
The ladder's own reproducibility is +-145 points: closercleo-term714, one
unchanged file, read 1363.7 on 08-11 and 1218.6 on 08-12. Under that noise
floor the engine family spans 77 points and the RL family 137 -- both
unresolvable -- so the ONLY within-family pair the ladder can actually
distinguish is k01 vs k06. Any rho here is therefore mostly measuring "can you
tell a tape replay from an RL net", which is easy and useless. The headline
number is concordance on resolvable pairs, and the must-pass is k01 > k06.

Why the tally is keyed on the full path and nothing is ingested
--------------------------------------------------------------
tournament.py's short(path) is the BASENAME and that is the BT key, so the 12
roster members named main.py would collapse into one ratings row. That is not
hypothetical: run #100 did exactly this, with `main` carrying 1,440 games =
4 x 360. It is also why duel101 and 14 other ablations were deliberately never
ingested (docs/RUNS.md:527-559). _play already writes full paths into the
JSONL, so the fix is to tally them there and never touch the database.
"""
import argparse
import glob
import json
import math
import os
import random
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from stats import bradley_terry          # noqa: E402  (used unmodified)
from tracefeat import rank, spearman     # noqa: E402  (tie-aware)

LADDER_NOISE = 145.0   # the term714 reread, 1363.7 -> 1218.6 on one file

# (path, submission id, real ladder score, family). Scores from README.md:385-397
# and docs/RUNS.md:8337-8345, both post-convergence reads. NOTE a real
# contradiction in the archive: docs/RUNS.md:3149-3151 labels topline 2035.9 and
# k06 2302.2, swapped relative to README.md:385-386, docs/RUNS.md:8337-8338 and
# docs/RUNS.md:9280-9281. The latter three agree, so they are used; the swap is
# named here so the choice is visible rather than buried.
ROSTER = [
    ("submissions/2026-08-21-sower-it228/main.py",       55668491,  555.4, "RL"),
    ("submissions/2026-08-21-anvil-samp/main.py",        55676605,  601.5, "RL"),
    ("submissions/2026-08-21-harrow-samp/main.py",       55673426,  610.1, "RL"),
    ("submissions/2026-08-07-barnyard/main.py",          55332339,  621.4, "engine"),
    ("submissions/2026-08-08-enhanced/main.py",          55358912,  623.6, "engine"),
    ("submissions/2026-08-22-hybrid-cleo12/main.py",     55688747,  692.2, "RL+tape"),
    ("submissions/2026-08-09-marketgarden/main.py",      55385371,  700.1, "engine"),
    ("submissions/2026-08-09-bigberry-fertgate/main.py", 55386857,  711.4, "engine"),
    ("submissions/2026-08-10-mgtight/main.py",           55402695,  759.9, "engine"),
    ("submissions/2026-08-11-mgtightgrain/main.py",      55418588,  767.4, "engine"),
    ("submissions/2026-08-09-bigberry-altwater/main.py", 55386385,  780.4, "engine"),
    ("submissions/2026-08-11-mgtight-here/main.py",      55431972,  818.4, "engine"),
    ("submissions/2026-08-10-mgtight-liq29/main.py",     55404837,  836.8, "engine"),
    ("submissions/2026-08-11-closercleo/main.py",        55439740, 1287.2, "cleo"),
    ("submissions/2026-08-11-closercleo-term714/main.py",55442784, 1363.7, "cleo"),
    ("agents/champ/k06.py",                              55489160, 2035.9, "tape"),
    ("agents/champ/k01.py",                              55484175, 2302.2, "tape"),
]
# the standing gate's exact ten (docs/VALIDATING.md:24), so the incumbent ruler
# is computed from the SAME episodes as the challenger -- paired, not a rerun
TIER_A = [f"agents/wrapped/w{n}.py" for n in
          ("39", "48", "16", "68", "56", "25", "12", "28", "05", "02")]


def load(shard_dir):
    rows = []
    for f in sorted(glob.glob(os.path.join(shard_dir, "shard-*.jsonl"))):
        with open(f) as fh:
            for line in fh:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    return rows


def tally(rows, keep_field=None):
    """wins/games keyed on FULL PATH; a tie is half to each side."""
    wins = defaultdict(float)
    games = defaultdict(float)
    for r in rows:
        if r["status"] != ["DONE", "DONE"]:
            continue
        a, b = r["left"], r["right"]
        if keep_field is not None:
            other = b if a in ROSTER_PATHS else a
            if other not in keep_field:
                continue
        ma, mb = r["money"]
        wins[(a, b)] += 1.0 if ma > mb else (0.5 if ma == mb else 0.0)
        wins[(b, a)] += 1.0 if mb > ma else (0.5 if ma == mb else 0.0)
        games[(a, b)] += 1.0
        games[(b, a)] += 1.0
    return wins, games


def bt_elo(wins, games, names, regularise=True):
    """BT strengths -> Elo referenced to the field median.

    regularise: add one virtual opponent at 0.5 wins / 1 game against every
    entrant (the Haldane half-count correction). BT diverges on a saturated
    field -- run #100's k01 went 360/360 and got a finite but arbitrary +1328,
    and stats.py guards only with max(v, 1e-12), so it never raises. With
    thousands of real games the shrinkage is ~0.03% for anyone unsaturated and
    decisive for anyone at 0 or 100%.
    """
    w, g, ns = dict(wins), dict(games), list(names)
    if regularise:
        ns = ns + ["_prior"]
        for n in names:
            w[(n, "_prior")] = w.get((n, "_prior"), 0.0) + 0.5
            w[("_prior", n)] = w.get(("_prior", n), 0.0) + 0.5
            g[(n, "_prior")] = g.get((n, "_prior"), 0.0) + 1.0
            g[("_prior", n)] = g.get(("_prior", n), 0.0) + 1.0
    p = bradley_terry(w, g, ns)
    vals = sorted(p[n] for n in names)
    med = vals[len(vals) // 2] or 1e-12
    return {n: 400.0 * math.log10(max(p[n], 1e-12) / med) for n in names}


def winrate(wins, games, who):
    gw = sum(v for (a, _b), v in games.items() if a == who)
    ww = sum(v for (a, _b), v in wins.items() if a == who)
    return (ww / gw) if gw else float("nan"), gw, ww


def concordance(xs, ys, noise):
    """Of the pairs the LADDER can resolve, what fraction does x order right?"""
    ok = tot = 0
    for i in range(len(ys)):
        for j in range(i + 1, len(ys)):
            if abs(ys[i] - ys[j]) < noise:
                continue
            tot += 1
            if (xs[i] - xs[j]) * (ys[i] - ys[j]) > 0:
                ok += 1
    return (ok / tot if tot else float("nan")), ok, tot


def boot_ci(xs, ys, iters=10000, seed=0):
    rng = random.Random(seed)
    n = len(xs)
    out = []
    for _ in range(iters):
        idx = [rng.randrange(n) for _ in range(n)]
        bx = [xs[i] for i in idx]
        by = [ys[i] for i in idx]
        if len(set(by)) > 2:
            out.append(spearman(bx, by))
    out.sort()
    if not out:
        return float("nan"), float("nan")
    return out[int(0.025 * len(out))], out[int(0.975 * len(out))]


ROSTER_PATHS = {p for p, *_ in ROSTER}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--shards", default="data/shards/ruler-bt-v1")
    a = ap.parse_args(argv)
    sd = a.shards if os.path.isabs(a.shards) else os.path.join(ROOT, a.shards)
    rows = load(sd)
    if not rows:
        sys.exit(f"no shard-*.jsonl under {sd}")
    errs = sum(1 for r in rows if r["status"] != ["DONE", "DONE"])
    print(f"{len(rows):,} episodes from {sd}   ({errs} non-DONE dropped)")

    field = sorted({(r["right"] if r["left"] in ROSTER_PATHS else r["left"])
                    for r in rows} - ROSTER_PATHS)
    print(f"field: {len(field)} opponents   roster: {len(ROSTER)} candidates")
    print(f"tier-A present: {sum(1 for t in TIER_A if t in field)}/10\n")

    names = [p for p, *_ in ROSTER] + field
    wF, gF = tally(rows)
    wA, gA = tally(rows, keep_field=set(TIER_A))
    eF = bt_elo(wF, gF, names)
    eA = bt_elo(wA, gA, [p for p, *_ in ROSTER] + TIER_A)
    eF_raw = bt_elo(wF, gF, names, regularise=False)

    money, hands = defaultdict(list), defaultdict(list)
    for r in rows:
        if r["status"] != ["DONE", "DONE"]:
            continue
        for side, who in ((0, r["left"]), (1, r["right"])):
            if who in ROSTER_PATHS:
                money[who].append(r["money"][side])
                h = ((r.get("digest") or [{}, {}])[side] or {}).get("hands") or {}
                if "20" in h:
                    hands[who].append(float(h["20"]))

    def med(v):
        v = sorted(v)
        return v[len(v) // 2] if v else float("nan")

    print(f"{'candidate':<40}{'ladder':>8}{'R1 winA':>9}{'R2 btA':>9}"
          f"{'R3 btF':>9}{'R4 med$':>10}{'R5 winF':>9}{'R6 h@20':>9}  sat")
    R = {k: [] for k in ("y", "R1", "R2", "R3", "R4", "R5", "R6")}
    tag = []
    for p, _sid, y, fam in ROSTER:
        r1, gA_n, _ = winrate(wA, gA, p)
        r5, gF_n, wF_n = winrate(wF, gF, p)
        sat = "SATURATED" if wF_n in (0.0, gF_n) else ""
        R["y"].append(y); R["R1"].append(r1); R["R2"].append(eA[p])
        R["R3"].append(eF[p]); R["R4"].append(med(money[p]))
        R["R5"].append(r5); R["R6"].append(med(hands[p]))
        tag.append((p, fam, sat))
        print(f"{os.path.basename(os.path.dirname(p))[:39]:<40}{y:>8.1f}"
              f"{r1*100:>8.1f}%{eA[p]:>9.0f}{eF[p]:>9.0f}{med(money[p]):>10,.0f}"
              f"{r5*100:>8.1f}%{med(hands[p]):>9.1f}  {sat}")

    print(f"\n{'ruler':<10}{'rho':>8}{'95% CI':>18}{'concordant':>13}  what it is")
    LABEL = {"R1": "the incumbent gate, verbatim (10 wrapped, win rate)",
             "R2": "BT over the incumbent's own ten",
             "R3": "BT over the full field  <- the challenger",
             "R4": "median money (the proxy; rho +0.73 on ladder digests)",
             "R5": "full-field win rate (the field-size control)",
             "R6": "hands@20, the best known ruler, never measured locally"}
    for k in ("R1", "R2", "R3", "R4", "R5", "R6"):
        xs = R[k]
        if any(x != x for x in xs):
            print(f"{k:<10}{'n/a':>8}   (missing values)")
            continue
        rho = spearman(xs, R["y"])
        lo, hi = boot_ci(xs, R["y"])
        c, ok, tot = concordance(xs, R["y"], LADDER_NOISE)
        print(f"{k:<10}{rho:>+8.3f}   [{lo:>+6.3f},{hi:>+6.3f}]"
              f"{c*100:>9.1f}% {ok}/{tot}  {LABEL[k]}")

    print(f"\nsanity: rho(R3 regularised, R3 raw) = "
          f"{spearman([eF[p] for p,*_ in ROSTER], [eF_raw[p] for p,*_ in ROSTER]):+.3f}"
          f"   (< 1.0 means saturation actually bit)")

    i1 = [i for i, (p, *_ ) in enumerate(ROSTER) if p.endswith("k01.py")][0]
    i6 = [i for i, (p, *_ ) in enumerate(ROSTER) if p.endswith("k06.py")][0]
    print(f"\nMUST-PASS  k01 (2302.2) vs k06 (2035.9) -- the only within-family "
          f"pair the ladder resolves")
    for k in ("R1", "R2", "R3", "R5", "R6"):
        d = R[k][i1] - R[k][i6]
        print(f"   {k}: {'k01 > k06  OK' if d > 0 else 'k01 < k06  WRONG WAY'} "
              f"(delta {d:+.3f})")

    fams = defaultdict(list)
    for (p, fam, _s), y in zip(tag, R["y"]):
        fams[fam].append(y)
    print("\nconfound, stated not buried: family membership nearly sorts y by "
          "itself, and only ONE pair is within-family resolvable")
    for fam, ys in sorted(fams.items(), key=lambda kv: min(kv[1])):
        span = max(ys) - min(ys)
        print(f"   {fam:<9} n={len(ys)}  {min(ys):>7.1f}-{max(ys):>7.1f}  "
              f"span {span:>6.1f}  {'RESOLVABLE' if span >= LADDER_NOISE else 'below the +-145 noise floor'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
