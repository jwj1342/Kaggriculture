"""Composable strategy engine for Kaggriculture.

This is a template, not a submission. `tools/registry.py` stamps out named
strategies by replacing the CONFIG block below, so every strategy in the library
shares one execution path and differences between them are differences of
configuration only. That is what makes the tournament results comparable.

A strategy is an assignment of one option to each **atom** (orthogonal axis):

    land       how many 5x5 quadrants to own
    labour     how many hands per day, and what share of cash payroll may take
    produce    the crop plan and herd targets
    market     how sale sizing responds to price
    intel      whether and how the opponent's board changes our behaviour
    muck       what happens to the free daily fertilizer: collected, sold, or
               spent on the crops

Module-level state persists for a whole episode (the framework execs the file
once and calls the function 720 times), which the `adaptive` market atom relies
on to track the opponent's realised sell rate.
"""

import math

# === STRATEGY CONFIG (generated -- do not edit by hand) ===
CONFIG = {   'name': 'smallhold-solo-bigberry-flood-frontrun-compost',
    'atoms': {   'land': 'smallhold',
                 'labour': 'solo',
                 'produce': 'bigberry',
                 'market': 'flood',
                 'intel': 'frontrun',
                 'muck': 'compost'},
    'land': 2,
    'hands': 0,
    'hire_frac': 0.0,
    'crops': [['STRAWBERRY', 28, 19], ['MELON', 8, 18]],
    'animals': {'COW': 6, 'SHEEP': 4},
    'market': 'flood',
    'intel': 'frontrun',
    'muck': True,
    'harvest_product': True,
    'fertilise': True}
# === END CONFIG ===

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
SHOPS = {
    "BAKERY": ["EGG", "WHEAT"], "PIZZA_SHOP": ["MILK", "TOMATO", "WHEAT"],
    "BRUNCH_SPOT": ["EGG", "WHEAT", "STRAWBERRY"], "YARN_STORE": ["WOOL"],
    "ICE_CREAM_SHOP": ["STRAWBERRY", "MILK", "WHEAT"], "PET_CAFE": ["CARROT"],
    "SMOOTHIE_SHOP": ["STRAWBERRY", "MILK"],
    "FARMERS_MARKET": ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY"],
}
LAND_PRICES = [1000, 2000, 4000]
SHED_CAPACITY = 100
MAX_ORDERS = 10
LIQUIDATE_DAY = 28
PRODUCT_OF = {a: d["product"] for a, d in ANIMALS.items()}
LAST_PLANT_DAY = {"WHEAT": 24, "CARROT": 25, "TOMATO": 19, "STRAWBERRY": 13, "MELON": 18}

WATER_MAX = {}
for _c, _d in CROPS.items():
    if not _d["ongoing"]:
        _w = _d["max_yield_day"] - (_d["max_yield_day"] + 1) // 2 + 1
        WATER_MAX[_c] = min(_d["max_yield"], 1 + _w)

# Per-seat episode memory. Reset when we see step 0 again.
_MEM = [None, None]


def _shape(f, x):
    x = max(0.0, x)
    if f == "linear":
        return x
    if f == "sq":
        return x * x
    if f == "sqrt":
        return math.sqrt(x)
    if f == "log":
        return math.log(1.0 + x)
    if f == "log10":
        return math.log10(1.0 + x)
    return x


def market_price(item, inv):
    p = MARKET_PARAMS[item]
    base, i0, t = p["base"], p["I0"], p["T"]
    if inv < i0:
        amp = p["below_target"] * base / _shape(p["below_func"], t)
        return max(1, int(round(base + amp * _shape(p["below_func"], i0 - inv))))
    amp = p["above_target"] * base / _shape(p["above_func"], t)
    return max(1, int(round(base - amp * _shape(p["above_func"], inv - i0))))


def _fib(n):
    a, b = 1, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def _shed_tiles(n):
    h = n // 2
    return [(h - 1, h - 1), (h, h - 1), (h - 1, h), (h, h)]


def _dist(ax, ay, bx, by):
    return abs(ax - bx) + abs(ay - by)


def _step_toward(fx, fy, tx, ty):
    if fx != tx and abs(fx - tx) >= abs(fy - ty):
        return "EAST" if tx > fx else "WEST"
    if fy != ty:
        return "SOUTH" if ty > fy else "NORTH"
    if fx != tx:
        return "EAST" if tx > fx else "WEST"
    return None


def _town_drain(shops, step, turns_per_day=24):
    """Units the town removes at this step. Deterministic, so it can be
    subtracted when inferring what the opponent sold."""
    drain = {p: 0 for p in PRODUCTS}
    if step % 4 == 0:
        for s in shops:
            prods = SHOPS.get(s, [])
            mult = 2 if len(prods) == 1 else 1
            for p in prods:
                drain[p] += mult
    if step % turns_per_day == 0:
        for p in PRODUCTS:
            if p != "FERTILIZER":
                drain[p] += 1
    return drain


def _opponent_board(opp_farm, day):
    """Their public board -> what is harvestable now, soon, and at all."""
    ready = {p: 0 for p in PRODUCTS}
    imminent = {p: 0 for p in PRODUCTS}
    capacity = {p: 0 for p in PRODUCTS}
    for row in opp_farm.get("tiles", []) or []:
        for t in row:
            if not isinstance(t, dict):
                continue
            if t.get("kind") == "PLANT":
                crop = t.get("crop")
                if crop not in CROPS:
                    continue
                cd = CROPS[crop]
                age = day - t.get("planted_day", day)
                yu = int(t.get("yield_units", 0) or 0)
                capacity[crop] += cd["max_yield"]
                if age >= cd["first_yield_day"]:
                    ready[crop] += yu
                elif age >= cd["first_yield_day"] - 2:
                    imminent[crop] += max(yu, 1)
            elif "animal" in t:
                a = t.get("animal")
                if a not in ANIMALS:
                    continue
                ad = ANIMALS[a]
                prod = ad["product"]
                capacity[prod] += ad["max_held"]
                ready[prod] += int(t.get("yield_units", 0) or 0)
                if day - t.get("placed_day", day) >= ad["first_yield_day"] - 2:
                    imminent[prod] += 1
                if t.get("fertilizer_available"):
                    ready["FERTILIZER"] += 1
                capacity["FERTILIZER"] += 1
    return ready, imminent, capacity


def _plan(obs):
    cfg = CONFIG
    player = obs.get("player", 0)
    farms = obs.get("farms", []) or []
    if not farms or player >= len(farms):
        return {"farmer": ["PASS"], "hands": [], "market": []}

    farm = farms[player]
    opp = farms[1 - player] if len(farms) >= 2 else {}
    priv = obs.get("private", {}) or {}
    shed = dict(priv.get("shed", {}) or {})
    seeds = dict(priv.get("seeds", {}) or {})
    invs = [dict(d or {}) for d in (priv.get("inventories", []) or [{}])]
    tiles = farm["tiles"]
    n = len(tiles)
    day, hour = obs.get("day", 0), obs.get("hour", 0)
    step = obs.get("step", day * 24 + hour)
    money = farm["money"]
    market = obs.get("market", {}) or {}
    m_inv = dict(market.get("inventory", {}) or {})
    shops = list((obs.get("town", {}) or {}).get("unlocked_shops", []) or [])
    unlocked = farm.get("unlocked_quadrants", ["NW"]) or ["NW"]
    endgame = day >= LIQUIDATE_DAY
    shed_total = sum(shed.values())

    # ---- episode memory: infer what the opponent has been selling -----------
    seat = 1 if player == 1 else 0
    mem = _MEM[seat]
    if mem is None or step <= mem.get("last_step", -1):
        mem = {"last_step": step, "prev_inv": None, "pending": {}, "opp_sold": {p: 0 for p in PRODUCTS}}
        _MEM[seat] = mem
    if mem["prev_inv"] is not None:
        drain = _town_drain(shops, step - 1)
        for p in PRODUCTS:
            delta = m_inv.get(p, 0) - mem["prev_inv"].get(p, 0)
            # delta = (our sells) + (their sells) - town drain - buys
            theirs = delta - mem["pending"].get(p, 0) + drain[p]
            if theirs > 0:
                mem["opp_sold"][p] += theirs
    mem["prev_inv"] = dict(m_inv)
    mem["last_step"] = step
    opp_sold = mem["opp_sold"]
    opp_sell_rate = sum(opp_sold.values()) / max(1, step)

    opp_ready, opp_imminent, opp_capacity = _opponent_board(opp, day)
    behind = float(opp.get("money", 0) or 0) > money * 1.15

    # ---- resolve atoms into this turn's behaviour --------------------------
    market_mode = cfg["market"]
    intel = cfg["intel"]
    if intel == "spite" and behind and day >= 12:
        market_mode = "flood"
    if market_mode == "adaptive":
        # Meter against a meterer, flood against a flooder. 0.9 units/turn is
        # roughly what a metered agent produces; above that they are dumping.
        market_mode = "flood" if opp_sell_rate > 0.9 else "metered"

    crop_plan = [list(c) for c in cfg["crops"]]
    animal_plan = dict(cfg["animals"])
    if intel == "evade":
        crop_plan.sort(key=lambda c: opp_capacity.get(c[0], 0))
        animal_plan = {a: v for a, v in sorted(
            animal_plan.items(), key=lambda kv: opp_capacity.get(PRODUCT_OF[kv[0]], 0))}

    target_animals = sum(animal_plan.values())

    units = [(0, farm["farmer"][0], farm["farmer"][1])]
    for i, pos in enumerate(farm.get("hands", []) or []):
        units.append((i + 1, pos[0], pos[1]))
    n_units = len(units)
    while len(invs) < n_units:
        invs.append({})
    st = _shed_tiles(n)
    st_set = set(st)

    animals_live, empty_structs, plants, weeds, free, owned = [], [], [], [], [], []
    counts = {a: 0 for a in ANIMALS}
    crop_counts = {c: 0 for c in CROPS}
    for y in range(n):
        for x in range(n):
            t = tiles[y][x]
            if t == "LOCKED":
                continue
            owned.append((x, y))
            if t is None:
                free.append((x, y))
            elif isinstance(t, dict):
                k = t.get("kind")
                if k == "WEED":
                    weeds.append((x, y))
                elif k == "PLANT":
                    plants.append((x, y, t))
                    crop_counts[t["crop"]] = crop_counts.get(t["crop"], 0) + 1
                elif "animal" in t:
                    animals_live.append((x, y, t))
                    counts[t["animal"]] = counts.get(t["animal"], 0) + 1
                else:
                    empty_structs.append((x, y, k))

    n_animals = len(animals_live)
    carried = {a: sum(iv.get(a, 0) for iv in invs[:n_units]) for a in ANIMALS}
    in_shed = {a: shed.get(a, 0) for a in ANIMALS}
    waiting = {a: carried[a] + in_shed[a] for a in ANIMALS}
    n_waiting = sum(waiting.values())

    # The feed reserve, computed once. Three call sites need it: the buyer, to
    # decide whether to top up; the gate on livestock, to decide whether the
    # next mouth is already covered; and the seller, to decide what is surplus.
    # Computing it separately in each place is what makes wheat bought for the
    # herd get sold straight back -- 944 units churned through the market in a
    # single measured episode, with the herd stuck at six of a planned fourteen.
    _committed = n_animals + n_waiting
    if day <= 23 and _committed < target_animals:
        _committed = min(target_animals, _committed + 2)
    feed_reserve = min(28, _committed * 2)
    carried_wheat_all = sum(iv.get("WHEAT", 0) for iv in invs[:n_units])

    def feed_solvent():
        """Is the next mouth's feed already in hand -- shed or carried?

        Counting only the shed deadlocks the herd: hands hold eight wheat at a
        time, so a farm actively feeding can have most of its stock in transit
        and look insolvent while it is not.
        """
        need = min(28, (n_animals + 1) * 3)
        return shed.get("WHEAT", 0) + carried_wheat_all >= need

    def shed_dist(x, y):
        return min(_dist(x, y, sx, sy) for sx, sy in st)

    owned.sort(key=lambda p: (shed_dist(p[0], p[1]), p[1], p[0]))
    zone = min(len(owned) - 2, max(4, n_animals + len(empty_structs) + n_waiting + 3))
    zone = max(0, min(zone, target_animals))
    animal_zone = set(owned[:zone])

    # ---- tasks -------------------------------------------------------------
    tasks = []
    unfed = 0
    if not endgame:
        for (x, y, t) in animals_live:
            if not t.get("fed_today"):
                unfed += 1
                tasks.append((0 if t.get("consecutive_unfed", 0) >= 1 else 6, x, y, ["FEED"], "WHEAT"))
            held = t.get("yield_units", 0)
            cap = ANIMALS[t["animal"]]["max_held"]
            if cfg["harvest_product"] and held >= cap:
                tasks.append((1, x, y, ["HARVEST"], None))
            if cfg["muck"] and t.get("fertilizer_available"):
                tasks.append((4, x, y, ["COLLECT_FERTILIZER"], None))
            if not t.get("cared_today"):
                tasks.append((7, x, y, ["CARE"], None))
            if cfg["harvest_product"] and 0 < held >= cap - 2:
                tasks.append((9, x, y, ["HARVEST"], None))

        for (x, y, t) in plants:
            cd = CROPS[t["crop"]]
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
                tgt = WATER_MAX[t["crop"]]
                if age >= cd["first_yield_day"] and (yu >= tgt or age >= cd["max_yield_day"]):
                    tasks.append((1, x, y, ["HARVEST"], None))
                elif not watered:
                    w0 = (cd["max_yield_day"] + 1) // 2
                    if thirsty:
                        tasks.append((2, x, y, ["WATER"], None))
                    elif w0 <= age <= cd["max_yield_day"] and yu < tgt:
                        tasks.append((3 if t["crop"] == "MELON" else 8, x, y, ["WATER"], None))

        # Fertilizer spent on the crops rather than sold.
        #
        # For an `ongoing` crop this is the single largest multiplier in the
        # game and nothing in the library used it. Production ticks every
        # `interval` days from `first_yield_day`, and the end-of-day rule adds
        # `2 if (watered and fertilized) else 1` units -- so a tile that is
        # fertilized on its production days yields 8 units over its life
        # instead of 4. One FERTILIZE sets `fertilized_until_day = day + 2`,
        # covering three days, which is more than one strawberry tick.
        #
        # For a non-ongoing crop the cap is the cap, so fertilizer adds no
        # units. It still pays: each WATER inside the ripening window counts
        # double, so a fertilized melon needs three waterings instead of five.
        # Only ever fertilize a tile that is **already watered today**, and only
        # after every watering task has been placed.
        #
        # The end-of-day rule is `fertilized = was_watered and
        # fertilized_until_day >= current_day`: fertilizer on a tile that never
        # gets watered does nothing at all. The first version of this ranked
        # FERTILIZE at priority 3 and watering at 8, so it competed with the
        # very action it depends on -- measured in run #7, `compost` lost to
        # `muck` in 15 pairings out of 15 while yielding only 2.7 strawberry per
        # planting against a fertilized ceiling of 8.
        fert_targets = 0
        if cfg.get("fertilise"):
            for (x, y, t) in plants:
                cd = CROPS[t["crop"]]
                age = day - t["planted_day"]
                if not t.get("watered_today"):
                    continue
                if t.get("fertilized_until_day", -1) >= day + 1:
                    continue
                if cd["ongoing"]:
                    if age >= cd["first_yield_day"] - 1:
                        tasks.append((9, x, y, ["FERTILIZE"], "FERTILIZER"))
                        fert_targets += 1
                else:
                    w0 = (cd["max_yield_day"] + 1) // 2
                    if w0 - 1 <= age <= cd["max_yield_day"]:
                        tasks.append((10, x, y, ["FERTILIZE"], "FERTILIZER"))
                        fert_targets += 1
            carried_f = sum(iv.get("FERTILIZER", 0) for iv in invs[:n_units])
            gap_f = fert_targets - carried_f
            if gap_f > 0 and shed.get("FERTILIZER", 0) > 0:
                for _ in range(min(n_units, -(-gap_f // 6))):
                    tasks.append((4, None, None, ["PICKUP_FERT"], None))

        carried_wheat = sum(iv.get("WHEAT", 0) for iv in invs[:n_units])
        gap = unfed - carried_wheat
        if gap > 0 and shed.get("WHEAT", 0) > 0:
            for _ in range(min(n_units, -(-gap // 8))):
                tasks.append((1, None, None, ["PICKUP_WHEAT"], None))

        for _ in range(sum(in_shed.values())):
            tasks.append((5, None, None, ["PICKUP_ANIMAL"], None))
        for (x, y, kind) in empty_structs:
            for a in animal_plan:
                if ANIMALS[a]["structure"] == kind:
                    tasks.append((5, x, y, ["PLACE", a], a))

        free_p = sum(1 for e in empty_structs if e[2] == "PASTURE")
        free_c = sum(1 for e in empty_structs if e[2] == "COOP")
        want_p = max(0, waiting["COW"] + waiting["SHEEP"] - free_p)
        want_c = max(0, waiting["GOOSE"] - free_c)
        affordable = int(max(0.0, money - 300) // 450)
        room = max(0, target_animals - n_animals - len(empty_structs))
        extra = max(0, min(affordable, 4) - want_p - want_c)
        plan_p = max(0, animal_plan.get("COW", 0) + animal_plan.get("SHEEP", 0)
                     - counts["COW"] - counts["SHEEP"] - free_p - want_p)
        build_q = (["BUILD_PASTURE"] * want_p + ["BUILD_COOP"] * want_c
                   + ["BUILD_PASTURE" if plan_p > 0 else "BUILD_COOP"] * extra)[:room]

        budget = {c: seeds.get(c, 0) for c in CROPS}
        want = [[c, max(0, tgt - crop_counts.get(c, 0))] for (c, tgt, ld) in crop_plan if day <= ld]
        for (x, y) in sorted(free, key=lambda p: (shed_dist(p[0], p[1]), p[1], p[0])):
            if (x, y) in animal_zone:
                if build_q:
                    tasks.append((5, x, y, [build_q.pop(0)], None))
                continue
            for entry in want:
                c, rem = entry
                if rem > 0 and budget.get(c, 0) > 0:
                    tasks.append((6 if c == "MELON" else 10, x, y, ["PLANT", c], None))
                    budget[c] -= 1
                    entry[1] -= 1
                    break

        wp = 6 if len(free) <= len(weeds) + 4 else 11
        for (x, y) in weeds:
            tasks.append((wp, x, y, ["DIG"], None))
    else:
        for (x, y, t) in animals_live:
            if t.get("yield_units", 0) > 0:
                tasks.append((0, x, y, ["HARVEST"], None))
        for (x, y, t) in plants:
            if t.get("yield_units", 0) > 0 and day - t["planted_day"] >= CROPS[t["crop"]]["first_yield_day"]:
                tasks.append((0, x, y, ["HARVEST"], None))

    tasks.sort(key=lambda t: t[0])

    # ---- assignment --------------------------------------------------------
    actions = [None] * n_units
    busy = [False] * n_units
    claimed = set()
    wheat_left = shed.get("WHEAT", 0)
    fert_left = shed.get("FERTILIZER", 0)
    shed_animals = dict(in_shed)

    for (prio, tx, ty, act, need) in tasks:
        op = act[0]
        if tx is None:
            best, bd, bt = None, None, None
            for k, (idx, ux, uy) in enumerate(units):
                if busy[k]:
                    continue
                if op == "PICKUP_WHEAT" and invs[idx].get("WHEAT", 0) >= 4:
                    continue
                if op == "PICKUP_FERT" and invs[idx].get("FERTILIZER", 0) >= 3:
                    continue
                if op == "PICKUP_ANIMAL" and any(invs[idx].get(a, 0) for a in ANIMALS):
                    continue
                tgt = min(st, key=lambda p: _dist(ux, uy, p[0], p[1]))
                d = _dist(ux, uy, tgt[0], tgt[1])
                if bd is None or d < bd:
                    best, bd, bt = k, d, tgt
            if best is None:
                continue
            idx, ux, uy = units[best]
            if (ux, uy) in st_set:
                if op == "PICKUP_WHEAT":
                    take = min(8, wheat_left)
                    if take <= 0:
                        continue
                    wheat_left -= take
                    actions[best] = ["PICKUP", "WHEAT", take]
                elif op == "PICKUP_FERT":
                    take = min(6, fert_left)
                    if take <= 0:
                        continue
                    fert_left -= take
                    actions[best] = ["PICKUP", "FERTILIZER", take]
                else:
                    open_kinds = {e[2] for e in empty_structs}
                    pick = next((a for a in ("COW", "SHEEP", "GOOSE")
                                 if shed_animals.get(a, 0) > 0
                                 and ANIMALS[a]["structure"] in open_kinds), None)
                    if pick is None:
                        pick = next((a for a in ("COW", "SHEEP", "GOOSE")
                                     if shed_animals.get(a, 0) > 0), None)
                    if pick is None:
                        continue
                    shed_animals[pick] -= 1
                    actions[best] = ["PICKUP", pick, 1]
            else:
                actions[best] = [_step_toward(ux, uy, bt[0], bt[1])]
            busy[best] = True
            continue

        if (tx, ty, op) in claimed:
            continue
        best, bd = None, None
        for k, (idx, ux, uy) in enumerate(units):
            if busy[k] or (need and invs[idx].get(need, 0) <= 0):
                continue
            d = _dist(ux, uy, tx, ty)
            if bd is None or d < bd:
                best, bd = k, d
        if best is None:
            continue
        idx, ux, uy = units[best]
        actions[best] = act if (ux, uy) == (tx, ty) else [_step_toward(ux, uy, tx, ty)]
        busy[best] = True
        claimed.add((tx, ty, op))

    for k, (idx, ux, uy) in enumerate(units):
        if busy[k]:
            continue
        inv = invs[idx]
        # A small carried stock of fertilizer is field stock, not produce -- it
        # must not trigger a trip to the shed, or it gets dropped and sold.
        keep_f = (inv.get("FERTILIZER", 0)
                  if cfg.get("fertilise") and not endgame
                  and inv.get("FERTILIZER", 0) <= 3 else 0)
        produce = sum(v for it, v in inv.items()
                      if it in PRODUCTS and it != "WHEAT") - keep_f
        if (ux, uy) in st_set:
            if produce > 0 and shed_total < SHED_CAPACITY:
                actions[k] = ["DROP"]
            elif not endgame and n_animals and wheat_left > 0 and inv.get("WHEAT", 0) < 2:
                take = min(8, wheat_left)
                wheat_left -= take
                actions[k] = ["PICKUP", "WHEAT", take]
            else:
                actions[k] = ["PASS"]
        elif produce >= 6 or endgame or sum(inv.values()) >= 12:
            tgt = min(st, key=lambda p: _dist(ux, uy, p[0], p[1]))
            mv = _step_toward(ux, uy, tgt[0], tgt[1])
            actions[k] = [mv] if mv else ["PASS"]
        else:
            actions[k] = ["PASS"]
        busy[k] = True

    # ---- market ------------------------------------------------------------
    orders = []
    spend = 0.0
    submitted = {p: 0 for p in PRODUCTS}

    def afford(c):
        return money - spend >= c

    if not endgame:
        if cfg["hands"] > 0 and hour <= 3:
            hires = farm.get("hires_today", 0)
            payroll = sum(_fib(i) for i in range(hires))
            budget_h = max(4.0, money * cfg["hire_frac"])
            while len(orders) < 7 and hires < cfg["hands"]:
                c = _fib(hires)
                if payroll + c > budget_h or not afford(c + 40):
                    break
                orders.append(["HIRE"])
                spend += c
                payroll += c
                hires += 1

        n_extra = len(unlocked) - 1
        crop_room = sum(1 for p in free if p not in animal_zone)
        if n_extra < min(len(LAND_PRICES), cfg["land"] - 1) and len(orders) < MAX_ORDERS:
            price = LAND_PRICES[n_extra]
            if crop_room <= 8 and afford(price + [600, 1500, 3000][n_extra]):
                orders.append(["BUY_LAND"])
                spend += price

        # --- feed first, then the mouth -------------------------------------
        # An animal eats one wheat a day, returns nothing for four to eight
        # days, and escapes after two unfed ones. Buying it against an empty
        # shed loses it: being able to afford the wheat is not the same as
        # having it. This is the defect the enhanced baseline was built to fix
        # -- three to five animals lost per episode, measured -- and it was
        # still in the library engine, so every strategy here has been quietly
        # starving its herd whenever the opening was tight.
        need_w = feed_reserve
        if n_animals == 0 and day <= 23 and target_animals:
            need_w = max(need_w, 6)
        if (len(orders) < MAX_ORDERS and need_w
                and shed.get("WHEAT", 0) < need_w
                and shed_total < SHED_CAPACITY - 10):
            wpx = market_price("WHEAT", m_inv.get("WHEAT", 10000) - 1)
            k = min(10, need_w - shed.get("WHEAT", 0))
            if afford(wpx * k + 150):
                orders.append(["BUY_PRODUCT", "WHEAT", k])
                spend += wpx * k

        housing = len(empty_structs) + max(0, target_animals - n_animals - len(empty_structs))
        if (len(orders) < MAX_ORDERS and day <= 23 and n_waiting < 2
                and housing > n_waiting and shed_total < SHED_CAPACITY - 8):
            owned_of = {a: counts[a] + waiting[a] for a in ANIMALS}
            want_a = next((a for a in ("COW", "SHEEP", "GOOSE")
                           if owned_of[a] < animal_plan.get(a, 0)), None)
            if want_a:
                c = ANIMALS[want_a]["cost"]
                if feed_solvent() and afford(c + (100 if day < 12 else 400)):
                    orders.append(["BUY_ANIMAL", want_a, 1])
                    spend += c

        for (c, tgt, ld) in crop_plan:
            if len(orders) >= MAX_ORDERS or crop_room <= 0 or day > ld:
                continue
            have = crop_counts.get(c, 0) + seeds.get(c, 0)
            if have >= tgt:
                continue
            cost1 = CROPS[c]["seed"]
            k = min(4, tgt - have, crop_room)
            # Seeds must not eat the herd. A flat $100 floor is fine for a $10
            # wheat seed and ruinous for a $100 strawberry seed: the ladder's
            # strongest shape, reconstructed, spent $4,000 on 44 seeds in the
            # first two days and then sat on $72 with three hands and no animals
            # until day 10, while the real opponent held ~$1,800 through the
            # same window and had eight animals by day 10. Reserve the next few
            # animals, and their first feed, before buying anything to plant.
            pending_herd = max(0, target_animals - n_animals - n_waiting)
            floor_cash = 100 + min(4, pending_herd) * 420
            if k > 0 and afford(cost1 * k + floor_cash):
                orders.append(["BUY_SEED", c, k])
                spend += cost1 * k
                crop_room -= k

    # Fertilizer held back for the field. Sized off the ongoing tiles, which are
    # the only ones it multiplies: each needs roughly one application every
    # three days, and the shed is a day behind the field.
    # Nothing consumes fertilizer, so its price only falls and holding a large
    # stock is a pure loss -- run #7 measured `muck` (dump it all) beating
    # `compost` in every one of fifteen pairings, partly because dumping first
    # takes the whole pool and leaves the opponent selling at $8. Keep only what
    # the standing ongoing tiles can actually absorb in the next couple of days.
    fert_reserve = 0
    if cfg.get("fertilise") and not endgame:
        ongoing_tiles = sum(crop_counts.get(c, 0) for c in CROPS if CROPS[c]["ongoing"])
        fert_reserve = min(12, ongoing_tiles)

    sellable = []
    for item in PRODUCTS:
        held = shed.get(item, 0)
        if held <= 0:
            continue
        if item == "WHEAT" and not endgame and feed_reserve:
            held = max(0, held - feed_reserve)
            if held <= 0:
                continue
        if item == "FERTILIZER" and fert_reserve:
            held = max(0, held - fert_reserve)
            if held <= 0:
                continue
        inv0 = m_inv.get(item, 10000)
        threat = opp_ready.get(item, 0) + opp_imminent.get(item, 0)
        sellable.append((market_price(item, inv0) * min(held, 8) + threat * 50,
                         item, held, inv0, threat))
    sellable.sort(reverse=True)

    pressure = shed_total >= 74
    for (_, item, held, inv0, threat) in sellable:
        if len(orders) >= MAX_ORDERS:
            break
        if endgame or market_mode == "flood":
            qty = min(held, 40)
        elif market_mode == "vault":
            qty = min(held, 8) if pressure else 0
        else:
            base = MARKET_PARAMS[item]["base"]
            frac = 0.0 if item == "FERTILIZER" else 0.55
            batch = 8
            if intel in ("frontrun", "spite") and threat >= 4:
                frac *= 0.5
                batch = 20
            floor = base * frac
            qty = 0
            lim = min(batch, held)
            while qty < lim and market_price(item, inv0 + qty) >= floor:
                qty += 1
            if pressure and qty == 0:
                qty = min(held, 8)
        if qty > 0:
            orders.append(["SELL", item, qty])
            submitted[item] += qty

    mem["pending"] = submitted
    return {
        "farmer": actions[0] if actions and actions[0] else ["PASS"],
        "hands": [a if a else ["PASS"] for a in actions[1:]],
        "market": orders[:MAX_ORDERS],
    }


def agent(obs):
    try:
        return _plan(obs)
    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}
