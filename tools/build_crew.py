"""Give a PASSing hand a second chance at AUTO. No retraining.

Why (docs/RUNS.md 2026-08-23). Our net's hands do productive work on 11.5% of
their turns against k06's 38.8%, at a comparable crew size (7.8 against 8.6), and
the whole difference is PASS: 2,763 hand-PASSes against 584. And 96% of ours
happen while real work is sitting on the board -- 2,048 unwatered plants, 1,223
unharvested, 987 unfed animals, 849 uncared.

The mechanism this tests: the 12 hand heads are conditionally independent given
the state, so nothing stops them all choosing the same family. rl/actions.py
claims targets in hand order and "a task whose family has no target left PASSes",
so the first few hands take the available tiles and the rest stand still even
though other families have work. That is a coordination failure, not a shortage.

So: decode with the net's own tasks, find the hands that came out PASS, retry
those at AUTO, and decode once more. AUTO claims from every family it handles
(HARVEST / WATER / CARE / COLLECT_FERTILIZER / DIG) with the same in-order
claiming, so the spilled hands fill in behind the ones that got a target. The
net's PLANT / FEED / FERTILIZE choices are preserved for hands that did get work,
which matters because AUTO deliberately never plants -- forcing every hand to AUTO
would stop the farm planting at all.

If this recovers a large share of the production gap, the collision is real and
the fix belongs in training (the hand heads need to see each other's picks, or be
decoded autoregressively). If it does not, PASS is downstream of the small farm
and the hand head is not the constraint.

    python tools/build_crew.py <export-or-hybrid-dir> <out-dir>

Inserted INSIDE _act rather than wrapped around the agent: CLAUDE.md's loader
takes the LAST callable bound at module level, so wrapping `agent` and leaving the
original bound after it loads the unwrapped one and every variant scores
identically with no error.
"""
import os
import re
import shutil
import sys

src_dir, out_dir = sys.argv[1], sys.argv[2]
os.makedirs(out_dir, exist_ok=True)
for f in os.listdir(src_dir):
    if f == "__pycache__":
        continue
    s = os.path.join(src_dir, f)
    if os.path.isfile(s):
        shutil.copy(s, os.path.join(out_dir, f))

main = os.path.join(out_dir, "main.py")
src = open(main).read()

# _act's multi-head tail, which we replace with a decode-retry-decode
old_tail = """    tasks = [_pick(row) for row in hlog]
    return _A.decode_multi(obs_dict, _pick(flog), tasks, _pick(mlog))"""
if old_tail not in src:
    sys.exit("could not find the decode_multi tail in _act -- refusing to emit an "
             "agent whose spill silently never fires")

new_tail = """    tasks = [_pick(row) for row in hlog]
    _f, _m = _pick(flog), _pick(mlog)
    act = _A.decode_multi(obs_dict, _f, tasks, _m)
    # ---- crew spill (tools/build_crew.py) --------------------------------
    # The hand heads pick independently, so they pile onto one family; targets
    # are claimed in hand order and a family with none left PASSes. 96% of this
    # net's 2,763 hand-PASSes happen with work still on the board. Retry the
    # PASSing hands at AUTO, which claims from every family it handles, and
    # decode once more. Hands that DID get work keep the net's task, so the
    # net's PLANT/FEED/FERTILIZE choices survive -- AUTO never plants.
    try:
        hs = act.get("hands") or []
        spill = [i for i, h in enumerate(hs) if h and h[0] == "PASS"]
        if spill and any(t != 0 for t in (tasks[i] for i in spill)):
            t2 = list(tasks)
            for i in spill:
                t2[i] = 0                      # AUTO
            act2 = _A.decode_multi(obs_dict, _f, t2, _m)
            h2 = act2.get("hands") or []
            if sum(1 for h in h2 if h and h[0] == "PASS") < len(spill):
                act = act2
    except Exception:
        pass
    return act"""
src = src.replace(old_tail, new_tail, 1)
open(main, "w").write(src)
print(f"crew spill written: {out_dir}")
