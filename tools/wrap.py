#!/usr/bin/env python
"""Put the same adaptive layer around each mined plan, so they can be compared.

    python tools/wrap.py --top 10 --out agents/wrapped

A recorded plan on its own is one player's 720-turn action log. Replayed
anywhere but the board it was recorded on, a large share of its actions become
silent no-ops and it collapses -- which is why a round robin of *bare*
recordings against one wrapped agent measures the wrapper, not the plans. That
mistake produced a "91.7%, beats all twelve" result for an agent sitting at
1,352 on a ladder whose top is 3,180.

So every plan gets the same layer: `agents/ref/closer_cleo.py` minus its own
plan. What that layer actually does, measured (`docs/ROADMAP.md` §4):

* `_terminal_action` -- from step 714, a board-reading harvest/carry/sell
  controller replaces the plan entirely for the last six turns
* `_terminal_liquidation` -- from step 680, whatever is in the shed gets listed
* sell ordering -- the most valuable sale takes the earliest market slot

The parts that would *not* transplant are already dead in the donor: `_SUPPLY`
is a self-play supply table read only by `_reserve_price`, which is only called
for items in `_RESERVE`, and `_RESERVE` is empty. `_front_run` reads the plan's
next turn, so it transplants correctly, and in any case never fires -- the
agent holds no shed inventory between turns.

The result is a fair field: every agent has the same wrapper, so a win is about
the plan.

TWO THINGS MEASURED ABOUT THIS SELECTION, 2026-08-13 -- read before trusting a
number that came out of a field built here.

1. `--top` sorts by sighting count, and that ordering runs out early. Of the 347
   plans clearing `--min-score`, only 57 have `count >= 2`; the remaining 290 are
   tied at one sighting, so `--top 100` fills its last 43 seats in whatever order
   the dict happens to iterate. Selecting the same 247 leftovers by best
   single-episode money instead (`agents/darkhorse/`) put 18 of 40 above the old
   field's tenth-place threshold. The frequency filter was mostly not a filter.

2. A win here does not mean the plan is good. Checked against the source teams'
   real ladder ratings across all 100 plans: spearman -0.05, n=100 -- no relation
   at all, and one team's own episodes span 14% to 93% locally. What this field
   measures is whether a recording still functions on an unfamiliar board.
   `docs/ROADMAP.md` §10.5.

Neither is fixed here on purpose: changing the selection would silently
invalidate every comparison already recorded against a field built by the old
one. Fix it deliberately, rebuild, and say so in `docs/RUNS.md`.
"""

import argparse
import base64
import gzip
import json
import os
import re
import sys
import zlib

DONOR = "agents/ref/closer_cleo.py"
TRACE_RE = re.compile(
    r"(_TRACE = json\.loads\(zlib\.decompress\(base64\.b85decode\(\s*')(.*?)('\s*\)\))",
    re.S)


def _repack(turns):
    """b85(zlib(json)) -- the donor's own encoding, so only the payload changes."""
    return base64.b85encode(zlib.compress(json.dumps(turns).encode(), 9)).decode()


def build(turns, donor_src, terminal_at=714):
    m = TRACE_RE.search(donor_src)
    if not m:
        raise SystemExit(f"{DONOR}: no _TRACE blob to replace")
    out = donor_src[:m.start(2)] + _repack(turns) + donor_src[m.end(2):]
    out = out.replace("    if step >= 717:\n        return _terminal_action(obs)",
                      f"    if step >= {terminal_at}:\n        return _terminal_action(obs)")
    return out


def verify(src, path, turns):
    """Load it the way the framework will and make it answer a known question."""
    from kaggle_environments.agent import get_last_callable
    fn = get_last_callable(src, path=path)
    if fn.__name__ != "agent":
        raise SystemExit(f"{path}: framework would load {fn.__name__}")
    got = fn({"step": 0})
    want = turns[0]
    if got.get("farmer") != want.get("farmer"):
        raise SystemExit(f"{path}: step 0 is {got.get('farmer')}, "
                         f"the plan says {want.get('farmer')} -- transplant failed")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", default="data/tracelib/index.json")
    ap.add_argument("--out", default="agents/wrapped")
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--min-score", type=float, default=50000)
    ap.add_argument("--terminal-at", type=int, default=714)
    a = ap.parse_args()

    donor = open(DONOR).read()
    idx = json.load(open(a.index))
    rows = [(k, v) for k, v in idx["lines"].items() if v["best_score"] >= a.min_score]
    rows.sort(key=lambda kv: -kv[1]["count"])
    os.makedirs(a.out, exist_ok=True)
    for f in os.listdir(a.out):
        if f.endswith(".py"):
            os.remove(os.path.join(a.out, f))

    man = {}
    for i, (lid, v) in enumerate(rows[:a.top], 1):
        turns = json.loads(gzip.decompress(base64.b64decode(v["turns"])).decode())
        name = f"w{i:02d}"
        path = os.path.join(a.out, name + ".py")
        src = build(turns, donor, a.terminal_at)
        compile(src, path, "exec")
        with open(path, "w") as f:
            f.write(src)
        verify(src, path, turns)
        man[name] = {k: v[k] for k in ("count", "teams", "best_score", "date")
                     if k in v}
        print(f"  {path}  plan seen {v['count']}x across {len(v['teams'])} teams, "
              f"best ${v['best_score']:,.0f}")
    with open(os.path.join(a.out, "manifest.json"), "w") as f:
        json.dump(man, f, indent=1, sort_keys=True)
    print(f"\n  {len(man)} plans, one shared wrapper -- now a win is about the plan")
    return 0


if __name__ == "__main__":
    sys.exit(main())
