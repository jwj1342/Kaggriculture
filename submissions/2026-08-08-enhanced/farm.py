"""Board survey and the action scheduler.

Every turn: read the board, emit a list of pending tasks ranked by
coins-per-action, and greedily assign each to the nearest capable idle unit.

Priorities are ordered by measured value, with anything that destroys an asset
pulled to the front regardless of its marginal return. The numbers behind the
ordering are in docs/GAME_ECONOMICS.md; the short version is that harvesting a
full animal is ~6 units in one action, a melon watered inside its bonus window is
+1 melon (~$250) for one action, and CARE is +$160/day for one action, while
wheat is ~$25/action and not worth an action anyone else wants.

Two logistics facts drive most of the structure:
  * FEED takes wheat from the *acting unit's* inventory, not the shed, and
    PICKUP only works on the four tiles beside the shed. Restock trips are
    therefore first-class tasks, not something idle units improvise. Without
    that the schedule deadlocks and the whole herd starves.
  * Harvested goods sit in a unit's inventory until end of day unless it walks
    back and DROPs, so produce cannot be sold the day it is picked without a
    deliberate trip.
"""

from engine import (ANIMALS, CROPS, SHED_CAPACITY, WATER_MAX,
                    dist, shed_tiles, step_toward)


def survey(farm, board):
    """One pass over the tiles, returning everything the planner needs."""
    animals, empty_structs, plants, weeds, free, owned = [], [], [], [], [], []
    counts = {a: 0 for a in ANIMALS}
    crops = {c: 0 for c in CROPS}
    for y in range(board):
        row = farm["tiles"][y]
        for x in range(board):
            t = row[x]
            if t == "LOCKED":
                continue
            owned.append((x, y))
            if t is None:
                free.append((x, y))
            elif isinstance(t, dict):
                kind = t.get("kind")
                if kind == "WEED":
                    weeds.append((x, y))
                elif kind == "PLANT":
                    plants.append((x, y, t))
                    crops[t["crop"]] = crops.get(t["crop"], 0) + 1
                elif "animal" in t:
                    animals.append((x, y, t))
                    counts[t["animal"]] = counts.get(t["animal"], 0) + 1
                else:
                    empty_structs.append((x, y, kind))
    return {"animals": animals, "empty_structs": empty_structs, "plants": plants,
            "weeds": weeds, "free": free, "owned": owned,
            "counts": counts, "crops": crops}


def build_tasks(view, plan, day, shed, seeds, endgame, n_units, invs, money):
    """Pending work, as (priority, x, y, action, required_item).

    x is None for a shed errand, which is resolved per-unit at assignment time.
    """
    tasks = []
    if endgame:
        # Only harvesting matters now; everything else is sunk cost. Unsold
        # inventory scores zero, so the last two days are pure liquidation.
        for (x, y, t) in view["animals"]:
            if t.get("yield_units", 0) > 0:
                tasks.append((0, x, y, ["HARVEST"], None))
        for (x, y, t) in view["plants"]:
            cd = CROPS[t["crop"]]
            if t.get("yield_units", 0) > 0 and day - t["planted_day"] >= cd["first_yield_day"]:
                tasks.append((0, x, y, ["HARVEST"], None))
        return tasks

    unfed = 0
    for (x, y, t) in view["animals"]:
        starving = t.get("consecutive_unfed", 0) >= 1
        if not t.get("fed_today"):
            unfed += 1
            tasks.append((0 if starving else 6, x, y, ["FEED"], "WHEAT"))
        held = t.get("yield_units", 0)
        cap = ANIMALS[t["animal"]]["max_held"]
        if held >= cap:
            # A full animal stops producing. ~6 units in one action.
            tasks.append((1, x, y, ["HARVEST"], None))
        if t.get("fertilizer_available"):
            # Free every day, and gone if not collected today.
            tasks.append((4, x, y, ["COLLECT_FERTILIZER"], None))
        if not t.get("cared_today"):
            tasks.append((7, x, y, ["CARE"], None))
        if 0 < held >= cap - 2:
            tasks.append((9, x, y, ["HARVEST"], None))

    for (x, y, t) in view["plants"]:
        crop = t["crop"]
        cd = CROPS[crop]
        age = day - t["planted_day"]
        watered = t.get("watered_today", False)
        units = t.get("yield_units", 0)
        thirsty = t.get("consecutive_unwatered", 0) >= 1
        if cd["ongoing"]:
            if not watered:
                tasks.append((2 if thirsty else 8, x, y, ["WATER"], None))
            if age >= cd["first_yield_day"] and units >= 2:
                tasks.append((3, x, y, ["HARVEST"], None))
        else:
            target = WATER_MAX[crop]
            ripe = age >= cd["first_yield_day"] and (units >= target or age >= cd["max_yield_day"])
            if ripe:
                tasks.append((1, x, y, ["HARVEST"], None))
            elif not watered:
                window_start = (cd["max_yield_day"] + 1) // 2
                if thirsty:
                    tasks.append((2, x, y, ["WATER"], None))
                elif window_start <= age <= cd["max_yield_day"] and units < target:
                    tasks.append((3 if crop == "MELON" else 8, x, y, ["WATER"], None))

    # Feed logistics. Without explicit restock trips every unit stays busy with
    # watering and care and the herd starves -- measured at ~45k.
    carried = sum(iv.get("WHEAT", 0) for iv in invs[:n_units])
    gap = unfed - carried
    if gap > 0 and shed.get("WHEAT", 0) > 0:
        for _ in range(min(n_units, -(-gap // 8))):
            tasks.append((1, None, None, ["PICKUP_WHEAT"], None))

    # Animals bought but not yet placed are dead capital and a wasted shed slot.
    in_shed = sum(shed.get(a, 0) for a in ANIMALS)
    for _ in range(in_shed):
        tasks.append((5, None, None, ["PICKUP_ANIMAL"], None))
    for (x, y, kind) in view["empty_structs"]:
        for a in ANIMALS:
            if ANIMALS[a]["structure"] == kind:
                tasks.append((5, x, y, ["PLACE", a], a))

    # Build pens for animals that are waiting, and a little ahead of what we can
    # afford, but never more than the plan wants.
    waiting = {a: shed.get(a, 0) + sum(iv.get(a, 0) for iv in invs[:n_units])
               for a in ANIMALS}
    free_pasture = sum(1 for e in view["empty_structs"] if e[2] == "PASTURE")
    free_coop = sum(1 for e in view["empty_structs"] if e[2] == "COOP")
    want_pasture = max(0, waiting["COW"] + waiting["SHEEP"] - free_pasture)
    want_coop = max(0, waiting["GOOSE"] - free_coop)
    target_animals = sum(plan["animals"].values())
    placed = sum(view["counts"].values())
    room = max(0, target_animals - placed - len(view["empty_structs"]))
    lookahead = 0 if money < 900 else min(2, room)
    plan_pasture = max(0, plan["animals"].get("COW", 0) + plan["animals"].get("SHEEP", 0)
                       - view["counts"]["COW"] - view["counts"]["SHEEP"]
                       - free_pasture - want_pasture)
    queue = (["BUILD_PASTURE"] * want_pasture + ["BUILD_COOP"] * want_coop
             + ["BUILD_PASTURE" if plan_pasture > 0 else "BUILD_COOP"] * lookahead)[:room]

    # Zoning: the tiles nearest the shed go to animals, which want three visits a
    # day; crops want one and can live on the outside.
    st = shed_tiles(len(view["owned"]) and max(p[0] for p in view["owned"]) + 1 or 10)

    def shed_dist(p):
        return min(dist(p[0], p[1], sx, sy) for sx, sy in st)

    owned = sorted(view["owned"], key=lambda p: (shed_dist(p), p[1], p[0]))
    zone_size = min(len(owned) - 2, max(4, placed + len(view["empty_structs"])
                                        + sum(waiting.values()) + 3))
    zone = set(owned[:max(0, min(zone_size, target_animals))])

    budget = dict(seeds)
    want = [[c, max(0, n - view["crops"].get(c, 0))] for c, n in plan["crops"]]
    for (x, y) in sorted(view["free"], key=lambda p: (shed_dist(p), p[1], p[0])):
        if (x, y) in zone:
            if queue:
                tasks.append((5, x, y, [queue.pop(0)], None))
            continue
        for entry in want:
            crop, remaining = entry
            if remaining > 0 and budget.get(crop, 0) > 0:
                tasks.append((6 if crop == "MELON" else 10, x, y, ["PLANT", crop], None))
                budget[crop] -= 1
                entry[1] -= 1
                break

    # A weed squats on a tile worth a melon cycle; clearing one is cheap.
    weed_prio = 6 if len(view["free"]) <= len(view["weeds"]) + 4 else 11
    for (x, y) in view["weeds"]:
        tasks.append((weed_prio, x, y, ["DIG"], None))

    return tasks


def assign(tasks, units, invs, shed, view, board, endgame, shed_total):
    """Greedy nearest-capable assignment. Returns one action per unit."""
    st = shed_tiles(board)
    st_set = set(st)
    n = len(units)
    actions = [None] * n
    busy = [False] * n
    claimed = set()
    wheat_left = shed.get("WHEAT", 0)
    animals_left = {a: shed.get(a, 0) for a in ANIMALS}
    open_kinds = {e[2] for e in view["empty_structs"]}

    for (prio, tx, ty, act, need) in sorted(tasks, key=lambda t: t[0]):
        op = act[0]

        if tx is None:                                   # shed errand
            best, best_d, best_t = None, None, None
            for k, (idx, ux, uy) in enumerate(units):
                if busy[k]:
                    continue
                if op == "PICKUP_WHEAT" and invs[idx].get("WHEAT", 0) >= 4:
                    continue
                if op == "PICKUP_ANIMAL" and any(invs[idx].get(a, 0) for a in ANIMALS):
                    continue
                tgt = min(st, key=lambda p: dist(ux, uy, p[0], p[1]))
                d = dist(ux, uy, tgt[0], tgt[1])
                if best_d is None or d < best_d:
                    best, best_d, best_t = k, d, tgt
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
                    pick = next((a for a in ("COW", "SHEEP", "GOOSE")
                                 if animals_left.get(a, 0) > 0
                                 and ANIMALS[a]["structure"] in open_kinds), None)
                    pick = pick or next((a for a in ("COW", "SHEEP", "GOOSE")
                                         if animals_left.get(a, 0) > 0), None)
                    if pick is None:
                        continue
                    animals_left[pick] -= 1
                    actions[best] = ["PICKUP", pick, 1]
            else:
                actions[best] = [step_toward(ux, uy, best_t[0], best_t[1])]
            busy[best] = True
            continue

        if (tx, ty, op) in claimed:
            continue
        best, best_d = None, None
        for k, (idx, ux, uy) in enumerate(units):
            if busy[k] or (need and invs[idx].get(need, 0) <= 0):
                continue
            d = dist(ux, uy, tx, ty)
            if best_d is None or d < best_d:
                best, best_d = k, d
        if best is None:
            continue
        idx, ux, uy = units[best]
        actions[best] = act if (ux, uy) == (tx, ty) else [step_toward(ux, uy, tx, ty)]
        busy[best] = True
        claimed.add((tx, ty, op))

    # Idle units run produce back to the shed so it can be sold today rather
    # than tomorrow, and pick up feed while they are there.
    n_animals = len(view["animals"])
    for k, (idx, ux, uy) in enumerate(units):
        if busy[k]:
            continue
        inv = invs[idx]
        produce = sum(v for it, v in inv.items()
                      if it not in ANIMALS and it != "WHEAT")
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
            tgt = min(st, key=lambda p: dist(ux, uy, p[0], p[1]))
            mv = step_toward(ux, uy, tgt[0], tgt[1])
            actions[k] = [mv] if mv else ["PASS"]
        else:
            actions[k] = ["PASS"]
        busy[k] = True

    return actions
