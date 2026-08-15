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

Everything the per-step feature code needs comes from ONE pass over the
tile grids (analyze, memoised on observation identity): the scan dict for
masks/decode, the (2, C, N, N) encode block for obs.encode, the standing-asset
sums for obs.net_worth / obs.opp_visible_worth, and the herd size for the
BUY_WHEAT decode. It lives *here*, not in a separate module, because exported
agent directories copy exactly obs.py / actions.py / kg_rules.py (as
kg_rl_*) and must stay self-contained; obs.py imports it back under either
name and rl/fused.py re-exports it for engine-side callers.
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
# one shared single-pass board analysis per observation
# --------------------------------------------------------------------------
# Board channels mirror obs.py's layout exactly (obs.encode consumes .boards);
# obs.py owns the layout doc, this table must not drift from it.

_C = 24
# Flat offsets into one farm's (C, N, N) block viewed 1-D: channel*N*N, so a
# tile's cell for channel k is bf[k*100 + y*10 + x]. Integer indexing into the
# flat view stores the same float32 value as out[k, y, x] = v, ~2x cheaper.
_CROP_CH = {c: (5 + i) * N * N for i, c in enumerate(CROP_LIST)}
_ANIMAL_CH = {a: (15 + i) * N * N for i, a in enumerate(ANIMAL_LIST)}
_SEED_COST = {c: R.CROPS[c]["seed"] for c in CROP_LIST}
_CROP_BASE = {c: R.MARKET_PARAMS[c]["base"] for c in CROP_LIST}
_ANIMAL_COST = {a: R.ANIMALS[a]["cost"] for a in ANIMAL_LIST}
_ANIMAL_PROD_BASE = {a: R.MARKET_PARAMS[R.ANIMALS[a]["product"]]["base"]
                     for a in ANIMAL_LIST}
_FIRST_YIELD = {c: R.CROPS[c]["first_yield_day"] for c in CROP_LIST}
# Locked land is a whole-quadrant property (the engine initialises every
# non-NW tile "LOCKED" and BUY_LAND flips a full quadrant to None; nothing
# else creates or clears "LOCKED"), so channel 1 is block-written from
# unlocked_quadrants instead of tile by tile. Engine mapping: y < 5 is N,
# x < 5 is W; NW is always unlocked.
_LOCKED_BLOCKS = (("NE", (slice(0, 5), slice(5, 10))),
                  ("SW", (slice(5, 10), slice(0, 5))),
                  ("SE", (slice(5, 10), slice(5, 10))))


class Analysis:
    """Everything the per-step feature code re-derives from the tile grids,
    from ONE walk per farm: the scan dict (masks/decode), the (2, C, N, N)
    float32 encode block (obs.encode), the standing-asset sums at base prices
    (obs.net_worth / obs.opp_visible_worth) and the herd size (BUY_WHEAT
    decode). `boards` and `opp_assets` are None when built with full=False --
    scan-only callers (scripted opponents) never pay for the opponent walk or
    the numpy channel writes."""
    __slots__ = ("scan", "boards", "own_assets", "opp_assets", "herd")


def analyze(obs, full=True):
    """One pass over the player's tiles (and, when full, the opponent's)."""
    me = obs["player"]
    farms = obs["farms"]
    day = obs.get("day", 0)
    boards = np.zeros((2, _C, N, N), dtype=np.float32) if full else None

    s = {"empty": [], "weeds": [], "unwatered": [], "unfert": [], "harvest": [],
         "unfed": [], "uncared": [], "fert_ready": [],
         "coop_free": [], "pasture_free": []}
    empty, weeds, unwatered = s["empty"], s["weeds"], s["unwatered"]
    unfert, harvest, unfed = s["unfert"], s["harvest"], s["unfed"]
    uncared, fert_ready = s["uncared"], s["fert_ready"]
    coop_free, pasture_free = s["coop_free"], s["pasture_free"]

    farm = farms[me]
    if full:
        # Scalar stores go through a memoryview of the farm's flat block:
        # same float32 cast, ~25% cheaper than ndarray.__setitem__ (measured;
        # cast identity verified bit-for-bit in test_fused.py's gate).
        bf = memoryview(boards[0].reshape(-1))
        ch1 = boards[0, 1]
        unlocked = farm["unlocked_quadrants"]
        for q, block in _LOCKED_BLOCKS:
            if q not in unlocked:
                ch1[block] = 1.0                            # ch 1 locked
    else:
        bf = None
    own_assets = 0.0
    herd = 0
    tiles = farm["tiles"]
    for y in range(N):
        row = tiles[y]
        y10 = y * N
        for x, t in enumerate(row):
            if t is None:
                empty.append((x, y))
                if full:
                    bf[y10 + x] = 1.0                       # ch 0 empty
            elif t == "LOCKED":
                pass                                        # ch 1 already block-written
            elif isinstance(t, dict):
                # Engine tiles are disjoint (an occupied structure has
                # "animal" plus kind COOP/PASTURE; plants and weeds never
                # carry "animal"), so this single chain reproduces the
                # branch order of every walk it replaces.
                kind = t.get("kind")
                off = y10 + x
                if "animal" in t:
                    animal = t["animal"]
                    yu = t.get("yield_units", 0)
                    if not t["fed_today"]:
                        unfed.append((x, y))
                    if not t["cared_today"]:
                        uncared.append((x, y))
                    if t["fertilizer_available"]:
                        fert_ready.append((x, y))
                    if yu > 0:
                        harvest.append((x, y))
                    own_assets += _ANIMAL_COST[animal]
                    own_assets += yu * _ANIMAL_PROD_BASE[animal]
                    herd += 1
                    if full:
                        bf[_ANIMAL_CH[animal] + off] = 1.0  # ch 15..17 one-hot
                        bf[1000 + off] = yu / 6.0           # ch 10 yield
                        bf[1800 + off] = 1.0 if t.get("fed_today") else 0.0
                        bf[1900 + off] = 1.0 if t.get("cared_today") else 0.0
                        bf[2000 + off] = 1.0 if t.get("fertilizer_available") else 0.0
                        bf[2100 + off] = min(t.get("consecutive_unfed", 0), 2) / 2.0
                elif kind == "PLANT":
                    crop = t["crop"]
                    yu = t.get("yield_units", 0)
                    if not t["watered_today"]:
                        unwatered.append((x, y))
                    if t.get("fertilized_until_day", -1) < day:
                        unfert.append((x, y))
                    if yu > 0 and day - t["planted_day"] >= _FIRST_YIELD[crop]:
                        harvest.append((x, y))
                    own_assets += _SEED_COST[crop]
                    own_assets += yu * _CROP_BASE[crop]
                    if full:
                        bf[_CROP_CH[crop] + off] = 1.0      # ch 5..9 one-hot
                        bf[1000 + off] = yu / 6.0           # ch 10 yield
                        bf[1100 + off] = 1.0 if t.get("watered_today") else 0.0
                        bf[1300 + off] = min(t.get("consecutive_unwatered", 0), 2) / 2.0
                        fert_left = max(0, t.get("fertilized_until_day", -1) - day + 1)
                        bf[1200 + off] = min(fert_left, 3) / 3.0
                        bf[1400 + off] = min(day - t.get("planted_day", day), 12) / 12.0
                elif kind == "WEED":
                    weeds.append((x, y))
                    if full:
                        bf[200 + off] = 1.0                 # ch 2 weed
                elif kind == "COOP":
                    coop_free.append((x, y))
                    if full:
                        bf[300 + off] = 1.0                 # ch 3 empty coop
                elif kind == "PASTURE":
                    pasture_free.append((x, y))
                    if full:
                        bf[400 + off] = 1.0                 # ch 4 empty pasture

    opp_assets = None
    if full:
        fx, fy = farm["farmer"]
        bf[2200 + fy * N + fx] = 1.0                        # ch 22 farmer
        for hpos in farm.get("hands", []):
            bf[2300 + hpos[1] * N + hpos[0]] += 0.25        # ch 23 hands

        farm = farms[1 - me]
        bf = memoryview(boards[1].reshape(-1))
        ch1 = boards[1, 1]
        unlocked = farm["unlocked_quadrants"]
        for q, block in _LOCKED_BLOCKS:
            if q not in unlocked:
                ch1[block] = 1.0
        opp_assets = 0.0
        tiles = farm["tiles"]
        for y in range(N):
            row = tiles[y]
            y10 = y * N
            for x, t in enumerate(row):
                if t is None:
                    bf[y10 + x] = 1.0
                elif t == "LOCKED":
                    pass
                elif isinstance(t, dict):
                    kind = t.get("kind")
                    off = y10 + x
                    if "animal" in t:
                        animal = t["animal"]
                        yu = t.get("yield_units", 0)
                        opp_assets += _ANIMAL_COST[animal]
                        opp_assets += yu * _ANIMAL_PROD_BASE[animal]
                        bf[_ANIMAL_CH[animal] + off] = 1.0
                        bf[1000 + off] = yu / 6.0
                        bf[1800 + off] = 1.0 if t.get("fed_today") else 0.0
                        bf[1900 + off] = 1.0 if t.get("cared_today") else 0.0
                        bf[2000 + off] = 1.0 if t.get("fertilizer_available") else 0.0
                        bf[2100 + off] = min(t.get("consecutive_unfed", 0), 2) / 2.0
                    elif kind == "PLANT":
                        crop = t["crop"]
                        yu = t.get("yield_units", 0)
                        opp_assets += _SEED_COST[crop]
                        opp_assets += yu * _CROP_BASE[crop]
                        bf[_CROP_CH[crop] + off] = 1.0
                        bf[1000 + off] = yu / 6.0
                        bf[1100 + off] = 1.0 if t.get("watered_today") else 0.0
                        bf[1300 + off] = min(t.get("consecutive_unwatered", 0), 2) / 2.0
                        fert_left = max(0, t.get("fertilized_until_day", -1) - day + 1)
                        bf[1200 + off] = min(fert_left, 3) / 3.0
                        bf[1400 + off] = min(day - t.get("planted_day", day), 12) / 12.0
                    elif kind == "WEED":
                        bf[200 + off] = 1.0
                    elif kind == "COOP":
                        bf[300 + off] = 1.0
                    elif kind == "PASTURE":
                        bf[400 + off] = 1.0
        fx, fy = farm["farmer"]
        bf[2200 + fy * N + fx] = 1.0
        for hpos in farm.get("hands", []):
            bf[2300 + hpos[1] * N + hpos[0]] += 0.25

    a = Analysis()
    a.scan = s
    a.boards = boards
    a.own_assets = own_assets
    a.opp_assets = opp_assets
    a.herd = herd
    return a


_memo_obs = None
_memo_a = None


def _analysis(obs, full=True):
    """Memoised on observation object identity, like the old _scan: within a
    worker step every mask/decode/encode/net_worth call sees the same obs
    dict. A scan-only entry upgrades in place when someone then needs the
    boards."""
    global _memo_obs, _memo_a
    if obs is _memo_obs and (not full or _memo_a.boards is not None):
        return _memo_a
    a = analyze(obs, full)
    _memo_obs, _memo_a = obs, a
    return a


def _scan(obs):
    return _analysis(obs, full=False).scan


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
            d = abs(hx - t[0]) + abs(hy - t[1])  # _dist, inlined: hands x pool is the hot product
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
        herd = _analysis(obs, full=False).herd
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

# Structure spot list per animal, resolved once (COOP -> coop_free, ...).
_PLACE_SPOTS = [(a, "coop_free" if R.ANIMALS[a]["structure"] == "COOP"
                 else "pasture_free") for a in ANIMAL_LIST]


def farmer_mask(obs):
    # Built positionally in FARMER_ACTIONS order (PASS, moves, ops, DROP,
    # PLANT_<crop>..., PLACE_<animal>...); the per-name allow() closure and
    # its f-string keys were a measured ~11 us/step across both masks.
    farm, priv, inv, (fx, fy) = _me(obs)
    s = _scan(obs)
    day = obs.get("day", 0)
    shed = priv["shed"]
    seeds = priv["seeds"]
    empties = bool(s["empty"])
    vals = [
        True,                                   # PASS
        fy > 0,                                 # MOVE_N
        fy < N - 1,                             # MOVE_S
        fx < N - 1,                             # MOVE_E
        fx > 0,                                 # MOVE_W
        bool(s["unwatered"]),                   # WATER
        bool(s["harvest"]),                     # HARVEST
        bool(s["unfed"])                        # FEED
        and (inv.get("WHEAT", 0) > 0 or shed.get("WHEAT", 0) > 0),
        bool(s["uncared"]),                     # CARE
        bool(s["fert_ready"]),                  # COLLECT_FERT
        bool(s["unfert"])                       # FERTILIZE
        and (inv.get("FERTILIZER", 0) > 0 or shed.get("FERTILIZER", 0) > 0),
        bool(s["weeds"]),                       # DIG_WEED
        empties,                                # BUILD_COOP
        empties,                                # BUILD_PASTURE
        bool(inv),                              # DROP
    ]
    for c in CROP_LIST:                         # PLANT_<crop>
        vals.append(empties and seeds.get(c, 0) > 0 and day <= PLANT_DEADLINE[c])
    for a, spots in _PLACE_SPOTS:               # PLACE_<animal>
        vals.append((inv.get(a, 0) > 0 or shed.get(a, 0) > 0) and bool(s[spots]))
    return np.array(vals, dtype=bool)


def market_mask(obs):
    # Positional, in MARKET_ACTIONS order (NOOP, SELL_<p>..., BUY_SEED_<c>...,
    # BUY_WHEAT, BUY_FERT, BUY_<animal>..., BUY_LAND, HIRE).
    farm, priv, _inv, _pos = _me(obs)
    money = farm["money"]
    day = obs.get("day", 0)
    shed = priv["shed"]
    prices = obs["market"]["prices"]
    sget = shed.get
    vals = [True]                               # NOOP
    for p in PRODUCT_LIST:                      # SELL_<p>
        vals.append(sget(p, 0) > 0)
    for c in CROP_LIST:                         # BUY_SEED_<c>
        vals.append(money >= _SEED_COST[c] and day <= PLANT_DEADLINE[c])
    room = sum(shed.values()) < R.SHED_CAPACITY
    vals.append(room and money >= prices["WHEAT"] * 5)   # BUY_WHEAT
    vals.append(room and money >= prices["FERTILIZER"])  # BUY_FERT
    for a in ANIMAL_LIST:                       # BUY_<animal>
        vals.append(room and money >= _ANIMAL_COST[a])
    n_extra = len(farm["unlocked_quadrants"]) - 1
    vals.append(n_extra < len(R.LAND_PRICES)    # BUY_LAND
                and money >= R.LAND_PRICES[n_extra])
    vals.append(len(farm.get("hands", [])) < MAX_HANDS   # HIRE
                and money >= _fib(farm.get("hires_today", 0)))
    return np.array(vals, dtype=bool)
