"""Buy the next quadrant as soon as it is comfortably affordable. No retraining.

Why (docs/RUNS.md 2026-08-23). Of the three ladder-calibrated axes we are wrong on,
first-land day is the only one with NO running cost: a quadrant is a one-time
1000/2000/4000 that unlocks 25 tiles, whereas herd carries 1 wheat per animal per
day and crew is re-hired every morning at fibonacci wages. foreman just measured
-10,299 for forcing the crew axis, which is exactly the failure mode of forcing a
correlate that is really a consequence -- so land is the axis to isolate.

Measured: closer_cleo (ladder 1287.2) buys its first extra quadrant on day 7 and
k06 on day 6; our best RL net waits until day 11. rho for first-land day is -0.61.

BUY_LAND is appended as an extra market order rather than replacing the turn's
chosen action, so buying land does not cost that turn's sale -- the same reasoning
as bazaar, and it matters because BUY_LAND sits in the same collapsed 31-way head
(measured mean 0.00-1.52%).

A 1.5x margin is required over the price so the farm keeps working capital: buying
land down to the last dollar is how a policy bankrupts itself, and the engine's own
HIRE gate uses a comparable 5%-of-money guard.

    python tools/build_homestead.py <export-or-hybrid-dir> <out-dir> [--margin 1.5]
"""
import os, re, shutil, sys
pos = [a for a in sys.argv[1:] if not a.startswith("--")]
margin = 1.5
for a in sys.argv[1:]:
    if a.startswith("--margin"): margin = float(a.split("=",1)[1])
src_dir, out_dir = pos[0], pos[1]
os.makedirs(out_dir, exist_ok=True)
for f in os.listdir(src_dir):
    if f == "__pycache__": continue
    s = os.path.join(src_dir, f)
    if os.path.isfile(s): shutil.copy(s, os.path.join(out_dir, f))
main = os.path.join(out_dir, "main.py"); src = open(main).read()
helper = f'''

# ---- homestead: take the next quadrant early (tools/build_homestead.py) ----
# first-land day has rho = -0.61 against ladder score; cleo buys on day 7, k06 on
# day 6, our best RL net on day 11. Land is the only calibrated axis with no
# running cost. Appended, not substituted, so it does not cost the turn's sale.
_HS_MARGIN = {margin}


def _homestead(obs, act):
    try:
        farm = obs["farms"][obs["player"]]
        owned = len(farm.get("unlocked_quadrants") or [])
        prices = getattr(_R, "LAND_PRICES", None) if "_R" in globals() else None
        if prices is None:
            prices = [1000, 2000, 4000]
        if owned < 1 or owned >= 4 or owned - 1 >= len(prices):
            return act
        need = float(prices[owned - 1]) * _HS_MARGIN
        if float(farm.get("money", 0) or 0) < need:
            return act
        orders = [o for o in (act.get("market") or []) if o]
        if len(orders) >= 10 or any(o[0] == "BUY_LAND" for o in orders):
            return act
        act = dict(act); act["market"] = orders + [["BUY_LAND"]]
        return act
    except Exception:
        return act
'''
n = 0
for old, new in (
    ("    return _A.decode_multi(obs_dict, _pick(flog), tasks, _pick(mlog))",
     "    return _homestead(obs_dict,\n        _A.decode_multi(obs_dict, _pick(flog), tasks, _pick(mlog)))"),
    ("        return _A.decode(obs_dict, _pick(flog), _pick(mlog))",
     "        return _homestead(obs_dict,\n            _A.decode(obs_dict, _pick(flog), _pick(mlog)))")):
    if old in src: src = src.replace(old, new, 1); n += 1
if n == 0: sys.exit("no decode tail found -- refusing to emit a silent no-op")
m = re.search(r"\ndef (?:_net_)?agent\(", src)
src = src[:m.start()] + helper + src[m.start():]
open(main, "w").write(src)
print(f"homestead written: {out_dir} ({n} tail(s), margin={margin})")
