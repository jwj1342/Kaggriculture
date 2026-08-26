"""The first tests in this repo, on the one part that is pure.

`tools/stats.py` holds the estimator behind every number in `docs/`. It has no
I/O, so it is testable in the way nothing else here is -- and it is the piece
where a silent drift would be most expensive, because a wrong ranking looks
exactly like a right one.

    python tests/test_stats.py
"""
import os
import sys
from contextlib import redirect_stdout
from io import StringIO

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from stats import bradley_terry, wilson, resolved, elo    # noqa: E402
from eval import (_interval_winner, _paired_pool_summary, _summarise,
                  _win_score)  # noqa: E402

FAILS = []


def check(name, cond, detail=""):
    print(f"  {'ok  ' if cond else 'FAIL'}  {name}{'  ' + detail if detail else ''}")
    if not cond:
        FAILS.append(name)


def approx(a, b, tol=1e-6):
    return abs(a - b) <= tol


# --- bradley_terry ---------------------------------------------------------
names = ["a", "b", "c"]

# A perfectly transitive field must come out in order.
wins = {("a", "b"): 90, ("b", "a"): 10, ("a", "c"): 99, ("c", "a"): 1,
        ("b", "c"): 80, ("c", "b"): 20}
games = {k: 100 for k in wins}
p = bradley_terry(wins, games, names)
check("transitive field ranks a > b > c", p["a"] > p["b"] > p["c"],
      f"{p['a']:.2f} {p['b']:.2f} {p['c']:.2f}")

# Everyone identical -> equal strengths, normalised to mean 1.
wins = {(i, j): 50 for i in names for j in names if i != j}
games = {k: 100 for k in wins}
p = bradley_terry(wins, games, names)
check("a tied field gives equal strengths", all(approx(v, 1.0, 1e-6) for v in p.values()))
check("strengths normalise to mean 1", approx(sum(p.values()) / len(p), 1.0))

# Ties count a half each, so a field of all-ties is the same as a field of 50/50.
half = {(i, j): 50.0 for i in names for j in names if i != j}
check("fractional wins are accepted", approx(bradley_terry(half, games, names)["a"], 1.0, 1e-6))

# An agent that never plays must not blow up.
p = bradley_terry({}, {}, ["lonely"])
check("no games does not divide by zero", p == {"lonely": 1.0})

# Non-transitive rock-paper-scissors: the documented case. All three equal.
names3 = ["r", "p", "s"]
rps = {("r", "s"): 90, ("s", "r"): 10, ("s", "p"): 90, ("p", "s"): 10,
       ("p", "r"): 90, ("r", "p"): 10}
g3 = {k: 100 for k in rps}
p = bradley_terry(rps, g3, names3)
check("a rock-paper-scissors cycle collapses to equal strengths",
      max(p.values()) - min(p.values()) < 1e-6,
      "-- which is why any ranking is a ranking against its field")

# --- wilson ----------------------------------------------------------------
lo, hi = wilson(50, 100)
check("50/100 straddles 50%", lo < 50 < hi, f"[{lo:.1f}, {hi:.1f}]")
lo, hi = wilson(100, 100)
check("100/100 stays inside [0,100]", 0 <= lo <= 100 and approx(hi, 100.0, 1e-6),
      f"[{lo:.1f}, {hi:.1f}]")
lo, hi = wilson(0, 100)
check("0/100 stays inside [0,100]", approx(lo, 0.0, 1e-6) and 0 <= hi <= 100,
      f"[{lo:.1f}, {hi:.1f}]")
check("n=0 does not divide by zero", wilson(0, 0) == (0.0, 100.0))
w100 = wilson(60, 100)
w10k = wilson(6000, 10000)
check("more episodes narrow the interval",
      (w10k[1] - w10k[0]) < (w100[1] - w100[0]),
      f"{w100[1]-w100[0]:.1f} -> {w10k[1]-w10k[0]:.1f} points wide")

# --- resolved --------------------------------------------------------------
ok, n = resolved(60, 100)
check("60/100 is resolved at 10 points", ok)
ok, n = resolved(52, 100)
check("52/100 is not resolved", not ok, f"needs ~{n} episodes")
check("and the estimate is the documented 384-for-5-points order", 300 < n < 3000)
ok, n = resolved(50, 100)
check("an exact coin flip never resolves", not ok and n is None)
check("eval resolves 10/96 for B", _interval_winner(*wilson(10, 96)) == "B")
check("eval resolves 64/96 for A", _interval_winner(*wilson(64, 96)) == "A")
check("eval leaves 50/100 unresolved", _interval_winner(*wilson(50, 100)) is None)
check("eval scores ties as half wins", _win_score(32, 32) == 48)
with redirect_stdout(StringIO()):
    tied = _summarise("tie regression", [
        (2, 1, 0), (1, 2, 0), (1, 1, 0),
        (2, 1, 1), (1, 2, 1), (1, 1, 1),
    ])
check("eval summary keeps the overall half-win score",
      tied["score"] == 3 and approx(tied["winrate"], 0.5))

paired = _paired_pool_summary([
    {"tag": "0|wall|0", "seed": 1, "money": [10, 5]},
    {"tag": "1|wall|0", "seed": 1, "money": [8, 6]},
    {"tag": "0|wall|1", "seed": 2, "money": [6, 4]},
    {"tag": "1|wall|1", "seed": 2, "money": [7, 3]},
])
check("pool comparison pairs candidate, seed, opponent, and seat",
      approx(paired["all"]["margin"]["mean"], 2.5))
check("pool comparison reports own and opponent money effects",
      approx(paired["all"]["money"]["mean"], 1.5)
      and approx(paired["all"]["opponent_money"]["mean"], -1.0))
check("pool comparison clusters intervals by seed",
      paired["all"]["seed_clusters"] == 2)

# --- elo -------------------------------------------------------------------
e = elo({"a": 4.0, "b": 1.0, "c": 0.25})
check("elo preserves the ordering", e["a"] > e["b"] > e["c"])
check("elo centres the field on zero", approx(e["b"], 0.0, 1e-9))

print()
if FAILS:
    print(f"{len(FAILS)} failed: {', '.join(FAILS)}")
    sys.exit(1)
print("all passed")
