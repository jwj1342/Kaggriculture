"""Hire to the affordable ceiling every turn, the way k06 does. No retraining.

Why (docs/RUNS.md 2026-08-23). Against 18 submissions with real ladder scores
(555-2302), hands@20 is the strongest correlate of ladder score at rho = +0.96,
far ahead of money at +0.73. And it is not money's shadow for us: measured against
k06 at day 20, k06 holds 12 hands and is exactly budget-capped, while our nets hold
10 with the budget allowing 12. The fibonacci wage makes hand 11 cost 144 and hand
12 cost 233 against 15-21k of cash -- so we are leaving free hands on the table on
precisely the quantity that predicts ladder score.

k06's rule is effectively "always hire to the budget ceiling". This replicates it in
the decode layer, so it is measurable on an existing export at zero GPU cost.

HIRE is just another market order, so the top-up is APPENDED rather than replacing
the turn's chosen action -- hiring therefore does not cost the sale, which matters
because "not hiring up" was itself traced to one-action-per-turn (HIRE is market
index 21, in the same collapsed head, measured at a 0.00% median).

The engine's own gate is reproduced exactly: fib(hires_today + j) <= 0.05 * money
and crew < MAX_HANDS, capped by the remaining order slots. Hands are DAY LABOUR --
the engine fires the whole crew at end of day -- so the top-up must run every turn,
not once.

    python tools/build_foreman.py <export-or-hybrid-dir> <out-dir> [--frac 0.05]

--frac overrides the wage-budget fraction. 0.05 is the engine's own; a larger value
would hire past what the engine permits and the extra orders would be silent
no-ops, so it is capped at 0.05 here rather than offered as a dial.

Inserted INSIDE _act after the decode, not wrapped around the agent: CLAUDE.md's
loader takes the LAST callable bound at module level, so wrapping `agent` and
leaving the original bound after it loads the unwrapped one and every variant
scores identically with no error.
"""
import os
import re
import shutil
import sys

pos = [a for a in sys.argv[1:] if not a.startswith("--")]
frac = 0.05
for a in sys.argv[1:]:
    if a.startswith("--frac"):
        frac = min(0.05, float(a.split("=", 1)[1]))
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

# ---- foreman: hire to the affordable ceiling (tools/build_foreman.py) ------
# hands@20 is the strongest ladder correlate measured (rho = +0.96 over 18 scored
# submissions, against money's +0.73), and our nets leave 2 affordable hands
# unhired from day 15 while k06 sits exactly on its budget cap. Hand 11 costs 144
# and hand 12 costs 233 against 15-21k of cash.
_FOREMAN_FRAC = {frac}


def _fib_wage(n):
    """The engine's hire wage for the n-th hire of the day (actions._fib)."""
    a, b = 1, 1
    for _ in range(int(n)):
        a, b = b, a + b
    return a


def _foreman(obs, act):
    """Append HIRE orders up to what the engine's own gate permits."""
    try:
        farm = obs["farms"][obs["player"]]
        crew = len(farm.get("hands") or [])
        maxh = getattr(_A, "MAX_HANDS", 12)
        if crew >= maxh:
            return act
        orders = [o for o in (act.get("market") or []) if o]
        room = 10 - len(orders)                  # the engine drops past 10
        if room <= 0:
            return act
        cap = _FOREMAN_FRAC * float(farm.get("money", 0) or 0)
        hires = int(farm.get("hires_today", 0) or 0)
        add = 0
        while (add < room and crew + add < maxh
               and _fib_wage(hires + add) <= cap):
            add += 1
        if add <= 0:
            return act
        act = dict(act)
        act["market"] = orders + [["HIRE"]] * add
        return act
    except Exception:
        return act
'''

n_patched = 0
for old, new in (
    ("    return _A.decode_multi(obs_dict, _pick(flog), tasks, _pick(mlog))",
     "    return _foreman(obs_dict,\n"
     "                    _A.decode_multi(obs_dict, _pick(flog), tasks, _pick(mlog)))"),
    ("        return _A.decode(obs_dict, _pick(flog), _pick(mlog))",
     "        return _foreman(obs_dict,\n"
     "                        _A.decode(obs_dict, _pick(flog), _pick(mlog)))"),
):
    if old in src:
        src = src.replace(old, new, 1)
        n_patched += 1
if n_patched == 0:
    sys.exit("could not find a decode tail in _act -- refusing to emit an agent "
             "whose foreman silently never fires")

m = re.search(r"\ndef (?:_net_)?agent\(", src)
if not m:
    sys.exit("no agent function found")
src = src[:m.start()] + helper + src[m.start():]
open(main, "w").write(src)
print(f"foreman written: {out_dir} ({n_patched} decode tail(s), frac={frac})")
