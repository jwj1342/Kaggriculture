"""Mask BUY_WHEAT when the shed already holds the herd's feed. No retraining.

Why (docs/RUNS.md 2026-08-23). rl/actions.py decodes BUY_WHEAT as
`[["BUY_PRODUCT", "WHEAT", max(5, 2 * herd)]]` -- two days of feed for the whole
herd -- and NOTHING anywhere checks what the shed already holds: not the mask, not
the decode. Measured consequence on one episode against k06: the net fires it on
224 of 720 turns, ordering 946 wheat units for a herd of 3-4 that eats about 120
in a season, and 45,885 of its 54,101 outlays land on those turns. A SELL was
legal on 100% of them, with a median of 14 legal actions available, so this is not
a masking artefact forcing its hand -- it is a repeat purchase with no stop
condition.

This masks the action while `shed WHEAT >= 2 * herd`, i.e. while the shed already
holds what one firing would buy. It does not change what the action does, does not
add an action, and does not touch any other index -- so it is the narrowest
possible intervention on the defect, and it leaves the net free to buy the moment
the stock is actually drawn down.

Criterion (c) is satisfied: the rule has leverage because those turns have a dozen
other legal candidates. The archive's warning that decode-layer fixes are worth
about 2k and do not compose is noted -- but every one of those was a change to
WHICH action gets chosen, and this removes a repeated purchase with no stop
condition, so its size is set by the wasted spend rather than by better selection.

    python tools/build_thrift.py <export-or-hybrid-dir> <out-dir> [--days N]

--days N masks while the shed holds N days of feed (default 2, matching what one
firing buys).

The guard is inserted INSIDE _act after the market mask, not wrapped around the
agent: CLAUDE.md's loader takes the LAST callable bound at module level, so
wrapping `agent` and leaving the original bound after it loads the unwrapped one
and every variant scores identically with no error at all.
"""
import os
import re
import shutil
import sys

pos = [a for a in sys.argv[1:] if not a.startswith("--")]
days = 2
for a in sys.argv[1:]:
    if a.startswith("--days"):
        days = int(a.split("=", 1)[1]) if "=" in a else days
src_dir, out_dir = pos[0], pos[1]
os.makedirs(out_dir, exist_ok=True)
for f in os.listdir(src_dir):
    if f == "__pycache__":
        continue
    s = os.path.join(src_dir, f)
    if os.path.isfile(s):
        shutil.copy(s, os.path.join(out_dir, f))

main = os.path.join(out_dir, "main.py")
src = open(main).read()

helper = f'''

# ---- thrift guard (tools/build_thrift.py) ---------------------------------
# BUY_WHEAT decodes to max(5, 2 * herd) units of wheat and nothing checks the
# shed first, so the net re-buys the same two days of feed all game: 224 firings,
# 946 units ordered for a herd of 3-4 that eats about 120 a season, and 45,885 of
# 54,101 outlays on those turns. Mask it while the stock is already there.
_THRIFT_DAYS = {days}
try:
    _BW_IDX = list(_A.MARKET_ACTIONS).index("BUY_WHEAT")
except (AttributeError, ValueError):
    _BW_IDX = -1


def _thrift_block(obs):
    """True when the shed already holds _THRIFT_DAYS of feed for the herd."""
    try:
        farm = obs["farms"][obs["player"]]
        herd = sum(1 for row in farm["tiles"] for t in row
                   if isinstance(t, dict) and t.get("animal"))
        if herd == 0:
            return True          # no mouths: buying feed is pure waste
        shed = (obs.get("private") or {{}}).get("shed") or {{}}
        return int(shed.get("WHEAT", 0)) >= _THRIFT_DAYS * herd
    except Exception:
        return False


def _thrift(obs, mlog):
    if _BW_IDX >= 0 and _thrift_block(obs):
        mlog[_BW_IDX] = -1e9
'''

anchor = "    mlog[~_A.market_mask(obs_dict)] = -1e9\n"
if anchor not in src:
    sys.exit("could not find the market-mask line in _act -- refusing to emit an "
             "agent whose guard silently never fires")
src = src.replace(anchor, anchor + "    _thrift(obs_dict, mlog)\n", 1)

m = re.search(r"\ndef (?:_net_)?agent\(", src)
if not m:
    sys.exit("no agent function found")
src = src[:m.start()] + helper + src[m.start():]
open(main, "w").write(src)
print(f"thrift written: {out_dir} (masks BUY_WHEAT while the shed holds "
      f"{days} days of feed)")
