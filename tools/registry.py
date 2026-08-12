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
    "bigberrywool": {"crops": [["STRAWBERRY", 28, 19], ["MELON", 8, 18]],
                     "animals": {"COW": 4, "SHEEP": 8}},
    "berrymelon":   {"crops": [["STRAWBERRY", 24, 19], ["MELON", 14, 18]],
                     "animals": {"COW": 6, "SHEEP": 4}},

    # --- past `bigberry` again, now that watering costs half ----------------
    # The crop ladder peaked at 28 strawberry tiles when every tile was watered
    # every day. Alternate-day watering freed ~160 actions an episode, so the
    # tile budget is worth re-walking; these need the third quadrant.

    # --- the two shapes that beat `bigberry` on the ladder -------------------
    # Both hold three or four quadrants, leave 51-59 tiles idle, and out-sell us
    # on melon 107-120 to 72 while matching us on strawberry. A melon tile only
    # yields twice a season -- planted day 0 and again around day 12 -- so eight
    # tiles cap at 96 units and we realise 72. More melon tiles is the only way
    # to take more of a pool that is drained to the floor in every episode.

    # The shape that beat `bigberry` by 113k to 89k on the ladder. The tell is
    # in the seeds, not the board: they bought **107 strawberry seeds** and sold
    # 211 units, against our 37 seeds and 106 units. A strawberry tile hosts two
    # plantings a season, so 107 seeds needs about fifty tiles standing -- three
    # quadrants, and a target high enough that the buyer never stops.
    # --- around `marketgarden`, measured against the `bench` field ----------
    # It wins 83.9% there with the hiring ramp; these vary one thing at a time
    # so the optimum is walked out on a field that can actually rank things.
    "mgtight":      {"crops": [["STRAWBERRY", 16, 19], ["MELON", 8, 18]],
                     "animals": {"COW": 7, "SHEEP": 3}},
    # `mgtight` won the sweep at 90.2%, and the trend all the way down was
    # "smaller and denser" -- which is what the action budget would predict: a
    # tile the hands never reach is worse than no tile at all. These push past
    # it to find where it turns.
    "mgtightwide":  {"crops": [["STRAWBERRY", 16, 19], ["MELON", 10, 18]],
                     "animals": {"COW": 7, "SHEEP": 3}},
    # `mgtight` uses 34 of 50 tiles and still PASSes 30% of its actions. The
    # earlier wheat-filler test was confounded -- it sat on a 20-strawberry base
    # when 16 is the optimum -- so it is re-run here on the tight base, where
    # there are sixteen spare tiles and idle hands to work them.
    "mgtightgrain": {"crops": [["STRAWBERRY", 16, 19], ["MELON", 8, 18],
                               ["WHEAT", 14, 24]],
                     "animals": {"COW": 7, "SHEEP": 3}},
    "mgtightgrain2": {"crops": [["STRAWBERRY", 16, 19], ["MELON", 8, 18],
                                ["WHEAT", 24, 24]],
                      "animals": {"COW": 7, "SHEEP": 3}},
    "mgtightcarrot": {"crops": [["STRAWBERRY", 16, 19], ["MELON", 8, 18],
                                ["CARROT", 14, 25]],
                      "animals": {"COW": 7, "SHEEP": 3}},
    "mgtightherd":  {"crops": [["STRAWBERRY", 16, 19], ["MELON", 8, 18]],
                     "animals": {"COW": 9, "SHEEP": 5}},
    "mgtightboth":  {"crops": [["STRAWBERRY", 16, 19], ["MELON", 8, 18],
                               ["WHEAT", 12, 24]],
                     "animals": {"COW": 9, "SHEEP": 4}},
    # An animal affords four chainable actions on one tile -- FEED, CARE,
    # COLLECT_FERTILIZER, HARVEST -- and about 85% of the ladder leader's
    # zero-movement work comes from its thirteen animals against our ten. Herd
    # size was measured *before* the here-pass existed, so it is re-run.
    # --- the top of the leaderboard, read off Kaggle's daily episode dumps ---
    # 48 episodes averaging 3,068-3,218 rating, 96 farms (tools/topeps.py). The
    # median top farm: three quadrants, fourteen animals, fourteen hands at day
    # 20, 320 strawberry sold at 7.6 per planting, 38 idle tiles and 19 weeds it
    # never touches. It works 40.6% of its actions against our 21-27% and spends
    # 1.09 movement actions per action that works against our 1.85.
    #
    # Every one of those numbers was measured against a different, weaker field
    # before. This is the first time the target configuration has been visible.
    "apex":         {"crops": [["STRAWBERRY", 24, 19], ["MELON", 12, 18],
                               ["WHEAT", 10, 24]],
                     "animals": {"COW": 8, "SHEEP": 6}},
    "apexwide":     {"crops": [["STRAWBERRY", 28, 19], ["MELON", 14, 18],
                               ["WHEAT", 12, 24]],
                     "animals": {"COW": 9, "SHEEP": 5}},
    "apexherd":     {"crops": [["STRAWBERRY", 22, 19], ["MELON", 12, 18],
                               ["WHEAT", 10, 24]],
                     "animals": {"COW": 10, "SHEEP": 6}},

    # --- wheat as a four-day bridging loan, not a filler ---
    # Decoding the public meta's own opening (agents/ref/closer_cleo.py, days
    # 0-8) shows where our farm actually falls behind, and it is not day 15: it
    # is day 1. It puts 10 wheat + 7 melon in the ground on day 0, hires five
    # hands, buys the herd, and ends the day on $138; we end day 0 with nothing
    # planted and $552 in the bank, reach 8 plants by day 3 and sit there for
    # five days while it goes to 27. By day 8 it holds $2,328 against our $306.
    #
    # Wheat is why. Seed $10, first yield day 2, dead by day 4, $150 of produce
    # off one tile -- 15x in four days, against strawberry's 4.8x over ten --
    # and 4,000 units to the price floor, so the harvest can be dumped whole
    # without moving the market. The meta sells 40 units on day 5 and buys its
    # first strawberry seed with the proceeds.
    #
    # Every wheat atom above puts WHEAT last with a last-plant-day of 24, which
    # makes it a filler competing with strawberry for tiles and hands all season
    # -- and it lost by 31 points as recently as the last factorial. Listed
    # *first* with a last-plant-day of 4 it competes with nothing: the seed loop
    # walks `crop_plan` in order, so wheat gets the cash while strawberry is
    # still unaffordable, and it is dead and off the tiles before strawberry is
    # ready to take them. Same crop, opposite role.
    "mgboot":       {"crops": [["WHEAT", 12, 4], ["STRAWBERRY", 16, 19],
                               ["MELON", 8, 18]],
                     "animals": {"COW": 7, "SHEEP": 3}},
    "mgboot20":     {"crops": [["WHEAT", 20, 4], ["STRAWBERRY", 16, 19],
                               ["MELON", 8, 18]],
                     "animals": {"COW": 7, "SHEEP": 3}},
    # The meta buys melon on day 0 and strawberry only on day 4; this is its
    # ordering rather than ours.
    "mgbootmelon":  {"crops": [["WHEAT", 12, 4], ["MELON", 8, 18],
                               ["STRAWBERRY", 16, 19]],
                     "animals": {"COW": 7, "SHEEP": 3}},
    # One wheat generation is four days; this buys a second before handing over.
    "mgbootlong":   {"crops": [["WHEAT", 12, 8], ["STRAWBERRY", 16, 19],
                               ["MELON", 8, 18]],
                     "animals": {"COW": 7, "SHEEP": 3}},
    # If the bridge works, the farm it is bridging to should be bigger than the
    # one our scheduler could previously afford to start.
    "apexboot":     {"crops": [["WHEAT", 16, 4], ["STRAWBERRY", 24, 19],
                               ["MELON", 12, 18]],
                     "animals": {"COW": 8, "SHEEP": 6}},

    "berryflood":   {"crops": [["STRAWBERRY", 50, 19], ["MELON", 12, 18]],
                     "animals": {"COW": 6, "SHEEP": 6}},

    # --- filling the last ten days ------------------------------------------
    # Strawberry stops being worth planting on day 19 and each plant dies about
    # seventeen days after it goes in, so from roughly day 19 the tiles that
    # carried it stand empty -- measured on the ladder, we finish with 20 idle
    # tiles and 20 weeds while the season is still paying. Carrot yields three
    # units four days after planting and can still be sown on day 25; wheat
    # yields four in five days and doubles as feed. Listing them last in the
    # plan means they only ever take tiles the strawberry and melon do not
    # want.

    # --- soak up the idle labour --------------------------------------------
    # Read off the $160,864 opponent's replay, action by action. The gap is not
    # fertilizer: they issue 72 FERTILIZE against our 55. It is that **30% of
    # our actions are PASS and only 15% of theirs are** -- our hands run out of
    # work. They hold three quadrants, thirteen animals, and plant 148 wheat
    # seeds over the season, so there is always something to water and harvest:
    # 1,010 WATER and 390 HARVEST against our 368 and 119, and 42% of their
    # actions do work against our 21%.
    #
    # Wheat is the filler: $10 a seed, four units in five days, replantable to
    # day 24, and its market is 4,000 deep so the volume never crashes it.
    # Listed last so it only takes tiles the strawberry and melon do not want.
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


def plan_recheck():
    """Re-measure every axis around `mgtight`, on a field that can rank.

    Everything except `produce` was settled against anchors that lost to the
    whole library 97-100% of the time. Re-sweeping `produce` on `bench` moved
    the optimum by 32 points, so the rest is re-run rather than inherited.
    """
    out = []
    for labour, market, land, muck in itertools.product(
            ("crew", "gang", "crewrich", "handful", "gangtight", "lean"),
            ("flood", "metered", "adaptive", "paced"),
            ("smallhold", "estate", "homestead"),
            ("compost", "muck")):
        out.append({"land": land, "labour": labour, "produce": "mgtightgrain",
                    "market": market, "intel": "blind", "muck": muck,
                    "adapt": "shopwise"})
    return out


def plan_bench():
    """The standard reference field, and the reason it had to be replaced.

    Measured in run #22, every strategy in the library beats the old anchors --
    `estate-crew-berrybaron-flood-blind-muck`, `orchardherd`, and the submitted
    `enhanced` -- between 97% and 100% of the time. An anchor that loses to
    everything cannot rank anything. At the other end, `marketgarden` beat every
    other roster shape 53% to 90%, so the internal comparison was saturated too.

    This plan materialises a *spread*: the strongest shape of each production
    family, on both engines' worth of settings, so a new candidate is measured
    against opponents that are close to it rather than far below it. Use it as
    `--panel` for screens and as the fixed opponent set for ablations.
    """
    out = []
    # Regenerated 2026-08-11: the previous field had saturated again at 96%.
    # A reference must be able to beat the candidate sometimes.
    for produce in ("mgtightgrain", "mgtightwide", "mgtight", "mgtightgrain2",
                    "mgtightherd", "marketgarden", "bigberry", "berrymelon"):
        out.append({"land": "smallhold", "labour": "crew", "produce": produce,
                    "market": "flood", "intel": "blind", "muck": "compost",
                    "adapt": "shopwise"})
    # NOTE: the public reference agents in `agents/ref/` are not generated here
    # -- they are third-party code (MIT, see agents/ref/NOTICE) and four of them
    # replay the shared meta line that 79% of the top of the ladder runs. Add
    # them to any panel with `tournament.REF_PANEL`; a bench without them
    # measures our own family against itself.

    # One deliberate outlier, so the field is not all one idea. `orchardherd` is
    # weak as a *candidate* -- 36.5% -- and the third most informative opponent
    # in the whole panel, spreading candidates from 0% to 88.5%. Weak and
    # useless are different things.
    out.append({"land": "estate", "labour": "crew", "produce": "orchardherd",
                "market": "flood", "intel": "blind", "muck": "muck",
                "adapt": "fixed"})
    # `dairy` used to be the second outlier and was removed: over 7,296
    # episodes every one of ten candidates beat it in **every single episode**
    # -- mean 100.0%, standard deviation 0.0. An opponent with no variance
    # cannot rank anything, it just adds a constant to every score. Dropping it
    # and the three meta agents leaves the candidate ranking *completely
    # unchanged* (all ten hold their position) for 37% less compute.
    #
    # Keep the meta agents (`tournament.REF_PANEL`) even though they are
    # saturated the other way -- we win 0.2% against them. They are the target,
    # and they are the only local measurement of how far away it is. Report them
    # **separately** rather than averaging them in: three unbeatable opponents
    # in fifteen depress every headline number by about 25 points, which is how
    # "43%" turned out to mean "73.5% against opponents we can contest".
    #
    # What the panel still lacks is the middle. `tools/lines.py --emit` writes
    # the ladder's actual lines; `line1.py` sits at 66.6% against this panel,
    # just above our best engine's 60.9%, and is the most informative opponent
    # available. Add it with `--panel agents/bench3/*.py agents/lines/line1.py`.
    return out


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
    shapes = ("apex", "apexwide", "apexherd", "mgtightgrain")
    out = []
    for produce, land, labour in itertools.product(
            shapes, ("estate", "smallhold"), ("crew", "gang", "company")):
        out.append({"land": land, "labour": labour, "produce": produce,
                    "market": "flood", "intel": "blind", "muck": "compost",
                    "adapt": "shopwise"})
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


def plan_boot():
    """Does a four-day wheat bridge lift the ceiling that forced us small?

    A day-by-day comparison against the public meta (see the `mgboot` comment in
    PRODUCE) puts the divergence on day 1, not day 15: it has 17 plants down and
    $2 in the bank while we have 7 plants and $202, and by day 8 it holds
    $2,328 against our $306. Wheat -- $10 a seed, harvested day 2, gone day 4 --
    is what it opens with.

    The land axis rides along because the two are not independent. `smallhold`
    won every previous sweep on the argument that "a tile the hands never reach
    is worse than no tile", but that ceiling was measured on a farm that was
    broke until day 10. If the bridge works, the farm it can afford to service
    is a different farm, and `estate` -- the meta's own three-quadrant footprint
    -- has to be re-asked rather than inherited.
    """
    out = []
    for produce in ("mgtight", "mgboot", "mgboot20", "mgbootmelon",
                    "mgbootlong", "apexboot"):
        for land in ("smallhold", "estate"):
            out.append({"land": land, "labour": "crew", "produce": produce,
                        "market": "flood", "intel": "blind", "muck": "compost",
                        "adapt": "shopwise"})
    return out


PLANS = {"main": plan_main, "grid": plan_grid, "produce": plan_produce,
         "muck": plan_muck, "edge": plan_edge, "ladder": plan_ladder,
         "factorial": plan_factorial, "refine": plan_refine, "crop": plan_crop,
         "labour": plan_labour, "bench": plan_bench, "recheck": plan_recheck,
         "boot": plan_boot}


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
