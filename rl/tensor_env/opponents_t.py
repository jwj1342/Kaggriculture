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
