"""IDs and lookup tables for the batched GPU engine."""

BOARD = 10
N_PLAYER = 2
# Policy / decode action heads. Checkpoints are 12-hand; do not change this.
HAND_CAP = 12


def _fib_prefix(n):
    """Official `_fib(0)=1, _fib(1)=1, _fib(2)=2, ...` for the first n hires."""
    a, b = 1, 1
    out = []
    for _ in range(n):
        out.append(a)
        a, b = b, a + b
    return out


# Official interpreter does not cap farm hands. Money runs out around hire 25
# (cost ≈ $75k). 32 slots is past that; step() skips empty slots so the extra
# does not cost a full N_UNIT loop on typical farms.
ENGINE_HAND_CAP = 32
N_UNIT = 1 + ENGINE_HAND_CAP  # farmer + engine hand slots
MAX_ORDERS = 10
SHED_CAP = 100
EPISODE_STEPS = 720
TURNS_PER_DAY = 24
SEASON_DAYS = 30
FEATURE_DIM = 75
N_TASK = 13
N_MODE = 4
DONE_STEP = 720
WHEAT_SLOT = 0
FERT_SLOT = 8
ANIMAL_SHED0 = 9
MAX_MARKET_UNITS = 1000  # official order qty is uncapped; shed holds ≤100

# FARM_TASKS aligned with rl.action_space
TASK_IDLE, TASK_WATER, TASK_HARVEST = 0, 1, 2
TASK_PLANT0 = 3  # + crop id 0..4
TASK_FEED, TASK_CARE, TASK_COLLECT, TASK_DIG, TASK_BUILD = 8, 9, 10, 11, 12
MODE_HOLD, MODE_METERED, MODE_DUMP, MODE_RESTOCK = 0, 1, 2, 3
STARTING_MONEY = 3000.0
WEED_CHANCE = 0.005
MAX_SHOPS = 8
SHOP_UNLOCK_EVERY = 3  # days
SHOP_SELL_EVERY = 4    # steps
CENTER_SELL_EVERY = 24
MARKET_I0 = 10000
PRICE_FLOOR = 1.0
# Official inventory can dip below 0 on BUY_PRODUCT; LUT covers that range.
PRICE_INV_LO = -5000
PRICE_INV_MAX = 30000  # lookup table for vectorized market quotes
PHI_SCALE = 1000.0
TERMINAL_BONUS = 15.0

CROPS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"]
ANIMALS = ["COW", "SHEEP", "GOOSE"]
PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]
N_CROP = 5
N_ANIMAL = 3
N_PRODUCT = 9
N_SHED = N_PRODUCT + N_ANIMAL  # products 0-8, animals 9-11

# tile.kind
K_EMPTY, K_LOCKED, K_WEED, K_PLANT, K_PASTURE, K_COOP = range(6)

# unit ops
(
    OP_PASS, OP_NORTH, OP_SOUTH, OP_EAST, OP_WEST,
    OP_WATER, OP_HARVEST, OP_PLANT, OP_FEED, OP_CARE,
    OP_COLLECT, OP_DIG, OP_BUILD_COOP, OP_BUILD_PASTURE,
    OP_DROP, OP_PICKUP, OP_PLACE, OP_FERTILIZE,
) = range(18)

MOVE_OP = {OP_NORTH: (0, -1), OP_SOUTH: (0, 1), OP_EAST: (1, 0), OP_WEST: (-1, 0)}

# market ops
M_NONE, M_HIRE, M_BUY_LAND, M_BUY_SEED, M_BUY_PRODUCT, M_BUY_ANIMAL, M_SELL = range(7)

# animal -> structure kind
ANIMAL_STRUCT = [K_PASTURE, K_PASTURE, K_COOP]  # cow, sheep, goose
ANIMAL_COST = [400, 500, 300]
ANIMAL_PRODUCT = [6, 7, 5]  # MILK, WOOL, EGG
ANIMAL_FIRST = [8, 6, 4]
ANIMAL_INTERVAL = [2, 3, 1]
ANIMAL_MAX_HELD = [6, 6, 4]
ANIMAL_SHED = [9, 10, 11]  # shed slots

SEED_COST = [10, 20, 50, 100, 80]
CROP_FIRST = [2, 2, 8, 10, 10]
CROP_MAX_YIELD_DAY = [4, 3, 8, 10, 12]
CROP_INTERVAL = [0, 0, 1, 2, 0]
CROP_MAX_YIELD = [6, 4, 4, 4, 6]
CROP_ONGOING = [0, 0, 1, 1, 0]
WATER_WINDOW_START = [(d + 1) // 2 for d in CROP_MAX_YIELD_DAY]

BASE_PRICE = [25, 35, 60, 120, 250, 50, 160, 200, 100]
LAND_PRICES = [1000, 2000, 4000]  # NE, SW, SE after NW
HIRE_FIB = _fib_prefix(ENGINE_HAND_CAP)

# market shape params per product
# func: 0 linear, 1 sq, 2 sqrt, 3 log, 4 log10
MKT_T = [400, 450, 200, 100, 300, 332, 122, 105, 200]
MKT_BELOW_F = [2, 3, 0, 2, 3, 0, 2, 3, 0]
MKT_BELOW_T = [0.80, 0.20, 0.40, 0.70, 0.20, 0.40, 0.60, 0.20, 0.40]
MKT_ABOVE_F = [3, 2, 2, 0, 1, 3, 0, 1, 0]
MKT_ABOVE_T = [0.20, 0.70, 0.60, 1.60, 3.60, 0.20, 1.60, 3.20, 0.40]

# shops in sorted-name order (matches official rng.choice(sorted(SHOPS)))
SHOP_NAMES = [
    "BAKERY", "BRUNCH_SPOT", "FARMERS_MARKET", "ICE_CREAM_SHOP",
    "PET_CAFE", "PIZZA_SHOP", "SMOOTHIE_SHOP", "YARN_STORE",
]
# consume[shop, product] units per shop tick
_SHOP_ITEMS = {
    "BAKERY": ["EGG", "WHEAT"],
    "BRUNCH_SPOT": ["EGG", "WHEAT", "STRAWBERRY"],
    "FARMERS_MARKET": ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY"],
    "ICE_CREAM_SHOP": ["STRAWBERRY", "MILK", "WHEAT"],
    "PET_CAFE": ["CARROT"],
    "PIZZA_SHOP": ["MILK", "TOMATO", "WHEAT"],
    "SMOOTHIE_SHOP": ["STRAWBERRY", "MILK"],
    "YARN_STORE": ["WOOL"],
}
SHOP_CONSUME = [[0] * N_PRODUCT for _ in SHOP_NAMES]
for _i, _name in enumerate(SHOP_NAMES):
    _items = _SHOP_ITEMS[_name]
    _mult = 2 if len(_items) == 1 else 1
    for _it in _items:
        SHOP_CONSUME[_i][PRODUCTS.index(_it)] = _mult

TOWN_CENTER = [1, 1, 1, 1, 1, 1, 1, 1, 0]  # all products except fertilizer

SHED_TILES = [(4, 4), (5, 4), (4, 5), (5, 5)]  # board=10, NWSE
SPAWN = (4, 4)  # first NW shed-access tile
