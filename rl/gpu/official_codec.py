"""Convert official engine action dicts ↔ GPU Actions, and snapshot obs for diffs.

Replay indexing matches tools/tracelib.py: steps[i]["action"] produced
steps[i]["observation"], so turns[t] is applied on the board at GPU step t.
"""

import torch

from . import constants as C
from .state import Actions, empty_actions

_OP = {
    "PASS": C.OP_PASS,
    "NORTH": C.OP_NORTH,
    "SOUTH": C.OP_SOUTH,
    "EAST": C.OP_EAST,
    "WEST": C.OP_WEST,
    "WATER": C.OP_WATER,
    "HARVEST": C.OP_HARVEST,
    "PLANT": C.OP_PLANT,
    "FEED": C.OP_FEED,
    "CARE": C.OP_CARE,
    "COLLECT_FERTILIZER": C.OP_COLLECT,
    "DIG": C.OP_DIG,
    "BUILD_COOP": C.OP_BUILD_COOP,
    "BUILD_PASTURE": C.OP_BUILD_PASTURE,
    "DROP": C.OP_DROP,
    "PICKUP": C.OP_PICKUP,
    "PLACE": C.OP_PLACE,
    "FERTILIZE": C.OP_FERTILIZE,
}
_MOP = {
    "HIRE": C.M_HIRE,
    "BUY_LAND": C.M_BUY_LAND,
    "BUY_SEED": C.M_BUY_SEED,
    "BUY_PRODUCT": C.M_BUY_PRODUCT,
    "BUY_ANIMAL": C.M_BUY_ANIMAL,
    "SELL": C.M_SELL,
}
_KIND = {
    None: C.K_EMPTY,
    "LOCKED": C.K_LOCKED,
    "WEED": C.K_WEED,
    "PLANT": C.K_PLANT,
    "PASTURE": C.K_PASTURE,
    "COOP": C.K_COOP,
}


def _get(obs, key, default=None):
    if obs is None:
        return default
    if isinstance(obs, dict):
        return obs.get(key, default)
    return getattr(obs, key, default)


def _item_index(name, kind):
    if kind == "product":
        return C.PRODUCTS.index(name) if name in C.PRODUCTS else 0
    if kind == "crop":
        return C.CROPS.index(name) if name in C.CROPS else 0
    if kind == "animal":
        return C.ANIMALS.index(name) if name in C.ANIMALS else 0
    if name in C.PRODUCTS:
        return C.PRODUCTS.index(name)
    if name in C.ANIMALS:
        return C.ANIMAL_SHED[C.ANIMALS.index(name)]
    return 0


def _encode_unit(action):
    if not isinstance(action, (list, tuple)) or not action:
        return C.OP_PASS, 0, 0
    op = _OP.get(action[0], C.OP_PASS)
    arg, qty = 0, 0
    if op == C.OP_PLANT and len(action) >= 2:
        arg = _item_index(action[1], "crop")
    elif op in (C.OP_PICKUP, C.OP_PLACE) and len(action) >= 2:
        name = action[1]
        if name in C.ANIMALS:
            arg = C.ANIMAL_SHED[C.ANIMALS.index(name)]
        elif name in C.PRODUCTS:
            arg = C.PRODUCTS.index(name)
        qty = int(action[2]) if len(action) >= 3 else 1
    return op, arg, qty


def _encode_market_order(order):
    if not isinstance(order, (list, tuple)) or not order:
        return C.M_NONE, 0, 0
    mop = _MOP.get(order[0], C.M_NONE)
    item, qty = 0, 0
    if mop == C.M_SELL or mop == C.M_BUY_PRODUCT:
        if len(order) >= 3:
            item = _item_index(order[1], "product")
            qty = int(order[2])
    elif mop == C.M_BUY_SEED:
        if len(order) >= 3:
            item = _item_index(order[1], "crop")
            qty = int(order[2])
    elif mop == C.M_BUY_ANIMAL:
        if len(order) >= 3:
            item = _item_index(order[1], "animal")
            qty = int(order[2])
    return mop, item, qty


def encode_turn(actions_by_player, device="cpu") -> Actions:
    """actions_by_player: [player0_dict, player1_dict] -> Actions with B=1."""
    act = empty_actions(1, device)
    for p, raw in enumerate(actions_by_player[:2]):
        d = raw if isinstance(raw, dict) else {}
        farmer = d.get("farmer") or ["PASS"]
        op, arg, qty = _encode_unit(farmer)
        act.op[0, p, 0] = op
        act.arg[0, p, 0] = arg
        act.qty[0, p, 0] = qty
        hands = d.get("hands") or []
        if not isinstance(hands, list):
            hands = []
        for h, ha in enumerate(hands[:C.ENGINE_HAND_CAP]):
            op, arg, qty = _encode_unit(ha)
            act.op[0, p, 1 + h] = op
            act.arg[0, p, 1 + h] = arg
            act.qty[0, p, 1 + h] = qty
        market = d.get("market") or []
        if not isinstance(market, list):
            market = []
        for i, order in enumerate(market[:C.MAX_ORDERS]):
            mop, item, qty = _encode_market_order(order)
            act.m_op[0, p, i] = mop
            act.m_item[0, p, i] = item
            act.m_qty[0, p, i] = qty
    return act


def _item_vec(mapping, names):
    mapping = mapping or {}
    return [int(mapping.get(n, 0) or 0) for n in names]


def _inv_slot(name):
    if name in C.PRODUCTS:
        return C.PRODUCTS.index(name)
    if name in C.ANIMALS:
        return C.ANIMAL_SHED[C.ANIMALS.index(name)]
    return None


def _inv_order(mapping):
    """Official dict insertion order (qty > 0), as [slot, qty] pairs."""
    out = []
    for name, n in (mapping or {}).items():
        n = int(n or 0)
        if n <= 0:
            continue
        slot = _inv_slot(name)
        if slot is None:
            continue
        out.append([slot, n])
    return out


def _private_vec(obs):
    priv = _get(obs, "private") or {}
    shed = _item_vec(_get(priv, "shed"), C.PRODUCTS + C.ANIMALS)
    seeds = _item_vec(_get(priv, "seeds"), C.CROPS)
    invs = _get(priv, "inventories") or [{}]
    farmer_inv = invs[0] if invs else {}
    backpack = _item_vec(farmer_inv, C.PRODUCTS + C.ANIMALS)
    return shed, seeds, backpack, _inv_order(farmer_inv)


def _tile_flag(tile, key):
    if isinstance(tile, dict):
        return int(bool(tile.get(key)))
    return 0


def _tile_int(tile, key, default=0):
    if isinstance(tile, dict):
        v = tile.get(key)
        if v is None:
            return default
        return int(v)
    return default


def snapshot_official(obs, obs1=None):
    """Compact ground-truth from official observation(s) after a step.

    `obs` is seat 0. Pass `obs1` so player-1 private (shed/seeds/backpack)
    is compared; seat-0 observation does not include it.
    """
    farms = _get(obs, "farms") or []
    market = _get(obs, "market") or {}
    town = _get(obs, "town") or {}
    inv = _get(market, "inventory") or {}
    money = []
    kinds = []
    animals = []
    crops = []
    yields = []
    watered = []
    fed = []
    unwatered = []
    unfed = []
    pending = []
    cared = []
    fert_until = []
    n_hands = []
    farmer = []
    hands = []
    unlocked = []
    hires = []
    for farm in farms[:2]:
        money.append(int(round(float(_get(farm, "money") or 0))))
        tiles = _get(farm, "tiles") or []
        board, ab, cb, yb, wb, fb = [], [], [], [], [], []
        ub, ufb, pb, crb, fub = [], [], [], [], []
        for y in range(C.BOARD):
            row, ar, cr, yr, wr, fr = [], [], [], [], [], []
            ur, ufr, pr, car, fur = [], [], [], [], []
            for x in range(C.BOARD):
                tile = tiles[y][x] if y < len(tiles) and x < len(tiles[y]) else "LOCKED"
                if tile is None:
                    vals = (C.K_EMPTY, -1, -1, 0, 0, 0, 0, 0, 0, 0, -1)
                elif tile == "LOCKED" or not isinstance(tile, dict):
                    vals = (C.K_LOCKED, -1, -1, 0, 0, 0, 0, 0, 0, 0, -1)
                else:
                    an = tile.get("animal")
                    cp = tile.get("crop")
                    vals = (
                        _KIND.get(tile.get("kind"), C.K_EMPTY),
                        C.ANIMALS.index(an) if an in C.ANIMALS else -1,
                        C.CROPS.index(cp) if cp in C.CROPS else -1,
                        int(tile.get("yield_units") or 0),
                        _tile_flag(tile, "watered_today"),
                        _tile_flag(tile, "fed_today"),
                        _tile_int(tile, "consecutive_unwatered"),
                        _tile_int(tile, "consecutive_unfed"),
                        _tile_int(tile, "pending_care_bonus"),
                        _tile_flag(tile, "cared_today"),
                        _tile_int(tile, "fertilized_until_day", -1),
                    )
                k, ani, cpi, yu, wat, fd, uw, uf, pc, cd, fu = vals
                row.append(k)
                ar.append(ani)
                cr.append(cpi)
                yr.append(yu)
                wr.append(wat)
                fr.append(fd)
                ur.append(uw)
                ufr.append(uf)
                pr.append(pc)
                car.append(cd)
                fur.append(fu)
            board.append(row)
            ab.append(ar)
            cb.append(cr)
            yb.append(yr)
            wb.append(wr)
            fb.append(fr)
            ub.append(ur)
            ufb.append(ufr)
            pb.append(pr)
            crb.append(car)
            fub.append(fur)
        kinds.append(board)
        animals.append(ab)
        crops.append(cb)
        yields.append(yb)
        watered.append(wb)
        fed.append(fb)
        unwatered.append(ub)
        unfed.append(ufb)
        pending.append(pb)
        cared.append(crb)
        fert_until.append(fub)
        hs = _get(farm, "hands") or []
        n_hands.append(len(hs))
        farmer.append([int(v) for v in (_get(farm, "farmer") or [4, 4])])
        hands.append([[int(v) for v in p] for p in hs])
        uq = _get(farm, "unlocked_quadrants") or ["NW"]
        unlocked.append([int(q in uq) for q in ("NW", "NE", "SW", "SE")])
        hires.append(int(_get(farm, "hires_today") or 0))
    shed0, seeds0, inv0, ord0 = _private_vec(obs)
    if obs1 is not None:
        shed1, seeds1, inv1, ord1 = _private_vec(obs1)
    else:
        shed1 = seeds1 = inv1 = ord1 = None
    return {
        "money": money,
        "kinds": kinds,
        "animals": animals,
        "crops": crops,
        "yields": yields,
        "watered": watered,
        "fed": fed,
        "unwatered": unwatered,
        "unfed": unfed,
        "pending": pending,
        "cared": cared,
        "fert_until": fert_until,
        "n_hands": n_hands,
        "farmer": farmer,
        "hands": hands,
        "unlocked": unlocked,
        "hires_today": hires,
        "shed0": shed0,
        "seeds0": seeds0,
        "inv0": inv0,
        "inv_order0": ord0,
        "shed1": shed1,
        "seeds1": seeds1,
        "inv1": inv1,
        "inv_order1": ord1,
        "market_inv": [int(inv.get(p, 0) or 0) for p in C.PRODUCTS],
        "shops": list(_get(town, "unlocked_shops") or []),
        "day": int(_get(obs, "day") or 0),
        "hour": int(_get(obs, "hour") or 0),
    }


def _gpu_inv_order(st, b, p, u=0):
    inv = st.inv[b, p, u].detach().cpu()
    rank = st.inv_ord[b, p, u].detach().cpu()
    items = []
    for i in range(C.N_SHED):
        n = int(inv[i].item())
        if n <= 0:
            continue
        r = int(rank[i].item())
        items.append((r if r >= 0 else 10**6, i, n))
    items.sort()
    return [[i, n] for _, i, n in items]


def snapshot_gpu(st, b=0):
    shops = []
    n = int(st.n_shops[b].item())
    for i in range(n):
        sid = int(st.shops[b, i].item())
        if 0 <= sid < len(C.SHOP_NAMES):
            shops.append(C.SHOP_NAMES[sid])
    hands = []
    for p in range(2):
        nh = int(st.n_hands[b, p].item())
        hands.append(st.hand_xy[b, p, :nh].detach().cpu().tolist())
    return {
        "money": [int(round(float(st.money[b, p].item()))) for p in range(2)],
        "kinds": st.kind[b].detach().cpu().tolist(),
        "animals": st.animal[b].detach().cpu().tolist(),
        "crops": st.crop[b].detach().cpu().tolist(),
        "yields": st.yield_units[b].detach().cpu().tolist(),
        "watered": st.watered[b].detach().cpu().to(torch.int64).tolist(),
        "fed": st.fed[b].detach().cpu().to(torch.int64).tolist(),
        "unwatered": st.unwatered[b].detach().cpu().tolist(),
        "unfed": st.unfed[b].detach().cpu().tolist(),
        "pending": st.pending_care[b].detach().cpu().tolist(),
        "cared": st.cared[b].detach().cpu().to(torch.int64).tolist(),
        "fert_until": st.fert_until[b].detach().cpu().tolist(),
        "n_hands": [int(st.n_hands[b, p].item()) for p in range(2)],
        "farmer": [st.farmer_xy[b, p].detach().cpu().tolist() for p in range(2)],
        "hands": hands,
        "unlocked": [
            st.unlocked[b, p].detach().cpu().to(torch.int64).tolist()
            for p in range(2)
        ],
        "hires_today": [int(st.hires_today[b, p].item()) for p in range(2)],
        "shed0": [int(st.shed[b, 0, i].item()) for i in range(C.N_SHED)],
        "seeds0": [int(st.seeds[b, 0, i].item()) for i in range(C.N_CROP)],
        "inv0": [int(st.inv[b, 0, 0, i].item()) for i in range(C.N_SHED)],
        "inv_order0": _gpu_inv_order(st, b, 0, 0),
        "shed1": [int(st.shed[b, 1, i].item()) for i in range(C.N_SHED)],
        "seeds1": [int(st.seeds[b, 1, i].item()) for i in range(C.N_CROP)],
        "inv1": [int(st.inv[b, 1, 0, i].item()) for i in range(C.N_SHED)],
        "inv_order1": _gpu_inv_order(st, b, 1, 0),
        "market_inv": [int(st.market_inv[b, i].item()) for i in range(C.N_PRODUCT)],
        "shops": shops,
        "day": int(st.day[b].item()),
        "hour": int(st.hour[b].item()),
    }


def _first_cell(a, b):
    """Compact first (player, y, x, official, gpu) mismatch in a [2][H][W] grid."""
    try:
        for p in range(len(a)):
            for y in range(len(a[p])):
                for x in range(len(a[p][y])):
                    if a[p][y][x] != b[p][y][x]:
                        return {"p": p, "y": y, "x": x, "official": a[p][y][x], "gpu": b[p][y][x]}
    except (TypeError, IndexError):
        return {"official": a, "gpu": b}
    return {"official": a, "gpu": b}


def first_diff(official, gpu, fields=None):
    fields = fields or (
        "day", "hour", "n_hands", "hires_today", "unlocked",
        "farmer", "hands", "kinds", "animals", "crops",
        "yields", "watered", "fed", "unwatered", "unfed",
        "pending", "cared", "fert_until", "shops",
        "seeds0", "seeds1", "shed0", "shed1",
        "inv0", "inv1", "inv_order0", "inv_order1",
        "market_inv", "money",
    )
    grids = {
        "kinds", "animals", "crops", "yields", "watered", "fed",
        "unwatered", "unfed", "pending", "cared", "fert_until",
    }
    for key in fields:
        a, b = official.get(key), gpu.get(key)
        if a is None or b is None:
            continue
        if a != b:
            if key in grids:
                cell = _first_cell(a, b)
                return key, cell, cell
            return key, a, b
    return None
