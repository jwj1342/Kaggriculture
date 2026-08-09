#!/usr/bin/env python
"""Atomic strategy registry: definition, composition, and code generation.

A strategy is one option chosen from each of six **orthogonal atoms**. Because
the axes are independent, any assignment is a valid strategy and the whole
library is a cross product rather than a pile of hand-written agents.

    land     how much of the board to own
    labour   how many hands per day
    produce  what the farm makes
    market   how sale sizing reacts to price
    intel    whether the opponent's board changes behaviour
    muck     whether the free daily fertilizer is collected

Names are composed from the atoms, never versioned:

    estate-crew-mixedfarm-metered-blind-muck

so a name states exactly what the agent does and two identical configurations
can never end up with different names. A few well-known points on the grid also
carry a short alias.

    python tools/registry.py list                 # show the atom space
    python tools/registry.py gen --plan main      # generate a named plan
    python tools/registry.py gen --plan grid --out agents/lib
"""

import argparse
import hashlib
import itertools
import json
import os
import pprint
import sys

ENGINE = "agents/_engine.py"
LIB = "agents/lib"

# --------------------------------------------------------------------------
# The atoms
# --------------------------------------------------------------------------

LAND = {
    "homestead":    {"land": 1},   # NW only, never buys
    "smallhold":    {"land": 2},   # + NE
    "estate":       {"land": 3},   # + SW  (the public meta's footprint)
    "latifundium":  {"land": 4},   # + SE  (nobody on the ladder does this)
}

LABOUR = {
    "solo":   {"hands": 0,  "hire_frac": 0.0},
    "lean":   {"hands": 4,  "hire_frac": 0.06},
    "crew":   {"hands": 11, "hire_frac": 0.06},
    "swarm":  {"hands": 30, "hire_frac": 1.00},   # hires until broke
    # `crew` was tuned on an engine that starved its herd and churned its feed,
    # in an economy that ended the season around $40k. It now ends around $68k,
    # and 6% of a bigger pile buys a different number of hands, so the cap and
    # the head count are re-crossed here rather than inherited.
    #
    # `hire_frac` is a ceiling on *today's* payroll as a share of cash, and the
    # n-th hire of a day costs fib(n): the first eight together cost less than
    # one melon seed, the seventeenth alone more than the first fifteen.
    "handful":   {"hands": 6,  "hire_frac": 0.05},
    "gang":      {"hands": 14, "hire_frac": 0.08},
    "company":   {"hands": 18, "hire_frac": 0.12},
    "crewrich":  {"hands": 11, "hire_frac": 0.12},   # same crew, looser budget
    "gangtight": {"hands": 14, "hire_frac": 0.05},   # more hands, tighter budget
}

# Crop plans are (crop, target tiles, last day it can still be planted).
PRODUCE = {
    "melonrush":   {"crops": [["MELON", 40, 18]], "animals": {}},
    "berrypatch":  {"crops": [["STRAWBERRY", 40, 13]], "animals": {}},
    "graingrind":  {"crops": [["WHEAT", 40, 24]], "animals": {}},
    "rootcellar":  {"crops": [["CARROT", 40, 25]], "animals": {}},
    "vinehouse":   {"crops": [["TOMATO", 40, 19]], "animals": {}},
    "dairy":       {"crops": [], "animals": {"COW": 24}},
    "woolworks":   {"crops": [], "animals": {"SHEEP": 24}},
    "henhouse":    {"crops": [], "animals": {"GOOSE": 24}},
    "ranchmix":    {"crops": [], "animals": {"COW": 10, "SHEEP": 8, "GOOSE": 6}},
    "mixedfarm":   {"crops": [["MELON", 14, 18], ["STRAWBERRY", 14, 13], ["WHEAT", 20, 24]],
                    "animals": {"COW": 10, "SHEEP": 8, "GOOSE": 6}},
    "orchardherd": {"crops": [["MELON", 14, 18]], "animals": {"COW": 10, "SHEEP": 8}},
    "berryherd":   {"crops": [["STRAWBERRY", 16, 13]], "animals": {"COW": 10, "SHEEP": 8}},

    # --- reconstructed from real ladder opponents (docs/LADDER_FIELD.md) -----
    # These three are not designed; they are the shapes that actually beat us,
    # read out of 94 digested ladder replays. Keep them in the field so local
    # rank is measured against the competition rather than against ourselves.
    #
    # A strawberry planted on day 19 still catches one production tick on day
    # 29, so the replant window runs to 19 -- not to the 13 the older atoms
    # use, which leaves the tile idle for the last twelve days.
    "berrybaron":   {"crops": [["STRAWBERRY", 24, 19], ["MELON", 10, 18]],
                     "animals": {"COW": 8, "SHEEP": 6}},
    "grazier":      {"crops": [["WHEAT", 8, 24], ["MELON", 4, 18]],
                     "animals": {"COW": 14}},
    "marketgarden": {"crops": [["STRAWBERRY", 18, 19], ["MELON", 10, 18]],
                     "animals": {"COW": 8, "SHEEP": 3}},

    # --- exploring around the winner (run #8/#9) ----------------------------
    # `marketgarden` won the balanced factorial; these vary one thing at a time
    # around it. The quantities come from the engine's own arithmetic rather
    # than from taste:
    #
    #   sheep  interval 3, first yield day 6  -> 8 production events; CARE
    #          accrues +1 per fed-and-cared day and is spent on the next event,
    #          so ~4 wool an event, ~32 a season. Wool closes the season at
    #          120% of base and its market absorbs 390 -- we sell 39.
    #   cow    interval 2, first yield day 8  -> 11 events, ~3 milk each, ~33.
    #   tomato ongoing, interval 1, first yield day 8, dies after 4 ticks: 8
    #          units per planting when fertilized, in 12 days rather than
    #          strawberry's 16, from a $50 seed rather than $100.
    #
    # Last-plant days are the last day a planting still catches one tick:
    # strawberry 19, tomato 21, melon 18.
    "woolgarden":   {"crops": [["STRAWBERRY", 14, 19], ["MELON", 8, 18]],
                     "animals": {"SHEEP": 16}},
    "berrywool":    {"crops": [["STRAWBERRY", 16, 19], ["MELON", 6, 18]],
                     "animals": {"COW": 4, "SHEEP": 12}},
    "berrydairy":   {"crops": [["STRAWBERRY", 16, 19], ["MELON", 6, 18]],
                     "animals": {"COW": 12, "SHEEP": 4}},
    "evengarden":   {"crops": [["STRAWBERRY", 16, 19], ["MELON", 8, 18]],
                     "animals": {"COW": 8, "SHEEP": 8}},
    "tomatoherd":   {"crops": [["TOMATO", 18, 21], ["MELON", 6, 18]],
                     "animals": {"COW": 8, "SHEEP": 4}},
    "berrytomato":  {"crops": [["STRAWBERRY", 12, 19], ["TOMATO", 12, 21],
                               ["MELON", 6, 18]],
                     "animals": {"COW": 6, "SHEEP": 4}},
    "bigberry":     {"crops": [["STRAWBERRY", 28, 19], ["MELON", 8, 18]],
                     "animals": {"COW": 6, "SHEEP": 4}},
    "orchardgarden": {"crops": [["MELON", 14, 18], ["STRAWBERRY", 10, 19]],
                      "animals": {"COW": 8, "SHEEP": 6}},

    # --- pushing past `bigberry`, which won the crew slice of run #11 --------
    # More strawberry kept winning at every step so far, so these walk the
    # trade-off out until it stops: strawberry tiles up, melon and herd down.
    # Two quadrants is 50 tiles, so anything past ~46 needs the third.
    "berryfull":    {"crops": [["STRAWBERRY", 32, 19], ["MELON", 10, 18]],
                     "animals": {"COW": 6, "SHEEP": 6}},
    "hugeberry":    {"crops": [["STRAWBERRY", 36, 19], ["MELON", 6, 18]],
                     "animals": {"COW": 4, "SHEEP": 4}},
    "berryonly":    {"crops": [["STRAWBERRY", 40, 19]],
                     "animals": {"COW": 4, "SHEEP": 2}},
    "berrylean":    {"crops": [["STRAWBERRY", 32, 19], ["MELON", 8, 18]],
                     "animals": {"COW": 4, "SHEEP": 2}},
    "bigberrywool": {"crops": [["STRAWBERRY", 28, 19], ["MELON", 8, 18]],
                     "animals": {"COW": 4, "SHEEP": 8}},
    "bigberrycow":  {"crops": [["STRAWBERRY", 28, 19], ["MELON", 8, 18]],
                     "animals": {"COW": 10, "SHEEP": 2}},
    "berrymelon":   {"crops": [["STRAWBERRY", 24, 19], ["MELON", 14, 18]],
                     "animals": {"COW": 6, "SHEEP": 4}},

    # --- past `bigberry` again, now that watering costs half ----------------
    # The crop ladder peaked at 28 strawberry tiles when every tile was watered
    # every day. Alternate-day watering freed ~160 actions an episode, so the
    # tile budget is worth re-walking; these need the third quadrant.
    "berrysea":     {"crops": [["STRAWBERRY", 40, 19], ["MELON", 8, 18]],
                     "animals": {"COW": 6, "SHEEP": 4}},
    "berrymax":     {"crops": [["STRAWBERRY", 48, 19], ["MELON", 4, 18]],
                     "animals": {"COW": 4, "SHEEP": 2}},
    "berryherd2":   {"crops": [["STRAWBERRY", 36, 19], ["MELON", 8, 18]],
                     "animals": {"COW": 8, "SHEEP": 6}},

    # --- the two shapes that beat `bigberry` on the ladder -------------------
    # Both hold three or four quadrants, leave 51-59 tiles idle, and out-sell us
    # on melon 107-120 to 72 while matching us on strawberry. A melon tile only
    # yields twice a season -- planted day 0 and again around day 12 -- so eight
    # tiles cap at 96 units and we realise 72. More melon tiles is the only way
    # to take more of a pool that is drained to the floor in every episode.
    "laddergarden": {"crops": [["STRAWBERRY", 28, 19], ["MELON", 18, 18]],
                     "animals": {"COW": 6, "SHEEP": 6}},
    "bigberrymelon": {"crops": [["STRAWBERRY", 28, 19], ["MELON", 14, 18]],
                      "animals": {"COW": 6, "SHEEP": 4}},
    "melonberry":   {"crops": [["STRAWBERRY", 20, 19], ["MELON", 22, 18]],
                     "animals": {"COW": 6, "SHEEP": 4}},

    # The shape that beat `bigberry` by 113k to 89k on the ladder. The tell is
    # in the seeds, not the board: they bought **107 strawberry seeds** and sold
    # 211 units, against our 37 seeds and 106 units. A strawberry tile hosts two
    # plantings a season, so 107 seeds needs about fifty tiles standing -- three
    # quadrants, and a target high enough that the buyer never stops.
    "berryflood":   {"crops": [["STRAWBERRY", 50, 19], ["MELON", 12, 18]],
                     "animals": {"COW": 6, "SHEEP": 6}},
    "berrytide":    {"crops": [["STRAWBERRY", 42, 19], ["MELON", 12, 18]],
                     "animals": {"COW": 6, "SHEEP": 4}},
}

MARKET = {
    "metered":  {"market": "metered"},    # hold below a price floor
    "flood":    {"market": "flood"},      # sell everything on sight
    "vault":    {"market": "vault"},      # hold until the endgame
    "adaptive": {"market": "adaptive"},   # mirror the opponent's observed sell rate
    # Rate-matched to each product's own market rather than one rule for all
    # nine. Strawberry, wool and milk hit the $1 floor after 59-76 units while
    # the town takes 13-25 a day back out, so they are sold at about the drain
    # rate; melon is 158 deep and refilled one unit a day, so it is dumped; the
    # deep ones (wheat, egg, carrot, tomato, fertilizer) are dumped too.
    "paced":    {"market": "paced"},
}

INTEL = {
    "blind":    {"intel": "blind"},
    "frontrun": {"intel": "frontrun"},    # sell into their imminent harvests
    "evade":    {"intel": "evade"},       # produce what they are not producing
    "spite":    {"intel": "spite"},       # normal while ahead, flood while behind
}

# A seventh axis, and the first that is about the *town* rather than the farm or
# the opponent. Shops are drawn with replacement, so demand for a single product
# swings 49x between episodes; `fixed` bets on the average, `shopwise` reads the
# draw and re-weights the herd toward it.
ADAPT = {
    "fixed":    {"shopwise": False},
    "shopwise": {"shopwise": True},
}

MUCK = {
    "muck":   {"muck": True,  "harvest_product": True,  "fertilise": False},
    "nomuck": {"muck": False, "harvest_product": True,  "fertilise": False},
    "dung":   {"muck": True,  "harvest_product": False, "fertilise": False},
    # Spend the fertilizer on the crops instead of selling it. On an `ongoing`
    # crop it doubles every production tick (4 units per planting becomes 8);
    # on the rest it halves the watering actions. Ladder opponents do this and
    # no strategy in this library did, which is why every strawberry plan here
    # measured at exactly the unfertilized ceiling.
    "compost": {"muck": True, "harvest_product": True,  "fertilise": True},
}

AXES = [("land", LAND), ("labour", LABOUR), ("produce", PRODUCE),
        ("market", MARKET), ("intel", INTEL), ("muck", MUCK), ("adapt", ADAPT)]

REFERENCE = {"land": "estate", "labour": "crew", "produce": "mixedfarm",
             "market": "metered", "intel": "blind", "muck": "muck",
             "adapt": "fixed"}

# Short aliases for points on the grid worth talking about by name.
ALIASES = {
    ("homestead", "crew", "mixedfarm", "metered", "blind", "muck"): "cottage",
    ("estate", "crew", "mixedfarm", "metered", "blind", "muck"): "manor",
    ("homestead", "crew", "mixedfarm", "flood", "blind", "muck"): "firesale",
    ("homestead", "crew", "mixedfarm", "adaptive", "frontrun", "muck"): "mirror",
    ("estate", "solo", "mixedfarm", "metered", "blind", "muck"): "hermit",
    ("estate", "swarm", "mixedfarm", "metered", "blind", "muck"): "levy",
}


def name_of(combo):
    return "-".join(combo[k] for k, _ in AXES)


def config_of(combo):
    cfg = {"name": name_of(combo), "atoms": dict(combo)}
    for key, table in AXES:
        cfg.update(table[combo[key]])
    cfg.setdefault("crops", [])
    cfg.setdefault("animals", {})
    return cfg


# --------------------------------------------------------------------------
# Plans -- which slices of the cross product to materialise
# --------------------------------------------------------------------------

def plan_main():
    """One axis varied at a time from the reference. Isolates main effects."""
    out = [dict(REFERENCE)]
    for key, table in AXES:
        for opt in table:
            if opt == REFERENCE[key]:
                continue
            c = dict(REFERENCE)
            c[key] = opt
            out.append(c)
    return out


def plan_grid():
    """Full cross of the four structural axes, on the two best produce atoms."""
    out = []
    for land, labour, market, intel, produce in itertools.product(
            LAND, LABOUR, MARKET, INTEL, ("mixedfarm", "orchardherd")):
        out.append({"land": land, "labour": labour, "produce": produce,
                    "market": market, "intel": intel, "muck": "muck"})
    return out


def plan_produce():
    """Every production atom crossed with land and market."""
    out = []
    for produce, land, market in itertools.product(
            PRODUCE, ("homestead", "estate"), ("metered", "flood", "adaptive")):
        out.append({"land": land, "labour": "crew", "produce": produce,
                    "market": market, "intel": "blind", "muck": "muck"})
    return out


def plan_muck():
    """Fertilizer ablation across the animal-bearing produce atoms."""
    out = []
    for produce, muck, land in itertools.product(
            ("dairy", "woolworks", "henhouse", "ranchmix", "mixedfarm"),
            MUCK, ("homestead", "estate")):
        out.append({"land": land, "labour": "crew", "produce": produce,
                    "market": "metered", "intel": "blind", "muck": muck})
    return out


def plan_edge():
    """Deliberate boundary cases: the corners of the space."""
    corners = [
        # nothing at all
        {"land": "homestead", "labour": "solo", "produce": "graingrind",
         "market": "vault", "intel": "blind", "muck": "nomuck"},
        # maximum everything
        {"land": "latifundium", "labour": "swarm", "produce": "mixedfarm",
         "market": "flood", "intel": "spite", "muck": "muck"},
        # all land, no labour to work it
        {"land": "latifundium", "labour": "solo", "produce": "mixedfarm",
         "market": "metered", "intel": "blind", "muck": "muck"},
        # all labour, no land to work
        {"land": "homestead", "labour": "swarm", "produce": "mixedfarm",
         "market": "metered", "intel": "blind", "muck": "muck"},
        # pure denial: minimal self, dump everything
        {"land": "homestead", "labour": "lean", "produce": "rootcellar",
         "market": "flood", "intel": "spite", "muck": "muck"},
        # hoard everything and liquidate at the buzzer
        {"land": "estate", "labour": "crew", "produce": "mixedfarm",
         "market": "vault", "intel": "blind", "muck": "muck"},
        # animals but never collect the free fertilizer
        {"land": "estate", "labour": "crew", "produce": "ranchmix",
         "market": "metered", "intel": "blind", "muck": "nomuck"},
        # fertilizer only, never harvest a product
        {"land": "estate", "labour": "crew", "produce": "ranchmix",
         "market": "metered", "intel": "blind", "muck": "dung"},
    ]
    return corners


def plan_ladder():
    """The sparring field: shapes read off real ladder opponents.

    `tools/ladder.py` digested 94 episodes we actually played. Three archetypes
    account for nearly all of them, and every one of them owns three quadrants,
    fertilizes its crops, and leaves weeds standing. Each is materialised with
    and without `compost` so the fertilizer multiplier can be measured rather
    than assumed, and against `metered`/`flood` so sale sizing is not confounded
    with the production shape.

    Also included: the same three shapes on one quadrant, because "three
    quadrants" is the single largest disagreement between the real field and
    what this library measured, and it needs its own control.
    """
    out = []
    for produce, land, muck, market in itertools.product(
            ("berrybaron", "grazier", "marketgarden"),
            ("estate", "homestead"), ("compost", "muck"),
            ("metered", "flood")):
        out.append({"land": land, "labour": "crew", "produce": produce,
                    "market": market, "intel": "blind", "muck": muck})
    # The incumbent local champion and the strawberry plan that lost to it,
    # both given the fertilizer they never had. Same roster, one variable.
    for produce in ("orchardherd", "berryherd", "mixedfarm"):
        for muck in ("compost", "muck"):
            out.append({"land": "homestead", "labour": "crew", "produce": produce,
                        "market": "flood", "intel": "blind", "muck": muck})
    return out


def plan_factorial():
    """Every produce x land x muck x market, balanced by construction.

    The four axes the ladder pull put in question -- what to grow, how much land
    to hold, what to do with the fertilizer, and how fast to sell -- crossed
    completely, with labour and intel held at the options that measured best and
    are not in dispute.

    `market` is in here because of a measured interaction, not for completeness.
    Fertilizing strawberry raises the yield from 3.0 to 5.1 units per planting,
    but `flood` then dumps the extra into a pool that reaches its floor after 62
    units, and the fertilized agent *loses* while producing more. Fertilizer and
    sale sizing cannot be measured apart.

    Balance is the point. `docs/ATOM_EFFECTS.md` had to carry a standing warning
    that its main effects were confounded, because the older plans sample the
    axes unevenly: `orchardherd` appears in 256 strategies and `dairy` in 10, so
    a marginal mean over `produce` was partly a mean over the *company each atom
    keeps*. Here every cell has exactly one strategy and every marginal is a
    like-for-like comparison.
    """
    out = []
    for produce, land, muck, market in itertools.product(PRODUCE, LAND, MUCK, MARKET):
        out.append({"land": land, "labour": "crew", "produce": produce,
                    "market": market, "intel": "blind", "muck": muck})
    return out


def plan_refine():
    """Around the winner: produce x labour x intel x muck x market.

    Run #8 crossed produce with land, muck and market and settled `land` (two
    quadrants) but left `labour` and `intel` at their defaults, so neither has
    ever been measured against a field that can fertilize. This plan holds land
    at `smallhold` -- the measured best -- and crosses the two untested axes
    against the production shapes worth refining.
    """
    shapes = ("marketgarden", "berrybaron", "evengarden", "berrywool",
              "berrydairy", "woolgarden", "bigberry", "tomatoherd",
              "berrytomato", "orchardgarden")
    out = []
    for produce, labour, intel, muck, market in itertools.product(
            shapes, LABOUR, INTEL, ("compost", "muck"), ("flood", "adaptive")):
        out.append({"land": "smallhold", "labour": labour, "produce": produce,
                    "market": market, "intel": intel, "muck": muck})
    return out


def plan_crop():
    """Walk the strawberry/melon/herd trade-off out until it stops paying.

    Run #11 settled the axes that are not about *what to grow*: `crew` beats
    every other labour option by 39 points, `intel` is worth nothing at all
    (four options within 1.5 points of each other), `flood` edges `adaptive`.
    So those are fixed here and the tile budget is the only thing varied, plus
    land -- because past about 46 tiles the plan needs a third quadrant.
    """
    shapes = ("bigberry", "berrymelon", "berryfull", "marketgarden",
              "evengarden", "berrywool", "berrydairy", "bigberrymelon")
    out = []
    for produce, land, adapt, market in itertools.product(
            shapes, ("smallhold", "estate"), ("fixed", "shopwise"),
            ("flood",)):
        out.append({"land": land, "labour": "crew", "produce": produce,
                    "market": market, "intel": "blind", "muck": "muck",
                    "adapt": adapt})
    return out


def plan_labour():
    """Re-cross labour against the shapes that survived the crop ladder.

    Labour is the largest single effect measured anywhere in this project --
    `crew` beats `lean` by 39 points and `swarm` by 54 -- and its setting was
    inherited from an engine whose season ended around $40k rather than $68k.
    """
    shapes = ("bigberry", "bigberrywool", "berryfull", "marketgarden")
    out = []
    for produce, labour, land, market in itertools.product(
            shapes, LABOUR, ("smallhold", "estate"), ("flood", "metered")):
        if labour in ("solo", "swarm"):      # settled: 13.0%, both of them
            continue
        out.append({"land": land, "labour": labour, "produce": produce,
                    "market": market, "intel": "blind", "muck": "muck"})
    return out


PLANS = {"main": plan_main, "grid": plan_grid, "produce": plan_produce,
         "muck": plan_muck, "edge": plan_edge, "ladder": plan_ladder,
         "factorial": plan_factorial, "refine": plan_refine, "crop": plan_crop,
         "labour": plan_labour}


def plan_all():
    seen, out = set(), []
    for fn in (plan_main, plan_edge, plan_ladder, plan_produce, plan_muck, plan_grid):
        for c in fn():
            key = tuple(c[k] for k, _ in AXES)
            if key not in seen:
                seen.add(key)
                out.append(c)
    return out


PLANS["all"] = plan_all


# --------------------------------------------------------------------------
# Code generation
# --------------------------------------------------------------------------

START = "# === STRATEGY CONFIG (generated -- do not edit by hand) ==="
END = "# === END CONFIG ==="


def generate(combos, out_dir, engine_path=ENGINE):
    with open(engine_path) as f:
        src = f.read()
    if START not in src or END not in src:
        raise SystemExit("engine template is missing its CONFIG markers")
    head, rest = src.split(START, 1)
    _, tail = rest.split(END, 1)
    os.makedirs(out_dir, exist_ok=True)

    made = []
    for combo in combos:
        cfg = config_of(combo)
        alias = ALIASES.get(tuple(combo[k] for k, _ in AXES))
        if alias:
            cfg["alias"] = alias
        # Python literal, not JSON -- json.dumps emits `true`/`false`/`null`,
        # which are not valid Python and silently break the generated agent.
        body = f"{START}\nCONFIG = {pprint.pformat(cfg, indent=4, width=96, sort_dicts=False)}\n{END}"
        text = head + body + tail
        path = os.path.join(out_dir, cfg["name"] + ".py")
        with open(path, "w") as f:
            f.write(text)
        made.append({
            "name": cfg["name"], "alias": alias, "path": path,
            "atoms": dict(combo),
            "sha": hashlib.sha256(text.encode()).hexdigest()[:16],
        })
    return made


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    g = sub.add_parser("gen")
    g.add_argument("--plan", default="all", choices=sorted(PLANS))
    g.add_argument("--out", default=LIB)
    g.add_argument("--manifest", default=None)
    args = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)

    if args.cmd == "list":
        total = 1
        for key, table in AXES:
            total *= len(table)
            print(f"{key:9s} ({len(table)})")
            for opt, vals in table.items():
                mark = " *" if REFERENCE[key] == opt else "  "
                print(f"   {mark}{opt:14s} {json.dumps(vals)}")
        print(f"\nfull cross product: {total:,} strategies")
        print(f"reference: {name_of(REFERENCE)}")
        for k, v in PLANS.items():
            print(f"  plan {k:8s} -> {len(v()):>5,} strategies")
        return 0

    combos = PLANS[args.plan]()
    made = generate(combos, args.out)
    print(f"generated {len(made)} strategies into {args.out}/")
    path = args.manifest or os.path.join(args.out, "manifest.json")
    with open(path, "w") as f:
        json.dump(made, f, indent=1)
    print(f"manifest -> {path}")
    for m in made[:6]:
        print(f"  {m['name']}" + (f"  (alias {m['alias']})" if m["alias"] else ""))
    if len(made) > 6:
        print(f"  ... and {len(made) - 6} more")
    return 0


if __name__ == "__main__":
    sys.exit(main())
