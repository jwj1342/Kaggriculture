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
cst, sel, sel0, anyt, isel = ET.cst, ET.sel, ET.sel0, ET.anyt, ET.isel  # B4b kernel idioms

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


def _f32_div_exact():
    """The five fractional board channels divide a small non-negative integer
    (yield <= 6, fert_left <= 3, consec <= 2, age <= 12) by 6/3/2/12. The
    reference does the division in float64 and casts to float32; _boards
    divides in float32 directly. Prove on the whole int8 domain (a superset
    of every reachable numerator) that the two agree bit for bit."""
    a = torch.arange(-128, 128, dtype=torch.float64)
    for d in (6.0, 3.0, 2.0, 12.0):
        ref = (a / d).to(torch.float32).view(torch.int32)
        got = (a.to(torch.float32) / d).view(torch.int32)
        if not torch.equal(ref, got):
            return False
    return True


_F32_DIV_EXACT = _f32_div_exact()
assert _F32_DIV_EXACT, "float32 channel division is not bit-exact on this build"


class _Tables:
    __slots__ = ("base", "i0", "big_t", "crop_first", "land_prices",
                 "fib", "shop_ar", "crop_first_i8", "seed_cost", "animal_cost",
                 "struct_coop", "deadline", "perm")


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
        t.crop_first_i8 = torch.tensor(ET.CROP_FIRST, dtype=torch.int8, device=device)
        t.seed_cost = torch.tensor(_SEED_COST, dtype=f64, device=device)
        t.animal_cost = torch.tensor(_ANIMAL_COST, dtype=f64, device=device)
        t.struct_coop = torch.tensor(_STRUCT_IS_COOP, dtype=torch.bool, device=device)
        t.deadline = torch.tensor(_PLANT_DEADLINE, dtype=torch.int64, device=device)
        t.perm = (torch.tensor([0, 1], device=device), torch.tensor([1, 0], device=device))
        _CACHE[key] = t
    return t


# ---------------------------------------------------------------------------
# board block: (B, P, C, N, N) float32, obs.py channel layout
# ---------------------------------------------------------------------------

def _boards(ep, player, out):
    """Own-farm-first channel blocks written into out (B, 2, C, N*N) float32.
    Mirrors actions.analyze's writes channel by channel; stale per-tile
    fields (a decayed plant's watered flag, an escaped animal's cared flag)
    are masked out exactly as the snapshot masks them by omitting the keys.

    B4b: comparisons against cached int8 constants; every channel is first
    an int8 plane (indicators, or the masked integer numerator of a
    fractional channel -- x >= 0 on every masked-in tile, so masked-out is
    +0.0 exactly as torch.where(mask, x / d, 0.0)) in ONE int8 buffer that
    is converted to float32 in a single pass; the five fractional channels
    are then divided in place in float32, which _F32_DIV_EXACT proves equal
    to the reference's float64-then-cast on the whole reachable domain."""
    B, n = ep.B, ep.N
    day = ep._step // ep.turns_per_day
    f32, i8, i64 = torch.float32, torch.int8, torch.int64
    NN = n * n
    perm = _tables(ep.device).perm[player]                   # own-first order

    def own_first(x):                                        # (B, P, ...) -> (B, 2, NN)
        return x.index_select(1, perm).view(B, 2, NN)

    kind = own_first(ep.kind)
    animal = own_first(ep.animal)
    c = lambda v: cst(kind, v)
    anim = animal >= c(0)                # only ever true on COOP/PASTURE
    plant = kind == c(ET.K_PLANT)
    m8 = plant.view(i8)
    a8 = anim.view(i8)

    buf = torch.empty((B, 2, C, NN), dtype=i8, device=ep.device)

    def put(k, x):
        buf[:, :, k].copy_(x.view(i8) if x.dtype == torch.bool else x)

    put(0, kind == c(ET.K_EMPTY))
    put(1, kind == c(ET.K_LOCKED))
    put(2, kind == c(ET.K_WEED))
    put(3, (kind == c(ET.K_COOP)) & ~anim)
    put(4, (kind == c(ET.K_PASTURE)) & ~anim)
    crop = own_first(ep.crop)
    for ci in range(len(CROP_LIST)):     # channel loop, not a lane loop
        put(5 + ci, plant & (crop == c(ci)))
    put(10, own_first(ep.yield_units) * (plant | anim).view(i8))          # / 6
    put(11, own_first(ep.watered) & plant)
    put(12, (own_first(ep.fert_until) - (day - 1)).clamp(min=0, max=3).to(i8) * m8)  # / 3
    put(13, own_first(ep.consec_unwatered).clamp(max=2) * m8)            # / 2
    put(14, (day - own_first(ep.planted_day)).clamp(max=12).to(i8) * m8)  # / 12
    for ai in range(len(ANIMAL_LIST)):
        put(15 + ai, animal == c(ai))
    put(18, own_first(ep.fed) & anim)
    put(19, own_first(ep.cared) & anim)
    put(20, own_first(ep.fert_avail) & anim)
    put(21, own_first(ep.consec_unfed).clamp(max=2) * a8)                # / 2
    buf[:, :, 22:24].zero_()

    out.copy_(buf)                                           # one int8 -> f32 pass
    # Fractional channels: divide in float64 and cast, exactly the reference's
    # arithmetic. A float32 in-place divide was bit-exact on CPU (proved over
    # the int8 domain at import) but CUDA's f32 division differs by 1 ulp at
    # 5/12 (measured: 0.4166667 vs 0.41666666) -- device libm is not the
    # oracle, the reference's double-then-cast is. Cost is negligible: five
    # (B,2,100) planes.
    for ch, d in ((10, 6.0), (12, 3.0), (13, 2.0), (14, 12.0), (21, 2.0)):
        out[:, :, ch].copy_(buf[:, :, ch].to(torch.float64).div_(d))

    fxy = ep.farmer_xy.index_select(1, perm).to(i64)
    fidx = fxy[..., 1] * n + fxy[..., 0]
    out[:, :, 22].scatter_(2, fidx.unsqueeze(-1), 1.0)
    # Hands: += 0.25 per hand on its tile. Counts are small and 0.25 is a
    # power of two, so every partial sum is exact and the scatter_add order
    # cannot matter. Invalid slots contribute +0.0 at flat index 0 (their
    # stale coordinates are still in range, the contribution is zero).
    hxy = ep.hands_xy.index_select(1, perm).to(i64)
    hidx = hxy[..., 1] * n + hxy[..., 0]
    valid = (torch.arange(ep.H, device=ep.device).view(1, 1, -1)
             < ep.hands_n.index_select(1, perm).to(i64).unsqueeze(-1))
    out[:, :, 23].scatter_add_(2, hidx, valid.to(f32) * 0.25)


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
    float32 on ep.device -- own farm block, opponent block, globals. Written
    straight into one buffer (no reorder / cat copies)."""
    B, n = ep.B, ep.N
    out = torch.empty((B, OBS_DIM), dtype=torch.float32, device=ep.device)
    _boards(ep, player, out[:, :2 * C * n * n].view(B, 2, C, n * n))
    out[:, 2 * C * n * n:].copy_(_globals(ep, player))       # f64 -> f32 cast
    return out


# ---------------------------------------------------------------------------
# legality masks: actions.farmer_mask / actions.market_mask semantics
# ---------------------------------------------------------------------------

def masks_t(ep, player):
    """((B, 23) bool, (B, 22) bool) on ep.device.

    B4b form: the ten "is there any tile such that ..." predicates are one
    (B, 10, 100) stack reduced once; comparisons run against cached int8
    constants; the per-crop / per-animal / per-product column blocks are
    broadcast ops instead of per-column loops. Same booleans, fewer kernels."""
    dev = ep.device
    B, n = ep.B, ep.N
    day = ep._step // ep.turns_per_day
    t = _tables(dev)
    f64, i64, i8 = torch.float64, torch.int64, torch.int8

    kind = ep.kind[:, player].reshape(B, n * n)
    c = lambda v: cst(kind, v)
    anim = ep.animal[:, player].reshape(B, n * n) >= c(0)
    plant = kind == c(ET.K_PLANT)
    yu_pos = ep.yield_units[:, player].reshape(B, n * n) > c(0)
    age8 = (day - ep.planted_day[:, player].reshape(B, n * n)).to(i8)
    cf8 = isel(t.crop_first_i8, ep.crop[:, player].reshape(B, n * n).int())
    fert_due = (ep.fert_until[:, player].reshape(B, n * n) - day).to(i8) < c(0)
    preds = torch.stack([
        (plant & yu_pos & (age8 >= cf8)) | (anim & yu_pos),      # harvest
        plant & ~ep.watered[:, player].reshape(B, n * n),        # unwatered
        plant & fert_due,                                        # unfert
        anim & ~ep.fed[:, player].reshape(B, n * n),             # unfed
        anim & ~ep.cared[:, player].reshape(B, n * n),           # uncared
        anim & ep.fert_avail[:, player].reshape(B, n * n),       # fert_ready
        kind == c(ET.K_WEED),                                    # weeds
        kind == c(ET.K_EMPTY),                                   # empties
        (kind == c(ET.K_COOP)) & ~anim,                          # coop_free
        (kind == c(ET.K_PASTURE)) & ~anim,                       # pasture_free
    ], dim=1)                                                    # (B, 10, 100)
    anyp = preds.view(i8).sum(-1, dtype=torch.int32) != 0        # (B, 10)
    (harvest, unwatered, unfert, unfed, uncared, fert_ready, weeds, empties,
     coop_free, pasture_free) = anyp.unbind(1)

    inv0 = ep.unit_inv[:, player, 0]                         # (B, 12) farmer carry
    shed = ep.shed[:, player]                                # (B, 12)
    have = (inv0 > 0) | (shed > 0)                           # (B, 12)
    has_wheat = have[:, ET.WHEAT_I]
    has_fert = have[:, ET.FERT_I]
    fx = ep.farmer_xy[:, player, 0]
    fy = ep.farmer_xy[:, player, 1]
    tr = torch.ones(B, dtype=torch.bool, device=dev)
    seeds = ep.seeds_t[:, player]                            # (B, 5)
    open_c = (day <= t.deadline)                             # (5,) host-day gate
    plant_cols = empties.unsqueeze(-1) & (seeds > 0) & open_c
    place_cols = (have[:, ET.N_MKT:]
                  & torch.where(t.struct_coop, coop_free.unsqueeze(-1),
                                pasture_free.unsqueeze(-1)))
    fm = torch.cat([
        torch.stack([
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
        ], dim=1),
        plant_cols,                          # PLANT_<crop>
        place_cols,                          # PLACE_<animal>
    ], dim=1)

    money = ep.money[:, player]              # float64; int comparisons are exact
    money_u = money.unsqueeze(-1)
    room = shed.to(i64).sum(-1) < R.SHED_CAPACITY
    n_extra = ep.quad_unlocked[:, player].to(i64).sum(-1)
    land_price = t.land_prices[n_extra.clamp(max=len(E.LAND_PRICES) - 1)]
    hires = ep.hires_today[:, player].to(i64).clamp(max=_FIB_MAX)
    mm = torch.cat([
        tr.unsqueeze(-1),                                    # NOOP
        shed[:, :ET.N_MKT] > 0,                              # SELL_<p>
        (money_u >= t.seed_cost) & open_c,                   # BUY_SEED_<c>
        torch.stack([
            room & (money >= (ep.mkt_price[:, 0].to(i64) * 5).to(f64)),
            room & (money >= ep.mkt_price[:, ET.FERT_I].to(f64)),
        ], dim=1),
        room.unsqueeze(-1) & (money_u >= t.animal_cost),     # BUY_<animal>
        torch.stack([
            (n_extra < len(E.LAND_PRICES)) & (money >= land_price),
            (ep.hands_n[:, player] < A.MAX_HANDS) & (money >= t.fib[hires]),
        ], dim=1),
    ], dim=1)
    # mechanics-dead endgame: liquidation day + products in the shed ->
    # SELL_<p> only (actions.market_mask's twin; gate test_b3)
    if int(day) >= R.LIQUIDATE_DAY:
        sellable = shed[:, :ET.N_MKT] > 0
        dead = torch.zeros_like(mm)
        dead[:, 1:1 + ET.N_MKT] = sellable
        mm = torch.where(sellable.any(-1, keepdim=True), dead, mm)
    return fm, mm
