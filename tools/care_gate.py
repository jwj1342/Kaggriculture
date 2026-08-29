#!/usr/bin/env python
"""What binds care throughput in day 18-24, the six days that carry half the gap?

`67ec655` localised the executor's damage to day 18-24 (52.5% of a 46,091 span) and
`99a516a` read the mechanism off the existing byday numbers: in those six days our
crop stock goes 25 -> 19 and WATER goes 24 -> 18, while k01 goes 51 -> 58 and 45 ->
48. The engine says why that kills: `kaggriculture.py:783`, two consecutive unwatered
days and the crop dies. So the stock shrinks because care does not keep up.

What no reading has done yet is say WHICH constraint binds, and the candidates
prescribe opposite interventions:

  NO_CREW   the hand slot does not exist -- the crew was never hired. The lever is
            HIRE, and it is a MARKET action, not a farm one.
  PASS/none the hand exists and is told to do nothing. The lever is the task head.
  MOVE      the hand exists and is walking. The lever is routing/assignment.
  OTHER     the hand exists and is doing non-care work (PLANT/PICKUP/BUILD/...).
            Care lost a priority contest; the lever is the priority, not capacity.
  CARE_OP   the hand is doing care. Not a failure.

Every hand slot in every turn falls in exactly one bucket and the five sum to
MAX_HANDS * turns -- asserted, because a bucket that silently swallows another is
how "measured and refuted" gets confused with "never measured".

Two facts this tool exists to settle, both read rather than assumed:

1. `rl/actions.py:48` sets MAX_HANDS = 12, but `_do_hire` in the reference engine
   (`kaggriculture.py:702`) has NO cap: it appends a hand whenever the farm can
   afford `FARM_HAND_COST_MULT * fib(hires_today)`, and `hires_today` resets daily.
   So 12 is OUR action-space bound, not the game's. If a winning tape runs a bigger
   crew than 12, our policy cannot represent the winning configuration at all --
   and per the 08-23 gap localisation, the action space is the one candidate that
   has never been tested.
2. Whether care DEMAND is even unmet. Doing no watering is correct when nothing is
   thirsty, so the count of unwatered standing crops is reported next to the care
   ops. A throughput verdict without it would be unfalsifiable.

Discipline: `agents/champ/k01.py` runs as a known positive in the same invocation.
It beats these walls 91-98%, so it MUST read as high-coverage care. If the
instrument says the winner is idle, the instrument is wrong -- that is the rule
08-28 paid for when a `None` win field turned 61/64 into 0/64.

    python tools/care_gate.py rl/out/anvil-fix/main.py [more agents...] [--seeds N]
"""

import argparse
import collections
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DAYS = 30
TURNS_PER_DAY = 24
# Same buckets as plant_gate.py and the Phase 0 critic diagnostic, so the three can
# be laid side by side. WINDOW is the six days 67ec655 localised.
BUCKETS = ((0, 4), (5, 11), (12, 17), (18, 24), (25, 29))
WINDOW = (18, 24)

CARE_OPS = {"WATER", "FERTILIZE", "HARVEST", "CARE", "FEED"}
MOVE_OPS = {"NORTH", "SOUTH", "EAST", "WEST"}
REASONS = ("CARE_OP", "MOVE", "OTHER", "PASS", "NO_ORDER", "NO_CREW")


def _crop_table():
    """`ongoing` per crop, read from the engine copy rather than hard-coded --
    the balance has already changed once mid-competition."""
    sys.path.insert(0, os.path.join(ROOT, "reference/engine"))
    try:
        import kaggriculture as K
        return {c: bool(d["ongoing"]) for c, d in K.CROPS.items()}
    finally:
        sys.path.pop(0)


ONGOING = _crop_table()


def _max_hands():
    """Our action-space crew bound, read from the module that enforces it."""
    sys.path.insert(0, os.path.join(ROOT, "rl"))
    try:
        import actions as A
        return int(A.MAX_HANDS)
    finally:
        sys.path.pop(0)


def _bucket(day):
    for lo, hi in BUCKETS:
        if lo <= day <= hi:
            return (lo, hi)
    return BUCKETS[-1]


def _scan_board(farm):
    """Standing crops, and how close each is to dying of thirst.

    `consecutive_unwatered` is the engine's own counter and it kills at 2
    (kaggriculture.py:783). A crop already at 1 dies TODAY unless watered, so it is
    reported separately from merely-thirsty: those two numbers are the difference
    between "behind on chores" and "losing the farm".
    """
    crops = thirsty = doomed = animals = uncared = 0
    for row in farm["tiles"]:
        for t in row:
            if not isinstance(t, dict):
                continue
            if t.get("kind") == "PLANT":
                crops += 1
                if not t.get("watered_today"):
                    thirsty += 1
                    if t.get("consecutive_unwatered", 0) >= 1:
                        doomed += 1
            elif "animal" in t:
                animals += 1
                if not t.get("cared_today"):
                    uncared += 1
    return crops, thirsty, doomed, animals, uncared


def _plant_tiles(farm):
    return {(x, y): t
            for y, row in enumerate(farm["tiles"])
            for x, t in enumerate(row)
            if isinstance(t, dict) and t.get("kind") == "PLANT"}


def _why_gone(tile, step):
    """Why a standing crop is no longer standing, from its LAST live state.

    The engine turns a tile to WEED on two completely different events, and
    lumping them is the difference between a waste and a completed production
    cycle:

      EXPIRED  `_decay_plants` (kaggriculture.py:752) runs a crop down once
               `step >= max_lifespan_step`. What that MEANS depends on the crop:
               for an ongoing crop (TOMATO, STRAWBERRY) the field is only set
               after `production_count == max_yield` (line 802), so it was fully
               milked and this is no loss at all. For a one-shot crop (WHEAT,
               CARROT, MELON) it is set at PLANTING time (line 224), so expiry
               means the crop was grown and then never harvested -- the seed and
               every watering spent on it are simply thrown away. Reporting one
               number for both would hide a pure waste inside a healthy event.
      THIRST   `_daily_refresh_plants` (line 783) clears at
               `consecutive_unwatered >= 2`. The crop died before paying off.

    EXPIRED is checked before THIRST because a crop on its last legs is often
    also unwatered, and calling that a thirst death would invent a care problem.
    """
    mls = tile.get("max_lifespan_step", -1)
    if mls >= 0 and step >= mls:
        return "EXP_MILKED" if ONGOING.get(tile.get("crop")) else "EXP_UNPICKED"
    if not tile.get("watered_today") and tile.get("consecutive_unwatered", 0) >= 1:
        return "THIRST"
    return "OTHER"


def _op_positions(farm, act, want):
    """Tiles where an actor stood AND issued `want` on this turn.

    Ops resolve on the actor's own tile (`kaggriculture.py:337`), so standing
    position plus op is the whole attribution. Used to separate the ways a crop
    leaves a tile -- harvested (income) versus dead (loss) -- which the stock
    curve alone cannot tell apart and which prescribe opposite fixes.
    """
    if not isinstance(act, dict):
        return set()
    out = set()
    f = act.get("farmer")
    if f and (f[0] if isinstance(f, (list, tuple)) else f) == want:
        out.add(tuple(farm["farmer"]))
    for i, entry in enumerate(act.get("hands") or []):
        if not entry:
            continue
        op = entry[0] if isinstance(entry, (list, tuple)) else entry
        if op == want and i < len(farm["hands"]):
            out.add(tuple(farm["hands"][i]))
    return out


def _harvest_positions(farm, act):
    return _op_positions(farm, act, "HARVEST")


def probe(agent, opp, seed, max_hands):
    """One episode; per-turn hand-slot attribution for our seat (player 0).

    ALIGNMENT, measured not assumed (this cost a wrong reading once already):
    `env.steps[t].action` is the action that PRODUCED `env.steps[t].observation`,
    i.e. the decision taken at state t-1. Pairing it with the observation stored
    beside it shifts every attribution by one turn, which showed up as 89% of the
    winner's crop removals landing in an unexplained bucket. So all state is read
    from t-1 and only the action comes from t. PLANT and HARVEST do not move the
    actor, so t-1 positions are the acting positions. `_align_gate` below asserts
    this on real data every run rather than trusting this paragraph.
    """
    from kaggle_environments import make
    env = make("kaggriculture",
               configuration={"episodeSteps": DAYS * TURNS_PER_DAY, "seed": seed},
               debug=False)
    env.run([agent, opp])

    rows = []
    planted_ops = planted_tiles = 0
    for step in range(1, len(env.steps)):
        prev = env.steps[step - 1][0].observation
        act = env.steps[step][0].action
        farm = prev["farms"][0]
        day = prev.get("day", (step - 1) // TURNS_PER_DAY)
        n_hands = len(farm.get("hands", []))
        hands = (act.get("hands") or []) if isinstance(act, dict) else []
        crops, thirsty, doomed, animals, uncared = _scan_board(farm)

        # Stock flow across this one step: board(t-1) -> board(t), caused by
        # action(t) plus the day rollover. Deaths land on the rollover (the
        # engine clears a tile at consecutive_unwatered >= 2,
        # kaggriculture.py:783), which is what makes them separable from
        # harvests at all.
        before = _plant_tiles(farm)
        after = _plant_tiles(env.steps[step][0].observation["farms"][0])
        harvested_here = _harvest_positions(farm, act)
        gone = set(before) - set(after)
        fresh = set(after) - set(before)
        flow = collections.Counter(planted=len(fresh))
        for pos in gone:
            if pos in harvested_here:
                flow["harvested"] += 1
            else:
                flow[_why_gone(before[pos], step - 1)] += 1

        # Alignment gate: every tile that became PLANT must be a tile where a
        # PLANT op was issued. Under the wrong pairing this fails immediately.
        planted_tiles += len(fresh)
        planted_ops += len(fresh & _op_positions(farm, act, "PLANT"))

        why = collections.Counter()
        for slot in range(max_hands):
            if slot >= n_hands:
                # Mechanically absent: no policy could act here. Takes precedence
                # over everything else -- it is a property of the crew, not the
                # turn, and lumping it with PASS would blame the task head for a
                # hiring decision.
                why["NO_CREW"] += 1
                continue
            entry = hands[slot] if slot < len(hands) else None
            if not entry:
                why["NO_ORDER"] += 1
                continue
            op = entry[0] if isinstance(entry, (list, tuple)) else entry
            if op in CARE_OPS:
                why["CARE_OP"] += 1
            elif op in MOVE_OPS:
                why["MOVE"] += 1
            elif op == "PASS":
                why["PASS"] += 1
            else:
                why["OTHER"] += 1
        assert sum(why.values()) == max_hands, (why, max_hands)

        rows.append({"day": day, "n_hands": n_hands, "crops": crops,
                     "thirsty": thirsty, "doomed": doomed, "animals": animals,
                     "uncared": uncared, "why": why, "flow": flow})
    return rows, (planted_ops, planted_tiles)


def _pct(n, d):
    return 100.0 * n / d if d else 0.0


def report(name, rows, max_hands, seeds):
    turns = len(rows)
    if not turns:
        print(f"\n  {name}: no turns")
        return None
    total = collections.Counter()
    for r in rows:
        total.update(r["why"])
    slots = max_hands * turns
    assert sum(total.values()) == slots, (sum(total.values()), slots)

    print(f"\n  {name}   ({turns // seeds} turns x {seeds} seeds, "
          f"MAX_HANDS={max_hands})")
    print(f"    {'window':>9} {'crew':>5} {'crops':>6} {'thirsty':>8} "
          f"{'dying':>6} " + "".join(f"{k:>9}" for k in REASONS))
    for lo, hi in BUCKETS:
        sub = [r for r in rows if lo <= r["day"] <= hi]
        if not sub:
            continue
        w = collections.Counter()
        for r in sub:
            w.update(r["why"])
        n = max_hands * len(sub)
        tag = f"d{lo}-{hi}"
        if (lo, hi) == WINDOW:
            tag = f"*{tag}"
        print(f"    {tag:>9} "
              f"{sum(r['n_hands'] for r in sub) / len(sub):>5.1f} "
              f"{sum(r['crops'] for r in sub) / len(sub):>6.1f} "
              f"{sum(r['thirsty'] for r in sub) / len(sub):>8.1f} "
              f"{sum(r['doomed'] for r in sub) / len(sub):>6.1f} "
              + "".join(f"{_pct(w[k], n):>8.1f}%" for k in REASONS))

    # Stock flow. The stock curve on its own cannot say whether a shrinking farm
    # is being harvested or is dying, and those prescribe opposite fixes, so the
    # three flows are reported per day alongside the net change they must explain.
    flows = ("planted", "harvested", "EXP_MILKED", "EXP_UNPICKED", "THIRST",
             "OTHER")
    print(f"    {'window':>9} " + "".join(f"{k:>13}" for k in flows)
          + f"{'net/day':>9}   (per day; EXP_MILKED is no loss, "
          f"EXP_UNPICKED is pure waste)")
    for lo, hi in BUCKETS:
        sub = [r for r in rows if lo <= r["day"] <= hi]
        if not sub:
            continue
        ndays = (hi - lo + 1) * seeds
        v = {k: sum(r["flow"][k] for r in sub) / ndays for k in flows}
        tag = f"d{lo}-{hi}"
        if (lo, hi) == WINDOW:
            tag = f"*{tag}"
        net = v["planted"] - sum(v[k] for k in flows[1:])
        print(f"    {tag:>9} " + "".join(f"{v[k]:>13.1f}" for k in flows)
              + f"{net:>+9.1f}")

    # The window verdict: which single bucket holds the most hand-slots, and is
    # care demand actually unmet there.
    sub = [r for r in rows if WINDOW[0] <= r["day"] <= WINDOW[1]]
    if sub:
        w = collections.Counter()
        for r in sub:
            w.update(r["why"])
        n = max_hands * len(sub)
        care = w["CARE_OP"] / len(sub)          # care ops per turn
        demand = sum(r["thirsty"] for r in sub) / len(sub)
        crew = sum(r["n_hands"] for r in sub) / len(sub)
        top = max((k for k in REASONS if k != "CARE_OP"), key=lambda k: w[k])
        print(f"    day {WINDOW[0]}-{WINDOW[1]}: crew {crew:.1f}/{max_hands}, "
              f"{care:.2f} care ops/turn against {demand:.1f} unwatered crops; "
              f"biggest non-care bucket is {top} at {_pct(w[top], n):.1f}%")
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("agents", nargs="+")
    ap.add_argument("--opp", default=f"{ROOT}/agents/bench3/closer_cleo.py")
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--no-control", action="store_true",
                    help="skip the k01 known positive (do not use for a verdict)")
    a = ap.parse_args()

    max_hands = _max_hands()
    agents = list(a.agents)
    control = os.path.join(ROOT, "agents/champ/k01.py")
    if not a.no_control and os.path.exists(control) and control not in agents:
        agents.append(control)

    print(f"opponent {os.path.basename(a.opp)}, seeds {a.seeds}, "
          f"MAX_HANDS {max_hands} (ours; the engine has no crew cap)")
    peak = {}
    for ag in agents:
        name = os.path.basename(os.path.dirname(ag))
        if name in ("champ", "bench3", "spar"):
            name = os.path.basename(ag)[:-3]
        rows, ops, tiles = [], 0, 0
        for i in range(a.seeds):
            r, (po, pt) = probe(ag, a.opp, 10_000 + 977 * i, max_hands)
            rows += r
            ops += po
            tiles += pt
        # Hard gate, not a warning: under the wrong action/observation pairing
        # this ratio collapses, and every flow number below would be silently
        # attributed to the wrong turn.
        if tiles and ops < tiles:
            print(f"\nALIGN-FAIL {name}: {tiles} tiles became PLANT but only "
                  f"{ops} of them had a PLANT op issued there. The "
                  f"action/observation pairing is wrong; no number below is "
                  f"usable.")
            return 1
        print(f"\n  [align gate] {name}: {ops}/{tiles} new PLANT tiles "
              f"explained by a PLANT op at that tile")
        report(name, rows, max_hands, a.seeds)
        peak[name] = max(r["n_hands"] for r in rows)

    print("\npeak crew ever held (against our own MAX_HANDS bound):")
    for name, n in peak.items():
        flag = "  <-- EXCEEDS our action space" if n > max_hands else ""
        print(f"    {name:<24} {n:>3}{flag}")
    print("CARE-GATE-DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
