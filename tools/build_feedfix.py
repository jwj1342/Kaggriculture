"""Patch feed self-sufficiency into an exported net, with no retraining.

Why (docs/RUNS.md 2026-08-23). The measured deficit is a feed bill: 54,050 of
outlays against k06's 20,936, and zero wheat seeds a season against its 138. The
engine's FEED op takes 1 WHEAT per animal per day out of the farm's OWN shed, so
a farm that plants no wheat buys its feed at a price both farms drive from 27 to
49. haymaker attacks that in training. This attacks it in the decode layer, which
costs no GPU and answers a different question: is the net's problem the PRICE
SIGNAL it was trained on, or its policy? If forcing the purchase recovers most of
the gap, feed is the mechanism and haymaker should work; if it does not, feed was
a correlate and the training arm is aimed wrong.

One intervention is enough, and rl/actions.py says exactly where. The hand PLANT
task's crop "is the farm's most-held VIABLE seed ... the market head owns the mix
via BUY_SEED". So the net already knows how to walk a hand to an empty tile and
plant, and it already knows how to FEED from the shed; the only thing it never
does is buy the seed. Forcing BUY_SEED_WHEAT when the herd is short therefore
recruits all the existing machinery, and it does NOT need coordinates -- which
matters, because PLANT carries no target (`["PLANT", "WHEAT"]`), so an injected
plant would only land if a hand happened to be standing on an empty tile.

The override is deliberately rate-limited by its own condition rather than by a
counter: it fires only while the projected shortfall is positive AND the seed bag
is nearly empty, so it buys roughly one seed at a time as the bag drains.

It is not free. The market head emits one action a turn, so a forced seed purchase
costs that turn's SELL. That cost is inside the measurement, which is the point.

    python tools/build_feedfix.py <export-or-hybrid-dir> <out-dir> [--buffer N]

The wrapper is inserted INSIDE _act, before the decode call, rather than wrapped
around the agent function: CLAUDE.md's contract loads the LAST callable bound at
module level, so wrapping `agent` and leaving the original bound after it loads
the unwrapped one and every variant scores identically with no error.
"""
import os
import re
import shutil
import sys

args = [a for a in sys.argv[1:] if not a.startswith("--")]
buf = 2
for a in sys.argv[1:]:
    if a.startswith("--buffer"):
        buf = int(a.split("=", 1)[1]) if "=" in a else buf
src_dir, out_dir = args[0], args[1]
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

# ---- feed self-sufficiency override (tools/build_feedfix.py) ---------------
# The engine's FEED op is _inv_take(inv, "WHEAT", 1): one wheat per animal per
# day from this farm's own shed. The net never buys wheat seed (0 a season
# against the ladder tier's 138), so it feeds its herd from the market at a
# price both farms push from 27 to 49. rl/actions.py: the hand PLANT task's crop
# is the farm's most-held viable seed and "the market head owns the mix via
# BUY_SEED" -- so forcing the purchase is enough to recruit the planting and
# feeding machinery the net already has.
_FEED_BUFFER = {buf}
_SEASON_DAYS = 30
_WHEAT_MAXY = 6
try:
    _WSEED_IDX = list(_A.MARKET_ACTIONS).index("BUY_SEED_WHEAT")
except (AttributeError, ValueError):
    _WSEED_IDX = -1


def _feed_short(obs):
    """Projected wheat shortfall: herd x days left, minus shed wheat and the
    units still owed by standing wheat tiles. A standing wheat tile and shed
    wheat cannot double-count -- HARVEST on a one-shot crop sets the tile to
    None, so a tile that is still PLANT has not been harvested."""
    try:
        farm = obs["farms"][obs["player"]]
        priv = obs.get("private") or {{}}
        shed = priv.get("shed") or {{}}
        herd = 0
        tiles_wheat = 0
        for row in farm["tiles"]:
            for t in row:
                if not isinstance(t, dict):
                    continue
                if t.get("animal"):
                    herd += 1
                elif t.get("kind") == "PLANT" and t.get("crop") == "WHEAT":
                    tiles_wheat += 1
        if herd == 0:
            return 0, 0
        day = int(obs.get("day", 0) or 0)
        need = herd * max(0, _SEASON_DAYS - day)
        have = int(shed.get("WHEAT", 0)) + _WHEAT_MAXY * tiles_wheat
        return max(0, need - have), int((priv.get("seeds") or {{}}).get("WHEAT", 0))
    except Exception:
        return 0, 0


def _bias_feed(obs, mlog):
    """Force BUY_SEED_WHEAT while the herd is short and the bag is nearly empty.

    Uses max + 20 rather than a huge constant: the export samples at _TEMP 1.0
    and a 1e9 logit overflows the softmax."""
    if _WSEED_IDX < 0:
        return
    short, bag = _feed_short(obs)
    if short <= 0 or bag > _FEED_BUFFER:
        return
    if mlog[_WSEED_IDX] <= -1e8:      # illegal this turn under the market mask
        return
    mlog[_WSEED_IDX] = float(mlog.max()) + 20.0
'''

# insert the call inside _act, right after the market mask is applied
anchor = "    mlog[~_A.market_mask(obs_dict)] = -1e9\n"
if anchor not in src:
    sys.exit("could not find the market-mask line in _act -- refusing to emit an "
             "agent whose override silently never fires")
src = src.replace(anchor, anchor + "    _bias_feed(obs_dict, mlog)\n", 1)

# the helper must be defined before _act runs but after _A is imported; putting it
# at the end of the module is enough (it is called at inference time), except that
# CLAUDE.md's loader takes the LAST callable bound at module level. So the helper
# goes in BEFORE the agent function.
m = re.search(r"\ndef (?:_net_)?agent\(", src)
if not m:
    sys.exit("no agent function found")
src = src[:m.start()] + helper + src[m.start():]
open(main, "w").write(src)
print(f"feedfix written: {out_dir} (buffer {buf})")
