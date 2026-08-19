"""Vectorized Kaggriculture step on batched tensors.

Day-end weeds and shop unlocks use the official Random stream so recorded
episodes can be replayed (see rl.gpu.verify). Backpack deposits follow
Python dict insertion order, matching `_drop_inventories_to_shed`.
"""

import math
import random

import numpy as np
import torch

from . import constants as C
from .state import (
    TensorState, Actions, gather_tile, scatter_inplace, reset_tile,
    unit_xy, is_shed_tile, all_unit_alive,
)
from .tables import Tables


def _shape(fn, x):
    x = x.clamp(min=0)
    linear = x
    sq = x * x
    sqrt = x.sqrt()
    log = (1.0 + x).log()
    log10 = log * 0.4342944819032518
    out = torch.where(fn == 1, sq, linear)
    out = torch.where(fn == 2, sqrt, out)
    out = torch.where(fn == 3, log, out)
    out = torch.where(fn == 4, log10, out)
    return out


def market_prices(inv, T: Tables):
    """inv [B, 9] int -> prices [B, 9] float."""
    inv_f = inv.to(torch.float32)
    below = inv_f < T.i0
    delta = (T.i0 - inv_f).abs()
    fn = torch.where(below, T.mkt_below_f, T.mkt_above_f)
    tgt = torch.where(below, T.mkt_below_t, T.mkt_above_t)
    amp = tgt * T.base_price / _shape(fn, T.mkt_t).clamp(min=1e-6)
    raw = torch.where(below, T.base_price + amp * _shape(fn, delta),
                      T.base_price - amp * _shape(fn, delta))
    return raw.round().clamp(min=C.PRICE_FLOOR)


def _gather_item(inv_bp, idx, empty=0):
    """inv [B,2,N], idx [B,2] long -> [B,2]."""
    idx = idx.long().clamp(0, inv_bp.shape[-1] - 1)
    return inv_bp.gather(-1, idx.unsqueeze(-1)).squeeze(-1)


def _add_item(inv_bp, idx, n, mask):
    """Add n to inv[idx] where mask. inv [B,2,N], idx/n/mask [B,2]."""
    idx = idx.long().clamp(0, inv_bp.shape[-1] - 1)
    n = n.to(inv_bp.dtype)
    cur = inv_bp.gather(-1, idx.unsqueeze(-1)).squeeze(-1)
    nxt = torch.where(mask, cur + n, cur)
    inv_bp.scatter_(-1, idx.unsqueeze(-1), nxt.unsqueeze(-1))


def _take_item(inv_bp, idx, n, mask):
    """Take n if available. Returns success mask."""
    idx = idx.long().clamp(0, inv_bp.shape[-1] - 1)
    n = n.to(inv_bp.dtype)
    cur = inv_bp.gather(-1, idx.unsqueeze(-1)).squeeze(-1)
    ok = mask & (cur >= n)
    nxt = torch.where(ok, cur - n, cur)
    inv_bp.scatter_(-1, idx.unsqueeze(-1), nxt.unsqueeze(-1))
    return ok


def _cpu_shape(fn, x):
    """Official `_shape` on CPython floats (sqrt/log match the interpreter)."""
    x = max(0.0, float(x))
    if fn == 0:
        return x
    if fn == 1:
        return x * x
    if fn == 2:
        return math.sqrt(x)
    if fn == 3:
        return math.log(1.0 + x)
    return math.log10(1.0 + x)


def _cpu_market_price(item_i, inventory):
    """Same `int(round(...))` as reference/engine/kaggriculture.py `market_price`."""
    base = float(C.BASE_PRICE[item_i])
    i0 = float(C.MARKET_I0)
    t = float(C.MKT_T[item_i])
    if inventory < i0:
        fn = C.MKT_BELOW_F[item_i]
        tgt = C.MKT_BELOW_T[item_i]
        amp = tgt * base / _cpu_shape(fn, t)
        price = base + amp * _cpu_shape(fn, i0 - inventory)
    else:
        fn = C.MKT_ABOVE_F[item_i]
        tgt = C.MKT_ABOVE_T[item_i]
        amp = tgt * base / _cpu_shape(fn, t)
        price = base - amp * _cpu_shape(fn, inventory - i0)
    return max(int(C.PRICE_FLOOR), int(round(price)))


def attach_price_table(T: Tables):
    """LUT from CPython `market_price` (`int(round)`), then gather on device.

    GPU sqrt/log is not bit-exact with the interpreter; tensorize D1 was to
    tabulate on the host once.
    """
    if getattr(T, "price_table", None) is not None:
        return
    lo = C.PRICE_INV_LO
    hi = C.PRICE_INV_MAX
    width = hi - lo + 1
    host = [[_cpu_market_price(i, inv) for i in range(C.N_PRODUCT)]
            for inv in range(lo, hi + 1)]
    T.price_lo = lo
    T.price_table = torch.tensor(host, device=T.device, dtype=torch.float32)


def _quote_table(T: Tables, inv_levels):
    """inv_levels [..., 9] int -> prices [..., 9] from the CPython LUT."""
    idx = (inv_levels.long() - int(getattr(T, "price_lo", C.PRICE_INV_LO))).clamp(
        0, T.price_table.shape[0] - 1)
    col = torch.arange(C.N_PRODUCT, device=inv_levels.device)
    return T.price_table[idx, col]


def quote_market(st, T: Tables):
    """Current market prices [B, 9] from the official LUT."""
    attach_price_table(T)
    return _quote_table(T, st.market_inv)


def _n_live_units(st: TensorState):
    """Farmer + max live hands in this batch (capped by tensor width).

    Uses the host-side hire counter so the hot path never reads GPU n_hands.
    """
    return min(C.N_UNIT, 1 + int(getattr(st, "cpu_max_hands", 0)))


def _inv_add(st: TensorState, u: int, idx, n, mask):
    """Add to a unit backpack and record official dict insertion order."""
    inv = st.inv[:, :, u, :]
    ord_ = st.inv_ord[:, :, u, :]
    nxt = st.inv_next[:, :, u]
    idx = idx.long().clamp(0, C.N_SHED - 1)
    n = n.to(inv.dtype)
    cur = inv.gather(-1, idx.unsqueeze(-1)).squeeze(-1)
    adding = mask & (n > 0)
    was_empty = adding & (cur <= 0)
    cur_ord = ord_.gather(-1, idx.unsqueeze(-1)).squeeze(-1)
    new_ord = torch.where(was_empty, nxt.to(ord_.dtype), cur_ord)
    ord_.scatter_(-1, idx.unsqueeze(-1), new_ord.unsqueeze(-1))
    st.inv_next[:, :, u] = nxt + was_empty.to(nxt.dtype)
    inv.scatter_(-1, idx.unsqueeze(-1), torch.where(adding, cur + n, cur).unsqueeze(-1))


def _inv_take(st: TensorState, u: int, idx, n, mask):
    """Take from a unit backpack; qty 0 deletes the dict key (clears insertion rank)."""
    inv = st.inv[:, :, u, :]
    ord_ = st.inv_ord[:, :, u, :]
    idx = idx.long().clamp(0, C.N_SHED - 1)
    n = n.to(inv.dtype)
    cur = inv.gather(-1, idx.unsqueeze(-1)).squeeze(-1)
    ok = mask & (n > 0) & (cur >= n)
    new_qty = torch.where(ok, cur - n, cur)
    emptied = ok & (new_qty == 0)
    cur_ord = ord_.gather(-1, idx.unsqueeze(-1)).squeeze(-1)
    new_ord = torch.where(emptied, torch.full_like(cur_ord, -1), cur_ord)
    ord_.scatter_(-1, idx.unsqueeze(-1), new_ord.unsqueeze(-1))
    inv.scatter_(-1, idx.unsqueeze(-1), new_qty.unsqueeze(-1))
    return ok


def _deposit_inv(st: TensorState, u: int, mask):
    """Official DROP / end-of-day: iterate `inv.items()` insertion order.

    Each item is deposited up to remaining shed room; leftover of that item
    (and every later item) is discarded, not kept in the backpack.
    """
    inv = st.inv[:, :, u, :]
    ord_ = st.inv_ord[:, :, u, :]
    absent = torch.full_like(ord_, 10**6, dtype=torch.int32)
    key = torch.where(inv > 0, ord_.to(torch.int32), absent)
    order_idx = key.argsort(dim=-1)
    for r in range(C.N_SHED):
        item = order_idx[..., r]
        carry = inv.gather(-1, item.unsqueeze(-1)).squeeze(-1)
        active = mask & (carry > 0)
        room = (C.SHED_CAP - st.shed.sum(-1)).clamp(min=0)
        take = torch.minimum(carry.to(room.dtype), room).to(st.shed.dtype)
        take = torch.where(active, take, take.new_zeros(take.shape))
        cur_s = st.shed.gather(-1, item.unsqueeze(-1)).squeeze(-1)
        st.shed.scatter_(-1, item.unsqueeze(-1), (cur_s + take).unsqueeze(-1))
    z = mask.unsqueeze(-1)
    st.inv[:, :, u, :] = torch.where(z, torch.zeros_like(inv), inv)
    st.inv_ord[:, :, u, :] = torch.where(z, torch.full_like(ord_, -1), ord_)
    st.inv_next[:, :, u] = torch.where(
        mask, torch.zeros_like(st.inv_next[:, :, u]), st.inv_next[:, :, u],
    )


def _apply_moves(st: TensorState, act: Actions, u: int, T: Tables, alive):
    xy = unit_xy(st, u)
    op = act.op[:, :, u].long()
    dx = T.move_dx[op]
    dy = T.move_dy[op]
    moving = alive & (op >= C.OP_NORTH) & (op <= C.OP_WEST)
    nx = xy[..., 0] + dx
    ny = xy[..., 1] + dy
    ok = moving & (nx >= 0) & (nx < C.BOARD) & (ny >= 0) & (ny < C.BOARD)
    xy[..., 0] = torch.where(ok, nx, xy[..., 0])
    xy[..., 1] = torch.where(ok, ny, xy[..., 1])
    if u == 0:
        st.farmer_xy = xy
    else:
        st.hand_xy[:, :, u - 1, :] = xy


def _apply_moves_all(st: TensorState, act: Actions, T: Tables):
    """Move farmer + live hand slots in one shot. No unit-unit blocking."""
    n_u = _n_live_units(st)
    B = st.batch_size()
    device = st.device()
    xy = torch.empty(B, C.N_PLAYER, n_u, 2, dtype=st.farmer_xy.dtype, device=device)
    xy[:, :, 0, :] = st.farmer_xy
    if n_u > 1:
        xy[:, :, 1:, :] = st.hand_xy[:, :, :n_u - 1, :]
    op = act.op[:, :, :n_u].long()
    u = torch.arange(n_u, device=device)
    alive = (u == 0) | (st.n_hands.unsqueeze(-1) > (u - 1))
    moving = alive & (op >= C.OP_NORTH) & (op <= C.OP_WEST)
    nx = xy[..., 0] + T.move_dx[op]
    ny = xy[..., 1] + T.move_dy[op]
    ok = moving & (nx >= 0) & (nx < C.BOARD) & (ny >= 0) & (ny < C.BOARD)
    xy[..., 0] = torch.where(ok, nx, xy[..., 0])
    xy[..., 1] = torch.where(ok, ny, xy[..., 1])
    st.farmer_xy = xy[:, :, 0, :].contiguous()
    if n_u > 1:
        st.hand_xy[:, :, :n_u - 1, :] = xy[:, :, 1:, :]


def _unit_inv(st: TensorState, u: int):
    return st.inv[:, :, u, :]


def _apply_shed_ops(st: TensorState, act: Actions, u: int, T: Tables, alive):
    xy = unit_xy(st, u)
    op = act.op[:, :, u]
    arg = act.arg[:, :, u].long()
    qty = act.qty[:, :, u].to(torch.int32).clamp(min=0)
    at_shed = is_shed_tile(xy) & alive
    inv = _unit_inv(st, u)
    kind = gather_tile(st.kind, xy)
    animal = gather_tile(st.animal, xy)

    dump = at_shed & (op == C.OP_DROP)
    _deposit_inv(st, u, dump)

    pickup = at_shed & (op == C.OP_PICKUP)
    item = arg.clamp(0, C.N_SHED - 1)
    n = torch.minimum(qty, _gather_item(st.shed, item)).to(torch.int32)
    n = torch.where(pickup, n, n.new_zeros(n.shape))
    _add_item(st.shed, item, -n, pickup & (n > 0))
    _inv_add(st, u, item, n, pickup & (n > 0))

    is_anim = (op == C.OP_PLACE) & (arg >= C.ANIMAL_SHED0) & (arg < C.ANIMAL_SHED0 + C.N_ANIMAL)
    aid = (arg - C.ANIMAL_SHED0).clamp(0, C.N_ANIMAL - 1)
    on_struct = is_anim & (kind == T.animal_struct[aid]) & (animal < 0)
    place_shed = at_shed & (op == C.OP_PLACE) & (~on_struct)
    n = torch.minimum(qty.clamp(min=1), _gather_item(inv, item)).to(torch.int32)
    room = (C.SHED_CAP - st.shed.sum(dim=-1)).clamp(min=0)
    n = torch.minimum(n, room)
    n = torch.where(place_shed, n, n.new_zeros(n.shape))
    ok = place_shed & (n > 0)
    _inv_take(st, u, item, n, ok)
    _add_item(st.shed, item, n, ok)


def _apply_tile_ops(st: TensorState, act: Actions, u: int, T: Tables, alive):
    xy = unit_xy(st, u)
    op = act.op[:, :, u]
    arg = act.arg[:, :, u].long()
    kind = gather_tile(st.kind, xy)
    crop = gather_tile(st.crop, xy)
    animal = gather_tile(st.animal, xy)
    owned = alive & (kind != C.K_LOCKED)
    inv = _unit_inv(st, u)
    day = st.day.to(torch.int32)[:, None].expand_as(kind)

    # PLACE animal onto empty matching structure (arg = shed slot 9..11)
    is_anim_place = (op == C.OP_PLACE) & (arg >= C.ANIMAL_SHED0) & (arg < C.ANIMAL_SHED0 + C.N_ANIMAL)
    aid = (arg - C.ANIMAL_SHED0).clamp(0, C.N_ANIMAL - 1)
    want_kind = T.animal_struct[aid]
    slot = T.animal_shed[aid]
    empty_struct = (kind == want_kind) & (animal < 0)
    place_a = owned & is_anim_place & empty_struct
    took = _inv_take(st, u, slot, torch.ones_like(slot, dtype=inv.dtype), place_a)
    scatter_inplace(st.animal, xy, aid.to(torch.int16), took)
    scatter_inplace(st.placed_day, xy, st.day.to(torch.int16)[:, None].expand_as(kind), took)
    scatter_inplace(st.yield_units, xy, 0, took)
    scatter_inplace(st.fed, xy, False, took)
    scatter_inplace(st.unfed, xy, 0, took)
    scatter_inplace(st.cared, xy, False, took)
    scatter_inplace(st.fert_avail, xy, False, took)
    scatter_inplace(st.pending_care, xy, 0, took)

    # PLANT
    cid = arg.clamp(0, C.N_CROP - 1)
    plant = owned & (op == C.OP_PLANT) & (kind == C.K_EMPTY)
    has_seed = _gather_item(st.seeds, cid) > 0
    plant = plant & has_seed
    _take_item(st.seeds, cid, torch.ones_like(cid, dtype=st.seeds.dtype), plant)
    ongoing = T.crop_ongoing[cid]
    y0 = torch.where(ongoing, torch.zeros_like(kind, dtype=torch.int16),
                     torch.ones_like(kind, dtype=torch.int16))
    max_day = T.crop_max_day[cid]
    life = torch.where(
        ongoing,
        torch.full_like(day, -1),
        (day + max_day + 1) * C.TURNS_PER_DAY,
    )
    reset_tile(st, xy, plant, kind=C.K_PLANT)
    scatter_inplace(st.crop, xy, cid.to(torch.int16), plant)
    scatter_inplace(st.planted_day, xy, st.day.to(torch.int16)[:, None].expand_as(kind), plant)
    scatter_inplace(st.yield_units, xy, y0, plant)
    scatter_inplace(st.unwatered, xy, 1, plant)
    scatter_inplace(st.max_life, xy, life, plant)

    # WATER
    watered = gather_tile(st.watered, xy)
    fert_until = gather_tile(st.fert_until, xy)
    yu = gather_tile(st.yield_units, xy)
    planted_day = gather_tile(st.planted_day, xy)
    is_plant = kind == C.K_PLANT
    water = owned & (op == C.OP_WATER) & is_plant & (~watered)
    scatter_inplace(st.watered, xy, True, water)
    c = crop.clamp(min=0).long()
    age = day - planted_day.to(torch.int32)
    window = T.water_window[c]
    maxd = T.crop_max_day[c]
    in_win = (age >= window) & (age <= maxd) & (~T.crop_ongoing[c])
    bonus = torch.where(fert_until.to(torch.int32) >= day, 2, 1).to(yu.dtype)
    new_y = torch.minimum(yu + bonus, T.crop_max_yield[c])
    scatter_inplace(st.yield_units, xy, new_y, water & in_win)

    # HARVEST
    harv = owned & (op == C.OP_HARVEST) & (yu > 0)
    first = T.crop_first[c]
    mature = (~is_plant) | (age >= first)
    harv = harv & mature
    plant_h = harv & is_plant
    anim_h = harv & (animal >= 0)
    _inv_add(st, u, c, yu.to(inv.dtype), plant_h)
    prod = T.animal_product[animal.clamp(min=0).long()]
    _inv_add(st, u, prod, yu.to(inv.dtype), anim_h)
    scatter_inplace(st.yield_units, xy, 0, harv)
    one_shot = plant_h & (~T.crop_ongoing[c])
    reset_tile(st, xy, one_shot, kind=C.K_EMPTY)

    # FERTILIZE
    fert = owned & (op == C.OP_FERTILIZE) & is_plant
    took_f = _inv_take(st, u, torch.full_like(c, C.FERT_SLOT),
                       torch.ones_like(c, dtype=inv.dtype), fert)
    until = torch.maximum(fert_until.to(torch.int32), day + 2).to(st.fert_until.dtype)
    scatter_inplace(st.fert_until, xy, until, took_f)

    # DIG
    has_animal = animal >= 0
    dig = owned & (op == C.OP_DIG) & (kind != C.K_EMPTY) & (~has_animal)
    reset_tile(st, xy, dig, kind=C.K_EMPTY)

    # BUILD
    build_c = owned & (op == C.OP_BUILD_COOP) & (kind == C.K_EMPTY)
    build_p = owned & (op == C.OP_BUILD_PASTURE) & (kind == C.K_EMPTY)
    reset_tile(st, xy, build_c, kind=C.K_COOP)
    reset_tile(st, xy, build_p, kind=C.K_PASTURE)

    # FEED / CARE / COLLECT
    is_anim = animal >= 0
    fed = gather_tile(st.fed, xy)
    cared = gather_tile(st.cared, xy)
    favail = gather_tile(st.fert_avail, xy)
    feed = owned & (op == C.OP_FEED) & is_anim & (~fed)
    took_w = _inv_take(st, u, torch.zeros_like(c), torch.ones_like(c, dtype=inv.dtype), feed)
    scatter_inplace(st.fed, xy, True, took_w)
    care = owned & (op == C.OP_CARE) & is_anim & (~cared)
    scatter_inplace(st.cared, xy, True, care)
    coll = owned & (op == C.OP_COLLECT) & is_anim & favail
    scatter_inplace(st.fert_avail, xy, False, coll)
    _inv_add(st, u, torch.full_like(c, C.FERT_SLOT), torch.ones_like(c, dtype=inv.dtype), coll)


def _block_overplant(st: TensorState, act: Actions):
    """If PLANT demand for a crop exceeds seeds, drop all those PLANTs (official rule)."""
    n_u = _n_live_units(st)
    B = st.batch_size()
    device = st.device()
    u = torch.arange(n_u, device=device)
    alive = (u == 0) | (st.n_hands.unsqueeze(-1) > (u - 1))
    op_u = act.op[:, :, :n_u]
    cid = act.arg[:, :, :n_u].long().clamp(0, C.N_CROP - 1)
    plant = (op_u == C.OP_PLANT) & alive
    demand = torch.zeros(B, C.N_PLAYER, C.N_CROP, device=device, dtype=torch.int32)
    demand.scatter_add_(-1, cid, plant.to(torch.int32))
    blocked = demand > st.seeds
    drop = plant & blocked.gather(-1, cid)
    act.op[:, :, :n_u] = torch.where(drop, torch.zeros_like(op_u), op_u)


def _hire(st: TensorState, mask, T: Tables):
    idx = st.hires_today.to(torch.int64).clamp(0, len(C.HIRE_FIB) - 1)
    cost = T.hire_fib[idx]
    can = mask & (st.n_hands < C.ENGINE_HAND_CAP) & (st.money >= cost)
    st.money = st.money - torch.where(can, cost, torch.zeros_like(cost))
    # Official spawn: min occupancy on the four shed-access tiles, NWSE tie-break.
    fx = st.farmer_xy[..., 0]
    fy = st.farmer_xy[..., 1]
    occ = ((fx.unsqueeze(-1) == T.shed_x) & (fy.unsqueeze(-1) == T.shed_y)).to(torch.int32)
    hx = st.hand_xy[..., 0]
    hy = st.hand_xy[..., 1]
    h_idx = torch.arange(C.ENGINE_HAND_CAP, device=st.device())
    live_h = h_idx.view(1, 1, -1) < st.n_hands.unsqueeze(-1)
    hand_hit = (
        (hx.unsqueeze(-1) == T.shed_x) & (hy.unsqueeze(-1) == T.shed_y) & live_h.unsqueeze(-1)
    )
    occ = occ + hand_hit.to(torch.int32).sum(2)
    score = occ.to(torch.float32) + torch.arange(4, device=st.device(), dtype=torch.float32) * 1e-3
    best = score.argmin(-1)
    bx = T.shed_x[best]
    by = T.shed_y[best]
    B = st.batch_size()
    pcount = C.N_PLAYER
    bb = torch.arange(B, device=st.device())[:, None].expand(B, pcount)
    pp = torch.arange(pcount, device=st.device())[None, :].expand(B, pcount)
    nh = st.n_hands.long().clamp(0, C.ENGINE_HAND_CAP - 1)
    curx = st.hand_xy[bb, pp, nh, 0]
    cury = st.hand_xy[bb, pp, nh, 1]
    st.hand_xy[bb, pp, nh, 0] = torch.where(can, bx, curx)
    st.hand_xy[bb, pp, nh, 1] = torch.where(can, by, cury)
    st.n_hands = st.n_hands + can.to(st.n_hands.dtype)
    st.hires_today = st.hires_today + can.to(st.hires_today.dtype)


def _buy_land(st: TensorState, mask, T: Tables):
    n_extra = st.unlocked.to(torch.int64).sum(-1) - 1
    n_extra = n_extra.clamp(0, 3)
    cost = T.land_prices[n_extra.clamp(0, 2)]
    can = mask & (n_extra < 3) & (st.money >= cost)
    st.money = st.money - torch.where(can, cost, torch.zeros_like(cost))
    # unlock quadrant: extra 0->NE(1), 1->SW(2), 2->SE(3)
    qid = (n_extra + 1).clamp(1, 3)
    yy = T.yy.expand(st.batch_size(), C.N_PLAYER, C.BOARD, C.BOARD)
    xx = T.xx.expand(st.batch_size(), C.N_PLAYER, C.BOARD, C.BOARD)
    quad = (yy >= C.BOARD // 2).to(torch.int64) * 2 + (xx >= C.BOARD // 2).to(torch.int64)
    match = (quad == qid[:, :, None, None]) & (st.kind == C.K_LOCKED) & can[:, :, None, None]
    st.kind = torch.where(match, torch.zeros_like(st.kind), st.kind)
    # mark unlocked flag
    st.unlocked.scatter_(-1, qid.unsqueeze(-1), torch.where(
        can.unsqueeze(-1), torch.ones_like(st.unlocked[:, :, :1]),
        st.unlocked.gather(-1, qid.unsqueeze(-1)),
    ))


def _scatter_amt(item_p, amount, out_like):
    """amount/item_p [B,2] -> add into [B, 9]."""
    out = torch.zeros_like(out_like)
    out.scatter_add_(-1, item_p[:, 0:1], amount[:, 0:1].to(out.dtype))
    out.scatter_add_(-1, item_p[:, 1:2], amount[:, 1:2].to(out.dtype))
    return out


def _apply_qty_orders(st: TensorState, mop, item, qty, T: Tables):
    """One market slot, both players, all units of the order in tensor form.

    Ticks are interleaved: both players see the same start-of-tick inventory.
    Sell/buy-product change that inventory; buy-seed/animal only touch money.
    """
    attach_price_table(T)
    K = C.SHED_CAP
    B = st.batch_size()
    device = st.device()
    item_p = item.clamp(0, C.N_PRODUCT - 1)
    crop_i = item.clamp(0, C.N_CROP - 1)
    anim_i = item.clamp(0, C.N_ANIMAL - 1)

    is_sell = mop == C.M_SELL
    is_bp = mop == C.M_BUY_PRODUCT
    is_bs = mop == C.M_BUY_SEED
    is_ba = mop == C.M_BUY_ANIMAL
    buy_allowed = (item == C.WHEAT_SLOT) | (item == C.FERT_SLOT)

    have = _gather_item(st.shed, item_p)
    room = (C.SHED_CAP - st.shed.sum(-1)).clamp(min=0)
    n_sell = torch.where(is_sell, torch.minimum(qty, have), torch.zeros_like(qty))
    n_bp = torch.where(is_bp & buy_allowed, torch.minimum(qty, room), torch.zeros_like(qty))
    n_bs = torch.where(is_bs, qty, torch.zeros_like(qty))
    n_ba = torch.where(is_ba, torch.minimum(qty, room), torch.zeros_like(qty))

    t = torch.arange(K, device=device)
    sell_t = is_sell.unsqueeze(-1) & (t.view(1, 1, K) < n_sell.unsqueeze(-1))
    bp_t = (is_bp & buy_allowed).unsqueeze(-1) & (t.view(1, 1, K) < n_bp.unsqueeze(-1))

    delta = torch.zeros(B, K, C.N_PRODUCT, device=device, dtype=torch.int32)
    for p in range(C.N_PLAYER):
        ip = item_p[:, p, None, None].expand(B, K, 1)
        add = torch.zeros(B, K, C.N_PRODUCT, device=device, dtype=torch.int32)
        add.scatter_(-1, ip, sell_t[:, p].to(torch.int32).unsqueeze(-1))
        sub = torch.zeros(B, K, C.N_PRODUCT, device=device, dtype=torch.int32)
        sub.scatter_(-1, ip, bp_t[:, p].to(torch.int32).unsqueeze(-1))
        delta = delta + add - sub

    inv_before = torch.empty(B, K, C.N_PRODUCT, device=device, dtype=st.market_inv.dtype)
    inv_before[:, 0, :] = st.market_inv
    if K > 1:
        inv_before[:, 1:, :] = st.market_inv.unsqueeze(1) + delta.cumsum(1)[:, :-1, :].to(st.market_inv.dtype)

    quotes = _quote_table(T, inv_before)
    quotes_buy = _quote_table(T, inv_before - 1)
    item_exp = item_p.unsqueeze(-1).unsqueeze(-1).expand(B, C.N_PLAYER, K, 1)
    q = torch.gather(quotes.unsqueeze(1).expand(B, C.N_PLAYER, K, C.N_PRODUCT), 3, item_exp).squeeze(-1)
    q_buy = torch.gather(
        quotes_buy.unsqueeze(1).expand(B, C.N_PLAYER, K, C.N_PRODUCT), 3, item_exp,
    ).squeeze(-1)

    sell_money = (q * sell_t).sum(-1)
    st.money = st.money + sell_money
    _add_item(st.shed, item_p, -n_sell, n_sell > 0)

    cost_bp = torch.where(bp_t, q_buy, torch.zeros_like(q_buy))
    cum_bp = cost_bp.cumsum(-1)
    bp_ok = bp_t & (cum_bp <= st.money.unsqueeze(-1))
    n_bp_ok = bp_ok.to(torch.int32).sum(-1)
    st.money = st.money - (q_buy * bp_ok).sum(-1)
    _add_item(st.shed, item_p, n_bp_ok, n_bp_ok > 0)

    inc_sell = (sell_t & (q > 1)).to(st.market_inv.dtype).sum(-1)
    st.market_inv = st.market_inv + _scatter_amt(item_p, inc_sell, st.market_inv)
    st.market_inv = st.market_inv - _scatter_amt(item_p, n_bp_ok, st.market_inv)

    seed_cost = T.seed_cost[crop_i]
    n_afford_s = torch.div(
        st.money, seed_cost.clamp(min=1e-6), rounding_mode="floor",
    ).to(torch.int32).clamp(min=0)
    n_bs = torch.minimum(n_bs, n_afford_s)
    st.money = st.money - n_bs.to(st.money.dtype) * seed_cost
    _add_item(st.seeds, crop_i, n_bs, n_bs > 0)

    anim_cost = T.animal_cost[anim_i]
    room2 = (C.SHED_CAP - st.shed.sum(-1)).clamp(min=0)
    n_ba = torch.minimum(n_ba, room2)
    n_afford_a = torch.div(
        st.money, anim_cost.clamp(min=1e-6), rounding_mode="floor",
    ).to(torch.int32).clamp(min=0)
    n_ba = torch.minimum(n_ba, n_afford_a)
    st.money = st.money - n_ba.to(st.money.dtype) * anim_cost
    _add_item(st.shed, T.animal_shed[anim_i], n_ba, n_ba > 0)


def _process_market(st: TensorState, act: Actions, T: Tables):
    attach_price_table(T)
    # One host copy per turn so empty slots skip the heavy qty kernel without
    # a GPU .any() per slot. Hire-cap is updated once, not per HIRE order.
    mop_cpu = act.m_op.detach().cpu()
    hired = False
    for slot in range(C.MAX_ORDERS):
        mop = act.m_op[:, :, slot]
        item = act.m_item[:, :, slot].long()
        qty = act.m_qty[:, :, slot].to(torch.int32).clamp(min=0, max=C.MAX_MARKET_UNITS)
        slot_cpu = mop_cpu[:, :, slot]
        if int((slot_cpu == C.M_HIRE).any()):
            _hire(st, mop == C.M_HIRE, T)
            hired = True
        if int((slot_cpu == C.M_BUY_LAND).any()):
            _buy_land(st, mop == C.M_BUY_LAND, T)
        if int((slot_cpu >= C.M_BUY_SEED).any()):
            _apply_qty_orders(st, mop, item, qty, T)
    if hired:
        st.cpu_max_hands = min(
            C.ENGINE_HAND_CAP,
            int(st.n_hands.max().clamp(min=0).item()),
        )


def _town_consume(st: TensorState, T: Tables):
    step = st.step
    shop_tick = (step % C.SHOP_SELL_EVERY) == 0
    center_tick = (step % C.CENTER_SELL_EVERY) == 0
    shops = st.shops.to(torch.int64)
    valid = shops >= 0
    sid = shops.clamp(min=0)
    row = T.shop_consume[sid]  # [B, 8, 9]
    consume = (row * valid.to(row.dtype).unsqueeze(-1)).sum(1)
    st.market_inv = st.market_inv - torch.where(
        shop_tick[:, None], consume, torch.zeros_like(consume))
    center = T.town_center.unsqueeze(0).expand_as(st.market_inv)
    st.market_inv = st.market_inv - torch.where(
        center_tick[:, None], center, torch.zeros_like(center))


def _become_weed(st: TensorState, mask):
    """Official replaces the tile with {kind: WEED}; drop plant/animal fields."""
    st.kind = torch.where(mask, torch.full_like(st.kind, C.K_WEED), st.kind)
    st.crop = torch.where(mask, torch.full_like(st.crop, -1), st.crop)
    st.animal = torch.where(mask, torch.full_like(st.animal, -1), st.animal)
    st.planted_day = torch.where(mask, torch.zeros_like(st.planted_day), st.planted_day)
    st.placed_day = torch.where(mask, torch.zeros_like(st.placed_day), st.placed_day)
    st.yield_units = torch.where(mask, torch.zeros_like(st.yield_units), st.yield_units)
    st.watered = torch.where(mask, torch.zeros_like(st.watered), st.watered)
    st.unwatered = torch.where(mask, torch.zeros_like(st.unwatered), st.unwatered)
    st.fed = torch.where(mask, torch.zeros_like(st.fed), st.fed)
    st.unfed = torch.where(mask, torch.zeros_like(st.unfed), st.unfed)
    st.cared = torch.where(mask, torch.zeros_like(st.cared), st.cared)
    st.fert_avail = torch.where(mask, torch.zeros_like(st.fert_avail), st.fert_avail)
    st.fert_until = torch.where(mask, torch.full_like(st.fert_until, -1), st.fert_until)
    st.pending_care = torch.where(mask, torch.zeros_like(st.pending_care), st.pending_care)
    st.max_life = torch.where(mask, torch.full_like(st.max_life, -1), st.max_life)


def _decay_plants(st: TensorState):
    is_plant = st.kind == C.K_PLANT
    mls = st.max_life
    step = st.step.to(torch.int32)[:, None, None, None]
    ripe = is_plant & (mls >= 0) & (step >= mls) & (((step - mls) % 2) == 0)
    st.yield_units = torch.where(ripe, st.yield_units - 1, st.yield_units)
    die = ripe & (st.yield_units <= 0)
    _become_weed(st, die)


def _end_of_day(st: TensorState, T: Tables, eod=None):
    """Day-end refresh. `eod` is [B] bool so mixed-hour batches only tick due envs."""
    B = st.batch_size()
    if eod is None:
        eod = torch.ones(B, dtype=torch.bool, device=st.device())
    em = eod[:, None, None, None]
    emp = eod[:, None]

    day = st.day.to(torch.int32)[:, None, None, None]
    is_plant = st.kind == C.K_PLANT
    was_watered = st.watered
    unwatered = torch.where(was_watered, torch.zeros_like(st.unwatered), st.unwatered + 1)
    weed = is_plant & (unwatered >= 2) & em
    still = is_plant & (~weed) & em
    st.unwatered = torch.where(still, unwatered, st.unwatered)
    st.watered = torch.where(still, torch.zeros_like(st.watered), st.watered)
    _become_weed(st, weed)

    cid = st.crop.clamp(min=0).long()
    ongoing = T.crop_ongoing[cid] & still
    first = T.crop_first[cid]
    interval = T.crop_interval[cid].clamp(min=1)
    planted = st.planted_day.to(torch.int32)
    dsf = (day + 1) - planted - first
    due = ongoing & (dsf >= 0) & ((dsf % interval) == 0)
    prod_count = dsf // interval + 1
    maxy = T.crop_max_yield[cid]
    due = due & (prod_count <= maxy.to(torch.int32))
    ferted = was_watered & (st.fert_until.to(torch.int32) >= st.day.to(torch.int32)[:, None, None, None])
    add = torch.where(ferted, 2, 1).to(st.yield_units.dtype)
    st.yield_units = torch.where(due, torch.minimum(st.yield_units + add, maxy), st.yield_units)
    last = due & (prod_count == maxy.to(torch.int32))
    life = (st.day.to(torch.int32) + 2) * C.TURNS_PER_DAY  # (next_day+1)*24
    st.max_life = torch.where(last, life[:, None, None, None].to(st.max_life.dtype), st.max_life)

    # animals
    has_a = st.animal >= 0
    unfed = torch.where(st.fed, torch.zeros_like(st.unfed), st.unfed + 1)
    escape = has_a & (unfed >= 2) & em
    aid = st.animal.clamp(min=0).long()
    struct = T.animal_struct[aid]
    st.kind = torch.where(escape, struct, st.kind)
    st.animal = torch.where(escape, torch.full_like(st.animal, -1), st.animal)
    st.yield_units = torch.where(escape, torch.zeros_like(st.yield_units), st.yield_units)
    stay = has_a & (~escape) & em
    st.unfed = torch.where(stay, unfed, torch.where(escape, torch.zeros_like(unfed), st.unfed))

    first_a = T.animal_first[aid]
    ivl = T.animal_interval[aid].clamp(min=1)
    placed = st.placed_day.to(torch.int32)
    dsf_a = (day + 1) - placed - first_a
    produce = stay & (dsf_a >= 0) & ((dsf_a % ivl) == 0)
    bonus = torch.where(st.fed, st.pending_care, torch.zeros_like(st.pending_care))
    add_a = (1 + bonus).to(st.yield_units.dtype)
    held = T.animal_max_held[aid]
    st.yield_units = torch.where(produce, torch.minimum(st.yield_units + add_a, held), st.yield_units)
    st.pending_care = torch.where(produce, torch.zeros_like(st.pending_care), st.pending_care)
    care_bonus = stay & st.cared & st.fed
    st.pending_care = torch.where(care_bonus, st.pending_care + 1, st.pending_care)
    st.fert_avail = torch.where(stay, torch.ones_like(st.fert_avail), st.fert_avail)
    st.fed = torch.where(stay | escape, torch.zeros_like(st.fed), st.fed)
    st.cared = torch.where(stay | escape, torch.zeros_like(st.cared), st.cared)

    # weeds + shop unlock use the official Random((seed * 1_000_003) ^ day)
    # stream: farm 0 empty tiles (y,x), farm 1 empty tiles, then rng.choice(shops).
    _official_weeds_and_shops(st, eod)

    # drop inventories into shed (dict insertion order; overflow discarded)
    n_u = _n_live_units(st)
    for u in range(n_u):
        _deposit_inv(st, u, emp.expand(B, C.N_PLAYER))
    inv_m = eod[:, None, None, None]
    st.inv = torch.where(inv_m, torch.zeros_like(st.inv), st.inv)
    st.inv_ord = torch.where(inv_m, torch.full_like(st.inv_ord, -1), st.inv_ord)
    st.inv_next = torch.where(eod[:, None, None], torch.zeros_like(st.inv_next), st.inv_next)

    # fire hands, reset farmer
    st.farmer_xy[..., 0] = torch.where(emp, T.spawn[0], st.farmer_xy[..., 0])
    st.farmer_xy[..., 1] = torch.where(emp, T.spawn[1], st.farmer_xy[..., 1])
    hm = eod[:, None, None, None]
    st.hand_xy = torch.where(hm, torch.zeros_like(st.hand_xy), st.hand_xy)
    st.n_hands = torch.where(emp, torch.zeros_like(st.n_hands), st.n_hands)
    st.hires_today = torch.where(emp, torch.zeros_like(st.hires_today), st.hires_today)


_SHOP_NAMES = list(C.SHOP_NAMES)


def _official_weeds_and_shops(st: TensorState, eod=None):
    """Match interpreter _spawn_weeds + shop draw: Random((seed * 1_000_003) ^ day).

    Only the empty-tile mask and tiny shop vectors cross the host. Weed writes
    go back with index_put; the rest of `kind` stays on device.
    """
    B = st.batch_size()
    device = st.kind.device
    empty_np = (st.kind == C.K_EMPTY).detach().cpu().numpy()
    seeds_np = st.seed.detach().cpu().numpy()
    days_np = st.day.detach().cpu().numpy()
    n_shops_np = st.n_shops.detach().cpu().numpy().copy()
    if eod is None:
        eod_np = np.ones(B, dtype=bool)
    else:
        eod_np = np.asarray(eod.detach().cpu().numpy(), dtype=bool)
    chance = C.WEED_CHANCE
    weed_b, weed_p, weed_y, weed_x = [], [], [], []
    shop_b, shop_slot, shop_id = [], [], []
    for b in range(B):
        if not eod_np[b]:
            continue
        rng = random.Random((int(seeds_np[b]) * 1_000_003) ^ int(days_np[b]))
        rnd = rng.random
        for p in range(C.N_PLAYER):
            ys, xs = np.nonzero(empty_np[b, p])
            for y, x in zip(ys.tolist(), xs.tolist()):
                if rnd() < chance:
                    weed_b.append(b)
                    weed_p.append(p)
                    weed_y.append(y)
                    weed_x.append(x)
        next_day = int(days_np[b]) + 1
        ns = int(n_shops_np[b])
        if next_day > 0 and next_day % C.SHOP_UNLOCK_EVERY == 0 and ns < C.MAX_SHOPS:
            shop_b.append(b)
            shop_slot.append(ns)
            shop_id.append(C.SHOP_NAMES.index(rng.choice(_SHOP_NAMES)))
            n_shops_np[b] = ns + 1
    if weed_b:
        bb = torch.tensor(weed_b, device=device, dtype=torch.long)
        pp = torch.tensor(weed_p, device=device, dtype=torch.long)
        yy = torch.tensor(weed_y, device=device, dtype=torch.long)
        xx = torch.tensor(weed_x, device=device, dtype=torch.long)
        st.kind[bb, pp, yy, xx] = C.K_WEED
        st.crop[bb, pp, yy, xx] = -1
        st.animal[bb, pp, yy, xx] = -1
        st.planted_day[bb, pp, yy, xx] = 0
        st.placed_day[bb, pp, yy, xx] = 0
        st.yield_units[bb, pp, yy, xx] = 0
        st.watered[bb, pp, yy, xx] = False
        st.unwatered[bb, pp, yy, xx] = 0
        st.fed[bb, pp, yy, xx] = False
        st.unfed[bb, pp, yy, xx] = 0
        st.cared[bb, pp, yy, xx] = False
        st.fert_avail[bb, pp, yy, xx] = False
        st.fert_until[bb, pp, yy, xx] = -1
        st.pending_care[bb, pp, yy, xx] = 0
        st.max_life[bb, pp, yy, xx] = -1
    if shop_b:
        bb = torch.tensor(shop_b, device=device, dtype=torch.long)
        ss = torch.tensor(shop_slot, device=device, dtype=torch.long)
        sid = torch.tensor(shop_id, device=device, dtype=st.shops.dtype)
        st.shops[bb, ss] = sid
        st.n_shops.copy_(
            torch.from_numpy(n_shops_np).to(device=device, dtype=st.n_shops.dtype)
        )


def step(st: TensorState, act: Actions, T: Tables) -> TensorState:
    """Advance every live env by one turn. Mutates `st` and `act` (plant blocking).

    Unit shed/tile ops stay a short loop over live workers (shared shed and
    same-tile writes are sequential, like market slots). Moves, market ticks,
    town, and decay are batched on B.
    """
    attach_price_table(T)
    _block_overplant(st, act)
    _apply_moves_all(st, act, T)
    n_u = _n_live_units(st)
    alive_all = all_unit_alive(st, n_u)
    for u in range(n_u):
        alive = alive_all[:, :, u]
        _apply_shed_ops(st, act, u, T, alive)
        _apply_tile_ops(st, act, u, T, alive)
    _process_market(st, act, T)
    _town_consume(st, T)
    _decay_plants(st)
    cpu_step = getattr(st, "cpu_step", 0)
    if ((cpu_step + 1) % C.TURNS_PER_DAY) == 0:
        eod = torch.ones(st.batch_size(), dtype=torch.bool, device=st.device())
        _end_of_day(st, T, eod)
        st.cpu_max_hands = 0
    st.cpu_step = cpu_step + 1
    st.step = st.step + 1
    st.day = st.step // C.TURNS_PER_DAY
    st.hour = st.step % C.TURNS_PER_DAY
    st.done = st.step >= C.DONE_STEP
    return st
