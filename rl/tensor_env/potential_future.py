"""Future-credit potential: Kilo's rl/potential.py (new-branch b53739f),
ported to EpisodeT tensors as an alternative shaping potential.

Where net_worth_t values what you HOLD (standing assets at base price),
this one values what the state is EXPECTED to deliver by the end of the
season: planting credits the expected remaining harvest immediately
(a melon seed lifts phi by ~$750 the moment it is planted), animals carry
their remaining production events, unfed/uncared animals are charged a
flight-risk penalty, weeds an opportunity cost, hands and land a
productivity value. The point is credit assignment: 240-turn causal chains
(plant melon -> harvest) become instant gradient.

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

# -- design constants (Kilo's, not engine values) ---------------------------
SHED_DISCOUNT = 0.9
SEED_RESIDUAL = 0.5
# PLANT_CREDIT / ANIMAL_CREDIT are the two flat haircuts that make CASH the
# highest-credit asset in phi (money enters at 1.0, see the `phi + ep.money`
# line below). A standing crop is worth half of the cash it converts into and
# an animal 0.4 of it, so "liquidate the inherited farm and sit on the money"
# is a phi improvement -- which is exactly the takeover behaviour 512c3fa
# measured (day 12: 0 seeds bought, 1 PLANT, 121 units sold, standing crops
# 38 -> 9 by day 27, and money AHEAD by 1,851 at day 14).
#
# The obvious objection is that 0.5 prices the risk that a crop dies. It does
# not: risk is already modelled separately and these sit on TOP of it --
# `expected` is the expected remaining harvest, (1 - stress) is the water
# risk, and the animal term subtracts UNFED_RISK / UNCARED_RISK as explicit
# penalties. So both are a second, unconditional discount.
#
# Exposed as --plant-credit / --animal-credit for the A/B (same pattern as
# --land-value). Defaults are Kilo's originals and the gates pin that path.
PLANT_CREDIT = 0.5
ANIMAL_CREDIT = 0.4
UNFED_RISK = 0.8
UNCARED_RISK = 0.3
WATER_STRESS = 0.15
WEED_COST = 25.0
HAND_VALUE = 40.0
LAND_VALUE = 300.0
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


def future_worth_t(ep, player, shed_at_market=False, land_value=LAND_VALUE,
                   plant_credit=PLANT_CREDIT,
                   animal_credit=ANIMAL_CREDIT, shed_animals=0.0):
    """(B,) float64 future-credit potential for one seat.

    shed_at_market: value shed PRODUCTS at min(current market price, base)
    instead of flat base -- removes the hoarding subsidy (selling below
    base was a negative reward at the moment of sale, and market prices
    sit far below base for anything the two farms actually produce at
    volume). Kilo's original formula is shed_at_market=False; the gate
    pins that path only."""
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
    plant_val = expected * L["crop_base"][crop] * plant_credit * (1.0 - stress)
    phi = (plant_val * is_plant.to(f64)).sum((-1, -2))

    # animals: held + remaining production events, minus neglect risk
    has_a = ep.animal[:, player] >= 0
    aidx = ep.animal[:, player].long().clamp(min=0)
    a_start = torch.maximum(torch.full_like(placed, day),
                            placed + L["a_first"][aidx])
    rem_a = torch.where(a_start > SEASON_DAYS, yu,
                        yu + 1.0 + (SEASON_DAYS - a_start) / L["a_int"][aidx])
    a_val = (rem_a * L["a_base"][aidx] * animal_credit
             - (~ep.fed[:, player]).to(f64) * L["a_cost"][aidx] * UNFED_RISK
             - (~ep.cared[:, player]).to(f64) * L["a_cost"][aidx] * UNCARED_RISK)
    phi = phi + (a_val * has_a.to(f64)).sum((-1, -2))

    phi = phi - WEED_COST * (kind == ET.K_WEED).to(f64).sum((-1, -2))
    phi = phi + HAND_VALUE * ep.hands_n[:, player].to(f64)
    # land_value: Kilo's flat $300/quadrant. The iter-160 census (RUNS.md
    # 2026-08-21) showed the economy land-gated with BUY_LAND's true value
    # (~5k of downstream crop credit per quadrant) invisible at 300 --
    # --land-value raises it for the A/B; the default keeps Kilo's path
    # byte-exact for the gate.
    phi = phi + land_value * ep.quad_unlocked[:, player].to(f64).sum(-1)
    if shed_at_market:
        eff9 = torch.minimum(ep.mkt_price.to(f64), L["base9"])   # (B, 9)
        shed9 = ep.shed[:, player, :len(_BASE9)].to(f64)
        phi = phi + (shed9 * eff9).sum(-1) * SHED_DISCOUNT
    else:
        phi = phi + (ep.shed[:, player].to(f64)
                     * L["base12"]).sum(-1) * SHED_DISCOUNT
    # shed_animals: the shed's three ANIMAL slots are weighted 0.0 in base12
    # (Kilo's loop ranges over PRODUCTS), so BUYING an animal converts cash --
    # phi weight 1.0 -- into an object phi prices at nothing. Measured on
    # herd1 (pure RL, 421 iterations, 2026-09-08): BUY_GOOSE/COW/SHEEP are
    # LEGAL on 27-28% of turns and the policy assigns them a conditional
    # probability of 3e-6 to 7e-6, four thousand times below uniform, while
    # BUY_LAND -- also a masked purchase -- gets 0.0127 and HIRE 0.112. That
    # is not missing opportunity, it is correct optimisation of a potential
    # that charges the first step of the only chain that decides ladder games:
    # across 546 real ladder episodes our win rate is 0.966 against opponents
    # ending with <=7 animals and 0.147 against those with 16+. PLACE_*, FEED
    # and CARE are then legal on 0.000% of turns, because nothing is ever
    # held. Pricing a shed animal at its PURCHASE COST makes the buy
    # phi-neutral rather than a loss -- it is not a hoarding subsidy (that bug
    # priced dead PRODUCT above market); placing is still strictly better,
    # since a placed animal earns rem_a * a_base * animal_credit on top.
    if shed_animals:
        n_p = len(_BASE9)
        shed_a = ep.shed[:, player, n_p:].to(f64)            # (B, 3)
        phi = phi + (shed_a * L["a_cost"]).sum(-1) * shed_animals
    phi = phi + (ep.seeds_t[:, player].to(f64) * L["seedc"]).sum(-1) * SEED_RESIDUAL
    phi = phi + ep.money[:, player]
    return phi
