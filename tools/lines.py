#!/usr/bin/env python
"""Cluster the recorded ladder trajectories into the distinct *lines* they play.

    python tools/lines.py                      # report the clusters
    python tools/lines.py --emit agents/lines  # write one representative each

The top of the ladder is a monoculture, but not of the plan embedded in
`agents/ref/`: aligned within +-8 turns, only 8 of 156 recorded trajectories
overlap `closer_cleo`'s `_TRACE` above 30%, while the recordings match *each
other* at a median of 75.4% with half of all pairs above 90%. Comparing turn by
turn without the alignment gives 0% for plans that are identical two turns
apart, which is how that went unnoticed.

What the clusters are for:

* **A panel opponent at the right strength.** `agents/bench3` has nothing
  between "we beat it 90% of the time" and "we lose 99.8% of the time". The
  largest cluster's representative sits at 66.6% against that panel, just above
  our best engine's 60.9% — the most informative opponent available to us.
* **Knowing which line is which.** The most-played line is not the strongest.
  Cluster 1 is 97 of 156 recordings across 38 teams with a median original score
  of $78,510; cluster 2 is ten recordings from ten teams at $132,032.

And the thing to remember before copying any of them: replayed on seeds they
never saw, cluster 1 holds 66.6% but cluster 2 collapses to 11.8% and cluster 3
to 0.9%. These are open-loop recordings — different weeds and a different
opponent turn their actions into silent no-ops. **The most-played line is the
most robust one, not the best one**, and a raw recording scores 0.0% against
every agent that wraps a plan in an adaptive layer.
"""

import argparse
import base64
import glob
import gzip
import json
import os
import re
import shutil
import sys

TURNS_RE = re.compile(
    r'_TURNS = json\.loads\(gzip\.decompress\(base64\.b64decode\(\s*'
    r'["\'](.*?)["\']\s*\)\)', re.S)


def signature(path):
    m = TURNS_RE.search(open(path).read())
    if not m:
        return None
    turns = json.loads(gzip.decompress(base64.b64decode(m.group(1))).decode())
    return [json.dumps([t.get("farmer"), t.get("hands")], sort_keys=True)
            for t in turns]


def overlap(a, b, span=8):
    """Best turn-by-turn agreement over shifts of +-`span`.

    The shift is the whole point: two farms playing the same plan one turn apart
    agree on nothing at all when compared index to index.
    """
    n = min(len(a), len(b)) - span
    best = 0
    for s in range(-span, span + 1):
        best = max(best, sum(1 for i in range(span, n) if a[i] == b[i + s]))
    return best / (n - span)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ghosts", default="agents/ghosts")
    ap.add_argument("--threshold", type=float, default=0.85)
    ap.add_argument("--emit", metavar="DIR",
                    help="write the top clusters' best-scoring representative")
    ap.add_argument("--top", type=int, default=4)
    a = ap.parse_args()

    paths = sorted(glob.glob(os.path.join(a.ghosts, "*.py")))
    sigs = {p: s for p in paths if (s := signature(p))}
    if not sigs:
        raise SystemExit(f"no decodable ghosts in {a.ghosts} "
                         f"-- run tools/fetch_fields.sh ghosts")
    man = json.load(open(os.path.join(a.ghosts, "manifest.json")))
    by_ep = {v["episode"]: v for v in man.values()}

    def meta(p):
        return by_ep.get(int(re.search(r"ghost-(\d+)-", p).group(1)), {})

    left, clusters = list(sigs), []
    while left:                      # greedy: seed on the first unassigned
        seed = left[0]
        grp = [q for q in left if overlap(sigs[seed], sigs[q]) > a.threshold]
        clusters.append(grp)
        left = [q for q in left if q not in grp]
    clusters.sort(key=len, reverse=True)

    print(f"{len(sigs)} trajectories -> {len(clusters)} lines "
          f"(agreement > {a.threshold:.0%}, aligned within +-8 turns)\n")
    print(f"{'line':>5}{'traces':>8}{'teams':>7}{'median $':>11}{'best $':>11}  representative")
    for i, c in enumerate(clusters[:a.top]):
        scores = sorted(m.get("original_score", 0) for m in map(meta, c))
        rep = max(c, key=lambda p: meta(p).get("original_score", 0))
        print(f"{i+1:>5}{len(c):>8}{len({meta(p).get('team') for p in c}):>7}"
              f"{scores[len(scores)//2]:>11,.0f}{scores[-1]:>11,.0f}  "
              f"{os.path.basename(rep)}")

    if a.emit:
        os.makedirs(a.emit, exist_ok=True)
        print()
        for i, c in enumerate(clusters[:a.top]):
            rep = max(c, key=lambda p: meta(p).get("original_score", 0))
            dst = os.path.join(a.emit, f"line{i+1}.py")
            shutil.copy(rep, dst)
            print(f"  wrote {dst}  ({len(c)} traces, {meta(rep).get('team')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
