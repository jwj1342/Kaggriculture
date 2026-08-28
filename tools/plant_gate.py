#!/usr/bin/env python
"""Why is PLANT illegal? Attribute each masked turn to the clause that failed.

Why this exists (docs/RUNS.md 2026-08-28, the two verdicts `3317c97` and
`d370fe1`). `tools/head_health.py` established that the raw net's PLANT task is
legal on only 9-10% of turns, which retracted "it can plant and will not". That
made the *precondition* the bottleneck, and `rl/actions.py:764` says the
precondition is a three-way conjunction:

    plant_ok = bool(s["empty"]) and any(seeds[c] > 0 and day <= DEADLINE[c])

`d370fe1` eliminated the deadline clause by reading a constant (WHEAT/CARROT
run to day 27 of 30) and then inferred that seeds are what binds, from four
agents whose BUY_SEED rate and PLANT legality move together (0.04%/10%,
0.02%/9%, 0.79%/30%, 16.42%/57%). That inference is a four-point correlation
across agents that differ in every other way too, and the cheap direct
measurement was never taken. This is that measurement.

It reads the two live clauses at the moment the mask closes, so an illegal turn
lands in exactly one bucket:

  - NO_EMPTY   every unlocked tile is occupied (or the land is still locked).
                 The lever is land or clearing, NOT seed.
  - NO_SEED    a vacant tile exists and the farm holds no seed at all.
                 The lever is BUY_SEED.
  - EXPIRED    a vacant tile exists, seed is held, every held crop is past its
                 own PLANT_DEADLINE while a plantable crop still exists. The
                 farm bought the wrong seed, not too little.
  - BOTH       neither clause holds.
  - MECH_DEAD  day > max(PLANT_DEADLINE) = 27. Nothing is plantable by anyone,
                 including a perfect player, so this is not a policy failure and
                 is excluded from the live-turn legality rate. It takes
                 precedence over the other four: it is a property of the
                 calendar, not of this farm.

`NO_EMPTY` and `NO_SEED` prescribe opposite interventions, which is why the
aggregate legality rate alone could not choose between them.

No network forward is needed -- the clauses are board state -- but the board
depends on the policy, so each agent plays its own episode. One episode is
~3 s; the default three seeds over four agents is a login-node read.

    python tools/plant_gate.py rl/out/anvil-fix rl/out/chisel-fix \
                               [--opp agents/champ/k06.py] [--seeds 10000,10001]

Reference points to reproduce (head_health, 2026-08-28): PLANT legality 10% for
anvil-fix, 9% for chisel-fix, 30% for hybrid-cleo12, 57% for mktfloor-it16.
"""

import argparse
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The G1 chain reads day 12 onward as where the marginal loss is created
# (`512c3fa`), and the critic diagnostic splits the season the same way, so the
# buckets here match those so the two can be laid side by side.
BUCKETS = ((0, 4), (5, 11), (12, 19), (20, 29))
REASONS = ("NO_EMPTY", "NO_SEED", "EXPIRED", "BOTH", "MECH_DEAD")


def _purge():
    """Drop every module an export brought in.

    `kg_rules` is the one name every export shares, so without this the second
    agent silently reuses the first agent's rules module and the comparison it
    is here to make would be between one engine and itself.
    """
    for m in [m for m in sys.modules
              if m == "kg_rules" or m.startswith("kg_rl_")]:
        del sys.modules[m]


def _load_actions(d):
    """Import an export's private actions module (no weights needed)."""
    _purge()
    sys.path.insert(0, d)
    try:
        for f in sorted(os.listdir(d)):
            if f.startswith("kg_rl_actions_") and f.endswith(".py"):
                return __import__(f[:-3])
    finally:
        sys.path.pop(0)
    raise RuntimeError(f"no private actions module in {d}")


def _bucket(day):
    for lo, hi in BUCKETS:
        if lo <= day <= hi:
            return (lo, hi)
    return BUCKETS[-1]


def probe(d, opp, seed):
    """One episode; return per-turn clause readings for our seat."""
    from kaggle_environments import make
    act = _load_actions(d)
    # 27 in engine 1.32.7 (WHEAT/CARROT). Read, never assumed: the balance has
    # already changed once mid-competition.
    max_deadline = max(act.PLANT_DEADLINE.values())
    cheapest = min(act._SEED_COST.values())
    env = make("kaggriculture",
               configuration={"episodeSteps": 720, "seed": seed}, debug=False)
    env.run([os.path.join(d, "main.py"), opp])

    rows = []
    for step in range(len(env.steps) - 1):
        o = env.steps[step][0].observation
        try:
            farm, priv, _inv, _pos = act._me(o)
            s = act._scan(o)
            day = o.get("day", 0)
            seeds = priv["seeds"]
            n_empty = len(s["empty"])
            held = sum(seeds.get(c, 0) for c in act.CROP_LIST)
            viable = [c for c in act.CROP_LIST
                      if seeds.get(c, 0) > 0 and day <= act.PLANT_DEADLINE[c]]
            n_hands = len(farm.get("hands", []))
            # Locked land is a whole-quadrant property, so separate "the farm
            # is full" from "the farm has never been expanded": they prescribe
            # clearing versus BUY_LAND.
            n_unlocked = len(farm.get("unlocked_quadrants", []))
            legal = bool(n_empty) and bool(viable)
            if legal:
                reason = None
            elif day > max_deadline:
                reason = "MECH_DEAD"
            elif not n_empty and not viable:
                reason = "BOTH"
            elif not n_empty:
                reason = "NO_EMPTY"
            elif held == 0:
                reason = "NO_SEED"
            else:
                reason = "EXPIRED"
            rows.append({"day": day, "legal": legal, "reason": reason,
                         "n_empty": n_empty, "held": held, "hands": n_hands,
                         "unlocked": n_unlocked, "money": farm.get("money", 0),
                         "cheapest": cheapest, "max_dl": max_deadline,
                         "maxh": act.MAX_HANDS})
        except Exception:
            continue
    return rows


def _pct(a, b):
    return 100.0 * a / b if b else float("nan")


def report(name, rows):
    turns = len(rows)
    legal = sum(r["legal"] for r in rows)
    slots = sum(r["hands"] for r in rows)
    legal_slots = sum(r["hands"] for r in rows if r["legal"])
    why = Counter(r["reason"] for r in rows if not r["legal"])
    illegal = turns - legal
    max_deadline = rows[0]["max_dl"]

    # The headline rate that head_health prints includes the days on which the
    # calendar forbids planting outright, so a perfect player also scores below
    # 100%. The live rate is the one a policy can be held to.
    dead = why["MECH_DEAD"]
    live = turns - dead

    print(f"\n  {name}")
    print(f"    turns {turns}   PLANT legal {_pct(legal, turns):5.1f}% "
          f"(hand-slot weighted {_pct(legal_slots, slots):5.1f}%, "
          f"which is what head_health prints)")
    print(f"    excluding the {dead} turns past day {max_deadline} where no "
          f"crop is plantable at all: {_pct(legal, live):5.1f}% of {live} live "
          f"turns")
    # Same numerator, head_health's denominator: it walks all MAX_HANDS rows of
    # hand_task_mask and counts every row with any legal action, but rows past
    # the live hand count are IDLE-only, so PLANT can never be legal in them.
    # That caps the reported rate at n_hands/MAX_HANDS and mixes crew size into
    # a legality number. Printed so the two can be reconciled instead of
    # disagreeing silently.
    maxh = rows[0]["maxh"]
    mean_hands = sum(r["hands"] for r in rows) / turns
    print(f"    same numerator over all {maxh} MAX_HANDS rows, which is "
          f"head_health's denominator: {_pct(legal_slots, maxh * turns):5.1f}% "
          f"(mean live hands {mean_hands:.1f}, so that view is capped at "
          f"{_pct(mean_hands, maxh):.0f}%)")
    if not illegal:
        print("    nothing illegal to attribute")
        return why, turns, legal
    print(f"    of the {illegal} illegal turns:")
    for k in REASONS:
        if why[k]:
            print(f"      {k:<9} {why[k]:>5}  {_pct(why[k], illegal):5.1f}%")

    print(f"    {'day':<8}{'turns':>6}{'legal%':>8}"
          + "".join(f"{k:>10}" for k in REASONS))
    for lo, hi in BUCKETS:
        sub = [r for r in rows if _bucket(r["day"]) == (lo, hi)]
        if not sub:
            continue
        sl = sum(r["legal"] for r in sub)
        sw = Counter(r["reason"] for r in sub if not r["legal"])
        bad = len(sub) - sl
        print(f"    {f'{lo}-{hi}':<8}{len(sub):>6}{_pct(sl, len(sub)):>7.1f}%"
              + "".join(f"{_pct(sw[k], bad):>9.0f}%" if bad else f"{'-':>10}"
                        for k in REASONS))

    # Levels, not just which clause: "0.2 empty tiles" and "no seed while 8
    # tiles sit vacant" are different diagnoses even inside one bucket.
    ill = [r for r in rows if not r["legal"]]
    print(f"    on illegal turns: mean empty tiles "
          f"{sum(r['n_empty'] for r in ill) / len(ill):.2f}, "
          f"mean seeds held {sum(r['held'] for r in ill) / len(ill):.2f}, "
          f"mean unlocked quadrants "
          f"{sum(r['unlocked'] for r in ill) / len(ill):.2f}")
    # "Holds no seed" and "cannot afford seed" prescribe opposite fixes, and
    # only one of them is about the market head.
    ns = [r for r in rows if r["reason"] == "NO_SEED"]
    if ns:
        cheap = ns[0]["cheapest"]
        afford = sum(r["money"] >= cheap for r in ns)
        print(f"    on the {len(ns)} NO_SEED turns: cheapest seed ${cheap}, "
              f"mean money ${sum(r['money'] for r in ns) / len(ns):,.0f}, "
              f"could afford one on {_pct(afford, len(ns)):.1f}%")
    return why, turns, legal


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--opp", default=f"{ROOT}/agents/champ/k06.py")
    ap.add_argument("--seeds", default="10000,10001,10002")
    a = ap.parse_args()

    seeds = [int(s) for s in a.seeds.split(",") if s.strip()]
    print(f"\n  PLANT precondition attribution, opponent "
          f"{os.path.basename(a.opp)}, seeds {seeds}")
    print(f"  every turn of our seat is read; each illegal turn lands in "
          f"exactly one of {', '.join(REASONS)}")

    summary = []
    for d in a.dirs:
        name = os.path.basename(d.rstrip("/"))
        pooled = []
        for sd in seeds:
            try:
                pooled += probe(d, a.opp, sd)
            except Exception as e:
                print(f"  {name} seed {sd}: ERROR {e}")
        if not pooled:
            continue
        why, turns, legal = report(f"{name}  (pooled over {len(seeds)} seeds)",
                                   pooled)
        summary.append((name, turns, legal, why))

    print(f"\n  {'agent':<20}{'legal%':>8}"
          + "".join(f"{k:>10}" for k in REASONS))
    for name, turns, legal, why in summary:
        bad = turns - legal
        print(f"  {name[:20]:<20}{_pct(legal, turns):>7.1f}%"
              + "".join(f"{_pct(why[k], bad):>9.0f}%" if bad else f"{'-':>10}"
                        for k in REASONS))
    print("\nPLANT-GATE-DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
