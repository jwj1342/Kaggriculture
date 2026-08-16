"""Tensor-native action path for the batched engine (DESIGN.md B3b): step_idx.

EpisodeT.step_raw takes per-lane python action dicts -- bench.py measured that
interface as the O(B) host bottleneck under real load (DESIGN §4.5). This
module attaches the index interface the policy heads produce directly:

    import engine_t_idx            # attaches EpisodeT.step_idx on import
    ep.step_idx(f_idx, m_idx)      # (B, 2) int tensors, per lane per player:
                                   # indices into actions.FARMER_ACTIONS /
                                   # actions.MARKET_ACTIONS

and performs EXACTLY what step_raw would do given
`actions.decode(obs[lane][player], f, m)` dicts for every lane. The macro
realisation is transcribed from rl/actions.py and recomputed as batch tensor
ops: nearest-target selection with the (dist, y, x) lexicographic tie-break,
one greedy _step_toward move, the _with_stock shed legs (PICKUP want=12/5/1,
"return None -> PASS" fallbacks), the scripted hands dispatcher (per-hand
greedy assignment over the shared chore pool with its 'taken' exclusion and
the >=8-carry DROP leg), and the compound market decodes (liquidation-day
full-shed sell, HIRE bursts under the 0.05*money cap with no floor,
herd-scaled BUY_WHEAT). Unit effects are applied as masked tensor updates in
the engine's unit order (farmer, then hands slot by slot; players never
interact during the unit phase, so slots run batch-parallel). The market
per-unit lockstep, HIRE/BUY_LAND atomics, town/decay/end-of-day phases are
engine_t's own methods, reused unchanged -- step_raw itself is untouched.

Host-side work that remains, and why:
  * the end-of-day segment was already host-side (D2 RNG); before it runs,
    the dict-insertion-order metadata `_inv_ord` is rebuilt from this
    module's tensor `_ord_seq` so EpisodeT._end_of_day is reused verbatim.
  * scalar any()/max() reads that steer bounded loops (order slots, hand
    slots, lockstep units, per-op subsets) -- the reference itself is serial
    over those; nothing here loops over lanes. HIRE / BUY_LAND atomics are
    vectorised over their per-order-index event subsets (_idx_do_hire /
    _idx_do_land transcribe engine_t._do_hire / _do_buy_land, including the
    exact float money arithmetic and the spawn-tile occupancy sort key).

Insertion-order bookkeeping: engine_np unit inventories are dicts, and the
two capacity-limited deposit paths (DROP, end-of-day drop) walk them in
insertion order. step_raw tracks that with per-lane python lists
(`_inv_ord`); step_idx tracks it as `_ord_seq` (B,P,1+H,I) int32 -- the
monotone counter value at the moment an item's count went 0 -> positive
(0 = absent). Ascending _ord_seq over count>0 items IS dict insertion order
(deletion on zero plus re-insertion at the end matches re-adding at a fresh,
higher counter). The list representation is rebuilt from the tensor once per
day at the end-of-day boundary; do not interleave step_raw and step_idx calls
on one instance within a day (across day boundaries both stay consistent).

Gate: rl/tensor_env/test_b3b.py (G5 per-step snapshot equivalence against
decode+step_raw, G6 throughput under masks_t-sampled action load).
"""

import os
import sys

import torch

try:
    from . import engine_np as E
    from . import engine_t as ET
except ImportError:                      # flat imports (verify_t.py pattern)
    import engine_np as E
    import engine_t as ET

_RL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RL not in sys.path:
    sys.path.insert(0, _RL)

import actions as A                      # semantics source for decode
import kg_rules as R
from kg_rules import _fib

N = 10
NI = len(ET.ITEMS)                       # 12 inventory/shed items
BIG = 1 << 20

# --- pin every ordering baked into indices below (features_t pattern) ------
assert A.CROP_LIST == ET.CROP_NAMES and A.ANIMAL_LIST == ET.ANIMAL_NAMES
assert A.PRODUCT_LIST == ET.PRODUCTS
assert ET.ITEMS == A.PRODUCT_LIST + A.ANIMAL_LIST
assert ET.WHEAT_I == 0 and ET.FERT_I == 8 and ET.N_MKT == 9
assert A.FARMER_ACTIONS[:15] == [
    "PASS", "MOVE_N", "MOVE_S", "MOVE_E", "MOVE_W",
    "WATER", "HARVEST", "FEED", "CARE", "COLLECT_FERT", "FERTILIZE",
    "DIG_WEED", "BUILD_COOP", "BUILD_PASTURE", "DROP"]
assert A.FARMER_ACTIONS[15:20] == [f"PLANT_{c}" for c in A.CROP_LIST]
assert A.FARMER_ACTIONS[20:23] == [f"PLACE_{a}" for a in A.ANIMAL_LIST]
assert A.MARKET_ACTIONS[0] == "NOOP"
assert A.MARKET_ACTIONS[1:10] == [f"SELL_{p}" for p in A.PRODUCT_LIST]
assert A.MARKET_ACTIONS[10:15] == [f"BUY_SEED_{c}" for c in A.CROP_LIST]
assert A.MARKET_ACTIONS[15:22] == (
    ["BUY_WHEAT", "BUY_FERT"] + [f"BUY_{a}" for a in A.ANIMAL_LIST]
    + ["BUY_LAND", "HIRE"])
assert A._SHED == [(4, 4), (5, 4), (4, 5), (5, 5)]
assert E.FARMER_MOVES == {"NORTH": (0, -1), "SOUTH": (0, 1),
                          "EAST": (1, 0), "WEST": (-1, 0)}
assert R.LIQUIDATE_DAY == 29 and R.MAX_ORDERS >= ET.N_MKT

# --- unit op codes (internal; 1..4 mirror FARMER_ACTIONS' move block) -------
U_PASS, U_MOVE_N, U_MOVE_S, U_MOVE_E, U_MOVE_W = 0, 1, 2, 3, 4
U_WATER, U_HARVEST, U_FEED, U_CARE, U_COLLECT, U_FERTILIZE = 5, 6, 7, 8, 9, 10
U_DIG, U_BUILD_COOP, U_BUILD_PASTURE, U_DROP = 11, 12, 13, 14
U_PLANT, U_PLACE, U_PICKUP = 15, 16, 17

# --- target families for the farmer's macro intents ------------------------
F_NONE, F_EMPTY, F_WEED, F_UNWAT, F_UNFERT, F_HARV = 0, 1, 2, 3, 4, 5
F_UNFED, F_UNCARED, F_FREADY, F_COOPF, F_PASTF, F_SHED = 6, 7, 8, 9, 10, 11

_LUT_FAM = ([F_NONE] * 5
            + [F_UNWAT, F_HARV, F_UNFED, F_UNCARED, F_FREADY, F_UNFERT,
               F_WEED, F_EMPTY, F_EMPTY, F_SHED]
            + [F_EMPTY] * 5
            + [F_COOPF if R.ANIMALS[a]["structure"] == "COOP" else F_PASTF
               for a in A.ANIMAL_LIST])
_LUT_OP = ([U_PASS, U_MOVE_N, U_MOVE_S, U_MOVE_E, U_MOVE_W,
            U_WATER, U_HARVEST, U_FEED, U_CARE, U_COLLECT, U_FERTILIZE,
            U_DIG, U_BUILD_COOP, U_BUILD_PASTURE, U_DROP]
           + [U_PLANT] * 5 + [U_PLACE] * 3)
_LUT_ARG = [0] * 15 + [0, 1, 2, 3, 4] + [0, 1, 2]
# _with_stock legs: farmer index -> (item idx in ITEMS, PICKUP want)
_WS = {7: (ET.WHEAT_I, 12), 10: (ET.FERT_I, 5),
       20: (ET.N_MKT + 0, 1), 21: (ET.N_MKT + 1, 1), 22: (ET.N_MKT + 2, 1)}
_LUT_WS = [i in _WS for i in range(23)]
_LUT_WS_ITEM = [_WS.get(i, (0, 0))[0] for i in range(23)]
_LUT_WS_WANT = [_WS.get(i, (0, 0))[1] for i in range(23)]

# scripted-hands chore pool: family order IS the dispatch priority
# (harvest > water > care > collect fertilizer > dig weeds)
_POOL_OPS = [U_HARVEST, U_WATER, U_CARE, U_COLLECT, U_DIG]

# market order op codes: engine_t's 1..4 plus the two atomics
OP_HIRE, OP_LAND = 5, 6


class _Tabs:
    __slots__ = ("fam", "op", "arg", "ws", "ws_item", "ws_want",
                 "xs", "ys", "tile", "shed100", "dx", "dy", "fam5",
                 "pool_op", "crop_first", "crop_maxday", "crop_maxy",
                 "crop_ongoing", "animal_struct", "animal_product",
                 "fib", "fib_int", "land_prices", "ar9", "j4", "ar4",
                 "shed4x", "shed4y", "shed4t",
                 "c_e", "c_w", "c_s", "c_n", "c_pass")


_CACHE = {}


def _tabs(device):
    key = str(device)
    t = _CACHE.get(key)
    if t is None:
        i64 = torch.int64
        mk = lambda v: torch.tensor(v, dtype=i64, device=device)
        t = _Tabs()
        t.fam = mk(_LUT_FAM)
        t.op = mk(_LUT_OP)
        t.arg = mk(_LUT_ARG)
        t.ws = torch.tensor(_LUT_WS, dtype=torch.bool, device=device)
        t.ws_item = mk(_LUT_WS_ITEM)
        t.ws_want = mk(_LUT_WS_WANT)
        t.tile = torch.arange(N * N, dtype=i64, device=device)
        t.xs = t.tile % N
        t.ys = t.tile // N
        shed = torch.zeros(N * N, dtype=torch.bool, device=device)
        for (x, y) in A._SHED:
            shed[y * N + x] = True
        t.shed100 = shed
        t.dx = mk([0, 0, 0, 1, -1])      # per U_MOVE code
        t.dy = mk([0, -1, 1, 0, 0])
        t.fam5 = torch.arange(5, dtype=i64, device=device)
        t.pool_op = mk(_POOL_OPS)
        t.shed4x = mk([x for x, _ in A._SHED])
        t.shed4y = mk([y for _, y in A._SHED])
        t.shed4t = t.shed4y * N + t.shed4x
        t.ar4 = torch.arange(4, dtype=i64, device=device)
        t.crop_first = mk(ET.CROP_FIRST)
        t.crop_maxday = mk(ET.CROP_MAXDAY)
        t.crop_maxy = mk(ET.CROP_MAXY)
        t.crop_ongoing = torch.tensor(ET.CROP_ONGOING, dtype=torch.bool, device=device)
        t.animal_struct = mk(ET.ANIMAL_STRUCT)
        t.animal_product = mk(ET.ANIMAL_PRODUCT)
        # fib(n) exact in float64 through n=78; decode money never nears
        # fib(79) ~ 1.4e16, so the clamped compare cannot flip (same
        # argument, documented, as features_t's HIRE affordability).
        t.fib = torch.tensor([float(_fib(i)) for i in range(79)],
                             dtype=torch.float64, device=device)
        t.fib_int = mk([E._fib(i) for i in range(79)])
        t.land_prices = torch.tensor(E.LAND_PRICES, dtype=torch.float64,
                                     device=device)
        t.ar9 = torch.arange(ET.N_MKT, dtype=i64, device=device)
        t.j4 = torch.arange(4, dtype=i64, device=device)
        t.c_e = mk(U_MOVE_E)
        t.c_w = mk(U_MOVE_W)
        t.c_s = mk(U_MOVE_S)
        t.c_n = mk(U_MOVE_N)
        t.c_pass = mk(U_PASS)
        _CACHE[key] = t
    return t


def _dir_code(t, fx, fy, tx, ty):
    """kg_rules._step_toward, vectorised to U_MOVE_* / U_PASS codes."""
    dx = tx - fx
    dy = ty - fy
    ew = torch.where(dx > 0, t.c_e, t.c_w)
    ns = torch.where(dy > 0, t.c_s, t.c_n)
    c1 = (dx != 0) & (dx.abs() >= dy.abs())
    c2 = ~c1 & (dy != 0)
    c3 = ~c1 & ~c2 & (dx != 0)
    return torch.where(c2, ns, torch.where(c1 | c3, ew, t.c_pass))


def _nearest(t, mask, fx, fy):
    """min over mask (..., 100) of the (dist, y, x) lexicographic key --
    dist*100 + y*10 + x is exactly that order (y*10+x < 100 encodes (y, x)).
    Returns (key_min, tx, ty); key_min == BIG when the mask is empty."""
    dist = (t.xs - fx.unsqueeze(-1)).abs() + (t.ys - fy.unsqueeze(-1)).abs()
    key = torch.where(mask, dist * 100 + t.tile, BIG)
    kmin = key.min(-1).values
    tsel = kmin % 100
    return kmin, tsel % N, tsel // N


def _nearest_shed(t, fx, fy):
    """_nearest restricted to the four (always present) shed-access tiles."""
    dist = ((t.shed4x - fx.unsqueeze(-1)).abs()
            + (t.shed4y - fy.unsqueeze(-1)).abs())
    kmin = (dist * 100 + t.shed4t).min(-1).values
    tsel = kmin % 100
    return tsel % N, tsel // N


# ---------------------------------------------------------------------------
# insertion-order bookkeeping (_ord_seq <-> _inv_ord)
# ---------------------------------------------------------------------------

def _idx_init_ord(self):
    """First step_idx call: derive _ord_seq from the list representation so a
    warm start after step_raw steps stays exact."""
    self._ord_seq = torch.zeros_like(self.unit_inv, dtype=torch.int32)
    ctr = 1
    for b in range(self.B):
        for p in range(self.NUM_PLAYERS):
            for u, lst in enumerate(self._inv_ord[b][p]):
                for item in lst:
                    self._ord_seq[b, p, u, item] = ctr
                    ctr += 1
    self._ord_ctr = ctr


def _idx_inv_add(self, b, p, u, item, n):
    """engine_t._inv_add over an event subset (unique (b,p) rows)."""
    prev = self.unit_inv[b, p, u, item].to(torch.int64)
    self.unit_inv[b, p, u, item] = (prev + n).to(torch.int16)
    new = prev == 0
    if bool(new.any()):
        self._ord_seq[b[new], p[new], u, item[new]] = self._ord_ctr
    self._ord_ctr += 1


def _idx_inv_take(self, b, p, u, item, n=1):
    """engine_t._inv_take over an event subset; returns the success mask."""
    cur = self.unit_inv[b, p, u, item].to(torch.int64)
    ok = cur >= n
    bo, po, io = b[ok], p[ok], item[ok]
    newv = cur[ok] - n
    self.unit_inv[bo, po, u, io] = newv.to(torch.int16)
    z = newv == 0
    if bool(z.any()):
        self._ord_seq[bo[z], po[z], u, io[z]] = 0
    return ok


def _idx_sync_inv_ord(self):
    """Rebuild the _inv_ord lists from _ord_seq so the (host) _end_of_day
    drop walks items in dict insertion order, exactly as step_raw's would."""
    hn = self.hands_n.tolist()
    inv_ord = self._inv_ord
    for b in range(self.B):
        row = inv_ord[b]
        for p in range(self.NUM_PLAYERS):
            row[p] = [[] for _ in range(1 + hn[b][p])]
    present = (self.unit_inv > 0) & (self._ord_seq > 0)
    if not bool(present.any()):
        return
    rows = present.nonzero().tolist()    # sorted by (b, p, u, item)
    seqs = self._ord_seq[present].tolist()
    i, k = 0, len(rows)
    while i < k:
        b, p, u, _ = rows[i]
        j = i
        while j < k and rows[j][0] == b and rows[j][1] == p and rows[j][2] == u:
            j += 1
        pairs = sorted((seqs[m], rows[m][3]) for m in range(i, j))
        if u <= hn[b][p]:
            inv_ord[b][p][u] = [it for _, it in pairs]
        i = j


# ---------------------------------------------------------------------------
# decode (all from PRE-step state, exactly like the caller-side decode)
# ---------------------------------------------------------------------------

def _idx_decode_farmer(self, f_idx, fam, t):
    B, P = self.B, self.NUM_PLAYERS
    i64 = torch.int64
    fx = self.farmer_xy[:, :, 0].to(i64)
    fy = self.farmer_xy[:, :, 1].to(i64)
    pos_i = fy * N + fx

    fam0 = t.fam[f_idx]
    op0 = t.op[f_idx]
    arg0 = t.arg[f_idx]
    ws = t.ws[f_idx]
    ws_item = t.ws_item[f_idx]
    ws_want = t.ws_want[f_idx]

    inv0 = self.unit_inv[:, :, 0, :].to(i64)                 # farmer carry
    shed_inv = self.shed.to(i64)
    stocked = inv0.gather(2, ws_item.unsqueeze(-1)).squeeze(-1) > 0
    stock = shed_inv.gather(2, ws_item.unsqueeze(-1)).squeeze(-1)

    def fam_pick(fidx):
        return fam.gather(2, fidx.view(B, P, 1, 1).expand(B, P, 1, N * N)).squeeze(2)

    base_any = fam_pick(fam0).any(-1)
    # _with_stock: unstocked + shed stock + live targets -> shed detour;
    # unstocked otherwise -> None -> PASS.
    shed_leg = ws & ~stocked & (stock > 0) & base_any
    dead = ws & ~stocked & ~shed_leg
    dead |= (op0 == U_PLANT) & (
        self.seeds_t.to(i64).gather(2, arg0.unsqueeze(-1)).squeeze(-1) <= 0)
    dead |= (op0 == U_DROP) & ~(inv0 > 0).any(-1)

    family = torch.where(shed_leg, torch.full_like(fam0, F_SHED), fam0)
    family = torch.where(dead, torch.zeros_like(fam0), family)   # F_NONE
    tgt = fam_pick(family)
    any_t = tgt.any(-1)
    on_t = tgt.gather(2, pos_i.unsqueeze(-1)).squeeze(-1)
    _, tx, ty = _nearest(t, tgt, fx, fy)
    mv = _dir_code(t, fx, fy, tx, ty)

    engaged = family != F_NONE
    f_op = torch.where(dead, t.c_pass, op0)
    f_op = torch.where(engaged & ~any_t, t.c_pass, f_op)     # nothing to do
    on = engaged & any_t & on_t
    pickup = on & shed_leg
    f_op = torch.where(pickup, torch.full_like(f_op, U_PICKUP), f_op)
    f_op = torch.where(engaged & any_t & ~on_t, mv, f_op)    # one greedy step
    f_arg = torch.where(pickup, ws_item, arg0)
    f_qty = torch.where(pickup, torch.minimum(stock, ws_want),
                        torch.zeros_like(stock))
    return f_op, f_arg, f_qty


def _idx_decode_hands(self, pool_masks, t):
    """actions._hands_actions: per hand, greedy nearest untaken chore with
    strict-< first-pool-index tie-break == min (dist, family, y, x); the
    >=8-carry DROP leg. Serial over hand slots (the reference is), batch
    tensor ops within each.

    Distance is family-independent, so the untaken pool collapses to a
    per-tile "best remaining family" map mf (9 = none): min over
    dist*1024 + mf*100 + tile is exactly min over (dist, family, y, x), and
    a claim only has to refresh mf at the claimed tile."""
    B, P = self.B, self.NUM_PLAYERS
    i64 = torch.int64
    max_h = int(self.hands_n.max())
    if max_h == 0:
        return []
    avail = torch.stack(pool_masks, dim=2)                   # (B, P, 5, 100)
    mf = torch.where(avail, t.fam5.view(1, 1, 5, 1), 9).min(2).values
    avail = avail.clone()                                    # 'taken' support
    hn = self.hands_n.to(i64)
    carry = self.unit_inv.to(i64).sum(-1)                    # (B, P, 1+H)
    ops = []
    for u in range(max_h):
        act = hn > u
        hx = self.hands_xy[:, :, u, 0].to(i64)
        hy = self.hands_xy[:, :, u, 1].to(i64)
        hpos = hy * N + hx
        dist = (t.xs - hx.unsqueeze(-1)).abs() + (t.ys - hy.unsqueeze(-1)).abs()
        loaded = act & (carry[:, :, u + 1] >= 8)
        seek = act & ~loaded
        key = torch.where(mf < 9, dist * 1024 + mf * 100 + t.tile, BIG)
        kmin = key.min(-1).values
        has = seek & (kmin < BIG)
        sel = kmin % 1024                                    # family*100 + tile
        fsel = sel // 100
        tsel = sel % 100
        if bool(has.any()):
            nb, np_ = has.nonzero(as_tuple=True)             # claim entries
            ft, tt = fsel[nb, np_], tsel[nb, np_]
            avail[nb, np_, ft, tt] = False
            cols = avail[nb, np_, :, tt]                     # (K, 5)
            mf[nb, np_, tt] = torch.where(cols, t.fam5, 9).min(-1).values
        on_p = has & (hpos == tsel)
        pool_op = t.pool_op[fsel.clamp(max=4)]
        mv_p = _dir_code(t, hx, hy, tsel % N, tsel // N)
        op_u = torch.where(has, torch.where(on_p, pool_op, mv_p), t.c_pass)
        if bool(loaded.any()):
            sx, sy = _nearest_shed(t, hx, hy)
            on_shed = t.shed100[hpos]
            mv_s = _dir_code(t, hx, hy, sx, sy)
            drop_op = torch.where(on_shed, torch.full_like(op_u, U_DROP), mv_s)
            op_u = torch.where(loaded, drop_op, op_u)
        ops.append(op_u)
    return ops


def _idx_decode_market(self, m_idx, herd, day, t):
    """actions._market_action to (B, P, S) order-slot tensors. Quantities are
    pre-step by construction (this runs before the unit phase, like the
    caller-side decode)."""
    B, P = self.B, self.NUM_PLAYERS
    dev = self.device
    i64 = torch.int64
    S = self.max_market_orders
    m_op = torch.zeros((B, P, S), dtype=i64, device=dev)
    m_item = torch.zeros((B, P, S), dtype=i64, device=dev)
    m_rem = torch.zeros((B, P, S), dtype=i64, device=dev)
    shed9 = self.shed[:, :, :ET.N_MKT].to(i64)
    m = m_idx

    sell = (m >= 1) & (m <= 9)
    if bool(sell.any()):
        pi = (m - 1).clamp(min=0, max=ET.N_MKT - 1)
        if day >= R.LIQUIDATE_DAY:
            # liquidation-day compound decode: whole shed, primary product
            # first, the rest in PRODUCT_LIST order, MAX_ORDERS cap.
            sellable = shed9 > 0
            okey = torch.where(t.ar9 == pi.unsqueeze(-1),
                               torch.zeros_like(shed9), t.ar9 + 1)
            okey = torch.where(sellable, okey, BIG + t.ar9)  # unique keys
            order = okey.argsort(-1)
            for s in range(min(ET.N_MKT, S)):
                itq = order[..., s]
                val = sell & (okey.gather(2, itq.unsqueeze(-1)).squeeze(-1) < BIG)
                m_op[..., s] = torch.where(val, ET.OP_SELL, m_op[..., s])
                m_item[..., s] = torch.where(val, itq, m_item[..., s])
                m_rem[..., s] = torch.where(
                    val, shed9.gather(2, itq.unsqueeze(-1)).squeeze(-1),
                    m_rem[..., s])
        else:
            cnt = shed9.gather(2, pi.unsqueeze(-1)).squeeze(-1)
            val = sell & (cnt > 0)
            m_op[..., 0] = torch.where(val, ET.OP_SELL, m_op[..., 0])
            m_item[..., 0] = torch.where(val, pi, m_item[..., 0])
            m_rem[..., 0] = torch.where(val, cnt, m_rem[..., 0])

    seed = (m >= 10) & (m <= 14)
    m_op[..., 0] = torch.where(seed, ET.OP_SEED, m_op[..., 0])
    m_item[..., 0] = torch.where(seed, (m - 10).clamp(min=0), m_item[..., 0])
    m_rem[..., 0] = torch.where(seed, torch.ones_like(m), m_rem[..., 0])

    bw = m == 15                                             # BUY_WHEAT
    m_op[..., 0] = torch.where(bw, ET.OP_BUYP, m_op[..., 0])
    m_item[..., 0] = torch.where(bw, torch.zeros_like(m), m_item[..., 0])
    m_rem[..., 0] = torch.where(bw, (2 * herd).clamp(min=5), m_rem[..., 0])

    bf = m == 16                                             # BUY_FERT
    m_op[..., 0] = torch.where(bf, ET.OP_BUYP, m_op[..., 0])
    m_item[..., 0] = torch.where(bf, torch.full_like(m, ET.FERT_I), m_item[..., 0])
    m_rem[..., 0] = torch.where(bf, torch.ones_like(m), m_rem[..., 0])

    ba = (m >= 17) & (m <= 19)                               # BUY_<animal>
    m_op[..., 0] = torch.where(ba, ET.OP_ANIMAL, m_op[..., 0])
    m_item[..., 0] = torch.where(ba, (m - 17).clamp(min=0), m_item[..., 0])
    m_rem[..., 0] = torch.where(ba, torch.ones_like(m), m_rem[..., 0])

    land = m == 20
    m_op[..., 0] = torch.where(land, OP_LAND, m_op[..., 0])

    hire = m == 21
    if bool(hire.any()):
        # burst: up to 4 while fib(hires_today + j) <= 0.05 * money and the
        # crew stays under MAX_HANDS; empty burst falls back to one HIRE.
        hires = self.hires_today.to(i64).unsqueeze(-1) + t.j4
        fib = t.fib[hires.clamp(max=78)]
        cond = (((self.hands_n.to(i64).unsqueeze(-1) + t.j4) < A.MAX_HANDS)
                & (fib <= 0.05 * self.money.unsqueeze(-1)))
        k = cond.to(i64).cumprod(-1).sum(-1)                 # leading-true run
        for j in range(4):
            slot = hire & ((k > j) | ((j == 0) & (k == 0)))
            m_op[..., j] = torch.where(slot, OP_HIRE, m_op[..., j])
    return m_op, m_item, m_rem


# ---------------------------------------------------------------------------
# apply: one unit slot, batch-parallel (transcribes engine_t._apply_unit)
# ---------------------------------------------------------------------------

def _idx_apply_slot(self, u, op, arg, qty, day, t):
    B, P = self.B, self.NUM_PLAYERS
    i64 = torch.int64
    if u == 0:
        px = self.farmer_xy[:, :, 0].to(i64)
        py = self.farmer_xy[:, :, 1].to(i64)
    else:
        px = self.hands_xy[:, :, u - 1, 0].to(i64)
        py = self.hands_xy[:, :, u - 1, 1].to(i64)

    # -- moves (bounds-checked; LOCKED tiles are walkable) --
    mmask = (op >= U_MOVE_N) & (op <= U_MOVE_W)
    if bool(mmask.any()):
        opm = op.clamp(0, 4)
        nx = px + t.dx[opm]
        ny = py + t.dy[opm]
        okm = mmask & (nx >= 0) & (nx < N) & (ny >= 0) & (ny < N)
        nxw = torch.where(okm, nx, px).to(torch.int8)
        nyw = torch.where(okm, ny, py).to(torch.int8)
        if u == 0:
            self.farmer_xy[:, :, 0] = nxw
            self.farmer_xy[:, :, 1] = nyw
        else:
            self.hands_xy[:, :, u - 1, 0] = nxw
            self.hands_xy[:, :, u - 1, 1] = nyw

    def sub(code):
        m = op == code
        if not bool(m.any()):
            return None
        b, p = m.nonzero(as_tuple=True)
        return b, p, px[b, p], py[b, p]

    s = sub(U_WATER)
    if s:
        b, p, x, y = s
        ok = (self.kind[b, p, y, x] == ET.K_PLANT) & ~self.watered[b, p, y, x]
        b, p, x, y = b[ok], p[ok], x[ok], y[ok]
        if b.numel():
            self.watered[b, p, y, x] = True
            ci = self.crop[b, p, y, x].to(i64)
            aged = day - self.planted_day[b, p, y, x].to(i64)
            win = (~t.crop_ongoing[ci]
                   & ((t.crop_maxday[ci] + 1) // 2 <= aged)
                   & (aged <= t.crop_maxday[ci]))
            bonus = torch.where(self.fert_until[b, p, y, x].to(i64) >= day, 2, 1)
            cur = self.yield_units[b, p, y, x].to(i64)
            new = torch.minimum(t.crop_maxy[ci], cur + bonus)
            self.yield_units[b, p, y, x] = torch.where(win, new, cur).to(torch.int8)

    s = sub(U_HARVEST)
    if s:
        b, p, x, y = s
        kk = self.kind[b, p, y, x]
        yuv = self.yield_units[b, p, y, x].to(i64)
        ai = self.animal[b, p, y, x].to(i64)
        ci = self.crop[b, p, y, x].to(i64)
        aged = day - self.planted_day[b, p, y, x].to(i64)
        okp = (kk == ET.K_PLANT) & (yuv > 0) & (aged >= t.crop_first[ci])
        oks = ((kk == ET.K_COOP) | (kk == ET.K_PASTURE)) & (ai >= 0) & (yuv > 0)
        ok = okp | oks
        if bool(ok.any()):
            b2, p2, x2, y2 = b[ok], p[ok], x[ok], y[ok]
            units = yuv[ok]
            item = torch.where(okp[ok], ci[ok],
                               t.animal_product[ai[ok].clamp(min=0)])
            self.yield_units[b2, p2, y2, x2] = 0
            done_p = okp[ok] & ~t.crop_ongoing[ci[ok]]       # one-shot crop
            b3, p3, x3, y3 = b2[done_p], p2[done_p], x2[done_p], y2[done_p]
            if b3.numel():
                self.kind[b3, p3, y3, x3] = ET.K_EMPTY
                self.animal[b3, p3, y3, x3] = -1
            self._idx_inv_add(b2, p2, u, item, units)

    s = sub(U_FEED)
    if s:
        b, p, x, y = s
        kk = self.kind[b, p, y, x]
        ok = (((kk == ET.K_COOP) | (kk == ET.K_PASTURE))
              & (self.animal[b, p, y, x] >= 0) & ~self.fed[b, p, y, x])
        b2, p2, x2, y2 = b[ok], p[ok], x[ok], y[ok]
        if b2.numel():
            took = self._idx_inv_take(
                b2, p2, u, torch.full_like(b2, ET.WHEAT_I), 1)
            b3, p3, x3, y3 = b2[took], p2[took], x2[took], y2[took]
            if b3.numel():
                self.fed[b3, p3, y3, x3] = True

    s = sub(U_CARE)
    if s:
        b, p, x, y = s
        kk = self.kind[b, p, y, x]
        ok = (((kk == ET.K_COOP) | (kk == ET.K_PASTURE))
              & (self.animal[b, p, y, x] >= 0) & ~self.cared[b, p, y, x])
        b2, p2, x2, y2 = b[ok], p[ok], x[ok], y[ok]
        if b2.numel():
            self.cared[b2, p2, y2, x2] = True

    s = sub(U_COLLECT)
    if s:
        b, p, x, y = s
        kk = self.kind[b, p, y, x]
        ok = (((kk == ET.K_COOP) | (kk == ET.K_PASTURE))
              & (self.animal[b, p, y, x] >= 0) & self.fert_avail[b, p, y, x])
        b2, p2, x2, y2 = b[ok], p[ok], x[ok], y[ok]
        if b2.numel():
            self.fert_avail[b2, p2, y2, x2] = False
            self._idx_inv_add(b2, p2, u, torch.full_like(b2, ET.FERT_I), 1)

    s = sub(U_FERTILIZE)
    if s:
        b, p, x, y = s
        ok = self.kind[b, p, y, x] == ET.K_PLANT
        b2, p2, x2, y2 = b[ok], p[ok], x[ok], y[ok]
        if b2.numel():
            took = self._idx_inv_take(
                b2, p2, u, torch.full_like(b2, ET.FERT_I), 1)
            b3, p3, x3, y3 = b2[took], p2[took], x2[took], y2[took]
            if b3.numel():
                self.fert_until[b3, p3, y3, x3] = torch.maximum(
                    self.fert_until[b3, p3, y3, x3].to(i64),
                    torch.full_like(b3, day + 2)).to(torch.int16)

    s = sub(U_DIG)
    if s:
        b, p, x, y = s
        kk = self.kind[b, p, y, x]
        struct = (kk == ET.K_COOP) | (kk == ET.K_PASTURE)
        ok = ((kk != ET.K_EMPTY) & (kk != ET.K_LOCKED)
              & ~(struct & (self.animal[b, p, y, x] >= 0)))
        b2, p2, x2, y2 = b[ok], p[ok], x[ok], y[ok]
        if b2.numel():
            self.kind[b2, p2, y2, x2] = ET.K_EMPTY
            self.animal[b2, p2, y2, x2] = -1

    for code, kcode in ((U_BUILD_COOP, ET.K_COOP), (U_BUILD_PASTURE, ET.K_PASTURE)):
        s = sub(code)
        if s:
            b, p, x, y = s
            ok = self.kind[b, p, y, x] == ET.K_EMPTY
            b2, p2, x2, y2 = b[ok], p[ok], x[ok], y[ok]
            if b2.numel():
                self.kind[b2, p2, y2, x2] = kcode
                self.animal[b2, p2, y2, x2] = -1

    s = sub(U_PLANT)
    if s:
        # Atomic PLANT validation degenerates to the plain seed check here:
        # decode emits at most one PLANT per (lane, player) per turn (hands
        # never plant), so per-crop demand is <= 1.
        b, p, x, y = s
        ci = arg[b, p]
        ok = ((self.kind[b, p, y, x] == ET.K_EMPTY)
              & (self.seeds_t[b, p, ci] > 0))
        b2, p2, x2, y2, c2 = b[ok], p[ok], x[ok], y[ok], ci[ok]
        if b2.numel():
            self.seeds_t[b2, p2, c2] = (self.seeds_t[b2, p2, c2].to(i64) - 1
                                        ).to(torch.int16)
            ong = t.crop_ongoing[c2]
            self.kind[b2, p2, y2, x2] = ET.K_PLANT
            self.animal[b2, p2, y2, x2] = -1
            self.crop[b2, p2, y2, x2] = c2.to(torch.int8)
            self.planted_day[b2, p2, y2, x2] = day
            self.watered[b2, p2, y2, x2] = False
            self.consec_unwatered[b2, p2, y2, x2] = 1  # planting day counts
            self.yield_units[b2, p2, y2, x2] = torch.where(
                ong, torch.zeros_like(c2), torch.ones_like(c2)).to(torch.int8)
            self.mls[b2, p2, y2, x2] = torch.where(
                ong, torch.full_like(c2, -1),
                (day + t.crop_maxday[c2] + 1) * self.turns_per_day
            ).to(torch.int32)
            self.fert_until[b2, p2, y2, x2] = -1

    s = sub(U_PLACE)
    if s:
        b, p, x, y = s
        ai = arg[b, p]
        on_struct = ((self.kind[b, p, y, x].to(i64) == t.animal_struct[ai])
                     & (self.animal[b, p, y, x] < 0))
        b2, p2, x2, y2, a2 = b[on_struct], p[on_struct], x[on_struct], y[on_struct], ai[on_struct]
        if b2.numel():
            took = self._idx_inv_take(b2, p2, u, ET.N_MKT + a2, 1)
            b3, p3, x3, y3, a3 = b2[took], p2[took], x2[took], y2[took], a2[took]
            if b3.numel():
                self.animal[b3, p3, y3, x3] = a3.to(torch.int8)
                self.placed_day[b3, p3, y3, x3] = day
                self.yield_units[b3, p3, y3, x3] = 0
                self.consec_unfed[b3, p3, y3, x3] = 0
                self.fed[b3, p3, y3, x3] = False
                self.cared[b3, p3, y3, x3] = False
                self.fert_avail[b3, p3, y3, x3] = False
                self.pending[b3, p3, y3, x3] = 0
        # off-structure PLACE falls through to the shed-drop path (n = 1)
        off = ~on_struct & t.shed100[y * N + x]
        b2, p2, a2 = b[off], p[off], ai[off]
        if b2.numel():
            room_ok = (self.shed[b2, p2].to(i64).sum(-1) < self.shed_capacity)
            have_ok = self.unit_inv[b2, p2, u, ET.N_MKT + a2] >= 1
            ok2 = room_ok & have_ok
            b3, p3, a3 = b2[ok2], p2[ok2], a2[ok2]
            if b3.numel():
                took = self._idx_inv_take(b3, p3, u, ET.N_MKT + a3, 1)
                # have_ok made the take unconditional; deposit the unit
                self.shed[b3, p3, ET.N_MKT + a3] = (
                    self.shed[b3, p3, ET.N_MKT + a3].to(i64) + 1).to(torch.int16)

    s = sub(U_PICKUP)
    if s:
        b, p, x, y = s
        adj = t.shed100[y * N + x]
        b2, p2 = b[adj], p[adj]
        if b2.numel():
            item = arg[b2, p2]
            n = torch.minimum(qty[b2, p2], self.shed[b2, p2, item].to(i64))
            ok = n > 0
            b3, p3, i3, n3 = b2[ok], p2[ok], item[ok], n[ok]
            if b3.numel():
                self.shed[b3, p3, i3] = (self.shed[b3, p3, i3].to(i64) - n3
                                         ).to(torch.int16)
                self._idx_inv_add(b3, p3, u, i3, n3)

    s = sub(U_DROP)
    if s:
        b, p, x, y = s
        adj = t.shed100[y * N + x]
        b2, p2 = b[adj], p[adj]
        if b2.numel():
            # dict-insertion-order deposit, capacity-limited per item;
            # overflow is discarded (engine_t DROP, vectorised over events
            # via the _ord_seq ranks -- events have unique (lane, player)).
            seqs = self._ord_seq[b2, p2, u, :].to(i64)
            cnts = self.unit_inv[b2, p2, u, :].to(i64)
            keys = torch.where(cnts > 0, seqs, BIG)
            order = keys.argsort(-1)
            room = (self.shed_capacity
                    - self.shed[b2, p2].to(i64).sum(-1)).clamp(min=0)
            for r in range(NI):
                it = order[:, r]
                valid = keys.gather(1, it.unsqueeze(-1)).squeeze(-1) < BIG
                nn = cnts.gather(1, it.unsqueeze(-1)).squeeze(-1)
                take = torch.minimum(nn, room) * valid
                self.shed[b2, p2, it] = (self.shed[b2, p2, it].to(i64) + take
                                         ).to(torch.int16)
                room = room - take
            self.unit_inv[b2, p2, u, :] = 0
            self._ord_seq[b2, p2, u, :] = 0


# ---------------------------------------------------------------------------
# market processing (order-slot loop; reuses engine_t's lockstep)
# ---------------------------------------------------------------------------

def _idx_do_hire(self, b, p, t):
    """engine_t._do_hire over an event subset (one order per (lane, player)
    per index, so rows are unique; farms are independent). Exact python-float
    money arithmetic is preserved: money is integer-valued float64 and
    fib costs are exact in float64 through fib(78).

    step_raw's list-side bookkeeping (_inv_ord gaining an empty inventory) is
    skipped: the new hand's counts and _ord_seq rows are already zero, and
    the lists are rebuilt wholesale at the end-of-day sync."""
    i64 = torch.int64
    hires = self.hires_today[b, p].to(i64)
    cost = t.fib_int[hires.clamp(max=78)] * self.hire_mult
    money = self.money[b, p]
    ok = money >= cost.to(torch.float64)
    if not bool(ok.any()):
        return
    bo, po = b[ok], p[ok]
    hn = self.hands_n[bo, po].to(i64)
    if bool((hn >= self.H).any()):
        raise OverflowError(f"more than {self.H} hands in lanes "
                            f"{bo[hn >= self.H].tolist()}")
    self.money[bo, po] = money[ok] - cost[ok].to(torch.float64)
    self.hires_today[bo, po] = (hires[ok] + 1).to(torch.int16)
    # Spawn: first free shed-access tile (NWSE), ties by min occupancy --
    # min over occupancy*4 + NWSE index, exactly _spawn_hand's sort key.
    fx = self.farmer_xy[bo, po, 0].to(i64)
    fy = self.farmer_xy[bo, po, 1].to(i64)
    occ = ((fx.unsqueeze(-1) == t.shed4x)
           & (fy.unsqueeze(-1) == t.shed4y)).to(i64)
    hxs = self.hands_xy[bo, po, :, 0].to(i64)                # (K, H)
    hys = self.hands_xy[bo, po, :, 1].to(i64)
    validh = (torch.arange(self.H, dtype=i64, device=self.device)
              < hn.unsqueeze(-1))
    occ = occ + (((hxs.unsqueeze(-1) == t.shed4x)
                  & (hys.unsqueeze(-1) == t.shed4y))
                 & validh.unsqueeze(-1)).sum(1)
    sel = (occ * 4 + t.ar4).min(-1).values % 4
    self.hands_xy[bo, po, hn, 0] = t.shed4x[sel].to(torch.int8)
    self.hands_xy[bo, po, hn, 1] = t.shed4y[sel].to(torch.int8)
    self.hands_n[bo, po] = (hn + 1).to(torch.int8)


def _idx_do_land(self, b, p, t):
    """engine_t._do_buy_land over an event subset."""
    i64 = torch.int64
    n_extra = self.quad_unlocked[b, p].to(i64).sum(-1)
    room = n_extra < len(E.LAND_ORDER)
    cost = t.land_prices[n_extra.clamp(max=len(E.LAND_PRICES) - 1)]
    ok = room & (self.money[b, p] >= cost)
    if not bool(ok.any()):
        return
    bo, po, ne = b[ok], p[ok], n_extra[ok]
    self.money[bo, po] = self.money[bo, po] - cost[ok]
    self.quad_unlocked[bo, po, ne] = True
    rows = self.kind[bo, po]                                 # (K, N, N)
    sel = self._quad_t[ne] & (rows == ET.K_LOCKED)
    self.kind[bo, po] = torch.where(
        sel, torch.full_like(rows, ET.K_EMPTY), rows)


def _idx_market(self, m_op, m_item, m_rem, t):
    used = (m_op != ET.OP_DEAD).any(0).any(0).tolist()
    gmax = 0
    for i, live in enumerate(used):
        if live:
            gmax = i + 1
    for i in range(gmax):
        opi = m_op[..., i]
        hire = opi == OP_HIRE
        if bool(hire.any()):
            self._idx_do_hire(*hire.nonzero(as_tuple=True), t)
        land = opi == OP_LAND
        if bool(land.any()):
            self._idx_do_land(*land.nonzero(as_tuple=True), t)
        live_op = torch.where(opi >= OP_HIRE, torch.zeros_like(opi), opi)
        if bool((live_op != ET.OP_DEAD).any()):
            self._market_lockstep(live_op, m_item[..., i], m_rem[..., i])
        self._refresh_prices()


# ---------------------------------------------------------------------------
# step_idx
# ---------------------------------------------------------------------------

def step_idx(self, f_idx, m_idx):
    """Advance every lane one turn from action-head indices.

    f_idx, m_idx: (B, 2) integer tensors / array-likes -- per lane, per
    player, indices into actions.FARMER_ACTIONS / actions.MARKET_ACTIONS.
    Byte-equivalent to step_raw fed with actions.decode(...) per lane.
    """
    if self.done:
        return
    if self.N != N or self.NUM_PLAYERS != 2:
        raise ValueError("step_idx supports the standard 10x10 two-player game")
    dev = self.device
    t = _tabs(dev)
    i64 = torch.int64
    B, P = self.B, self.NUM_PLAYERS
    step = self._step
    day = step // self.turns_per_day

    f_idx = torch.as_tensor(f_idx, dtype=i64, device=dev).reshape(B, P)
    m_idx = torch.as_tensor(m_idx, dtype=i64, device=dev).reshape(B, P)

    if getattr(self, "_ord_seq", None) is None:
        self._idx_init_ord()

    # ---- one shared pre-step board scan (actions.analyze's families) ----
    kind = self.kind.reshape(B, P, N * N)
    anim_f = self.animal.reshape(B, P, N * N) >= 0
    plant_f = kind == ET.K_PLANT
    yu_pos = self.yield_units.reshape(B, P, N * N) > 0
    age = day - self.planted_day.reshape(B, P, N * N).to(i64)
    harv_f = ((plant_f & yu_pos
               & (age >= t.crop_first[self.crop.reshape(B, P, N * N).to(i64)]))
              | (anim_f & yu_pos))
    unwat_f = plant_f & ~self.watered.reshape(B, P, N * N)
    unfert_f = plant_f & (self.fert_until.reshape(B, P, N * N).to(i64) < day)
    unfed_f = anim_f & ~self.fed.reshape(B, P, N * N)
    uncared_f = anim_f & ~self.cared.reshape(B, P, N * N)
    fready_f = anim_f & self.fert_avail.reshape(B, P, N * N)
    weed_f = kind == ET.K_WEED
    empty_f = kind == ET.K_EMPTY
    coopf_f = (kind == ET.K_COOP) & ~anim_f
    pastf_f = (kind == ET.K_PASTURE) & ~anim_f
    herd = anim_f.sum(-1)                                    # BUY_WHEAT scale
    fam = torch.stack(
        [torch.zeros_like(empty_f), empty_f, weed_f, unwat_f, unfert_f,
         harv_f, unfed_f, uncared_f, fready_f, coopf_f, pastf_f,
         t.shed100.view(1, 1, N * N).expand(B, P, N * N)], dim=2)

    # ---- decode everything from the pre-step state ----
    f_op, f_arg, f_qty = self._idx_decode_farmer(f_idx, fam, t)
    hand_ops = self._idx_decode_hands(
        [harv_f, unwat_f, uncared_f, fready_f, weed_f], t)
    m_op, m_item, m_rem = self._idx_decode_market(m_idx, herd, day, t)

    # ---- apply: unit phase (slot-serial, batch-parallel), then market ----
    zero = torch.zeros((B, P), dtype=i64, device=dev)
    self._idx_apply_slot(0, f_op, f_arg, f_qty, day, t)
    for u, op_u in enumerate(hand_ops):
        self._idx_apply_slot(u + 1, op_u, zero, zero, day, t)
    self._idx_market(m_op, m_item, m_rem, t)

    self._town_consume(step)
    self._decay_plants(step)
    if (step + 1) % self.turns_per_day == 0:
        self._idx_sync_inv_ord()
        self._end_of_day(day)
        self._ord_seq.zero_()
        self._ord_ctr = 1

    next_step = step + 1
    self._step = next_step
    self.day = next_step // self.turns_per_day
    self.hour = next_step % self.turns_per_day
    if step >= self.episode_steps - 2:
        self.done = True
        self.reward = self.money.clone()


# ---- attach to EpisodeT ---------------------------------------------------

ET.EpisodeT.step_idx = step_idx
ET.EpisodeT._idx_init_ord = _idx_init_ord
ET.EpisodeT._idx_inv_add = _idx_inv_add
ET.EpisodeT._idx_inv_take = _idx_inv_take
ET.EpisodeT._idx_sync_inv_ord = _idx_sync_inv_ord
ET.EpisodeT._idx_decode_farmer = _idx_decode_farmer
ET.EpisodeT._idx_decode_hands = _idx_decode_hands
ET.EpisodeT._idx_decode_market = _idx_decode_market
ET.EpisodeT._idx_apply_slot = _idx_apply_slot
ET.EpisodeT._idx_do_hire = _idx_do_hire
ET.EpisodeT._idx_do_land = _idx_do_land
ET.EpisodeT._idx_market = _idx_market
