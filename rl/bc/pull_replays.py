#!/usr/bin/env python
"""Fetch and KEEP the replays behind the current tape library's lines.

tracelib pull digests a 29 MB replay into an 11 KB one-seat tape and
deletes it -- right for plan mining, wrong for imitation learning, which
needs (observation, action) pairs. This walks data/tracelib/index.json,
re-downloads each line's source episode from the daily dataset and
stores it gzipped under data/ilreplays/<episode>.json.gz. Replays carry
every step's observations for both seats, so no engine reconstruction
is needed downstream (and none is possible for pre-1.32.7 tapes anyway).

    source setup_env.sh
    python rl/bc/pull_replays.py            # everything in the library
    python rl/bc/pull_replays.py --limit 8  # pilot

Network + login-node friendly: one file at a time, resumable (skips
episodes already on disk), ~2-4 MB each on disk after gzip.
"""

import argparse
import gzip
import json
import os
import shutil
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, os.path.join(_REPO, "tools"))
from kaggle_cli import dataset_file, dataset_files  # noqa: E402

LIB = os.path.join(_REPO, "data", "tracelib", "index.json")
OUT = os.path.join(_REPO, "data", "ilreplays")
WORK = os.path.join(_REPO, "data", "tracelib", "work", "_ilpull")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="0 = all")
    args = ap.parse_args()

    with open(LIB) as f:
        lines = json.load(f)["lines"]
    wanted = {}                       # episode -> date
    for v in lines.values():
        wanted[v["episode"]] = v["date"]
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(WORK, exist_ok=True)

    by_date = {}
    for ep_id, d in sorted(wanted.items()):
        by_date.setdefault(d, []).append(ep_id)
    got = skipped = missing = 0
    for d, eps in sorted(by_date.items()):
        slug = f"kaggle/kaggriculture-episodes-{d}"
        names = None
        for ep_id in eps:
            out = os.path.join(OUT, f"{ep_id}.json.gz")
            if os.path.exists(out):
                skipped += 1
                continue
            if args.limit and got >= args.limit:
                break
            if names is None:
                names = set(dataset_files(slug))
            name = f"{ep_id}.json"
            if name not in names:
                missing += 1
                print(f"  {ep_id}: not in {d}'s dataset listing")
                continue
            path = dataset_file(slug, name, WORK)
            if not path:
                missing += 1
                continue
            with open(path, "rb") as fin, gzip.open(out, "wb", 6) as fout:
                shutil.copyfileobj(fin, fout)
            os.remove(path)
            got += 1
            print(f"  {ep_id} ({d}) -> {out} "
                  f"[{os.path.getsize(out) // 1024} KB]", flush=True)
    print(f"done: {got} fetched, {skipped} already on disk, {missing} missing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
