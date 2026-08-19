"""Batched features and potential on TensorState (player 0 is the learner)."""

import math

import torch

from . import constants as C
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


def farm_phi(st, T: Tables, p, hide_private=False):
    """Dollar potential for one player. Opponent private is hidden when True."""
    phi = st.money[:, p].to(torch.float32)
    if not hide_private:
        phi = phi + (st.shed[:, p, :C.N_PRODUCT].to(torch.float32) * T.base_price * 0.9).sum(-1)
        phi = phi + (st.seeds[:, p].to(torch.float32) * T.seed_cost * 0.5).sum(-1)

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
    stress = ((~st.watered[:, p]) & (st.unwatered[:, p] >= 1)).to(torch.float32) * 0.15
    crop_price = T.base_price[cid.clamp(max=C.N_PRODUCT - 1)]
    # crop id 0-4 maps to product 0-4
    plant_phi = rem * crop_price * 0.5 * (1.0 - stress)
    phi = phi + (plant_phi * is_plant.to(torch.float32)).sum(dim=(-1, -2))
    phi = phi - ((st.kind[:, p] == C.K_WEED).to(torch.float32).sum(dim=(-1, -2)) * 25.0)

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
    a_phi = (held + rem_ev) * a_price * 0.4
    a_phi = a_phi - torch.where(~st.fed[:, p], T.animal_cost[aid] * 0.8, torch.zeros_like(a_phi))
    a_phi = a_phi - torch.where(~st.cared[:, p], T.animal_cost[aid] * 0.3, torch.zeros_like(a_phi))
    phi = phi + (a_phi * has_a.to(torch.float32)).sum(dim=(-1, -2))

    phi = phi + st.n_hands[:, p].to(torch.float32) * 40.0
    phi = phi + (st.unlocked[:, p].to(torch.float32).sum(-1) - 1.0) * 300.0
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
