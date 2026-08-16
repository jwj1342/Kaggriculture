"""Batched torch tensor engine for Kaggriculture (DESIGN.md phase B1).

B independent two-player episodes advance in lockstep; state lives in torch
tensors laid out per DESIGN.md Appendix A. Semantics are transcribed from
rl/tensor_env/engine_np.py (the byte-exact oracle) and every acceptance gate
diffs full reconstructed snapshots against it (rl/tensor_env/verify_t.py).

Design decisions honoured here:
  D1  state is integer tensors; the only floats are money (float64) and the
      price formula -- which is made bit-exact on any device by tabulating
      engine_np.market_price(item, inventory) over an integer inventory range
      once on the host and gathering from the table thereafter.
  D2  hybrid stepping: the per-turn phases are tensor ops; the end-of-day RNG
      segment (row-major weed draws whose count depends on each farm's empty
      tiles, and the shop unlock draw) runs on the host with
      random.Random((seed * 1_000_003) ^ day) per lane, exactly mirroring
      engine_np._end_of_day's call order, then writes back to the tensors.
  D3  the market per-unit lockstep loop stays serial over the unit index but
      each iteration quotes and commits over (B,) index tensors.

Host-side python is confined to: per-lane action parsing/dispatch (bounded by
B x units), the atomic HIRE / BUY_LAND orders, the end-of-day RNG segment and
capacity-ordered inventory drops, and snapshot reconstruction. The bulk
per-tile phases (plant decay, daily plant/animal refresh transitions, town
consumption, price refresh) are tensor ops over (B, P, N, N) / (B, 9).

One piece of host metadata augments the Appendix A tensors: per-unit item
insertion order (`_inv_ord`). engine_np's inventories are dicts, and the two
capacity-limited deposit paths (DROP, end-of-day drop) walk items in dict
insertion order -- near a full shed, *which* items land is order-dependent, so
byte-exactness requires remembering it. Counts stay authoritative in
`unit_inv`; the order list is bookkeeping only.
"""

import random

import torch

try:
    from . import engine_np as E
except ImportError:  # verify_t.py imports this module flat
    import engine_np as E


# ---------------------------------------------------------------------------
# Static index spaces (Appendix A conventions)
# ---------------------------------------------------------------------------

PRODUCTS = list(E.PRODUCTS)                # 9 market items
ANIMAL_NAMES = list(E.ANIMALS)             # GOOSE, COW, SHEEP
ITEMS = PRODUCTS + ANIMAL_NAMES            # I = 12 shed / inventory items
CROP_NAMES = list(E.CROPS)                 # 5, == PRODUCTS[:5]
SHOP_SORTED = sorted(E.SHOPS)              # rng.choice draws from this order

ITEM_IDX = {n: i for i, n in enumerate(ITEMS)}
PRODUCT_IDX = {n: i for i, n in enumerate(PRODUCTS)}
CROP_IDX = {n: i for i, n in enumerate(CROP_NAMES)}
ANIMAL_IDX = {n: i for i, n in enumerate(ANIMAL_NAMES)}
SHOP_IDX = {n: i for i, n in enumerate(SHOP_SORTED)}

K_EMPTY, K_LOCKED, K_WEED, K_COOP, K_PASTURE, K_PLANT = 0, 1, 2, 3, 4, 5
KIND_NAME = {K_WEED: "WEED", K_COOP: "COOP", K_PASTURE: "PASTURE"}
STRUCT_CODE = {"COOP": K_COOP, "PASTURE": K_PASTURE}

WHEAT_I = ITEM_IDX["WHEAT"]
FERT_I = ITEM_IDX["FERTILIZER"]
N_MKT = len(PRODUCTS)                      # 9; FERTILIZER is index 8 (last)

# Host-side per-crop tables, indexed by crop idx.
CROP_FIRST = [E.CROPS[c]["first_yield_day"] for c in CROP_NAMES]
CROP_MAXDAY = [E.CROPS[c]["max_yield_day"] for c in CROP_NAMES]
CROP_INTERVAL = [E.CROPS[c]["interval"] for c in CROP_NAMES]
CROP_MAXY = [E.CROPS[c]["max_yield"] for c in CROP_NAMES]
CROP_ONGOING = [E.CROPS[c]["ongoing"] for c in CROP_NAMES]
CROP_SEED_COST = [E.CROPS[c]["seed"] for c in CROP_NAMES]

# Host-side per-animal tables, indexed by animal idx.
ANIMAL_COST = [E.ANIMALS[a]["cost"] for a in ANIMAL_NAMES]
ANIMAL_STRUCT = [STRUCT_CODE[E.ANIMALS[a]["structure"]] for a in ANIMAL_NAMES]
ANIMAL_FIRST = [E.ANIMALS[a]["first_yield_day"] for a in ANIMAL_NAMES]
ANIMAL_INTERVAL = [E.ANIMALS[a]["interval"] for a in ANIMAL_NAMES]
ANIMAL_MAX = [E.ANIMALS[a]["max_held"] for a in ANIMAL_NAMES]
ANIMAL_PRODUCT = [PRODUCT_IDX[E.ANIMALS[a]["product"]] for a in ANIMAL_NAMES]

# Per-shop-instance consumption vector over the 9 market items (SHOP_SORTED
# order): single-product shops consume 2 of it, multi-product shops 1 each.
_SHOP_CONS = []
for _shop in SHOP_SORTED:
    _prods = E.SHOPS[_shop]
    _mult = 2 if len(_prods) == 1 else 1
    _row = [0] * N_MKT
    for _it in _prods:
        _row[PRODUCT_IDX[_it]] += _mult
    _SHOP_CONS.append(_row)

# Market order op codes (0 = dead / no order).
OP_DEAD, OP_SELL, OP_BUYP, OP_SEED, OP_ANIMAL = 0, 1, 2, 3, 4


# ---------------------------------------------------------------------------
# Bit-exact price table (D1)
# ---------------------------------------------------------------------------
# market_price is a pure function of (item, integer inventory) but goes
# through libm (sqrt/log); rather than trusting a device's libm to match
# CPython's, tabulate the reference implementation itself over the reachable
# inventory range. Any lookup outside the range raises -- widen the bounds
# rather than clamping if that ever fires.

_PRICE_LO = -20_000
_PRICE_HI = 40_000
_PRICE_W = _PRICE_HI - _PRICE_LO
_PRICE_HOST = None
_PRICE_DEV = {}


def _price_table(device):
    global _PRICE_HOST
    if _PRICE_HOST is None:
        rows = [[E.market_price(item, inv) for inv in range(_PRICE_LO, _PRICE_HI)]
                for item in PRODUCTS]
        _PRICE_HOST = torch.tensor(rows, dtype=torch.int64)
    key = str(device)
    if key not in _PRICE_DEV:
        _PRICE_DEV[key] = _PRICE_HOST.to(device)
    return _PRICE_DEV[key]


# ---------------------------------------------------------------------------
# EpisodeT
# ---------------------------------------------------------------------------

class EpisodeT:
    """B lockstepped two-player episodes on torch tensors.

    seeds[lane] is that lane's resolved episode seed (the end-of-day RNG key).
    .step_raw(actions) with actions[lane] = [p0_action_dict, p1_action_dict]
    advances every lane one turn. .snapshot(lane) reconstructs exactly the
    structure engine_np.Episode.snapshot() returns. .done is a python bool for
    the whole batch (fixed episode length keeps lanes in agreement).
    """

    NUM_PLAYERS = 2

    def __init__(self, seeds, episode_steps=720, device="cpu",
                 board_size=10, starting_money=3000, turns_per_day=24,
                 shed_capacity=100, weed_spawn_chance=0.005,
                 town_shop_unlock_interval=3, town_shop_sell_interval=4,
                 town_center_sell_interval=24, max_market_orders_per_turn=10,
                 farm_hand_cost_mult=E.FARM_HAND_COST_MULT, max_hands=32):
        self.seeds = [int(s) for s in seeds]
        self.B = len(self.seeds)
        self.episode_steps = int(episode_steps)
        self.device = torch.device(device)
        self.N = int(board_size)
        self.starting_money = int(starting_money)
        self.turns_per_day = max(1, int(turns_per_day))
        self.shed_capacity = int(shed_capacity)
        self.weed_spawn_chance = float(weed_spawn_chance)
        self.town_shop_unlock_interval = max(1, int(town_shop_unlock_interval))
        self.town_shop_sell_interval = max(1, int(town_shop_sell_interval))
        self.town_center_sell_interval = max(1, int(town_center_sell_interval))
        self.max_market_orders = max(1, int(max_market_orders_per_turn))
        self.hire_mult = int(farm_hand_cost_mult)
        self.H = int(max_hands)

        B, P, N, H, I = self.B, self.NUM_PLAYERS, self.N, self.H, len(ITEMS)
        dev = self.device
        half = N // 2
        # Shed access tiles in NWSE order; spawn = first one in the NW
        # quadrant (engine_np._shed_access_tiles / _default_spawn).
        self._shed_tiles = [(half - 1, half - 1), (half, half - 1),
                            (half - 1, half), (half, half)]
        self._shed_adj = set(self._shed_tiles)
        self._spawn = next(t for t in self._shed_tiles
                           if t[0] < half and t[1] < half)

        # ---- board tensors (B, P, N, N) -- Appendix A ----
        kind0 = torch.full((N, N), K_LOCKED, dtype=torch.int8)
        kind0[:half, :half] = K_EMPTY          # [y, x]: NW quadrant unlocked
        self.kind = kind0.to(dev).expand(B, P, N, N).clone()
        self.animal = torch.full((B, P, N, N), -1, dtype=torch.int8, device=dev)
        self.crop = torch.zeros((B, P, N, N), dtype=torch.int8, device=dev)
        self.yield_units = torch.zeros((B, P, N, N), dtype=torch.int8, device=dev)
        self.planted_day = torch.zeros((B, P, N, N), dtype=torch.int16, device=dev)
        self.placed_day = torch.zeros((B, P, N, N), dtype=torch.int16, device=dev)
        self.watered = torch.zeros((B, P, N, N), dtype=torch.bool, device=dev)
        self.consec_unwatered = torch.zeros((B, P, N, N), dtype=torch.int8, device=dev)
        self.mls = torch.zeros((B, P, N, N), dtype=torch.int32, device=dev)
        self.fert_until = torch.zeros((B, P, N, N), dtype=torch.int16, device=dev)
        self.fed = torch.zeros((B, P, N, N), dtype=torch.bool, device=dev)
        self.cared = torch.zeros((B, P, N, N), dtype=torch.bool, device=dev)
        self.fert_avail = torch.zeros((B, P, N, N), dtype=torch.bool, device=dev)
        self.consec_unfed = torch.zeros((B, P, N, N), dtype=torch.int8, device=dev)
        self.pending = torch.zeros((B, P, N, N), dtype=torch.int8, device=dev)

        # ---- farm scalars / units ----
        self.money = torch.full((B, P), float(self.starting_money),
                                dtype=torch.float64, device=dev)
        self.farmer_xy = torch.zeros((B, P, 2), dtype=torch.int8, device=dev)
        self.farmer_xy[:, :, 0] = self._spawn[0]
        self.farmer_xy[:, :, 1] = self._spawn[1]
        self.hands_xy = torch.zeros((B, P, H, 2), dtype=torch.int8, device=dev)
        self.hands_n = torch.zeros((B, P), dtype=torch.int8, device=dev)
        self.hires_today = torch.zeros((B, P), dtype=torch.int16, device=dev)
        self.quad_unlocked = torch.zeros((B, P, 3), dtype=torch.bool, device=dev)
        self.unit_inv = torch.zeros((B, P, 1 + H, I), dtype=torch.int16, device=dev)
        self.shed = torch.zeros((B, P, I), dtype=torch.int16, device=dev)
        self.seeds_t = torch.zeros((B, P, len(CROP_NAMES)), dtype=torch.int16, device=dev)

        # ---- market / town / clock ----
        self.mkt_inv = torch.full((B, N_MKT), E.MARKET_I0, dtype=torch.int32, device=dev)
        self.mkt_price = torch.tensor([E.MARKET_PARAMS[i]["base"] for i in PRODUCTS],
                                      dtype=torch.int32, device=dev).expand(B, N_MKT).clone()
        self.shops_seq = torch.full((B, E.MAX_SHOP_INSTANCES), -1,
                                    dtype=torch.int8, device=dev)
        self._shops_len = [0] * B              # host mirror of shops_seq fill
        self._step = 0
        self.day = 0
        self.hour = 0
        self.done = False
        self.reward = torch.zeros((B, P), dtype=torch.float64, device=dev)

        # Item insertion order per (lane, player, unit) -- see module docstring.
        self._inv_ord = [[[[]] for _ in range(P)] for _ in range(B)]

        # ---- device lookup tables ----
        t32 = lambda v: torch.tensor(v, dtype=torch.int32, device=dev)
        self._price_t = _price_table(dev)
        self._ar9 = torch.arange(N_MKT, dtype=torch.int64, device=dev)
        self._crop_first_t = t32(CROP_FIRST)
        self._crop_int_t = t32(CROP_INTERVAL).clamp(min=1)   # 0 only on non-ongoing
        self._crop_maxy_t = t32(CROP_MAXY)
        self._crop_ongoing_t = torch.tensor(CROP_ONGOING, dtype=torch.bool, device=dev)
        self._animal_first_t = t32(ANIMAL_FIRST)
        self._animal_int_t = t32(ANIMAL_INTERVAL)
        self._animal_max_t = t32(ANIMAL_MAX)
        self._crop_cost_t = torch.tensor(CROP_SEED_COST, dtype=torch.int64, device=dev)
        self._animal_cost_t = torch.tensor(ANIMAL_COST, dtype=torch.int64, device=dev)
        self._shop_cons_t = torch.tensor(_SHOP_CONS, dtype=torch.int32, device=dev)
        # Quadrant masks [q, y, x] in LAND_ORDER (NE, SW, SE).
        qm = torch.zeros((3, N, N), dtype=torch.bool)
        qm[0, :half, half:] = True             # NE
        qm[1, half:, :half] = True             # SW
        qm[2, half:, half:] = True             # SE
        self._quad_t = qm.to(dev)

    # ------------------------------------------------------------------
    # interpreter (engine_np.Episode.step)
    # ------------------------------------------------------------------

    def step_raw(self, actions):
        if self.done:
            return
        step = self._step
        day = step // self.turns_per_day

        # -- per-unit farm actions (host dispatch, tensor state) --
        for lane in range(self.B):
            acts = actions[lane]
            for p in range(self.NUM_PLAYERS):
                action = acts[p] if isinstance(acts[p], dict) else {}
                farmer_action = action.get("farmer", ["PASS"])
                hands_actions = action.get("hands", [])
                if not isinstance(hands_actions, list):
                    hands_actions = []

                # Atomic PLANT validation: if total PLANT requests for a crop
                # this turn exceed available seeds, drop ALL of them.
                plant_demand = {}
                for a in [farmer_action, *hands_actions]:
                    if isinstance(a, list) and len(a) >= 2 and a[0] == "PLANT":
                        plant_demand[a[1]] = plant_demand.get(a[1], 0) + 1
                blocked = set()
                for crop, n in plant_demand.items():
                    ci = CROP_IDX.get(crop) if isinstance(crop, str) else None
                    avail = int(self.seeds_t[lane, p, ci]) if ci is not None else 0
                    if n > avail:
                        blocked.add(crop)

                def _allowed(a):
                    if (isinstance(a, list) and len(a) >= 2 and a[0] == "PLANT"
                            and a[1] in blocked):
                        return ["PASS"]
                    return a

                self._apply_unit(lane, p, 0, _allowed(farmer_action), day)
                for h_idx, hand_action in enumerate(hands_actions):
                    self._apply_unit(lane, p, h_idx + 1, _allowed(hand_action), day)

        self._process_market(actions)
        self._town_consume(step)
        self._decay_plants(step)
        if (step + 1) % self.turns_per_day == 0:
            self._end_of_day(day)

        next_step = step + 1
        self._step = next_step
        self.day = next_step // self.turns_per_day
        self.hour = next_step % self.turns_per_day

        if step >= self.episode_steps - 2:
            self.done = True
            self.reward = self.money.clone()

    # ------------------------------------------------------------------
    # per-unit actions (engine_np._apply_unit_action, host transcription)
    # ------------------------------------------------------------------

    def _inv_add(self, lane, p, u, idx, n):
        cur = int(self.unit_inv[lane, p, u, idx])
        if cur == 0:
            self._inv_ord[lane][p][u].append(idx)
        self.unit_inv[lane, p, u, idx] = cur + n

    def _inv_take(self, lane, p, u, idx, n=1):
        cur = int(self.unit_inv[lane, p, u, idx])
        if cur < n:
            return False
        cur -= n
        self.unit_inv[lane, p, u, idx] = cur
        if cur == 0:
            self._inv_ord[lane][p][u].remove(idx)
        return True

    def _shed_room(self, lane, p):
        return max(0, self.shed_capacity - int(self.shed[lane, p].sum()))

    def _apply_unit(self, lane, p, u, action, day):
        """Invalid / illegal actions are silent no-ops (as in the engine)."""
        if not isinstance(action, list) or not action:
            return
        op = action[0]
        if u == 0:
            fx = int(self.farmer_xy[lane, p, 0])
            fy = int(self.farmer_xy[lane, p, 1])
        else:
            if u - 1 >= int(self.hands_n[lane, p]):
                return                          # hand does not exist
            fx = int(self.hands_xy[lane, p, u - 1, 0])
            fy = int(self.hands_xy[lane, p, u - 1, 1])

        if op in E.FARMER_MOVES:
            dx, dy = E.FARMER_MOVES[op]
            nx, ny = fx + dx, fy + dy
            if not (0 <= nx < self.N and 0 <= ny < self.N):
                return
            # Movement onto LOCKED tiles is allowed; tile ops still no-op.
            if u == 0:
                self.farmer_xy[lane, p, 0] = nx
                self.farmer_xy[lane, p, 1] = ny
            else:
                self.hands_xy[lane, p, u - 1, 0] = nx
                self.hands_xy[lane, p, u - 1, 1] = ny
            return

        if op == "PASS":
            return

        kind = int(self.kind[lane, p, fy, fx])

        # Shed operations resolve before the LOCKED guard.
        if op == "DROP":
            if (fx, fy) not in self._shed_adj:
                return
            ord_list = self._inv_ord[lane][p][u]
            for idx in list(ord_list):          # dict insertion order
                n = int(self.unit_inv[lane, p, u, idx])
                take = min(n, self._shed_room(lane, p))
                if take > 0:
                    self.shed[lane, p, idx] += take
                self.unit_inv[lane, p, u, idx] = 0   # overflow discarded
            ord_list.clear()
            return

        if op == "PICKUP":
            if (fx, fy) not in self._shed_adj:
                return
            if len(action) < 2:
                return
            item = action[1]
            n = int(action[2]) if len(action) >= 3 else 1
            if n <= 0:
                return
            idx = ITEM_IDX.get(item)
            available = int(self.shed[lane, p, idx]) if idx is not None else 0
            n = min(n, available)
            if n <= 0:
                return
            self.shed[lane, p, idx] -= n
            self._inv_add(lane, p, u, idx, n)
            return

        if op == "PLACE":
            if len(action) < 2:
                return
            item = action[1]
            # Animal placement: standing on a matching unoccupied structure.
            ai = ANIMAL_IDX.get(item) if isinstance(item, str) else None
            if (ai is not None and kind == ANIMAL_STRUCT[ai]
                    and int(self.animal[lane, p, fy, fx]) < 0):
                if self._inv_take(lane, p, u, N_MKT + ai, 1):
                    t = (lane, p, fy, fx)
                    self.animal[t] = ai
                    self.placed_day[t] = day
                    self.yield_units[t] = 0
                    self.consec_unfed[t] = 0
                    self.fed[t] = False
                    self.cared[t] = False
                    self.fert_avail[t] = False
                    self.pending[t] = 0
                return
            # Shed drop path: orthogonally adjacent to the shed.
            if (fx, fy) in self._shed_adj:
                n = int(action[2]) if len(action) >= 3 else 1
                if n <= 0:
                    return
                idx = ITEM_IDX.get(item)
                have = int(self.unit_inv[lane, p, u, idx]) if idx is not None else 0
                n = min(n, have)
                if n <= 0:
                    return
                n = min(n, self._shed_room(lane, p))
                if n <= 0:
                    return
                self._inv_take(lane, p, u, idx, n)
                self.shed[lane, p, idx] += n
            return

        # Everything below mutates the tile the unit stands on.
        if kind == K_LOCKED:
            return

        if op == "PLANT":
            if len(action) < 2:
                return
            crop = action[1]
            ci = CROP_IDX.get(crop) if isinstance(crop, str) else None
            if ci is None:
                return
            if kind != K_EMPTY:
                return
            if int(self.seeds_t[lane, p, ci]) <= 0:
                return
            self.seeds_t[lane, p, ci] -= 1
            t = (lane, p, fy, fx)
            ongoing = CROP_ONGOING[ci]
            self.kind[t] = K_PLANT
            self.animal[t] = -1
            self.crop[t] = ci
            self.planted_day[t] = day
            self.watered[t] = False
            self.consec_unwatered[t] = 1        # planting day counts as unwatered
            self.yield_units[t] = 0 if ongoing else 1
            self.mls[t] = (-1 if ongoing
                           else (day + CROP_MAXDAY[ci] + 1) * self.turns_per_day)
            self.fert_until[t] = -1
            return

        if op == "WATER":
            if kind != K_PLANT:
                return
            t = (lane, p, fy, fx)
            if bool(self.watered[t]):
                return
            self.watered[t] = True
            ci = int(self.crop[t])
            if not CROP_ONGOING[ci]:
                age_days = day - int(self.planted_day[t])
                window_start = (CROP_MAXDAY[ci] + 1) // 2
                if window_start <= age_days <= CROP_MAXDAY[ci]:
                    bonus = 2 if int(self.fert_until[t]) >= day else 1
                    self.yield_units[t] = min(CROP_MAXY[ci],
                                              int(self.yield_units[t]) + bonus)
            return

        if op == "HARVEST":
            t = (lane, p, fy, fx)
            if kind == K_PLANT:
                units = int(self.yield_units[t])
                if units <= 0:
                    return
                ci = int(self.crop[t])
                if day - int(self.planted_day[t]) < CROP_FIRST[ci]:
                    return
                self.yield_units[t] = 0
                self._inv_add(lane, p, u, ci, units)   # crop idx == item idx
                if not CROP_ONGOING[ci]:
                    self.kind[t] = K_EMPTY
                    self.animal[t] = -1
            elif kind in (K_COOP, K_PASTURE):
                ai = int(self.animal[t])
                if ai < 0:
                    return                      # empty structure: no yield key
                units = int(self.yield_units[t])
                if units <= 0:
                    return
                self.yield_units[t] = 0
                self._inv_add(lane, p, u, ANIMAL_PRODUCT[ai], units)
            return                              # WEED: yield_units absent -> 0

        if op == "FERTILIZE":
            if kind != K_PLANT:
                return
            if not self._inv_take(lane, p, u, FERT_I, 1):
                return
            t = (lane, p, fy, fx)
            self.fert_until[t] = max(int(self.fert_until[t]), day + 2)
            return

        if op == "DIG":
            if kind == K_EMPTY:
                return
            if kind in (K_COOP, K_PASTURE) and int(self.animal[lane, p, fy, fx]) >= 0:
                return                          # does not remove a placed animal
            self.kind[lane, p, fy, fx] = K_EMPTY
            self.animal[lane, p, fy, fx] = -1
            return

        if op == "BUILD_COOP" or op == "BUILD_PASTURE":
            if kind != K_EMPTY:
                return
            self.kind[lane, p, fy, fx] = (K_COOP if op == "BUILD_COOP" else K_PASTURE)
            self.animal[lane, p, fy, fx] = -1
            return

        if op == "FEED":
            t = (lane, p, fy, fx)
            if kind not in (K_COOP, K_PASTURE) or int(self.animal[t]) < 0:
                return
            if bool(self.fed[t]):
                return
            if not self._inv_take(lane, p, u, WHEAT_I, 1):
                return
            self.fed[t] = True
            return

        if op == "COLLECT_FERTILIZER":
            t = (lane, p, fy, fx)
            if kind not in (K_COOP, K_PASTURE) or int(self.animal[t]) < 0:
                return
            if not bool(self.fert_avail[t]):
                return
            self.fert_avail[t] = False
            self._inv_add(lane, p, u, FERT_I, 1)
            return

        if op == "CARE":
            t = (lane, p, fy, fx)
            if kind not in (K_COOP, K_PASTURE) or int(self.animal[t]) < 0:
                return
            if bool(self.cared[t]):
                return
            self.cared[t] = True
            return

    # ------------------------------------------------------------------
    # market (engine_np._process_market; D3 lockstep over (B,) tensors)
    # ------------------------------------------------------------------

    def _process_market(self, actions):
        B, dev = self.B, self.device
        queues = []
        for lane in range(B):
            qs = []
            for p in range(self.NUM_PLAYERS):
                action = actions[lane][p] if isinstance(actions[lane][p], dict) else {}
                m = action.get("market", [])
                q = list(m) if isinstance(m, list) else []
                qs.append(q[:self.max_market_orders])
            queues.append(qs)

        gmax = max((max(len(qs[0]), len(qs[1])) for qs in queues), default=0)
        for i in range(gmax):
            # Parse order i per lane/player; atomics (HIRE, BUY_LAND) resolve
            # here, once, in player order -- exactly as in the engine.
            op = torch.zeros((B, 2), dtype=torch.int64)
            item = torch.zeros((B, 2), dtype=torch.int64)
            rem = torch.zeros((B, 2), dtype=torch.int64)
            any_live = False
            for lane in range(B):
                for p in range(self.NUM_PLAYERS):
                    q = queues[lane][p]
                    if i >= len(q):
                        continue
                    ostate = E._parse_order(q[i])
                    if ostate is None:
                        continue
                    t = ostate["type"]
                    if t == "HIRE":
                        self._do_hire(lane, p)
                        continue
                    if t == "BUY_LAND":
                        self._do_buy_land(lane, p)
                        continue
                    # Sub-op validation the engine performs at first quote (a
                    # bad item aborts the order before committing anything).
                    o_item = ostate["item"]
                    if not isinstance(o_item, str):
                        continue
                    if t == "SELL":
                        idx = PRODUCT_IDX.get(o_item)
                        code = OP_SELL
                    elif t == "BUY_PRODUCT":
                        idx = PRODUCT_IDX.get(o_item) if o_item in ("WHEAT", "FERTILIZER") else None
                        code = OP_BUYP
                    elif t == "BUY_SEED":
                        idx = CROP_IDX.get(o_item)
                        code = OP_SEED
                    else:  # BUY_ANIMAL
                        idx = ANIMAL_IDX.get(o_item)
                        code = OP_ANIMAL
                    if idx is None:
                        continue
                    op[lane, p] = code
                    item[lane, p] = idx
                    rem[lane, p] = ostate["remaining"]
                    any_live = True
            if any_live:
                self._market_lockstep(op.to(dev), item.to(dev), rem.to(dev))
            # Engine refreshes after every order index; a lane whose queue is
            # already exhausted refreshes idempotently (prices = f(inventory)).
            self._refresh_prices()

    def _market_lockstep(self, op, item, rem):
        """Per-unit loop: serial over the unit index, (B,) tensors within."""
        dev = self.device
        B = self.B
        alive = op != OP_DEAD
        f64 = torch.float64
        for _esc in range(100_000):             # engine's escape counter
            live = alive & (rem > 0)
            if not bool(live.any()):
                break
            # -- quote both players at pre-commit inventory --
            price = torch.zeros((B, 2), dtype=torch.int64, device=dev)
            m = live & (op == OP_SELL)
            if bool(m.any()):
                l, pp = m.nonzero(as_tuple=True)
                it = item[l, pp]
                price[l, pp] = self._price_at(it, self.mkt_inv[l, it].to(torch.int64))
            m = live & (op == OP_BUYP)
            if bool(m.any()):
                # Quoted at post-buy inventory (inventory - 1).
                l, pp = m.nonzero(as_tuple=True)
                it = item[l, pp]
                price[l, pp] = self._price_at(it, self.mkt_inv[l, it].to(torch.int64) - 1)
            m = live & (op == OP_SEED)
            if bool(m.any()):
                l, pp = m.nonzero(as_tuple=True)
                price[l, pp] = self._crop_cost_t[item[l, pp]]
            m = live & (op == OP_ANIMAL)
            if bool(m.any()):
                l, pp = m.nonzero(as_tuple=True)
                price[l, pp] = self._animal_cost_t[item[l, pp]]

            # -- commit, player order; a failed commit kills the order --
            for p in range(self.NUM_PLAYERS):
                lv = live[:, p]
                if not bool(lv.any()):
                    continue
                opp = op[:, p]

                m = lv & (opp == OP_SELL)
                if bool(m.any()):
                    l = m.nonzero(as_tuple=True)[0]
                    it = item[l, p]
                    ok = self.shed[l, p, it] > 0
                    lo, ito = l[ok], it[ok]
                    pr = price[lo, p]
                    self.shed[lo, p, ito] -= 1
                    self.money[lo, p] += pr.to(f64)
                    inc = pr > 1                # $1 sales do not add supply
                    self.mkt_inv[lo[inc], ito[inc]] += 1
                    rem[lo, p] -= 1
                    alive[l[~ok], p] = False

                m = lv & (opp == OP_BUYP)
                if bool(m.any()):
                    l = m.nonzero(as_tuple=True)[0]
                    it = item[l, p]
                    pr = price[l, p]
                    ok = ((self.money[l, p] >= pr.to(f64))
                          & (self.shed[l, p].sum(-1) < self.shed_capacity))
                    lo, ito, po = l[ok], it[ok], pr[ok]
                    self.money[lo, p] -= po.to(f64)
                    self.shed[lo, p, ito] += 1
                    self.mkt_inv[lo, ito] -= 1
                    rem[lo, p] -= 1
                    alive[l[~ok], p] = False

                m = lv & (opp == OP_SEED)
                if bool(m.any()):
                    l = m.nonzero(as_tuple=True)[0]
                    it = item[l, p]
                    pr = price[l, p]
                    ok = self.money[l, p] >= pr.to(f64)
                    lo, ito, po = l[ok], it[ok], pr[ok]
                    self.money[lo, p] -= po.to(f64)
                    self.seeds_t[lo, p, ito] += 1
                    rem[lo, p] -= 1
                    alive[l[~ok], p] = False

                m = lv & (opp == OP_ANIMAL)
                if bool(m.any()):
                    l = m.nonzero(as_tuple=True)[0]
                    it = item[l, p]
                    pr = price[l, p]
                    ok = ((self.money[l, p] >= pr.to(f64))
                          & (self.shed[l, p].sum(-1) < self.shed_capacity))
                    lo, ito, po = l[ok], it[ok], pr[ok]
                    self.money[lo, p] -= po.to(f64)
                    self.shed[lo, p, N_MKT + ito] += 1
                    rem[lo, p] -= 1
                    alive[l[~ok], p] = False

    def _do_hire(self, lane, p):
        hires = int(self.hires_today[lane, p])
        cost = self.hire_mult * E._fib(hires)
        money = float(self.money[lane, p])
        if money < cost:                        # exact python float-vs-int compare
            return
        self.money[lane, p] = money - cost
        self.hires_today[lane, p] = hires + 1
        # Spawn: first free shed-access tile (NWSE), ties by min occupancy.
        hn = int(self.hands_n[lane, p])
        occ = {t: 0 for t in self._shed_tiles}
        farmer = (int(self.farmer_xy[lane, p, 0]), int(self.farmer_xy[lane, p, 1]))
        positions = [farmer] + [tuple(xy) for xy in
                                self.hands_xy[lane, p, :hn].tolist()]
        for pos in positions:
            if pos in occ:
                occ[pos] += 1
        best = sorted(occ.items(),
                      key=lambda kv: (kv[1], self._shed_tiles.index(kv[0])))[0][0]
        if hn >= self.H:
            raise OverflowError(f"lane {lane} player {p}: more than {self.H} hands")
        self.hands_xy[lane, p, hn, 0] = best[0]
        self.hands_xy[lane, p, hn, 1] = best[1]
        self.hands_n[lane, p] = hn + 1
        self._inv_ord[lane][p].append([])       # inventories.append({})

    def _do_buy_land(self, lane, p):
        n_extra = int(self.quad_unlocked[lane, p].sum())
        if n_extra >= len(E.LAND_ORDER):
            return
        cost = E.LAND_PRICES[n_extra]
        money = float(self.money[lane, p])
        if money < cost:
            return
        self.money[lane, p] = money - cost
        self.quad_unlocked[lane, p, n_extra] = True
        sel = self._quad_t[n_extra] & (self.kind[lane, p] == K_LOCKED)
        self.kind[lane, p][sel] = K_EMPTY

    # ------------------------------------------------------------------
    # town / prices / decay (tensor phases)
    # ------------------------------------------------------------------

    def _price_at(self, items, invs):
        iv = invs - _PRICE_LO
        if iv.numel():
            lo, hi = int(iv.min()), int(iv.max())
            if lo < 0 or hi >= _PRICE_W:
                raise RuntimeError(
                    f"market inventory {min(lo, hi) + _PRICE_LO} outside price "
                    f"table [{_PRICE_LO}, {_PRICE_HI}); widen the bounds")
        return self._price_t[items, iv]

    def _refresh_prices(self):
        self.mkt_price = self._price_at(
            self._ar9, self.mkt_inv.to(torch.int64)).to(torch.int32)

    def _town_consume(self, step):
        if step % self.town_shop_sell_interval == 0:
            # Each unlocked shop instance consumes independently.
            cons = self._shop_cons_t[self.shops_seq.clamp(min=0).long()]
            cons = cons * (self.shops_seq >= 0).unsqueeze(-1)
            self.mkt_inv -= cons.sum(1).to(torch.int32)
        if step % self.town_center_sell_interval == 0:
            self.mkt_inv[:, :N_MKT - 1] -= 1    # all products but FERTILIZER
        self._refresh_prices()

    def _decay_plants(self, step):
        m = ((self.kind == K_PLANT) & (self.mls >= 0) & (self.mls <= step)
             & (torch.remainder(step - self.mls.to(torch.int32), 2) == 0))
        if not bool(m.any()):
            return
        self.yield_units[m] -= 1
        w = m & (self.yield_units <= 0)
        self.kind[w] = K_WEED
        self.animal[w] = -1

    # ------------------------------------------------------------------
    # end of day (engine_np._end_of_day; D2 hybrid)
    # ------------------------------------------------------------------

    def _end_of_day(self, day):
        tpd = self.turns_per_day
        next_day = day + 1

        # -- daily plant refresh (no RNG: pure tensor transition) --
        plant = self.kind == K_PLANT
        was_watered = self.watered & plant
        self.consec_unwatered = torch.where(
            plant, torch.where(was_watered, 0, self.consec_unwatered + 1),
            self.consec_unwatered)
        self.watered = self.watered & ~plant
        to_weed = plant & (self.consec_unwatered >= 2)
        self.kind[to_weed] = K_WEED
        alive_p = plant & ~to_weed
        ci = self.crop.long()
        ongoing = self._crop_ongoing_t[ci]
        interval = self._crop_int_t[ci]
        maxy = self._crop_maxy_t[ci]
        dsf = next_day - self.planted_day.to(torch.int32) - self._crop_first_t[ci]
        prodm = (alive_p & ongoing & (dsf >= 0)
                 & (torch.remainder(dsf, interval) == 0))
        pcount = torch.div(dsf, interval, rounding_mode="floor") + 1
        prodm = prodm & (pcount <= maxy)
        # Fertilizer bonus only applies on watered days.
        fert = was_watered & (self.fert_until.to(torch.int32) >= day)
        newy = torch.minimum(maxy, self.yield_units.to(torch.int32)
                             + torch.where(fert, 2, 1))
        self.yield_units = torch.where(prodm, newy.to(torch.int8), self.yield_units)
        setml = prodm & (pcount == maxy)
        self.mls = torch.where(setml, (next_day + 1) * tpd, self.mls)

        # -- daily animal refresh (no RNG) --
        anim = self.animal >= 0
        fed = self.fed
        self.consec_unfed = torch.where(
            anim, torch.where(fed, 0, self.consec_unfed + 1), self.consec_unfed)
        escape = anim & (self.consec_unfed >= 2)
        self.animal[escape] = -1                # animal escapes; structure remains
        alive_a = anim & ~escape
        ai = self.animal.clamp(min=0).long()
        a_int = self._animal_int_t[ai]
        a_max = self._animal_max_t[ai]
        dsf_a = next_day - self.placed_day.to(torch.int32) - self._animal_first_t[ai]
        prod_a = alive_a & (dsf_a >= 0) & (torch.remainder(dsf_a, a_int) == 0)
        # Care bonus only consumed on a fed production day.
        bonus = torch.where(fed, self.pending.to(torch.int32), 0)
        newy_a = torch.minimum(a_max, self.yield_units.to(torch.int32) + 1 + bonus)
        self.yield_units = torch.where(prod_a, newy_a.to(torch.int8), self.yield_units)
        self.pending = torch.where(prod_a, 0, self.pending)
        care_acc = alive_a & self.cared & fed
        self.pending = torch.where(care_acc, self.pending + 1, self.pending)
        self.fert_avail = self.fert_avail | alive_a
        self.fed = self.fed & ~alive_a
        self.cared = self.cared & ~alive_a

        # -- weeds + shop unlock: the CPU RNG segment (D2) --
        # RNG call order per lane: P0's empty tiles row-major, then P1's, then
        # (every unlock day) rng.choice(sorted(SHOPS)). The intervening
        # refresh/drop phases consume no RNG, so hoisting them preserves the
        # byte stream.
        empty = (self.kind == K_EMPTY).cpu().tolist()   # [lane][p][y][x]
        wl, wp, wy, wx = [], [], [], []
        N = self.N
        for lane in range(self.B):
            rng = random.Random((self.seeds[lane] * 1_000_003) ^ day)
            for p in range(self.NUM_PLAYERS):
                lane_empty = empty[lane][p]
                for y in range(N):
                    row = lane_empty[y]
                    for x in range(N):
                        if row[x] and rng.random() < self.weed_spawn_chance:
                            wl.append(lane); wp.append(p); wy.append(y); wx.append(x)
            if next_day > 0 and next_day % self.town_shop_unlock_interval == 0:
                if self._shops_len[lane] < E.MAX_SHOP_INSTANCES:
                    name = rng.choice(SHOP_SORTED)
                    self.shops_seq[lane, self._shops_len[lane]] = SHOP_IDX[name]
                    self._shops_len[lane] += 1
        if wl:
            self.kind[wl, wp, wy, wx] = K_WEED

        # -- drop every unit inventory into the shed (host: order-dependent
        #    near capacity), then reset units for the new day --
        for lane in range(self.B):
            for p in range(self.NUM_PLAYERS):
                n_units = 1 + int(self.hands_n[lane, p])
                for u in range(n_units):
                    for idx in self._inv_ord[lane][p][u]:
                        n = int(self.unit_inv[lane, p, u, idx])
                        take = min(n, self._shed_room(lane, p))
                        if take > 0:
                            self.shed[lane, p, idx] += take
                self.unit_inv[lane, p] = 0
                self._inv_ord[lane][p] = [[]]
        self.farmer_xy[:, :, 0] = self._spawn[0]
        self.farmer_xy[:, :, 1] = self._spawn[1]
        self.hands_n.zero_()
        self.hires_today.zero_()

    # ------------------------------------------------------------------
    # snapshot (byte-compatible with engine_np.Episode.snapshot)
    # ------------------------------------------------------------------

    def snapshot(self, lane):
        N = self.N
        kind = self.kind[lane].tolist()
        animal = self.animal[lane].tolist()
        crop = self.crop[lane].tolist()
        yu = self.yield_units[lane].tolist()
        planted = self.planted_day[lane].tolist()
        placed = self.placed_day[lane].tolist()
        watered = self.watered[lane].tolist()
        cuw = self.consec_unwatered[lane].tolist()
        mls = self.mls[lane].tolist()
        fert_u = self.fert_until[lane].tolist()
        fed = self.fed[lane].tolist()
        cared = self.cared[lane].tolist()
        fav = self.fert_avail[lane].tolist()
        cuf = self.consec_unfed[lane].tolist()
        pend = self.pending[lane].tolist()
        money = self.money[lane].tolist()
        farmer = self.farmer_xy[lane].tolist()
        hands_n = self.hands_n[lane].tolist()
        hands = self.hands_xy[lane].tolist()
        hires = self.hires_today[lane].tolist()
        quads = self.quad_unlocked[lane].tolist()
        inv = self.unit_inv[lane].tolist()
        shed = self.shed[lane].tolist()
        seeds = self.seeds_t[lane].tolist()

        farms, private = [], []
        for p in range(self.NUM_PLAYERS):
            tiles = []
            for y in range(N):
                row = []
                for x in range(N):
                    k = kind[p][y][x]
                    if k == K_EMPTY:
                        row.append(None)
                    elif k == K_LOCKED:
                        row.append("LOCKED")
                    elif k == K_WEED:
                        row.append({"kind": "WEED"})
                    elif k == K_PLANT:
                        row.append({
                            "kind": "PLANT",
                            "crop": CROP_NAMES[crop[p][y][x]],
                            "planted_day": planted[p][y][x],
                            "watered_today": watered[p][y][x],
                            "consecutive_unwatered": cuw[p][y][x],
                            "yield_units": yu[p][y][x],
                            "max_lifespan_step": mls[p][y][x],
                            "fertilized_until_day": fert_u[p][y][x],
                        })
                    else:                       # COOP / PASTURE
                        ai = animal[p][y][x]
                        if ai < 0:
                            row.append({"kind": KIND_NAME[k]})
                        else:
                            row.append({
                                "kind": KIND_NAME[k],
                                "animal": ANIMAL_NAMES[ai],
                                "placed_day": placed[p][y][x],
                                "yield_units": yu[p][y][x],
                                "consecutive_unfed": cuf[p][y][x],
                                "fed_today": fed[p][y][x],
                                "cared_today": cared[p][y][x],
                                "fertilizer_available": fav[p][y][x],
                                "pending_care_bonus": pend[p][y][x],
                            })
                tiles.append(row)
            farms.append({
                "farmer": farmer[p],
                "hands": hands[p][:hands_n[p]],
                "hires_today": hires[p],
                "money": money[p],
                "tiles": tiles,
                "unlocked_quadrants": (["NW"] + [E.LAND_ORDER[i] for i in range(3)
                                                 if quads[p][i]]),
            })
            private.append({
                "inventories": [
                    {ITEMS[i]: v for i, v in enumerate(inv[p][u]) if v > 0}
                    for u in range(1 + hands_n[p])
                ],
                "seeds": {c: seeds[p][ci] for ci, c in enumerate(CROP_NAMES)},
                "shed": {it: shed[p][i] for i, it in enumerate(ITEMS)},
            })

        mi = self.mkt_inv[lane].tolist()
        mp = self.mkt_price[lane].tolist()
        return {
            "day": self._step // self.turns_per_day,
            "hour": self._step % self.turns_per_day,
            "farms": farms,
            "market": {"inventory": {it: mi[i] for i, it in enumerate(PRODUCTS)},
                       "prices": {it: mp[i] for i, it in enumerate(PRODUCTS)}},
            "town": {"unlocked_shops": [SHOP_SORTED[int(s)] for s in
                                        self.shops_seq[lane, :self._shops_len[lane]].tolist()]},
            "private": private,
        }
