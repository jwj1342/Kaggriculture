"""Tensor-state barnyard: agents/barnyard.py transcribed to batched tensor
ops, emitting step_idx-override encodings (B4a's opponent family, grown up).

Barnyard is a priority scheduler over ALL units at once -- feed logistics,
animal placement, builds, metered market -- which the 23x22 macro space
cannot express, so unlike the starter this port bypasses the macro heads
entirely: compute(ep, player) returns the engine's internal unit-op and
market-order encodings, and engine_t_idx.step_idx(..., override=) grafts
them onto one seat while the learner keeps the macro path.

Transcription discipline (the gate is test_barn.py):
  * tunables and tables are read off agents/barnyard.py itself (imported),
    never copied -- one source of truth, pinned by asserts;
  * every ordering the reference relies on is reproduced exactly: task
    construction order (animals, plants, wheat trips, shed animals, place
    pairs, the single build+plant pass over shed-distance-sorted tiles,
    weeds), python's stable sort by priority (unique composite keys),
    nearest-idle-unit ties by unit order, nearest-shed-tile ties by
    _shed_tiles list order, the (value, item-name) descending sell sort,
    ANIMALS dict-iteration order;
  * money arithmetic is float64 in the reference's expression order;
  * prices come from the engine's exact table (_price_at).

The assignment loop is serial over ordered task slots (as the reference
is), batched over lanes, with an all-units-busy early exit -- typically a
few dozen iterations. Correctness first; per-priority batching is a later
optimisation if barnyard-stage batches ever dominate a profile.
"""

import os
import sys

import torch

try:
    from . import engine_np as E
    from . import engine_t as ET
    from . import engine_t_idx as X
except ImportError:                      # flat imports (verify_t.py pattern)
    import engine_np as E
    import engine_t as ET
    import engine_t_idx as X

_RL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RL not in sys.path:
    sys.path.insert(0, _RL)

import actions as A                      # puts agents/ on sys.path
import kg_rules as R

_REPO = os.path.dirname(_RL)
_AG = os.path.join(_REPO, "agents")
if _AG not in sys.path:
    sys.path.insert(0, _AG)
import barnyard as BY                    # the reference: tunables + tables

N = 10
S_MKT = 10
BIG = 1 << 20
i64 = torch.int64
f64 = torch.float64

# ---- pin the reference's tables against the engine's ----------------------
assert list(BY.CROPS) == ET.CROP_NAMES and list(BY.ANIMALS) == ET.ANIMAL_NAMES
assert BY.PRODUCTS == ET.PRODUCTS and BY.LAND_PRICES == list(E.LAND_PRICES)
assert BY.SHED_CAPACITY == 100 and BY.MAX_MARKET_ORDERS == S_MKT
for _c, _d in BY.CROPS.items():
    for _k in ("seed", "first_yield_day", "max_yield_day", "interval",
               "max_yield"):
        assert _d[_k] == R.CROPS[_c][_k], (_c, _k)
for _a, _d in BY.ANIMALS.items():
    for _k in ("cost", "structure", "first_yield_day", "interval", "max_held",
               "product"):
        assert _d[_k] == R.ANIMALS[_a][_k], (_a, _k)
for _i in range(8):
    assert BY._fib(_i) == R._fib(_i)
assert BY._shed_tiles(N) == A._SHED

_ANIMAL_IDX = {a: i for i, a in enumerate(ET.ANIMAL_NAMES)}   # GOOSE, COW, SHEEP
_CROP_IDX = {c: i for i, c in enumerate(ET.CROP_NAMES)}
_WHEAT = ET.WHEAT_I
_ANIMAL_ITEM = [ET.N_MKT + i for i in range(3)]               # ITEMS indices

# unit-op string forms (dict conversion for the gate / step_raw parity)
_OP_STR = {X.U_PASS: ["PASS"], X.U_MOVE_N: ["NORTH"], X.U_MOVE_S: ["SOUTH"],
           X.U_MOVE_E: ["EAST"], X.U_MOVE_W: ["WEST"], X.U_WATER: ["WATER"],
           X.U_HARVEST: ["HARVEST"], X.U_FEED: ["FEED"], X.U_CARE: ["CARE"],
           X.U_COLLECT: ["COLLECT_FERTILIZER"], X.U_DIG: ["DIG"],
           X.U_BUILD_COOP: ["BUILD_COOP"], X.U_BUILD_PASTURE: ["BUILD_PASTURE"],
           X.U_DROP: ["DROP"]}

_TABS = {}


class _BT:
    __slots__ = ("shed_dist", "rank_perm", "rank_inv", "near_shed_tile",
                 "dir_lut", "shed100", "sell_rank", "fib", "fibsum",
                 "crop_first", "crop_maxday", "crop_maxy", "crop_ongoing",
                 "water_max", "crop_seed", "sell_floor", "animal_cap",
                 "animal_cost", "plan_crop", "plan_target", "plan_last",
                 "land_prices", "land_reserve")


def _bt(device):
    key = str(device)
    t = _TABS.get(key)
    if t is not None:
        return t
    t = _BT()
    mk = lambda v: torch.tensor(v, dtype=i64, device=device)
    shed = BY._shed_tiles(N)                       # [(x, y)] x4, list order
    sd = [min(abs(x - sx) + abs(y - sy) for sx, sy in shed)
          for y in range(N) for x in range(N)]
    t.shed_dist = mk(sd)
    order = sorted(range(N * N),
                   key=lambda q: (sd[q], q // N, q % N))       # (dist, y, x)
    t.rank_perm = mk(order)
    inv = [0] * (N * N)
    for r, q in enumerate(order):
        inv[q] = r
    t.rank_inv = mk(inv)
    near = []
    for q in range(N * N):
        x, y = q % N, q // N
        bx, by = min(shed, key=lambda s: BY._dist(x, y, s[0], s[1]))
        near.append(by * N + bx)                    # min() ties: list order
    t.near_shed_tile = mk(near)
    xt = X._tabs(device)
    t.dir_lut = xt.dir_lut
    t.shed100 = xt.shed100
    # sell sort tie-break: reverse tuple sort -- the larger item NAME wins
    names_desc = sorted(BY.PRODUCTS, reverse=True)
    t.sell_rank = mk([len(names_desc) - 1 - names_desc.index(q)
                      for q in BY.PRODUCTS])        # bigger = earlier on ties
    t.fib = mk([BY._fib(i) for i in range(40)])
    fs, acc = [], 0
    for i in range(40):
        fs.append(acc)
        acc += BY._fib(i)
    t.fibsum = mk(fs)
    t.crop_first = mk([BY.CROPS[c]["first_yield_day"] for c in ET.CROP_NAMES])
    t.crop_maxday = mk([BY.CROPS[c]["max_yield_day"] for c in ET.CROP_NAMES])
    t.crop_maxy = mk([BY.CROPS[c]["max_yield"] for c in ET.CROP_NAMES])
    t.crop_ongoing = torch.tensor(
        [BY.CROPS[c]["ongoing"] for c in ET.CROP_NAMES],
        dtype=torch.bool, device=device)
    t.water_max = mk([BY.WATER_MAX.get(c, 0) for c in ET.CROP_NAMES])
    t.crop_seed = mk([BY.CROPS[c]["seed"] for c in ET.CROP_NAMES])
    t.sell_floor = torch.tensor(
        [BY.MARKET_PARAMS[q]["base"] * BY.SELL_FLOOR.get(q, 0.55)
         for q in BY.PRODUCTS], dtype=f64, device=device)
    t.animal_cap = mk([BY.ANIMALS[a]["max_held"] for a in ET.ANIMAL_NAMES])
    t.animal_cost = mk([BY.ANIMALS[a]["cost"] for a in ET.ANIMAL_NAMES])
    t.plan_crop = mk([_CROP_IDX[c] for c, _, _ in BY.CROP_PLAN])
    t.plan_target = mk([tg for _, tg, _ in BY.CROP_PLAN])
    t.plan_last = mk([ld for _, _, ld in BY.CROP_PLAN])
    t.land_prices = mk(BY.LAND_PRICES)
    t.land_reserve = mk([600, 1500, 3000])
    _TABS[key] = t
    return t


def compute(ep, player, want_dicts=False):
    """Barnyard's turn for every lane -> step_idx override encodings.

    want_dicts additionally returns per-lane action dicts in step_raw form
    (the gate compares them against agents/barnyard.py verbatim)."""
    dev = ep.device
    t = _bt(dev)
    B = ep.B
    assert B != N * N, "a batch of exactly 100 lanes is shape-ambiguous here"
    p = player
    day = ep._step // ep.turns_per_day
    hour = ep._step % ep.turns_per_day
    endgame = day >= BY.LIQUIDATE_DAY

    # ---- survey (all (B, 100) unless noted) --------------------------------
    kind = ep.kind[:, p].reshape(B, N * N).long()
    animal = ep.animal[:, p].reshape(B, N * N).long()
    yu = ep.yield_units[:, p].reshape(B, N * N).long()
    planted = ep.planted_day[:, p].reshape(B, N * N).long()
    watered = ep.watered[:, p].reshape(B, N * N)
    thirsty = ep.consec_unwatered[:, p].reshape(B, N * N) >= 1
    fed = ep.fed[:, p].reshape(B, N * N)
    cared = ep.cared[:, p].reshape(B, N * N)
    starving = ep.consec_unfed[:, p].reshape(B, N * N) >= 1
    favail = ep.fert_avail[:, p].reshape(B, N * N)
    crop = ep.crop[:, p].reshape(B, N * N).long()

    has_a = animal >= 0
    aidx = animal.clamp(min=0)
    is_plant = kind == ET.K_PLANT
    is_weed = kind == ET.K_WEED
    is_free = kind == ET.K_EMPTY
    owned = kind != ET.K_LOCKED
    coop_free = (kind == ET.K_COOP) & ~has_a
    past_free = (kind == ET.K_PASTURE) & ~has_a

    money = ep.money[:, p]                             # f64 view (read-only)
    shed = ep.shed[:, p].to(i64)                       # (B, 12)
    seeds = ep.seeds_t[:, p].to(i64)                   # (B, 5)
    H = int(ep.hands_n.max())
    U = 1 + H
    inv = ep.unit_inv[:, p, :U].to(i64)                # (B, U, 12)
    fxy = ep.farmer_xy[:, p].to(i64).unsqueeze(1)
    hxy = ep.hands_xy[:, p, :H].to(i64) if H else fxy[:, :0]
    upos = torch.cat([fxy, hxy], 1)                    # (B, U, 2) [x, y]
    upos_f = upos[..., 1] * N + upos[..., 0]           # (B, U) flat tiles
    u_ar = torch.arange(U, dtype=i64, device=dev).view(1, U)
    active = u_ar <= ep.hands_n[:, p:p + 1].to(i64)
    n_units = 1 + ep.hands_n[:, p].to(i64)

    counts = torch.stack([(has_a & (animal == a)).sum(-1) for a in range(3)], 1)
    crop_counts = torch.stack([(is_plant & (crop == c)).sum(-1)
                               for c in range(5)], 1)
    n_animals = has_a.sum(-1)
    animals_in_shed = shed[:, ET.N_MKT:]
    carried_animals = (inv[:, :, ET.N_MKT:] * active.unsqueeze(-1)).sum(1)
    waiting = animals_in_shed + carried_animals
    n_pending = waiting.sum(-1)
    n_empty_structs = (coop_free | past_free).sum(-1)
    shed_total = shed.sum(-1)
    n_free = is_free.sum(-1)
    n_weeds = is_weed.sum(-1)

    zone_size = torch.minimum(
        owned.sum(-1) - 2,
        torch.clamp(n_animals + n_empty_structs + n_pending + 3, min=4))
    zone_size = zone_size.clamp(max=BY.TARGET_ANIMALS)
    perm = t.rank_perm.view(1, -1).expand(B, -1)
    owned_r = owned.gather(1, perm)
    in_zone_r = owned_r & (owned_r.long().cumsum(1) <= zone_size.view(B, 1))
    zone = torch.zeros_like(owned)
    zone.scatter_(1, perm, in_zone_r)

    # ---- task candidates ----------------------------------------------------
    # columns per candidate batch: (valid, prio, ctr, op, tile, arg, qty,
    # need, kcode); ordering key = prio * 4096 + ctr, unique by construction.
    # kcode: 0 = tile task, 1 = wheat trip (shed errand), 2 = shed animal.
    cand = []
    zeros = torch.zeros((B,), dtype=i64, device=dev)
    tiles_ar = torch.arange(N * N, dtype=i64, device=dev)

    def _norm(v, W, fill=0):
        if v is None:
            return torch.full((B, W), fill, dtype=i64, device=dev)
        if not torch.is_tensor(v):
            return torch.full((B, W), int(v), dtype=i64, device=dev)
        v = v.long()
        if v.dim() == 0:
            return v.view(1, 1).expand(B, W)
        if v.dim() == 2:
            return v.expand(B, W)
        if v.shape[0] == W and W != B:
            return v.view(1, W).expand(B, W)
        return v.view(B, 1).expand(B, W)

    def add(valid, prio, ctr, op, tile=None, arg=0, qty=0, need=-1, kcode=0):
        if valid.dim() == 1:
            valid = valid.view(B, 1)
        W = valid.shape[-1]
        cand.append((valid, _norm(prio, W), _norm(ctr, W), _norm(op, W),
                     _norm(tile, W), _norm(arg, W), _norm(qty, W),
                     _norm(need, W, -1),
                     torch.full((B, W), kcode, dtype=i64, device=dev)))

    shed_wheat0 = shed[:, _WHEAT]
    if not endgame:
        cap = t.animal_cap[aidx]
        feed_prio = torch.where(starving, torch.zeros_like(kind),
                                torch.full_like(kind, 6))
        # A) animals, tile order, five sub-slots each (construction order)
        add(has_a & ~fed, feed_prio, tiles_ar * 5 + 0, X.U_FEED,
            tile=tiles_ar, need=_WHEAT)
        add(has_a & (yu >= cap), 1, tiles_ar * 5 + 1, X.U_HARVEST, tile=tiles_ar)
        add(has_a & favail, 4, tiles_ar * 5 + 2, X.U_COLLECT, tile=tiles_ar)
        add(has_a & ~cared, 7, tiles_ar * 5 + 3, X.U_CARE, tile=tiles_ar)
        add(has_a & (yu > 0) & (yu < cap) & (yu >= cap - 2), 9,
            tiles_ar * 5 + 4, X.U_HARVEST, tile=tiles_ar)

        # B) plants, tile order, two sub-slots
        age = day - planted
        first = t.crop_first[crop]
        ongoing = t.crop_ongoing[crop]
        wmax = t.water_max[crop]
        maxday = t.crop_maxday[crop]
        ripe = (age >= first) & ((yu >= wmax) | (age >= maxday))
        in_window = (((maxday + 1) // 2) <= age) & (age <= maxday)
        melon = crop == _CROP_IDX["MELON"]
        b0_valid = is_plant & torch.where(
            ongoing, ~watered,
            ripe | (~watered & (thirsty | (in_window & (yu < wmax)))))
        b0_op = torch.where(~ongoing & ripe,
                            torch.full_like(kind, X.U_HARVEST),
                            torch.full_like(kind, X.U_WATER))
        p8 = torch.full_like(kind, 8)
        b0_prio = torch.where(
            ongoing, torch.where(thirsty, torch.full_like(kind, 2), p8),
            torch.where(ripe, torch.full_like(kind, 1),
                        torch.where(thirsty, torch.full_like(kind, 2),
                                    torch.where(melon, torch.full_like(kind, 3),
                                                p8))))
        add(b0_valid, b0_prio, 500 + tiles_ar * 2, b0_op, tile=tiles_ar)
        add(is_plant & ongoing & (age >= first) & (yu >= 2), 3,
            500 + tiles_ar * 2 + 1, X.U_HARVEST, tile=tiles_ar)

        # C) wheat trips (shed errands, prio 1)
        carried_wheat = (inv[:, :, _WHEAT] * active).sum(-1)
        unfed_n = (has_a & ~fed).sum(-1)
        gap = unfed_n - carried_wheat
        trips = torch.minimum(n_units, -(-gap // BY.WHEAT_PER_TRIP))
        trips = torch.where((gap > 0) & (shed_wheat0 > 0), trips, zeros)
        take0 = torch.minimum(
            torch.full_like(shed_wheat0, BY.WHEAT_PER_TRIP), shed_wheat0)
        for k in range(16):
            add(trips > k, 1, 700 + k, X.U_PICKUP, arg=_WHEAT, qty=take0,
                kcode=1)

        # D) shed-animal errands (prio 5)
        n_shed_a = animals_in_shed.sum(-1)
        for k in range(24):
            add(n_shed_a > k, 5, 740 + k, X.U_PICKUP, kcode=2)

        # E) PLACE pairs per empty struct: GOOSE for coops; COW then SHEEP
        # for pastures (ANIMALS dict order filtered by structure)
        for mask, a, j in ((coop_free, _ANIMAL_IDX["GOOSE"], 0),
                           (past_free, _ANIMAL_IDX["COW"], 0),
                           (past_free, _ANIMAL_IDX["SHEEP"], 1)):
            add(mask, 5, 800 + tiles_ar * 2 + j, X.U_PLACE, tile=tiles_ar,
                arg=a, need=_ANIMAL_ITEM[a])

        # F+G) one pass over shed-distance-sorted free tiles: zone tiles eat
        # the build queue, the rest take crops in plan order
        free_pasture = past_free.sum(-1)
        free_coop = coop_free.sum(-1)
        need_pasture = (waiting[:, _ANIMAL_IDX["COW"]]
                        + waiting[:, _ANIMAL_IDX["SHEEP"]]
                        - free_pasture).clamp(min=0)
        need_coop = (waiting[:, _ANIMAL_IDX["GOOSE"]] - free_coop).clamp(min=0)
        afford_now = ((money - 300).clamp(min=0.0) // 450).to(i64)
        room = (BY.TARGET_ANIMALS - n_animals - n_empty_structs).clamp(min=0)
        lookahead = (torch.minimum(afford_now, zeros + 4)
                     - need_pasture - need_coop).clamp(min=0)
        plan_pasture = (BY.TARGET_COWS + BY.TARGET_SHEEP
                        - counts[:, _ANIMAL_IDX["COW"]]
                        - counts[:, _ANIMAL_IDX["SHEEP"]]
                        - free_pasture - need_pasture).clamp(min=0)
        qlen = torch.minimum(need_pasture + need_coop + lookahead, room)

        free_r = is_free.gather(1, perm)
        fz_r = free_r & in_zone_r
        fnz_r = free_r & ~in_zone_r
        qidx_r = fz_r.long().cumsum(1) - 1
        la_op = torch.where(plan_pasture > 0,
                            torch.full_like(zeros, X.U_BUILD_PASTURE),
                            torch.full_like(zeros, X.U_BUILD_COOP)).view(B, 1)
        build_op_r = torch.where(
            qidx_r < need_pasture.view(B, 1),
            torch.full_like(qidx_r, X.U_BUILD_PASTURE),
            torch.where(qidx_r < (need_pasture + need_coop).view(B, 1),
                        torch.full_like(qidx_r, X.U_BUILD_COOP), la_op))
        build_valid_r = fz_r & (qidx_r < qlen.view(B, 1))

        want = (t.plan_target.view(1, 3)
                - crop_counts.gather(1, t.plan_crop.view(1, 3).expand(B, 3))
                ).clamp(min=0)
        want = torch.where(t.plan_last.view(1, 3) >= day, want,
                           torch.zeros_like(want))
        kq = torch.minimum(
            want, seeds.gather(1, t.plan_crop.view(1, 3).expand(B, 3)))
        cidx_r = fnz_r.long().cumsum(1) - 1
        k0 = kq[:, 0].view(B, 1)
        k01 = (kq[:, 0] + kq[:, 1]).view(B, 1)
        k012 = (kq[:, 0] + kq[:, 1] + kq[:, 2]).view(B, 1)
        plant_arg_r = torch.where(
            cidx_r < k0, t.plan_crop[0].expand_as(cidx_r),
            torch.where(cidx_r < k01, t.plan_crop[1].expand_as(cidx_r),
                        t.plan_crop[2].expand_as(cidx_r)))
        plant_valid_r = fnz_r & (cidx_r < k012)
        plant_prio_r = torch.where(plant_arg_r == _CROP_IDX["MELON"],
                                   torch.full_like(cidx_r, 6),
                                   torch.full_like(cidx_r, 10))
        rank_of = t.rank_inv.view(1, -1).expand(B, -1)

        def unrank(x_r, fill=0):
            out = torch.full_like(x_r, fill)
            return out.scatter(1, perm, x_r)

        add(unrank(build_valid_r.long()).bool(), 5, 1000 + rank_of,
            unrank(build_op_r), tile=tiles_ar)
        add(unrank(plant_valid_r.long()).bool(), unrank(plant_prio_r),
            1000 + rank_of, X.U_PLANT, tile=tiles_ar, arg=unrank(plant_arg_r))

        # H) weeds
        weed_prio = torch.where(n_free <= n_weeds + 4,
                                torch.full_like(zeros, 6),
                                torch.full_like(zeros, 11))
        add(is_weed, weed_prio.view(B, 1).expand(B, N * N), 1200 + tiles_ar,
            X.U_DIG, tile=tiles_ar)
    else:
        age = day - planted
        first = t.crop_first[crop]
        add(has_a & (yu > 0), 0, tiles_ar * 5, X.U_HARVEST, tile=tiles_ar)
        add(is_plant & (yu > 0) & (age >= first), 0, 500 + tiles_ar * 2,
            X.U_HARVEST, tile=tiles_ar)

    # ---- order candidates by (prio, construction ctr); compact valid -------
    valid = torch.cat([c[0] for c in cand], 1)
    key = torch.cat([c[1] for c in cand], 1) * 4096 \
        + torch.cat([c[2] for c in cand], 1)
    key = torch.where(valid, key, torch.full_like(key, BIG))
    n_valid = int(valid.sum(1).max()) if valid.numel() else 0
    order = key.argsort(1)[:, :n_valid]

    def g(i):
        return torch.cat([c[i] for c in cand], 1).gather(1, order)

    o_valid = valid.gather(1, order)
    o_op, o_tile, o_arg = g(3), g(4), g(5)
    o_qty, o_need, o_kc = g(6), g(7), g(8)

    # ---- serial greedy assignment ------------------------------------------
    busy = ~active                                     # inactive slots = busy
    out_op = torch.full((B, U), X.U_PASS, dtype=i64, device=dev)
    out_arg = torch.zeros((B, U), dtype=i64, device=dev)
    out_qty = torch.zeros((B, U), dtype=i64, device=dev)
    # per-unit INTENT (kickstart teacher labels): the task op a unit was
    # assigned, independent of whether this turn emits the op itself or a
    # move toward its target. Wheat errands count as U_FEED (our FEED hand
    # task owns its own pickup leg), shed-animal errands as U_PLACE,
    # produce runbacks as U_DROP; unassigned stays U_PASS.
    out_task = torch.full((B, U), X.U_PASS, dtype=i64, device=dev)
    out_ta = torch.zeros((B, U), dtype=i64, device=dev)
    claimed = torch.zeros((B, N * N * 18), dtype=torch.bool, device=dev)
    shed_wheat_left = shed_wheat0.clone()
    shed_animals_left = animals_in_shed.clone()
    coop_open = coop_free.any(-1)
    past_open = past_free.any(-1)
    at_shed_u = t.shed100[upos_f]                      # (B, U)
    shed_dist_u = t.shed_dist[upos_f]
    dir_to_shed_u = t.dir_lut[upos_f * (N * N) + t.near_shed_tile[upos_f]]

    for s in range(o_op.shape[1]):
        if s % 4 == 0 and bool(busy.all()):
            break
        live = o_valid[:, s]
        if not bool(live.any()):
            continue
        c_op, c_tile = o_op[:, s], o_tile[:, s]
        c_arg, c_qty = o_arg[:, s], o_qty[:, s]
        c_need, c_kc = o_need[:, s], o_kc[:, s]

        # tile tasks -------------------------------------------------------
        tl = live & (c_kc == 0)
        if bool(tl.any()):
            cl = claimed.gather(1, (c_tile * 18 + c_op).view(B, 1)).squeeze(1)
            tl = tl & ~cl
            need_ok = torch.where(
                (c_need >= 0).view(B, 1),
                inv.gather(2, c_need.clamp(min=0).view(B, 1, 1)
                           .expand(B, U, 1)).squeeze(-1) > 0,
                torch.ones_like(busy))
            elig = ~busy & need_ok & tl.view(B, 1)
            dist = (upos[..., 0] - (c_tile % N).view(B, 1)).abs() \
                + (upos[..., 1] - (c_tile // N).view(B, 1)).abs()
            ukey = torch.where(elig, dist * 64 + u_ar,
                               torch.full_like(dist, BIG))
            kmin, best = ukey.min(1)
            found = tl & (kmin < BIG)
            if bool(found.any()):
                bpos = upos_f.gather(1, best.view(B, 1)).squeeze(1)
                at = bpos == c_tile
                mv = t.dir_lut[bpos * (N * N) + c_tile]
                fb = found
                bi = best[fb]
                out_op[fb, bi] = torch.where(at, c_op, mv)[fb]
                out_arg[fb, bi] = torch.where(at, c_arg,
                                              torch.zeros_like(c_arg))[fb]
                out_qty[fb, bi] = torch.where(at, c_qty,
                                              torch.zeros_like(c_qty))[fb]
                out_task[fb, bi] = c_op[fb]
                out_ta[fb, bi] = c_arg[fb]
                busy[fb, bi] = True
                claimed[fb, (c_tile * 18 + c_op)[fb]] = True

        # shed errands (kcode 1 = wheat trip, 2 = shed animal) ---------------
        for kc in (1, 2):
            sl = live & (c_kc == kc)
            if not bool(sl.any()):
                continue
            if kc == 1:
                pre = inv[:, :, _WHEAT] < BY.WHEAT_PER_TRIP // 2
                sl = sl & (torch.minimum(c_qty, shed_wheat_left) > 0)
            else:
                pre = ~(inv[:, :, ET.N_MKT:] > 0).any(-1)
                sl = sl & (shed_animals_left.sum(-1) > 0)
            elig = ~busy & pre & sl.view(B, 1)
            ukey = torch.where(elig, shed_dist_u * 64 + u_ar,
                               torch.full_like(shed_dist_u, BIG))
            kmin, best = ukey.min(1)
            found = sl & (kmin < BIG)
            if not bool(found.any()):
                continue
            at = at_shed_u.gather(1, best.view(B, 1)).squeeze(1)
            mv = dir_to_shed_u.gather(1, best.view(B, 1)).squeeze(1)
            if kc == 1:
                take = torch.minimum(c_qty, shed_wheat_left)
                fb, aa = found, found & at
                bi = best[fb]
                out_op[fb, bi] = torch.where(at, torch.full_like(mv, X.U_PICKUP),
                                             mv)[fb]
                out_arg[aa, best[aa]] = _WHEAT
                out_qty[aa, best[aa]] = take[aa]
                shed_wheat_left = torch.where(aa, shed_wheat_left - take,
                                              shed_wheat_left)
                out_task[fb, bi] = X.U_FEED
                busy[fb, bi] = True
            else:
                # prefer an animal whose structure is open: COW, SHEEP, GOOSE
                openk = [past_open, past_open, coop_open]
                prefs = [_ANIMAL_IDX["COW"], _ANIMAL_IDX["SHEEP"],
                         _ANIMAL_IDX["GOOSE"]]
                pick = torch.full((B,), -1, dtype=i64, device=dev)
                for pass_ in (0, 1):
                    for j, a in enumerate(prefs):
                        ok = (shed_animals_left[:, a] > 0) & (pick < 0)
                        if pass_ == 0:
                            ok = ok & openk[j]
                        pick = torch.where(ok, torch.full_like(pick, a), pick)
                fb = found & (pick >= 0)
                aa, mvb = fb & at, fb & ~at
                pa = pick.clamp(min=0)
                out_op[aa, best[aa]] = X.U_PICKUP
                out_arg[aa, best[aa]] = (pa + ET.N_MKT)[aa]
                out_qty[aa, best[aa]] = 1
                shed_animals_left[aa, pa[aa]] -= 1
                out_op[mvb, best[mvb]] = mv[mvb]
                out_task[fb, best[fb]] = X.U_PLACE
                out_ta[fb, best[fb]] = pa[fb]
                busy[fb, best[fb]] = True

    # ---- idle units: run produce back to the shed ---------------------------
    produce_u = inv[:, :, 1:ET.N_MKT].sum(-1)          # products minus WHEAT
    carrying_u = inv.sum(-1)
    for u in range(U):
        idle = active[:, u] & ~busy[:, u]
        if not bool(idle.any()):
            continue
        at = at_shed_u[:, u]
        drop = idle & at & (produce_u[:, u] > 0) & (shed_total < BY.SHED_CAPACITY)
        pick = idle & at & ~drop & (n_animals > 0) & (shed_wheat_left > 0) \
            & (inv[:, u, _WHEAT] < 2)
        if endgame:
            pick = torch.zeros_like(pick)
        walk = idle & ~at & ((produce_u[:, u] >= 6) | (carrying_u[:, u] >= 12))
        if endgame:
            walk = idle & ~at
        take = torch.minimum(
            torch.full_like(shed_wheat_left, BY.WHEAT_PER_TRIP),
            shed_wheat_left)
        out_op[drop, u] = X.U_DROP
        out_op[pick, u] = X.U_PICKUP
        out_arg[pick, u] = _WHEAT
        out_qty[pick, u] = take[pick]
        shed_wheat_left = torch.where(pick, shed_wheat_left - take,
                                      shed_wheat_left)
        out_op[walk, u] = dir_to_shed_u[:, u][walk]
        out_task[drop, u] = X.U_DROP
        out_task[pick, u] = X.U_FEED     # wheat restock serves the feeding loop
        out_task[walk, u] = X.U_DROP
        busy[:, u] |= idle

    # ---- market --------------------------------------------------------------
    m_op = torch.zeros((B, S_MKT), dtype=i64, device=dev)
    m_item = torch.zeros((B, S_MKT), dtype=i64, device=dev)
    m_rem = torch.zeros((B, S_MKT), dtype=i64, device=dev)
    ptr = torch.zeros((B,), dtype=i64, device=dev)
    spend = torch.zeros((B,), dtype=f64, device=dev)

    def push(mask, op, item, rem):
        mk2 = mask & (ptr < S_MKT)
        if bool(mk2.any()):
            idx = ptr[mk2]
            m_op[mk2, idx] = op[mk2] if torch.is_tensor(op) else op
            m_item[mk2, idx] = item[mk2] if torch.is_tensor(item) else item
            m_rem[mk2, idx] = rem[mk2] if torch.is_tensor(rem) else rem
            ptr.add_(mk2.to(i64))
        return mk2

    mkt_inv = ep.mkt_inv.to(i64)                       # (B, 9)

    if not endgame:
        if hour <= 3:
            hires = ep.hires_today[:, p].to(i64).clone()
            payroll = t.fibsum[hires.clamp(max=39)].to(f64)
            budget = torch.clamp(money * BY.HIRE_BUDGET_FRAC, min=4.0)
            alive = torch.ones((B,), dtype=torch.bool, device=dev)
            for _ in range(7):
                cost = t.fib[hires.clamp(max=39)].to(f64)
                ok = (alive & (ptr < 7) & (hires < BY.HAND_CAP)
                      & (payroll + cost <= budget)
                      & (money - spend >= cost + 40))
                ok = push(ok, X.OP_HIRE, 0, 0)
                cz = torch.where(ok, cost, torch.zeros_like(cost))
                spend = spend + cz
                payroll = payroll + cz
                hires = hires + ok.to(i64)
                alive = ok

        n_extra = ep.quad_unlocked[:, p].to(i64).sum(-1)
        crop_room = (is_free & ~zone).sum(-1)
        land_p = t.land_prices[n_extra.clamp(max=2)].to(f64)
        reserve = t.land_reserve[n_extra.clamp(max=2)].to(f64)
        ok = ((n_extra < min(len(BY.LAND_PRICES), BY.MAX_QUADRANTS - 1))
              & (crop_room <= 8) & (money - spend >= land_p + reserve))
        ok = push(ok, X.OP_LAND, 0, 0)
        spend = spend + torch.where(ok, land_p, torch.zeros_like(land_p))

        housing_free = n_empty_structs + room
        owned_of = counts + animals_in_shed
        gz = _ANIMAL_IDX
        want_a = torch.full((B,), -1, dtype=i64, device=dev)
        want_a = torch.where(owned_of[:, gz["COW"]] < BY.TARGET_COWS,
                             torch.full_like(want_a, gz["COW"]), want_a)
        want_a = torch.where(
            (want_a < 0) & (owned_of[:, gz["SHEEP"]] < BY.TARGET_SHEEP),
            torch.full_like(want_a, gz["SHEEP"]), want_a)
        want_a = torch.where(
            (want_a < 0) & (owned_of[:, gz["GOOSE"]] < BY.TARGET_GEESE)
            & (day <= 20),
            torch.full_like(want_a, gz["GOOSE"]), want_a)
        cost = t.animal_cost[want_a.clamp(min=0)].to(f64)
        keep = 100.0 if day < 12 else 400.0
        ok = ((day <= 23) & (n_pending < 2) & (housing_free > n_pending)
              & (shed_total < BY.SHED_CAPACITY - 8) & (want_a >= 0)
              & (money - spend >= cost + keep))
        ok = push(ok, ET.OP_ANIMAL, want_a.clamp(min=0), 1)
        spend = spend + torch.where(ok, cost, torch.zeros_like(cost))

        for ci in range(3):
            cidx = int(t.plan_crop[ci])
            last_day = int(t.plan_last[ci])
            tgt = int(t.plan_target[ci])
            have = crop_counts[:, cidx] + seeds[:, cidx]
            k = torch.minimum(torch.minimum(
                torch.full_like(have, 4), tgt - have), crop_room)
            cost1 = float(t.crop_seed[cidx])
            ok = ((day <= last_day) & (crop_room > 0) & (have < tgt) & (k > 0)
                  & (money - spend >= cost1 * k.to(f64) + 100))
            ok = push(ok, ET.OP_SEED, cidx, k)
            kz = torch.where(ok, k, torch.zeros_like(k))
            spend = spend + cost1 * kz.to(f64)
            crop_room = crop_room - kz

        need_wheat = torch.minimum(
            torch.full_like(n_animals, BY.WHEAT_RESERVE_CAP),
            n_animals * BY.WHEAT_RESERVE_PER_ANIMAL)
        wprice = ep._price_at(torch.full_like(mkt_inv[:, 0], _WHEAT),
                              mkt_inv[:, _WHEAT] - 1).to(f64)
        kw = torch.minimum(torch.full_like(need_wheat, 10),
                           need_wheat - shed[:, _WHEAT])
        ok = ((n_animals > 0) & (shed[:, _WHEAT] < need_wheat)
              & (shed_total < BY.SHED_CAPACITY - 10)
              & (money - spend >= wprice * kw.to(f64) + 150))
        ok = push(ok, ET.OP_BUYP, _WHEAT, kw)
        spend = spend + torch.where(ok, wprice * kw.to(f64),
                                    torch.zeros_like(spend))

    # sells: (value, item-name) descending, metered by our own price impact
    held9 = shed[:, :ET.N_MKT].clone()
    if not endgame:
        reserve_w = torch.minimum(
            torch.full_like(n_animals, BY.WHEAT_RESERVE_CAP),
            n_animals * BY.WHEAT_RESERVE_PER_ANIMAL)
        held9[:, _WHEAT] = (held9[:, _WHEAT] - reserve_w).clamp(min=0)
    ar9 = torch.arange(ET.N_MKT, dtype=i64, device=dev)
    price0 = ep._price_at(ar9.view(1, -1).expand(B, -1).reshape(-1),
                          mkt_inv.reshape(-1)).view(B, ET.N_MKT).to(i64)
    value = price0 * torch.minimum(held9, torch.full_like(held9, BY.SELL_BATCH))
    skey = torch.where(held9 > 0, value * 16 + t.sell_rank.view(1, -1),
                       torch.full_like(value, -1))
    sorder = skey.argsort(1, descending=True)
    pressure = shed_total >= BY.SHED_PRESSURE
    offs = torch.arange(BY.SELL_BATCH, dtype=i64, device=dev)
    pgrid = ep._price_at(
        ar9.view(1, -1, 1).expand(B, -1, BY.SELL_BATCH).reshape(-1),
        (mkt_inv.view(B, ET.N_MKT, 1) + offs.view(1, 1, -1)).reshape(-1)
    ).view(B, ET.N_MKT, BY.SELL_BATCH).to(f64)
    lead = (pgrid >= t.sell_floor.view(1, ET.N_MKT, 1)).to(i64) \
        .cumprod(-1).sum(-1)                          # (B, 9) leading run
    for r in range(ET.N_MKT):
        it = sorder[:, r]
        held_r = held9.gather(1, it.view(B, 1)).squeeze(1)
        ok_r = skey.gather(1, it.view(B, 1)).squeeze(1) >= 0
        if endgame:
            qty = torch.minimum(held_r, torch.full_like(held_r, 40))
        else:
            lead_r = lead.gather(1, it.view(B, 1)).squeeze(1)
            metered = torch.minimum(lead_r, torch.minimum(
                held_r, torch.full_like(held_r, BY.SELL_BATCH)))
            qty = torch.where(
                pressure,
                torch.minimum(held_r, torch.full_like(held_r, BY.SELL_BATCH)),
                metered)
        push(ok_r & (qty > 0), ET.OP_SELL, it, qty)

    ops = {"f_op": out_op[:, 0], "f_arg": out_arg[:, 0], "f_qty": out_qty[:, 0],
           "h_op": [out_op[:, u] for u in range(1, U)],
           "h_arg": [out_arg[:, u] for u in range(1, U)],
           "h_qty": [out_qty[:, u] for u in range(1, U)],
           "m_op": m_op, "m_item": m_item, "m_rem": m_rem,
           # intent labels (kickstart teachers read these; the override
           # graft in step_idx ignores unknown keys)
           "task": out_task, "task_arg": out_ta}
    if not want_dicts:
        return ops
    return ops, _to_dicts(ep, p, ops)


def _op_to_list(op, arg, qty):
    if op == X.U_PLANT:
        return ["PLANT", ET.CROP_NAMES[arg]]
    if op == X.U_PLACE:
        return ["PLACE", ET.ANIMAL_NAMES[arg]]
    if op == X.U_PICKUP:
        return ["PICKUP", ET.ITEMS[arg], qty]
    return list(_OP_STR[op])


def _to_dicts(ep, p, ops):
    """step_raw-form action dicts per lane (the gate's comparison side)."""
    B = ep.B
    n_hands = ep.hands_n[:, p].tolist()
    f = (ops["f_op"].tolist(), ops["f_arg"].tolist(), ops["f_qty"].tolist())
    h = [(o.tolist(), a.tolist(), q.tolist())
         for o, a, q in zip(ops["h_op"], ops["h_arg"], ops["h_qty"])]
    m_op = ops["m_op"].tolist()
    m_item = ops["m_item"].tolist()
    m_rem = ops["m_rem"].tolist()
    out = []
    for lane in range(B):
        market = []
        for s in range(S_MKT):
            op = m_op[lane][s]
            if op == 0:
                continue
            if op == X.OP_HIRE:
                market.append(["HIRE"])
            elif op == X.OP_LAND:
                market.append(["BUY_LAND"])
            elif op == ET.OP_SELL:
                market.append(["SELL", ET.PRODUCTS[m_item[lane][s]],
                               m_rem[lane][s]])
            elif op == ET.OP_BUYP:
                market.append(["BUY_PRODUCT", ET.PRODUCTS[m_item[lane][s]],
                               m_rem[lane][s]])
            elif op == ET.OP_SEED:
                market.append(["BUY_SEED", ET.CROP_NAMES[m_item[lane][s]],
                               m_rem[lane][s]])
            elif op == ET.OP_ANIMAL:
                market.append(["BUY_ANIMAL", ET.ANIMAL_NAMES[m_item[lane][s]],
                               m_rem[lane][s]])
        out.append({
            "farmer": _op_to_list(f[0][lane], f[1][lane], f[2][lane]),
            "hands": [_op_to_list(h[u][0][lane], h[u][1][lane], h[u][2][lane])
                      for u in range(n_hands[lane])],
            "market": market,
        })
    return out


class BarnyardOpponent:
    """trl_env opponent adapter: provides step_idx override encodings."""

    provides_ops = True

    def __call__(self, ep, player):
        return compute(ep, player)
