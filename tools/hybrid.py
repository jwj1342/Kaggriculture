#!/usr/bin/env python
"""Splice a recorded opening onto our engine, to measure what the opening is worth.

    python tools/hybrid.py agents/boot/<agent>.py --open agents/ref/closer_cleo.py \
        --days 4,8,12,16,20 --out agents/hybrid

The public meta is a single 720-turn action sequence indexed by `obs["step"]`
(see docs/ROADMAP.md §2). A day-by-day comparison puts our farm behind from day
1 and never recovering: at day 8 it holds $2,034 and 27 plants against our $306
and 8. The open question is *how much of the season's result is decided in that
window* -- and it is answerable without committing a week to a search.

The instrument: replay the recorded opening for the first N days, then hand the
board to our engine and let it play the rest. Sweep N. N=0 is our engine alone,
N=30 is the recording alone, and the curve between them is the value of the
opening, in dollars, measured rather than argued.

**This produces measuring instruments, not submissions.** The trace is
third-party and reconstructible from public replays; `agents/ref/NOTICE`
declines to claim a licence over it, 104 teams already run it, and the final
ranking is a Bradley-Terry tournament among submissions -- where a clone of the
modal agent draws 50% against the mode by construction. Keep these in
`agents/hybrid/`, which is git-ignored, and never snapshot one into
`submissions/`.

Handover is safe because `_plan` in `agents/_engine.py` holds no per-episode
state -- `_TO_FLOOR` is a pure memo -- so it reads the spliced board as it would
any other. Positional `hands` actions line up because the opening is replayed
from step 0, so the hand count is the one the recording itself hired.
"""

import argparse
import base64
import json
import os
import re
import sys
import zlib

TRACE_RE = re.compile(
    r"_TRACE\s*=\s*json\.loads\(\s*zlib\.decompress\(\s*base64\.b85decode\(\s*"
    r"['\"](.*?)['\"]\s*\)\s*\)[^)]*\)", re.S)

TAIL = '''

# --- spliced opening ---------------------------------------------------------
# Everything above is the generated agent, untouched. `_OPEN` is a recorded
# 720-turn action sequence; we replay its first {days} days ({handover} turns)
# and then hand the board back to the engine above.
import base64 as _b64
import copy as _copy
import json as _json
import zlib as _zlib

# The engine's own `agent` is parked in a *list*, not a name. `get_last_callable`
# returns `[v for v in env.values() if callable(v)][-1]`, and a plain
# `_INNER = agent` inserts a new callable *after* `agent` in the module dict --
# so the framework loads the engine and silently ignores the splice. Every
# handover day then scores identically and looks like "the opening is worth
# nothing". A list is not callable, so the redefined `agent` stays last.
_INNER = [agent]
_HANDOVER = {handover}
_ADOPT = {adopt}
_ADOPTED = []
_PASS = {{"farmer": ["PASS"], "hands": [], "market": []}}
_OPEN = _json.loads(_zlib.decompress(_b64.b85decode(
    {blob!r})).decode())


def _adopt(obs):
    """Raise the engine's targets to the farm it just inherited.

    The seed loop skips a crop once `have >= tgt`, and the targets are absolute
    counts: hand an engine configured for 16 strawberry a board carrying 41 and
    it will never replant one. Measured at a day-16 handover, the farm decays
    55 -> 49 -> 35 -> 23 -> 12 plants while the recording it came from holds
    32-42 over the same days. Without this, the sweep measures our target
    ceiling and calls it the value of the opening.
    """
    farm = (obs.get("farms") or [{{}}])[int(obs.get("player", 0) or 0)]
    crops, animals = {{}}, {{}}
    for row in farm.get("tiles") or []:
        for t in row:
            if isinstance(t, dict):
                if t.get("kind") == "PLANT":
                    crops[t["crop"]] = crops.get(t["crop"], 0) + 1
                elif "animal" in t:
                    animals[t["animal"]] = animals.get(t["animal"], 0) + 1
    plan = {{c: [c, tgt, ld] for (c, tgt, ld) in CONFIG["crops"]}}
    for c, n in crops.items():
        if c in plan:
            plan[c][1] = max(plan[c][1], n)
        else:                       # a crop the recording grows and we do not
            plan[c] = [c, n, CROPS[c]["max_yield_day"] + 15]
    CONFIG["crops"] = [plan[c] for c in plan]
    for a, n in animals.items():
        CONFIG["animals"][a] = max(CONFIG["animals"].get(a, 0), n)
    CONFIG["hands"] = max(CONFIG["hands"], len(farm.get("hands") or []))


# Same trap as `_INNER`, one level up: `def _adopt` binds a callable *after*
# `agent` in the module dict, so `get_last_callable` would load it instead. Park
# it in a list and drop the name.
_ADOPT_FN = [_adopt]
del _adopt


def agent(obs):
    try:
        i = int(obs.get("step", 0) or 0)
        if i < _HANDOVER:
            return _copy.deepcopy(_OPEN[i]) if 0 <= i < len(_OPEN) else _PASS
        if _ADOPT and not _ADOPTED:
            _ADOPTED.append(1)
            try:
                _ADOPT_FN[0](obs)
            except Exception:
                pass
        return _INNER[0](obs)
    except Exception:
        return _PASS
'''


def extract_trace_blob(path):
    src = open(path).read()
    m = TRACE_RE.search(src)
    if not m:
        raise SystemExit(f"{path}: no _TRACE blob found")
    blob = m.group(1)
    turns = json.loads(zlib.decompress(base64.b85decode(blob)).decode())
    return blob, turns


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("agent", help="a generated agent whose last callable is `agent`")
    ap.add_argument("--open", dest="opener", default="agents/ref/closer_cleo.py")
    ap.add_argument("--days", default="0,4,8,12,16,20",
                    help="handover days to emit, comma separated")
    ap.add_argument("--out", default="agents/hybrid")
    ap.add_argument("--adopt", action="store_true",
                    help="at handover, raise crop/herd/hand targets to the "
                         "inherited board (see _adopt); without it the sweep "
                         "measures our target ceiling, not the opening")
    a = ap.parse_args()

    blob, turns = extract_trace_blob(a.opener)
    base = open(a.agent).read()
    stem = os.path.splitext(os.path.basename(a.agent))[0]
    opener = os.path.splitext(os.path.basename(a.opener))[0]
    os.makedirs(a.out, exist_ok=True)
    print(f"opening: {opener} ({len(turns)} turns)   engine: {stem}")

    for d in [int(x) for x in a.days.split(",")]:
        handover = d * 24
        if d == 0:                       # N=0 is the engine alone: copy it as-is
            out = os.path.join(a.out, f"{stem}--n00.py")
            open(out, "w").write(base)
        else:
            tag = "a" if a.adopt else ""
            out = os.path.join(a.out, f"{stem}--{opener}-n{d:02d}{tag}.py")
            src = base + TAIL.format(days=d, handover=handover, blob=blob,
                                     adopt=bool(a.adopt))
            compile(src, out, "exec")    # never ship a file that silently PASSes
            open(out, "w").write(src)
            _verify(src, out, turns, handover)
        print(f"  day {d:>2} -> {out}")
    return 0


def _verify(src, out, turns, handover):
    """Load it the way the framework does and prove the splice is live.

    Compiling is not enough: a file can compile, load, and quietly run the
    *wrong* function. Ask for step 0 and step `handover`, and require the first
    to come from the recording and the second not to.
    """
    from kaggle_environments.agent import get_last_callable
    fn = get_last_callable(src, path=out)
    if fn.__name__ != "agent":
        raise SystemExit(f"{out}: framework would load {fn.__name__}, not agent")
    got = fn({"step": 0})
    if got != turns[0]:
        raise SystemExit(f"{out}: step 0 is not the recorded opening -- splice inert")
    if fn({"step": handover}) == turns[handover]:
        raise SystemExit(f"{out}: still replaying at step {handover} -- no handover")


if __name__ == "__main__":
    sys.exit(main())
