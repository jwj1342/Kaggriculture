"""Device-side potential function: rl/obs.py net_worth over EpisodeT tensors (B4c).

net_worth_t(ep, player) -> (B,) float64 on ep.device, equal -- as float64,
bit for bit -- to obs.net_worth(dict obs rebuilt from ep.snapshot(lane)) for
every lane. The gate is rl/tensor_env/test_b4c.py (i).

Why exact equality is achievable without any lookup tables
----------------------------------------------------------
Every asset term in obs.net_worth is an integer: land credit (LAND_PRICES
prefix sums), shed items at base price / animal cost, seeds at seed cost,
unit inventories at the same per-item value, standing plants at
seed cost + yield * crop base, placed animals at cost + yield * product base.
The reference accumulates them in a python float; the partial sums stay
far below 2^53 so every intermediate is exact and the summation order is
irrelevant. Here the total is formed in int64 and cast once to float64
(exact). The three float operations the reference then performs --
    money + 0.5 * min(money, 800.0) + decay * assets
with decay = min(1.0, max(0.0, (720.0 - t) / 120.0)), t = day * 24 + hour --
are IEEE-754 float64 add / mul, correctly rounded on CPU and CUDA alike, and
are issued in the same order and association: (money + 0.5*min) + decay*assets.
`decay` is a host python float (t is the batch-wide step count), so it is the
identical double the reference computes.

Money is ep.money (float64) untouched.
"""

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

import kg_rules as R                     # the price/cost tables obs.py reads

# --- pin the orderings the item-value vector bakes in ----------------------
assert ET.ITEMS == R.PRODUCTS + list(R.ANIMALS)          # shed / unit_inv axis
assert ET.CROP_NAMES == list(R.CROPS)                    # crop idx -> name
assert ET.ANIMAL_NAMES == list(R.ANIMALS)                # animal idx -> name
assert list(E.LAND_PRICES) == list(R.LAND_PRICES)
assert E.LAND_ORDER == ["NE", "SW", "SE"]                # quad_unlocked axis

# Per-item value: products (incl. FERTILIZER) at base price, animals at cost
# -- obs.net_worth's `if item in R.ANIMALS: cost else base price` for shed
# and inventories alike.
_ITEM_VALUE = ([R.MARKET_PARAMS[p]["base"] for p in R.PRODUCTS]
               + [R.ANIMALS[a]["cost"] for a in R.ANIMALS])
_SEED_COST = [R.CROPS[c]["seed"] for c in R.CROPS]
_CROP_BASE = [R.MARKET_PARAMS[c]["base"] for c in R.CROPS]
_ANIMAL_COST = [R.ANIMALS[a]["cost"] for a in R.ANIMALS]
_ANIMAL_PROD_BASE = [R.MARKET_PARAMS[R.ANIMALS[a]["product"]]["base"]
                     for a in R.ANIMALS]
# sum(LAND_PRICES[:k]) for k extra quadrants unlocked, k = 0..3
_LAND_CUM = [sum(R.LAND_PRICES[:k]) for k in range(len(R.LAND_PRICES) + 1)]


class _Tables:
    __slots__ = ("item_value", "seed_cost", "crop_base", "animal_cost",
                 "animal_prod_base", "land_cum", "slot_ar")


_CACHE = {}


def _tables(device, H):
    key = (str(device), H)
    t = _CACHE.get(key)
    if t is None:
        i64 = torch.int64
        t = _Tables()
        t.item_value = torch.tensor(_ITEM_VALUE, dtype=i64, device=device)
        t.seed_cost = torch.tensor(_SEED_COST, dtype=i64, device=device)
        t.crop_base = torch.tensor(_CROP_BASE, dtype=i64, device=device)
        t.animal_cost = torch.tensor(_ANIMAL_COST, dtype=i64, device=device)
        t.animal_prod_base = torch.tensor(_ANIMAL_PROD_BASE, dtype=i64, device=device)
        t.land_cum = torch.tensor(_LAND_CUM, dtype=i64, device=device)
        t.slot_ar = torch.arange(1 + H, dtype=i64, device=device)
        _CACHE[key] = t
    return t


def assets_t(ep, player):
    """Integer asset total (B,) int64: everything obs.net_worth credits at
    base prices before the end-game decay is applied."""
    B, H = ep.B, ep.H
    i64 = torch.int64
    t = _tables(ep.device, H)

    # land credit: number of extra quadrants unlocked -> prefix sum of prices
    n_extra = ep.quad_unlocked[:, player].to(i64).sum(-1)              # (B,)
    assets = t.land_cum[n_extra]

    # shed items (products at base, animals at cost); counts are >= 0
    assets = assets + (ep.shed[:, player].to(i64) * t.item_value).sum(-1)

    # seeds at seed cost
    assets = assets + (ep.seeds_t[:, player].to(i64) * t.seed_cost).sum(-1)

    # unit inventories: farmer slot 0 plus the first hands_n hand slots
    # (snapshot only lists 1 + hands_n inventories; slots beyond are dead)
    live = t.slot_ar.view(1, -1) <= ep.hands_n[:, player].to(i64).view(B, 1)  # (B,1+H)
    inv = ep.unit_inv[:, player].to(i64)                                # (B,1+H,12)
    inv = inv * live.unsqueeze(-1)
    assets = assets + (inv.sum(1) * t.item_value).sum(-1)

    # standing tiles
    kind = ep.kind[:, player].reshape(B, -1)
    plant = kind == ET.K_PLANT
    animal_idx = ep.animal[:, player].reshape(B, -1).to(i64)
    anim = animal_idx >= 0
    yu = ep.yield_units[:, player].reshape(B, -1).to(i64)
    crop_idx = ep.crop[:, player].reshape(B, -1).to(i64)
    plant_val = t.seed_cost[crop_idx] + yu * t.crop_base[crop_idx]
    anim_val = (t.animal_cost[animal_idx.clamp(min=0)]
                + yu * t.animal_prod_base[animal_idx.clamp(min=0)])
    assets = assets + torch.where(plant, plant_val, torch.zeros_like(plant_val)).sum(-1)
    assets = assets + torch.where(anim, anim_val, torch.zeros_like(anim_val)).sum(-1)
    return assets


def decay_at(ep):
    """The reference's end-game decay scalar for the batch's current step."""
    day = ep._step // ep.turns_per_day
    hour = ep._step % ep.turns_per_day
    t = day * 24 + hour
    return min(1.0, max(0.0, (720.0 - t) / 120.0))


def net_worth_t(ep, player):
    """obs.net_worth for every lane at `player`'s perspective: (B,) float64."""
    money = ep.money[:, player]                                          # f64
    assets = assets_t(ep, player).to(torch.float64)                      # exact
    decay = decay_at(ep)
    return money + 0.5 * torch.clamp(money, max=800.0) + decay * assets
