"""Factored action space for Kaggriculture RL.

A turn is decoded as (farm_task, market_mode):
- farm_task ∈ {IDLE, WATER, HARVEST, PLANT_WHEAT, ..., BUILD}
- market_mode ∈ {HOLD, METERED, DUMP, RESTOCK}

The decoder guarantees legality: every emitted action is a valid no-op at worst.
This module must stay pure-stdlib so it can be copied verbatim into the exported
single-file submission agent.
"""

import math

CROPS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"]
ANIMALS = ["COW", "SHEEP", "GOOSE"]
PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]

FARM_TASKS = [
    "IDLE", "WATER", "HARVEST",
    "PLANT_WHEAT", "PLANT_CARROT", "PLANT_TOMATO", "PLANT_STRAWBERRY", "PLANT_MELON",
    "FEED", "CARE", "COLLECT_FERT", "DIG", "BUILD",
]
MARKET_MODES = ["HOLD", "METERED", "DUMP", "RESTOCK"]

TASK_IDX = {name: i for i, name in enumerate(FARM_TASKS)}
MODE_IDX = {name: i for i, name in enumerate(MARKET_MODES)}

# Soft logit extras on top of the learned IDLE / RESTOCK priors.
# Split by calendar day (not raw 720-step index): watering, feed, and
# liquidation are daily. This is an emphasis, not a mask — illegal ops
# stay silent no-ops if the decoder cannot find a target.
PHASE_EARLY_LAST_DAY = 8    # days 0–8  (steps 0–215)
PHASE_LATE_FIRST_DAY = 28   # days 28–29 (steps 672–719)
PHASE_BUILD_BOOST = 2.0
PHASE_CHORE_BOOST = 1.5
PHASE_HARVEST_BOOST = 2.0
PHASE_DUMP_BOOST = 2.0
# feats[4] in rl.features.encode is clamp(step / 720)
STEP_FEATURE_INDEX = 4


def phase_index(day):
    """0 early / 1 mid / 2 late."""
    try:
        d = int(day)
    except (TypeError, ValueError):
        d = 0
    if d >= PHASE_LATE_FIRST_DAY:
        return 2
    if d <= PHASE_EARLY_LAST_DAY:
        return 0
    return 1


def day_from_step_feature(step_n):
    """Invert feats[4] = clamp(step / 720) back to a calendar day 0–29."""
    try:
        x = float(step_n)
    except (TypeError, ValueError):
        x = 0.0
    if x < 0.0:
        x = 0.0
    if x > 1.0:
        x = 1.0
    d = int(x * 30.0)
    if d < 0:
        return 0
    if d > 29:
        return 29
    return d


def phase_task_bias(day):
    """Length-13 extras for farmer / hand task logits."""
    b = [0.0] * len(FARM_TASKS)
    p = phase_index(day)
    if p == 0:
        b[TASK_IDX["BUILD"]] = PHASE_BUILD_BOOST
    elif p == 1:
        for name in ("WATER", "HARVEST", "FEED", "CARE"):
            b[TASK_IDX[name]] = PHASE_CHORE_BOOST
    else:
        b[TASK_IDX["HARVEST"]] = PHASE_HARVEST_BOOST
    return b


def phase_mode_bias(day):
    """Length-4 extras for market-mode logits. RESTOCK stays on the learned prior."""
    b = [0.0] * len(MARKET_MODES)
    if phase_index(day) == 2:
        b[MODE_IDX["DUMP"]] = PHASE_DUMP_BOOST
    return b


PHASE_TASK_BIAS = tuple(tuple(phase_task_bias(d)) for d in (0, 15, 28))
PHASE_MODE_BIAS = tuple(tuple(phase_mode_bias(d)) for d in (0, 15, 28))

# Targets aligned with agents/barnyard.py — IDLE fallback *is* the policy
# for most steps, so these numbers are the agent's economy, not decoration.
CROP_PLAN = [("MELON", 14, 18), ("STRAWBERRY", 14, 18), ("WHEAT", 20, 26)]
ANIMAL_TARGET = {"COW": 10, "SHEEP": 8, "GOOSE": 4}
TARGET_ANIMALS = sum(ANIMAL_TARGET.values())
HAND_CAP = 12
HIRE_BUDGET_FRAC = 0.06
LAND_PRICES = [1000, 2000, 4000]
MAX_QUADRANTS = 3
CASH_FLOOR = 800
WHEAT_PER_TRIP = 8
WHEAT_RESERVE_PER_ANIMAL = 2
WHEAT_RESERVE_CAP = 28
SHED_CAPACITY = 100
SHED_PRESSURE = 74
LIQUIDATE_DAY = 28
SELL_BATCH = 8
SELL_FLOOR = {
    "MELON": 0.45, "MILK": 0.55, "WOOL": 0.55, "STRAWBERRY": 0.55,
    "TOMATO": 0.55, "CARROT": 0.55, "EGG": 0.50, "WHEAT": 0.60,
    "FERTILIZER": 0.0,
}

# Replicated from engine so the agent is self-contained for the exported file.
CROP_DATA = {
    "WHEAT":      {"seed": 10,  "first_yield_day": 2,  "max_yield_day": 4,  "interval": 0, "max_yield": 6,  "ongoing": False},
    "CARROT":     {"seed": 20,  "first_yield_day": 2,  "max_yield_day": 3,  "interval": 0, "max_yield": 4,  "ongoing": False},
    "TOMATO":     {"seed": 50,  "first_yield_day": 8,  "max_yield_day": 8,  "interval": 1, "max_yield": 4,  "ongoing": True},
    "STRAWBERRY": {"seed": 100, "first_yield_day": 10, "max_yield_day": 10, "interval": 2, "max_yield": 4,  "ongoing": True},
    "MELON":      {"seed": 80,  "first_yield_day": 10, "max_yield_day": 12, "interval": 0, "max_yield": 6,  "ongoing": False},
}
ANIMAL_DATA = {
    "GOOSE": {"cost": 300, "structure": "COOP",    "first_yield_day": 4, "interval": 1, "max_held": 4, "product": "EGG"},
    "COW":   {"cost": 400, "structure": "PASTURE", "first_yield_day": 8, "interval": 2, "max_held": 6, "product": "MILK"},
    "SHEEP": {"cost": 500, "structure": "PASTURE", "first_yield_day": 6, "interval": 3, "max_held": 6, "product": "WOOL"},
}
WATER_MAX = {}
for _c, _d in CROP_DATA.items():
    if not _d["ongoing"]:
        _window = _d["max_yield_day"] - (_d["max_yield_day"] + 1) // 2 + 1
        WATER_MAX[_c] = min(_d["max_yield"], 1 + _window)
MARKET_PARAMS = {
    "WHEAT":      {"base": 25,  "I0": 10000, "T": 400, "below_func": "sqrt",   "below_target": 0.80, "above_func": "log",    "above_target": 0.20},
    "CARROT":     {"base": 35,  "I0": 10000, "T": 450, "below_func": "log",    "below_target": 0.20, "above_func": "sqrt",   "above_target": 0.70},
    "TOMATO":     {"base": 60,  "I0": 10000, "T": 200, "below_func": "linear", "below_target": 0.40, "above_func": "sqrt",   "above_target": 0.60},
    "STRAWBERRY": {"base": 120, "I0": 10000, "T": 100, "below_func": "sqrt",   "below_target": 0.70, "above_func": "linear", "above_target": 1.60},
    "MELON":      {"base": 250, "I0": 10000, "T": 300, "below_func": "log",    "below_target": 0.20, "above_func": "sq",     "above_target": 3.60},
    "EGG":        {"base": 50,  "I0": 10000, "T": 332, "below_func": "linear", "below_target": 0.40, "above_func": "log",    "above_target": 0.20},
    "MILK":       {"base": 160, "I0": 10000, "T": 122, "below_func": "sqrt",   "below_target": 0.60, "above_func": "linear", "above_target": 1.60},
    "WOOL":       {"base": 200, "I0": 10000, "T": 105, "below_func": "log",    "below_target": 0.20, "above_func": "sq",     "above_target": 3.20},
    "FERTILIZER": {"base": 100, "I0": 10000, "T": 200, "below_func": "linear", "below_target": 0.40, "above_func": "linear", "above_target": 0.40},
}

def _shape(func, x):
    x = max(0.0, x)
    if func == "linear": return x
    if func == "sq": return x * x
    if func == "sqrt": return math.sqrt(x)
    if func == "log": return math.log(1.0 + x)
    if func == "log10": return math.log10(1.0 + x)
    return x


def market_price(item, inventory):
    p = MARKET_PARAMS[item]
    base, i0, t = p["base"], p["I0"], p["T"]
    if inventory < i0:
        amp = p["below_target"] * base / _shape(p["below_func"], t)
        price = base + amp * _shape(p["below_func"], i0 - inventory)
    else:
        amp = p["above_target"] * base / _shape(p["above_func"], t)
        price = base - amp * _shape(p["above_func"], inventory - i0)
    return max(1, int(round(price)))


def _sell_qty(item, inv, held, cap, floor_frac):
    floor = MARKET_PARAMS[item]["base"] * floor_frac
    n = 0
    limit = min(cap, held)
    while n < limit and market_price(item, inv + n) >= floor:
        n += 1
    return n


def _get(d, k, default=None):
    if isinstance(d, dict):
        return d.get(k, default)
    return getattr(d, k, default)


def _safe_int(x, default=0):
    try:
        return int(x)
    except Exception:
        return int(default)


def _step_toward(fx, fy, tx, ty):
    if fx != tx and abs(fx - tx) >= abs(fy - ty):
        return "EAST" if tx > fx else "WEST"
    if fy != ty:
        return "SOUTH" if ty > fy else "NORTH"
    if fx != tx:
        return "EAST" if tx > fx else "WEST"
    return None


def _manhattan(ax, ay, bx, by):
    return abs(ax - bx) + abs(ay - by)


def _shed_access_tiles(board_size):
    half = board_size // 2
    return [(half - 1, half - 1), (half, half - 1), (half - 1, half), (half, half)]


def _quadrant_of(x, y, board_size):
    half = board_size // 2
    return ("N" if y < half else "S") + ("W" if x < half else "E")


def _scan(farm, board_size=10, day=0):
    tiles = _get(farm, "tiles") or []
    unlocked = _get(farm, "unlocked_quadrants") or ["NW"]
    cands = {t: [] for t in FARM_TASKS if t != "IDLE" and t != "BUILD"}
    builds = []
    for y, row in enumerate(tiles):
        for x, t in enumerate(row or []):
            if t is None:
                if _quadrant_of(x, y, board_size) in unlocked:
                    builds.append((x, y))
                continue
            if t == "LOCKED":
                continue
            if not isinstance(t, dict):
                continue
            kind = t.get("kind")
            if kind == "PLANT":
                crop = t.get("crop")
                if crop in CROPS:
                    age = int(day) - int(t.get("planted_day") or 0)
                    first = CROP_DATA.get(crop, {}).get("first_yield_day", 0)
                    if not t.get("watered_today") and t.get("consecutive_unwatered", 1) < 2:
                        cands["WATER"].append((x, y))
                    if t.get("yield_units", 0) > 0 and age >= first:
                        cands["HARVEST"].append((x, y))
                continue
            if "animal" in t:
                animal = t.get("animal")
                if animal in ANIMALS:
                    if not t.get("fed_today"):
                        cands["FEED"].append((x, y))
                    if not t.get("cared_today"):
                        cands["CARE"].append((x, y))
                    if t.get("fertilizer_available"):
                        cands["COLLECT_FERT"].append((x, y))
                continue
            if kind == "WEED":
                cands["DIG"].append((x, y))
                continue
    for crop in CROPS:
        cands["PLANT_" + crop] = list(builds)
    cands["BUILD"] = builds
    return cands


def _want_build(farm, priv):
    """Only convert soil to a structure when an unplaced animal needs housing."""
    shed = _get(priv, "shed") or {}
    empty_pasture = 0
    empty_coop = 0
    for row in _get(farm, "tiles") or []:
        for t in (row or []):
            if not isinstance(t, dict) or "animal" in t:
                continue
            if t.get("kind") == "PASTURE":
                empty_pasture += 1
            elif t.get("kind") == "COOP":
                empty_coop += 1
    if int(shed.get("COW", 0) or 0) + int(shed.get("SHEEP", 0) or 0) > empty_pasture:
        return "PASTURE"
    if int(shed.get("GOOSE", 0) or 0) > empty_coop:
        return "COOP"
    return None


def _unit_op(task, pos, inv, farm, priv, board_size, shed_capacity=100, cands=None, day=0):
    fx, fy = pos
    carrying = None
    for a in ANIMALS:
        if inv.get(a, 0) > 0:
            carrying = a
            break
    if carrying:
        for y, row in enumerate(_get(farm, "tiles") or []):
            for x, t in enumerate(row or []):
                if isinstance(t, dict) and t.get("kind") == ANIMAL_DATA[carrying]["structure"] and "animal" not in t:
                    if fx == x and fy == y:
                        return ["PLACE", carrying]
                    return [_step_toward(fx, fy, x, y)]
        return ["PASS"]

    if cands is None:
        cands = _scan(farm, board_size, day)
    if task == "FEED" and inv.get("WHEAT", 0) == 0:
        shed = _get(priv, "shed") or {}
        if shed.get("WHEAT", 0) > 0:
            shed_tiles = _shed_access_tiles(board_size)
            for tx, ty in shed_tiles:
                if fx == tx and fy == ty:
                    take = min(WHEAT_PER_TRIP, shed.get("WHEAT", 0))
                    if take > 0:
                        return ["PICKUP", "WHEAT", take]
                    return ["PASS"]
            sx, sy = shed_tiles[0]
            return [_step_toward(fx, fy, sx, sy)]
        return ["PASS"]

    if task == "BUILD":
        need = _want_build(farm, priv)
        if not need:
            return _default_task(pos, farm, priv, board_size, shed_capacity, cands=cands, allow_build=False)
        target_list = cands.get("BUILD", [])
        if not target_list:
            return ["PASS"]
        tx, ty = _nearest((fx, fy), target_list)[0]
        if tx is None:
            return ["PASS"]
        if fx == tx and fy == ty:
            return ["BUILD_COOP"] if need == "COOP" else ["BUILD_PASTURE"]
        return [_step_toward(fx, fy, tx, ty)]

    target_list = cands.get(task, [])
    if not target_list:
        return ["PASS"]
    tx, ty = _nearest((fx, fy), target_list)[0]
    if tx is None:
        return ["PASS"]
    if fx == tx and fy == ty:
        if task == "WATER": return ["WATER"]
        if task == "HARVEST": return ["HARVEST"]
        if task == "FEED": return ["FEED"]
        if task == "CARE": return ["CARE"]
        if task == "COLLECT_FERT": return ["COLLECT_FERTILIZER"]
        if task == "DIG": return ["DIG"]
        if task.startswith("PLANT_"):
            crop = task.split("_", 1)[1]
            return ["PLANT", crop]
        return ["PASS"]
    return [_step_toward(fx, fy, tx, ty)]


def _default_task(pos, farm, priv, board_size, shed_capacity=100, cands=None, allow_build=True, day=0):
    fx, fy = pos
    if cands is None:
        cands = _scan(farm, board_size, day)
    seeds = _get(priv, "seeds") or {}
    order = ["WATER", "HARVEST", "CARE", "FEED", "COLLECT_FERT",
             "PLANT_MELON", "PLANT_STRAWBERRY", "PLANT_WHEAT", "PLANT_CARROT", "PLANT_TOMATO",
             "DIG"]
    if allow_build and _want_build(farm, priv):
        order.append("BUILD")
    for task in order:
        if task.startswith("PLANT_") and seeds.get(task.split("_", 1)[1], 0) <= 0:
            continue
        tgt = cands.get(task, [])
        if tgt:
            tx, ty = _nearest((fx, fy), tgt)[0]
            if tx is not None:
                if fx == tx and fy == ty:
                    if task == "HARVEST": return ["HARVEST"]
                    if task == "WATER": return ["WATER"]
                    if task == "CARE": return ["CARE"]
                    if task == "FEED": return ["FEED"]
                    if task == "COLLECT_FERT": return ["COLLECT_FERTILIZER"]
                    if task == "DIG": return ["DIG"]
                    if task == "BUILD":
                        need = _want_build(farm, priv)
                        return ["BUILD_COOP"] if need == "COOP" else ["BUILD_PASTURE"]
                    if task.startswith("PLANT_"):
                        return ["PLANT", task.split("_", 1)[1]]
                return [_step_toward(fx, fy, tx, ty)]
    return ["PASS"]


def _nearest(pos, cands):
    fx, fy = pos
    best = None
    best_d = 1 << 30
    for (x, y) in cands:
        d = _manhattan(fx, fy, x, y)
        if d < best_d:
            best_d = d
            best = (x, y)
    return best, best_d


def _move(fx, fy, tx, ty):
    mv = _step_toward(fx, fy, tx, ty)
    return [mv] if mv else ["PASS"]


def _unit_states(farm, priv):
    farmer = tuple(_get(farm, "farmer") or [0, 0])
    hands = [tuple(p) for p in (_get(farm, "hands") or [])]
    invs = [dict(x or {}) for x in (_get(priv, "inventories") or [])]
    while len(invs) < 1 + len(hands):
        invs.append({})
    return [(farmer, invs[0])] + [(hands[i], invs[i + 1]) for i in range(len(hands))]


def _survey(farm, priv, board_size, day):
    tiles = _get(farm, "tiles") or []
    unlocked = list(_get(farm, "unlocked_quadrants") or ["NW"])
    plants, animals_live, weeds, free_tiles, empty_structs, owned = [], [], [], [], [], []
    counts = {a: 0 for a in ANIMALS}
    crop_counts = {c: 0 for c in CROPS}
    for y, row in enumerate(tiles):
        for x, t in enumerate(row or []):
            if t == "LOCKED":
                continue
            owned.append((x, y))
            if t is None:
                if _quadrant_of(x, y, board_size) in unlocked:
                    free_tiles.append((x, y))
            elif isinstance(t, dict):
                kind = t.get("kind")
                if kind == "WEED":
                    weeds.append((x, y))
                elif kind == "PLANT":
                    plants.append((x, y, t))
                    crop = t.get("crop")
                    if crop in crop_counts:
                        crop_counts[crop] += 1
                elif "animal" in t:
                    animals_live.append((x, y, t))
                    a = t.get("animal")
                    if a in counts:
                        counts[a] += 1
                else:
                    empty_structs.append((x, y, kind))
    return {
        "plants": plants, "animals": animals_live, "weeds": weeds,
        "free": free_tiles, "empty_structs": empty_structs, "owned": owned,
        "counts": counts, "crop_counts": crop_counts, "unlocked": unlocked,
    }


def _assign_all(farm, priv, board_size, day, task_names, shed_capacity=SHED_CAPACITY):
    """Assign one action per unit with claimed tiles (barnyard-style).

    Non-IDLE task names take their typed target first; remaining IDLE units
    share a priority queue so they do not pile onto the same plant.
    """
    units = _unit_states(farm, priv)
    n_units = len(units)
    ops = [["PASS"] for _ in range(n_units)]
    busy = [False] * n_units
    if n_units == 0:
        return ops

    S = _survey(farm, priv, board_size, day)
    shed = dict(_get(priv, "shed") or {})
    seeds = dict(_get(priv, "seeds") or {})
    invs = [u[1] for u in units]
    day = int(day)
    endgame = day >= LIQUIDATE_DAY
    shed_tiles = _shed_access_tiles(board_size)
    shed_set = set(shed_tiles)

    def shed_dist(x, y):
        return min(_manhattan(x, y, sx, sy) for sx, sy in shed_tiles)

    animals_in_shed = {a: int(shed.get(a, 0) or 0) for a in ANIMALS}
    animals_carried = {a: sum(int(iv.get(a, 0) or 0) for iv in invs) for a in ANIMALS}
    waiting = {a: animals_in_shed[a] + animals_carried[a] for a in ANIMALS}
    n_animals = len(S["animals"])
    n_pending = sum(waiting.values())

    owned = list(S["owned"])
    owned.sort(key=lambda p: (shed_dist(p[0], p[1]), p[1], p[0]))
    zone_cap = n_animals + 6 if day < 16 else TARGET_ANIMALS
    zone_size = min(max(0, len(owned) - 2),
                    max(4, n_animals + len(S["empty_structs"]) + n_pending + 3),
                    zone_cap)
    animal_zone = set(owned[:max(0, zone_size)])

    def walk_or_do(pos, tx, ty, action):
        fx, fy = pos
        if fx == tx and fy == ty:
            return action
        return _move(fx, fy, tx, ty)

    for i, (pos, inv) in enumerate(units):
        carrying = next((a for a in ANIMALS if int(inv.get(a, 0) or 0) > 0), None)
        if not carrying:
            continue
        kind = ANIMAL_DATA[carrying]["structure"]
        spots = [(x, y) for (x, y, k) in S["empty_structs"] if k == kind]
        if spots:
            (tx, ty), _ = _nearest(pos, spots)
            ops[i] = walk_or_do(pos, tx, ty, ["PLACE", carrying])
        else:
            ops[i] = ["PASS"]
        busy[i] = True

    cands = _scan(farm, board_size, day)
    claimed = set()

    def nearest_free(pos, tiles, op0):
        best, best_d = None, 1 << 30
        for (x, y) in tiles:
            if (x, y, op0) in claimed:
                continue
            d = _manhattan(pos[0], pos[1], x, y)
            if d < best_d:
                best, best_d = (x, y), d
        return best

    op0_map = {
        "WATER": ["WATER"], "HARVEST": ["HARVEST"], "FEED": ["FEED"], "CARE": ["CARE"],
        "COLLECT_FERT": ["COLLECT_FERTILIZER"], "DIG": ["DIG"],
    }
    for i, (pos, inv) in enumerate(units):
        if busy[i]:
            continue
        task = task_names[i] if i < len(task_names) else "IDLE"
        if task == "IDLE":
            continue
        if task == "FEED" and int(inv.get("WHEAT", 0) or 0) <= 0:
            if int(shed.get("WHEAT", 0) or 0) > 0:
                t_ = min(shed_tiles, key=lambda p: _manhattan(pos[0], pos[1], p[0], p[1]))
                if pos in shed_set:
                    take = min(WHEAT_PER_TRIP, int(shed.get("WHEAT", 0) or 0))
                    ops[i] = ["PICKUP", "WHEAT", take] if take > 0 else ["PASS"]
                else:
                    ops[i] = _move(pos[0], pos[1], t_[0], t_[1])
            else:
                ops[i] = ["PASS"]
            busy[i] = True
            continue
        if task == "BUILD":
            need = _want_build(farm, priv)
            tgt = nearest_free(pos, cands.get("BUILD", []), "BUILD")
            if need and tgt:
                claimed.add((tgt[0], tgt[1], "BUILD"))
                action = ["BUILD_COOP"] if need == "COOP" else ["BUILD_PASTURE"]
                ops[i] = walk_or_do(pos, tgt[0], tgt[1], action)
            else:
                ops[i] = ["PASS"]
            busy[i] = True
            continue
        if task.startswith("PLANT_"):
            action = ["PLANT", task.split("_", 1)[1]]
            op0 = "PLANT"
        else:
            action = op0_map.get(task, ["PASS"])
            op0 = action[0]
        tgt = nearest_free(pos, cands.get(task, []), op0)
        if tgt is None:
            ops[i] = ["PASS"]
        else:
            claimed.add((tgt[0], tgt[1], op0))
            ops[i] = walk_or_do(pos, tgt[0], tgt[1], action)
        busy[i] = True

    tasks = []
    unfed = 0
    if not endgame:
        for (x, y, t) in S["animals"]:
            starving = int(t.get("consecutive_unfed", 0) or 0) >= 1
            if not t.get("fed_today"):
                unfed += 1
                tasks.append((0 if starving else 6, x, y, ["FEED"], "WHEAT"))
            held = int(t.get("yield_units", 0) or 0)
            animal = t.get("animal")
            cap = ANIMAL_DATA.get(animal, {}).get("max_held", 6)
            if held >= cap:
                tasks.append((1, x, y, ["HARVEST"], None))
            if t.get("fertilizer_available"):
                tasks.append((4, x, y, ["COLLECT_FERTILIZER"], None))
            if not t.get("cared_today"):
                tasks.append((7, x, y, ["CARE"], None))
            if 0 < held < cap and held >= cap - 2:
                tasks.append((9, x, y, ["HARVEST"], None))

        for (x, y, t) in S["plants"]:
            crop = t.get("crop")
            cd = CROP_DATA.get(crop, {})
            age = day - int(t.get("planted_day") or 0)
            watered = t.get("watered_today", False)
            yu = int(t.get("yield_units", 0) or 0)
            thirsty = int(t.get("consecutive_unwatered", 0) or 0) >= 1
            if cd.get("ongoing"):
                if not watered:
                    tasks.append((2 if thirsty else 3, x, y, ["WATER"], None))
                if age >= cd.get("first_yield_day", 0) and yu >= 2:
                    tasks.append((3, x, y, ["HARVEST"], None))
            else:
                target = WATER_MAX.get(crop, cd.get("max_yield", 1))
                ripe = age >= cd.get("first_yield_day", 0) and (
                    yu >= target or age >= cd.get("max_yield_day", 0))
                if ripe:
                    tasks.append((1, x, y, ["HARVEST"], None))
                elif not watered:
                    window_start = (cd.get("max_yield_day", 0) + 1) // 2
                    in_window = window_start <= age <= cd.get("max_yield_day", 0)
                    if thirsty:
                        tasks.append((2, x, y, ["WATER"], None))
                    elif in_window and yu < target:
                        tasks.append((3 if crop == "MELON" else 8, x, y, ["WATER"], None))

        carried_wheat = sum(int(iv.get("WHEAT", 0) or 0) for iv in invs)
        wheat_gap = unfed - carried_wheat
        if wheat_gap > 0 and int(shed.get("WHEAT", 0) or 0) > 0:
            trips = min(n_units, -(-wheat_gap // WHEAT_PER_TRIP))
            take = min(WHEAT_PER_TRIP, int(shed.get("WHEAT", 0) or 0))
            for _ in range(max(0, trips)):
                tasks.append((1, None, None, ["PICKUP", "WHEAT", take], None))

        for _ in range(sum(animals_in_shed.values())):
            tasks.append((5, None, None, ["PICKUP_ANIMAL"], None))
        for (x, y, kind) in S["empty_structs"]:
            for a, ad in ANIMAL_DATA.items():
                if ad["structure"] == kind:
                    tasks.append((5, x, y, ["PLACE", a], a))

        free_pasture = sum(1 for e in S["empty_structs"] if e[2] == "PASTURE")
        free_coop = sum(1 for e in S["empty_structs"] if e[2] == "COOP")
        need_pasture = max(0, waiting["COW"] + waiting["SHEEP"] - free_pasture)
        need_coop = max(0, waiting["GOOSE"] - free_coop)
        money = float(_get(farm, "money") or 0)
        affordable_now = int(max(0.0, money - 300) // 450)
        room = max(0, TARGET_ANIMALS - n_animals - len(S["empty_structs"]))
        lookahead = max(0, min(affordable_now, 4) - need_pasture - need_coop)
        if S["crop_counts"].get("MELON", 0) < 10:
            lookahead = 0
        plan_pasture = max(0, ANIMAL_TARGET["COW"] + ANIMAL_TARGET["SHEEP"]
                           - S["counts"]["COW"] - S["counts"]["SHEEP"]
                           - free_pasture - need_pasture)
        build_queue = (["BUILD_PASTURE"] * need_pasture + ["BUILD_COOP"] * need_coop
                       + ["BUILD_PASTURE" if plan_pasture > 0 else "BUILD_COOP"] * lookahead)
        build_queue = build_queue[:room]

        plant_budget = {c: int(seeds.get(c, 0) or 0) for c in CROPS}
        want_crop = []
        for (crop, target, last_day) in CROP_PLAN:
            if day <= last_day:
                want_crop.append([crop, max(0, int(target) - S["crop_counts"].get(crop, 0))])

        for (x, y) in sorted(S["free"], key=lambda p: (shed_dist(p[0], p[1]), p[1], p[0])):
            if (x, y) in animal_zone:
                if build_queue:
                    tasks.append((5, x, y, [build_queue.pop(0)], None))
                continue
            for entry in want_crop:
                crop, remaining = entry
                if remaining > 0 and plant_budget.get(crop, 0) > 0:
                    tasks.append((6 if crop == "MELON" else 10, x, y, ["PLANT", crop], None))
                    plant_budget[crop] -= 1
                    entry[1] -= 1
                    break

        weed_prio = 6 if len(S["free"]) <= len(S["weeds"]) + 4 else 11
        for (x, y) in S["weeds"]:
            tasks.append((weed_prio, x, y, ["DIG"], None))
    else:
        for (x, y, t) in S["animals"]:
            if int(t.get("yield_units", 0) or 0) > 0:
                tasks.append((0, x, y, ["HARVEST"], None))
        for (x, y, t) in S["plants"]:
            crop = t.get("crop")
            cd = CROP_DATA.get(crop, {})
            if int(t.get("yield_units", 0) or 0) > 0 and (
                    day - int(t.get("planted_day") or 0) >= cd.get("first_yield_day", 0)):
                tasks.append((0, x, y, ["HARVEST"], None))

    tasks.sort(key=lambda t: t[0])
    shed_wheat_left = int(shed.get("WHEAT", 0) or 0)
    shed_animals_left = dict(animals_in_shed)
    shed_total = sum(int(v or 0) for v in shed.values())

    for (_prio, tx, ty, act, need) in tasks:
        op = act[0]
        if tx is None:
            best, best_d, best_t = None, None, None
            for k, (pos, inv) in enumerate(units):
                if busy[k]:
                    continue
                if op == "PICKUP" and int(inv.get("WHEAT", 0) or 0) >= WHEAT_PER_TRIP // 2:
                    continue
                if op == "PICKUP_ANIMAL" and any(int(inv.get(a, 0) or 0) for a in ANIMALS):
                    continue
                t_ = min(shed_tiles, key=lambda p: _manhattan(pos[0], pos[1], p[0], p[1]))
                d = _manhattan(pos[0], pos[1], t_[0], t_[1])
                if best_d is None or d < best_d:
                    best, best_d, best_t = k, d, t_
            if best is None:
                continue
            pos, inv = units[best]
            if pos in shed_set:
                if op == "PICKUP":
                    take = min(int(act[2]), shed_wheat_left)
                    if take <= 0:
                        continue
                    shed_wheat_left -= take
                    ops[best] = ["PICKUP", "WHEAT", take]
                else:
                    open_kinds = {e[2] for e in S["empty_structs"]}
                    pick = next((a for a in ("COW", "SHEEP", "GOOSE")
                                 if shed_animals_left.get(a, 0) > 0
                                 and ANIMAL_DATA[a]["structure"] in open_kinds), None)
                    if pick is None:
                        pick = next((a for a in ("COW", "SHEEP", "GOOSE")
                                     if shed_animals_left.get(a, 0) > 0), None)
                    if pick is None:
                        continue
                    shed_animals_left[pick] -= 1
                    ops[best] = ["PICKUP", pick, 1]
            else:
                ops[best] = _move(pos[0], pos[1], best_t[0], best_t[1])
            busy[best] = True
            continue

        op0 = act[0]
        if (tx, ty, op0) in claimed:
            continue
        best, best_d = None, None
        for k, (pos, inv) in enumerate(units):
            if busy[k]:
                continue
            if need is not None and int(inv.get(need, 0) or 0) <= 0:
                continue
            d = _manhattan(pos[0], pos[1], tx, ty)
            if best_d is None or d < best_d:
                best, best_d = k, d
        if best is None:
            continue
        pos, inv = units[best]
        ops[best] = walk_or_do(pos, tx, ty, act)
        busy[best] = True
        claimed.add((tx, ty, op0))

    for k, (pos, inv) in enumerate(units):
        if busy[k]:
            continue
        carrying = sum(int(v or 0) for v in inv.values())
        at_shed = pos in shed_set
        produce = sum(int(v or 0) for it, v in inv.items() if it in PRODUCTS and it != "WHEAT")
        if at_shed:
            if produce > 0 and shed_total < SHED_CAPACITY:
                ops[k] = ["DROP"]
            elif (not endgame) and n_animals > 0 and shed_wheat_left > 0 and int(inv.get("WHEAT", 0) or 0) < 2:
                take = min(WHEAT_PER_TRIP, shed_wheat_left)
                shed_wheat_left -= take
                ops[k] = ["PICKUP", "WHEAT", take]
            else:
                ops[k] = ["PASS"]
        elif produce >= 6 or endgame or carrying >= 12:
            t_ = min(shed_tiles, key=lambda p: _manhattan(pos[0], pos[1], p[0], p[1]))
            ops[k] = _move(pos[0], pos[1], t_[0], t_[1])
        else:
            ops[k] = ["PASS"]
        busy[k] = True
    return ops


def _append_sells(orders, shed, market, n_animals, endgame, pressure):
    m_inv = _get(market, "inventory") or {}
    sellable = []
    for item in PRODUCTS:
        held = int(shed.get(item, 0) or 0)
        if held <= 0:
            continue
        if item == "WHEAT" and not endgame:
            held = max(0, held - min(WHEAT_RESERVE_CAP, n_animals * WHEAT_RESERVE_PER_ANIMAL))
            if held <= 0:
                continue
        inv0 = int(m_inv.get(item, 10000) or 10000)
        price = market_price(item, inv0)
        sellable.append((price * min(held, SELL_BATCH), item, held, inv0))
    sellable.sort(reverse=True)
    for (_, item, held, inv0) in sellable:
        if len(orders) >= 10:
            break
        if endgame:
            qty = min(held, 40)
        elif pressure:
            qty = min(held, SELL_BATCH)
        else:
            qty = _sell_qty(item, inv0, held, SELL_BATCH, SELL_FLOOR.get(item, 0.55))
        if qty > 0:
            orders.append(["SELL", item, qty])
    return orders


def _market_orders(mode, farm, priv, market, step, day, board_size=10, hour=0):
    shed = dict(_get(priv, "shed") or {})
    seeds = dict(_get(priv, "seeds") or {})
    money = float(_get(farm, "money") or 0)
    orders = []
    S = _survey(farm, priv, board_size, day)
    n_animals = len(S["animals"])
    shed_total = sum(int(v or 0) for v in shed.values())
    endgame = int(day) >= LIQUIDATE_DAY or int(step) >= 680
    pressure = shed_total >= SHED_PRESSURE

    if mode == "HOLD" and not endgame:
        return orders

    if mode == "DUMP" or endgame:
        items = sorted(shed.keys(), key=lambda i: -market_price(i, (_get(market, "inventory") or {}).get(i, 10000)) * int(shed.get(i, 0) or 0) if i in MARKET_PARAMS else 0)
        for item in items:
            if len(orders) >= 10:
                break
            n = int(shed.get(item, 0) or 0)
            if n > 0 and item in PRODUCTS:
                orders.append(["SELL", item, n])
        return orders

    if mode == "METERED":
        return _append_sells(orders, shed, market, n_animals, False, pressure)

    if mode != "RESTOCK":
        return orders

    spend = 0.0

    def afford(cost):
        return money - spend >= cost

    # Sell first so hour-0 hiring cannot starve the 10-order cap.
    if not endgame:
        midgame = int(day) >= 6 or shed_total >= 12
        if midgame:
            _append_sells(orders, shed, market, n_animals, False, pressure)

        shed_tiles = _shed_access_tiles(board_size)

        def shed_dist(x, y):
            return min(_manhattan(x, y, sx, sy) for sx, sy in shed_tiles)

        owned = list(S["owned"])
        owned.sort(key=lambda p: (shed_dist(p[0], p[1]), p[1], p[0]))
        waiting_n = sum(int(shed.get(a, 0) or 0) for a in ANIMALS)
        zone_size = min(max(0, len(owned) - 2),
                        max(4, n_animals + len(S["empty_structs"]) + waiting_n + 3),
                        TARGET_ANIMALS)
        animal_zone = set(owned[:max(0, zone_size)])
        crop_room = sum(1 for p in S["free"] if p not in animal_zone)
        melon_have = S["crop_counts"].get("MELON", 0) + int(seeds.get("MELON", 0) or 0)

        # Seeds first: melon is the cash engine. Shrink k if a 4-pack does not fit.
        room_left = crop_room
        keep_cash = 400 if int(day) <= 2 else 100
        for (crop, target, last_day) in CROP_PLAN:
            if len(orders) >= 10 or room_left <= 0 or int(day) > last_day:
                continue
            have = S["crop_counts"].get(crop, 0) + int(seeds.get(crop, 0) or 0)
            if have >= target:
                continue
            cost1 = CROP_DATA[crop]["seed"]
            k = min(4, target - have, room_left)
            while k > 0 and not afford(cost1 * k + keep_cash):
                k -= 1
            if k > 0:
                orders.append(["BUY_SEED", crop, k])
                spend += cost1 * k
                room_left -= k

        if int(hour) <= 3:
            hires = int(_get(farm, "hires_today") or 0)
            payroll = sum(_hire_cost(i) for i in range(hires))
            budget = max(4.0, money * HIRE_BUDGET_FRAC)
            hired_now = 0
            while len(orders) < 10 and hires < HAND_CAP and hired_now < 7:
                cost = _hire_cost(hires)
                if payroll + cost > budget or not afford(cost + 40):
                    break
                orders.append(["HIRE"])
                spend += cost
                payroll += cost
                hires += 1
                hired_now += 1

        n_extra = len(S["unlocked"]) - 1
        if n_extra < min(len(LAND_PRICES), MAX_QUADRANTS - 1) and len(orders) < 10:
            price = LAND_PRICES[n_extra]
            reserve = [600, 1500, 3000][n_extra]
            if crop_room <= 8 and afford(price + reserve):
                orders.append(["BUY_LAND"])
                spend += price

        animals_in_shed = {a: int(shed.get(a, 0) or 0) for a in ANIMALS}
        n_pending = sum(animals_in_shed.values())
        housing_free = len(S["empty_structs"]) + max(0, TARGET_ANIMALS - n_animals - len(S["empty_structs"]))
        melon_ready = melon_have >= 8 or int(day) >= 4
        if (melon_ready and len(orders) < 10 and int(day) <= 23
                and n_pending < 2 and housing_free > n_pending
                and shed_total < SHED_CAPACITY - 8):
            invs = _get(priv, "inventories") or []
            carried = {a: sum(int((iv or {}).get(a, 0) or 0) for iv in invs) for a in ANIMALS}
            owned_of = {a: S["counts"][a] + animals_in_shed.get(a, 0) + carried.get(a, 0) for a in ANIMALS}
            want = None
            if owned_of["COW"] < ANIMAL_TARGET["COW"]:
                want = "COW"
            elif owned_of["SHEEP"] < ANIMAL_TARGET["SHEEP"]:
                want = "SHEEP"
            elif owned_of["GOOSE"] < ANIMAL_TARGET["GOOSE"] and int(day) >= 16:
                want = "GOOSE"
            if want is not None:
                cost = ANIMAL_DATA[want]["cost"]
                keep = 100 if int(day) < 12 else 400
                if afford(cost + keep):
                    orders.append(["BUY_ANIMAL", want, 1])
                    spend += cost

        need_wheat = min(WHEAT_RESERVE_CAP, max(n_animals, 1) * WHEAT_RESERVE_PER_ANIMAL)
        m_inv = _get(market, "inventory") or {}
        if (len(orders) < 10 and n_animals > 0
                and int(shed.get("WHEAT", 0) or 0) < need_wheat
                and shed_total < SHED_CAPACITY - 10):
            w_price = market_price("WHEAT", int(m_inv.get("WHEAT", 10000) or 10000) - 1)
            k = min(10, need_wheat - int(shed.get("WHEAT", 0) or 0))
            if afford(w_price * k + 150):
                orders.append(["BUY_PRODUCT", "WHEAT", k])
                spend += w_price * k

        if not midgame:
            _append_sells(orders, shed, market, n_animals, False, pressure)
    return orders


def _hire_cost(n_already_today):
    a, b = 1, 1
    for _ in range(int(n_already_today)):
        a, b = b, a + b
    return a


def decode(task_idx, mode_idx, obs, step=None):
    player = int(_get(obs, "player") or 0)
    farms = _get(obs, "farms") or []
    farm = farms[player] if player < len(farms) else {}
    priv = _get(obs, "private") or {}
    market = _get(obs, "market") or {}
    board_size = 10
    if step is None:
        step = int(_get(obs, "step") or 0)

    if step >= 714:
        mode_idx = MODE_IDX["DUMP"]

    task = FARM_TASKS[int(task_idx)] if 0 <= int(task_idx) < len(FARM_TASKS) else "IDLE"
    mode = MARKET_MODES[int(mode_idx)] if 0 <= int(mode_idx) < len(MARKET_MODES) else "HOLD"

    hands = _get(farm, "hands") or []
    day = int(_get(obs, "day") or 0)
    hour = int(_get(obs, "hour") or 0)
    names = [task] + ["IDLE"] * len(hands)
    assigned = _assign_all(farm, priv, board_size, day, names)
    farmer_op = assigned[0] if assigned else ["PASS"]
    hands_ops = assigned[1:]

    market_orders = _market_orders(mode, farm, priv, market, step, day, board_size, hour=hour)

    return {
        "farmer": farmer_op,
        "hands": hands_ops[:len(hands)],
        "market": market_orders[:10],
    }


def decode_per_unit(tasks, mode_idx, obs, step=None, hand_cap=12):
    """Per-unit decoding: tasks[0] is the farmer's task, tasks[1:] are hands'.

    IDLE units share a claimed barnyard-style scheduler; non-IDLE units take
    their typed target first so the policy can still override.
    """
    player = int(_get(obs, "player") or 0)
    farms = _get(obs, "farms") or []
    farm = farms[player] if player < len(farms) else {}
    priv = _get(obs, "private") or {}
    market = _get(obs, "market") or {}
    board_size = 10
    if step is None:
        step = int(_get(obs, "step") or 0)

    mode = MARKET_MODES[int(mode_idx)] if 0 <= int(mode_idx) < len(MARKET_MODES) else "HOLD"
    if step >= 714:
        mode = "DUMP"

    hands = _get(farm, "hands") or []
    day = int(_get(obs, "day") or 0)
    hour = int(_get(obs, "hour") or 0)

    names = []
    n = 1 + min(len(hands), hand_cap)
    for i in range(n):
        idx = int(tasks[i]) if i < len(tasks) else 0
        names.append(FARM_TASKS[idx] if 0 <= idx < len(FARM_TASKS) else "IDLE")
    assigned = _assign_all(farm, priv, board_size, day, names)
    farmer_op = assigned[0] if assigned else ["PASS"]
    hands_ops = assigned[1:]

    market_orders = _market_orders(mode, farm, priv, market, step, day, board_size, hour=hour)

    return {
        "farmer": farmer_op,
        "hands": hands_ops,
        "market": market_orders[:10],
    }


def labels_from_plan_turn(turn):
    """Map a recorded turn to (task_idx, mode_idx) for BC pretraining."""
    market = _get(turn, "market") or []
    mode = 0
    if market:
        has_buy = any(isinstance(o, list) and o and o[0] in ("BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "HIRE", "BUY_LAND") for o in market)
        has_sell = any(isinstance(o, list) and o and o[0] == "SELL" for o in market)
        total_sell = sum(int(o[2] or 0) for o in market if isinstance(o, list) and len(o) >= 3 and o[0] == "SELL")
        if has_buy:
            mode = MODE_IDX["RESTOCK"]
        elif total_sell >= 15:
            mode = MODE_IDX["DUMP"]
        elif has_sell:
            mode = MODE_IDX["METERED"]
        else:
            mode = MODE_IDX["HOLD"]
    else:
        mode = MODE_IDX["HOLD"]

    farmer = _get(turn, "farmer") or ["PASS"]
    op = farmer[0] if isinstance(farmer, list) and farmer else "PASS"
    if op == "WATER":
        task = TASK_IDX["WATER"]
    elif op == "HARVEST":
        task = TASK_IDX["HARVEST"]
    elif op == "FEED":
        task = TASK_IDX["FEED"]
    elif op == "CARE":
        task = TASK_IDX["CARE"]
    elif op == "COLLECT_FERTILIZER":
        task = TASK_IDX["COLLECT_FERT"]
    elif op == "DIG":
        task = TASK_IDX["DIG"]
    elif op == "BUILD_COOP" or op == "BUILD_PASTURE":
        task = TASK_IDX["BUILD"]
    elif op == "PLANT" and len(farmer) >= 2 and farmer[1] in CROPS:
        task = TASK_IDX.get("PLANT_" + farmer[1], TASK_IDX["IDLE"])
    else:
        task = TASK_IDX["IDLE"]
    return task, mode


def decode_market_only(mode_idx, obs, step=None):
    """Decode only market mode to market orders (farm actions come from plan)."""
    mode = MARKET_MODES[int(mode_idx)] if 0 <= int(mode_idx) < len(MARKET_MODES) else "HOLD"
    player = int(_get(obs, "player") or 0)
    farms = _get(obs, "farms") or []
    farm = farms[player] if player < len(farms) else {}
    priv = _get(obs, "private") or {}
    market = _get(obs, "market") or {}
    if step is None:
        step = int(_get(obs, "step") or 0)
    if step >= 714:
        mode = "DUMP"
    return _market_orders(mode, farm, priv, market, step, _get(obs, "day") or 0,
                          hour=int(_get(obs, "hour") or 0))


def market_mode_from_turn(turn):
    """Map a recorded turn's market orders to a market_mode index."""
    market = _get(turn, "market") or []
    if not market:
        return MODE_IDX["HOLD"]
    has_buy = any(isinstance(o, list) and o and o[0] in ("BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "HIRE", "BUY_LAND") for o in market)
    has_sell = any(isinstance(o, list) and o and o[0] == "SELL" for o in market)
    total_sell = sum(int(o[2] or 0) for o in market if isinstance(o, list) and len(o) >= 3 and o[0] == "SELL")
    if has_buy:
        return MODE_IDX["RESTOCK"]
    if total_sell >= 15:
        return MODE_IDX["DUMP"]
    if has_sell:
        return MODE_IDX["METERED"]
    return MODE_IDX["HOLD"]
