"""Buy seed while empty tiles wait. No retraining. Zero GPU.

Why (docs/RUNS.md 2026-08-23). Forcing each calibrated acquisition axis individually
LOSES: foreman (crew 10->12) measured -10,299 and homestead (land 2.0->3.7) measured
-5,844, and homestead's behaviour row says why -- it bought the land and could not
fill it, seeds stayed at 50 while bare tiles went 18/19 to 56/60.

That identifies the root of the chain. Seed purchase is upstream of all three axes:
45-50 seeds a season (k06 buys 207) can only fill ~45 tiles, so land past two
quadrants sits idle, crew past 10 has nothing to do, and herd past 6 cannot be fed.
The other axes are its consequences, which is why forcing them individually fails.

So this forces the ROOT: append a BUY_SEED order while unlocked tiles sit empty.
STRAWBERRY, because strawberry sold has rho = +0.88 with ladder score (second only to
the hands marker) and we sell 98 against closer_cleo's 270.

Appended, not substituted, so buying seed does not cost that turn's sale.

    python tools/build_sower2.py <export-dir> <out-dir> [--crop STRAWBERRY] [--per 1]
"""
import os, re, shutil, sys
pos = [a for a in sys.argv[1:] if not a.startswith("--")]
crop, per = "STRAWBERRY", 1
for a in sys.argv[1:]:
    if a.startswith("--crop"): crop = a.split("=",1)[1]
    if a.startswith("--per"):  per = int(a.split("=",1)[1])
src_dir, out_dir = pos[0], pos[1]
os.makedirs(out_dir, exist_ok=True)
for f in os.listdir(src_dir):
    if f == "__pycache__": continue
    s = os.path.join(src_dir, f)
    if os.path.isfile(s): shutil.copy(s, os.path.join(out_dir, f))
main = os.path.join(out_dir, "main.py"); src = open(main).read()
helper = f'''

# ---- sower2: buy seed while land sits empty (tools/build_sower2.py) --------
# Seed purchase is the ROOT of the acquisition chain: 45-50 seeds a season fills
# ~45 tiles, so land past 2 quadrants is idle (homestead: bare 18->56 when land
# went 2.0->3.7), crew past 10 idles (foreman: -10,299) and herd past 6 starves.
# STRAWBERRY: rho +0.88 with ladder score, and we sell 98 vs cleo's 270.
_SOW_CROP = "{crop}"
_SOW_PER = {per}


def _sower2(obs, act):
    try:
        farm = obs["farms"][obs["player"]]
        empty = sum(1 for row in farm["tiles"] for t in row if t is None)
        if empty <= 0:
            return act
        priv = obs.get("private") or {{}}
        seeds = (priv.get("seeds") or {{}})
        held = int(seeds.get(_SOW_CROP, 0) or 0)
        if held >= empty:                 # already enough seed for the idle land
            return act
        orders = [o for o in (act.get("market") or []) if o]
        if len(orders) >= 10:
            return act
        # keep working capital: the engine's own HIRE gate uses 5% of money, so
        # spend seed money only out of a comparable slice
        money = float(farm.get("money", 0) or 0)
        prices = (obs.get("market") or {{}}).get("prices") or {{}}
        cost = float(prices.get(_SOW_CROP, 100) or 100)
        if money < cost * 10:
            return act
        act = dict(act)
        act["market"] = orders + [["BUY_SEED", _SOW_CROP, _SOW_PER]]
        return act
    except Exception:
        return act
'''
n = 0
for old, new in (
    ("    return _A.decode_multi(obs_dict, _pick(flog), tasks, _pick(mlog))",
     "    return _sower2(obs_dict,\n        _A.decode_multi(obs_dict, _pick(flog), tasks, _pick(mlog)))"),
    ("        return _A.decode(obs_dict, _pick(flog), _pick(mlog))",
     "        return _sower2(obs_dict,\n            _A.decode(obs_dict, _pick(flog), _pick(mlog)))")):
    if old in src: src = src.replace(old, new, 1); n += 1
if n == 0: sys.exit("no decode tail -- refusing to emit a silent no-op")
m = re.search(r"\ndef (?:_net_)?agent\(", src)
src = src[:m.start()] + helper + src[m.start():]
open(main, "w").write(src)
print(f"sower2 written: {out_dir} ({n} tail(s), crop={crop})")
