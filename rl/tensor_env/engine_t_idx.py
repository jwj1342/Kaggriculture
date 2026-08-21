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

Host-side work that remains, and why (B4b):
  * per step, four host reads: max hands (hand-slot loop bound), one (S, 18)
    op-presence table for the unit slots, one (3, S) presence table for the
    market order indices, and the deferred-error flag; plus one bool per
    market lockstep iteration (loop termination) and per-op nonzero() calls
    inside the unit slots (event subsets -- cheap on CPU, a sync each on a
    GPU; the remaining GPU-side item). The reference itself is serial over
    every one of these loops; nothing here loops over lanes.
  * per day, the MT19937 word pull (engine_t._eod_rng) and one max over
    the empty-tile counts that sizes it.
  HIRE / BUY_LAND atomics are vectorised over their per-order-index event
  subsets (_idx_do_hire / _idx_do_land transcribe engine_t._do_hire /
  _do_buy_land, including the exact float money arithmetic and the
  spawn-tile occupancy sort key).

Insertion-order bookkeeping: engine_np unit inventories are dicts, and the
two capacity-limited deposit paths (DROP, end-of-day drop) walk them in
insertion order. step_raw tracks that with per-lane python lists
(`_inv_ord`); step_idx tracks it as `_ord_seq` (B,P,1+H,I) int32 -- the
monotone counter value at the moment an item's count went 0 -> positive
(0 = absent). Ascending _ord_seq over count>0 items IS dict insertion order
(deletion on zero plus re-insertion at the end matches re-adding at a fresh,
higher counter). Both deposit paths are closed-form tensor ops on those
ranks (engine_t._eod_drop_seq, the U_DROP block); the list representation
is derived from the lists once at the first step_idx call (warm start after
step_raw) and both are reset at every day boundary. Do not interleave
step_raw and step_idx calls on one instance within a day (across day
boundaries both stay consistent). A per-unit carried total (`_idx_carry`)
is kept alongside for the dispatcher's >=8-carry test.

CPU kernel idioms (engine_t.cst / sel / sel0 / anyt / isel, position LUTs in
_tabs, index_select / index_copy_ on flat views): see engine_t's module
comment; every one is an exact integer/boolean identity.

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
cst, sel, sel0, anyt, isel = ET.cst, ET.sel, ET.sel0, ET.anyt, ET.isel  # B4b kernel idioms

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
assert A.MARKET_ACTIONS[22:31] == [f"SELL_HALF_{p}" for p in A.PRODUCT_LIST]
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
                 "shed100", "crop_first", "crop_maxday", "crop_maxy",
                 "crop_ongoing", "animal_struct", "animal_product",
                 "fib", "fib_int", "land_prices", "ar9", "j4", "ar4",
                 "shed4x", "shed4y", "shed4t", "c_pass",
                 # B4b LUTs -- one gather replaces an elementwise chain; see
                 # _tabs for the exact definitions.
                 "dir_lut", "key100_lut", "key1024_lut", "shed_dir",
                 "crop_first_i8", "u_arange", "hand_op_lut", "mfk_lut",
                 "pack_clear", "mop_lut", "mitem_lut", "mrem_lut", "move_lut",
                 "move_code", "plant_deadline")


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
        t.plant_deadline = mk([A.PLANT_DEADLINE[c] for c in A.CROP_LIST])
        t.ws = torch.tensor(_LUT_WS, dtype=torch.bool, device=device)
        t.ws_item = mk(_LUT_WS_ITEM)
        t.ws_want = mk(_LUT_WS_WANT)
        shed = torch.zeros(N * N, dtype=torch.bool, device=device)
        for (x, y) in A._SHED:
            shed[y * N + x] = True
        t.shed100 = shed
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
        t.c_pass = mk(U_PASS)

        # ---- B4b position LUTs, built on the host from the reference
        # semantics (kg_rules._step_toward for the move code; the (dist, y,
        # x) lexicographic key for nearest-target ties) ----
        code_of = {None: U_PASS, "NORTH": U_MOVE_N, "SOUTH": U_MOVE_S,
                   "EAST": U_MOVE_E, "WEST": U_MOVE_W}
        dir_lut = [0] * (N * N * N * N)          # [from_pos * 100 + to_pos]
        key100 = [0] * (N * N * N * N)           # dist * 100 + to_pos
        key1024 = [0] * (N * N * N * N)          # dist * 1024 + to_pos
        for fp in range(N * N):
            fx, fy = fp % N, fp // N
            for tp in range(N * N):
                tx, ty = tp % N, tp // N
                d = abs(tx - fx) + abs(ty - fy)
                dir_lut[fp * N * N + tp] = code_of[R._step_toward(fx, fy, tx, ty)]
                key100[fp * N * N + tp] = d * 100 + tp
                key1024[fp * N * N + tp] = d * 1024 + tp
        t.dir_lut = mk(dir_lut)
        t.key100_lut = torch.tensor(key100, dtype=torch.int32,
                                    device=device).view(N * N, N * N)
        t.key1024_lut = torch.tensor(key1024, dtype=torch.int32,
                                     device=device).view(N * N, N * N)
        # loaded-hand leg: DROP when standing on a shed-access tile, else one
        # step toward the nearest one (min over (dist, y, x) == min key100).
        shed_dir = []
        shed_ts = [y * N + x for (x, y) in A._SHED]
        for fp in range(N * N):
            if fp in shed_ts:
                shed_dir.append(U_DROP)
            else:
                best = min(shed_ts, key=lambda tp: key100[fp * N * N + tp])
                shed_dir.append(dir_lut[fp * N * N + best])
        t.shed_dir = mk(shed_dir)
        t.crop_first_i8 = torch.tensor(ET.CROP_FIRST, dtype=torch.int8,
                                       device=device)
        t.u_arange = torch.arange(1024, dtype=i64, device=device)   # >= 1 + max_hands
        # hand slot: (position, sel = family*100 + tile) -> op: the pool op
        # when standing on the tile, else the step toward it. sel >= 500
        # (no family) is unreachable when a target exists; filled with PASS.
        hol = [U_PASS] * (N * N * 1024)
        for fp in range(N * N):
            for f in range(5):
                for tp in range(N * N):
                    hol[fp * 1024 + f * 100 + tp] = (
                        _POOL_OPS[f] if fp == tp else dir_lut[fp * N * N + tp])
        t.hand_op_lut = mk(hol)
        # packed pool code (bit 4-f set <=> family f available) -> mfk =
        # 100 * (lowest available family), BIG when none.
        mfk_lut = []
        for code in range(32):
            fams = [f for f in range(5) if code & (1 << (4 - f))]
            mfk_lut.append(fams[0] * 100 if fams else BIG)
        t.mfk_lut = torch.tensor(mfk_lut, dtype=torch.int32, device=device)
        t.pack_clear = torch.tensor([~(1 << (4 - f)) & 0x1F for f in range(5)],
                                    dtype=torch.int8, device=device)
        # market head index -> slot-0 (op, item, unit-quantity) -- SELL keeps
        # the shed count and BUY_WHEAT the herd-scaled quantity at decode.
        mop = [ET.OP_DEAD] + [ET.OP_SELL] * 9 + [ET.OP_SEED] * 5 + [ET.OP_BUYP] * 2 \
            + [ET.OP_ANIMAL] * 3 + [OP_LAND, OP_HIRE] + [ET.OP_SELL] * 9
        mitem = [0] + list(range(9)) + list(range(5)) + [ET.WHEAT_I, ET.FERT_I] \
            + list(range(3)) + [0, 0] + list(range(9))
        mrem = [0] + [0] * 9 + [1] * 5 + [0, 1] + [1] * 3 + [0, 0] + [0] * 9
        assert len(mop) == len(mitem) == len(mrem) == A.N_MARKET == 31
        t.mop_lut = mk(mop)
        t.mitem_lut = mk(mitem)
        t.mrem_lut = mk(mrem)
        # unit op code -> move code (1..4 for the four moves, else 0 = stay);
        # (position, move code) -> new position, bounds-checked (E.FARMER_MOVES)
        t.move_code = mk([c if U_MOVE_N <= c <= U_MOVE_W else 0 for c in range(18)])
        mv_d = {U_MOVE_N: E.FARMER_MOVES["NORTH"], U_MOVE_S: E.FARMER_MOVES["SOUTH"],
                U_MOVE_E: E.FARMER_MOVES["EAST"], U_MOVE_W: E.FARMER_MOVES["WEST"]}
        move_lut = []
        for fp in range(N * N):
            fx, fy = fp % N, fp // N
            for c in range(5):
                dx, dy = mv_d.get(c, (0, 0))
                nx, ny = fx + dx, fy + dy
                move_lut.append(ny * N + nx if 0 <= nx < N and 0 <= ny < N else fp)
        t.move_lut = mk(move_lut)
        _CACHE[key] = t
    return t


def _nearest(t, mask, pos):
    """min over mask (..., 100) of the (dist, y, x) lexicographic key --
    dist*100 + y*10 + x is exactly that order (y*10+x < 100 encodes (y, x));
    the key row for the unit's position is a LUT gather. Masked-in tiles are
    shifted by -BIG so the min lands on them whenever any exists. Returns
    (found mask, target tile index -- garbage where not found)."""
    key = t.key100_lut.index_select(0, pos.reshape(-1)).view(mask.shape)
    key = key - mask.to(torch.int32) * BIG
    kmin = key.amin(-1)
    return kmin < 0, ((kmin + BIG) % 100).long()


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
    # per-unit carried total (B, P, 1+H) int16 == unit_inv.sum(-1); kept
    # incrementally by the three unit_inv writers below + the two zeroings
    # (U_DROP, end of day) so the >=8-carry test is a (B, P, U) read.
    self._idx_carry = self.unit_inv.sum(-1, dtype=torch.int16)


def _idx_inv_add(self, i, u, item, n):
    """engine_t._inv_add over an event subset. i: (K,) flat (lane*P + player)
    unit-row indices (unique per call), item: (K,) item indices, n: int or
    (K,) int64. No host sync: the insertion rank is a masked write."""
    HI = (1 + self.H) * NI
    li = i * HI + u * NI + item
    inv_f = self.unit_inv.view(-1)
    prev = inv_f.index_select(0, li).to(torch.int64)
    inv_f.index_copy_(0, li, (prev + n).to(torch.int16))
    ci = i * (1 + self.H) + u
    car_f = self._idx_carry.view(-1)
    car_f.index_copy_(0, ci, car_f.index_select(0, ci)
                      + (n if isinstance(n, int) else n.to(torch.int16)))
    seq_f = self._ord_seq.view(-1)
    seq = seq_f.index_select(0, li)
    seq_f.index_copy_(0, li, torch.where(
        prev == 0, torch.full_like(seq, self._ord_ctr), seq))
    self._ord_ctr += 1


def _idx_inv_take(self, i, u, item, n=1):
    """engine_t._inv_take over an event subset; returns the success mask."""
    HI = (1 + self.H) * NI
    li = i * HI + u * NI + item
    inv_f = self.unit_inv.view(-1)
    cur = inv_f.index_select(0, li).to(torch.int64)
    ok = cur >= n
    newv = torch.where(ok, cur - n, cur)
    inv_f.index_copy_(0, li, newv.to(torch.int16))
    ci = i * (1 + self.H) + u
    car_f = self._idx_carry.view(-1)
    car_f.index_copy_(0, ci, car_f.index_select(0, ci) - (cur - newv).to(torch.int16))
    seq_f = self._ord_seq.view(-1)
    seq = seq_f.index_select(0, li)
    seq_f.index_copy_(0, li, torch.where(ok & (newv == 0), torch.zeros_like(seq), seq))
    return ok


# ---------------------------------------------------------------------------
# decode (all from PRE-step state, exactly like the caller-side decode)
# ---------------------------------------------------------------------------

def _idx_decode_farmer(self, f_idx, fam, t):
    """fam: (12, B, P, 100) bool family planes (step_idx's scan buffer)."""
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

    fam_flat = fam.view(12 * B * P, N * N)
    ar_bp = self._idx_ar_bp                                  # arange(B*P)

    def fam_pick(fidx):                                      # (B, P, 100)
        return fam_flat.index_select(0, fidx.view(-1) * (B * P) + ar_bp).view(B, P, N * N)

    base_any = anyt(fam_pick(fam0))
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
    any_t = anyt(tgt)
    on_t = tgt.gather(2, pos_i.unsqueeze(-1)).squeeze(-1)
    _, tsel = _nearest(t, tgt, pos_i)
    mv = t.dir_lut.index_select(0, (pos_i * (N * N) + tsel).view(-1)).view(B, P)

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


def _idx_decode_hands(self, pool_masks, t, h_tasks=None, feed_plane=None,
                      plant_kit=None):
    """actions._hands_actions: per hand, greedy nearest untaken chore with
    strict-< first-pool-index tie-break == min (dist, family, y, x); the
    >=8-carry DROP leg. Serial over hand slots (the reference is), batch
    tensor ops within each.

    h_tasks (B, P, >=max_h) int64 or None: per-hand task indices into
    actions.HAND_TASKS (0 AUTO, 1 IDLE, 2.. one chore family). AUTO slots
    keep the classic cascade (the mfk minimum over available families);
    a task slot's per-tile key component becomes "family f if its bit is
    still set at that tile, else BIG" -- same claims, same op LUT, so the
    exclusion semantics against AUTO hands are shared, exactly as in
    actions._hands_actions_multi. IDLE wins over the DROP leg (the CPU
    reference checks IDLE before the carry test). None == all-AUTO.

    FEED (task index 7) is task-only and consumable, so it never enters
    the packed pool: AUTO's 5-family mfk machinery is untouched by
    construction (all-AUTO stays byte-identical to the cascade). FEED
    slots ride `feed_plane` (the caller's unfed-tile plane) with their own
    claims -- key constant 500 = family 5, so ties break dist-then-tile
    exactly like the CPU pool, where FEED entries come last -- and a
    wheat-less FEED hand runs the shed PICKUP leg: qty = min(stock left
    after earlier fetchers this turn, 8 - carry), PASS when the stock or
    the unclaimed targets run out, DROP first when loaded (mirrors
    actions._hands_actions_multi line for line).

    PLANT (task index 8) rides `plant_kit` the same way: (plane,
    crop_flat, budget_flat) where plane is the empty-tile plane,
    crop_flat (B*P,) the farm's most-held seed (argmax = CPU's first-max
    over CROP_LIST), and budget_flat (B*P,) the pre-step seed stock --
    no farmer adjustment on either side; same-turn contention resolves
    in the slot-serial apply, the reference's unit order. Key constant
    600 = family 6 (PLANT pool entries come after FEED on the CPU);
    claims are serial in hand order and each claim -- walking hands
    included -- reserves one seed from the budget, exactly the CPU's
    plant_left. A loaded PLANT hand takes the generic DROP leg (the CPU
    carry test precedes target selection for every task but FEED).

    Distance is family-independent, so the untaken pool collapses to a
    per-tile "best remaining family" map mf (9 = none): min over
    dist*1024 + mf*100 + tile is exactly min over (dist, family, y, x), and
    a claim only has to refresh mf at the claimed tile. B4b form: the pool
    is one packed int8 map (bit 4-f = family f still available), mf comes
    from a 32-entry LUT on it and is kept pre-scaled (mfk = mf*100, BIG when
    none) so a slot costs one gather, one add and one amin over (B, P, 100)
    plus (B, P) bookkeeping; a claim clears one bit and refreshes one mfk
    entry through index_put_s aimed at a dummy slot where the hand claims
    nothing (no host sync); the op is one LUT gather on (position, selected
    family*100 + tile), the loaded-hand leg another on position (DROP on a
    shed tile, else the step toward the nearest one). pool_masks: 5
    (B, P, 100) bool planes in dispatch priority order.

    Returns (ops, args, qtys): per hand slot (B, P) tensors; args/qtys are
    all-zero except FEED's PICKUP leg (arg = WHEAT item, its qty)."""
    B, P = self.B, self.NUM_PLAYERS
    i64, i32, i8 = torch.int64, torch.int32, torch.int8
    max_h = int(self.hands_n.max())
    if max_h == 0:
        return [], [], []
    BP = B * P
    NN = N * N
    dev = self.device
    packed = torch.zeros(BP * NN + 1, dtype=i8, device=dev)  # + dummy slot
    pk = packed[:BP * NN]
    pk.copy_(pool_masks[0].view(i8).view(-1))
    for f in range(1, 5):
        pk.mul_(2).add_(pool_masks[f].view(i8).view(-1))
    mfk_flat = torch.empty(BP * NN + 1, dtype=i32, device=dev)
    mfk_flat[:BP * NN] = t.mfk_lut.index_select(0, pk.int())
    mfk = mfk_flat[:BP * NN].view(B, P, NN)
    keybuf = torch.empty((B, P, NN), dtype=i32, device=dev)
    hn = self.hands_n.to(i64).unsqueeze(-1)                  # (B, P, 1)
    hxy = self.hands_xy[:, :, :max_h].to(i64)                # (B, P, U, 2)
    hpos = hxy[..., 1] * N + hxy[..., 0]                     # (B, P, U)
    act = hn > t.u_arange[:max_h]
    loaded = act & (self._idx_carry[:, :, 1:max_h + 1] >= 8)
    seek = act & ~loaded
    idle = None
    use_feed = False
    use_plant = False
    if h_tasks is not None:
        ht = h_tasks[:, :, :max_h]
        idle = ht == 1
        is_auto = (ht == 0).unsqueeze(-1)                    # (B, P, U, 1)
        # clamp keeps FEED's shift in range; its famk is never used (seek
        # excludes FEED slots from the packed-pool path below)
        fam_t = (ht - 2).clamp(min=0, max=4)                 # 0..4 on task slots
        shift_t = (4 - fam_t).to(i8)
        pk3 = packed[:BP * NN].view(B, P, NN)                # live view: claims show
        seek = seek & ~idle
        is_feed = ht == 7
        use_feed = feed_plane is not None and bool(is_feed.any())
        if use_feed:
            seek = seek & ~is_feed
            feedbuf = torch.zeros(BP * NN + 1, dtype=torch.bool, device=dev)
            feedbuf[:BP * NN] = feed_plane.reshape(-1)
            feedv = feedbuf[:BP * NN].view(B, P, NN)         # live view: claims show
            pen5 = torch.full_like(mfk, 500)
            penBIG = torch.full_like(mfk, BIG)
            wheat_left = self.shed[:, :, ET.WHEAT_I].to(i64).reshape(-1).clone()
            hand_wheat = self.unit_inv[:, :, 1:max_h + 1, ET.WHEAT_I].to(i64)
            carry = self._idx_carry[:, :, 1:max_h + 1].to(i64)
            on_shed = t.shed100.index_select(0, hpos.view(-1)).view(B, P, max_h)
        is_plant = ht == 8
        use_plant = plant_kit is not None and bool(is_plant.any())
        if use_plant:
            seek = seek & ~is_plant
            p_plane, crop_flat, plant_left = plant_kit
            plant_left = plant_left.clone()
            plantbuf = torch.zeros(BP * NN + 1, dtype=torch.bool, device=dev)
            plantbuf[:BP * NN] = p_plane.reshape(-1)
            plantv = plantbuf[:BP * NN].view(B, P, NN)       # live view: claims show
            pen6 = torch.full_like(mfk, 600)
            pen6BIG = torch.full_like(mfk, BIG)
    drop_op = t.shed_dir.index_select(0, hpos.view(-1)).view(B, P, max_h)
    bp100 = self._idx_ar_bp * NN                             # (B*P,)
    dummy = torch.full((BP,), BP * NN, dtype=i64, device=dev)
    zero2 = torch.zeros((B, P), dtype=i64, device=dev)
    ops, args, qtys = [], [], []
    for u in range(max_h):
        hp = hpos[:, :, u].reshape(-1)                       # (B*P,)
        if h_tasks is None:
            eff = mfk
        else:
            avail = ((pk3 >> shift_t[:, :, u].unsqueeze(-1)) & 1) != 0
            famk = torch.where(
                avail, (fam_t[:, :, u] * 100).unsqueeze(-1).to(i32),
                torch.full_like(mfk, BIG))
            eff = torch.where(is_auto[:, :, u], mfk, famk)
        torch.add(t.key1024_lut.index_select(0, hp).view(B, P, NN), eff,
                  out=keybuf)
        kmin = keybuf.amin(-1).view(-1)
        has = seek[:, :, u].reshape(-1) & (kmin < BIG)
        sel_ = kmin % 1024                                   # family*100 + tile
        lin = torch.where(has, bp100 + sel_ % 100, dummy)    # claimed tile (flat)
        fsel = (sel_ // 100).clamp(max=4)
        # claim: clear the family bit at the tile; refresh mfk there
        newp = packed.index_select(0, lin) & t.pack_clear[fsel]
        packed[lin] = newp
        mfk_flat[lin] = t.mfk_lut.index_select(0, newp.int())
        # op: pool op on the tile / step toward it; loaded -> DROP leg
        op_u = torch.where(has, t.hand_op_lut[hp * 1024 + sel_], t.c_pass)
        op_u = torch.where(loaded[:, :, u].reshape(-1), drop_op[:, :, u].reshape(-1), op_u)
        arg_u = qty_u = None
        if use_feed:
            act_u = act[:, :, u].reshape(-1)
            loaded_u = loaded[:, :, u].reshape(-1)
            isf = is_feed[:, :, u].reshape(-1) & act_u
            fw = hand_wheat[:, :, u].reshape(-1)
            # a wheat-carrying FEED hand never runs the DROP leg (feeding
            # consumes; the CPU skips the carry test for it entirely) --
            # even when every target is already claimed it PASSes in place
            op_u = torch.where(isf & (fw > 0) & loaded_u, t.c_pass, op_u)
            # (a) wheat in hand: claim the nearest unclaimed unfed tile
            torch.add(t.key1024_lut.index_select(0, hp).view(B, P, NN),
                      torch.where(feedv, pen5, penBIG), out=keybuf)
            kf = keybuf.amin(-1).view(-1)
            hasf = isf & (fw > 0) & (kf < BIG)
            tile_f = ((kf % 1024) - 500).clamp(min=0, max=NN - 1).to(i64)
            feedbuf[torch.where(hasf, bp100 + tile_f, dummy)] = False
            mvf = t.dir_lut.index_select(0, hp * NN + tile_f)
            opf = torch.where(hp == tile_f,
                              torch.full_like(op_u, U_FEED), mvf)
            op_u = torch.where(hasf, opf, op_u)
            # (b) wheat-less: shed PICKUP leg (loaded slots already DROP);
            # PASS when no stock or no unclaimed target remains
            feed_any = feedv.any(-1).reshape(-1)
            fetch = (isf & (fw <= 0) & ~loaded_u
                     & (wheat_left > 0) & feed_any)
            pick = fetch & on_shed[:, :, u].reshape(-1)
            qty = torch.minimum(
                wheat_left, (8 - carry[:, :, u].reshape(-1)).clamp(min=0))
            qty = torch.where(pick, qty, torch.zeros_like(qty))
            wheat_left = wheat_left - qty                    # serial reservation
            fop = torch.where(on_shed[:, :, u].reshape(-1),
                              torch.full_like(op_u, U_PICKUP),
                              drop_op[:, :, u].reshape(-1))
            op_u = torch.where(fetch, fop, op_u)
            arg_u = torch.full_like(qty, ET.WHEAT_I).view(B, P)
            qty_u = qty.view(B, P)
        if use_plant:
            act_u = act[:, :, u].reshape(-1)
            loaded_u = loaded[:, :, u].reshape(-1)
            # a loaded PLANT hand already took the generic DROP leg above
            isp = is_plant[:, :, u].reshape(-1) & act_u & ~loaded_u
            torch.add(t.key1024_lut.index_select(0, hp).view(B, P, NN),
                      torch.where(plantv, pen6, pen6BIG), out=keybuf)
            kp = keybuf.amin(-1).view(-1)
            hasp = isp & (kp < BIG) & (plant_left > 0)
            tile_p = ((kp % 1024) - 600).clamp(min=0, max=NN - 1).to(i64)
            plantbuf[torch.where(hasp, bp100 + tile_p, dummy)] = False
            plant_left = plant_left - hasp.to(i64)  # claim reserves the seed
            mvp = t.dir_lut.index_select(0, hp * NN + tile_p)
            op_p = torch.where(hp == tile_p,
                               torch.full_like(op_u, U_PLANT), mvp)
            op_u = torch.where(hasp, op_p, op_u)
            base_arg = (arg_u.reshape(-1) if arg_u is not None
                        else torch.zeros_like(op_u))
            arg_u = torch.where(hasp, crop_flat, base_arg).view(B, P)
        if idle is not None:  # IDLE beats the DROP leg (reference order)
            op_u = torch.where(idle[:, :, u].reshape(-1), t.c_pass, op_u)
        ops.append(op_u.view(B, P))
        args.append(arg_u if arg_u is not None else zero2)
        qtys.append(qty_u if qty_u is not None else zero2)
    return ops, args, qtys


def _idx_decode_market(self, m_idx, herd, day, t):
    """actions._market_action to (B, P, S) order-slot tensors. Quantities are
    pre-step by construction (this runs before the unit phase, like the
    caller-side decode). Slot 0 is three LUT gathers on the head index plus
    the SELL count / BUY_WHEAT quantity; the liquidation-day compound sell
    and the HIRE burst are the only multi-slot decodes."""
    B, P = self.B, self.NUM_PLAYERS
    dev = self.device
    i64 = torch.int64
    S = self.max_market_orders
    m_op = torch.zeros((B, P, S), dtype=i64, device=dev)
    m_item = torch.zeros((B, P, S), dtype=i64, device=dev)
    m_rem = torch.zeros((B, P, S), dtype=i64, device=dev)
    shed9 = self.shed[:, :, :ET.N_MKT].to(i64)
    m = m_idx

    op0 = t.mop_lut[m]
    item0 = t.mitem_lut[m]
    cnt = shed9.gather(2, item0.unsqueeze(-1)).squeeze(-1)
    sell = op0 == ET.OP_SELL
    # indices 22.. are SELL_HALF_<p>: meter to ceil(half) of the holding
    sq = torch.where(m >= 22, (cnt + 1) // 2, cnt)
    m_op[..., 0] = torch.where(sell & (cnt == 0), torch.zeros_like(op0), op0)
    m_item[..., 0] = item0
    m_rem[..., 0] = torch.where(sell, sq, torch.where(
        m == 15, (2 * herd).clamp(min=5), t.mrem_lut[m]))   # 15 = BUY_WHEAT

    if day >= R.LIQUIDATE_DAY and bool(sell.any()):
        # liquidation-day compound decode: whole shed, primary product
        # first, the rest in PRODUCT_LIST order, MAX_ORDERS cap.
        pi = item0
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

    hire = m == 21
    if bool(hire.any()):
        # burst: up to 4 while fib(hires_today + j) <= 0.05 * money and the
        # crew stays under MAX_HANDS; empty burst falls back to one HIRE
        # (slot 0 already carries OP_HIRE from the LUT).
        hires = self.hires_today.to(i64).unsqueeze(-1) + t.j4
        fib = t.fib[hires.clamp(max=78)]
        cond = (((self.hands_n.to(i64).unsqueeze(-1) + t.j4) < A.MAX_HANDS)
                & (fib <= 0.05 * self.money.unsqueeze(-1)))
        k = cond.to(i64).cumprod(-1).sum(-1)                 # leading-true run
        for j in range(1, 4):
            slot = hire & (k > j)
            m_op[..., j] = torch.where(slot, OP_HIRE, m_op[..., j])
    return m_op, m_item, m_rem


# ---------------------------------------------------------------------------
# apply: one unit slot, batch-parallel (transcribes engine_t._apply_unit)
# ---------------------------------------------------------------------------

def _idx_apply_slot(self, u, op, arg, qty, day, t, pres):
    """One unit slot for every (lane, player), transcribing engine_t's
    _apply_unit. pres[code]: python bool, whether any unit in this slot has
    op == code (one batched D2H per step in step_idx replaces 14 any() syncs
    per slot). B4b form: every board read/write is index_select /
    index_copy_ on the flat (B*P*100) view at the unit's linear tile index
    (3-6x cheaper than 4-tensor advanced indexing on the CPU build); events
    of one op are unique per (lane, player), so masked write-backs of
    unchanged values are safe and replace the per-op filtering."""
    B, P = self.B, self.NUM_PLAYERS
    i64, i8, i16 = torch.int64, torch.int8, torch.int16
    NN = N * N
    if u == 0:
        pxy = self.farmer_xy.to(i64)                          # (B, P, 2)
    else:
        pxy = self.hands_xy[:, :, u - 1].to(i64)
    pos = pxy[..., 1] * N + pxy[..., 0]                      # (B, P)

    # -- moves (bounds-checked; LOCKED tiles are walkable): one LUT gather --
    if pres[U_MOVE_N] or pres[U_MOVE_S] or pres[U_MOVE_E] or pres[U_MOVE_W]:
        newpos = t.move_lut[pos * 5 + t.move_code[op]]
        nxy = torch.stack([newpos % N, newpos // N], -1).to(i8)
        if u == 0:
            self.farmer_xy.copy_(nxy)
        else:
            self.hands_xy[:, :, u - 1] = nxy

    lin_all = (self._idx_ar_bp * NN + pos.view(-1))          # (B*P,) flat tile
    opf = op.view(-1)
    kind_f = self.kind.view(-1)
    animal_f = self.animal.view(-1)
    yield_f = self.yield_units.view(-1)
    crop_f = self.crop.view(-1)
    planted_f = self.planted_day.view(-1)
    watered_f = self.watered.view(-1)
    fert_until_f = self.fert_until.view(-1)
    fed_f = self.fed.view(-1)
    cared_f = self.cared.view(-1)
    fert_avail_f = self.fert_avail.view(-1)
    shed2 = self.shed.view(B * P, NI)
    shed_f = self.shed.view(-1)

    def sub(code):
        if not pres[code]:
            return None
        i = (opf == code).nonzero().squeeze(1)               # event rows (B*P index)
        return i, lin_all.index_select(0, i)

    def struct_with_animal(L):
        kk = kind_f.index_select(0, L)
        return (((kk == ET.K_COOP) | (kk == ET.K_PASTURE))
                & (animal_f.index_select(0, L) >= 0))

    s = sub(U_WATER)
    if s:
        i, L = s
        wat = watered_f.index_select(0, L)
        ok = (kind_f.index_select(0, L) == ET.K_PLANT) & ~wat
        watered_f.index_copy_(0, L, wat | ok)
        ci = crop_f.index_select(0, L).to(i64)
        aged = day - planted_f.index_select(0, L).to(i64)
        maxday = t.crop_maxday[ci]
        win = ok & ~t.crop_ongoing[ci] & ((maxday + 1) // 2 <= aged) & (aged <= maxday)
        bonus = (fert_until_f.index_select(0, L).to(i64) >= day).to(i64) + 1
        cur = yield_f.index_select(0, L).to(i64)
        new = torch.minimum(t.crop_maxy[ci], cur + bonus)
        yield_f.index_copy_(0, L, torch.where(win, new, cur).to(i8))

    s = sub(U_HARVEST)
    if s:
        i, L = s
        kk = kind_f.index_select(0, L)
        yuv = yield_f.index_select(0, L).to(i64)
        ai = animal_f.index_select(0, L).to(i64)
        ci = crop_f.index_select(0, L).to(i64)
        aged = day - planted_f.index_select(0, L).to(i64)
        okp = (kk == ET.K_PLANT) & (yuv > 0) & (aged >= t.crop_first[ci])
        oks = ((kk == ET.K_COOP) | (kk == ET.K_PASTURE)) & (ai >= 0) & (yuv > 0)
        ok = okp | oks
        j = ok.nonzero().squeeze(1)
        if j.numel():
            L2 = L.index_select(0, j)
            item = torch.where(okp, ci, t.animal_product[ai.clamp(min=0)]).index_select(0, j)
            yield_f.index_fill_(0, L2, 0)
            done_p = okp & ~t.crop_ongoing[ci]               # one-shot crop
            k = done_p.nonzero().squeeze(1)
            if k.numel():
                L3 = L.index_select(0, k)
                kind_f.index_fill_(0, L3, ET.K_EMPTY)
                animal_f.index_fill_(0, L3, -1)
            self._idx_inv_add(i.index_select(0, j), u, item, yuv.index_select(0, j))

    s = sub(U_FEED)
    if s:
        i, L = s
        ok = struct_with_animal(L) & ~fed_f.index_select(0, L)
        j = ok.nonzero().squeeze(1)
        if j.numel():
            i2, L2 = i.index_select(0, j), L.index_select(0, j)
            took = self._idx_inv_take(i2, u, torch.full_like(i2, ET.WHEAT_I), 1)
            fed_f.index_copy_(0, L2, took)                   # (was False: ok)

    s = sub(U_CARE)
    if s:
        i, L = s
        cur = cared_f.index_select(0, L)
        cared_f.index_copy_(0, L, cur | (struct_with_animal(L) & ~cur))

    s = sub(U_COLLECT)
    if s:
        i, L = s
        ok = struct_with_animal(L) & fert_avail_f.index_select(0, L)
        j = ok.nonzero().squeeze(1)
        if j.numel():
            i2, L2 = i.index_select(0, j), L.index_select(0, j)
            fert_avail_f.index_fill_(0, L2, False)
            self._idx_inv_add(i2, u, torch.full_like(i2, ET.FERT_I), 1)

    s = sub(U_FERTILIZE)
    if s:
        i, L = s
        ok = kind_f.index_select(0, L) == ET.K_PLANT
        j = ok.nonzero().squeeze(1)
        if j.numel():
            i2, L2 = i.index_select(0, j), L.index_select(0, j)
            took = self._idx_inv_take(i2, u, torch.full_like(i2, ET.FERT_I), 1)
            cur = fert_until_f.index_select(0, L2).to(i64)
            new = torch.where(took, torch.maximum(cur, torch.full_like(cur, day + 2)), cur)
            fert_until_f.index_copy_(0, L2, new.to(i16))

    s = sub(U_DIG)
    if s:
        i, L = s
        kk = kind_f.index_select(0, L)
        struct = (kk == ET.K_COOP) | (kk == ET.K_PASTURE)
        ok = ((kk != ET.K_EMPTY) & (kk != ET.K_LOCKED)
              & ~(struct & (animal_f.index_select(0, L) >= 0)))
        j = ok.nonzero().squeeze(1)
        if j.numel():
            L2 = L.index_select(0, j)
            kind_f.index_fill_(0, L2, ET.K_EMPTY)
            animal_f.index_fill_(0, L2, -1)

    for code, kcode in ((U_BUILD_COOP, ET.K_COOP), (U_BUILD_PASTURE, ET.K_PASTURE)):
        s = sub(code)
        if s:
            i, L = s
            ok = kind_f.index_select(0, L) == ET.K_EMPTY
            j = ok.nonzero().squeeze(1)
            if j.numel():
                L2 = L.index_select(0, j)
                kind_f.index_fill_(0, L2, kcode)
                animal_f.index_fill_(0, L2, -1)

    s = sub(U_PLANT)
    if s:
        # Atomic PLANT validation degenerates to the plain seed check here:
        # one unit per (lane, player) per SLOT, and slots apply serially
        # (farmer first, hands in order), so per-crop demand is <= 1 per
        # sub call and hands planting re-read the post-farmer stock --
        # same-turn contention resolves exactly like the reference's
        # serial unit order.
        i, L = s
        ci = arg.view(-1).index_select(0, i)
        seeds_f = self.seeds_t.view(-1)
        si = i * len(ET.CROP_NAMES) + ci
        seeds = seeds_f.index_select(0, si).to(i64)
        ok = (kind_f.index_select(0, L) == ET.K_EMPTY) & (seeds > 0)
        j = ok.nonzero().squeeze(1)
        if j.numel():
            L2, c2, si2 = L.index_select(0, j), ci.index_select(0, j), si.index_select(0, j)
            seeds_f.index_copy_(0, si2, (seeds.index_select(0, j) - 1).to(i16))
            ong = t.crop_ongoing[c2]
            kind_f.index_fill_(0, L2, ET.K_PLANT)
            animal_f.index_fill_(0, L2, -1)
            crop_f.index_copy_(0, L2, c2.to(i8))
            planted_f.index_fill_(0, L2, day)
            watered_f.index_fill_(0, L2, False)
            self.consec_unwatered.view(-1).index_fill_(0, L2, 1)  # planting day counts
            yield_f.index_copy_(0, L2, (~ong).to(i8))
            self.mls.view(-1).index_copy_(0, L2, torch.where(
                ong, torch.full_like(c2, -1),
                (day + t.crop_maxday[c2] + 1) * self.turns_per_day).to(torch.int32))
            fert_until_f.index_fill_(0, L2, -1)

    s = sub(U_PLACE)
    if s:
        i, L = s
        ai_raw = arg.view(-1).index_select(0, i)
        # arg >= 100 encodes the reference's SECOND place semantics: a
        # shed-ADJACENT deposit of item (arg - 100), qty in the qty slot
        # (top-meta tapes use it for produce logistics -- ['PLACE','MILK',6];
        # the macro space and barnyard never emit it, so the idx path only
        # carried the animal branch until tape_t needed this one)
        dep = ai_raw >= 100
        jd = dep.nonzero().squeeze(1)
        if jd.numel():
            i2 = i.index_select(0, jd)
            it2 = (ai_raw.index_select(0, jd) - 100).clamp(min=0, max=NI - 1)
            adj2 = t.shed100[(L.index_select(0, jd)) % NN]
            n2 = qty.view(-1).index_select(0, i2).clamp(min=0)
            HI = (1 + self.H) * NI
            have2 = self.unit_inv.view(-1).index_select(
                0, i2 * HI + u * NI + it2).to(i64)
            room2 = (self.shed_capacity
                     - shed2.index_select(0, i2).to(i64).sum(-1)).clamp(min=0)
            n2 = torch.minimum(torch.minimum(n2, have2), room2)
            k = ((n2 > 0) & adj2).nonzero().squeeze(1)
            if k.numel():
                i3 = i2.index_select(0, k)
                it3 = it2.index_select(0, k)
                n3 = n2.index_select(0, k)
                self._idx_inv_take(i3, u, it3, n3)
                sl = i3 * NI + it3
                shed_f.index_copy_(0, sl, shed_f.index_select(0, sl)
                                   + n3.to(shed_f.dtype))
        ai = torch.where(dep, torch.zeros_like(ai_raw), ai_raw)
        on_struct = (~dep
                     & (kind_f.index_select(0, L).to(i64) == t.animal_struct[ai])
                     & (animal_f.index_select(0, L) < 0))
        j = on_struct.nonzero().squeeze(1)
        if j.numel():
            i2, L2, a2 = i.index_select(0, j), L.index_select(0, j), ai.index_select(0, j)
            took = self._idx_inv_take(i2, u, ET.N_MKT + a2, 1)
            k = took.nonzero().squeeze(1)
            if k.numel():
                L3, a3 = L2.index_select(0, k), a2.index_select(0, k)
                animal_f.index_copy_(0, L3, a3.to(i8))
                self.placed_day.view(-1).index_fill_(0, L3, day)
                yield_f.index_fill_(0, L3, 0)
                self.consec_unfed.view(-1).index_fill_(0, L3, 0)
                fed_f.index_fill_(0, L3, False)
                cared_f.index_fill_(0, L3, False)
                fert_avail_f.index_fill_(0, L3, False)
                self.pending.view(-1).index_fill_(0, L3, 0)
        # off-structure PLACE falls through to the shed-drop path (n = 1)
        off = ~on_struct & ~dep & t.shed100[L % NN]
        j = off.nonzero().squeeze(1)
        if j.numel():
            i2, a2 = i.index_select(0, j), ai.index_select(0, j)
            room_ok = shed2.index_select(0, i2).to(i64).sum(-1) < self.shed_capacity
            HI = (1 + self.H) * NI
            have_ok = self.unit_inv.view(-1).index_select(
                0, i2 * HI + u * NI + ET.N_MKT + a2) >= 1
            k = (room_ok & have_ok).nonzero().squeeze(1)
            if k.numel():
                i3, a3 = i2.index_select(0, k), a2.index_select(0, k)
                self._idx_inv_take(i3, u, ET.N_MKT + a3, 1)   # have_ok: unconditional
                sl = i3 * NI + ET.N_MKT + a3
                shed_f.index_copy_(0, sl, shed_f.index_select(0, sl) + 1)

    s = sub(U_PICKUP)
    if s:
        i, L = s
        adj = t.shed100[L % NN]
        j = adj.nonzero().squeeze(1)
        if j.numel():
            i2 = i.index_select(0, j)
            item = arg.view(-1).index_select(0, i2)
            sl = i2 * NI + item
            n = torch.minimum(qty.view(-1).index_select(0, i2),
                              shed_f.index_select(0, sl).to(i64))
            k = (n > 0).nonzero().squeeze(1)
            if k.numel():
                i3, it3, sl3, n3 = (i2.index_select(0, k), item.index_select(0, k),
                                    sl.index_select(0, k), n.index_select(0, k))
                shed_f.index_copy_(0, sl3, (shed_f.index_select(0, sl3).to(i64) - n3).to(i16))
                self._idx_inv_add(i3, u, it3, n3)

    s = sub(U_DROP)
    if s:
        i, L = s
        adj = t.shed100[L % NN]
        j = adj.nonzero().squeeze(1)
        if j.numel():
            # dict-insertion-order deposit, capacity-limited per item;
            # overflow is discarded. Greedy fill in rank order is closed
            # form: take_k = min(n_k, max(0, room - sum_{j<k} n_j)).
            i2 = i.index_select(0, j)
            ur = i2 * (1 + self.H) + u                       # unit rows
            seqs = self._ord_seq.view(-1, NI).index_select(0, ur).to(i64)
            cnts = self.unit_inv.view(-1, NI).index_select(0, ur).to(i64)
            keys = torch.where(cnts > 0, seqs, BIG)
            order = keys.argsort(-1)
            n_sorted = cnts.gather(1, order)
            before = n_sorted.cumsum(-1) - n_sorted
            rows = shed2.index_select(0, i2)
            room = (self.shed_capacity - rows.to(i64).sum(-1)).clamp(min=0)
            take = torch.minimum(n_sorted, (room.unsqueeze(-1) - before).clamp(min=0))
            shed2.index_copy_(0, i2, rows.scatter_add(1, order, take.to(i16)))
            self.unit_inv.view(-1, NI).index_fill_(0, ur, 0)
            self._ord_seq.view(-1, NI).index_fill_(0, ur, 0)
            self._idx_carry.view(-1).index_fill_(0, ur, 0)


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
    bo, po = b[ok], p[ok]
    if not bo.numel():
        return
    hn = self.hands_n[bo, po].to(i64)
    over = hn >= self.H
    self._err[1] |= over.any()                # raised by _check_err (end of step)
    hn = hn.clamp(max=self.H - 1)
    self.money[bo, po] = money[ok] - cost[ok].to(torch.float64)
    self.hires_today[bo, po] = (hires[ok] + 1).to(torch.int16)
    # Spawn: first free shed-access tile (NWSE), ties by min occupancy --
    # min over occupancy*4 + NWSE index, exactly _spawn_hand's sort key.
    # Occupancy of the 100 tiles by farmer + valid hands (K, 101; column 100
    # is the dummy for invalid hand slots), then read the four shed tiles.
    fxy = self.farmer_xy[bo, po].to(i64)                     # (K, 2)
    hxy = self.hands_xy[bo, po].to(i64)                      # (K, H, 2)
    hpos = hxy[..., 1] * N + hxy[..., 0]
    validh = t.u_arange[:self.H] < hn.unsqueeze(-1)
    hpos = torch.where(validh, hpos, torch.full_like(hpos, N * N))
    cnt = torch.zeros((bo.numel(), N * N + 1), dtype=i64, device=self.device)
    cnt.scatter_add_(1, hpos, torch.ones_like(hpos))
    cnt.scatter_add_(1, (fxy[:, 1] * N + fxy[:, 0]).unsqueeze(-1),
                     torch.ones((bo.numel(), 1), dtype=i64, device=self.device))
    occ = cnt[:, t.shed4t]                                   # (K, 4)
    sel = (occ * 4 + t.ar4).amin(-1) % 4
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
    """Order-index loop; per index the HIRE / BUY_LAND atomics (player order
    is irrelevant: farms are independent), then engine_t's lockstep for the
    market ops. Presence of each kind at each index is one host read."""
    pres = torch.stack([(m_op == OP_HIRE).any(0).any(0),
                        (m_op == OP_LAND).any(0).any(0),
                        ((m_op != ET.OP_DEAD) & (m_op < OP_HIRE)).any(0).any(0)]
                       ).tolist()                             # (3, S) bools
    used = [h or l or m for h, l, m in zip(*pres)]
    gmax = 0
    for i, live in enumerate(used):
        if live:
            gmax = i + 1
    for i in range(gmax):
        opi = m_op[..., i]
        if pres[0][i]:
            self._idx_do_hire(*(opi == OP_HIRE).nonzero(as_tuple=True), t)
        if pres[1][i]:
            self._idx_do_land(*(opi == OP_LAND).nonzero(as_tuple=True), t)
        if pres[2][i]:
            live_op = torch.where(opi >= OP_HIRE, torch.zeros_like(opi), opi)
            self._market_lockstep(live_op, m_item[..., i], m_rem[..., i])
        self._refresh_prices()


# ---------------------------------------------------------------------------
# step_idx
# ---------------------------------------------------------------------------

def step_idx(self, f_idx, m_idx, override=None, h_idx=None):
    """Advance every lane one turn from action-head indices.

    f_idx, m_idx: (B, 2) integer tensors / array-likes -- per lane, per
    player, indices into actions.FARMER_ACTIONS / actions.MARKET_ACTIONS.
    Byte-equivalent to step_raw fed with actions.decode(...) per lane.

    override: optional (seat, ops) -- replace ONE seat's decoded actions
    with raw internal encodings before the apply phase (tensor opponents
    whose behaviour the macro space cannot express, e.g. barnyard_t):
        ops["f_op"/"f_arg"/"f_qty"]: (B,) unit codes for the farmer slot
        ops["h_op"/"h_arg"/"h_qty"]: lists of (B,) per hand slot
        ops["m_op"/"m_item"/"m_rem"]: (B, S) market order slots
    The overridden seat's f_idx/m_idx are decoded and discarded; the apply
    phase and everything after it are untouched, so override=None is
    bit-for-bit the old path (gate: test_barn.py G0).

    h_idx (B, P, >=1) or None: per-hand task indices (actions.HAND_TASKS)
    for the multi-head action space; None keeps the classic scripted
    cascade. Gate: test_multi.py M2 (byte-equal to step_raw fed
    actions.decode_multi, and all-AUTO == the h_idx=None path).
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
    fam = getattr(self, "_idx_fam", None)
    if fam is None or fam.shape[1] != B:
        # (12, B, P, 100) family planes; plane 0 (F_NONE) stays False and
        # plane 11 (F_SHED) is constant -- both written once here.
        fam = torch.zeros((12, B, P, N * N), dtype=torch.bool, device=dev)
        fam[F_SHED] = t.shed100.view(1, 1, N * N)
        self._idx_fam = fam
        self._idx_ar_bp = torch.arange(B * P, dtype=i64, device=dev)

    # ---- one shared pre-step board scan (actions.analyze's families),
    #      written straight into the family planes ----
    kind = self.kind.reshape(B, P, N * N)
    c = lambda v: cst(kind, v)                               # int8 constants
    anim_f = self.animal.reshape(B, P, N * N) >= c(0)
    plant_f = kind == c(ET.K_PLANT)
    yu_pos = self.yield_units.reshape(B, P, N * N) > c(0)
    age8 = (day - self.planted_day.reshape(B, P, N * N)).to(torch.int8)
    cf8 = isel(t.crop_first_i8, self.crop.reshape(B, P, N * N).int())
    harv_f = ((plant_f & yu_pos & (age8 >= cf8)) | (anim_f & yu_pos))
    unwat_f = plant_f & ~self.watered.reshape(B, P, N * N)
    unfert_f = plant_f & ((self.fert_until.reshape(B, P, N * N) - day).to(torch.int8) < c(0))
    unfed_f = anim_f & ~self.fed.reshape(B, P, N * N)
    uncared_f = anim_f & ~self.cared.reshape(B, P, N * N)
    fready_f = anim_f & self.fert_avail.reshape(B, P, N * N)
    weed_f = kind == c(ET.K_WEED)
    torch.eq(kind, c(ET.K_EMPTY), out=fam[F_EMPTY])
    torch.bitwise_and(kind == c(ET.K_COOP), ~anim_f, out=fam[F_COOPF])
    torch.bitwise_and(kind == c(ET.K_PASTURE), ~anim_f, out=fam[F_PASTF])
    fam[F_WEED] = weed_f
    fam[F_UNWAT] = unwat_f
    fam[F_UNFERT] = unfert_f
    fam[F_HARV] = harv_f
    fam[F_UNFED] = unfed_f
    fam[F_UNCARED] = uncared_f
    fam[F_FREADY] = fready_f
    herd = anim_f.view(torch.int8).sum(-1, dtype=torch.int32).to(i64)  # BUY_WHEAT scale

    # ---- decode everything from the pre-step state ----
    h_tasks = None
    if h_idx is not None:
        h_tasks = torch.as_tensor(h_idx, dtype=i64, device=dev)
        h_tasks = h_tasks.reshape(B, P, -1)
        pad = int(self.hands_n.max()) - h_tasks.shape[-1]
        if pad > 0:  # short task vectors default to AUTO, like the reference
            h_tasks = torch.nn.functional.pad(h_tasks, (0, pad))
    f_op, f_arg, f_qty = self._idx_decode_farmer(f_idx, fam, t)
    plant_kit = None
    if h_tasks is not None and bool((h_tasks == 8).any()):
        # hand PLANT: most-held VIABLE seed (seed held and the planting
        # deadline not passed; argmax = CPU first-max over CROP_LIST),
        # budget = the pre-step stock -- no farmer adjustment, exactly
        # like the CPU decode; same-turn contention (farmer takes the
        # last seed or the claimed tile) resolves in the slot-serial
        # apply, the reference's unit order
        seeds64 = self.seeds_t.to(i64)
        viable = (seeds64 > 0) & (day <= t.plant_deadline).view(1, 1, -1)
        key6 = torch.where(viable, seeds64, torch.full_like(seeds64, -1))
        crop_sel = key6.argmax(-1)                           # (B, P)
        stock = (seeds64.gather(-1, crop_sel.unsqueeze(-1)).squeeze(-1)
                 * viable.gather(-1, crop_sel.unsqueeze(-1)).squeeze(-1))
        plant_kit = (fam[F_EMPTY], crop_sel.reshape(-1),
                     stock.reshape(-1))
    hand_ops, hand_args, hand_qtys = self._idx_decode_hands(
        [harv_f, unwat_f, uncared_f, fready_f, weed_f], t, h_tasks,
        unfed_f, plant_kit)
    m_op, m_item, m_rem = self._idx_decode_market(m_idx, herd, day, t)

    zero = torch.zeros((B, P), dtype=i64, device=dev)
    for seat, ops in ([] if override is None
                      else [override] if isinstance(override, tuple)
                      else list(override)):
        # graft one seat's raw internal encodings over the macro decode;
        # clone before writing -- decode may hand back one shared zero
        # tensor across slots (and FEED slots carry real arg/qty now).
        # A list of (seat, ops) grafts several seats (bank generation
        # plays barnyard on both); the single-tuple form is unchanged.
        f_op[:, seat] = ops["f_op"]
        f_arg[:, seat] = ops["f_arg"]
        f_qty[:, seat] = ops["f_qty"]
        h_op, h_arg, h_qty = ops["h_op"], ops["h_arg"], ops["h_qty"]
        while len(hand_ops) < len(h_op):
            hand_ops.append(zero.clone())
            hand_args.append(zero)
            hand_qtys.append(zero)
        for u in range(len(hand_ops)):
            if u < len(h_op):
                hand_ops[u] = hand_ops[u].clone()
                hand_ops[u][:, seat] = h_op[u]
                hand_args[u] = hand_args[u].clone()
                hand_args[u][:, seat] = h_arg[u]
                hand_qtys[u] = hand_qtys[u].clone()
                hand_qtys[u][:, seat] = h_qty[u]
            else:
                hand_ops[u] = hand_ops[u].clone()
                hand_ops[u][:, seat] = U_PASS
        m_op[:, seat] = ops["m_op"]
        m_item[:, seat] = ops["m_item"]
        m_rem[:, seat] = ops["m_rem"]

    # ---- apply: unit phase (slot-serial, batch-parallel), then market ----
    # op presence per slot: one (S, 18) host read for the whole step.
    all_ops = torch.stack([f_op] + hand_ops, 0).view(-1, B * P)   # (S, B*P)
    pres = torch.zeros((all_ops.shape[0], 18), dtype=torch.bool,
                       device=dev).scatter_(1, all_ops, True).tolist()
    self._idx_apply_slot(0, f_op, f_arg, f_qty, day, t, pres[0])
    for u, op_u in enumerate(hand_ops):
        self._idx_apply_slot(u + 1, op_u, hand_args[u], hand_qtys[u], day, t,
                             pres[u + 1])
    self._idx_market(m_op, m_item, m_rem, t)

    self._town_consume(step)
    self._decay_plants(step)
    if (step + 1) % self.turns_per_day == 0:
        self._end_of_day(day, seq_drop=True)     # tensor-rank deposit; resets _inv_ord
        self._ord_ctr = 1
    self._check_err()

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
ET.EpisodeT._idx_decode_farmer = _idx_decode_farmer
ET.EpisodeT._idx_decode_hands = _idx_decode_hands
ET.EpisodeT._idx_decode_market = _idx_decode_market
ET.EpisodeT._idx_apply_slot = _idx_apply_slot
ET.EpisodeT._idx_do_hire = _idx_do_hire
ET.EpisodeT._idx_do_land = _idx_do_land
ET.EpisodeT._idx_market = _idx_market
