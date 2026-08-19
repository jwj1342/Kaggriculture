"""Fixed-shape tensor state for batched Kaggriculture."""

from dataclasses import dataclass, fields

import torch

from . import constants as C


@dataclass
class TensorState:
    kind: torch.Tensor          # [B,2,H,W] int16
    crop: torch.Tensor          # [B,2,H,W] int16  -1 none
    animal: torch.Tensor        # [B,2,H,W] int16  -1 none
    planted_day: torch.Tensor
    placed_day: torch.Tensor
    yield_units: torch.Tensor
    watered: torch.Tensor       # bool
    unwatered: torch.Tensor     # int16
    fed: torch.Tensor
    unfed: torch.Tensor
    cared: torch.Tensor
    fert_avail: torch.Tensor
    fert_until: torch.Tensor    # int16, -1
    pending_care: torch.Tensor
    max_life: torch.Tensor      # int32, -1

    farmer_xy: torch.Tensor     # [B,2,2] long x,y
    n_hands: torch.Tensor       # [B,2] long
    hand_xy: torch.Tensor       # [B,2,ENGINE_HAND_CAP,2]
    inv: torch.Tensor           # [B,2,N_UNIT,N_SHED] int32  products+animals
    inv_ord: torch.Tensor       # [B,2,N_UNIT,N_SHED] int16  dict insertion rank, -1 empty
    inv_next: torch.Tensor      # [B,2,N_UNIT] int16  next insertion rank

    money: torch.Tensor         # [B,2] float32
    shed: torch.Tensor          # [B,2,12] int32
    seeds: torch.Tensor         # [B,2,5] int32
    unlocked: torch.Tensor      # [B,2,4] bool  NW NE SW SE
    hires_today: torch.Tensor   # [B,2] int16

    market_inv: torch.Tensor    # [B,9] int32
    shops: torch.Tensor         # [B,8] int16  -1 empty
    n_shops: torch.Tensor       # [B] int16

    step: torch.Tensor          # [B] int32
    day: torch.Tensor
    hour: torch.Tensor
    done: torch.Tensor          # [B] bool
    seed: torch.Tensor          # [B] int64
    phi: torch.Tensor           # [B] float32  relative Φ for player 0

    def batch_size(self):
        return int(self.kind.shape[0])

    def device(self):
        return self.kind.device

    def to(self, device):
        kwargs = {f.name: getattr(self, f.name).to(device) for f in fields(self)}
        return TensorState(**kwargs)


@dataclass
class Actions:
    """Per-unit farm ops + 10 market orders, both players.

    op/arg/qty: [B, 2, N_UNIT]
    m_op/m_item/m_qty: [B, 2, 10]
    """
    op: torch.Tensor
    arg: torch.Tensor
    qty: torch.Tensor
    m_op: torch.Tensor
    m_item: torch.Tensor
    m_qty: torch.Tensor

    def to(self, device):
        return Actions(
            self.op.to(device), self.arg.to(device), self.qty.to(device),
            self.m_op.to(device), self.m_item.to(device), self.m_qty.to(device),
        )


def empty_actions(batch, device, dtype=torch.int16):
    z = dict(device=device)
    return Actions(
        op=torch.zeros(batch, C.N_PLAYER, C.N_UNIT, dtype=torch.int16, **z),
        arg=torch.zeros(batch, C.N_PLAYER, C.N_UNIT, dtype=torch.int16, **z),
        qty=torch.zeros(batch, C.N_PLAYER, C.N_UNIT, dtype=torch.int16, **z),
        m_op=torch.zeros(batch, C.N_PLAYER, C.MAX_ORDERS, dtype=torch.int16, **z),
        m_item=torch.zeros(batch, C.N_PLAYER, C.MAX_ORDERS, dtype=torch.int16, **z),
        m_qty=torch.zeros(batch, C.N_PLAYER, C.MAX_ORDERS, dtype=torch.int16, **z),
    )


def _quadrant(x, y, half=C.BOARD // 2):
    # 0 NW, 1 NE, 2 SW, 3 SE
    ns = (y >= half).to(torch.int64) * 2
    ew = (x >= half).to(torch.int64)
    return ns + ew


def new_state(batch, device, seeds=None):
    B = int(batch)
    H = W = C.BOARD
    z = dict(device=device)
    kind = torch.full((B, 2, H, W), C.K_LOCKED, dtype=torch.int16, **z)
    yy = torch.arange(H, device=device).view(1, 1, H, 1).expand(B, 2, H, W)
    xx = torch.arange(W, device=device).view(1, 1, 1, W).expand(B, 2, H, W)
    nw = _quadrant(xx, yy) == 0
    kind = torch.where(nw, torch.zeros_like(kind), kind)  # empty in NW

    neg = torch.full((B, 2, H, W), -1, dtype=torch.int16, **z)
    z16 = torch.zeros((B, 2, H, W), dtype=torch.int16, **z)
    z32 = torch.zeros((B, 2, H, W), dtype=torch.int32, **z)
    bf = torch.zeros((B, 2, H, W), dtype=torch.bool, **z)

    if seeds is None:
        seed_t = torch.arange(B, device=device, dtype=torch.int64)
    else:
        seed_t = torch.as_tensor(seeds, device=device, dtype=torch.int64).reshape(-1)
        if seed_t.numel() == 1:
            seed_t = seed_t.expand(B).clone()
        elif seed_t.numel() != B:
            raise ValueError(f"seeds length {seed_t.numel()} != batch {B}")

    spawn = torch.tensor(C.SPAWN, device=device, dtype=torch.int64)
    farmer = spawn.view(1, 1, 2).expand(B, 2, 2).contiguous()

    st = TensorState(
        kind=kind, crop=neg.clone(), animal=neg.clone(),
        planted_day=z16.clone(), placed_day=z16.clone(), yield_units=z16.clone(),
        watered=bf.clone(), unwatered=z16.clone(),
        fed=bf.clone(), unfed=z16.clone(), cared=bf.clone(),
        fert_avail=bf.clone(), fert_until=neg.clone(),
        pending_care=z16.clone(), max_life=z32.clone() - 1,
        farmer_xy=farmer,
        n_hands=torch.zeros(B, 2, dtype=torch.int64, **z),
        hand_xy=torch.zeros(B, 2, C.ENGINE_HAND_CAP, 2, dtype=torch.int64, **z),
        inv=torch.zeros(B, 2, C.N_UNIT, C.N_SHED, dtype=torch.int32, **z),
        inv_ord=torch.full((B, 2, C.N_UNIT, C.N_SHED), -1, dtype=torch.int16, **z),
        inv_next=torch.zeros(B, 2, C.N_UNIT, dtype=torch.int16, **z),
        money=torch.full((B, 2), C.STARTING_MONEY, dtype=torch.float32, **z),
        shed=torch.zeros(B, 2, C.N_SHED, dtype=torch.int32, **z),
        seeds=torch.zeros(B, 2, C.N_CROP, dtype=torch.int32, **z),
        unlocked=torch.zeros(B, 2, 4, dtype=torch.bool, **z),
        hires_today=torch.zeros(B, 2, dtype=torch.int16, **z),
        market_inv=torch.full((B, C.N_PRODUCT), C.MARKET_I0, dtype=torch.int32, **z),
        shops=torch.full((B, C.MAX_SHOPS), -1, dtype=torch.int16, **z),
        n_shops=torch.zeros(B, dtype=torch.int16, **z),
        step=torch.zeros(B, dtype=torch.int32, **z),
        day=torch.zeros(B, dtype=torch.int32, **z),
        hour=torch.zeros(B, dtype=torch.int32, **z),
        done=torch.zeros(B, dtype=torch.bool, **z),
        seed=seed_t,
        phi=torch.zeros(B, dtype=torch.float32, **z),
    )
    st.unlocked[:, :, 0] = True
    st.cpu_step = 0
    st.cpu_max_hands = 0
    return st


def unit_xy(st: TensorState, u: int):
    """[B,2,2] position of unit u (0=farmer)."""
    if u == 0:
        return st.farmer_xy
    return st.hand_xy[:, :, u - 1, :]


def set_unit_xy(st: TensorState, u: int, xy):
    if u == 0:
        st.farmer_xy = xy
    else:
        st.hand_xy[:, :, u - 1, :] = xy


def unit_alive(st: TensorState, u: int):
    if u == 0:
        return torch.ones(st.batch_size(), C.N_PLAYER, dtype=torch.bool, device=st.device())
    return st.n_hands > (u - 1)


def all_unit_xy(st: TensorState, n_u=None):
    """farmer + hands as [B,2,U,2]."""
    n_u = C.N_UNIT if n_u is None else int(n_u)
    B = st.batch_size()
    xy = torch.empty(B, C.N_PLAYER, n_u, 2, dtype=st.farmer_xy.dtype, device=st.device())
    xy[:, :, 0, :] = st.farmer_xy
    take = min(n_u - 1, C.ENGINE_HAND_CAP)
    if take > 0:
        xy[:, :, 1:1 + take, :] = st.hand_xy[:, :, :take, :]
    return xy


def all_unit_alive(st: TensorState, n_u=None):
    """[B,2,U] farmer always live; hand u-1 live iff n_hands > u-1."""
    n_u = C.N_UNIT if n_u is None else int(n_u)
    u = torch.arange(n_u, device=st.device())
    return (u == 0) | (st.n_hands.unsqueeze(-1) > (u - 1))


def gather_tile(grid, xy):
    """grid [B,2,H,W], xy [B,2,2] -> [B,2]."""
    b, p = grid.shape[:2]
    x = xy[..., 0].long().clamp(0, C.BOARD - 1)
    y = xy[..., 1].long().clamp(0, C.BOARD - 1)
    bb = torch.arange(b, device=grid.device)[:, None].expand(b, p)
    pp = torch.arange(p, device=grid.device)[None, :].expand(b, p)
    return grid[bb, pp, y, x]


def scatter_tile(grid, xy, val, mask):
    """Write val into grid at xy where mask. Returns new tensor (no in-place on views)."""
    out = grid.clone()
    scatter_inplace(out, xy, val, mask)
    return out


def _index_xy(grid, xy):
    b, p = grid.shape[:2]
    x = xy[..., 0].long().clamp(0, C.BOARD - 1)
    y = xy[..., 1].long().clamp(0, C.BOARD - 1)
    bb = torch.arange(b, device=grid.device)[:, None].expand(b, p)
    pp = torch.arange(p, device=grid.device)[None, :].expand(b, p)
    return bb, pp, y, x


def scatter_inplace(grid, xy, val, mask):
    """In-place write (env is not differentiated)."""
    bb, pp, y, x = _index_xy(grid, xy)
    cur = grid[bb, pp, y, x]
    if not torch.is_tensor(val):
        val = torch.full_like(cur, val)
    else:
        if val.dtype != cur.dtype:
            val = val.to(dtype=cur.dtype)
        if val.shape != cur.shape:
            val = val.expand_as(cur)
    grid[bb, pp, y, x] = torch.where(mask, val, cur)


def gather_hw(grid, xy):
    """grid [B,H,W], xy [B,2] -> [B]."""
    x = xy[..., 0].long().clamp(0, C.BOARD - 1)
    y = xy[..., 1].long().clamp(0, C.BOARD - 1)
    b = torch.arange(grid.shape[0], device=grid.device)
    return grid[b, y, x]


_SHED_XY = {}


def is_shed_tile(xy):
    """xy [B,2,2] -> [B,2] bool."""
    key = (xy.device, xy.dtype)
    cached = _SHED_XY.get(key)
    if cached is None:
        cached = (
            torch.tensor([t[0] for t in C.SHED_TILES], device=xy.device, dtype=xy.dtype),
            torch.tensor([t[1] for t in C.SHED_TILES], device=xy.device, dtype=xy.dtype),
        )
        _SHED_XY[key] = cached
    sx, sy = cached
    return ((xy[..., 0, None] == sx) & (xy[..., 1, None] == sy)).any(-1)


def quadrant(x, y):
    ns = (y >= C.BOARD // 2).to(torch.int64) * 2
    ew = (x >= C.BOARD // 2).to(torch.int64)
    return ns + ew


def reset_tile(st, xy, mask, kind=C.K_EMPTY):
    scatter_inplace(st.kind, xy, kind, mask)
    scatter_inplace(st.crop, xy, -1, mask)
    scatter_inplace(st.animal, xy, -1, mask)
    scatter_inplace(st.planted_day, xy, 0, mask)
    scatter_inplace(st.placed_day, xy, 0, mask)
    scatter_inplace(st.yield_units, xy, 0, mask)
    scatter_inplace(st.watered, xy, False, mask)
    scatter_inplace(st.unwatered, xy, 0, mask)
    scatter_inplace(st.fed, xy, False, mask)
    scatter_inplace(st.unfed, xy, 0, mask)
    scatter_inplace(st.cared, xy, False, mask)
    scatter_inplace(st.fert_avail, xy, False, mask)
    scatter_inplace(st.fert_until, xy, -1, mask)
    scatter_inplace(st.pending_care, xy, 0, mask)
    scatter_inplace(st.max_life, xy, -1, mask)
