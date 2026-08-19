"""Vectorized task → engine Actions (training decoder).

IDLE falls through to a barnyard-style priority scheduler so a scripted
opponent of all-IDLE + RESTOCK is already a reasonable farmer.
"""

import torch

from . import constants as C
from .state import Actions, empty_actions, gather_hw, unit_xy
from .tables import Tables
from .engine import quote_market


def _step_toward(fx, fy, tx, ty):
    ax = (tx - fx).abs()
    ay = (ty - fy).abs()
    use_x = (fx != tx) & (ax >= ay)
    op = torch.zeros_like(fx, dtype=torch.int16)
    op = torch.where(use_x & (tx > fx), torch.full_like(op, C.OP_EAST), op)
    op = torch.where(use_x & (tx < fx), torch.full_like(op, C.OP_WEST), op)
    use_y = (~use_x) & (fy != ty)
    op = torch.where(use_y & (ty > fy), torch.full_like(op, C.OP_SOUTH), op)
    op = torch.where(use_y & (ty < fy), torch.full_like(op, C.OP_NORTH), op)
    use_x2 = (~use_x) & (~use_y) & (fx != tx)
    op = torch.where(use_x2 & (tx > fx), torch.full_like(op, C.OP_EAST), op)
    op = torch.where(use_x2 & (tx < fx), torch.full_like(op, C.OP_WEST), op)
    return op


def _nearest(mask, xy, T: Tables):
    """mask [B,2,H,W], xy [B,2,2] -> tx, ty, found [B,2]."""
    dist = (T.xx - xy[..., 0, None, None]).abs() + (T.yy - xy[..., 1, None, None]).abs()
    dist = dist.masked_fill(~mask, 10_000)
    flat = dist.reshape(xy.shape[0], C.N_PLAYER, -1)
    best = flat.argmin(-1)
    found = torch.gather(flat, -1, best.unsqueeze(-1)).squeeze(-1) < 9_999
    tx = best % C.BOARD
    ty = best // C.BOARD
    return tx, ty, found


def _unit_dist(xy, T: Tables):
    """Manhattan distance from xy [B,2] to every tile -> [B,H,W]."""
    xx = T.xx.view(1, 1, C.BOARD)
    yy = T.yy.view(1, C.BOARD, 1)
    return (xx - xy[:, 0, None, None]).abs() + (yy - xy[:, 1, None, None]).abs()


def _unit_dist_units(xy, T: Tables):
    """xy [B,U,2] -> dist [B,U,H,W]."""
    xx = T.xx.view(1, 1, 1, C.BOARD)
    yy = T.yy.view(1, 1, C.BOARD, 1)
    return (xx - xy[..., 0, None, None]).abs() + (yy - xy[..., 1, None, None]).abs()


def _nearest_from_dist(mask, dist):
    """mask [B,H,W], dist [B,H,W] -> tx, ty, found [B]."""
    flat = dist.masked_fill(~mask, 10_000).reshape(dist.shape[0], -1)
    best = flat.argmin(-1)
    found = torch.gather(flat, 1, best.unsqueeze(1)).squeeze(1) < 9_999
    return best % C.BOARD, best // C.BOARD, found


def _nearest_stack(mask, dist):
    """mask [B,K,H,W], dist [B,H,W] -> tx, ty, found [B,K]. One argmin for K tasks."""
    B, K = mask.shape[:2]
    flat = dist.unsqueeze(1).masked_fill(~mask, 10_000).reshape(B, K, -1)
    best = flat.argmin(-1)
    found = torch.gather(flat, -1, best.unsqueeze(-1)).squeeze(-1) < 9_999
    return best % C.BOARD, best // C.BOARD, found


def _nearest_player(mask, xy, T: Tables):
    """mask [B,H,W], xy [B,2] -> tx, ty, found [B]. No dummy two-player tensors."""
    return _nearest_from_dist(mask, _unit_dist(xy, T))


def _claim(mask, tx, ty, claimed):
    b, p = tx.shape
    bb = torch.arange(b, device=tx.device)[:, None].expand(b, p)
    pp = torch.arange(p, device=tx.device)[None, :].expand(b, p)
    x = tx.clamp(0, C.BOARD - 1)
    y = ty.clamp(0, C.BOARD - 1)
    mask[bb, pp, y, x] = mask[bb, pp, y, x] & (~claimed)


def _claim_player(mask, tx, ty, ok):
    """mask [B,H,W]: clear claimed tiles in-place."""
    b = torch.arange(tx.shape[0], device=tx.device)
    x = tx.clamp(0, C.BOARD - 1)
    y = ty.clamp(0, C.BOARD - 1)
    mask[b, y, x] = mask[b, y, x] & (~ok)


def _walk_or_do(fx, fy, tx, ty, found, do_op, do_arg=None, do_qty=None):
    op = torch.zeros_like(fx, dtype=torch.int16)
    arg = torch.zeros_like(fx, dtype=torch.int16)
    qty = torch.zeros_like(fx, dtype=torch.int16)
    here = found & (fx == tx) & (fy == ty)
    walk = found & (~here)
    op = torch.where(here, do_op.to(op.dtype), op)
    op = torch.where(walk, _step_toward(fx, fy, tx, ty), op)
    if do_arg is not None:
        arg = torch.where(here, do_arg.to(arg.dtype), arg)
    if do_qty is not None:
        qty = torch.where(here, do_qty.to(qty.dtype), qty)
    return op, arg, qty, found


def _task_masks(st, T: Tables):
    is_plant = st.kind == C.K_PLANT
    cid = st.crop.clamp(min=0).long()
    day = st.day.to(torch.int32)[:, None, None, None]
    age = day - st.planted_day.to(torch.int32)
    water = is_plant & (~st.watered) & (st.unwatered < 2)
    harvest_p = is_plant & (st.yield_units > 0) & (age >= T.crop_first[cid])
    harvest_a = (st.animal >= 0) & (st.yield_units > 0)
    harvest = harvest_p | harvest_a
    feed = (st.animal >= 0) & (~st.fed)
    care = (st.animal >= 0) & (~st.cared)
    collect = (st.animal >= 0) & st.fert_avail
    dig = st.kind == C.K_WEED
    empty = st.kind == C.K_EMPTY
    empty_pasture = (st.kind == C.K_PASTURE) & (st.animal < 0)
    empty_coop = (st.kind == C.K_COOP) & (st.animal < 0)
    return {
        "water": water, "harvest": harvest, "feed": feed, "care": care,
        "collect": collect, "dig": dig, "empty": empty,
        "empty_pasture": empty_pasture, "empty_coop": empty_coop,
    }


def _task_key(task):
    # map task id -> mask name and plant crop
    plant_crop = torch.where(
        (task >= C.TASK_PLANT0) & (task < C.TASK_PLANT0 + C.N_CROP),
        task - C.TASK_PLANT0,
        torch.full_like(task, -1),
    )
    return plant_crop


def decode_tasks(st, tasks, player, T: Tables, market_mode=None) -> Actions:
    """Decode [B, 14] (farmer + 12 hands + mode) for one player into Actions.

    The unit loop is required: later workers claim tiles the earlier ones
    targeted. PLACE / pickup-animal are batched inside each iteration.
    """
    B = st.batch_size()
    device = st.device()
    act = empty_actions(B, device)
    p = int(player)
    tasks = tasks.long()
    n_policy = 1 + C.HAND_CAP
    unit_tasks = tasks[:, :n_policy]
    mode = tasks[:, n_policy] if tasks.shape[1] > n_policy else torch.full(
        (B,), C.MODE_RESTOCK, device=device, dtype=torch.int64)
    if market_mode is not None:
        mode = torch.full((B,), int(market_mode), device=device, dtype=torch.int64)
    mode = torch.where(st.step >= 714, torch.full_like(mode, C.MODE_DUMP), mode)

    masks = _task_masks(st, T)
    # per-player slices of masks we will claim
    claimed = {k: v.clone() for k, v in masks.items()}

    n_hands = st.n_hands[:, p]
    farmer = st.farmer_xy[:, p, :]
    hands = st.hand_xy[:, p, :, :]
    inv_all = st.inv[:, p, :, :]  # [B, 13, 12]
    shed = st.shed[:, p, :]
    seeds = st.seeds[:, p, :]

    # cpu_max_hands is updated from market HIRE without reading GPU n_hands.
    n_live = min(n_policy, 1 + int(getattr(st, "cpu_max_hands", 0)))

    xy_all = torch.zeros(B, n_live, 2, dtype=farmer.dtype, device=device)
    xy_all[:, 0] = farmer
    if n_live > 1:
        xy_all[:, 1:] = hands[:, :n_live - 1, :]
    dist_all = _unit_dist_units(xy_all, T)
    live_all = torch.ones(B, n_live, dtype=torch.bool, device=device)
    if n_live > 1:
        live_all[:, 1:] = n_hands[:, None] > torch.arange(n_live - 1, device=device)

    plant_priority = [4, 3, 0, 1, 2]  # melon, strawberry, wheat, carrot, tomato
    cows = shed[:, C.ANIMAL_SHED0] + shed[:, C.ANIMAL_SHED0 + 1]
    geese = shed[:, C.ANIMAL_SHED0 + 2]
    shed_x0 = T.shed_x[0].expand(B)
    shed_y0 = T.shed_y[0].expand(B)

    _k = ("water", "harvest", "feed", "care", "collect", "dig", "empty")
    spec_ki = torch.tensor(
        [0, 1, 2, 3, 4, 5, 6, 6, 6, 6, 6, 6, 6,
         0, 1, 3, 2, 4, 6, 6, 6, 6, 6, 5, 6, 6],
        device=device, dtype=torch.int64)
    spec_op = torch.tensor(
        [C.OP_WATER, C.OP_HARVEST, C.OP_FEED, C.OP_CARE, C.OP_COLLECT, C.OP_DIG,
         C.OP_PLANT, C.OP_PLANT, C.OP_PLANT, C.OP_PLANT, C.OP_PLANT,
         C.OP_BUILD_PASTURE, C.OP_BUILD_COOP,
         C.OP_WATER, C.OP_HARVEST, C.OP_CARE, C.OP_FEED, C.OP_COLLECT,
         C.OP_PLANT, C.OP_PLANT, C.OP_PLANT, C.OP_PLANT, C.OP_PLANT,
         C.OP_DIG, C.OP_BUILD_PASTURE, C.OP_BUILD_COOP],
        device=device, dtype=torch.int16)
    spec_arg = torch.tensor(
        [-1, -1, -1, -1, -1, -1, 0, 1, 2, 3, 4, -1, -1,
         -1, -1, -1, -1, -1, 4, 3, 0, 1, 2, -1, -1, -1],
        device=device, dtype=torch.int16)

    ops = torch.zeros(B, n_policy, dtype=torch.int16, device=device)
    args = torch.zeros(B, n_policy, dtype=torch.int16, device=device)
    qtys = torch.zeros(B, n_policy, dtype=torch.int16, device=device)
    pasture = claimed["empty_pasture"]
    coop = claimed["empty_coop"]

    for u in range(n_live):
        live = live_all[:, u]
        xy = xy_all[:, u]
        fx, fy = xy[:, 0], xy[:, 1]
        dist = dist_all[:, u]
        task = unit_tasks[:, u]
        inv = inv_all[:, u, :]
        assigned = torch.zeros(B, dtype=torch.bool, device=device)

        def nearest_p(mask_bp):
            return _nearest_from_dist(mask_bp[:, p], dist)

        def claim_p(mask_bp, tx, ty, ok):
            _claim_player(mask_bp[:, p], tx, ty, ok)

        # carrying animal → PLACE on empty matching structure (first of cow/sheep/goose)
        inv_a = inv[:, C.ANIMAL_SHED0:C.ANIMAL_SHED0 + C.N_ANIMAL] > 0
        has_c = inv_a.any(-1)
        carrying = inv_a.to(torch.int64).argmax(-1)
        struct_mask = torch.where(
            (carrying == 2)[:, None, None, None], coop, pasture)
        struct_mask = torch.where(has_c[:, None, None, None], struct_mask,
                                  torch.zeros_like(struct_mask))
        tx, ty, found = nearest_p(struct_mask)
        do = live & has_c & found & (~assigned)
        dop = torch.full((B,), C.OP_PLACE, dtype=torch.int16, device=device)
        darg = (carrying + C.ANIMAL_SHED0).to(torch.int16)
        dqty = torch.ones(B, dtype=torch.int16, device=device)
        o, a, q, ok = _walk_or_do(fx, fy, tx, ty, do, dop, darg, dqty)
        ops[:, u] = torch.where(ok, o, ops[:, u])
        args[:, u] = torch.where(ok, a, args[:, u])
        qtys[:, u] = torch.where(ok, q, qtys[:, u])
        assigned = assigned | ok
        claim_p(claimed["empty_pasture"], tx, ty, ok & (carrying != 2))
        claim_p(claimed["empty_coop"], tx, ty, ok & (carrying == 2))

        # FEED without wheat: walk to shed / PICKUP
        need_feed = live & (~assigned) & (
            (task == C.TASK_FEED) | ((task == C.TASK_IDLE) & claimed["feed"][:, p].any(dim=(-1, -2)))
        )
        no_wheat = inv[:, C.WHEAT_SLOT] <= 0
        shed_w = shed[:, C.WHEAT_SLOT] > 0
        go_pickup = need_feed & no_wheat & shed_w
        at_shed = ((fx[:, None] == T.shed_x) & (fy[:, None] == T.shed_y)).any(-1)
        pk = go_pickup & at_shed
        ops[:, u] = torch.where(pk, torch.full_like(ops[:, u], C.OP_PICKUP), ops[:, u])
        args[:, u] = torch.where(pk, torch.full_like(args[:, u], C.WHEAT_SLOT), args[:, u])
        take = torch.minimum(shed[:, C.WHEAT_SLOT], torch.full_like(shed[:, C.WHEAT_SLOT], 8)).to(torch.int16)
        qtys[:, u] = torch.where(pk, take, qtys[:, u])
        assigned = assigned | pk
        walk_s = go_pickup & (~at_shed)
        ops[:, u] = torch.where(walk_s, _step_toward(fx, fy, shed_x0, shed_y0), ops[:, u])
        assigned = assigned | walk_s

        # pickup animals from shed if idle and housing exists (first matching kind)
        want_pickup_a = live & (~assigned) & (task == C.TASK_IDLE)
        has_h = torch.stack((
            claimed["empty_pasture"][:, p].any(dim=(-1, -2)),
            claimed["empty_pasture"][:, p].any(dim=(-1, -2)),
            claimed["empty_coop"][:, p].any(dim=(-1, -2)),
        ), dim=-1)
        in_shed = shed[:, C.ANIMAL_SHED0:C.ANIMAL_SHED0 + C.N_ANIMAL] > 0
        go_a = want_pickup_a[:, None] & has_h & in_shed
        first_a = go_a & (go_a.to(torch.int32).cumsum(1) == 1)
        pk_a = first_a & at_shed[:, None]
        ws_a = first_a & (~at_shed[:, None])
        which = first_a.to(torch.int64).argmax(-1)
        any_pk = pk_a.any(-1)
        any_ws = ws_a.any(-1)
        ops[:, u] = torch.where(any_pk, torch.full_like(ops[:, u], C.OP_PICKUP), ops[:, u])
        args[:, u] = torch.where(
            any_pk, (which + C.ANIMAL_SHED0).to(args.dtype), args[:, u])
        qtys[:, u] = torch.where(any_pk, torch.ones_like(qtys[:, u]), qtys[:, u])
        assigned = assigned | any_pk
        ops[:, u] = torch.where(any_ws, _step_toward(fx, fy, shed_x0, shed_y0), ops[:, u])
        assigned = assigned | any_ws

        # One argmin for 7 masks, then pick the first matching task (explicit
        # then IDLE). Claims only the chosen tile; later units see updated masks.
        stack = torch.stack([claimed[k][:, p] for k in _k], dim=1)
        ntx, nty, nfound = _nearest_stack(stack, dist)
        explicit = task != C.TASK_IDLE
        idle = live & (~assigned) & (task == C.TASK_IDLE)
        has_w = inv[:, C.WHEAT_SLOT] > 0
        n_past = claimed["empty_pasture"][:, p].sum(dim=(-1, -2))
        n_coop = claimed["empty_coop"][:, p].sum(dim=(-1, -2))
        need_p = cows > n_past
        need_c = geese > n_coop
        pe = explicit[:, None] & (
            task[:, None] == (C.TASK_PLANT0 + torch.arange(C.N_CROP, device=device))
        ) & (seeds > 0)
        pi = idle[:, None] & (seeds[:, plant_priority] > 0)
        conds = torch.stack((
            explicit & (task == C.TASK_WATER),
            explicit & (task == C.TASK_HARVEST),
            explicit & (task == C.TASK_FEED) & has_w,
            explicit & (task == C.TASK_CARE),
            explicit & (task == C.TASK_COLLECT),
            explicit & (task == C.TASK_DIG),
            pe[:, 0], pe[:, 1], pe[:, 2], pe[:, 3], pe[:, 4],
            explicit & (task == C.TASK_BUILD) & need_p,
            explicit & (task == C.TASK_BUILD) & need_c & (~need_p),
            idle,
            idle,
            idle,
            idle & has_w,
            idle,
            pi[:, 0], pi[:, 1], pi[:, 2], pi[:, 3], pi[:, 4],
            idle,
            idle & need_p,
            idle & need_c,
        ), dim=1)
        conds = live[:, None] & (~assigned[:, None]) & conds & nfound.gather(
            1, spec_ki.view(1, -1).expand(B, -1))
        first = conds & (conds.int().cumsum(1) == 1)
        has = first.any(dim=1)
        sel = first.long().argmax(dim=1)
        ch = spec_ki[sel]
        tx = ntx.gather(1, ch.unsqueeze(1)).squeeze(1)
        ty = nty.gather(1, ch.unsqueeze(1)).squeeze(1)
        arg_s = spec_arg[sel]
        o, a, q, ok = _walk_or_do(
            fx, fy, tx, ty, has, spec_op[sel],
            torch.where(arg_s >= 0, arg_s, torch.zeros_like(arg_s)),
        )
        a = torch.where(arg_s >= 0, a, torch.zeros_like(a))
        ops[:, u] = torch.where(ok, o, ops[:, u])
        args[:, u] = torch.where(ok, a, args[:, u])
        assigned = assigned | ok
        for ki_i, name in enumerate(_k):
            claim_p(claimed[name], tx, ty, ok & (ch == ki_i))

    act.op[:, p, :n_policy] = ops
    act.arg[:, p, :n_policy] = args
    act.qty[:, p, :n_policy] = qtys
    _fill_market(st, act, mode, p, T)
    return act


def _push(act, p, slot, op, item, qty, mask):
    can = mask & (slot < C.MAX_ORDERS)
    idx = slot.clamp(max=C.MAX_ORDERS - 1)
    B = slot.shape[0]
    bb = torch.arange(B, device=slot.device)
    act.m_op[bb, p, idx] = torch.where(can, op.to(act.m_op.dtype), act.m_op[bb, p, idx])
    act.m_item[bb, p, idx] = torch.where(can, item.to(act.m_item.dtype), act.m_item[bb, p, idx])
    act.m_qty[bb, p, idx] = torch.where(can, qty.to(act.m_qty.dtype), act.m_qty[bb, p, idx])
    return slot + can.long()


def _fill_market(st, act: Actions, mode, p, T: Tables):
    B = st.batch_size()
    device = st.device()
    slot = torch.zeros(B, dtype=torch.int64, device=device)
    shed = st.shed[:, p, :]
    seeds = st.seeds[:, p, :]
    money = st.money[:, p]
    day = st.day
    hour = st.hour
    prices = quote_market(st, T)
    n_animals = (st.animal[:, p] >= 0).sum(dim=(-1, -2))
    planted = torch.stack([(st.kind[:, p] == C.K_PLANT) & (st.crop[:, p] == c)
                           for c in range(C.N_CROP)], dim=-1).sum(dim=(1, 2))  # [B,5]
    empty_n = (st.kind[:, p] == C.K_EMPTY).sum(dim=(-1, -2))
    n_extra = st.unlocked[:, p].to(torch.int64).sum(-1) - 1
    hires = st.hires_today[:, p].to(torch.int64)
    shed_total = shed.sum(-1)
    endgame = (day >= 28) | (st.step >= 680)
    dump = (mode == C.MODE_DUMP) | endgame
    hold = (mode == C.MODE_HOLD) & (~endgame)
    metered = (mode == C.MODE_METERED) | ((mode == C.MODE_RESTOCK) & ((day >= 6) | (shed_total >= 12)))
    restock = mode == C.MODE_RESTOCK

    def sell_item(i, qty_cap, mask):
        nonlocal slot
        held = shed[:, i]
        cap = qty_cap if torch.is_tensor(qty_cap) else torch.full_like(held, qty_cap)
        q = torch.minimum(held, cap)
        ok = mask & (q > 0) & (~hold)
        slot = _push(act, p, slot,
                     torch.full((B,), C.M_SELL, device=device, dtype=torch.int16),
                     torch.full((B,), i, device=device, dtype=torch.int16),
                     q.to(torch.int16), ok)

    # DUMP / METERED sells. Cap is per-env — do not use dump.any() (GPU sync
    # plus it forced every env in the batch to sell 80 when one dumped).
    for i in range(C.N_PRODUCT):
        cap = torch.where(dump, shed[:, i], torch.full_like(shed[:, i], 8))
        wheat_keep = torch.minimum(
            torch.full_like(n_animals, 28), n_animals * 2)
        if i == C.WHEAT_SLOT:
            held = (shed[:, i] - torch.where(endgame, torch.zeros_like(wheat_keep), wheat_keep)).clamp(min=0)
            cap = torch.minimum(cap, held)
        floor = T.base_price[i] * (0.0 if i == C.FERT_SLOT else 0.50)
        ok_price = prices[:, i] >= floor
        sell_item(i, cap, (dump | metered) & ok_price)

    # RESTOCK buys
    spend = torch.zeros(B, dtype=torch.float32, device=device)

    def afford(cost):
        return money - spend >= cost

    for c, target, last in ((4, 14, 18), (3, 14, 18), (0, 20, 26)):
        have = planted[:, c] + seeds[:, c]
        need = (target - have).clamp(min=0)
        k = torch.minimum(need, torch.full_like(need, 4))
        k = torch.minimum(k, empty_n.clamp(max=8))
        cost1 = T.seed_cost[c]
        keep = torch.where(day <= 2, torch.full_like(money, 400), torch.full_like(money, 100))
        while_k = k.clone()
        # shrink k until affordable (vectorized by looping 4)
        for _ in range(4):
            too_much = ~afford(cost1 * while_k.to(money.dtype) + keep) & (while_k > 0)
            while_k = torch.where(too_much, while_k - 1, while_k)
        ok = restock & (~endgame) & (day <= last) & (while_k > 0)
        slot = _push(act, p, slot,
                     torch.full((B,), C.M_BUY_SEED, device=device, dtype=torch.int16),
                     torch.full((B,), c, device=device, dtype=torch.int16),
                     while_k.to(torch.int16), ok)
        spend = spend + torch.where(ok, cost1 * while_k.to(money.dtype), torch.zeros_like(spend))

    # hire (hour <= 3)
    hire_ok = restock & (~endgame) & (hour <= 3) & (hires < C.HAND_CAP)
    budget = money * 0.06
    for _ in range(7):
        cost = T.hire_fib[hires.clamp(0, len(C.HIRE_FIB) - 1)]
        ok = hire_ok & (hires < C.HAND_CAP) & afford(cost + 40) & (cost <= budget)
        slot = _push(act, p, slot,
                     torch.full((B,), C.M_HIRE, device=device, dtype=torch.int16),
                     torch.zeros(B, dtype=torch.int16, device=device),
                     torch.ones(B, dtype=torch.int16, device=device), ok)
        spend = spend + torch.where(ok, cost, torch.zeros_like(spend))
        hires = hires + ok.long()

    # land
    can_land = restock & (~endgame) & (n_extra < 3) & (empty_n <= 8)
    price = T.land_prices[n_extra.clamp(0, 2)]
    reserve = torch.tensor([600.0, 1500.0, 3000.0], device=device)[n_extra.clamp(0, 2)]
    ok = can_land & afford(price + reserve)
    slot = _push(act, p, slot,
                 torch.full((B,), C.M_BUY_LAND, device=device, dtype=torch.int16),
                 torch.zeros(B, dtype=torch.int16, device=device),
                 torch.ones(B, dtype=torch.int16, device=device), ok)
    spend = spend + torch.where(ok, price, torch.zeros_like(spend))

    # animals
    placed = torch.stack([(st.animal[:, p] == a).sum(dim=(-1, -2)) for a in range(C.N_ANIMAL)], dim=-1)
    waiting = shed[:, C.ANIMAL_SHED0:C.ANIMAL_SHED0 + 3]
    owned = placed + waiting
    targets = torch.tensor([10, 8, 4], device=device)
    want = torch.full((B,), -1, dtype=torch.int64, device=device)
    want = torch.where(owned[:, 0] < targets[0], torch.zeros_like(want), want)
    want = torch.where((want < 0) & (owned[:, 1] < targets[1]), torch.ones_like(want), want)
    want = torch.where((want < 0) & (owned[:, 2] < targets[2]) & (day >= 16),
                       torch.full_like(want, 2), want)
    cost_a = torch.where(want >= 0, T.animal_cost[want.clamp(min=0)], torch.zeros(B, device=device))
    keep_a = torch.where(day < 12, torch.full_like(money, 100), torch.full_like(money, 400))
    ok = restock & (~endgame) & (day <= 23) & (want >= 0) & afford(cost_a + keep_a) & (waiting.sum(-1) < 2)
    slot = _push(act, p, slot,
                 torch.full((B,), C.M_BUY_ANIMAL, device=device, dtype=torch.int16),
                 want.clamp(min=0).to(torch.int16),
                 torch.ones(B, dtype=torch.int16, device=device), ok)

    # wheat for animals
    need_w = torch.minimum(torch.full_like(n_animals, 28), n_animals.clamp(min=1) * 2)
    short = shed[:, C.WHEAT_SLOT] < need_w
    k = torch.minimum((need_w - shed[:, C.WHEAT_SLOT]).clamp(min=0), torch.full_like(need_w, 10))
    wprice = prices[:, C.WHEAT_SLOT]
    ok = restock & (~endgame) & (n_animals > 0) & short & afford(wprice * k.to(money.dtype) + 150)
    slot = _push(act, p, slot,
                 torch.full((B,), C.M_BUY_PRODUCT, device=device, dtype=torch.int16),
                 torch.zeros(B, dtype=torch.int16, device=device),
                 k.to(torch.int16), ok)


def decode_starter(st, player, T: Tables) -> Actions:
    """Official starter: carrot loop, farmer only."""
    B = st.batch_size()
    device = st.device()
    p = int(player)
    act = empty_actions(B, device)
    xy = st.farmer_xy[:, p, :]
    kind = gather_hw(st.kind[:, p], xy)
    crop = gather_hw(st.crop[:, p], xy)
    planted = gather_hw(st.planted_day[:, p], xy)
    watered = gather_hw(st.watered[:, p], xy)
    age = st.day.to(torch.int32) - planted.to(torch.int32)
    seeds_c = st.seeds[:, p, 1]
    shed_c = st.shed[:, p, 1]
    money = st.money[:, p]

    # market: sell carrots, buy carrot seed
    sell = shed_c > 0
    act.m_op[:, p, 0] = torch.where(sell, torch.full_like(act.m_op[:, p, 0], C.M_SELL), act.m_op[:, p, 0])
    act.m_item[:, p, 0] = torch.where(sell, torch.ones_like(act.m_item[:, p, 0]), act.m_item[:, p, 0])
    act.m_qty[:, p, 0] = torch.where(sell, shed_c.to(torch.int16), act.m_qty[:, p, 0])
    buy = (seeds_c == 0) & (money >= 20)
    slot = sell.long()  # 0 or 1
    bb = torch.arange(B, device=device)
    act.m_op[bb, p, slot] = torch.where(buy, torch.full((B,), C.M_BUY_SEED, device=device, dtype=torch.int16),
                                        act.m_op[bb, p, slot])
    act.m_item[bb, p, slot] = torch.where(buy, torch.ones(B, device=device, dtype=torch.int16),
                                          act.m_item[bb, p, slot])
    act.m_qty[bb, p, slot] = torch.where(buy, torch.ones(B, device=device, dtype=torch.int16),
                                         act.m_qty[bb, p, slot])

    plant = (kind == C.K_EMPTY) & (seeds_c > 0)
    is_carrot = (kind == C.K_PLANT) & (crop == 1)
    harv = is_carrot & (age >= 3)
    water = is_carrot & (~watered) & (~harv)
    op = torch.zeros(B, dtype=torch.int16, device=device)
    arg = torch.zeros(B, dtype=torch.int16, device=device)
    op = torch.where(plant, torch.full_like(op, C.OP_PLANT), op)
    arg = torch.where(plant, torch.ones_like(arg), arg)
    op = torch.where(harv, torch.full_like(op, C.OP_HARVEST), op)
    op = torch.where(water, torch.full_like(op, C.OP_WATER), op)
    act.op[:, p, 0] = op
    act.arg[:, p, 0] = arg
    return act


def decode_scripted(st, player, T: Tables) -> Actions:
    """All-IDLE farm + RESTOCK market (default scheduler ≈ barnyard farm)."""
    B = st.batch_size()
    tasks = torch.zeros(B, 1 + C.HAND_CAP + 1, dtype=torch.int64, device=st.device())
    tasks[:, -1] = C.MODE_RESTOCK
    return decode_tasks(st, tasks, player, T)


def merge_actions(a0: Actions, a1: Actions, p0=0, p1=1) -> Actions:
    act = Actions(
        op=a0.op.clone(), arg=a0.arg.clone(), qty=a0.qty.clone(),
        m_op=a0.m_op.clone(), m_item=a0.m_item.clone(), m_qty=a0.m_qty.clone(),
    )
    act.op[:, p1] = a1.op[:, p1]
    act.arg[:, p1] = a1.arg[:, p1]
    act.qty[:, p1] = a1.qty[:, p1]
    act.m_op[:, p1] = a1.m_op[:, p1]
    act.m_item[:, p1] = a1.m_item[:, p1]
    act.m_qty[:, p1] = a1.m_qty[:, p1]
    return act
