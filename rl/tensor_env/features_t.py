"""Device-side featurization + legality masks from EpisodeT tensor state (B3, D5).

obs.encode / actions.farmer_mask / actions.market_mask recomputed as tensor
ops over engine_t.EpisodeT's state; per lane bit-identical to the CPU
reference path applied to the dict rebuilt from ep.snapshot(lane). The gate
is rl/tensor_env/test_b3.py (pattern of test_fused.py: exact equality at
every step of full episodes).

Bit-equality strategy
---------------------
* Indicator channels and mask booleans are exact by construction.
* Every fractional feature in the CPU path is "python double arithmetic on
  integer state, stored into a float32 array". IEEE-754 float64 add / sub /
  mul / div are correctly rounded on CPU and CUDA alike, and torch's
  float64 -> float32 cast is the same round-to-nearest-even as numpy's
  store, so computing the identical expression in float64 tensors and
  casting once is bit-identical to the reference -- no lookup tables needed.
* HOST-COMPUTED exceptions (documented per the B3 brief): global feature
  slots 2 and 3 -- math.log1p(max(0.0, money)) / 12.0 for each player --
  go through libm's log1p, which torch does not reproduce bit-for-bit
  (SLEEF on CPU, CUDA libm on GPU). They are computed on the host with
  math.log1p from the exact python floats pulled off ep.money and written
  into the feature matrix. This is the only per-lane host work here.
* HIRE affordability gathers fib(hires_today) from a float64 table, exact
  for every index <= 78 (fib(78) < 2^53); the index is clamped there, which
  cannot flip the comparison -- fib(78) ~ 8.9e15 exceeds any reachable
  money by eight orders of magnitude, so the mask is False either way.

Layout contracts are asserted against rl/actions.py + rl/obs.py at import;
this module must never restate a constant those two own without an assert.

No per-lane python loops anywhere below (host scalars such as day and the
two documented log1p slots excepted).
"""

import math
import os
import sys

import torch

try:
    from . import engine_np as E
    from . import engine_t as ET
except ImportError:                      # flat imports (verify_t.py pattern)
    import engine_np as E
    import engine_t as ET

_RL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RL not in sys.path:
    sys.path.insert(0, _RL)

import actions as A                      # semantics source for the masks
import obs as O                          # layout source for encode
import kg_rules as R                     # actions' import put agents/ on path
from kg_rules import _fib

N = 10
C = O.C                                  # 24 board channels
G = O.G                                  # 67 global features
OBS_DIM = O.OBS_DIM                      # 2*C*N*N + G = 4867
N_FARMER = A.N_FARMER                    # 23
N_MARKET = A.N_MARKET                    # 22

CROP_LIST = A.CROP_LIST
ANIMAL_LIST = A.ANIMAL_LIST
PRODUCT_LIST = A.PRODUCT_LIST

# --- pin every ordering this module bakes into tensor indices -------------
assert OBS_DIM == 2 * C * N * N + G
assert CROP_LIST == ET.CROP_NAMES and ANIMAL_LIST == ET.ANIMAL_NAMES
assert PRODUCT_LIST == ET.PRODUCTS and O.SHOP_LIST == ET.SHOP_SORTED
assert ET.ITEMS == PRODUCT_LIST + ANIMAL_LIST
assert PRODUCT_LIST[0] == "WHEAT" and ET.FERT_I == 8      # market col 15/16
assert E.LAND_ORDER == O._QUADS == ["NE", "SW", "SE"]
assert A.FARMER_ACTIONS[:15] == [
    "PASS", "MOVE_N", "MOVE_S", "MOVE_E", "MOVE_W",
    "WATER", "HARVEST", "FEED", "CARE", "COLLECT_FERT", "FERTILIZE",
    "DIG_WEED", "BUILD_COOP", "BUILD_PASTURE", "DROP"]
assert A.FARMER_ACTIONS[15:20] == [f"PLANT_{c}" for c in CROP_LIST]
assert A.FARMER_ACTIONS[20:23] == [f"PLACE_{a}" for a in ANIMAL_LIST]
assert A.MARKET_ACTIONS[0] == "NOOP"
assert A.MARKET_ACTIONS[1:10] == [f"SELL_{p}" for p in PRODUCT_LIST]
assert A.MARKET_ACTIONS[10:15] == [f"BUY_SEED_{c}" for c in CROP_LIST]
assert A.MARKET_ACTIONS[15:22] == (
    ["BUY_WHEAT", "BUY_FERT"] + [f"BUY_{a}" for a in ANIMAL_LIST]
    + ["BUY_LAND", "HIRE"])

_PLANT_DEADLINE = [A.PLANT_DEADLINE[c] for c in CROP_LIST]
_SEED_COST = [R.CROPS[c]["seed"] for c in CROP_LIST]
_ANIMAL_COST = [R.ANIMALS[a]["cost"] for a in ANIMAL_LIST]
_STRUCT_IS_COOP = [R.ANIMALS[a]["structure"] == "COOP" for a in ANIMAL_LIST]
_FIB_MAX = 78                            # last n with fib(n) exact in float64


class _Tables:
    __slots__ = ("base", "i0", "big_t", "crop_first", "land_prices",
                 "fib", "shop_ar")


_CACHE = {}


def _tables(device):
    key = str(device)
    t = _CACHE.get(key)
    if t is None:
        f64 = torch.float64
        t = _Tables()
        t.base = torch.tensor([R.MARKET_PARAMS[p]["base"] for p in PRODUCT_LIST],
                              dtype=f64, device=device)
        t.i0 = torch.tensor([R.MARKET_PARAMS[p]["I0"] for p in PRODUCT_LIST],
                            dtype=f64, device=device)
        t.big_t = torch.tensor([R.MARKET_PARAMS[p]["T"] for p in PRODUCT_LIST],
                               dtype=f64, device=device)
        t.crop_first = torch.tensor(ET.CROP_FIRST, dtype=torch.int64, device=device)
        t.land_prices = torch.tensor(E.LAND_PRICES, dtype=f64, device=device)
        t.fib = torch.tensor([float(_fib(i)) for i in range(_FIB_MAX + 1)],
                             dtype=f64, device=device)
        t.shop_ar = torch.arange(len(ET.SHOP_SORTED), device=device)
        _CACHE[key] = t
    return t


# ---------------------------------------------------------------------------
# board block: (B, P, C, N, N) float32, obs.py channel layout
# ---------------------------------------------------------------------------

def _boards(ep):
    """Both farms' channel blocks, player-agnostic (encode_t reorders to
    own-farm-first). Mirrors actions.analyze's writes channel by channel;
    stale per-tile fields (a decayed plant's watered flag, an escaped
    animal's cared flag) are masked out exactly as the snapshot masks them
    by omitting the keys."""
    dev = ep.device
    B, P, n = ep.B, ep.NUM_PLAYERS, ep.N
    day = ep._step // ep.turns_per_day
    f32, f64, i64 = torch.float32, torch.float64, torch.int64

    kind = ep.kind
    anim = ep.animal >= 0                # only ever true on COOP/PASTURE
    plant = kind == ET.K_PLANT

    ch = torch.zeros((B, P, C, n, n), dtype=f32, device=dev)
    ch[:, :, 0] = (kind == ET.K_EMPTY).to(f32)
    ch[:, :, 1] = (kind == ET.K_LOCKED).to(f32)
    ch[:, :, 2] = (kind == ET.K_WEED).to(f32)
    ch[:, :, 3] = ((kind == ET.K_COOP) & ~anim).to(f32)
    ch[:, :, 4] = ((kind == ET.K_PASTURE) & ~anim).to(f32)
    for ci in range(len(CROP_LIST)):     # channel loop, not a lane loop
        ch[:, :, 5 + ci] = (plant & (ep.crop == ci)).to(f32)

    yu = ep.yield_units.to(f64)
    ch[:, :, 10] = torch.where(plant | anim, yu / 6.0, 0.0).to(f32)
    ch[:, :, 11] = (ep.watered & plant).to(f32)
    fert_left = (ep.fert_until.to(i64) - day + 1).clamp(min=0, max=3)
    ch[:, :, 12] = torch.where(plant, fert_left.to(f64) / 3.0, 0.0).to(f32)
    cuw = ep.consec_unwatered.to(i64).clamp(max=2)
    ch[:, :, 13] = torch.where(plant, cuw.to(f64) / 2.0, 0.0).to(f32)
    age = (day - ep.planted_day.to(i64)).clamp(max=12)
    ch[:, :, 14] = torch.where(plant, age.to(f64) / 12.0, 0.0).to(f32)

    for ai in range(len(ANIMAL_LIST)):
        ch[:, :, 15 + ai] = (ep.animal == ai).to(f32)
    ch[:, :, 18] = (ep.fed & anim).to(f32)
    ch[:, :, 19] = (ep.cared & anim).to(f32)
    ch[:, :, 20] = (ep.fert_avail & anim).to(f32)
    cuf = ep.consec_unfed.to(i64).clamp(max=2)
    ch[:, :, 21] = torch.where(anim, cuf.to(f64) / 2.0, 0.0).to(f32)

    flat = ch.view(B, P, C, n * n)
    fidx = ep.farmer_xy[:, :, 1].to(i64) * n + ep.farmer_xy[:, :, 0].to(i64)
    flat[:, :, 22].scatter_(2, fidx.unsqueeze(-1), 1.0)
    # Hands: += 0.25 per hand on its tile. Counts are small and 0.25 is a
    # power of two, so every partial sum is exact and the scatter_add order
    # cannot matter. Invalid slots contribute +0.0 at flat index 0 (their
    # stale coordinates are still in range, the contribution is zero).
    hidx = ep.hands_xy[:, :, :, 1].to(i64) * n + ep.hands_xy[:, :, :, 0].to(i64)
    valid = (torch.arange(ep.H, device=dev).view(1, 1, -1)
             < ep.hands_n.to(i64).unsqueeze(-1))
    flat[:, :, 23].scatter_add_(2, hidx, valid.to(f32) * 0.25)
    return ch


# ---------------------------------------------------------------------------
# global features: (B, G) float64 -> float32, obs._global_features order
# ---------------------------------------------------------------------------

def _globals(ep, player):
    dev = ep.device
    B = ep.B
    f64, i64 = torch.float64, torch.int64
    day = ep._step // ep.turns_per_day
    hour = ep._step % ep.turns_per_day
    opp = 1 - player
    t = _tables(dev)

    g = torch.empty((B, G), dtype=f64, device=dev)
    g[:, 0] = day / 30.0
    g[:, 1] = hour / 24.0
    # Slots 2/3: log1p of money -- host-computed (module docstring).
    money = ep.money.cpu().tolist()
    g[:, 2] = torch.tensor([math.log1p(max(0.0, m[player])) / 12.0
                            for m in money], dtype=f64, device=dev)
    g[:, 3] = torch.tensor([math.log1p(max(0.0, m[opp])) / 12.0
                            for m in money], dtype=f64, device=dev)
    g[:, 4] = ep.hands_n[:, player].to(f64) / 10.0
    g[:, 5] = ep.hands_n[:, opp].to(f64) / 10.0
    g[:, 6] = ep.hires_today[:, player].to(f64) / 8.0
    shed = ep.shed[:, player].to(i64)                        # (B, 12)
    g[:, 7] = shed.sum(-1).to(f64) / R.SHED_CAPACITY
    g[:, 8:17] = ep.mkt_price.to(f64) / t.base / 2.0
    g[:, 17:26] = (((t.i0 - ep.mkt_inv.to(f64)) / t.big_t)
                   .clamp(min=-3.0, max=3.0) / 3.0)
    g[:, 26:35] = shed[:, :9].clamp(max=60).to(f64) / 60.0
    g[:, 35:38] = shed[:, 9:].clamp(max=4).to(f64) / 4.0
    g[:, 38:43] = ep.seeds_t[:, player].to(i64).clamp(max=20).to(f64) / 20.0
    g[:, 43:52] = (ep.unit_inv[:, player, 0, :9].to(i64).clamp(max=20)
                   .to(f64) / 20.0)
    g[:, 52:55] = ep.quad_unlocked[:, player].to(f64)
    g[:, 55:58] = ep.quad_unlocked[:, opp].to(f64)
    cnt = (ep.shops_seq.unsqueeze(-1) == t.shop_ar).sum(1)   # (B, 8)
    g[:, 58:66] = cnt.to(f64) / 4.0
    g[:, 66] = (ep.shops_seq >= 0).sum(-1).to(f64) / 8.0
    return g


def encode_t(ep, player):
    """obs.encode for every lane at `player`'s perspective: (B, OBS_DIM)
    float32 on ep.device -- own farm block, opponent block, globals."""
    boards = _boards(ep)[:, [player, 1 - player]]            # own-first copy
    g = _globals(ep, player).to(torch.float32)
    return torch.cat([boards.reshape(ep.B, -1), g], dim=1)


# ---------------------------------------------------------------------------
# legality masks: actions.farmer_mask / actions.market_mask semantics
# ---------------------------------------------------------------------------

def masks_t(ep, player):
    """((B, 23) bool, (B, 22) bool) on ep.device."""
    dev = ep.device
    B, n = ep.B, ep.N
    day = ep._step // ep.turns_per_day
    t = _tables(dev)
    f64, i64 = torch.float64, torch.int64

    kind = ep.kind[:, player]
    anim = ep.animal[:, player] >= 0
    plant = kind == ET.K_PLANT
    yu_pos = ep.yield_units[:, player] > 0

    def anyt(m):
        return m.view(B, -1).any(-1)

    crop_first = t.crop_first[ep.crop[:, player].to(i64)]
    age = day - ep.planted_day[:, player].to(i64)
    harvest = anyt((plant & yu_pos & (age >= crop_first)) | (anim & yu_pos))
    unwatered = anyt(plant & ~ep.watered[:, player])
    unfert = anyt(plant & (ep.fert_until[:, player].to(i64) < day))
    unfed = anyt(anim & ~ep.fed[:, player])
    uncared = anyt(anim & ~ep.cared[:, player])
    fert_ready = anyt(anim & ep.fert_avail[:, player])
    weeds = anyt(kind == ET.K_WEED)
    empties = anyt(kind == ET.K_EMPTY)
    coop_free = anyt((kind == ET.K_COOP) & ~anim)
    pasture_free = anyt((kind == ET.K_PASTURE) & ~anim)

    inv0 = ep.unit_inv[:, player, 0]                         # farmer carry
    shed = ep.shed[:, player]
    has_wheat = (inv0[:, ET.WHEAT_I] > 0) | (shed[:, ET.WHEAT_I] > 0)
    has_fert = (inv0[:, ET.FERT_I] > 0) | (shed[:, ET.FERT_I] > 0)
    fx = ep.farmer_xy[:, player, 0].to(i64)
    fy = ep.farmer_xy[:, player, 1].to(i64)
    tr = torch.ones(B, dtype=torch.bool, device=dev)
    fl = torch.zeros(B, dtype=torch.bool, device=dev)

    cols = [
        tr,                              # PASS
        fy > 0, fy < n - 1, fx < n - 1, fx > 0,
        unwatered,                       # WATER
        harvest,                         # HARVEST
        unfed & has_wheat,               # FEED
        uncared,                         # CARE
        fert_ready,                      # COLLECT_FERT
        unfert & has_fert,               # FERTILIZE
        weeds,                           # DIG_WEED
        empties,                         # BUILD_COOP
        empties,                         # BUILD_PASTURE
        (inv0 > 0).any(-1),              # DROP
    ]
    seeds = ep.seeds_t[:, player]
    for ci in range(len(CROP_LIST)):     # PLANT_<crop>: deadline is host-side
        cols.append(empties & (seeds[:, ci] > 0)
                    if day <= _PLANT_DEADLINE[ci] else fl)
    for ai in range(len(ANIMAL_LIST)):   # PLACE_<animal>
        have = (inv0[:, ET.N_MKT + ai] > 0) | (shed[:, ET.N_MKT + ai] > 0)
        cols.append(have & (coop_free if _STRUCT_IS_COOP[ai] else pasture_free))
    fm = torch.stack(cols, dim=1)

    money = ep.money[:, player]          # float64; int comparisons are exact
    mcols = [tr]                         # NOOP
    for pi in range(ET.N_MKT):           # SELL_<p>
        mcols.append(shed[:, pi] > 0)
    for ci in range(len(CROP_LIST)):     # BUY_SEED_<c>
        mcols.append((money >= _SEED_COST[ci])
                     if day <= _PLANT_DEADLINE[ci] else fl)
    room = shed.to(i64).sum(-1) < R.SHED_CAPACITY
    mcols.append(room & (money >= (ep.mkt_price[:, 0].to(i64) * 5).to(f64)))
    mcols.append(room & (money >= ep.mkt_price[:, ET.FERT_I].to(f64)))
    for ai in range(len(ANIMAL_LIST)):   # BUY_<animal>
        mcols.append(room & (money >= _ANIMAL_COST[ai]))
    n_extra = ep.quad_unlocked[:, player].to(i64).sum(-1)
    land_price = t.land_prices[n_extra.clamp(max=len(E.LAND_PRICES) - 1)]
    mcols.append((n_extra < len(E.LAND_PRICES)) & (money >= land_price))
    hires = ep.hires_today[:, player].to(i64).clamp(max=_FIB_MAX)
    mcols.append((ep.hands_n[:, player] < A.MAX_HANDS) & (money >= t.fib[hires]))
    mm = torch.stack(mcols, dim=1)
    return fm, mm
