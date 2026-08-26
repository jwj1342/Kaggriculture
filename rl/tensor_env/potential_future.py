"""Future-credit potential: Kilo's rl/potential.py (new-branch b53739f),
ported to EpisodeT tensors as an alternative shaping potential.

Where net_worth_t values what you HOLD (standing assets at base price),
this one values what the state is EXPECTED to deliver by the end of the
season: planting credits the expected remaining harvest immediately,
animals carry remaining production plus a herd-asset term, shed livestock
count at purchase-cost residual, empty housing is an asset, unfed/uncared
animals are charged a flight-risk penalty, weeds an opportunity cost,
hands and land a productivity value. Credits live in rl/potential.py
(plant 0.25, animal 0.9) so a day-0 cow outranks a melon plant. The point
is credit assignment: 240-turn causal chains become instant gradient.

Semantics are ported expression for expression from Kilo's dict version --
including its deliberate simplifications (one-shot crops count max_yield
flat; the opponent term in his relative form zeroed the hidden shed; land
at $300/quadrant, not the purchase price). Two departures, both documented:
we read the true tensor state on both seats (training-side reward may see
everything; his version ran inside the obs-limited agent), and the
relative form is exposed as --opp-lambda instead of being hard-wired --
per-step full zero-sum shaping is this repo's archived negative result.

Every game constant is asserted against kg_rules at import; the gate
(test_trl.py) replays his dict formula per lane against the tensor result
on mid-game states.
"""

import os
import sys

import torch

try:
    from . import engine_t as ET
except ImportError:  # flat imports (verify_t.py pattern)
    import engine_t as ET

_RL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RL not in sys.path:
    sys.path.insert(0, _RL)

import kg_rules as R

try:
    from potential import (
        ANIMAL_CREDIT,
        HAND_VALUE,
        HERD_ASSET,
        HOUSING_VALUE,
        LAND_VALUE,
        PLANT_CREDIT,
        SEED_RESIDUAL,
        SHED_ANIMAL_CREDIT,
        SHED_DISCOUNT,
        UNCARED_RISK,
        UNFED_RISK,
        WATER_STRESS,
        WEED_COST,
    )
except ImportError:
    from rl.potential import (
        ANIMAL_CREDIT,
        HAND_VALUE,
        HERD_ASSET,
        HOUSING_VALUE,
        LAND_VALUE,
        PLANT_CREDIT,
        SEED_RESIDUAL,
        SHED_ANIMAL_CREDIT,
        SHED_DISCOUNT,
        UNCARED_RISK,
        UNFED_RISK,
        WATER_STRESS,
        WEED_COST,
    )

SEASON_DAYS = 30

# -- engine constants, pinned against kg_rules ------------------------------
assert ET.CROP_NAMES == list(R.CROPS) and ET.ANIMAL_NAMES == list(R.ANIMALS)
assert ET.PRODUCTS == R.PRODUCTS
_CROPS = [R.CROPS[c] for c in ET.CROP_NAMES]
_ANIMALS = [R.ANIMALS[a] for a in ET.ANIMAL_NAMES]
_BASE9 = [float(R.MARKET_PARAMS[p]["base"]) for p in ET.PRODUCTS]
_SEEDC = [float(c["seed"]) for c in _CROPS]
_CROP_BASE = [float(R.MARKET_PARAMS[c]["base"]) for c in ET.CROP_NAMES]
_MAXY = [float(c["max_yield"]) for c in _CROPS]
_ONGOING = [bool(c.get("ongoing")) for c in _CROPS]
_INTERVAL = [max(1.0, float(c.get("interval") or 1)) for c in _CROPS]
_FIRSTY = [float(c["first_yield_day"]) for c in _CROPS]
_A_COST = [float(a["cost"]) for a in _ANIMALS]
_A_BASE = [float(R.MARKET_PARAMS[a["product"]]["base"]) for a in _ANIMALS]
_A_INT = [max(1.0, float(a.get("interval") or 1)) for a in _ANIMALS]
_A_FIRST = [float(a["first_yield_day"]) for a in _ANIMALS]

_LUTS = {}


def _luts(device):
    key = str(device)
    if key not in _LUTS:
        f64 = torch.float64
        t = lambda v: torch.tensor(v, dtype=f64, device=device)
        _LUTS[key] = {
            "base9": t(_BASE9), "seedc": t(_SEEDC), "crop_base": t(_CROP_BASE),
            "maxy": t(_MAXY), "interval": t(_INTERVAL), "firsty": t(_FIRSTY),
            "ongoing": torch.tensor(_ONGOING, device=device),
            "a_cost": t(_A_COST), "a_base": t(_A_BASE),
            "a_int": t(_A_INT), "a_first": t(_A_FIRST),
            # shed axis is 9 products + 3 animals; the formula values only
            # the products (Kilo's loop ranges over PRODUCTS)
            "base12": t(_BASE9 + [0.0] * (len(ET.ITEMS) - len(_BASE9))),
        }
    return _LUTS[key]


def future_worth_t(ep, player):
    """(B,) float64 future-credit potential for one seat."""
    L = _luts(ep.device)
    f64 = torch.float64
    day = float(ep._step // ep.turns_per_day)

    kind = ep.kind[:, player].long()
    crop = ep.crop[:, player].long()
    yu = ep.yield_units[:, player].to(f64)
    planted = ep.planted_day[:, player].to(f64)
    placed = ep.placed_day[:, player].to(f64)
    watered = ep.watered[:, player]
    stress = ((~watered) & (ep.consec_unwatered[:, player] >= 1)).to(f64) * WATER_STRESS

    # plants: expected remaining harvest, credited now
    is_plant = kind == ET.K_PLANT
    maxy = L["maxy"][crop]
    interval = L["interval"][crop]
    first = L["firsty"][crop]
    start = torch.maximum(torch.full_like(planted, day), planted + first)
    rem_events = 1.0 + (SEASON_DAYS - start) / interval
    dsf = day - planted - first
    produced = torch.minimum(
        torch.div(dsf, interval, rounding_mode="floor") + 1.0, maxy)
    produced = torch.where(dsf >= 0, produced, torch.zeros_like(produced))
    rem_cap = torch.clamp(maxy - produced, min=0.0)
    exp_ongoing = torch.where(start > SEASON_DAYS, yu,
                              yu + torch.minimum(rem_cap, rem_events))
    expected = torch.where(L["ongoing"][crop], exp_ongoing, maxy)
    plant_val = expected * L["crop_base"][crop] * PLANT_CREDIT * (1.0 - stress)
    phi = (plant_val * is_plant.to(f64)).sum((-1, -2))

    # animals: held + remaining production events, minus neglect risk
    has_a = ep.animal[:, player] >= 0
    aidx = ep.animal[:, player].long().clamp(min=0)
    a_start = torch.maximum(torch.full_like(placed, day),
                            placed + L["a_first"][aidx])
    rem_a = torch.where(a_start > SEASON_DAYS, yu,
                        yu + 1.0 + (SEASON_DAYS - a_start) / L["a_int"][aidx])
    a_val = (rem_a * L["a_base"][aidx] * ANIMAL_CREDIT + HERD_ASSET
             - (~ep.fed[:, player]).to(f64) * L["a_cost"][aidx] * UNFED_RISK
             - (~ep.cared[:, player]).to(f64) * L["a_cost"][aidx] * UNCARED_RISK)
    phi = phi + (a_val * has_a.to(f64)).sum((-1, -2))

    empty_h = ((kind == ET.K_PASTURE) | (kind == ET.K_COOP)) & (ep.animal[:, player] < 0)
    phi = phi + HOUSING_VALUE * empty_h.to(f64).sum((-1, -2))

    phi = phi - WEED_COST * (kind == ET.K_WEED).to(f64).sum((-1, -2))
    phi = phi + HAND_VALUE * ep.hands_n[:, player].to(f64)
    phi = phi + LAND_VALUE * ep.quad_unlocked[:, player].to(f64).sum(-1)
    phi = phi + (ep.shed[:, player].to(f64) * L["base12"]).sum(-1) * SHED_DISCOUNT
    n_prod = len(ET.PRODUCTS)
    waiting = ep.shed[:, player, n_prod:n_prod + len(ET.ANIMAL_NAMES)].to(f64)
    phi = phi + (waiting * L["a_cost"] * SHED_ANIMAL_CREDIT).sum(-1)
    phi = phi + (ep.seeds_t[:, player].to(f64) * L["seedc"]).sum(-1) * SEED_RESIDUAL
    phi = phi + ep.money[:, player]
    return phi
