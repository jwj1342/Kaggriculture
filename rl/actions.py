"""Factored action space: a farmer head and a market head, both discrete.

Design (README §4): each farmer option is an *intent* ("water the nearest
unwatered plant"). decode() realises one greedy step of that intent per turn:
perform the op if standing on a target, else move one tile toward the nearest
target; intents that need stock (FEED wants WHEAT in hand) insert the
go-to-shed-and-PICKUP leg automatically. The executor is stateless -- the
policy re-decides every turn and may switch intents freely.

Masks cover mechanical feasibility only ("is there anything to water"), never
quality ("is watering wise"). They err permissive: anything that slips through
decodes to PASS, which the engine treats as a no-op anyway.

No HIRE in v0 -- hands are an M2 feature (shared per-unit policy).
"""

import os
import sys

import numpy as np

_AGENTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agents")
if _AGENTS not in sys.path:
    sys.path.insert(0, _AGENTS)

import kg_rules as R
from kg_rules import _dist, _shed_tiles, _step_toward

N = 10
CROP_LIST = list(R.CROPS)
ANIMAL_LIST = list(R.ANIMALS)
PRODUCT_LIST = list(R.PRODUCTS)

FARMER_ACTIONS = (
    ["PASS", "MOVE_N", "MOVE_S", "MOVE_E", "MOVE_W",
     "WATER", "HARVEST", "FEED", "CARE", "COLLECT_FERT", "FERTILIZE",
     "DIG_WEED", "BUILD_COOP", "BUILD_PASTURE", "DROP"]
    + [f"PLANT_{c}" for c in CROP_LIST]
    + [f"PLACE_{a}" for a in ANIMAL_LIST]
)

MARKET_ACTIONS = (
    ["NOOP"]
    + [f"SELL_{p}" for p in PRODUCT_LIST]
    + [f"BUY_SEED_{c}" for c in CROP_LIST]
    + ["BUY_WHEAT", "BUY_FERT"]
    + [f"BUY_{a}" for a in ANIMAL_LIST]
    + ["BUY_LAND"]
)

N_FARMER = len(FARMER_ACTIONS)   # 23
N_MARKET = len(MARKET_ACTIONS)   # 21

_MOVES = {"MOVE_N": "NORTH", "MOVE_S": "SOUTH", "MOVE_E": "EAST", "MOVE_W": "WEST"}
_SHED = _shed_tiles(N)


# --------------------------------------------------------------------------
# board scans
# --------------------------------------------------------------------------

def _me(obs):
    p = obs["player"]
    farm = obs["farms"][p]
    priv = obs["private"]
    inv = priv["inventories"][0] if priv["inventories"] else {}
    return farm, priv, inv, tuple(farm["farmer"])


def _targets(farm, pred):
    """All (x, y) whose tile satisfies pred. LOCKED tiles never qualify."""
    out = []
    for y in range(N):
        row = farm["tiles"][y]
        for x in range(N):
            t = row[x]
            if t != "LOCKED" and pred(t, x, y):
                out.append((x, y))
    return out


def _unlocked_empty(farm):
    return _targets(farm, lambda t, x, y: t is None)


def _plants(farm, pred=lambda t: True):
    return _targets(
        farm,
        lambda t, x, y: isinstance(t, dict) and t.get("kind") == "PLANT" and pred(t),
    )


def _animals(farm, pred=lambda t: True):
    return _targets(
        farm, lambda t, x, y: isinstance(t, dict) and "animal" in t and pred(t)
    )


def _harvestables(farm, day):
    def ok(t, x, y):
        if not isinstance(t, dict) or t.get("yield_units", 0) <= 0:
            return False
        if "animal" in t:
            return True
        if t.get("kind") == "PLANT":
            return day - t["planted_day"] >= R.CROPS[t["crop"]]["first_yield_day"]
        return False
    return _targets(farm, ok)


# --------------------------------------------------------------------------
# greedy one-step intent realisation
# --------------------------------------------------------------------------

def _goto_do(pos, targets, op):
    """op (a full action list) if standing on a target, else one step toward
    the nearest. None if there is nothing to do."""
    if not targets:
        return None
    fx, fy = pos
    if (fx, fy) in set(targets):
        return op
    tx, ty = min(targets, key=lambda t: (_dist(fx, fy, t[0], t[1]), t[1], t[0]))
    mv = _step_toward(fx, fy, tx, ty)
    return [mv] if mv else None


def _with_stock(obs, item, want, targets, op):
    """Like _goto_do but the op consumes `item` from the unit inventory:
    detour via the shed to PICKUP up to `want` units when running empty."""
    farm, priv, inv, pos = _me(obs)
    if inv.get(item, 0) > 0:
        return _goto_do(pos, targets, op)
    stock = priv["shed"].get(item, 0)
    if stock <= 0 or not targets:
        return None
    if pos in _SHED:
        return ["PICKUP", item, min(stock, want)]
    return _goto_do(pos, _SHED, ["PASS"])  # never lands on PASS: pos not in _SHED


def _farmer_action(obs, name):
    farm, priv, inv, pos = _me(obs)
    day = obs.get("day", 0)

    if name == "PASS":
        return ["PASS"]
    if name in _MOVES:
        return [_MOVES[name]]
    if name == "WATER":
        return _goto_do(pos, _plants(farm, lambda t: not t["watered_today"]), ["WATER"])
    if name == "HARVEST":
        return _goto_do(pos, _harvestables(farm, day), ["HARVEST"])
    if name == "FEED":
        return _with_stock(obs, "WHEAT", 10,
                           _animals(farm, lambda t: not t["fed_today"]), ["FEED"])
    if name == "CARE":
        return _goto_do(pos, _animals(farm, lambda t: not t["cared_today"]), ["CARE"])
    if name == "COLLECT_FERT":
        return _goto_do(pos, _animals(farm, lambda t: t["fertilizer_available"]),
                        ["COLLECT_FERTILIZER"])
    if name == "FERTILIZE":
        return _with_stock(obs, "FERTILIZER", 5,
                           _plants(farm, lambda t: t.get("fertilized_until_day", -1) < day),
                           ["FERTILIZE"])
    if name == "DIG_WEED":
        return _goto_do(
            pos,
            _targets(farm, lambda t, x, y: isinstance(t, dict) and t.get("kind") == "WEED"),
            ["DIG"],
        )
    if name in ("BUILD_COOP", "BUILD_PASTURE"):
        op = "BUILD_COOP" if name == "BUILD_COOP" else "BUILD_PASTURE"
        return _goto_do(pos, _unlocked_empty(farm), [op])
    if name == "DROP":
        if not inv:
            return None
        return _goto_do(pos, _SHED, ["DROP"])
    if name.startswith("PLANT_"):
        crop = name[len("PLANT_"):]
        if priv["seeds"].get(crop, 0) <= 0:
            return None
        return _goto_do(pos, _unlocked_empty(farm), ["PLANT", crop])
    if name.startswith("PLACE_"):
        animal = name[len("PLACE_"):]
        kind = R.ANIMALS[animal]["structure"]
        spots = _targets(
            farm,
            lambda t, x, y: isinstance(t, dict)
            and t.get("kind") == kind and "animal" not in t,
        )
        return _with_stock(obs, animal, 1, spots, ["PLACE", animal])
    return None


def _market_action(obs, name):
    farm, priv, inv, pos = _me(obs)
    shed = priv["shed"]
    if name == "NOOP":
        return []
    if name.startswith("SELL_"):
        p = name[len("SELL_"):]
        n = shed.get(p, 0)
        return [["SELL", p, n]] if n > 0 else []
    if name.startswith("BUY_SEED_"):
        return [["BUY_SEED", name[len("BUY_SEED_"):], 1]]
    if name == "BUY_WHEAT":
        return [["BUY_PRODUCT", "WHEAT", 5]]
    if name == "BUY_FERT":
        return [["BUY_PRODUCT", "FERTILIZER", 1]]
    if name.startswith("BUY_") and name[len("BUY_"):] in R.ANIMALS:
        return [["BUY_ANIMAL", name[len("BUY_"):], 1]]
    if name == "BUY_LAND":
        return [["BUY_LAND"]]
    return []


def decode(obs, f_idx, m_idx):
    """(farmer index, market index) -> raw kaggle action dict."""
    farmer = _farmer_action(obs, FARMER_ACTIONS[f_idx]) or ["PASS"]
    market = _market_action(obs, MARKET_ACTIONS[m_idx])
    return {"farmer": farmer, "hands": [], "market": market}


# --------------------------------------------------------------------------
# legality masks
# --------------------------------------------------------------------------

def farmer_mask(obs):
    farm, priv, inv, (fx, fy) = _me(obs)
    day = obs.get("day", 0)
    shed = priv["shed"]
    empties = bool(_unlocked_empty(farm))
    m = np.zeros(N_FARMER, dtype=bool)

    def allow(name, ok):
        if ok:
            m[FARMER_ACTIONS.index(name)] = True

    allow("PASS", True)
    allow("MOVE_N", fy > 0)
    allow("MOVE_S", fy < N - 1)
    allow("MOVE_E", fx < N - 1)
    allow("MOVE_W", fx > 0)
    allow("WATER", bool(_plants(farm, lambda t: not t["watered_today"])))
    allow("HARVEST", bool(_harvestables(farm, day)))
    allow("FEED", bool(_animals(farm, lambda t: not t["fed_today"]))
          and (inv.get("WHEAT", 0) > 0 or shed.get("WHEAT", 0) > 0))
    allow("CARE", bool(_animals(farm, lambda t: not t["cared_today"])))
    allow("COLLECT_FERT", bool(_animals(farm, lambda t: t["fertilizer_available"])))
    allow("FERTILIZE",
          bool(_plants(farm, lambda t: t.get("fertilized_until_day", -1) < day))
          and (inv.get("FERTILIZER", 0) > 0 or shed.get("FERTILIZER", 0) > 0))
    allow("DIG_WEED", bool(_targets(
        farm, lambda t, x, y: isinstance(t, dict) and t.get("kind") == "WEED")))
    allow("BUILD_COOP", empties)
    allow("BUILD_PASTURE", empties)
    allow("DROP", bool(inv))
    for c in CROP_LIST:
        allow(f"PLANT_{c}", empties and priv["seeds"].get(c, 0) > 0)
    for a in ANIMAL_LIST:
        kind = R.ANIMALS[a]["structure"]
        has = inv.get(a, 0) > 0 or shed.get(a, 0) > 0
        spot = bool(_targets(
            farm,
            lambda t, x, y: isinstance(t, dict)
            and t.get("kind") == kind and "animal" not in t,
        ))
        allow(f"PLACE_{a}", has and spot)
    return m


def market_mask(obs):
    farm, priv, inv, _pos = _me(obs)
    money = farm["money"]
    shed = priv["shed"]
    prices = obs["market"]["prices"]
    m = np.zeros(N_MARKET, dtype=bool)

    def allow(name, ok):
        if ok:
            m[MARKET_ACTIONS.index(name)] = True

    allow("NOOP", True)
    for p in PRODUCT_LIST:
        allow(f"SELL_{p}", shed.get(p, 0) > 0)
    for c in CROP_LIST:
        allow(f"BUY_SEED_{c}", money >= R.CROPS[c]["seed"])
    room = sum(shed.values()) < R.SHED_CAPACITY
    allow("BUY_WHEAT", room and money >= prices["WHEAT"] * 5)
    allow("BUY_FERT", room and money >= prices["FERTILIZER"])
    for a in ANIMAL_LIST:
        allow(f"BUY_{a}", room and money >= R.ANIMALS[a]["cost"])
    n_extra = len(farm["unlocked_quadrants"]) - 1
    allow("BUY_LAND",
          n_extra < len(R.LAND_PRICES) and money >= R.LAND_PRICES[n_extra])
    return m
