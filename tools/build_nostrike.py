"""Mask IDLE out of the hand heads. No retraining. Zero GPU.

Why (docs/RUNS.md 2026-08-23). The hand-head argmax on real states puts 34.8% of
hand-slots on IDLE -- the single largest share, ahead of AUTO's 29.9% -- while
HARVEST gets 1.4%. IDLE decodes to ["PASS"] unconditionally, and hands are DAY
LABOUR whose fibonacci wage is paid whether they work or not, so IDLE is a strike
that costs the same as working. rl/tensor_env/trl_policy.py's MultiActorNet even
starts the hand-head bias at auto_bias=2.5 on AUTO precisely because "AUTO is a
competent default where IDLE is a strike" -- and the trained net drifted onto IDLE
anyway.

Half the strawberry deficit is harvests-per-tile (4.0 ours vs 6.6 for closer_cleo at
ladder 1287.2), and HARVEST is picked 1.4% of the time. This removes the strike
option so those slots fall to whatever the head ranks next.

One line: the IDLE column of the hand-task mask is cleared. No new action, no head
resize, existing checkpoints load unchanged -- so it is measurable at zero GPU.

Honest caveat: masking a class the policy was TRAINED to use pushes it off its own
distribution, which is how thrift broke its tail (p05 22,842 -> 0). The nine-opponent
array decides; a tail collapse means the strike was load-bearing.

    python tools/build_nostrike.py <export-or-hybrid-dir> <out-dir>
"""
import os, re, shutil, sys
src_dir, out_dir = sys.argv[1], sys.argv[2]
os.makedirs(out_dir, exist_ok=True)
for f in os.listdir(src_dir):
    if f == "__pycache__": continue
    s = os.path.join(src_dir, f)
    if os.path.isfile(s): shutil.copy(s, os.path.join(out_dir, f))
main = os.path.join(out_dir, "main.py"); src = open(main).read()
anchor = "    hlog[~hm] = -1e9\n"
if anchor not in src:
    sys.exit("could not find the hand-mask line in _act -- refusing to emit an "
             "agent whose IDLE mask silently never fires")
inject = anchor + '''    # nostrike: IDLE is a strike that still pays the wage (34.8% of hand-slots
    # chose it; HARVEST got 1.4%). Clear it so the slot falls to the next-ranked
    # task. Guarded: never mask the ONLY legal task for a hand.
    try:
        _idle = list(_A.HAND_TASKS).index("IDLE")
        _keep = hm[:, _idle].copy()
        hlog[:, _idle] = -1e9
        _dead = ~(hlog > -1e8).any(axis=1)
        if _dead.any():
            hlog[_dead, _idle] = 0.0
    except Exception:
        pass
'''
src = src.replace(anchor, inject, 1)
m = re.search(r"\ndef (?:_net_)?agent\(", src)
open(main, "w").write(src)
print(f"nostrike written: {out_dir}")
