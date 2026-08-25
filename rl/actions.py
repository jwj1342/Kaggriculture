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
    # metered selling, appended so every earlier index is stable: sell
    # ceil(half) of the holding. Measured on 13,183 recorded top-ladder
    # sell orders (rl/TODO.md #8): 47% are sell-ALL, the rest small
    # batches -- halving a few turns in a row composes any fraction.
    + [f"SELL_HALF_{p}" for p in PRODUCT_LIST]
)

N_FARMER = len(FARMER_ACTIONS)   # 23
N_MARKET = len(MARKET_ACTIONS)   # 31

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
    """The classic scheduler == every hand on AUTO (gate: test_multi M1)."""
    return _hands_actions_multi(obs, s, ())


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
        half = name.startswith("SELL_HALF_")
        p = name[len("SELL_HALF_"):] if half else name[len("SELL_"):]
        if day >= R.LIQUIDATE_DAY:
            # metering stops mattering at the buzzer: both flavours run
            # the whole-shed compound liquidation
            first = [["SELL", p, shed[p]]] if shed.get(p, 0) > 0 else []
            rest = [["SELL", q, shed[q]] for q in PRODUCT_LIST
                    if q != p and shed.get(q, 0) > 0]
            return (first + rest)[:R.MAX_ORDERS]
        n = shed.get(p, 0)
        if half:
            n = (n + 1) // 2
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
        # No floor under the budget cap: max(4, ...) let a bankrupt policy
        # keep hiring at fib pennies -- collapsed episodes showed 66-99 hires
        # on ~$0. Below $80 of cash the burst is simply empty.
        # Burst bound 10 = the order-slot cap, not 4: hands are DAY LABOUR
        # (the engine fires the whole crew at end of day), so a full crew
        # must be re-bought every morning -- at 4/action the policy needed
        # three HIREs a day and never learned the habit (the 4-hand
        # plateau); at 10 one action buys the working day.
        burst, cost_cap = [], 0.05 * farm["money"]
        hires = farm.get("hires_today", 0)
        while (len(burst) < 10 and n_hands + len(burst) < MAX_HANDS
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
# per-unit hand tasks (rl/TODO.md #0): the policy steers each hand
# --------------------------------------------------------------------------

# AUTO is the classic cascade above -- an all-AUTO policy is byte-identical
# to decode() (the gate is rl/tensor_env/test_multi.py). A named task locks
# that hand to ONE chore family this turn; IDLE passes. Claims ('taken') are
# shared across all hands in hand order, exactly as in the cascade.
# FEED is TASK-ONLY: AUTO hands never claim an unfed animal, so all-AUTO
# stays byte-identical to the classic cascade. It is the one consumable
# task -- a wheat-less FEED hand runs a shed PICKUP leg first (measured:
# barnyard's hands do 83% of its feeding, 181 FEEDs/episode; without this
# task the animal engine is capped by the farmer's 24 turns/day).
HAND_TASKS = ["AUTO", "IDLE", "HARVEST", "WATER", "CARE",
              "COLLECT_FERTILIZER", "DIG", "FEED", "PLANT", "FERTILIZE",
              "BUILD", "PLACE"]
N_HAND_TASK = len(HAND_TASKS)
_TASK_IDX = {n: i for i, n in enumerate(HAND_TASKS)}


def _hands_actions_multi(obs, s, tasks, farmer=None):
    """Per-hand chores under per-hand task choices.

    tasks: sequence of HAND_TASKS indices; entries beyond the live hand
    count are ignored, missing entries default to AUTO. The >=8-carry DROP
    leg applies to every non-IDLE task except a consumable-carrying FEED
    or FERTILIZE hand (both consume; unloading first would livelock the
    fetch trip); a task whose family has no target left PASSes.

    FERTILIZE is FEED with the item renamed: unfert plants as targets,
    FERTILIZER as the consumable, the same shed fetch leg and the same
    per-turn stock reservations in hand order.

    PLANT (like FEED, task-only: AUTO never plants) targets empty tiles;
    the crop is the farm's most-held VIABLE seed (held, and its
    PLANT_DEADLINE not passed; CROP_LIST order on ties -- the market head
    owns the mix via BUY_SEED), and this turn's planters share the
    pre-step seed stock in hand order, like FEED's wheat reservations.
    """
    farm, priv, _inv, _pos = _me(obs)
    hands = farm.get("hands", [])
    if not hands:
        return []
    shed = priv["shed"]
    free = {"COOP": s["coop_free"], "PASTURE": s["pasture_free"]}
    n_hands = len(hands)
    available = {
        animal: shed.get(animal, 0) + sum(
            inv.get(animal, 0)
            for inv in priv["inventories"][1:1 + n_hands])
        for animal in ANIMAL_LIST
    }
    placeable = [
        animal for animal in ANIMAL_LIST
        if available[animal] > 0 and free[R.ANIMALS[animal]["structure"]]
    ]
    place_animal = (max(placeable, key=lambda animal: available[animal])
                    if placeable else None)
    place_spots = (free[R.ANIMALS[place_animal]["structure"]]
                   if place_animal else [])
    place_left = shed.get(place_animal, 0) if place_animal else 0
    pool = ([("HARVEST", t) for t in s["harvest"]]
            + [("WATER", t) for t in s["unwatered"]]
            + [("CARE", t) for t in s["uncared"]]
            + [("COLLECT_FERTILIZER", t) for t in s["fert_ready"]]
            + [("DIG", t) for t in s["weeds"]]
            # BUILD and PLANT share EMPTY claims because they compete for tiles.
            + [("FEED", t) for t in s["unfed"]]
            + [("EMPTY", t) for t in s["empty"]]
            + [("FERTILIZE", t) for t in s["unfert"]]
            + [("PLACE", t) for t in place_spots])
    taken = set()
    acts = []
    invs = priv["inventories"]
    # this turn's fetchers share the pre-step shed stock, in hand order
    wheat_left = priv["shed"].get("WHEAT", 0)
    fert_left = priv["shed"].get("FERTILIZER", 0)
    seeds = priv["seeds"]
    day = obs.get("day", 0)
    viable = [c for c in CROP_LIST
              if seeds.get(c, 0) > 0 and day <= PLANT_DEADLINE[c]]
    plant_crop = max(viable, key=lambda c: seeds.get(c, 0)) if viable else None
    plant_left = seeds.get(plant_crop, 0) if plant_crop else 0
    # hands defer to the farmer: the engine's atomic PLANT validation
    # blocks a whole crop on over-demand, so a same-crop farmer PLANT
    # this turn takes one seed off the hands' budget
    if farmer and farmer[0] == "PLANT" and farmer[1] == plant_crop:
        plant_left -= 1
    for i, hpos in enumerate(hands):
        task = HAND_TASKS[tasks[i]] if i < len(tasks) else "AUTO"
        if task == "IDLE":
            acts.append(["PASS"])
            continue
        hx, hy = hpos[0], hpos[1]
        hinv = invs[i + 1] if i + 1 < len(invs) else {}
        carry = sum(hinv.values())
        if task == "FEED" and hinv.get("WHEAT", 0) <= 0:
            # wheat leg: only worth the trip while stock survives earlier
            # fetchers' reservations and an unfed target is still unclaimed
            if carry >= 8:
                acts.append(_goto_do((hx, hy), _SHED, ["DROP"]) or ["PASS"])
                continue
            has_target = any(o == "FEED" and j not in taken
                             for j, (o, _t) in enumerate(pool))
            if wheat_left <= 0 or not has_target:
                acts.append(["PASS"])
                continue
            if (hx, hy) in set(_SHED):
                qty = min(wheat_left, 8 - carry)
                wheat_left -= qty
                acts.append(["PICKUP", "WHEAT", qty])
            else:
                acts.append(_goto_do((hx, hy), _SHED, ["PASS"]) or ["PASS"])
            continue
        if task == "FERTILIZE" and hinv.get("FERTILIZER", 0) <= 0:
            # fertilizer leg: the FEED wheat trip, item for item
            if carry >= 8:
                acts.append(_goto_do((hx, hy), _SHED, ["DROP"]) or ["PASS"])
                continue
            has_target = any(o == "FERTILIZE" and j not in taken
                             for j, (o, _t) in enumerate(pool))
            if fert_left <= 0 or not has_target:
                acts.append(["PASS"])
                continue
            if (hx, hy) in set(_SHED):
                qty = min(fert_left, 8 - carry)
                fert_left -= qty
                acts.append(["PICKUP", "FERTILIZER", qty])
            else:
                acts.append(_goto_do((hx, hy), _SHED, ["PASS"]) or ["PASS"])
            continue
        if (task == "PLACE" and place_animal is not None
                and hinv.get(place_animal, 0) <= 0):
            if carry >= 8:
                acts.append(_goto_do((hx, hy), _SHED, ["DROP"]) or ["PASS"])
                continue
            has_target = any(op == "PLACE" and j not in taken
                             for j, (op, _target) in enumerate(pool))
            if place_left <= 0 or not has_target:
                acts.append(["PASS"])
                continue
            if (hx, hy) in set(_SHED):
                place_left -= 1
                acts.append(["PICKUP", place_animal, 1])
            else:
                acts.append(_goto_do((hx, hy), _SHED, ["PASS"]) or ["PASS"])
            continue
        if task == "PLACE" and place_animal is None:
            acts.append(["PASS"])
            continue
        if carry >= 8 and task not in ("FEED", "FERTILIZE", "PLACE"):
            acts.append(_goto_do((hx, hy), _SHED, ["DROP"]) or ["PASS"])
            continue
        if task == "BUILD" and not s["empty"]:
            acts.append(["PASS"])
            continue
        if task == "PLANT" and plant_left <= 0:
            # no seed survives earlier planters' reservations (or none held)
            acts.append(["PASS"])
            continue
        best, bestd = None, 10 ** 9
        for j, (_op, t) in enumerate(pool):
            if j in taken:
                continue
            if task == "AUTO":
                if _op in ("FEED", "EMPTY", "FERTILIZE", "PLACE"):
                    continue
            elif _op == "EMPTY":
                if task not in ("PLANT", "BUILD"):
                    continue
            elif _op != task:
                continue
            d = abs(hx - t[0]) + abs(hy - t[1])
            if d < bestd:
                best, bestd = j, d
        if best is None:
            acts.append(["PASS"])
            continue
        taken.add(best)
        op, t = pool[best]
        if op == "EMPTY" and task == "PLANT":
            plant_left -= 1  # reserved at claim time, walking hands included
        if (hx, hy) == t:
            if op == "EMPTY":
                acts.append(["PLANT", plant_crop] if task == "PLANT"
                            else ["BUILD_PASTURE"])
            elif op == "PLACE":
                acts.append(["PLACE", place_animal])
            else:
                acts.append([op])
        else:
            acts.append([_step_toward(hx, hy, t[0], t[1]) or "PASS"])
    return acts


def decode_multi(obs, f_idx, hand_idxs, m_idx):
    """(farmer, per-hand tasks, market) -> raw kaggle action dict."""
    s = _scan(obs)
    farmer = _farmer_action(obs, FARMER_ACTIONS[f_idx], s) or ["PASS"]
    return {"farmer": farmer,
            "hands": _hands_actions_multi(obs, s, hand_idxs, farmer),
            "market": _market_action(obs, MARKET_ACTIONS[m_idx])}


def hand_task_mask(obs):
    """(MAX_HANDS, N_HAND_TASK) bool: AUTO/IDLE always legal for live hands;
    a chore family is legal while it has at least one target; FEED needs an
    unfed animal plus reachable wheat (that hand's inventory or the shed);
    PLANT needs a viable farm seed (PLANT_DEADLINE not passed) plus an
    empty tile; BUILD needs an empty tile and the means to stock a pasture;
    PLACE needs a reachable animal and a free matching structure. Slots beyond
    the live hand count are IDLE-only (zero entropy, zero gradient)."""
    farm, priv, _inv, _pos = _me(obs)
    n_hands = len(farm.get("hands", []))
    s = _scan(obs)
    fam_has = {"HARVEST": bool(s["harvest"]), "WATER": bool(s["unwatered"]),
               "CARE": bool(s["uncared"]),
               "COLLECT_FERTILIZER": bool(s["fert_ready"]),
               "DIG": bool(s["weeds"])}
    chores = [fam_has[n] for n in HAND_TASKS[2:7]]
    day = obs.get("day", 0)
    plant_ok = (bool(s["empty"])
                and any(priv["seeds"].get(c, 0) > 0
                        and day <= PLANT_DEADLINE[c] for c in CROP_LIST))
    shed_wheat = priv["shed"].get("WHEAT", 0) > 0
    shed_fert = priv["shed"].get("FERTILIZER", 0) > 0
    unfert_any = bool(s["unfert"])
    min_animal = min(R.ANIMALS[a]["cost"] for a in ANIMAL_LIST)
    build_ok = bool(s["empty"]) and (
        farm.get("money", 0) >= min_animal
        or any(priv["shed"].get(a, 0) > 0 for a in ANIMAL_LIST))
    free = {"COOP": bool(s["coop_free"]),
            "PASTURE": bool(s["pasture_free"])}
    shed_place = any(
        priv["shed"].get(a, 0) > 0 and free[R.ANIMALS[a]["structure"]]
        for a in ANIMAL_LIST)
    invs = priv["inventories"]
    idle_only = [False, True] + [False] * (N_HAND_TASK - 2)
    rows = []
    for i in range(MAX_HANDS):
        if i >= n_hands:
            rows.append(list(idle_only))
            continue
        hinv = invs[i + 1] if i + 1 < len(invs) else {}
        feed_ok = bool(s["unfed"]) and (shed_wheat
                                        or hinv.get("WHEAT", 0) > 0)
        fert_ok = unfert_any and (shed_fert
                                  or hinv.get("FERTILIZER", 0) > 0)
        place_ok = shed_place or any(
            hinv.get(a, 0) > 0 and free[R.ANIMALS[a]["structure"]]
            for a in ANIMAL_LIST)
        rows.append([True, True] + list(chores) + [feed_ok, plant_ok,
                                                   fert_ok, build_ok,
                                                   place_ok])
    return rows


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
    for p in PRODUCT_LIST:                      # SELL_HALF_<p>
        vals.append(sget(p, 0) > 0)
    # Mechanics-dead endgame (the PLANT_DEADLINE pattern): on the
    # liquidation day with products in the shed, everything but selling is
    # dead -- post-deadline plants never mature, an animal placed now never
    # yields, escapes stop mattering, and stock held to the end realises
    # $0. SELL_<p> decodes compound into a full-shed liquidation here, so
    # any sell choice is a liquidation. Measured: five runs in a row left
    # 62-100 melons rotting in the shed behind a NOOP-happy argmax.
    if day >= R.LIQUIDATE_DAY:
        sellable = [sget(p, 0) > 0 for p in PRODUCT_LIST]
        if any(sellable):
            vals = ([False] + sellable
                    + [False] * (len(vals) - 1 - len(PRODUCT_LIST)))
    return np.array(vals, dtype=bool)
