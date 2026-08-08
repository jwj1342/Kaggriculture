"""Engine constants and the market model, mirrored from kaggriculture.py 1.32.6.

Kept standalone so the submission has no dependency on kaggle_environments
being importable at agent runtime. Re-diff against reference/engine/ after every
upgrade -- the balance changed once mid-competition already.
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
TURNS_PER_DAY = 24
SEASON_DAYS = 30
PRODUCT_OF = {a: d["product"] for a, d in ANIMALS.items()}

# Latest day a crop can be planted and still finish before the season ends.
LAST_PLANT_DAY = {"WHEAT": 24, "CARROT": 25, "TOMATO": 19, "STRAWBERRY": 13, "MELON": 18}

# Highest yield reachable on watering alone. Wheat and carrot cannot reach their
# nominal caps without fertilizer; melon reaches its cap of 6 on water by day 10.
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


def price(item, inv):
    """The engine's exact sell price at a given market inventory."""
    p = MARKET_PARAMS[item]
    base, i0, t = p["base"], p["I0"], p["T"]
    if inv < i0:
        amp = p["below_target"] * base / _shape(p["below_func"], t)
        return max(1, int(round(base + amp * _shape(p["below_func"], i0 - inv))))
    amp = p["above_target"] * base / _shape(p["above_func"], t)
    return max(1, int(round(base - amp * _shape(p["above_func"], inv - i0))))


def units_to_floor(item, inv, cap=4000):
    """How many more units can be sold before the price bottoms out at $1.

    This is the size of the remaining pool for a product the town does not
    consume. Melon's is ~158 from equilibrium; wool's ~59.
    """
    n = 0
    while n < cap and price(item, inv + n) > 1:
        n += 1
    return n


def revenue(item, inv, n):
    """Exact revenue from selling n units starting at this inventory."""
    return sum(price(item, inv + i) for i in range(n))


def town_rate(unlocked_shops):
    """Units per day the town removes from each product, given today's shops.

    Deterministic: every unlocked shop instance consumes one of each of its
    products every 4 turns (single-product shops take 2x), and the town centre
    takes one of every non-fertilizer product per day. Nothing consumes
    fertilizer, which is why its price only ever falls.
    """
    rate = {p: 0.0 for p in PRODUCTS}
    ticks = TURNS_PER_DAY // 4
    for shop in unlocked_shops or []:
        prods = SHOPS.get(shop, [])
        mult = 2 if len(prods) == 1 else 1
        for p in prods:
            rate[p] += ticks * mult
    for p in PRODUCTS:
        if p != "FERTILIZER":
            rate[p] += 1.0
    return rate


def fib(n):
    """Cost multiplier of the n-th hire of the day: 1, 1, 2, 3, 5, 8, 13, ..."""
    a, b = 1, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def payroll(n_hires):
    """Total cost of hiring n hands in one day."""
    return sum(fib(i) for i in range(n_hires))


def shed_tiles(board):
    h = board // 2
    return [(h - 1, h - 1), (h, h - 1), (h - 1, h), (h, h)]


def dist(ax, ay, bx, by):
    return abs(ax - bx) + abs(ay - by)


def step_toward(fx, fy, tx, ty):
    """Move on the longer axis first. Locked tiles are passable, so any monotone
    path is optimal."""
    if fx != tx and abs(fx - tx) >= abs(fy - ty):
        return "EAST" if tx > fx else "WEST"
    if fy != ty:
        return "SOUTH" if ty > fy else "NORTH"
    if fx != tx:
        return "EAST" if tx > fx else "WEST"
    return None
