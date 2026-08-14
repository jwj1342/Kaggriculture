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
C = 24

_QUADS = ["NE", "SW", "SE"]  # NW is always unlocked


def _encode_board(farm, out):
    """Fill one (C, N, N) block for one farm."""
    for y in range(N):
        row = farm["tiles"][y]
        for x in range(N):
            t = row[x]
            if t is None:
                out[0, y, x] = 1.0
            elif t == "LOCKED":
                out[1, y, x] = 1.0
            elif isinstance(t, dict):
                kind = t.get("kind")
                if kind == "WEED":
                    out[2, y, x] = 1.0
                elif kind == "PLANT":
                    out[5 + CROP_LIST.index(t["crop"]), y, x] = 1.0
                    out[10, y, x] = t.get("yield_units", 0) / 6.0
                    out[11, y, x] = 1.0 if t.get("watered_today") else 0.0
                    out[13, y, x] = min(t.get("consecutive_unwatered", 0), 2) / 2.0
                elif "animal" in t:
                    out[15 + ANIMAL_LIST.index(t["animal"]), y, x] = 1.0
                    out[10, y, x] = t.get("yield_units", 0) / 6.0
                    out[18, y, x] = 1.0 if t.get("fed_today") else 0.0
                    out[19, y, x] = 1.0 if t.get("cared_today") else 0.0
                    out[20, y, x] = 1.0 if t.get("fertilizer_available") else 0.0
                    out[21, y, x] = min(t.get("consecutive_unfed", 0), 2) / 2.0
                elif kind == "COOP":
                    out[3, y, x] = 1.0
                elif kind == "PASTURE":
                    out[4, y, x] = 1.0
    fx, fy = farm["farmer"]
    out[22, fy, fx] = 1.0
    for hx, hy in farm.get("hands", []):
        out[23, hy, hx] += 0.25


def _encode_board_days(farm, out, day):
    """Second pass for day-dependent channels (fert remaining, plant age)."""
    for y in range(N):
        row = farm["tiles"][y]
        for x in range(N):
            t = row[x]
            if isinstance(t, dict) and t.get("kind") == "PLANT":
                fert_left = max(0, t.get("fertilized_until_day", -1) - day + 1)
                out[12, y, x] = min(fert_left, 3) / 3.0
                out[14, y, x] = min(day - t.get("planted_day", day), 12) / 12.0


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
    for p in PRODUCT_LIST:
        g.append(prices[p] / R.MARKET_PARAMS[p]["base"] / 2.0)
    for p in PRODUCT_LIST:
        off = (R.MARKET_PARAMS[p]["I0"] - inv[p]) / R.MARKET_PARAMS[p]["T"]
        g.append(max(-3.0, min(3.0, off)) / 3.0)
    for p in PRODUCT_LIST:
        g.append(min(shed.get(p, 0), 60) / 60.0)
    for a in ANIMAL_LIST:
        g.append(min(shed.get(a, 0), 4) / 4.0)
    for c in CROP_LIST:
        g.append(min(seeds.get(c, 0), 20) / 20.0)
    for p in PRODUCT_LIST:
        g.append(min(carried.get(p, 0), 20) / 20.0)
    for q in _QUADS:
        g.append(1.0 if q in mine["unlocked_quadrants"] else 0.0)
    for q in _QUADS:
        g.append(1.0 if q in theirs["unlocked_quadrants"] else 0.0)
    unlocked = obs["town"]["unlocked_shops"]
    for s in SHOP_LIST:
        g.append(unlocked.count(s) / 4.0)
    g.append(len(unlocked) / 8.0)
    return g

G = 8 + 9 * 4 + 3 + 5 + 3 + 3 + 8 + 1
OBS_DIM = 2 * C * N * N + G


def encode(obs):
    """Raw obs dict (this player's view) -> float32 vector of OBS_DIM."""
    me = obs["player"]
    day = obs.get("day", 0)
    boards = np.zeros((2, C, N, N), dtype=np.float32)
    _encode_board(obs["farms"][me], boards[0])
    _encode_board_days(obs["farms"][me], boards[0], day)
    _encode_board(obs["farms"][1 - me], boards[1])
    _encode_board_days(obs["farms"][1 - me], boards[1], day)
    g = np.asarray(_global_features(obs), dtype=np.float32)
    assert g.shape[0] == G, f"global feature drift: {g.shape[0]} != {G}"
    return np.concatenate([boards.reshape(-1), g])


# --------------------------------------------------------------------------
# potential function for reward shaping
# --------------------------------------------------------------------------

def net_worth(obs):
    """Money plus everything convertible to money, at marginal current prices.

    Counts standing assets (planted crops, placed animals, accrued yield) so
    that planting/placing is not punished by the shaping delta. Marginal price
    overvalues big positions -- documented hacking risk, see README §5.
    """
    me = obs["player"]
    farm = obs["farms"][me]
    priv = obs["private"]
    prices = obs["market"]["prices"]

    worth = farm["money"]
    for item, n in priv["shed"].items():
        if n <= 0:
            continue
        if item in R.ANIMALS:
            worth += n * R.ANIMALS[item]["cost"]
        else:
            worth += n * prices[item]
    for c, n in priv["seeds"].items():
        worth += n * R.CROPS[c]["seed"]
    for invd in priv["inventories"]:
        for item, n in invd.items():
            if item in prices:
                worth += n * prices[item]
            elif item in R.ANIMALS:
                worth += n * R.ANIMALS[item]["cost"]
    for y in range(N):
        for x in range(N):
            t = farm["tiles"][y][x]
            if not isinstance(t, dict):
                continue
            if t.get("kind") == "PLANT":
                worth += R.CROPS[t["crop"]]["seed"]
                worth += t.get("yield_units", 0) * prices[t["crop"]]
            elif "animal" in t:
                a = R.ANIMALS[t["animal"]]
                worth += a["cost"]
                worth += t.get("yield_units", 0) * prices[a["product"]]
    return worth
