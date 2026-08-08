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
}

MARKET = {
    "metered":  {"market": "metered"},    # hold below a price floor
    "flood":    {"market": "flood"},      # sell everything on sight
    "vault":    {"market": "vault"},      # hold until the endgame
    "adaptive": {"market": "adaptive"},   # mirror the opponent's observed sell rate
}

INTEL = {
    "blind":    {"intel": "blind"},
    "frontrun": {"intel": "frontrun"},    # sell into their imminent harvests
    "evade":    {"intel": "evade"},       # produce what they are not producing
    "spite":    {"intel": "spite"},       # normal while ahead, flood while behind
}

MUCK = {
    "muck":   {"muck": True,  "harvest_product": True},
    "nomuck": {"muck": False, "harvest_product": True},
    "dung":   {"muck": True,  "harvest_product": False},   # fertilizer only
}

AXES = [("land", LAND), ("labour", LABOUR), ("produce", PRODUCE),
        ("market", MARKET), ("intel", INTEL), ("muck", MUCK)]

REFERENCE = {"land": "estate", "labour": "crew", "produce": "mixedfarm",
             "market": "metered", "intel": "blind", "muck": "muck"}

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


PLANS = {"main": plan_main, "grid": plan_grid, "produce": plan_produce,
         "muck": plan_muck, "edge": plan_edge}


def plan_all():
    seen, out = set(), []
    for fn in (plan_main, plan_edge, plan_produce, plan_muck, plan_grid):
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
