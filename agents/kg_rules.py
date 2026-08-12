"""The game's rules, mirrored -- not our policy.

A transcription of `reference/engine/kaggriculture.py`: the crop and animal
tables, the exact price model, the shop map, what the town removes per step.
It holds **no strategy**, reads no `CONFIG`, and everything in it is pure or a
constant derived from one.

That separation is the point. The engine was already rebalanced once
mid-competition -- 1.32.6 halved town demand and made shop draws replace -- and
when it happens again this is the only file that changes. **Re-diff it against
the installed package after every upgrade;** the competition overview page
describes pre-1.32.6 balance and is not the ground truth.

Per-episode mutable state deliberately does *not* live here. `_MEM` is in
`_engine.py` beside the policy that owns it.
"""

import math

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
# The last day of a 30-day season. Liquidating on 28 gave up a whole day of
# farming for no gain -- 24 turns is enough to harvest and dump everything, and
# the sweep is monotone: day 29 wins 92.9%, 28 gets 90.2%, 27 gets 85.9%, 26
# gets 76.0%.
LIQUIDATE_DAY = 29
PRODUCT_OF = {a: d["product"] for a, d in ANIMALS.items()}
LAST_PLANT_DAY = {"WHEAT": 24, "CARROT": 25, "TOMATO": 19, "STRAWBERRY": 13, "MELON": 18}

WATER_MAX = {}
for _c, _d in CROPS.items():
    if not _d["ongoing"]:
        _w = _d["max_yield_day"] - (_d["max_yield_day"] + 1) // 2 + 1
        WATER_MAX[_c] = min(_d["max_yield"], 1 + _w)


# How many units it takes to drive each product from base to the $1 floor.
# Computed once, because the whole `paced` market atom turns on it: the depths
# differ by sixty times across the nine products and the right selling rate
# differs with them.
_TO_FLOOR = {}


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


for _p in PRODUCTS:
    _i0 = MARKET_PARAMS[_p]["I0"]
    _n = 0
    while _n < 4000 and market_price(_p, _i0 + _n) > 1:
        _n += 1
    _TO_FLOOR[_p] = _n


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
