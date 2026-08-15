"""Factored action space: a farmer head and a market head, both discrete.

Design (README §4): each farmer option is an *intent* ("water the nearest
unwatered plant"). decode() realises one greedy step of that intent per turn:
perform the op if standing on a target, else move one tile toward the nearest
target; intents that need stock (FEED wants WHEAT in hand) insert the
go-to-shed-and-PICKUP leg automatically. The executor is stateless -- the
policy re-decides every turn and may switch intents freely.

Hands are *scripted labour, strategic hiring*: the market head owns HIRE (when
and how deep into the fib cost curve), while a dispatcher assigns each hand one
greedy step of consumable-free chores (harvest > water > care > collect
fertilizer > dig weeds; drop off at the shed when loaded). The policy's lever
is the size and timing of the crew, not its micromanagement -- the crew axis
dominates every other axis (CLAUDE.md), so it cannot stay outside the action
space, but per-hand RL control is deliberately deferred.

Masks cover mechanical feasibility only ("is there anything to water"), never
quality ("is watering wise"). They err permissive: anything that slips through
decodes to PASS, which the engine treats as a no-op anyway.

Everything mask/decode needs comes from ONE pass over the player's board
(_scan, memoised on observation identity) -- this code runs three times per
step inside rollout workers and was the throughput bottleneck when each
predicate rescanned the board.
"""

import os
import sys

import numpy as np

_AGENTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agents")
if _AGENTS not in sys.path:
    sys.path.insert(0, _AGENTS)

import kg_rules as R
from kg_rules import _dist, _fib, _shed_tiles, _step_toward

N = 10
CROP_LIST = list(R.CROPS)
ANIMAL_LIST = list(R.ANIMALS)
PRODUCT_LIST = list(R.PRODUCTS)
MAX_HANDS = 12

# Mechanics-dead planting deadline: a crop planted after day
# 29 - first_yield_day can never yield anything before the episode ends, so
# PLANT/BUY_SEED past it are pure money burns -- mask them like any other
# impossibility. (Measured: an argmax policy sank $14k into post-deadline
# melon seeds in one episode.) This is derived from the yield mechanics, not
# a strategy preference; profitable-but-late planting stays available.
PLANT_DEADLINE = {c: 29 - R.CROPS[c]["first_yield_day"] for c in CROP_LIST}

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
    + ["BUY_LAND", "HIRE"]
)

N_FARMER = len(FARMER_ACTIONS)   # 23
N_MARKET = len(MARKET_ACTIONS)   # 22

_F_IDX = {name: i for i, name in enumerate(FARMER_ACTIONS)}
_M_IDX = {name: i for i, name in enumerate(MARKET_ACTIONS)}
_MOVES = {"MOVE_N": "NORTH", "MOVE_S": "SOUTH", "MOVE_E": "EAST", "MOVE_W": "WEST"}
_SHED = _shed_tiles(N)


def _me(obs):
    p = obs["player"]
    farm = obs["farms"][p]
    priv = obs["private"]
    inv = priv["inventories"][0] if priv["inventories"] else {}
    return farm, priv, inv, tuple(farm["farmer"])


# --------------------------------------------------------------------------
# one shared board scan per observation
# --------------------------------------------------------------------------

_memo_obs = None
_memo_scan = None


def _scan(obs):
    global _memo_obs, _memo_scan
    if obs is _memo_obs:
        return _memo_scan
    farm, _priv, _inv, _pos = _me(obs)
    day = obs.get("day", 0)
    s = {"empty": [], "weeds": [], "unwatered": [], "unfert": [], "harvest": [],
         "unfed": [], "uncared": [], "fert_ready": [],
         "coop_free": [], "pasture_free": []}
    tiles = farm["tiles"]
    for y in range(N):
        row = tiles[y]
        for x in range(N):
            t = row[x]
            if t is None:
                s["empty"].append((x, y))
            elif t == "LOCKED" or not isinstance(t, dict):
                continue
            elif "animal" in t:
                if not t["fed_today"]:
                    s["unfed"].append((x, y))
                if not t["cared_today"]:
                    s["uncared"].append((x, y))
                if t["fertilizer_available"]:
                    s["fert_ready"].append((x, y))
                if t.get("yield_units", 0) > 0:
                    s["harvest"].append((x, y))
            else:
                kind = t.get("kind")
                if kind == "PLANT":
                    if not t["watered_today"]:
                        s["unwatered"].append((x, y))
                    if t.get("fertilized_until_day", -1) < day:
                        s["unfert"].append((x, y))
                    if (t.get("yield_units", 0) > 0
                            and day - t["planted_day"]
                            >= R.CROPS[t["crop"]]["first_yield_day"]):
                        s["harvest"].append((x, y))
                elif kind == "WEED":
                    s["weeds"].append((x, y))
                elif kind == "COOP":
                    s["coop_free"].append((x, y))
                elif kind == "PASTURE":
                    s["pasture_free"].append((x, y))
    _memo_obs, _memo_scan = obs, s
    return s


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


def _farmer_action(obs, name, s):
    farm, priv, inv, pos = _me(obs)

    if name == "PASS":
        return ["PASS"]
    if name in _MOVES:
        return [_MOVES[name]]
    if name == "WATER":
        return _goto_do(pos, s["unwatered"], ["WATER"])
    if name == "HARVEST":
        return _goto_do(pos, s["harvest"], ["HARVEST"])
    if name == "FEED":
        return _with_stock(obs, "WHEAT", 12, s["unfed"], ["FEED"])
    if name == "CARE":
        return _goto_do(pos, s["uncared"], ["CARE"])
    if name == "COLLECT_FERT":
        return _goto_do(pos, s["fert_ready"], ["COLLECT_FERTILIZER"])
    if name == "FERTILIZE":
        return _with_stock(obs, "FERTILIZER", 5, s["unfert"], ["FERTILIZE"])
    if name == "DIG_WEED":
        return _goto_do(pos, s["weeds"], ["DIG"])
    if name == "BUILD_COOP":
        return _goto_do(pos, s["empty"], ["BUILD_COOP"])
    if name == "BUILD_PASTURE":
        return _goto_do(pos, s["empty"], ["BUILD_PASTURE"])
    if name == "DROP":
        if not inv:
            return None
        return _goto_do(pos, _SHED, ["DROP"])
    if name.startswith("PLANT_"):
        crop = name[len("PLANT_"):]
        if priv["seeds"].get(crop, 0) <= 0:
            return None
        return _goto_do(pos, s["empty"], ["PLANT", crop])
    if name.startswith("PLACE_"):
        animal = name[len("PLACE_"):]
        kind = R.ANIMALS[animal]["structure"]
        spots = s["coop_free"] if kind == "COOP" else s["pasture_free"]
        return _with_stock(obs, animal, 1, spots, ["PLACE", animal])
    return None


# --------------------------------------------------------------------------
# scripted hands: consumable-free chores, one greedy step each
# --------------------------------------------------------------------------

def _hands_actions(obs, s):
    farm, priv, _inv, _pos = _me(obs)
    hands = farm.get("hands", [])
    if not hands:
        return []
    pool = ([("HARVEST", t) for t in s["harvest"]]
            + [("WATER", t) for t in s["unwatered"]]
            + [("CARE", t) for t in s["uncared"]]
            + [("COLLECT_FERTILIZER", t) for t in s["fert_ready"]]
            + [("DIG", t) for t in s["weeds"]])
    taken = set()
    acts = []
    invs = priv["inventories"]
    for i, hpos in enumerate(hands):
        hx, hy = hpos[0], hpos[1]
        hinv = invs[i + 1] if i + 1 < len(invs) else {}
        if sum(hinv.values()) >= 8:
            acts.append(_goto_do((hx, hy), _SHED, ["DROP"]) or ["PASS"])
            continue
        best, bestd = None, 10 ** 9
        for j, (_op, t) in enumerate(pool):
            if j in taken:
                continue
            d = _dist(hx, hy, t[0], t[1])
            if d < bestd:
                best, bestd = j, d
        if best is None:
            acts.append(["PASS"])
            continue
        taken.add(best)
        op, t = pool[best]
        if (hx, hy) == t:
            acts.append([op])
        else:
            acts.append([_step_toward(hx, hy, t[0], t[1]) or "PASS"])
    return acts


def _market_action(obs, name):
    """Decode one market-head option into up to 10 engine orders.

    Compound decodes, matched against barnyard's measured throughput (it fires
    up to 10 orders in one turn; a single-order head liquidates and hires an
    order of magnitude slower than every opponent in its band):
    - SELL_<p> on/after the liquidation day sells the *whole shed*, p first.
    - HIRE is a burst: up to 4 hires this turn while the fib cost stays small.
    - BUY_WHEAT scales with the herd instead of a flat 5.
    Head size is unchanged on purpose -- checkpoints keep resuming.
    """
    farm, priv, _inv, _pos = _me(obs)
    shed = priv["shed"]
    day = obs.get("day", 0)
    if name == "NOOP":
        return []
    if name.startswith("SELL_"):
        p = name[len("SELL_"):]
        if day >= R.LIQUIDATE_DAY:
            first = [["SELL", p, shed[p]]] if shed.get(p, 0) > 0 else []
            rest = [["SELL", q, shed[q]] for q in PRODUCT_LIST
                    if q != p and shed.get(q, 0) > 0]
            return (first + rest)[:R.MAX_ORDERS]
        n = shed.get(p, 0)
        return [["SELL", p, n]] if n > 0 else []
    if name.startswith("BUY_SEED_"):
        return [["BUY_SEED", name[len("BUY_SEED_"):], 1]]
    if name == "BUY_WHEAT":
        herd = sum(1 for row in farm["tiles"] for t in row
                   if isinstance(t, dict) and "animal" in t)
        return [["BUY_PRODUCT", "WHEAT", max(5, 2 * herd)]]
    if name == "BUY_FERT":
        return [["BUY_PRODUCT", "FERTILIZER", 1]]
    if name.startswith("BUY_") and name[len("BUY_"):] in R.ANIMALS:
        return [["BUY_ANIMAL", name[len("BUY_"):], 1]]
    if name == "BUY_LAND":
        return [["BUY_LAND"]]
    if name == "HIRE":
        n_hands = len(farm.get("hands", []))
        burst, cost_cap = [], max(4.0, 0.05 * farm["money"])
        hires = farm.get("hires_today", 0)
        while (len(burst) < 4 and n_hands + len(burst) < MAX_HANDS
               and _fib(hires + len(burst)) <= cost_cap):
            burst.append(["HIRE"])
        return burst or [["HIRE"]]
    return []


def decode(obs, f_idx, m_idx):
    """(farmer index, market index) -> raw kaggle action dict."""
    s = _scan(obs)
    farmer = _farmer_action(obs, FARMER_ACTIONS[f_idx], s) or ["PASS"]
    return {"farmer": farmer,
            "hands": _hands_actions(obs, s),
            "market": _market_action(obs, MARKET_ACTIONS[m_idx])}


# --------------------------------------------------------------------------
# legality masks
# --------------------------------------------------------------------------

def farmer_mask(obs):
    farm, priv, inv, (fx, fy) = _me(obs)
    s = _scan(obs)
    day = obs.get("day", 0)
    shed = priv["shed"]
    empties = bool(s["empty"])
    m = np.zeros(N_FARMER, dtype=bool)

    def allow(name, ok):
        if ok:
            m[_F_IDX[name]] = True

    allow("PASS", True)
    allow("MOVE_N", fy > 0)
    allow("MOVE_S", fy < N - 1)
    allow("MOVE_E", fx < N - 1)
    allow("MOVE_W", fx > 0)
    allow("WATER", bool(s["unwatered"]))
    allow("HARVEST", bool(s["harvest"]))
    allow("FEED", bool(s["unfed"])
          and (inv.get("WHEAT", 0) > 0 or shed.get("WHEAT", 0) > 0))
    allow("CARE", bool(s["uncared"]))
    allow("COLLECT_FERT", bool(s["fert_ready"]))
    allow("FERTILIZE", bool(s["unfert"])
          and (inv.get("FERTILIZER", 0) > 0 or shed.get("FERTILIZER", 0) > 0))
    allow("DIG_WEED", bool(s["weeds"]))
    allow("BUILD_COOP", empties)
    allow("BUILD_PASTURE", empties)
    allow("DROP", bool(inv))
    for c in CROP_LIST:
        allow(f"PLANT_{c}", empties and priv["seeds"].get(c, 0) > 0
              and day <= PLANT_DEADLINE[c])
    for a in ANIMAL_LIST:
        kind = R.ANIMALS[a]["structure"]
        has = inv.get(a, 0) > 0 or shed.get(a, 0) > 0
        spots = s["coop_free"] if kind == "COOP" else s["pasture_free"]
        allow(f"PLACE_{a}", has and bool(spots))
    return m


def market_mask(obs):
    farm, priv, _inv, _pos = _me(obs)
    money = farm["money"]
    day = obs.get("day", 0)
    shed = priv["shed"]
    prices = obs["market"]["prices"]
    m = np.zeros(N_MARKET, dtype=bool)

    def allow(name, ok):
        if ok:
            m[_M_IDX[name]] = True

    allow("NOOP", True)
    for p in PRODUCT_LIST:
        allow(f"SELL_{p}", shed.get(p, 0) > 0)
    for c in CROP_LIST:
        allow(f"BUY_SEED_{c}", money >= R.CROPS[c]["seed"]
              and day <= PLANT_DEADLINE[c])
    room = sum(shed.values()) < R.SHED_CAPACITY
    allow("BUY_WHEAT", room and money >= prices["WHEAT"] * 5)
    allow("BUY_FERT", room and money >= prices["FERTILIZER"])
    for a in ANIMAL_LIST:
        allow(f"BUY_{a}", room and money >= R.ANIMALS[a]["cost"])
    n_extra = len(farm["unlocked_quadrants"]) - 1
    allow("BUY_LAND",
          n_extra < len(R.LAND_PRICES) and money >= R.LAND_PRICES[n_extra])
    allow("HIRE",
          len(farm.get("hands", [])) < MAX_HANDS
          and money >= _fib(farm.get("hires_today", 0)))
    return m
