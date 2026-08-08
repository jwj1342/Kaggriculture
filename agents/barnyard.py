"""Kaggriculture baseline v1 -- "Barnyard".

An honest first baseline that plays the shape of the current public meta:

  1. Melon + wheat in the opening for capital (melon = highest profit/tile-day).
  2. Convert that capital into an animal engine (cows, then sheep, then geese).
  3. FEED + CARE every animal every day -- CARE triples steady-state yield.
  4. COLLECT_FERTILIZER daily and sell it immediately (fertilizer has no town
     demand, so its price only ever falls -- holding it is strictly a loss).
  5. Hire farm hands aggressively: the n-th hire of a day costs fib(n), so the
     first ~8 hands cost less than one melon seed. Actions, not land, are the
     binding constraint.
  6. Meter every sale. Premium goods (strawberry/wool/milk/melon) fall off a
     price cliff after ~60-160 units, so we sell small batches and only while
     the price holds.
  7. Liquidate everything over the last two days -- unsold inventory scores $0.

The agent is a priority scheduler: every turn it builds a list of pending farm
tasks, sorts them by urgency, and greedily assigns each to the nearest capable
idle unit. Everything is pure Python and O(tiles x units) per turn, comfortably
inside the 1s actTimeout.

Logistics note that drives much of the design: FEED consumes wheat from the
*acting unit's* inventory, and PICKUP only works next to the shed. Units are
therefore explicitly routed back for feed instead of being left to improvise.
"""

import math

# --------------------------------------------------------------------------
# Engine constants (mirrored from kaggriculture.py so the agent is standalone)
# --------------------------------------------------------------------------

CROPS = {
    "WHEAT":      {"seed": 10, "first_yield_day": 2, "max_yield_day": 4, "interval": 0, "max_yield": 6, "ongoing": False},
    "CARROT":     {"seed": 20, "first_yield_day": 2, "max_yield_day": 3, "interval": 0, "max_yield": 4, "ongoing": False},
    "TOMATO":     {"seed": 50, "first_yield_day": 8, "max_yield_day": 8, "interval": 1, "max_yield": 4, "ongoing": True},
    "STRAWBERRY": {"seed": 100, "first_yield_day": 10, "max_yield_day": 10, "interval": 2, "max_yield": 4, "ongoing": True},
    "MELON":      {"seed": 80, "first_yield_day": 10, "max_yield_day": 12, "interval": 0, "max_yield": 6, "ongoing": False},
}

ANIMALS = {
    "GOOSE": {"cost": 300, "structure": "COOP",    "first_yield_day": 4, "interval": 1, "max_held": 4, "product": "EGG"},
    "COW":   {"cost": 400, "structure": "PASTURE", "first_yield_day": 8, "interval": 2, "max_held": 6, "product": "MILK"},
    "SHEEP": {"cost": 500, "structure": "PASTURE", "first_yield_day": 6, "interval": 3, "max_held": 6, "product": "WOOL"},
}

PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]

MARKET_PARAMS = {
    "WHEAT":      {"base":  25, "I0": 10000, "T": 400, "below_func": "sqrt",   "below_target": 0.80, "above_func": "log",    "above_target": 0.20},
    "CARROT":     {"base":  35, "I0": 10000, "T": 450, "below_func": "log",    "below_target": 0.20, "above_func": "sqrt",   "above_target": 0.70},
    "TOMATO":     {"base":  60, "I0": 10000, "T": 200, "below_func": "linear", "below_target": 0.40, "above_func": "sqrt",   "above_target": 0.60},
    "STRAWBERRY": {"base": 120, "I0": 10000, "T": 100, "below_func": "sqrt",   "below_target": 0.70, "above_func": "linear", "above_target": 1.60},
    "MELON":      {"base": 250, "I0": 10000, "T": 300, "below_func": "log",    "below_target": 0.20, "above_func": "sq",     "above_target": 3.60},
    "EGG":        {"base":  50, "I0": 10000, "T": 332, "below_func": "linear", "below_target": 0.40, "above_func": "log",    "above_target": 0.20},
    "MILK":       {"base": 160, "I0": 10000, "T": 122, "below_func": "sqrt",   "below_target": 0.60, "above_func": "linear", "above_target": 1.60},
    "WOOL":       {"base": 200, "I0": 10000, "T": 105, "below_func": "log",    "below_target": 0.20, "above_func": "sq",     "above_target": 3.20},
    "FERTILIZER": {"base": 100, "I0": 10000, "T": 200, "below_func": "linear", "below_target": 0.40, "above_func": "linear", "above_target": 0.40},
}

LAND_PRICES = [1000, 2000, 4000]
SHED_CAPACITY = 100
MAX_MARKET_ORDERS = 10

# Highest yield reachable on watering alone (no fertilizer), per one-shot crop.
WATER_MAX = {}
for _c, _d in CROPS.items():
    if not _d["ongoing"]:
        _window = _d["max_yield_day"] - (_d["max_yield_day"] + 1) // 2 + 1
        WATER_MAX[_c] = min(_d["max_yield"], 1 + _window)


def _shape(func, x):
    x = max(0.0, x)
    if func == "linear":
        return x
    if func == "sq":
        return x * x
    if func == "sqrt":
        return math.sqrt(x)
    if func == "log":
        return math.log(1.0 + x)
    if func == "log10":
        return math.log10(1.0 + x)
    return x


def market_price(item, inventory):
    """Exact copy of the engine's price curve, so we can price our own impact."""
    p = MARKET_PARAMS[item]
    base, i0, t = p["base"], p["I0"], p["T"]
    if inventory < i0:
        amp = p["below_target"] * base / _shape(p["below_func"], t)
        price = base + amp * _shape(p["below_func"], i0 - inventory)
    else:
        amp = p["above_target"] * base / _shape(p["above_func"], t)
        price = base - amp * _shape(p["above_func"], inventory - i0)
    return max(1, int(round(price)))


def _fib(n):
    a, b = 1, 1
    for _ in range(n):
        a, b = b, a + b
    return a


# --------------------------------------------------------------------------
# Tunables
# --------------------------------------------------------------------------

# Herd size is calibrated to town demand, not to land: ~3 of the 8 shop slots
# want milk and ~1 wants wool, which absorbs roughly 12 milk and 6 wool a day.
# Geese are a safety valve -- egg price is logarithmic and never really crashes.
TARGET_COWS = 10
TARGET_SHEEP = 10
TARGET_GEESE = 8
TARGET_ANIMALS = TARGET_COWS + TARGET_SHEEP + TARGET_GEESE

# (crop, target tiles, last day it can still be planted and finish)
CROP_PLAN = [
    ("MELON",      14, 18),
    ("STRAWBERRY", 14, 13),
    ("WHEAT",      20, 24),
]

# Three quadrants, never four. SE costs $4,000 -- more than NE and SW combined --
# and the high-value work (melon, animals) saturates its market at ~37 tiles.
# Measured over 8 seeds: 1 quadrant 49.1k, 2 -> 68.7k, 3 -> 68.9k, 4 -> 68.9k.
MAX_QUADRANTS = 3
CROP_SCALE = 1.0          # multiplier on every CROP_PLAN target (to fill extra land)

HAND_CAP = 14             # hard ceiling on hands per day
HIRE_BUDGET_FRAC = 0.06   # share of cash a day's payroll may consume

LIQUIDATE_DAY = 28        # from this day on, dump everything at any price
SHED_PRESSURE = 74        # above this many items, sell regardless of price
WHEAT_PER_TRIP = 8        # units of feed a hand carries out of the shed
WHEAT_RESERVE_PER_ANIMAL = 2
WHEAT_RESERVE_CAP = 28    # feed hoarded past this just clogs the 100-slot shed

# Fraction of base price below which we would rather hold than sell.
SELL_FLOOR = {
    "MELON": 0.45, "MILK": 0.55, "WOOL": 0.55, "STRAWBERRY": 0.55,
    "TOMATO": 0.55, "CARROT": 0.55, "EGG": 0.50, "WHEAT": 0.60,
    "FERTILIZER": 0.0,     # no town demand -> price only falls -> always sell
}
SELL_BATCH = 8            # max units of one product per turn


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _shed_tiles(n):
    half = n // 2
    return [(half - 1, half - 1), (half, half - 1), (half - 1, half), (half, half)]


def _dist(ax, ay, bx, by):
    return abs(ax - bx) + abs(ay - by)


def _step_toward(fx, fy, tx, ty):
    # Move on the longer axis first. Locked tiles are passable and the board has
    # no obstacles, so any monotone path is optimal.
    if fx != tx and abs(fx - tx) >= abs(fy - ty):
        return "EAST" if tx > fx else "WEST"
    if fy != ty:
        return "SOUTH" if ty > fy else "NORTH"
    if fx != tx:
        return "EAST" if tx > fx else "WEST"
    return None


def _sell_qty(item, inv, held, cap, floor_frac):
    """Largest batch (<= cap, <= held) that keeps the price above the floor."""
    floor = MARKET_PARAMS[item]["base"] * floor_frac
    n = 0
    limit = min(cap, held)
    while n < limit and market_price(item, inv + n) >= floor:
        n += 1
    return n


# --------------------------------------------------------------------------
# Agent
# --------------------------------------------------------------------------

def _plan(obs):
    player = obs.get("player", 0)
    farms = obs.get("farms", []) or []
    if not farms or player >= len(farms):
        return {"farmer": ["PASS"], "hands": [], "market": []}

    farm = farms[player]
    priv = obs.get("private", {}) or {}
    shed = dict(priv.get("shed", {}) or {})
    seeds = dict(priv.get("seeds", {}) or {})
    invs = [dict(d or {}) for d in (priv.get("inventories", []) or [{}])]
    tiles = farm["tiles"]
    n = len(tiles)
    day = obs.get("day", 0)
    hour = obs.get("hour", 0)
    money = farm["money"]
    m_inv = dict((obs.get("market", {}) or {}).get("inventory", {}) or {})
    unlocked = farm.get("unlocked_quadrants", ["NW"]) or ["NW"]

    endgame = day >= LIQUIDATE_DAY
    shed_total = sum(shed.values())

    units = [(0, farm["farmer"][0], farm["farmer"][1])]
    for i, pos in enumerate(farm.get("hands", []) or []):
        units.append((i + 1, pos[0], pos[1]))
    n_units = len(units)
    while len(invs) < n_units:
        invs.append({})

    shed_tiles = _shed_tiles(n)
    shed_set = set(shed_tiles)

    def _shed_dist(x, y):
        return min(_dist(x, y, sx, sy) for sx, sy in shed_tiles)

    # ---- survey the board -------------------------------------------------
    animals_live = []      # (x, y, tile)
    empty_structs = []     # (x, y, kind)
    plants = []            # (x, y, tile)
    weeds = []
    owned = []             # every unlocked tile, for zoning
    free_tiles = []
    counts = {"COW": 0, "SHEEP": 0, "GOOSE": 0}
    crop_counts = {c: 0 for c in CROPS}

    for y in range(n):
        row = tiles[y]
        for x in range(n):
            t = row[x]
            if t == "LOCKED":
                continue
            owned.append((x, y))
            if t is None:
                free_tiles.append((x, y))
            elif isinstance(t, dict):
                kind = t.get("kind")
                if kind == "WEED":
                    weeds.append((x, y))
                elif kind == "PLANT":
                    plants.append((x, y, t))
                    crop_counts[t["crop"]] = crop_counts.get(t["crop"], 0) + 1
                elif "animal" in t:
                    animals_live.append((x, y, t))
                    counts[t["animal"]] = counts.get(t["animal"], 0) + 1
                else:
                    empty_structs.append((x, y, kind))

    n_animals = len(animals_live)
    animals_in_shed = {a: shed.get(a, 0) for a in ANIMALS}
    # Animals being carried are in neither the shed nor on the board. Missing
    # them makes the herd look smaller than it is and we over-buy.
    animals_carried = {a: sum(iv.get(a, 0) for iv in invs[:n_units]) for a in ANIMALS}
    waiting = {a: animals_in_shed[a] + animals_carried[a] for a in ANIMALS}
    n_pending_animals = sum(waiting.values())

    # Zoning: tiles closest to the shed go to animals (3+ visits/day each),
    # everything further out goes to crops (1 visit/day). The animal zone grows
    # with the herd so early-game land is not fenced off for nothing.
    owned.sort(key=lambda p: (_shed_dist(p[0], p[1]), p[1], p[0]))
    zone_size = min(len(owned) - 2, max(4, n_animals + len(empty_structs) + n_pending_animals + 3))
    zone_size = min(zone_size, TARGET_ANIMALS)
    animal_zone = set(owned[:zone_size])

    # ---- task list --------------------------------------------------------
    # (priority, x, y, action, required_item)   lower priority = more urgent
    # x/y == None means "the shed" and is resolved per-unit.
    tasks = []
    unfed = 0

    if not endgame:
        # Priorities are ordered by coins-per-action, with anything that would
        # destroy an asset (a starving animal, a plant one day from becoming a
        # weed) pulled to the front regardless of its marginal value.
        for (x, y, t) in animals_live:
            starving = t.get("consecutive_unfed", 0) >= 1
            if not t.get("fed_today"):
                unfed += 1
                tasks.append((0 if starving else 6, x, y, ["FEED"], "WHEAT"))
            held = t.get("yield_units", 0)
            cap = ANIMALS[t["animal"]]["max_held"]
            if held >= cap:
                # A full animal stops producing: harvesting is ~6 units/action,
                # the best trade on the board.
                tasks.append((1, x, y, ["HARVEST"], None))
            if t.get("fertilizer_available"):
                tasks.append((4, x, y, ["COLLECT_FERTILIZER"], None))
            if not t.get("cared_today"):
                tasks.append((7, x, y, ["CARE"], None))
            if 0 < held < cap and held >= cap - 2:
                tasks.append((9, x, y, ["HARVEST"], None))

        for (x, y, t) in plants:
            crop = t["crop"]
            cd = CROPS[crop]
            age = day - t["planted_day"]
            watered = t.get("watered_today", False)
            yu = t.get("yield_units", 0)
            thirsty = t.get("consecutive_unwatered", 0) >= 1
            if cd["ongoing"]:
                if not watered:
                    tasks.append((2 if thirsty else 8, x, y, ["WATER"], None))
                if age >= cd["first_yield_day"] and yu >= 2:
                    tasks.append((3, x, y, ["HARVEST"], None))
            else:
                target = WATER_MAX[crop]
                ripe = age >= cd["first_yield_day"] and (yu >= target or age >= cd["max_yield_day"])
                if ripe:
                    tasks.append((1, x, y, ["HARVEST"], None))
                elif not watered:
                    window_start = (cd["max_yield_day"] + 1) // 2
                    in_window = window_start <= age <= cd["max_yield_day"]
                    if thirsty:
                        tasks.append((2, x, y, ["WATER"], None))
                    elif in_window and yu < target:
                        # A watered day inside the window is +1 unit: on melon
                        # that is $250 for one action.
                        tasks.append((3 if crop == "MELON" else 8, x, y, ["WATER"], None))

        # Feed logistics: make sure enough wheat is out in the field. Without
        # this the schedule deadlocks -- every unit is busy with CARE/WATER and
        # nobody ever walks back for feed, so the whole herd starves.
        carried_wheat = sum(iv.get("WHEAT", 0) for iv in invs[:n_units])
        wheat_gap = unfed - carried_wheat
        if wheat_gap > 0 and shed.get("WHEAT", 0) > 0:
            trips = min(n_units, -(-wheat_gap // WHEAT_PER_TRIP))
            take = min(WHEAT_PER_TRIP, shed.get("WHEAT", 0))
            for _ in range(trips):
                tasks.append((1, None, None, ["PICKUP", "WHEAT", take], None))

        # Fetch bought animals out of the shed and onto their structures. An
        # animal idling in the shed is dead capital *and* a wasted shed slot.
        for _ in range(sum(animals_in_shed.values())):
            tasks.append((5, None, None, ["PICKUP_ANIMAL"], None))
        for (x, y, kind) in empty_structs:
            for a, ad in ANIMALS.items():
                if ad["structure"] == kind:
                    tasks.append((5, x, y, ["PLACE", a], a))

        # Build ahead of the herd: a pen with no animal is cheap, but an animal
        # with no pen is $400 of dead capital in a 100-slot shed. Build the kind
        # the waiting animals actually need first -- a coop cannot hold a sheep.
        free_pasture = sum(1 for e in empty_structs if e[2] == "PASTURE")
        free_coop = sum(1 for e in empty_structs if e[2] == "COOP")
        need_pasture = max(0, waiting["COW"] + waiting["SHEEP"] - free_pasture)
        need_coop = max(0, waiting["GOOSE"] - free_coop)
        affordable_now = int(max(0.0, money - 300) // 450)
        room = max(0, TARGET_ANIMALS - n_animals - len(empty_structs))
        lookahead = max(0, min(affordable_now, 4) - need_pasture - need_coop)
        plan_pasture = max(0, TARGET_COWS + TARGET_SHEEP - counts["COW"] - counts["SHEEP"]
                           - free_pasture - need_pasture)
        build_queue = (["BUILD_PASTURE"] * need_pasture + ["BUILD_COOP"] * need_coop
                       + ["BUILD_PASTURE" if plan_pasture > 0 else "BUILD_COOP"] * lookahead)
        build_queue = build_queue[:room]

        plant_budget = {c: seeds.get(c, 0) for c in CROPS}
        want_crop = []
        for (crop, target, last_day) in CROP_PLAN:
            if day <= last_day:
                scaled = int(round(target * CROP_SCALE))
                want_crop.append([crop, max(0, scaled - crop_counts.get(crop, 0))])

        for (x, y) in sorted(free_tiles, key=lambda p: (_shed_dist(p[0], p[1]), p[1], p[0])):
            if (x, y) in animal_zone:
                if build_queue:
                    tasks.append((5, x, y, [build_queue.pop(0)], None))
                continue          # inner tiles stay reserved for the herd
            for entry in want_crop:
                crop, remaining = entry
                if remaining > 0 and plant_budget.get(crop, 0) > 0:
                    tasks.append((6 if crop == "MELON" else 10, x, y, ["PLANT", crop], None))
                    plant_budget[crop] -= 1
                    entry[1] -= 1
                    break

        # A weed squats on a tile worth a melon cycle, so clearing one is worth
        # far more than its priority-11 reputation once land runs short.
        weed_prio = 6 if len(free_tiles) <= len(weeds) + 4 else 11
        for (x, y) in weeds:
            tasks.append((weed_prio, x, y, ["DIG"], None))
    else:
        for (x, y, t) in animals_live:
            if t.get("yield_units", 0) > 0:
                tasks.append((0, x, y, ["HARVEST"], None))
        for (x, y, t) in plants:
            if t.get("yield_units", 0) > 0 and day - t["planted_day"] >= CROPS[t["crop"]]["first_yield_day"]:
                tasks.append((0, x, y, ["HARVEST"], None))

    tasks.sort(key=lambda t: t[0])

    # ---- assign tasks to units -------------------------------------------
    actions = [None] * n_units
    busy = [False] * n_units
    claimed = set()
    shed_wheat_left = shed.get("WHEAT", 0)
    shed_animals_left = dict(animals_in_shed)

    for (prio, tx, ty, act, need) in tasks:
        op = act[0]

        if tx is None:
            # Shed errand: pick the idle unit closest to any shed tile.
            best, best_d, best_t = None, None, None
            for k, (idx, ux, uy) in enumerate(units):
                if busy[k]:
                    continue
                if op == "PICKUP" and invs[idx].get("WHEAT", 0) >= WHEAT_PER_TRIP // 2:
                    continue
                if op == "PICKUP_ANIMAL" and any(invs[idx].get(a, 0) for a in ANIMALS):
                    continue
                t_ = min(shed_tiles, key=lambda p: _dist(ux, uy, p[0], p[1]))
                d = _dist(ux, uy, t_[0], t_[1])
                if best_d is None or d < best_d:
                    best, best_d, best_t = k, d, t_
            if best is None:
                continue
            idx, ux, uy = units[best]
            if (ux, uy) in shed_set:
                if op == "PICKUP":
                    take = min(act[2], shed_wheat_left)
                    if take <= 0:
                        continue
                    shed_wheat_left -= take
                    actions[best] = ["PICKUP", "WHEAT", take]
                else:
                    # Prefer an animal that has a pen ready for it, so we do not
                    # carry a sheep around while only coops are free.
                    open_kinds = {e[2] for e in empty_structs}
                    pick = next((a for a in ("COW", "SHEEP", "GOOSE")
                                 if shed_animals_left.get(a, 0) > 0
                                 and ANIMALS[a]["structure"] in open_kinds), None)
                    if pick is None:
                        pick = next((a for a in ("COW", "SHEEP", "GOOSE")
                                     if shed_animals_left.get(a, 0) > 0), None)
                    if pick is None:
                        continue
                    shed_animals_left[pick] -= 1
                    actions[best] = ["PICKUP", pick, 1]
            else:
                actions[best] = [_step_toward(ux, uy, best_t[0], best_t[1])]
            busy[best] = True
            continue

        if (tx, ty, op) in claimed:
            continue
        best, best_d = None, None
        for k, (idx, ux, uy) in enumerate(units):
            if busy[k]:
                continue
            if need is not None and invs[idx].get(need, 0) <= 0:
                continue
            d = _dist(ux, uy, tx, ty)
            if best_d is None or d < best_d:
                best, best_d = k, d
        if best is None:
            continue
        idx, ux, uy = units[best]
        actions[best] = act if (ux, uy) == (tx, ty) else [_step_toward(ux, uy, tx, ty)]
        busy[best] = True
        claimed.add((tx, ty, op))

    # ---- idle units: run produce back to the shed -------------------------
    for k, (idx, ux, uy) in enumerate(units):
        if busy[k]:
            continue
        inv = invs[idx]
        carrying = sum(inv.values())
        at_shed = (ux, uy) in shed_set
        produce = sum(v for it, v in inv.items() if it in PRODUCTS and it != "WHEAT")

        if at_shed:
            if produce > 0 and shed_total < SHED_CAPACITY:
                actions[k] = ["DROP"]
            elif not endgame and n_animals > 0 and shed_wheat_left > 0 and inv.get("WHEAT", 0) < 2:
                take = min(WHEAT_PER_TRIP, shed_wheat_left)
                shed_wheat_left -= take
                actions[k] = ["PICKUP", "WHEAT", take]
            else:
                actions[k] = ["PASS"]
        elif produce >= 6 or endgame or carrying >= 12:
            t_ = min(shed_tiles, key=lambda p: _dist(ux, uy, p[0], p[1]))
            mv = _step_toward(ux, uy, t_[0], t_[1])
            actions[k] = [mv] if mv else ["PASS"]
        else:
            actions[k] = ["PASS"]
        busy[k] = True

    # ---- market -----------------------------------------------------------
    orders = []
    spend = 0.0

    def _afford(cost):
        return money - spend >= cost

    if not endgame:
        # Hire early: the n-th hire of the day costs fib(n), so the first eight
        # hands together cost less than one melon seed.
        if hour <= 3:
            # fib(n) explodes -- the 17th hand alone costs more than the first
            # fifteen combined -- so cap the whole day's payroll as a fraction
            # of cash instead of chasing a fixed head count.
            hires = farm.get("hires_today", 0)
            payroll = sum(_fib(i) for i in range(hires))
            budget = max(4.0, money * HIRE_BUDGET_FRAC)
            while len(orders) < 7 and hires < HAND_CAP:
                cost = _fib(hires)
                if payroll + cost > budget or not _afford(cost + 40):
                    break
                orders.append(["HIRE"])
                spend += cost
                payroll += cost
                hires += 1

        # Land. Tiles are the binding constraint once there are hands to work
        # them, and every quadrant is cheap next to what a melon tile earns.
        n_extra = len(unlocked) - 1
        crop_room = sum(1 for p in free_tiles if p not in animal_zone)
        if n_extra < min(len(LAND_PRICES), MAX_QUADRANTS - 1) and len(orders) < MAX_MARKET_ORDERS:
            price = LAND_PRICES[n_extra]
            reserve = [600, 1500, 3000][n_extra]
            if crop_room <= 8 and _afford(price + reserve):
                orders.append(["BUY_LAND"])
                spend += price

        # Animals. Never buy faster than we can house them -- an animal in the
        # shed earns nothing and occupies one of only 100 shed slots.
        housing_free = len(empty_structs) + max(0, TARGET_ANIMALS - n_animals - len(empty_structs))
        if (len(orders) < MAX_MARKET_ORDERS and day <= 23
                and n_pending_animals < 2 and housing_free > n_pending_animals
                and shed_total < SHED_CAPACITY - 8):
            owned_of = {a: counts[a] + animals_in_shed.get(a, 0) for a in ANIMALS}
            want = None
            if owned_of["COW"] < TARGET_COWS:
                want = "COW"
            elif owned_of["SHEEP"] < TARGET_SHEEP:
                want = "SHEEP"
            elif owned_of["GOOSE"] < TARGET_GEESE and day <= 20:
                want = "GOOSE"
            if want is not None:
                cost = ANIMALS[want]["cost"]
                keep = 100 if day < 12 else 400
                if _afford(cost + keep):
                    orders.append(["BUY_ANIMAL", want, 1])
                    spend += cost

        # Seeds -- only ever buy what there is a free crop tile to plant.
        for (crop, target, last_day) in CROP_PLAN:
            if len(orders) >= MAX_MARKET_ORDERS or crop_room <= 0 or day > last_day:
                continue
            have = crop_counts.get(crop, 0) + seeds.get(crop, 0)
            target = int(round(target * CROP_SCALE))
            if have >= target:
                continue
            cost1 = CROPS[crop]["seed"]
            k = min(4, target - have, crop_room)
            if k > 0 and _afford(cost1 * k + 100):
                orders.append(["BUY_SEED", crop, k])
                spend += cost1 * k
                crop_room -= k

        # Buy feed. Growing wheat costs ~6 actions for 4 units; buying it costs
        # ~$30-50 and zero actions, and actions are what we are short of.
        need_wheat = min(WHEAT_RESERVE_CAP, n_animals * WHEAT_RESERVE_PER_ANIMAL)
        if (len(orders) < MAX_MARKET_ORDERS and n_animals > 0
                and shed.get("WHEAT", 0) < need_wheat and shed_total < SHED_CAPACITY - 10):
            w_price = market_price("WHEAT", m_inv.get("WHEAT", 10000) - 1)
            k = min(10, need_wheat - shed.get("WHEAT", 0))
            if _afford(w_price * k + 150):
                orders.append(["BUY_PRODUCT", "WHEAT", k])
                spend += w_price * k

    # Sells: highest cash value first, metered against our own price impact.
    sellable = []
    for item in PRODUCTS:
        held = shed.get(item, 0)
        if held <= 0:
            continue
        if item == "WHEAT" and not endgame:
            held = max(0, held - min(WHEAT_RESERVE_CAP, n_animals * WHEAT_RESERVE_PER_ANIMAL))
            if held <= 0:
                continue
        inv0 = m_inv.get(item, 10000)
        price = market_price(item, inv0)
        sellable.append((price * min(held, SELL_BATCH), item, held, inv0))
    sellable.sort(reverse=True)

    pressure = shed_total >= SHED_PRESSURE
    for (_, item, held, inv0) in sellable:
        if len(orders) >= MAX_MARKET_ORDERS:
            break
        if endgame:
            qty = min(held, 40)
        elif pressure:
            qty = min(held, SELL_BATCH)
        else:
            qty = _sell_qty(item, inv0, held, SELL_BATCH, SELL_FLOOR.get(item, 0.55))
        if qty > 0:
            orders.append(["SELL", item, qty])

    return {
        "farmer": actions[0] if actions and actions[0] else ["PASS"],
        "hands": [a if a else ["PASS"] for a in actions[1:]],
        "market": orders[:MAX_MARKET_ORDERS],
    }


def agent(obs):
    try:
        return _plan(obs)
    except Exception:
        # Never crash out of an episode -- a passed turn beats a dead agent.
        return {"farmer": ["PASS"], "hands": [], "market": []}
