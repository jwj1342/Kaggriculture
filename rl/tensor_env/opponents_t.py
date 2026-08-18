"""B4a: tensor-state opponents. First member: the reference starter agent.

The reference starter (reference/engine/kaggriculture.py) never moves: it
sells carrots, keeps one carrot seed bought, and plants/waters/harvests the
single tile under its feet. Its whole decision reads ~7 scalars per lane, so
we gather them straight off the engine tensors — no snapshot rebuild (the
python path costs ~ms/lane; this costs one (B,) gather set).

`starter_actions(ep, player)` returns per-lane raw action dicts, gate-checked
byte-identical to `reference starter_agent(snapshot_obs)` in test_b4a.py.
The dict form keeps step_raw compatibility; fusing into the internal op path
is B4b's kernel work, not a correctness question.
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_RL = os.path.dirname(_HERE)
for _p in (_HERE, _RL):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import torch

import actions as A
import kg_rules as R

_CROPS = list(R.CROPS)
_PRODUCTS_I = R.PRODUCTS + list(R.ANIMALS)   # engine_t shed axis (I=12)
CARROT_SEED_IDX = _CROPS.index("CARROT")
CARROT_PROD_IDX = _PRODUCTS_I.index("CARROT")
_CARROT_SEED_COST = R.CROPS["CARROT"]["seed"]
_CARROT_MAX_YIELD_DAY = R.CROPS["CARROT"]["max_yield_day"]
_KIND_EMPTY, _KIND_PLANT = 0, 5


def starter_actions(ep, player):
    """Reference starter decisions for every lane, from tensor state."""
    B = ep.money.shape[0]
    day = ep._step // ep.turns_per_day

    fx = ep.farmer_xy[:, player, 0].long()
    fy = ep.farmer_xy[:, player, 1].long()
    lanes = range(B)
    flat = (fy * 10 + fx)

    def at(t):
        return t[:, player].reshape(B, -1).gather(1, flat.view(B, 1)).view(B)

    kind = at(ep.kind).cpu().numpy()
    crop = at(ep.crop).cpu().numpy()
    planted = at(ep.planted_day).cpu().numpy()
    watered = at(ep.watered).cpu().numpy()
    seeds_c = ep.seeds_t[:, player, CARROT_SEED_IDX].cpu().numpy()
    shed_c = ep.shed[:, player, CARROT_PROD_IDX].cpu().numpy()
    money = ep.money[:, player].cpu().numpy()

    out = []
    for i in lanes:
        market = []
        if shed_c[i] > 0:
            market.append(["SELL", "CARROT", int(shed_c[i])])
        if seeds_c[i] == 0 and money[i] >= _CARROT_SEED_COST:
            market.append(["BUY_SEED", "CARROT", 1])
        farmer = ["PASS"]
        if kind[i] == _KIND_EMPTY and seeds_c[i] > 0:
            farmer = ["PLANT", "CARROT"]
        elif kind[i] == _KIND_PLANT and _CROPS[crop[i]] == "CARROT":
            if day - int(planted[i]) >= _CARROT_MAX_YIELD_DAY:
                farmer = ["HARVEST"]
            elif not bool(watered[i]):
                farmer = ["WATER"]
        out.append({"farmer": farmer, "hands": [], "market": market})
    return out


# ---------------------------------------------------------------------------
# B4c: the same decisions as macro-head indices, for engine_t_idx.step_idx
# ---------------------------------------------------------------------------
#
# step_idx takes (B, 2) head indices for BOTH seats, so the tensor starter has
# to speak actions.FARMER_ACTIONS / MARKET_ACTIONS.  actions.decode(...) of
# the indices below reproduces the starter's raw farmer action lane by lane
# (gate: test_b4c.py (ii)) because the starter never moves off its spawn
# tile and never touches any other tile, so every intent's "nearest target"
# is its own tile:
#   PLANT_CARROT  <- kind == EMPTY and carrot seeds > 0     (decode: pos in
#                    s["empty"], seeds > 0 -> ["PLANT", "CARROT"])
#   HARVEST       <- carrot plant with age >= max_yield_day  (decode: pos in
#                    s["harvest"] -> ["HARVEST"]; when yield_units == 0 the
#                    decode falls to ["PASS"] and the raw ["HARVEST"] is an
#                    engine no-op -- effect-identical, see the gate)
#   WATER         <- carrot plant, unwatered, age < max_yield_day
#   PASS          <- otherwise
#
# MARKET-HEAD APPROXIMATION (documented, accepted): the reference starter can
# emit BOTH ["SELL","CARROT",n] and ["BUY_SEED","CARROT",1] in one turn; the
# market head is single-choice.  Priority: SELL_CARROT if the shed holds
# carrots, else BUY_SEED_CARROT if seeds == 0 and money >= seed cost, else
# NOOP.  When both fire, the buy is deferred one turn (next turn the shed is
# empty and seeds are still 0, so BUY_SEED_CARROT fires then).  In the
# starter's actual trajectory the two conditions essentially never coincide
# (it plants at hour 1 of a harvest day, when the harvest is still in the
# farmer's inventory, not the shed), so the tensor-starter's play matches
# the reference except for that one-turn buy deferral.  SELL_CARROT decodes
# to the whole carrot stock, and on/after LIQUIDATE_DAY to the whole shed
# carrot-first -- the starter's shed only ever holds carrots, so identical.

_F_PASS = A.FARMER_ACTIONS.index("PASS")
_F_WATER = A.FARMER_ACTIONS.index("WATER")
_F_HARVEST = A.FARMER_ACTIONS.index("HARVEST")
_F_PLANT_CARROT = A.FARMER_ACTIONS.index("PLANT_CARROT")
_M_NOOP = A.MARKET_ACTIONS.index("NOOP")
_M_SELL_CARROT = A.MARKET_ACTIONS.index("SELL_CARROT")
_M_BUY_SEED_CARROT = A.MARKET_ACTIONS.index("BUY_SEED_CARROT")


def starter_indices(ep, player):
    """Reference starter decisions as (fa (B,), ma (B,)) int64 head indices,
    computed on ep.device with no host round trip."""
    B = ep.money.shape[0]
    day = ep._step // ep.turns_per_day
    i64 = torch.int64

    fx = ep.farmer_xy[:, player, 0].to(i64)
    fy = ep.farmer_xy[:, player, 1].to(i64)
    flat = (fy * 10 + fx).view(B, 1)

    def at(t):
        return t[:, player].reshape(B, -1).gather(1, flat).view(B)

    kind = at(ep.kind).to(i64)
    crop = at(ep.crop).to(i64)
    planted = at(ep.planted_day).to(i64)
    watered = at(ep.watered)
    seeds_c = ep.seeds_t[:, player, CARROT_SEED_IDX].to(i64)
    shed_c = ep.shed[:, player, CARROT_PROD_IDX].to(i64)
    money = ep.money[:, player]

    carrot_plant = (kind == _KIND_PLANT) & (crop == CARROT_SEED_IDX)
    ripe = carrot_plant & ((day - planted) >= _CARROT_MAX_YIELD_DAY)
    thirsty = carrot_plant & ~ripe & ~watered
    plantable = (kind == _KIND_EMPTY) & (seeds_c > 0)

    fa = torch.full((B,), _F_PASS, dtype=i64, device=ep.device)
    fa = torch.where(thirsty, torch.full_like(fa, _F_WATER), fa)
    fa = torch.where(ripe, torch.full_like(fa, _F_HARVEST), fa)
    fa = torch.where(plantable, torch.full_like(fa, _F_PLANT_CARROT), fa)

    buy = (seeds_c == 0) & (money >= _CARROT_SEED_COST)
    ma = torch.full((B,), _M_NOOP, dtype=i64, device=ep.device)
    ma = torch.where(buy, torch.full_like(ma, _M_BUY_SEED_CARROT), ma)
    ma = torch.where(shed_c > 0, torch.full_like(ma, _M_SELL_CARROT), ma)
    return fa, ma
