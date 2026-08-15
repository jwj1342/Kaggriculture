"""Observation encoding: raw kaggle obs dict -> fixed-length float32 vector.

Layout (all indices computed at import, OBS_DIM is the single source of truth):

    [ own board  C*N*N ]  channel-major (C, y, x), flattened
    [ opp board  C*N*N ]  same channels, opponent's farm
    [ global     G     ]  money, clock, market, own private stocks, town

The board section keeps its (C, y, x) structure so a CNN can reshape it for
free later; the MLP just eats the flat vector.

The environment is *almost* fully observable: both farms, market inventory,
prices and shops are shared state. The opponent's shed/seeds are private and
absent here -- inferring them from market flow is an M2 feature, not v0.
"""

import math
import os
import sys

import numpy as np

_AGENTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agents")
if _AGENTS not in sys.path:
    sys.path.insert(0, _AGENTS)

import kg_rules as R

# The fused single-pass board analysis (boards block, scan dict, asset sums)
# lives in actions.py so that an exported agent directory -- this file plus
# actions.py and kg_rules.py under per-export kg_rl_*_<name> aliases -- stays
# self-contained. The sibling is found by transforming this module's own
# import name (obs -> actions), so any per-export suffix carries over and two
# exports in one process can never cross-bind through the module cache.
import importlib
try:
    _ACT = importlib.import_module(
        __name__.replace("obs", "actions") if "obs" in __name__ else "actions")
except ImportError:
    import actions as _ACT

N = 10  # boardSize; the whole repo assumes the default advanced game
CROP_LIST = list(R.CROPS)          # 5, fixed order
ANIMAL_LIST = list(R.ANIMALS)      # 3
PRODUCT_LIST = list(R.PRODUCTS)    # 9
SHOP_LIST = sorted(R.SHOPS)        # 8

# --- per-tile channels -----------------------------------------------------
# 0 empty  1 locked  2 weed  3 empty coop  4 empty pasture
# 5..9   crop one-hot            10 yield/6   11 watered  12 fert days/3
# 13 unwatered streak/2          14 plant age/12
# 15..17 animal one-hot          18 fed       19 cared    20 fert ready
# 21 unfed streak/2              22 farmer here            23 hands here/4
#
# This layout is the contract; the walk that fills it is actions.analyze
# (fused with the mask scan and the net-worth sums, one pass per farm).
C = 24

_QUADS = ["NE", "SW", "SE"]  # NW is always unlocked

# Per-product constants hoisted out of the per-step loop; the arithmetic in
# _global_features is unchanged (same ops, same order), only the nested dict
# lookups are pre-resolved.
_GF_BASE = [(p, R.MARKET_PARAMS[p]["base"]) for p in PRODUCT_LIST]
_GF_I0_T = [(p, R.MARKET_PARAMS[p]["I0"], R.MARKET_PARAMS[p]["T"])
            for p in PRODUCT_LIST]
_BASE_PRICES = {p: R.MARKET_PARAMS[p]["base"] for p in PRODUCT_LIST}


def _global_features(obs):
    me = obs["player"]
    farms = obs["farms"]
    mine, theirs = farms[me], farms[1 - me]
    priv = obs["private"]
    market = obs["market"]
    prices = market["prices"]
    inv = market["inventory"]
    shed = priv["shed"]
    seeds = priv["seeds"]
    carried = priv["inventories"][0] if priv["inventories"] else {}
    day, hour = obs.get("day", 0), obs.get("hour", 0)

    g = [
        day / 30.0,
        hour / 24.0,
        math.log1p(max(0.0, mine["money"])) / 12.0,
        math.log1p(max(0.0, theirs["money"])) / 12.0,
        len(mine.get("hands", [])) / 10.0,
        len(theirs.get("hands", [])) / 10.0,
        mine.get("hires_today", 0) / 8.0,
        sum(shed.values()) / R.SHED_CAPACITY,
    ]
    sget = shed.get
    cget = carried.get
    mq = mine["unlocked_quadrants"]
    tq = theirs["unlocked_quadrants"]
    unlocked = obs["town"]["unlocked_shops"]
    g += [prices[p] / base / 2.0 for p, base in _GF_BASE]
    g += [max(-3.0, min(3.0, (i0 - inv[p]) / tt)) / 3.0 for p, i0, tt in _GF_I0_T]
    g += [min(sget(p, 0), 60) / 60.0 for p in PRODUCT_LIST]
    g += [min(sget(a, 0), 4) / 4.0 for a in ANIMAL_LIST]
    g += [min(seeds.get(c, 0), 20) / 20.0 for c in CROP_LIST]
    g += [min(cget(p, 0), 20) / 20.0 for p in PRODUCT_LIST]
    g += [1.0 if q in mq else 0.0 for q in _QUADS]
    g += [1.0 if q in tq else 0.0 for q in _QUADS]
    cnt = {}
    for s in unlocked:  # one scan instead of eight .count() passes
        cnt[s] = cnt.get(s, 0) + 1
    g += [cnt.get(s, 0) / 4.0 for s in SHOP_LIST]
    g.append(len(unlocked) / 8.0)
    return g

G = 8 + 9 * 4 + 3 + 5 + 3 + 3 + 8 + 1
OBS_DIM = 2 * C * N * N + G


_BOARD_LEN = 2 * C * N * N


def encode(obs):
    """Raw obs dict (this player's view) -> float32 vector of OBS_DIM."""
    boards = _ACT._analysis(obs).boards
    g = _global_features(obs)
    assert len(g) == G, f"global feature drift: {len(g)} != {G}"
    out = np.empty(OBS_DIM, dtype=np.float32)
    out[:_BOARD_LEN] = boards.reshape(-1)
    out[_BOARD_LEN:] = g  # python floats -> float32, same cast as asarray
    return out


# --------------------------------------------------------------------------
# potential function for reward shaping
# --------------------------------------------------------------------------

def net_worth(obs):
    """Money plus everything convertible to money, at *base* prices.

    Base, not current, prices -- deliberately. Marking holdings to market made
    the shaping delta depend on the opponent: against a flooding seller,
    prices fall all episode, every held or standing unit bleeds value, and the
    locally optimal policy is to produce nothing. Measured twice as an erosion
    from ~12k to ~2k after the barnyard stage switch. At base prices,
    production is credited once when the unit exists and market swings only
    matter at the moment of sale (cash received vs base value released).
    """
    me = obs["player"]
    farm = obs["farms"][me]
    priv = obs["private"]
    prices = _BASE_PRICES  # read-only lookups; hoisted, values unchanged

    # End-game decay: over the last five days every non-cash asset ramps
    # linearly to worthless, money never does. Holding through the end is a
    # steady negative delta, selling converts decaying value into permanent
    # value -- liquidation discipline emerges from the reward shape instead
    # of a scripted rule. (Without it, an argmax policy finished with a full
    # shed, half its net worth unrealised.)
    t = obs.get("day", 0) * 24 + obs.get("hour", 0)
    decay = min(1.0, max(0.0, (720.0 - t) / 120.0))

    assets = 0.0
    # Land credit: neutralises the BUY_LAND cash dip in the shaping delta, the
    # same way seeds/animals are credited at cost.
    assets += sum(R.LAND_PRICES[:len(farm["unlocked_quadrants"]) - 1])
    for item, n in priv["shed"].items():
        if n <= 0:
            continue
        if item in R.ANIMALS:
            assets += n * R.ANIMALS[item]["cost"]
        else:
            assets += n * prices[item]
    for c, n in priv["seeds"].items():
        assets += n * R.CROPS[c]["seed"]
    for invd in priv["inventories"]:
        for item, n in invd.items():
            if item in prices:
                assets += n * prices[item]
            elif item in R.ANIMALS:
                assets += n * R.ANIMALS[item]["cost"]
    # Standing tiles (planted crops at seed cost + yield, placed animals at
    # cost + yield) come from the fused single pass in actions.analyze.
    assets += _ACT._analysis(obs).own_assets
    return farm["money"] + decay * assets


def opp_visible_worth(obs):
    """The opponent's *visible* wealth: money plus standing farm assets at
    base prices (their shed and seeds are private and excluded). Same
    end-game decay as net_worth. Used by the competitive shaping term -- the
    game is won on money DIFFERENCE, and suppressing the opponent's market
    (selling into their lanes) is as valuable as earning."""
    me = obs["player"]
    farm = obs["farms"][1 - me]
    t = obs.get("day", 0) * 24 + obs.get("hour", 0)
    decay = min(1.0, max(0.0, (720.0 - t) / 120.0))
    assets = float(sum(R.LAND_PRICES[:len(farm["unlocked_quadrants"]) - 1]))
    assets += _ACT._analysis(obs).opp_assets
    return farm["money"] + decay * assets
