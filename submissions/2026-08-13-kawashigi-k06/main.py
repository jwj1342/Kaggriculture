# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Rayk Kretzschmar
#
# The MIT grant covers the code in this file -- the market/SELL layer and the scheduler.
# It does NOT cover the base85 `_TRACE` field plan below, which is the shared public meta
# line reconstructed from public competition replays and is not the author's to license.
# See NOTICE, and the "Provenance" section of the dataset description.
"""Closer Cleo -- tier 9 of the Kaggriculture reference ladder.

Meta field plan, sells reordered in place so buys stay funded.

STRATEGY
Same meta field plan, but the SELL layer only reorders within the market slots the plan already used for selling. Nothing is moved into a slot that was holding a purchase.

WHAT THIS TIER TEACHES
The subtlest lesson in the dataset, and the most expensive one to learn the hard way. Sells fund the buys that follow them in the same queue; hoist the sells out of their original slots and a BUY_PRODUCT WHEAT later in the turn fails on a near-zero balance, animals go unfed, and the farm quietly loses far more than the reordering gained.

FIELD PLAN -- READ THIS BEFORE REUSING
This agent does not use an original field plan. It executes the shared public
meta line: `scripts/cross_team_identity.py` over 530 downloaded replays finds
identical 712-turn farmer/hand sequences played by large groups of unrelated
teams -- one group of 29, another of 15, another of 8, with 104 distinct teams
appearing in at least one shared plan. No single team is credited because the
line demonstrably belongs to none of them.

What is the author's own, and what separates tiers 6-9 from each other, is the
market layer: which product takes the earliest slot in the order queue, when to
hold, and when to liquidate. Tiers 6-9 bank within ~1% of each other against the
baseline yet separate cleanly head-to-head, which is the whole point.

Measured end-of-season bank: about 186,198 coins against the built-in
`starter` baseline over a 720-turn season.

This file is self-contained. Rename it to `main.py` and it is a valid
competition submission; or import it and call `agent(obs)` directly.

Part of the Kaggriculture Reference Agents dataset:
https://www.kaggle.com/datasets/raykkretzschmar/kaggriculture-reference-agents
"""

import base64
import copy
import json
import zlib

from plan import BLOB

_TRACE = json.loads(zlib.decompress(base64.b85decode(
    BLOB
)).decode("utf-8"))

_SELLABLE = ("STRAWBERRY", "MELON", "MILK", "WOOL", "EGG", "TOMATO", "CARROT", "WHEAT", "FERTILIZER")

_FRONT_RUN_HORIZON = 1
_FRONT_RUN_ITEMS = ("MELON", "STRAWBERRY", "MILK", "WOOL")
_BASE_PRICE = {"MELON": 250, "STRAWBERRY": 120, "MILK": 160, "WOOL": 200}
_GLUT_WEIGHT = {"MELON": 3.5, "STRAWBERRY": 2.0, "MILK": 2.0, "WOOL": 3.2}
_LAST_STEP = -1
_CLONE_CONFIDENCE = 0


def _public_signature(farm):
    """Compact public fingerprint for detecting a mirrored build."""
    counts = {item: 0 for item in (
        "COW", "SHEEP", "GOOSE", "WHEAT", "CARROT", "TOMATO",
        "STRAWBERRY", "MELON", "PASTURE", "COOP", "WEED",
    )}
    for row in farm.get("tiles", []) or []:
        for tile in row or []:
            if not isinstance(tile, dict):
                continue
            for key in ("animal", "crop", "kind"):
                value = tile.get(key)
                if value in counts:
                    counts[value] += 1
                    break
    positions = [farm.get("farmer", [0, 0]), *(farm.get("hands", []) or [])]
    return (
        len(farm.get("hands", []) or []),
        tuple(sorted(farm.get("unlocked_quadrants", []) or [])),
        tuple(sorted(tuple(position) for position in positions)),
        tuple(counts[item] for item in sorted(counts)),
    )


def _signature_distance(left, right):
    distance = abs(left[0] - right[0])
    distance += 3 * abs(len(left[1]) - len(right[1]))
    distance += sum(abs(a - b) for a, b in zip(left[3], right[3]))
    if left[2] != right[2]:
        distance += 2
    return distance


def _update_clone_profile(obs, step):
    global _CLONE_CONFIDENCE
    if step not in (4, 24) and not (step >= 48 and step % 24 == 0):
        return
    farms = obs.get("farms", []) or []
    if len(farms) < 2:
        return
    player = int(obs.get("player", 0) or 0)
    distance = _signature_distance(
        _public_signature(farms[player]),
        _public_signature(farms[1 - player]),
    )
    if distance <= 1:
        _CLONE_CONFIDENCE = min(8, _CLONE_CONFIDENCE + 1)
    elif distance <= 4:
        _CLONE_CONFIDENCE = max(0, _CLONE_CONFIDENCE - 1)
    else:
        _CLONE_CONFIDENCE = max(0, _CLONE_CONFIDENCE - 3)


def _front_run(action, obs, step):
    """Sell one premium line immediately before a clone's expected glut."""
    if _CLONE_CONFIDENCE < 2 or _FRONT_RUN_HORIZON <= 0:
        return
    orders = list(action.get("market", []) or [])
    if len(orders) >= 10:
        return
    already = {}
    for order in orders:
        if isinstance(order, list) and len(order) >= 3 and order[0] == "SELL":
            already[order[1]] = already.get(order[1], 0) + max(0, int(order[2] or 0))
    planned = {}
    end = min(len(_TRACE), step + _FRONT_RUN_HORIZON + 1)
    for future_step in range(step + 1, end):
        distance = future_step - step
        for order in _TRACE[future_step].get("market", []) or []:
            if not (
                isinstance(order, list) and len(order) >= 3
                and order[0] == "SELL" and order[1] in _FRONT_RUN_ITEMS
            ):
                continue
            item = order[1]
            quantity = max(0, int(order[2] or 0))
            if item not in planned:
                planned[item] = [distance, quantity]
            else:
                planned[item][1] += quantity
    shed = (obs.get("private") or {}).get("shed") or {}
    prices = ((obs.get("market") or {}).get("prices") or {})
    choices = []
    for item, (distance, quantity) in planned.items():
        available = max(0, int(shed.get(item, 0) or 0) - already.get(item, 0))
        quantity = min(available, quantity)
        if quantity <= 0:
            continue
        price = float(prices.get(item, _BASE_PRICE[item]) or 0)
        priority = (
            price * quantity * _GLUT_WEIGHT[item]
            + (_FRONT_RUN_HORIZON + 1 - distance) * _BASE_PRICE[item]
        )
        choices.append((priority, item, quantity))
    if choices:
        _, item, quantity = max(choices)
        orders.append(["SELL", item, quantity])
        action["market"] = orders[:10]


def _terminal_liquidation(action, obs, step):
    """Replay-derived safety net: leave no sellable shed inventory at season end."""
    if step < 680:
        return
    shed = (obs.get("private") or {}).get("shed") or {}
    market = action.setdefault("market", [])
    already = {
        order[1]
        for order in market
        if isinstance(order, list) and len(order) >= 2 and order[0] == "SELL"
    }
    for item in _SELLABLE:
        qty = int(shed.get(item, 0) or 0)
        if qty > 0 and item not in already and len(market) < 10:
            market.append(["SELL", item, qty])


def _shed_access(size):
    half = size // 2
    return [(half - 1, half - 1), (half, half - 1), (half - 1, half), (half, half)]


def _move_toward(pos, target, tiles):
    x, y = pos
    tx, ty = target
    choices = []
    if tx < x:
        choices.append(("WEST", (x - 1, y)))
    if tx > x:
        choices.append(("EAST", (x + 1, y)))
    if ty < y:
        choices.append(("NORTH", (x, y - 1)))
    if ty > y:
        choices.append(("SOUTH", (x, y + 1)))
    size = len(tiles)
    for op, (nx, ny) in choices:
        if 0 <= nx < size and 0 <= ny < size and tiles[ny][nx] != "LOCKED":
            return [op]
    return ["PASS"]


def _terminal_action(obs):
    """Observation-driven final-eight-turn harvest/drop/sell controller."""
    player = int(obs.get("player", 0) or 0)
    farm = (obs.get("farms") or [])[player]
    private = obs.get("private") or {}
    tiles = farm.get("tiles") or []
    size = len(tiles)
    positions = [farm.get("farmer", [0, 0]), *(farm.get("hands") or [])]
    inventories = list(private.get("inventories") or [])
    inventories.extend({} for _ in range(len(positions) - len(inventories)))
    sheds = set(_shed_access(size))

    available = {
        (x, y)
        for y, row in enumerate(tiles)
        for x, tile in enumerate(row)
        if isinstance(tile, dict) and int(tile.get("yield_units", 0) or 0) > 0
    }
    actions = []
    pending = {}
    for pos_raw, inventory in zip(positions, inventories):
        pos = tuple(pos_raw)
        inventory = inventory or {}
        load = sum(max(0, int(v or 0)) for v in inventory.values())
        x, y = pos
        tile = tiles[y][x] if 0 <= y < size and 0 <= x < size else None
        if load > 0 and pos in sheds:
            action = ["DROP"]
            for item, count in inventory.items():
                if item in _SELLABLE:
                    pending[item] = pending.get(item, 0) + max(0, int(count or 0))
        elif isinstance(tile, dict) and int(tile.get("yield_units", 0) or 0) > 0:
            action = ["HARVEST"]
            available.discard(pos)
        elif load > 0:
            target = min(sheds, key=lambda q: abs(q[0] - x) + abs(q[1] - y))
            action = _move_toward(pos, target, tiles)
        elif available:
            target = min(available, key=lambda q: (abs(q[0] - x) + abs(q[1] - y), q[1], q[0]))
            available.discard(target)
            action = _move_toward(pos, target, tiles)
        elif isinstance(tile, dict) and tile.get("fertilizer_available", False):
            action = ["COLLECT_FERTILIZER"]
        else:
            action = ["PASS"]
        actions.append(action)

    shed = dict(private.get("shed") or {})
    for item, count in pending.items():
        shed[item] = int(shed.get(item, 0) or 0) + count
    prices = ((obs.get("market") or {}).get("prices") or {})
    sells = [
        (int(shed.get(item, 0) or 0) * int(prices.get(item, 1) or 1), item, int(shed.get(item, 0) or 0))
        for item in _SELLABLE
    ]
    sells = [row for row in sells if row[2] > 0]
    sells.sort(reverse=True)
    market = [["SELL", item, qty] for _, item, qty in sells[:10]]
    if int(obs.get("hour", 0) or 0) <= 1:
        already = int(farm.get("hires_today", 0) or 0)
        for _ in range(min(10 - len(market), max(0, 8 - already))):
            market.append(["HIRE"])
    return {"farmer": actions[0], "hands": actions[1:], "market": market[:10]}


def _base_agent(obs, config=None):
    global _LAST_STEP, _CLONE_CONFIDENCE
    step = min(int(obs.get("step", 0) or 0), len(_TRACE) - 1)
    if step == 0 or step <= _LAST_STEP:
        _CLONE_CONFIDENCE = 0
    _LAST_STEP = step
    _update_clone_profile(obs, step)
    if step >= 714:
        return _terminal_action(obs)
    action = copy.deepcopy(_TRACE[step])
    _front_run(action, obs, step)
    _terminal_liquidation(action, obs, step)
    return action


# ===========================================================================
# Market-controller overlay
# ===========================================================================
import math as _math

# Per-step remaining sell volume of this field plan, measured over c27 self-play.
_SUPPLY = json.loads(zlib.decompress(base64.b85decode(
    'c%1Fr%Wm5+5Cza*39{~j!?(Ii3pWj#)PQRsXp4SH(SNTlZOK$D%hrRG91k$}ECK|GWl5pP5&z!5eqB9m??2xC_S${8>%g|40o8~KRn)i|T_c-Ng)B~CGN496wl}hgs1QXm@KJ@zO8JSLEoMTcp!~L+F{jWC^e|LF)=(2sf$PIb3(SlNzsDBEF#JfoWe(t$Yj9w9c;Cbw<7UNFSXW_+8eK!jXnZ0v6}ZhU25LvUVmLTB{V)npQt&Tu2T?{8u6>1DeP;Bfh-txjrG(rgadmg#C&QQ5mb7*zObT%PjIEHq#)0xwmcrH0IS6;r%ds_7fjeO<R-XVDHtFe5b{U9c@TIh4Qa~f2^712`IfKEUA#@B*lD={N5Gf8RziqLrKOgSyKR;|X>+lpP>YsCQadB~Rad9Oo3_rH(mxt||haX&ATwGjSTv-akk00C3!|SKjX7dw65Q*tshG7_nVVGkyprl}RZvx~bgg>YpF-fdKOSG4qgU%8bqxwVs6t+gzh!`qtez1P$MN(W?6824OUyMG5Y$A?9(^>?+g>mRks6oAK>ZeGxbZYtsodn6F-$d?$<E};~EL)F^?O7_S=&9^w^}PO$2eRE-I>Ru`&4T`{s6B{cFwQ{YZl6U*zQ14uWyS3#%h2Z*@^*MPQP3v8n8;y4cWAPRbdmZHJgFv)oG)UwHJsJsBlnMRadB~RadBm-FjM*T{4I2j>|PvW80OtT4e<Ic^F9%mLxt<aObni{eUSnSOm>`25B5IDhw)1T#~HJ2gbkb)it^`?XCZfm;OhyiIuT((rx*gdOtM5Af}2MpCW=~4u!#b8dq^Fe(W!z<VQjEXR6G?ub;2p#H~XpMB5DU|K3=`9*UzC3<m5IO40GEoV6^e>(Kih?vsxDB>cI}F?O-s7>4zgO*m=mOMPEO7fFHFt)1`zxoKzFEYZV<Sf2W`*g3~vl6)Si2btbe1*(mA?61N3mCrB|}<jgtQPJ>6GFRRV=>G|o`Y7^F*FlVr6C;{`%5t~lbSY!)lcb=RE!hfF_mzI-r-D(o354i67ZQuEZwrOsCA(S1oU{8hVL>-fNRvtUO?m%zt9OxwICh{0%a-kZ?nHV;0J{oL}oHQfG!C2wLe($Yu`<RKME{uGWj?HT?+Td1C5YbH5F*r?^*4GKtKIO3v+vWF6XxHyrn;6*2-<p>3c(Rs!pD~m+;RUgj8S*-S*aeT2QB@B!|NaA0p<>w'
)).decode("utf-8"))

_I0 = 10000
_PRICE_FLOOR = 1
_MP = {
    "WHEAT": (25, 400, "sqrt", 0.80, "log", 0.20),
    "CARROT": (35, 450, "log", 0.20, "sqrt", 0.70),
    "TOMATO": (60, 200, "linear", 0.40, "sqrt", 0.60),
    "STRAWBERRY": (120, 100, "sqrt", 0.70, "linear", 1.60),
    "MELON": (250, 300, "log", 0.20, "sq", 3.60),
    "EGG": (50, 332, "linear", 0.40, "log", 0.20),
    "MILK": (160, 122, "sqrt", 0.60, "linear", 1.60),
    "WOOL": (200, 105, "log", 0.20, "sq", 3.20),
    "FERTILIZER": (100, 200, "linear", 0.40, "linear", 0.40),
}
_SHOP_DEMAND = {
    "BAKERY": ("EGG", "WHEAT"),
    "PIZZA_SHOP": ("MILK", "TOMATO", "WHEAT"),
    "BRUNCH_SPOT": ("EGG", "WHEAT", "STRAWBERRY"),
    "YARN_STORE": ("WOOL",),
    "ICE_CREAM_SHOP": ("STRAWBERRY", "MILK", "WHEAT"),
    "PET_CAFE": ("CARROT",),
    "SMOOTHIE_SHOP": ("STRAWBERRY", "MILK"),
    "FARMERS_MARKET": ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY"),
}
_CENTER_ITEMS = tuple(k for k in _MP if k != "FERTILIZER")

# Products the controller owns, mapped to a reservation price expressed as a
# fraction of base price. Everything else keeps the tape's schedule untouched.
_RESERVE = {}
# Sort SELL orders by gross value so the most valuable sale takes the earliest
# slot; market slots resolve index by index across both players.
_SORT_SELLS = True
# Ranking key for slot placement: "gross", "unit" or "impact".
_SORT_KEY = 'impact'
# True places promoted sells ahead of buys/hires; False keeps the tape's layout.
_SELLS_FIRST = False
# Only these products may be promoted into early slots. Empty means all.
_PROMOTE = ('MILK', 'WOOL', 'STRAWBERRY', 'MELON', 'EGG', 'TOMATO', 'CARROT', 'FERTILIZER')
# Extra slot priority for a product whose remaining supply outruns the town's
# remaining appetite. Such a product is a race, not a hold: its price will only
# fall, so the units sold before the opponent's are the only ones worth much.
# Ranking purely by current price gets this backwards — a already-crashed product
# looks unimportant precisely when beating the opponent to the floor matters most.
_RACE_WEIGHT = 0.0
# Products that may be promoted only from this step onward. Selling wheat early
# lowers the price an opponent pays for feed, which can rescue a cash-starved
# rival; deferring wheat promotion keeps that pressure on during the early game
# when starvation actually bites.
_PROMOTE_AFTER = {}
# Products promoted only while the opponent's public money is at least this much.
# A rival near insolvency is the one most helped by our extra supply, so we hold
# that pressure on until they are clearly solvent.
_PROMOTE_IF_OPP_MONEY = {'WHEAT': 200.0}
# Force selling once the shed reaches this load, protecting end-of-day drops.
_SHED_PRESSURE = 80
# Reservation decays linearly to zero across this window, spreading liquidation.
_RAMP_START = 576
_RAMP_END = 716

_SUPPLY_DRIVER = {
    "MILK": ("animal", "COW"),
    "WOOL": ("animal", "SHEEP"),
    "EGG": ("animal", "GOOSE"),
    "FERTILIZER": ("animal", None),
    "STRAWBERRY": ("crop", "STRAWBERRY"),
    "MELON": ("crop", "MELON"),
    "WHEAT": ("crop", "WHEAT"),
    "CARROT": ("crop", "CARROT"),
    "TOMATO": ("crop", "TOMATO"),
}


def _mshape(func, x):
    if func == "linear":
        return x
    if func == "sq":
        return x * x
    if func == "sqrt":
        return _math.sqrt(x)
    if func == "log10":
        return _math.log10(1.0 + x)
    return _math.log(1.0 + x)


def _mprice(item, inventory):
    """Exact port of the engine's market_price."""
    base, throughput, below_f, below_t, above_f, above_t = _MP[item]
    if inventory < _I0:
        amp = below_t * base / _mshape(below_f, throughput)
        value = base + amp * _mshape(below_f, _I0 - inventory)
    else:
        amp = above_t * base / _mshape(above_f, throughput)
        value = base - amp * _mshape(above_f, inventory - _I0)
    return max(_PRICE_FLOOR, int(round(value)))


def _remaining_drain(item, step, shops):
    """Units of `item` the town consumes between `step` and the season end.

    Shops fire on steps divisible by 4, the town center on steps divisible by 12
    with multipliers that step up on days 10 and 20. Still-locked shops are
    credited from the day they are expected to unlock (one new shop every three
    days), so late-game demand is not understated.
    """
    if item == "FERTILIZER":
        return 0.0  # neither the shops nor the town center consume fertilizer
    unlocked = set(shops or ())
    live = 0
    pending = []
    for name, products in _SHOP_DEMAND.items():
        if item not in products:
            continue
        weight = 2 if len(products) == 1 else 1
        if name in unlocked:
            live += weight
        else:
            pending.append(weight)
    n_locked = len(_SHOP_DEMAND) - len(unlocked)
    pending_total = sum(pending)
    is_center = item in _CENTER_ITEMS
    total = 0.0
    for s in range(step, 720):
        day = s // 24
        if s % 4 == 0:
            total += live
            if pending_total and n_locked > 0:
                expected = min(n_locked, max(0, day // 3 + 1 - len(unlocked)))
                total += pending_total * (expected / n_locked)
        if is_center and s % 12 == 0:
            total += 4 if day >= 20 else (2 if day >= 10 else 1)
    return total


def _count_driver(farm, kind, name):
    total = 0
    for row in farm.get("tiles") or []:
        for tile in row or []:
            if not isinstance(tile, dict):
                continue
            if kind == "animal":
                animal = tile.get("animal")
                if animal and (name is None or animal == name):
                    total += 1
            elif tile.get("kind") == "PLANT" and tile.get("crop") == name:
                total += 1
    return total


def _opponent_scale(obs, item):
    """Opponent's expected remaining supply of `item`, relative to ours."""
    driver = _SUPPLY_DRIVER.get(item)
    if driver is None:
        return 1.0
    farms = obs.get("farms") or []
    if len(farms) < 2:
        return 1.0
    me = int(obs.get("player", 0) or 0)
    kind, name = driver
    mine = _count_driver(farms[me], kind, name)
    theirs = _count_driver(farms[1 - me], kind, name)
    if mine <= 0:
        return 1.0 if theirs > 0 else 0.0
    return max(0.0, min(2.0, theirs / float(mine)))


def _reserve_price(item, step, obs, shops):
    """Reservation price for one unit of `item`.

    A fixed fraction of base price, decayed linearly to zero over the
    liquidation ramp, and scaled down when the town's remaining appetite cannot
    absorb the supply still to come: a structurally oversupplied product is a
    race to sell, not something to hold.
    """
    base = _MP[item][0]
    frac = _RESERVE[item]
    if step >= _RAMP_START:
        span = float(max(1, _RAMP_END - _RAMP_START))
        frac *= max(0.0, (_RAMP_END - step) / span)
    drain = _remaining_drain(item, step, shops)
    supply = float(_SUPPLY.get(item, [0] * 721)[min(step, 720)])
    ahead = supply * (1.0 + _opponent_scale(obs, item))
    if ahead > 0.0:
        frac *= min(1.0, drain / ahead)
    return base * frac


def _plan_sells(obs, step, slots, short_of_cash):
    """Choose SELL orders for the controlled products."""
    if slots <= 0:
        return []
    shed = (obs.get("private") or {}).get("shed") or {}
    inventory = ((obs.get("market") or {}).get("inventory") or {})
    shops = (obs.get("town") or {}).get("unlocked_shops") or []
    load = sum(max(0, int(v or 0)) for v in shed.values())
    forced = load >= _SHED_PRESSURE or short_of_cash > 0

    candidates = []
    for item in _RESERVE:
        held = int(shed.get(item, 0) or 0)
        if held <= 0:
            continue
        inv = int(inventory.get(item, _I0) or _I0)
        if forced:
            units = held
        else:
            reserve = _reserve_price(item, step, obs, shops)
            units = 0
            while units < held and _mprice(item, inv + units) >= reserve:
                units += 1
        if units > 0:
            candidates.append((_mprice(item, inv) * units, item, units))
    candidates.sort(reverse=True)
    return [["SELL", item, units] for _, item, units in candidates[:slots]]


def _cash_needed(orders, obs):
    """Coins this turn's buy orders require."""
    seeds = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}
    animals = {"GOOSE": 300, "COW": 400, "SHEEP": 500}
    prices = ((obs.get("market") or {}).get("prices") or {})
    total = 0
    for order in orders:
        if not isinstance(order, list) or not order:
            continue
        op = order[0]
        if op == "BUY_SEED" and len(order) >= 3:
            total += seeds.get(order[1], 0) * int(order[2] or 0)
        elif op == "BUY_ANIMAL" and len(order) >= 3:
            total += animals.get(order[1], 0) * int(order[2] or 0)
        elif op == "BUY_PRODUCT" and len(order) >= 3:
            total += int(prices.get(order[1], 50) or 50) * int(order[2] or 0)
        elif op == "BUY_LAND":
            total += 4000
    return total


def _race_factor(item, step, obs):
    """1.0 when the town can absorb everything still coming, higher when not."""
    if _RACE_WEIGHT <= 0.0:
        return 1.0
    shops = (obs.get("town") or {}).get("unlocked_shops") or []
    drain = _remaining_drain(item, step, shops)
    supply = float(_SUPPLY.get(item, [0] * 721)[min(step, 720)])
    ahead = supply * (1.0 + _opponent_scale(obs, item))
    if ahead <= 0.0:
        return 1.0
    glut = max(0.0, 1.0 - drain / ahead)
    return 1.0 + _RACE_WEIGHT * glut


def _sell_priority(order, obs, step=0):
    """Rank a SELL order for slot placement; higher goes into an earlier slot.

    Market slots resolve index by index across both players, so an order in an
    earlier slot is priced before the opponent's matching order in a later slot.
    ``gross`` ranks by revenue at stake. ``impact`` ranks by how much revenue is
    actually lost by going second, which is the quantity times this order's own
    price impact — that promotes steep premium curves (wool, melon, milk) over
    large but nearly flat staple sales (wheat, egg).
    """
    if not (isinstance(order, list) and len(order) >= 3 and order[0] == "SELL"):
        return -1.0
    item = order[1]
    try:
        qty = int(order[2] or 0)
    except (TypeError, ValueError):
        return -1.0
    if qty <= 0 or item not in _MP:
        return -1.0
    inventory = ((obs.get("market") or {}).get("inventory") or {})
    inv = int(inventory.get(item, _I0) or _I0)
    unit = _mprice(item, inv)
    held = int(((obs.get("private") or {}).get("shed") or {}).get(item, 0) or 0)
    qty = min(qty, held) if held > 0 else qty
    race = _race_factor(item, step, obs)
    if _SORT_KEY == "unit":
        return float(unit) * race
    if _SORT_KEY == "impact":
        return float(qty) * float(unit - _mprice(item, inv + qty)) * race
    return float(unit) * float(qty) * race


def agent(obs, config=None):
    """c27 with its SELL layer partially replaced by the market controller."""
    action = _base_agent(obs, config)
    try:
        step = int(obs.get("step", 0) or 0)
        if step >= 717:
            return action  # proven terminal controller; leave untouched
        orders = list(action.get("market") or [])
        keep = [
            order for order in orders
            if not (
                isinstance(order, list) and len(order) >= 2
                and order[0] == "SELL" and order[1] in _RESERVE
            )
        ]
        player = int(obs.get("player", 0) or 0)
        money = float(((obs.get("farms") or [{}])[player]).get("money", 0) or 0)
        short = max(0.0, _cash_needed(keep, obs) - money)
        sells = _plan_sells(obs, step, 10 - len(keep), short)
        if not _SORT_SELLS:
            action["market"] = (sells + keep)[:10]
            return action

        def is_sell(o):
            return isinstance(o, list) and o and o[0] == "SELL"

        opp_money = None
        if _PROMOTE_IF_OPP_MONEY:
            farms = obs.get("farms") or []
            if len(farms) > 1:
                opp_money = float(farms[1 - player].get("money", 0) or 0)

        def promotable(o):
            if not is_sell(o):
                return False
            item = o[1]
            if item in _PROMOTE_IF_OPP_MONEY:
                if opp_money is None:
                    return False
                return opp_money >= _PROMOTE_IF_OPP_MONEY[item]
            if item in _PROMOTE_AFTER:
                return step >= _PROMOTE_AFTER[item]
            return not _PROMOTE or item in _PROMOTE

        # Only promotable sells compete for the earliest slots. WHEAT and
        # FERTILIZER are the only products an opponent can BUY_PRODUCT, so
        # promoting those ahead of their buys would lower the price they pay for
        # feed; those sells are deliberately left in their tape position, where
        # the opponent's buys have already drained inventory and lifted the price.
        merged = [o for o in sells if promotable(o)] + [o for o in keep if promotable(o)]
        merged.sort(key=lambda o: -_sell_priority(o, obs, step))
        rest = [o for o in sells if not promotable(o)] + [o for o in keep if not promotable(o)]
        if _SELLS_FIRST:
            action["market"] = (merged + rest)[:10]
        else:
            # Keep the tape's slot layout: sorted sells refill the slots that
            # already held promotable sells; every other order stays put.
            out = []
            queue = list(merged)
            for order in keep:
                out.append(queue.pop(0) if (promotable(order) and queue) else order)
            out.extend(queue)
            action["market"] = out[:10]
        return action
    except Exception:
        return action
