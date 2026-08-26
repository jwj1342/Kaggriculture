"""Batched features and potential on TensorState (player 0 is the learner)."""

import math

import torch

from ..potential import (
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
from . import constants as C
from ..board_obs import BOARD_FLAT, CH_PER_FARM, PACKED_DIM
from .engine import market_prices
from .tables import Tables


def _clamp(x, lo=-1.0, hi=1.0):
    return x.clamp(lo, hi)


def _logn(x, cap):
    x = x.to(torch.float32).clamp(min=0)
    return _clamp((1.0 + x).log() / math.log1p(float(cap)))


def encode(st, T: Tables, player=0):
    """Return [B, 75] features for `player` (default learner = 0)."""
    p = int(player)
    o = 1 - p
    day = st.day.to(torch.float32)
    hour = st.hour.to(torch.float32)
    step = st.step.to(torch.float32)
    feats = []

    ang_d = 2.0 * math.pi * (day / 30.0)
    ang_h = 2.0 * math.pi * (hour / 24.0)
    feats += [ang_d.sin(), ang_d.cos(), ang_h.sin(), ang_h.cos()]
    feats.append(_clamp(step / 720.0))

    money = st.money[:, p]
    feats.append(_logn(money, 200000))
    feats.append(_clamp(st.n_hands[:, p].to(torch.float32) / 12.0))
    feats.append(_clamp(st.unlocked[:, p].to(torch.float32).sum(-1) / 4.0))

    kind = st.kind[:, p]
    crop = st.crop[:, p]
    is_plant = kind == C.K_PLANT
    for c in range(C.N_CROP):
        pc = is_plant & (crop == c)
        feats.append(_clamp(pc.to(torch.float32).sum(dim=(-1, -2)) / 40.0))
        harv = pc & (st.yield_units[:, p] > 0)
        feats.append(_clamp(harv.to(torch.float32).sum(dim=(-1, -2)) / 20.0))
        need = pc & (~st.watered[:, p])
        feats.append(_clamp(need.to(torch.float32).sum(dim=(-1, -2)) / 30.0))

    animal = st.animal[:, p]
    for a in range(C.N_ANIMAL):
        pa = animal == a
        feats.append(_clamp(pa.to(torch.float32).sum(dim=(-1, -2)) / 20.0))
        feats.append(_clamp((pa & (~st.fed[:, p])).to(torch.float32).sum(dim=(-1, -2)) / 10.0))
        feats.append(_clamp((pa & (~st.cared[:, p])).to(torch.float32).sum(dim=(-1, -2)) / 10.0))
        feats.append(_clamp((pa & st.fert_avail[:, p]).to(torch.float32).sum(dim=(-1, -2)) / 10.0))

    weeds = (kind == C.K_WEED).to(torch.float32).sum(dim=(-1, -2))
    empty = (kind == C.K_EMPTY).to(torch.float32).sum(dim=(-1, -2))
    feats.append(_clamp(weeds / 50.0))
    feats.append(_clamp(empty / 60.0))

    for i in range(C.N_PRODUCT):
        feats.append(_logn(st.shed[:, p, i], 100))
    for c in range(C.N_CROP):
        feats.append(_logn(st.seeds[:, p, c], 20))

    prices = market_prices(st.market_inv, T)
    for i in range(C.N_PRODUCT):
        feats.append(_clamp((prices[:, i] / T.base_price[i] - 1.0) / 2.0))
    for i in range(C.N_PRODUCT):
        feats.append(_logn(st.market_inv[:, i], 20000))

    feats.append(_clamp(st.n_shops.to(torch.float32) / 8.0))

    opp_m = st.money[:, o]
    feats.append(_clamp(((opp_m - money).clamp(min=0) + 1).log() / math.log1p(200000.0)))
    feats.append(_clamp(st.n_hands[:, o].to(torch.float32) / 12.0))
    feats.append(_clamp(st.unlocked[:, o].to(torch.float32).sum(-1) / 4.0))
    opp_crops = ((st.kind[:, o] == C.K_PLANT).to(torch.float32).sum(dim=(-1, -2)))
    opp_anim = ((st.animal[:, o] >= 0).to(torch.float32).sum(dim=(-1, -2)))
    feats.append(_clamp(opp_crops / 40.0))
    feats.append(_clamp(opp_anim / 20.0))

    return torch.stack(feats, dim=-1)


def _farm_board(st, p):
    """[B, 22, H, W] for one player. Channel order is rl.board_obs."""
    kind = st.kind[:, p]
    crop = st.crop[:, p]
    animal = st.animal[:, p]
    device = kind.device
    B, H, W = kind.shape
    is_plant = kind == C.K_PLANT
    ch = [
        (kind == C.K_EMPTY).to(torch.float32),
        (kind == C.K_LOCKED).to(torch.float32),
        (kind == C.K_WEED).to(torch.float32),
        is_plant.to(torch.float32),
    ]
    for c in range(C.N_CROP):
        ch.append((is_plant & (crop == c)).to(torch.float32))
    ch.append((st.yield_units[:, p].to(torch.float32) / 6.0).clamp(0.0, 1.0))
    ch.append(st.watered[:, p].to(torch.float32))
    ch.append((st.unwatered[:, p].to(torch.float32) / 2.0).clamp(0.0, 1.0))
    ch.append((kind == C.K_PASTURE).to(torch.float32))
    ch.append((kind == C.K_COOP).to(torch.float32))
    for a in range(C.N_ANIMAL):
        ch.append((animal == a).to(torch.float32))
    ch.append(st.fed[:, p].to(torch.float32))
    ch.append(st.cared[:, p].to(torch.float32))
    ch.append(st.fert_avail[:, p].to(torch.float32))

    farmer = torch.zeros(B, H, W, device=device, dtype=torch.float32)
    fx = st.farmer_xy[:, p, 0].clamp(0, W - 1).long()
    fy = st.farmer_xy[:, p, 1].clamp(0, H - 1).long()
    farmer[torch.arange(B, device=device), fy, fx] = 1.0
    ch.append(farmer)

    hands = torch.zeros(B, H, W, device=device, dtype=torch.float32)
    cap = st.hand_xy.shape[2]
    n = st.n_hands[:, p].clamp(0, cap).long()
    hx = st.hand_xy[:, p, :, 0]
    hy = st.hand_xy[:, p, :, 1]
    slot = torch.arange(cap, device=device)[None, :]
    valid = (slot < n[:, None]) & (hx >= 0) & (hx < W) & (hy >= 0) & (hy < H)
    if bool(valid.any()):
        b_idx = torch.arange(B, device=device)[:, None].expand_as(hx)[valid]
        hands.index_put_(
            (b_idx, hy[valid].long(), hx[valid].long()),
            torch.full((int(valid.sum()),), 0.25, device=device, dtype=torch.float32),
            accumulate=True,
        )
    ch.append(hands.clamp(0.0, 1.0))
    stacked = torch.stack(ch, dim=1)
    if stacked.shape[1] != CH_PER_FARM:
        raise RuntimeError(f"board channels {stacked.shape[1]} != {CH_PER_FARM}")
    return stacked


def encode_board(st, player=0):
    """Own then opponent boards, [B, 44, 10, 10]."""
    p = int(player)
    mine = _farm_board(st, p)
    opp = _farm_board(st, 1 - p)
    return torch.cat([mine, opp], dim=1)


def encode_packed(st, T: Tables, player=0):
    """Global 75 + flattened boards. [B, PACKED_DIM]."""
    g = encode(st, T, player=player)
    b = encode_board(st, player=player).reshape(g.shape[0], BOARD_FLAT)
    packed = torch.cat([g, b], dim=-1)
    if packed.shape[-1] != PACKED_DIM:
        raise RuntimeError(f"packed {packed.shape[-1]} != {PACKED_DIM}")
    return packed


def farm_phi(st, T: Tables, p, hide_private=False):
    """Dollar potential for one player. Opponent private is hidden when True."""
    phi = st.money[:, p].to(torch.float32)
    if not hide_private:
        phi = phi + (st.shed[:, p, :C.N_PRODUCT].to(torch.float32) * T.base_price * SHED_DISCOUNT).sum(-1)
        waiting = st.shed[:, p, C.ANIMAL_SHED0:C.ANIMAL_SHED0 + C.N_ANIMAL].to(torch.float32)
        phi = phi + (waiting * T.animal_cost * SHED_ANIMAL_CREDIT).sum(-1)
        phi = phi + (st.seeds[:, p].to(torch.float32) * T.seed_cost * SEED_RESIDUAL).sum(-1)

    is_plant = st.kind[:, p] == C.K_PLANT
    cid = st.crop[:, p].clamp(min=0).long()
    day = st.day.to(torch.float32)[:, None, None]
    sitting = st.yield_units[:, p].to(torch.float32)
    ongoing = T.crop_ongoing[cid]
    interval = T.crop_interval[cid].clamp(min=1).to(torch.float32)
    first = T.crop_first[cid].to(torch.float32)
    planted = st.planted_day[:, p].to(torch.float32)
    start = torch.maximum(day, planted + first)
    remaining_events = 1.0 + (C.SEASON_DAYS - start).clamp(min=0) / interval
    remaining_events = torch.where(start > C.SEASON_DAYS, torch.zeros_like(remaining_events), remaining_events)
    dsf = day - planted - first
    produced = torch.where(dsf >= 0, (dsf // interval + 1).clamp(max=T.crop_max_yield[cid].to(dsf.dtype)), torch.zeros_like(dsf))
    remaining_cap = (T.crop_max_yield[cid].to(torch.float32) - produced.to(torch.float32)).clamp(min=0)
    rem_on = sitting + torch.minimum(remaining_cap, remaining_events)
    rem = torch.where(ongoing, rem_on, T.crop_max_yield[cid].to(torch.float32))
    stress = ((~st.watered[:, p]) & (st.unwatered[:, p] >= 1)).to(torch.float32) * WATER_STRESS
    crop_price = T.base_price[cid.clamp(max=C.N_PRODUCT - 1)]
    # crop id 0-4 maps to product 0-4
    plant_phi = rem * crop_price * PLANT_CREDIT * (1.0 - stress)
    phi = phi + (plant_phi * is_plant.to(torch.float32)).sum(dim=(-1, -2))
    phi = phi - ((st.kind[:, p] == C.K_WEED).to(torch.float32).sum(dim=(-1, -2)) * WEED_COST)

    empty_h = (
        ((st.kind[:, p] == C.K_PASTURE) | (st.kind[:, p] == C.K_COOP))
        & (st.animal[:, p] < 0)
    )
    phi = phi + empty_h.to(torch.float32).sum(dim=(-1, -2)) * HOUSING_VALUE

    has_a = st.animal[:, p] >= 0
    aid = st.animal[:, p].clamp(min=0).long()
    a_first = T.animal_first[aid].to(torch.float32)
    a_ivl = T.animal_interval[aid].clamp(min=1).to(torch.float32)
    placed = st.placed_day[:, p].to(torch.float32)
    start_a = torch.maximum(day, placed + a_first)
    rem_ev = 1.0 + (C.SEASON_DAYS - start_a).clamp(min=0) / a_ivl
    rem_ev = torch.where(start_a > C.SEASON_DAYS, torch.zeros_like(rem_ev), rem_ev)
    held = st.yield_units[:, p].to(torch.float32)
    prod_id = T.animal_product[aid]
    a_price = T.base_price[prod_id]
    a_phi = (held + rem_ev) * a_price * ANIMAL_CREDIT + HERD_ASSET
    a_phi = a_phi - torch.where(~st.fed[:, p], T.animal_cost[aid] * UNFED_RISK, torch.zeros_like(a_phi))
    a_phi = a_phi - torch.where(~st.cared[:, p], T.animal_cost[aid] * UNCARED_RISK, torch.zeros_like(a_phi))
    phi = phi + (a_phi * has_a.to(torch.float32)).sum(dim=(-1, -2))

    phi = phi + st.n_hands[:, p].to(torch.float32) * HAND_VALUE
    phi = phi + (st.unlocked[:, p].to(torch.float32).sum(-1) - 1.0) * LAND_VALUE
    return phi


def relative_phi(st, T: Tables, player=0):
    mine = farm_phi(st, T, player, hide_private=False)
    opp = farm_phi(st, T, 1 - int(player), hide_private=True)
    return mine - opp


def shaped_reward(st, phi_prev, T: Tables, player=0):
    phi = relative_phi(st, T, player)
    r = (phi - phi_prev) / C.PHI_SCALE
    done = st.done
    mine = st.money[:, player]
    opp = st.money[:, 1 - player]
    bonus = torch.where(mine > opp, torch.full_like(r, C.TERMINAL_BONUS),
                        torch.where(mine < opp, torch.full_like(r, -C.TERMINAL_BONUS), torch.zeros_like(r)))
    r = r + torch.where(done, bonus, torch.zeros_like(r))
    return r, phi
