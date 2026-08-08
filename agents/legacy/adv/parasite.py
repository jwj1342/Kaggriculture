"""Opponent-conditioned agent for Kaggriculture.

Same skeleton as agents/probe.py so results are comparable, plus one thing the
probes do not have: it reads the opponent's board every turn and lets that drive
what it produces and when it sells.

The market is the *only* channel between the two farms. You cannot touch their
tiles, animals or shed. And depressing a price requires selling goods, which
requires producing them -- so there is no free "suppress without playing" move.
What there is:

  * The pools are finite and shared (~62 strawberry, ~59 wool, ~76 milk, ~158
    melon before the $1 floor). Selling into a pool first is *simultaneously*
    earning it and denying it. Denial and profit are the same action.
  * Their whole board is public, including every animal's `yield_units` and
    every plant's `planted_day`, so their harvest schedule is computable.
  * The ladder scores win/loss only. Losing by $1 and losing by $100k are the
    same result, which changes what a trailing agent should do.

MODE picks which of those to exploit:

  "frontrun" -- normal economy; sell hard into any product the opponent is about
                to harvest, so their units land on a floor we already took.
  "avoid"    -- steer production away from whatever they are producing, to trade
                in uncontested pools instead of racing for the same ones.
  "parasite" -- the deliberately extreme version: minimal self-investment, never
                meter, dump everything on sight. Tests whether pure denial can
                win on its own. It is expected to lose; it is here to measure
                how much.
  "spite"    -- play normally while ahead, switch to parasite while behind. Since
                margin does not score, a trailing agent has nothing to protect.
"""

import math

MODE = "parasite"    # "frontrun" | "avoid" | "parasite" | "spite"
CROP = "MELON"            # base crop; MODE="avoid" may override per turn
ANIMAL = "COW"            # base animal; MODE="avoid" may override per turn
MAX_QUADRANTS = 3
HAND_CAP = 11
HIRE_BUDGET_FRAC = 0.06
ANIMAL_CAP = 24
FRONTRUN_HORIZON = 2      # days of opponent pipeline treated as imminent

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
MAX_ORDERS = 10
LIQUIDATE_DAY = 28
PRODUCT_OF = {a: d["product"] for a, d in ANIMALS.items()}

WATER_MAX = {}
for _c, _d in CROPS.items():
    if not _d["ongoing"]:
        _w = _d["max_yield_day"] - (_d["max_yield_day"] + 1) // 2 + 1
        WATER_MAX[_c] = min(_d["max_yield"], 1 + _w)


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


def _opponent_model(opp_farm, day):
    """What the opponent is holding and what is about to land, per product.

    `ready`    units sitting harvested-but-unsold on their board right now
    `imminent` units their board will produce within FRONTRUN_HORIZON days
    `capacity` how much of each product their board is built to make at all
    """
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
                elif age >= cd["first_yield_day"] - FRONTRUN_HORIZON:
                    imminent[crop] += max(yu, 1)
            elif "animal" in t:
                a = t.get("animal")
                if a not in ANIMALS:
                    continue
                ad = ANIMALS[a]
                prod = ad["product"]
                capacity[prod] += ad["max_held"]
                ready[prod] += int(t.get("yield_units", 0) or 0)
                age = day - t.get("placed_day", day)
                if age >= ad["first_yield_day"] - FRONTRUN_HORIZON:
                    imminent[prod] += 1
                if t.get("fertilizer_available"):
                    ready["FERTILIZER"] += 1
                capacity["FERTILIZER"] += 1
    return ready, imminent, capacity


def _plan(obs):
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
    money = farm["money"]
    m_inv = dict((obs.get("market", {}) or {}).get("inventory", {}) or {})
    unlocked = farm.get("unlocked_quadrants", ["NW"]) or ["NW"]
    endgame = day >= LIQUIDATE_DAY
    shed_total = sum(shed.values())

    opp_ready, opp_imminent, opp_capacity = _opponent_model(opp, day)
    behind = float(opp.get("money", 0) or 0) > money * 1.15

    mode = MODE
    if mode == "spite":
        # Margin does not score, so a trailing agent has nothing left to protect:
        # switch from building an economy to draining the shared one.
        mode = "parasite" if (behind and day >= 12) else "frontrun"

    crop, animal = CROP, ANIMAL
    if mode == "avoid":
        # Trade in pools they are not already racing us for.
        crop = min(("MELON", "STRAWBERRY", "TOMATO", "CARROT"),
                   key=lambda c: (opp_capacity.get(c, 0), -MARKET_PARAMS[c]["base"]))
        animal = min(("COW", "SHEEP", "GOOSE"),
                     key=lambda a: (opp_capacity.get(PRODUCT_OF[a], 0), ANIMALS[a]["cost"]))
    parasite = (mode == "parasite")
    if parasite:
        crop = "CARROT"        # fastest cycle: 4 days to sellable goods
        animal = None

    struct_kind = ANIMALS[animal]["structure"] if animal else None

    units = [(0, farm["farmer"][0], farm["farmer"][1])]
    for i, pos in enumerate(farm.get("hands", []) or []):
        units.append((i + 1, pos[0], pos[1]))
    n_units = len(units)
    while len(invs) < n_units:
        invs.append({})
    st = _shed_tiles(n)
    st_set = set(st)

    animals_live, empty_structs, plants, weeds, free = [], [], [], [], []
    n_crop = 0
    for y in range(n):
        for x in range(n):
            t = tiles[y][x]
            if t == "LOCKED":
                continue
            if t is None:
                free.append((x, y))
            elif isinstance(t, dict):
                k = t.get("kind")
                if k == "WEED":
                    weeds.append((x, y))
                elif k == "PLANT":
                    plants.append((x, y, t))
                    n_crop += 1
                elif "animal" in t:
                    animals_live.append((x, y, t))
                elif k == struct_kind:
                    empty_structs.append((x, y))

    n_animals = len(animals_live)
    carried = sum(iv.get(animal, 0) for iv in invs[:n_units]) if animal else 0
    in_shed = shed.get(animal, 0) if animal else 0
    waiting = carried + in_shed

    tasks = []
    unfed = 0
    if not endgame:
        for (x, y, t) in animals_live:
            if not t.get("fed_today"):
                unfed += 1
                tasks.append((0 if t.get("consecutive_unfed", 0) >= 1 else 5, x, y, ["FEED"], "WHEAT"))
            held = t.get("yield_units", 0)
            cap = ANIMALS[t["animal"]]["max_held"]
            if held >= cap:
                tasks.append((1, x, y, ["HARVEST"], None))
            if t.get("fertilizer_available"):
                tasks.append((3, x, y, ["COLLECT_FERTILIZER"], None))
            if not t.get("cared_today"):
                tasks.append((6, x, y, ["CARE"], None))
            if 0 < held >= cap - 2:
                tasks.append((8, x, y, ["HARVEST"], None))

        for (x, y, t) in plants:
            cd = CROPS[t["crop"]]
            age = day - t["planted_day"]
            watered = t.get("watered_today", False)
            yu = t.get("yield_units", 0)
            thirsty = t.get("consecutive_unwatered", 0) >= 1
            if cd["ongoing"]:
                if not watered:
                    tasks.append((2 if thirsty else 7, x, y, ["WATER"], None))
                if age >= cd["first_yield_day"] and yu >= 2:
                    tasks.append((4, x, y, ["HARVEST"], None))
            else:
                tgt = WATER_MAX[t["crop"]]
                if age >= cd["first_yield_day"] and (yu >= tgt or age >= cd["max_yield_day"]):
                    tasks.append((1, x, y, ["HARVEST"], None))
                elif not watered:
                    w0 = (cd["max_yield_day"] + 1) // 2
                    if thirsty:
                        tasks.append((2, x, y, ["WATER"], None))
                    elif w0 <= age <= cd["max_yield_day"] and yu < tgt:
                        tasks.append((4, x, y, ["WATER"], None))

        carried_wheat = sum(iv.get("WHEAT", 0) for iv in invs[:n_units])
        gap = unfed - carried_wheat
        if gap > 0 and shed.get("WHEAT", 0) > 0:
            for _ in range(min(n_units, -(-gap // 8))):
                tasks.append((1, None, None, ["PICKUP_WHEAT"], None))

        if animal:
            for _ in range(in_shed):
                tasks.append((5, None, None, ["PICKUP_ANIMAL"], None))
            for (x, y) in empty_structs:
                tasks.append((5, x, y, ["PLACE", animal], animal))
            need = max(0, min(waiting + 2, ANIMAL_CAP - n_animals) - len(empty_structs))
            build = "BUILD_PASTURE" if struct_kind == "PASTURE" else "BUILD_COOP"
        else:
            need, build = 0, None

        last_day = {"WHEAT": 24, "CARROT": 25, "TOMATO": 19, "STRAWBERRY": 13, "MELON": 18}
        can_plant = seeds.get(crop, 0) if crop else 0
        for (x, y) in sorted(free, key=lambda p: min(_dist(p[0], p[1], sx, sy) for sx, sy in st)):
            if need > 0:
                tasks.append((5, x, y, [build], None))
                need -= 1
            elif crop and can_plant > 0 and day <= last_day[crop]:
                tasks.append((7, x, y, ["PLANT", crop], None))
                can_plant -= 1
        for (x, y) in weeds:
            tasks.append((9, x, y, ["DIG"], None))
    else:
        for (x, y, t) in animals_live:
            if t.get("yield_units", 0) > 0:
                tasks.append((0, x, y, ["HARVEST"], None))
        for (x, y, t) in plants:
            if t.get("yield_units", 0) > 0 and day - t["planted_day"] >= CROPS[t["crop"]]["first_yield_day"]:
                tasks.append((0, x, y, ["HARVEST"], None))

    tasks.sort(key=lambda t: t[0])

    actions = [None] * n_units
    busy = [False] * n_units
    claimed = set()
    wheat_left = shed.get("WHEAT", 0)
    animals_left = in_shed

    for (prio, tx, ty, act, need_item) in tasks:
        op = act[0]
        if tx is None:
            best, bd, bt = None, None, None
            for k, (idx, ux, uy) in enumerate(units):
                if busy[k]:
                    continue
                if op == "PICKUP_WHEAT" and invs[idx].get("WHEAT", 0) >= 4:
                    continue
                if op == "PICKUP_ANIMAL" and animal and invs[idx].get(animal, 0):
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
                else:
                    if animals_left <= 0:
                        continue
                    animals_left -= 1
                    actions[best] = ["PICKUP", animal, 1]
            else:
                actions[best] = [_step_toward(ux, uy, bt[0], bt[1])]
            busy[best] = True
            continue

        if (tx, ty, op) in claimed:
            continue
        best, bd = None, None
        for k, (idx, ux, uy) in enumerate(units):
            if busy[k] or (need_item and invs[idx].get(need_item, 0) <= 0):
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
        produce = sum(v for it, v in inv.items() if it in PRODUCTS and it != "WHEAT")
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

    # ---------------- market ----------------
    orders = []
    spend = 0.0

    def afford(c):
        return money - spend >= c

    if not endgame:
        if HAND_CAP > 0 and hour <= 3:
            hires = farm.get("hires_today", 0)
            payroll = sum(_fib(i) for i in range(hires))
            cap = 4 if parasite else HAND_CAP
            budget = max(4.0, money * HIRE_BUDGET_FRAC)
            while len(orders) < 7 and hires < cap:
                c = _fib(hires)
                if payroll + c > budget or not afford(c + 40):
                    break
                orders.append(["HIRE"])
                spend += c
                payroll += c
                hires += 1

        n_extra = len(unlocked) - 1
        max_q = 1 if parasite else MAX_QUADRANTS
        if n_extra < min(len(LAND_PRICES), max_q - 1) and len(orders) < MAX_ORDERS:
            price = LAND_PRICES[n_extra]
            if len(free) <= 8 and afford(price + [600, 1500, 3000][n_extra]):
                orders.append(["BUY_LAND"])
                spend += price

        if (animal and len(orders) < MAX_ORDERS and day <= 23 and waiting < 2
                and n_animals + waiting < ANIMAL_CAP and shed_total < SHED_CAPACITY - 8):
            c = ANIMALS[animal]["cost"]
            if afford(c + (100 if day < 12 else 400)):
                orders.append(["BUY_ANIMAL", animal, 1])
                spend += c

        if crop and len(orders) < MAX_ORDERS and len(free) > 0:
            c = CROPS[crop]["seed"]
            k = max(0, min(6, len(free) - seeds.get(crop, 0)))
            if k > 0 and afford(c * k + 100):
                orders.append(["BUY_SEED", crop, k])
                spend += c * k

        if n_animals and len(orders) < MAX_ORDERS and shed_total < SHED_CAPACITY - 10:
            need_w = min(28, n_animals * 2)
            if shed.get("WHEAT", 0) < need_w:
                wp = market_price("WHEAT", m_inv.get("WHEAT", 10000) - 1)
                k = min(10, need_w - shed.get("WHEAT", 0))
                if afford(wp * k + 150):
                    orders.append(["BUY_PRODUCT", "WHEAT", k])
                    spend += wp * k

    # Sell sizing. `pressure` is how much of this product the opponent is about
    # to push into the same market -- the more they are holding, the more it is
    # worth taking the price down to the floor before their units arrive.
    sellable = []
    for item in PRODUCTS:
        held = shed.get(item, 0)
        if held <= 0:
            continue
        if item == "WHEAT" and not endgame and n_animals:
            held = max(0, held - min(28, n_animals * 2))
            if held <= 0:
                continue
        inv0 = m_inv.get(item, 10000)
        threat = opp_ready.get(item, 0) + opp_imminent.get(item, 0)
        sellable.append((market_price(item, inv0) * min(held, 8) + threat * 50,
                         item, held, inv0, threat))
    sellable.sort(reverse=True)

    shed_pressure = shed_total >= 74
    for (_, item, held, inv0, threat) in sellable:
        if len(orders) >= MAX_ORDERS:
            break
        if endgame or parasite:
            qty = min(held, 40)
        else:
            base = MARKET_PARAMS[item]["base"]
            floor_frac = 0.0 if item == "FERTILIZER" else 0.55
            batch = 8
            if mode == "frontrun" and threat >= 4:
                # They are about to dump this. Get in front: bigger batch, and
                # accept a worse price, because the price is going there anyway.
                floor_frac *= 0.5
                batch = 20
            floor = base * floor_frac
            qty = 0
            lim = min(batch, held)
            while qty < lim and market_price(item, inv0 + qty) >= floor:
                qty += 1
            if shed_pressure and qty == 0:
                qty = min(held, 8)
        if qty > 0:
            orders.append(["SELL", item, qty])

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
