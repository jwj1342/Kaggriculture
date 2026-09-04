"""TorchRL EnvBase over engine_t.EpisodeT: the device-agnostic batched env.

One KGTensorEnv is B lockstep two-player episodes with the learner on one
seat and a scripted/frozen opponent on the other, exposed as a single-agent
TorchRL environment of batch_size [B] (the VMAS/Brax pattern: the simulator
itself is the vectorization; no ParallelEnv processes anywhere). The same
class runs on CPU and CUDA -- `device` is the only switch, which is what
finally merges the rl-baseline (CPU) and tensorize (GPU) lines.

Semantics are train_t.py's collect() verbatim:
  * obs        = features_t.encode_t(ep, seat)            (B, OBS_DIM) float32
  * masks      = features_t.masks_t(ep, seat)             (B, 23/22) bool
  * action     = (farmer, market) int64 head indices, stacked (B, 2)
  * opponent   = opponents_t.starter_indices (or a frozen ActorNet, argmax
                 over masked logits -- the exported-agent behaviour)
  * reward     = (net_worth_t(s') - net_worth_t(s)) / 3000, float64 math
                 rounded once to float32, plus win_bonus * {+1,-1,0} by
                 final money at the terminal step
  * episodes are fixed-length (episode_steps), all lanes terminate together,
    so the terminal bootstrap is exactly zero and every _reset is global.
  * seeds: base_seed * 1_000_003 + episode_index * B + lane, the train_t
    derivation, so runs are reproducible given (base_seed, B).

`money` / `opp_money` ride along as observation entries (never fed to the
network) so the trainer can read win rates off the collected batch.
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_RL = os.path.dirname(_HERE)
for _p in (_HERE, _RL):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np
import torch
from tensordict import TensorDict
from torchrl.data import Binary, Composite, MultiCategorical, Unbounded
from torchrl.envs import EnvBase

import actions as A
import kg_rules
import obs as O
import engine_t
import engine_t_idx  # noqa: F401  (attaches EpisodeT.step_idx)
import features_t
import opponents_t
import potential_t
from trl_policy import ActorNet, NEG


def hand_task_mask_t(ep, player, n_hands=None):
    """(B, MAX_HANDS, N_HAND_TASK) bool -- the device twin of
    actions.hand_task_mask: AUTO/IDLE legal for live hand slots, a chore
    family legal while it has a target (step_idx's family definitions,
    which are actions.analyze's), dead slots IDLE-only. Gate: test_multi M4.
    """
    import engine_t_idx as X
    B, dev = ep.B, ep.device
    NN = ep.N * ep.N
    if n_hands is None:
        n_hands = A.MAX_HANDS
    day = ep._step // ep.turns_per_day
    kind = ep.kind[:, player].reshape(B, NN)
    anim = ep.animal[:, player].reshape(B, NN) >= 0
    plant = kind == engine_t.K_PLANT
    yu = ep.yield_units[:, player].reshape(B, NN) > 0
    age8 = (day - ep.planted_day[:, player].reshape(B, NN)).to(torch.int8)
    tabs = X._tabs(dev)
    cf8 = tabs.crop_first_i8[ep.crop[:, player].reshape(B, NN).int()]
    fams = torch.stack([
        ((plant & yu & (age8 >= cf8)) | (anim & yu)).any(-1),   # HARVEST
        (plant & ~ep.watered[:, player].reshape(B, NN)).any(-1),  # WATER
        (anim & ~ep.cared[:, player].reshape(B, NN)).any(-1),     # CARE
        (anim & ep.fert_avail[:, player].reshape(B, NN)).any(-1),  # COLLECT
        (kind == engine_t.K_WEED).any(-1),                         # DIG
    ], 1)                                                          # (B, 5)
    alive = (torch.arange(n_hands, device=dev).view(1, -1)
             < ep.hands_n[:, player].view(B, 1))                   # (B, H)
    mask = torch.zeros((B, n_hands, A.N_HAND_TASK), dtype=torch.bool,
                       device=dev)
    mask[:, :, 0] = alive                                          # AUTO
    mask[:, :, 1] = True                                           # IDLE
    mask[:, :, 2:2 + fams.shape[1]] = alive.unsqueeze(-1) & fams.unsqueeze(1)
    # FEED: an unfed animal exists and wheat is reachable -- that hand's
    # own inventory or the shed (actions.hand_task_mask's per-hand row)
    unfed_any = (anim & ~ep.fed[:, player].reshape(B, NN)).any(-1)  # (B,)
    shed_wheat = ep.shed[:, player, engine_t.WHEAT_I] > 0           # (B,)
    hand_wheat = ep.unit_inv[:, player, 1:n_hands + 1,
                             engine_t.WHEAT_I] > 0                  # (B, H)
    mask[:, :, 7] = (alive & (shed_wheat.view(B, 1) | hand_wheat)
                     & unfed_any.view(B, 1))
    # PLANT: a viable farm seed (deadline not passed) plus an empty tile
    viable = ((ep.seeds_t[:, player] > 0)
              & (day <= tabs.plant_deadline).view(1, -1))
    plant_ok = viable.any(-1) & (kind == engine_t.K_EMPTY).any(-1)  # (B,)
    mask[:, :, 8] = alive & plant_ok.view(B, 1)
    # FERTILIZE: an unfert plant exists and fertilizer is reachable --
    # that hand's own inventory or the shed (FEED's shape, item renamed)
    unfert_any = (plant & ((ep.fert_until[:, player].reshape(B, NN)
                            - day) < 0)).any(-1)                    # (B,)
    shed_fert = ep.shed[:, player, engine_t.FERT_I] > 0             # (B,)
    hand_fert = ep.unit_inv[:, player, 1:n_hands + 1,
                            engine_t.FERT_I] > 0                    # (B, H)
    mask[:, :, 9] = (alive & (shed_fert.view(B, 1) | hand_fert)
                     & unfert_any.view(B, 1))
    # BUILD: an empty tile and the means to stock a pasture. PLACE: a
    # reachable animal with a free matching structure.
    empty_any = (kind == engine_t.K_EMPTY).any(-1)                  # (B,)
    animal_item = X._tabs(dev).animal_item                          # (3,)
    min_animal = min(kg_rules.ANIMALS[a]["cost"] for a in A.ANIMAL_LIST)
    stockable = ((ep.money[:, player] >= min_animal)
                 | (ep.shed[:, player].index_select(
                     -1, animal_item) > 0).any(-1))
    mask[:, :, 10] = alive & (empty_any & stockable).view(B, 1)
    coop_free = ((kind == engine_t.K_COOP) & ~anim).any(-1)
    pasture_free = ((kind == engine_t.K_PASTURE) & ~anim).any(-1)
    free = torch.stack([coop_free, pasture_free, pasture_free], -1)
    shed_animals = ep.shed[:, player].index_select(-1, animal_item) > 0
    shed_place = (shed_animals & free).any(-1)
    hand_animals = ep.unit_inv[:, player, 1:n_hands + 1].index_select(
        -1, animal_item) > 0
    hand_place = (hand_animals & free.view(B, 1, 3)).any(-1)
    mask[:, :, 11] = alive & (shed_place.view(B, 1) | hand_place)

    # Appended RAW_* classes execute one exact primitive at the hand's current
    # tile.  Unlike persistent chores they are legal only when that primitive
    # can mutate state; this keeps the wider imitation head mechanically dense.
    hxy = ep.hands_xy[:, player, :n_hands].to(torch.int64)
    hpos = hxy[..., 1] * ep.N + hxy[..., 0]

    def at(plane):
        return plane.gather(1, hpos)

    hand_inv = ep.unit_inv[:, player, 1:n_hands + 1]
    carry = hand_inv.to(torch.int64).sum(-1)
    on_shed = tabs.shed100.index_select(0, hpos.reshape(-1)).view(B, n_hands)
    kind_h = kind.gather(1, hpos)
    anim_h = anim.gather(1, hpos)

    def raw(name, legal):
        mask[:, :, A.HAND_TASKS.index(name)] = alive & legal

    raw("RAW_MOVE_N", hxy[..., 1] > 0)
    raw("RAW_MOVE_S", hxy[..., 1] < ep.N - 1)
    raw("RAW_MOVE_E", hxy[..., 0] < ep.N - 1)
    raw("RAW_MOVE_W", hxy[..., 0] > 0)
    raw("RAW_WATER", at(plant & ~ep.watered[:, player].reshape(B, NN)))
    raw("RAW_HARVEST", at((plant & yu & (age8 >= cf8)) | (anim & yu)))
    raw("RAW_FEED", at(anim & ~ep.fed[:, player].reshape(B, NN))
        & (hand_inv[..., engine_t.WHEAT_I] > 0))
    raw("RAW_CARE", at(anim & ~ep.cared[:, player].reshape(B, NN)))
    raw("RAW_COLLECT_FERTILIZER",
        at(anim & ep.fert_avail[:, player].reshape(B, NN)))
    raw("RAW_FERTILIZE",
        at(plant & ((ep.fert_until[:, player].reshape(B, NN) - day) < 0))
        & (hand_inv[..., engine_t.FERT_I] > 0))
    raw("RAW_DIG", at(kind == engine_t.K_WEED))
    raw("RAW_BUILD_COOP", kind_h == engine_t.K_EMPTY)
    raw("RAW_BUILD_PASTURE", kind_h == engine_t.K_EMPTY)
    raw("RAW_DROP", on_shed & (carry > 0))
    for crop_i, crop in enumerate(A.CROP_LIST):
        raw(f"RAW_PLANT_{crop}",
            (kind_h == engine_t.K_EMPTY)
            & (ep.seeds_t[:, player, crop_i] > 0).view(B, 1)
            & (day <= A.PLANT_DEADLINE[crop]))
    for animal_i, animal in enumerate(A.ANIMAL_LIST):
        structure = (engine_t.K_COOP if kg_rules.ANIMALS[animal]["structure"]
                     == "COOP" else engine_t.K_PASTURE)
        raw(f"RAW_PLACE_{animal}",
            (kind_h == structure) & ~anim_h
            & (hand_inv[..., engine_t.N_MKT + animal_i] > 0))
    for item in A.HAND_PICKUP_ITEMS:
        item_i = engine_t.ITEM_IDX[item]
        raw(f"RAW_PICKUP_{item}",
            on_shed & (ep.shed[:, player, item_i] > 0).view(B, 1))
    return mask


# ---- kickstart teacher labels (Schmitt et al. 2018 / Lux-S1 recipe) --------
# barnyard_t's farmer intent and exact per-turn hand ops mapped into the
# policy's head vocabulary, queried on the LEARNER's own states -- teacher
# supervision without the distribution shift that killed the old line's BC.
# The metered multi-order market still collapses to one priority-picked head
# index, but every unit intent that has a hand-task action is preserved.

_KS_LUTS = {}


def _ks_luts(device):
    import engine_t_idx as X
    key = str(device)
    if key not in _KS_LUTS:
        i64 = torch.int64
        hand = [-1] * 18                    # unsupported raw op
        hand[X.U_PASS] = 1                  # unassigned unit: barnyard idles it
        for op, name in (
                (X.U_MOVE_N, "RAW_MOVE_N"), (X.U_MOVE_S, "RAW_MOVE_S"),
                (X.U_MOVE_E, "RAW_MOVE_E"), (X.U_MOVE_W, "RAW_MOVE_W"),
                (X.U_WATER, "RAW_WATER"),
                (X.U_HARVEST, "RAW_HARVEST"),
                (X.U_FEED, "RAW_FEED"), (X.U_CARE, "RAW_CARE"),
                (X.U_COLLECT, "RAW_COLLECT_FERTILIZER"),
                (X.U_FERTILIZE, "RAW_FERTILIZE"),
                (X.U_DIG, "RAW_DIG"),
                (X.U_BUILD_COOP, "RAW_BUILD_COOP"),
                (X.U_BUILD_PASTURE, "RAW_BUILD_PASTURE"),
                (X.U_DROP, "RAW_DROP")):
            hand[op] = A.HAND_TASKS.index(name)
        farmer = [0] * 18                   # default PASS
        for op, name in ((X.U_WATER, "WATER"), (X.U_HARVEST, "HARVEST"),
                         (X.U_FEED, "FEED"), (X.U_CARE, "CARE"),
                         (X.U_COLLECT, "COLLECT_FERT"),
                         (X.U_FERTILIZE, "FERTILIZE"),
                         (X.U_DIG, "DIG_WEED"), (X.U_BUILD_COOP, "BUILD_COOP"),
                         (X.U_BUILD_PASTURE, "BUILD_PASTURE"),
                         (X.U_DROP, "DROP")):
            farmer[op] = A.FARMER_ACTIONS.index(name)
        farmer[X.U_PLANT] = 15              # + crop arg below
        farmer[X.U_PLACE] = 20              # + animal arg below
        pickup = torch.full((len(engine_t.ITEMS),), -1, dtype=i64,
                            device=device)
        for item in A.HAND_PICKUP_ITEMS:
            pickup[engine_t.ITEM_IDX[item]] = A.HAND_TASKS.index(
                f"RAW_PICKUP_{item}")
        _KS_LUTS[key] = {
            "hand": torch.tensor(hand, dtype=i64, device=device),
            "farmer": torch.tensor(farmer, dtype=i64, device=device),
            "pickup": pickup}
    return _KS_LUTS[key]


def kickstart_labels(ep, player, ops=None):
    """(teacher_f (B,), teacher_m (B,), teacher_h (B, MAX_HANDS)) int64 --
    barnyard's decision on `player`'s seat in head-index vocabulary.
    Dead hand slots carry -1 (the CE loss skips them)."""
    import barnyard_t
    import engine_t_idx as X
    dev, B = ep.device, ep.B
    if ops is None:
        ops = barnyard_t.compute(ep, player)
    task, targ = ops["task"], ops["task_arg"]                  # (B, U)
    luts = _ks_luts(dev)
    f = luts["farmer"][task[:, 0]]
    f = torch.where(task[:, 0] == X.U_PLANT, 15 + targ[:, 0], f)
    f = torch.where(task[:, 0] == X.U_PLACE, 20 + targ[:, 0], f)
    if ops["h_op"]:
        hop = torch.stack(ops["h_op"], 1)
        harg = torch.stack(ops["h_arg"], 1)
    else:
        hop = torch.empty((B, 0), dtype=torch.int64, device=dev)
        harg = torch.empty_like(hop)
    h = luts["hand"][hop]
    for crop_i, crop in enumerate(A.CROP_LIST):
        h = torch.where(
            (hop == X.U_PLANT) & (harg == crop_i),
            torch.full_like(h, A.HAND_TASKS.index(f"RAW_PLANT_{crop}")), h)
    for animal_i, animal in enumerate(A.ANIMAL_LIST):
        h = torch.where(
            (hop == X.U_PLACE) & (harg == animal_i),
            torch.full_like(h, A.HAND_TASKS.index(f"RAW_PLACE_{animal}")), h)
    pickup_arg = harg.clamp(min=0, max=len(engine_t.ITEMS) - 1)
    h = torch.where(hop == X.U_PICKUP, luts["pickup"][pickup_arg], h)
    hn = ep.hands_n[:, player].to(torch.int64)
    ar = torch.arange(h.shape[1], device=dev).view(1, -1)
    h = torch.where(ar < hn.view(B, 1), h, torch.full_like(h, -1))
    if h.shape[1] < A.MAX_HANDS:
        h = torch.cat([h, torch.full((B, A.MAX_HANDS - h.shape[1]), -1,
                                     dtype=h.dtype, device=dev)], 1)
    else:
        h = h[:, :A.MAX_HANDS]
    # market: one head index from up to 10 orders; later writes win, so
    # the priority is SELL < BUY_WHEAT/FERT < BUY_SEED < HIRE < BUY_LAND <
    # BUY_ANIMAL (rarest and most build-critical claims the single slot)
    m_op, m_item, m_rem = ops["m_op"], ops["m_item"], ops["m_rem"]

    def first_item(cond):
        idx = torch.argmax(cond.to(torch.int64), 1)
        return m_item.gather(1, idx.view(B, 1)).squeeze(1), cond.any(1)

    m = torch.zeros((B,), dtype=torch.int64, device=dev)       # NOOP
    sell = m_op == engine_t.OP_SELL
    qty = torch.where(sell, m_rem, torch.zeros_like(m_rem))
    si = torch.argmax(qty, 1).view(B, 1)
    s_it = m_item.gather(1, si).squeeze(1)
    s_q = qty.gather(1, si).squeeze(1)
    held = ep.shed[:, player].to(torch.int64).gather(
        1, s_it.view(B, 1)).squeeze(1)
    # a metered teacher sell (qty <= ceil(half)) maps to SELL_HALF_<p>
    metered = s_q * 2 <= held + 1
    m = torch.where(sell.any(1),
                    torch.where(metered, 22 + s_it, 1 + s_it), m)
    it, any_ = first_item(m_op == engine_t.OP_BUYP)
    m = torch.where(any_ & (it == engine_t.WHEAT_I), torch.full_like(m, 15), m)
    m = torch.where(any_ & (it == engine_t.FERT_I), torch.full_like(m, 16), m)
    it, any_ = first_item(m_op == engine_t.OP_SEED)
    m = torch.where(any_, 10 + it, m)
    m = torch.where((m_op == X.OP_HIRE).any(1), torch.full_like(m, 21), m)
    m = torch.where((m_op == X.OP_LAND).any(1), torch.full_like(m, 20), m)
    it, any_ = first_item(m_op == engine_t.OP_ANIMAL)
    m = torch.where(any_, 17 + it, m)
    return f, m, h


class FrozenPolicyOpponent:
    """A past checkpoint / exported weights.npz / in-memory snapshot played
    greedily (argmax over masked logits) -- the behaviour of an exported
    numpy agent, so league members and submissions are represented
    faithfully on device. Residual exports (d_* arrays / base.+delta. keys)
    are summed exactly like the export template does -- a snapshot of a
    ResidualActor must play the combined policy, never just the prior."""

    def __init__(self, path, device="cpu"):
        if path.endswith(".npz"):
            arrays = dict(np.load(path))
        else:
            ck = torch.load(path, map_location="cpu", weights_only=False)
            full = ck.get("model") or ck.get("state_dict")
            arrays = self._sd_to_arrays(full)
        self._build(arrays, device)

    @staticmethod
    def _sd_to_arrays(full):
        from trl_policy import actor_arrays
        if any(k.startswith("base.") for k in full):
            arrays = actor_arrays(full, "base.")
            arrays.update({f"d_{k}": v
                           for k, v in actor_arrays(full, "delta.").items()})
            return arrays
        return actor_arrays(full)

    @classmethod
    def from_state_np(cls, arrays, device="cpu"):
        """Build from state_np() arrays (league self-snapshots); residual
        actors hand over base + d_* and both halves are honoured."""
        self = cls.__new__(cls)
        self._build(arrays, device)
        return self

    @staticmethod
    def _net_from_sd(sd, device):
        from trl_policy import adapt_legacy_observation
        sd, _ = adapt_legacy_observation(sd, O.OBS_DIM)
        h1, obs_dim = sd["l1.weight"].shape
        h2 = sd["l2.weight"].shape[0]
        net = ActorNet(obs_dim, sd["farmer.weight"].shape[0],
                       sd["market.weight"].shape[0], h1, h2)
        net.load_state_dict(sd)
        return net.to(device).eval()

    def _build(self, arrays, device):
        from trl_policy import arrays_to_sd

        def net_sd(prefix=""):
            sd = arrays_to_sd(arrays, prefix)
            sd.pop("hands.weight", None)   # the hand head is applied
            sd.pop("hands.bias", None)     # separately (see _hands below)
            sd.pop("couple_f", None)       # coupling tables likewise --
            sd.pop("couple_h", None)       # played via self._couple below
            return sd

        # Coupled snapshots (CoupledMultiHeadMasked exports): the market
        # argmax must be conditioned on the farmer/hand argmaxes, or the
        # snapshot silently plays the UNCOUPLED base policy -- the same
        # loads-the-unwrapped-agent failure mode CLAUDE.md's agent-contract
        # section warns about, one layer down.
        self._couple = None
        if "cfw" in arrays:
            self._couple = (torch.as_tensor(arrays["cfw"]).float().to(device),
                            torch.as_tensor(arrays["chw"]).float().to(device))

        self.net = self._net_from_sd(net_sd(), device)
        self.delta = None
        if any(str(k).startswith("d_") for k in arrays):
            self.delta = self._net_from_sd(net_sd("d_"), device)
        # multi-head exports carry a hands head on exactly one trunk; the
        # snapshot must play it, never silently fall back to AUTO
        self._hands = None
        for pfx, owner in (("", "net"), ("d_", "delta")):
            if f"{pfx}hw" in arrays:
                from trl_policy import adapt_legacy_hand_head
                hand_sd = {
                    "hands.weight": torch.as_tensor(arrays[f"{pfx}hw"]),
                    "hands.bias": torch.as_tensor(arrays[f"{pfx}hb"]),
                }
                hand_sd, _ = adapt_legacy_hand_head(hand_sd, new_bias=NEG)
                self._hands = (owner, hand_sd["hands.weight"].to(device),
                               hand_sd["hands.bias"].to(device))

    @property
    def provides_hands(self):
        return self._hands is not None

    def _logits(self, x):
        fl, ml = self.net(x)
        if self.delta is not None:
            dfl, dml = self.delta(x)
            fl, ml = fl + dfl, ml + dml
        return fl, ml

    def _hand_logits(self, x):
        owner, hw, hb = self._hands
        trunk = self.net if owner == "net" else self.delta
        h = torch.relu(trunk.l1(x))
        h = torch.relu(trunk.l2(h))
        hl = h @ hw.t() + hb
        return hl.view(*x.shape[:-1], -1, A.N_HAND_TASK)

    @torch.no_grad()
    def __call__(self, ep, player):
        x = features_t.encode_t(ep, player)
        fm, mm = features_t.masks_t(ep, player)
        fl, ml = self._logits(x)
        fa = fl.masked_fill(~fm, NEG).argmax(-1)
        if self._hands is None:
            if self._couple is not None:
                raise ValueError("coupled snapshot without a hand head -- "
                                 "the coupling conditions on hand tasks")
            ma = ml.masked_fill(~mm, NEG).argmax(-1)
            return fa, ma
        hl = self._hand_logits(x)
        hm = hand_task_mask_t(ep, player, hl.shape[-2])
        ha = hl.masked_fill(~hm, NEG).argmax(-1)
        if self._couple is not None:
            cfw, chw = self._couple
            ml = ml + cfw.t()[fa] + chw.t()[ha].mean(-2)
        ma = ml.masked_fill(~mm, NEG).argmax(-1)
        return fa, ma, ha


def _make_opponent(spec, device):
    if spec == "starter" or spec is None:
        return opponents_t.starter_indices
    if spec == "barnyard":
        import barnyard_t
        return barnyard_t.BarnyardOpponent()
    if str(spec).startswith("tape:"):
        # recorded top-meta line as an open-loop override opponent
        # (tape_t; gate: dollar-exact vs the pure python replay)
        import tape_t
        return tape_t.TapeOpponent(str(spec)[5:], device)
    return FrozenPolicyOpponent(spec, device)


# ---- build-curve potential (AlphaStar z, measured) --------------------------
# Per-day targets from the 231k-season anatomy (docs/RUNS.md 2026-08-20,
# 40 top-ladder seats): ~4 animals by day 2, 9 by day 8, plateau ~14;
# land 1 -> 2 (day 7) -> 3 (day 10); ~11-12 hands from day 8. The phi term
# is CURVE-CAPPED -- min(count, target(day)) -- so it pays for approaching
# the top build and stops paying beyond it; being a potential, an escaped
# animal or a fired hand takes its credit back.

def _interp30(points):
    out, (d0, v0) = [], points[0]
    pts = list(points) + [(29, points[-1][1])]
    j = 0
    for d in range(30):
        while j + 1 < len(pts) and pts[j + 1][0] <= d:
            j += 1
        if j + 1 < len(pts) and pts[j + 1][0] > pts[j][0]:
            a, b = pts[j], pts[j + 1]
            v = a[1] + (b[1] - a[1]) * (d - a[0]) / (b[0] - a[0])
        else:
            v = pts[j][1]
        out.append(v)
    return out

_BUILD_ANIMALS = _interp30([(0, 0.0), (2, 4.0), (8, 9.0), (11, 13.0),
                            (14, 14.5)])
_BUILD_LAND = _interp30([(0, 1.0), (7, 2.0), (10, 3.0)])
_BUILD_HANDS = _interp30([(0, 0.0), (2, 4.0), (8, 11.0), (11, 12.0)])
# crops-by-day from the same 40-seat anatomy (18.5 by day 2, ~60 at the
# day-14 plateau): draught's dairy line left 35 tiles EMPTY all season --
# the missing 38% of top income is crops, and nothing paid for planting
# breadth until this term
_BUILD_CROPS = _interp30([(0, 0.0), (2, 18.0), (8, 27.0), (11, 32.0),
                          (14, 58.0), (26, 54.0), (29, 8.0)])


def build_phi(ep, player, tabs):
    """(B,) float64: curve-capped build credit for one seat."""
    day = min(29, ep._step // ep.turns_per_day)
    a = (ep.animal[:, player] >= 0).sum((-1, -2)).to(torch.float64)
    land = ep.quad_unlocked[:, player].to(torch.float64).sum(-1)
    hands = ep.hands_n[:, player].to(torch.float64)
    kind = ep.kind[:, player]
    crops = (kind == engine_t.K_PLANT).to(torch.float64).sum((-1, -2))
    ta, tl, th, tc = tabs[0][day], tabs[1][day], tabs[2][day], tabs[3][day]
    return (400.0 * torch.clamp(a, max=ta)
            + 1000.0 * torch.clamp(land - 1.0, min=0.0, max=tl - 1.0)
            + 100.0 * torch.clamp(hands, max=th)
            + 30.0 * torch.clamp(crops, max=tc))


class KGTensorEnv(EnvBase):
    batch_locked = True

    def __init__(self, B, device="cpu", seat=0, alternate_seat=False,
                 episode_steps=720, base_seed=0, opponent="starter",
                 win_bonus=3.0, margin_bonus=0.0, margin_scale=30000.0,
                 opp_noise=0.0, handicap=0, potential="networth",
                 shape_scale=3000.0, opp_lambda=0.0, multi_head=False,
                 kickstart="", build_bonus=0.0, bank="", bank_frac=0.5,
                 shape_gamma=0.0, ks_every=1, fert_credit=0.0,
                 land_value=0.0, fixed_market_profile="",
                 plant_credit=0.0, animal_credit=0.0, fixed_farm_tape="",
                 farm_tape_market="buys"):
        super().__init__(device=torch.device(device),
                         batch_size=torch.Size([int(B)]))
        self.B = int(B)
        self.seat = int(seat)
        self.alternate_seat = bool(alternate_seat)
        self.episode_steps = int(episode_steps)
        self.base_seed = int(base_seed)
        self.win_bonus = float(win_bonus)
        # terminal margin reward: w * tanh((money_me - money_opp) / scale).
        # Bounded on purpose -- the per-step FULL zero-sum shaping was a
        # documented negative result (lambda=1.0 learnt mutual destruction);
        # a bounded terminal margin grades losses ("lose less") without
        # rewarding hurting the opponent at every step.
        self.margin_bonus = float(margin_bonus)
        self.margin_scale = float(margin_scale)
        # opponent smoothing: per lane, with prob opp_noise replace the
        # opponent's action with a uniformly random LEGAL one (handicap
        # curriculum's companion -- it dents an opponent's dominance
        # without touching its identity)
        self.opp_noise = float(opp_noise)
        # handicap curriculum: extra starting money for the learner seat,
        # applied at reset on the TRAINING engine only (eval always runs the
        # reference engine); trl_pool steps it down as the win gate passes
        self.handicap = int(handicap)
        # shaping potential: net_worth_t values what you hold; future_worth_t
        # (Kilo's future-credit formula) values what the state will deliver.
        # opp_lambda subtracts the opponent's potential delta -- the relative
        # form; lambda=1.0 per-step zero-sum is the archived negative result,
        # so it ships OFF and graded values are for A/Bs.
        if potential == "networth":
            self._pot = potential_t.net_worth_t
        elif potential == "future":
            import potential_future
            lv = float(land_value) or potential_future.LAND_VALUE
            pc = float(plant_credit) or potential_future.PLANT_CREDIT
            ac = float(animal_credit) or potential_future.ANIMAL_CREDIT
            self._pot = lambda ep, p: potential_future.future_worth_t(
                ep, p, land_value=lv, plant_credit=pc, animal_credit=ac)
        elif potential == "future-mkt":
            # future-credit with the HOARDING SUBSIDY removed: shed stock
            # valued at min(current market price, base) x 0.9, so selling
            # below base stops being punished at the moment of sale (the
            # documented hack: five runs held 62-100 melons because the
            # potential priced dead inventory at 48x its market value)
            import potential_future
            lv = float(land_value) or potential_future.LAND_VALUE
            pc = float(plant_credit) or potential_future.PLANT_CREDIT
            ac = float(animal_credit) or potential_future.ANIMAL_CREDIT
            self._pot = lambda ep, p: potential_future.future_worth_t(
                ep, p, shed_at_market=True, land_value=lv,
                plant_credit=pc, animal_credit=ac)
        else:
            raise ValueError(f"unknown potential {potential!r}")
        # Ng-correct shaping: r = gamma*phi(s') - phi(s). The plain
        # difference leaks (1-gamma)*phi per step -- an annuity for
        # HOLDING high-phi assets that summed to more than the win bonus
        # over a season (~4.8 units at phi~20k). 0 keeps the legacy
        # difference; set it to the training gamma to close the leak.
        self.shape_gamma = float(shape_gamma)
        self.shape_scale = float(shape_scale)
        self.opp_lambda = float(opp_lambda)
        # build-curve credit folded into the potential: rides the same
        # _prev_w differencing, reset init and opp_lambda paths
        self.build_bonus = float(build_bonus)
        if self.build_bonus > 0.0:
            f64 = torch.float64
            tabs = (torch.tensor(_BUILD_ANIMALS, dtype=f64, device=device),
                    torch.tensor(_BUILD_LAND, dtype=f64, device=device),
                    torch.tensor(_BUILD_HANDS, dtype=f64, device=device),
                    torch.tensor(_BUILD_CROPS, dtype=f64, device=device))
            base_pot, bb = self._pot, self.build_bonus

            def _pot_build(ep, player):
                return base_pot(ep, player) + bb * build_phi(ep, player, tabs)

            self._pot = _pot_build
        # fertilizer-stream credit: every placed animal accrues a daily
        # fertilizer (fert_avail) that neither potential priced, yet it is
        # the top meta's #1 income line (29.7% of the 231k anatomy). Each
        # animal carries w x base x remaining-days of stream value; being
        # a potential, escapes surrender it.
        self.fert_credit = float(fert_credit)
        if self.fert_credit > 0.0:
            base_pot_f, fc = self._pot, self.fert_credit
            fbase = float(A.R.MARKET_PARAMS["FERTILIZER"]["base"])

            def _pot_fert(ep, player):
                day = min(29, ep._step // ep.turns_per_day)
                n_a = (ep.animal[:, player] >= 0).sum((-1, -2)).to(
                    torch.float64)
                return (base_pot_f(ep, player)
                        + fc * fbase * (30.0 - day) * n_a)

            self._pot = _pot_fert
        self._prev_wo = None
        self.opp_fn = _make_opponent(opponent, self.device)
        # when set (e.g. trl_pool.OpponentPool.sample), called at every reset
        # to pick the next episode batch's opponent
        self.opponent_sampler = None
        self._ep = None
        self._episode_index = 0
        self._prev_w = None
        # One-step raw action grafts used by paired macro audits. They are
        # consumed by the next _step and leave the normal training path idle.
        self._step_overrides = []
        # backplay: comma-separated bank files (make_bank.py). A banked
        # reset restores mid-game barnyard-vs-barnyard states into the
        # fresh batch (random bank lanes -> env lanes), so the win signal
        # exists long before the policy can build day 0 -> 29 itself.
        # Bank choice and lane draw derive from (base_seed, episode_index)
        # -- deterministic, so --resume replays the same stream.
        self.bank_frac = float(bank_frac)
        self._banks = []
        if bank:
            import bank_t
            self._bank_mod = bank_t
            for path in str(bank).split(","):
                if path.strip():
                    self._banks.append(
                        torch.load(path.strip(), map_location=self.device,
                                   weights_only=False))

        # A named barnyard profile is a state-closed teacher on the learner's
        # own states.  It is separate from fixed_market_profile so the target
        # labels cannot mutate the executor that supplies real market orders.
        if kickstart and not (kickstart == "barnyard"
                              or kickstart.startswith("barnyard:")):
            raise ValueError(f"unknown kickstart teacher {kickstart!r}")
        self.kickstart = kickstart
        self._kickstart_executor = None
        self._kickstart_profile = ""
        if kickstart.startswith("barnyard:"):
            import barnyard_t
            profile = kickstart.split(":", 1)[1]
            if not profile:
                raise ValueError("barnyard kickstart profile must not be empty")
            self._kickstart_profile = profile
            self._kickstart_executor = barnyard_t.BarnyardOpponent(profile)
        # label every Nth step only: the profiler puts the teacher at 41%
        # of step time (a full barnyard compute per step); -1-filled steps
        # are skipped by the CE, so this trades label density for ~1.7x
        # collection throughput at ks_every=4
        self.ks_every = max(1, int(ks_every))
        self.fixed_market_profile = str(fixed_market_profile)
        self._fixed_market_planted = None
        # --fixed-farm-tape: the mirror image of fixed_market_profile. The farm
        # program (farmer + every hand slot) is grafted from a recorded tape at
        # the RAW op level, so only the market head can influence the reward.
        # Refused together with fixed_market_profile: with both grafted there
        # is nothing left for the policy to affect.
        self.fixed_farm_tape = str(fixed_farm_tape)
        self._farm_tape = None
        if self.fixed_farm_tape:
            if self.fixed_market_profile:
                raise ValueError(
                    "fixed_farm_tape and fixed_market_profile together graft "
                    "the whole action, leaving nothing trainable")
            if not multi_head:
                raise ValueError("fixed_farm_tape needs multi_head=True: the "
                                 "hand slots have to be graftable too, and "
                                 "without it they run the scripted cascade")
            import tape_t
            tab = tape_t.compile_trace(
                tape_t.load_trace(self.fixed_farm_tape), str(device))
            # Pad the hand block out to MAX_HANDS with PASS. A tape shorter
            # than MAX_HANDS would otherwise leave its tail slots carrying the
            # POLICY's decoded hand tasks, which would leak the policy back
            # into the farm program and quietly break the whole premise.
            H = tab["H"]
            if H < A.MAX_HANDS:
                pad = torch.zeros((tab["T"], A.MAX_HANDS - H, 3),
                                  dtype=torch.int64, device=tab["h"].device)
                tab["h"] = torch.cat([tab["h"], pad], 1)
                tab["H"] = A.MAX_HANDS
            # The tape's OWN market orders. A frozen farm program is not
            # independent of its market layer: PLANT consumes a seed the
            # market bought, FEED a product, CARE an animal, the outer
            # quadrants land, the hands a HIRE. Measured 2026-09-04 on this
            # very tape -- graft the farm with a silent market and the learner
            # ends the season on exactly its 3,000 of starting capital with
            # ZERO standing crops, while the same tape with its own market
            # makes 161,586. Graft the buys and it produces (peak 18 standing
            # crops) but earns 0 because it never sells; graft everything and
            # it is the tape, 82,019 against the tape's own 82,148.
            #   "none"  -- market entirely the policy's (the farm goes inert)
            #   "buys"  -- non-SELL orders grafted, SELL left to the policy.
            #              This is the one that matches what the third-party
            #              layer actually contributes: wrap.py's docstring
            #              says it "only reorders within the market slots the
            #              plan already used for selling".
            #   "all"   -- the whole tape; nothing trainable, for the ceiling
            if farm_tape_market not in ("none", "buys", "all"):
                raise ValueError(f"farm_tape_market={farm_tape_market!r}")
            self.farm_tape_market = farm_tape_market
            m = tab["m"].clone()                              # (T, S, 3)
            if farm_tape_market == "buys":
                m[m[..., 0] == engine_t.OP_SELL] = 0
            elif farm_tape_market == "none":
                m.zero_()
            tab["m_graft"] = m
            self._farm_tape = tab
        self._pending_teacher_ops = None
        self.kickstart_force = False
        # multi-head action space (rl/TODO.md #0): [farmer, market, hand x12]
        self.multi_head = bool(multi_head)
        bs, dev = self.batch_size, self.device
        obs_entries = dict(
            observation=Unbounded(shape=(*bs, O.OBS_DIM),
                                  dtype=torch.float32, device=dev),
            farmer_mask=Binary(n=A.N_FARMER, shape=(*bs, A.N_FARMER),
                               dtype=torch.bool, device=dev),
            market_mask=Binary(n=A.N_MARKET, shape=(*bs, A.N_MARKET),
                               dtype=torch.bool, device=dev),
            money=Unbounded(shape=(*bs,), dtype=torch.float64, device=dev),
            opp_money=Unbounded(shape=(*bs,), dtype=torch.float64, device=dev))
        nvec = [A.N_FARMER, A.N_MARKET]
        if self.multi_head:
            obs_entries["hand_mask"] = Binary(
                n=A.N_HAND_TASK, shape=(*bs, A.MAX_HANDS, A.N_HAND_TASK),
                dtype=torch.bool, device=dev)
            nvec = nvec + [A.N_HAND_TASK] * A.MAX_HANDS
        if self.kickstart:
            obs_entries["teacher_f"] = Unbounded(
                shape=(*bs,), dtype=torch.int64, device=dev)
            obs_entries["teacher_m"] = Unbounded(
                shape=(*bs,), dtype=torch.int64, device=dev)
            obs_entries["teacher_h"] = Unbounded(
                shape=(*bs, A.MAX_HANDS), dtype=torch.int64, device=dev)
        self.observation_spec = Composite(obs_entries, shape=bs, device=dev)
        self.action_spec = MultiCategorical(
            nvec=nvec, shape=(*bs, len(nvec)), dtype=torch.int64, device=dev)
        self.reward_spec = Unbounded(shape=(*bs, 1), dtype=torch.float32,
                                     device=dev)
        self.full_done_spec = Composite(
            done=Binary(n=1, shape=(*bs, 1), dtype=torch.bool, device=dev),
            terminated=Binary(n=1, shape=(*bs, 1), dtype=torch.bool,
                              device=dev),
            shape=bs, device=dev)

    # -- helpers -------------------------------------------------------------

    def _obs_td(self):
        ep, seat = self._ep, self.seat
        x = features_t.encode_t(ep, seat)
        fm, mm = features_t.masks_t(ep, seat)
        out = {"observation": x, "farmer_mask": fm, "market_mask": mm,
               "money": ep.money[:, seat].clone(),
               "opp_money": ep.money[:, 1 - seat].clone()}
        if self.multi_head:
            out["hand_mask"] = hand_task_mask_t(ep, seat, A.MAX_HANDS)
        if self.fixed_market_profile:
            # The route owns every market order, including compound baskets.
            # Give PPO a one-action market distribution so its entropy and
            # policy gradient are spent only on the learned execution heads.
            out["market_mask"].zero_()
            out["market_mask"][:, 0] = True
        if self.kickstart:
            teacher_ops = None
            if self._kickstart_executor is not None:
                if (self._kickstart_profile == self.fixed_market_profile
                        and self._fixed_market_planted is not None):
                    self._kickstart_executor.planted_total.copy_(
                        self._fixed_market_planted)
                teacher_ops = self._kickstart_executor(ep, seat)
                self._pending_teacher_ops = teacher_ops
            if ep._step % self.ks_every == 0:
                tf, tm, th = kickstart_labels(ep, seat, teacher_ops)
            else:
                tf = torch.full((self.B,), -1, dtype=torch.int64,
                                device=self.device)
                tm = tf.clone()
                th = torch.full((self.B, A.MAX_HANDS), -1, dtype=torch.int64,
                                device=self.device)
            out["teacher_f"], out["teacher_m"], out["teacher_h"] = tf, tm, th
        return TensorDict(out, batch_size=self.batch_size, device=self.device)

    def queue_step_override(self, seat, ops, lane_mask=None):
        """Queue one raw step_idx graft, optionally for selected lanes."""
        self._step_overrides.append((int(seat), ops, lane_mask))

    # -- EnvBase hooks -------------------------------------------------------

    def _reset(self, tensordict, **kwargs):
        if tensordict is not None and "_reset" in tensordict.keys():
            assert bool(tensordict["_reset"].all()), \
                "lanes terminate in lockstep; partial resets cannot happen"
        if self.alternate_seat and self._episode_index > 0:
            self.seat = 1 - self.seat
        if self.opponent_sampler is not None:
            self.opp_fn = self.opponent_sampler()
        seeds = [self.base_seed * 1_000_003 + self._episode_index * self.B + i
                 for i in range(self.B)]
        self._episode_index += 1
        self._ep = engine_t.EpisodeT(seeds, episode_steps=self.episode_steps,
                                     device=self.device)
        self._step_overrides.clear()
        self._pending_teacher_ops = None
        if self._banks:
            r = ((self._episode_index * 40503 + self.base_seed) % 997) / 997.0
            if r < self.bank_frac:
                g = torch.Generator().manual_seed(
                    self.base_seed * 7919 + self._episode_index)
                bk = self._banks[int(torch.randint(len(self._banks), (1,),
                                                   generator=g))]
                nb = bk["state"]["__B__"]
                src = torch.randint(nb, (self.B,), generator=g)
                self._bank_mod.restore_lanes(self._ep, bk["state"], src)
        if self.handicap:
            self._ep.money[:, self.seat] += float(self.handicap)
        if self.fixed_market_profile:
            current = self._ep.kind[:, self.seat].reshape(self.B, -1) \
                == engine_t.K_PLANT
            crop = self._ep.crop[:, self.seat].reshape(self.B, -1)
            self._fixed_market_planted = torch.stack(
                [(current & (crop == c)).sum(1)
                 for c in range(len(engine_t.CROP_NAMES))], 1).to(torch.int64)
        if self._kickstart_executor is not None:
            self._kickstart_executor.reset(self._ep, self.seat)
        self._prev_w = self._pot(self._ep, self.seat)
        if self.opp_lambda:
            self._prev_wo = self._pot(self._ep, 1 - self.seat)
        return self._obs_td()

    def _step(self, tensordict):
        ep, seat = self._ep, self.seat
        opp = 1 - seat
        step_overrides = self._step_overrides
        self._step_overrides = []
        action = tensordict["action"]
        fa, ma = action[..., 0], action[..., 1]
        h_idx = None
        if self.multi_head:
            h_idx = torch.zeros((self.B, 2, A.MAX_HANDS), dtype=torch.int64,
                                device=self.device)
            h_idx[:, seat] = action[..., 2:]
        if self.kickstart_force:
            tf = tensordict["teacher_f"]
            tf_safe = tf.clamp(min=0)
            f_legal = ((tf >= 0)
                       & tensordict["farmer_mask"].gather(
                           -1, tf_safe.unsqueeze(-1)).squeeze(-1))
            fa = torch.where(f_legal, tf_safe, fa)
            th = tensordict["teacher_h"]
            th_safe = th.clamp(min=0)
            h_legal = ((th >= 0)
                       & tensordict["hand_mask"].gather(
                           -1, th_safe.unsqueeze(-1)).squeeze(-1))
            h_idx[:, seat] = torch.where(
                h_legal, th_safe, h_idx[:, seat])
        if self.fixed_market_profile:
            import barnyard_t
            before_kind = ep.kind[:, seat].clone()
            before_crop = ep.crop[:, seat].clone()
            before_planted = ep.planted_day[:, seat].clone()
            if (self._kickstart_profile == self.fixed_market_profile
                    and self._pending_teacher_ops is not None):
                market_plan = self._pending_teacher_ops
            else:
                market_plan = barnyard_t.compute(
                    ep, seat, profile=self.fixed_market_profile,
                    planted_total=self._fixed_market_planted)
            self._pending_teacher_ops = None
            step_overrides.append((seat, {
                key: market_plan[key]
                for key in ("m_op", "m_item", "m_rem")
            }))
        if self._farm_tape is not None:
            tab = self._farm_tape
            t = min(ep._step, tab["T"] - 1)
            f = tab["f"][t]
            h = tab["h"][t]
            B = self.B
            ops = {
                "f_op": f[0].expand(B).clone(),
                "f_arg": f[1].expand(B).clone(),
                "f_qty": f[2].expand(B).clone(),
                "h_op": [h[u, 0].expand(B).clone() for u in range(tab["H"])],
                "h_arg": [h[u, 1].expand(B).clone() for u in range(tab["H"])],
                "h_qty": [h[u, 2].expand(B).clone() for u in range(tab["H"])],
            }
            mg = tab["m_graft"][t]                            # (S, 3)
            if bool((mg[:, 0] != engine_t.OP_DEAD).any()):
                S = ep.max_market_orders
                blk = torch.zeros((B, S, 3), dtype=torch.int64,
                                  device=self.device)
                k = min(S, mg.shape[0])
                blk[:, :k] = mg[:k].unsqueeze(0)
                ops["m_add"] = blk                # MERGE, not replace
            step_overrides.append((seat, ops))
        if getattr(self.opp_fn, "provides_ops", False):
            # raw-encoding opponent (barnyard_t): its seat bypasses the
            # macro decode via the step_idx override. --opp-noise here is
            # ACTION-DROP noise: on a noisy lane the opponent's units PASS
            # and its market goes silent this step -- a tempo handicap
            # that weakens the wall without touching its identity (the
            # macro-path random-legal replacement cannot reach raw ops)
            ops = self.opp_fn(ep, opp)
            if self.opp_noise > 0.0:
                import engine_t_idx as X
                assert X.U_PASS == 0 and engine_t.OP_DEAD == 0
                noisy = (torch.rand(self.B, device=self.device)
                         < self.opp_noise)
                if bool(noisy.any()):
                    nz2 = noisy.view(-1, 1)
                    for k in ("f_op", "f_arg", "f_qty"):
                        ops[k] = torch.where(noisy, torch.zeros_like(ops[k]),
                                             ops[k])
                    for k in ("h_op", "h_arg", "h_qty"):
                        ops[k] = [torch.where(noisy, torch.zeros_like(v), v)
                                  for v in ops[k]]
                    for k in ("m_op", "m_item", "m_rem"):
                        ops[k] = torch.where(nz2, torch.zeros_like(ops[k]),
                                             ops[k])
            f_idx = torch.zeros((self.B, 2), dtype=torch.int64,
                                device=self.device)
            m_idx = torch.zeros_like(f_idx)
            f_idx[:, seat] = fa
            m_idx[:, seat] = ma
            overrides = [(opp, ops), *step_overrides]
            ep.step_idx(f_idx, m_idx, override=overrides, h_idx=h_idx)
            if self.fixed_market_profile:
                self._record_fixed_market_plants(
                    before_kind, before_crop, before_planted)
            return self._finish_step(ep, seat, opp)
        res = self.opp_fn(ep, opp)
        if len(res) == 3:
            # a multi-head snapshot/export plays its hand heads too -- an
            # AUTO fallback here would silently be a different policy
            ofa, oma, oha = res
            if h_idx is None:
                h_idx = torch.zeros((self.B, 2, A.MAX_HANDS),
                                    dtype=torch.int64, device=self.device)
            h_idx[:, opp, :oha.shape[-1]] = oha
        else:
            ofa, oma = res
        if self.opp_noise > 0.0:
            ofm, omm = features_t.masks_t(ep, opp)
            noisy = torch.rand(ofa.shape, device=self.device) < self.opp_noise
            rfa = torch.multinomial(ofm.double(), 1).squeeze(-1)
            rma = torch.multinomial(omm.double(), 1).squeeze(-1)
            ofa = torch.where(noisy, rfa, ofa)
            oma = torch.where(noisy, rma, oma)
        if seat == 0:
            f_idx = torch.stack([fa, ofa], 1)
            m_idx = torch.stack([ma, oma], 1)
        else:
            f_idx = torch.stack([ofa, fa], 1)
            m_idx = torch.stack([oma, ma], 1)
        ep.step_idx(f_idx, m_idx, override=step_overrides or None, h_idx=h_idx)
        if self.fixed_market_profile:
            self._record_fixed_market_plants(
                before_kind, before_crop, before_planted)
        return self._finish_step(ep, seat, opp)

    def _record_fixed_market_plants(self, before_kind, before_crop,
                                    before_planted):
        """Advance the market plan from plants that actually reached state."""
        kind = self._ep.kind[:, self.seat]
        crop = self._ep.crop[:, self.seat]
        planted = self._ep.planted_day[:, self.seat]
        is_plant = kind == engine_t.K_PLANT
        new = (is_plant & ((before_kind != engine_t.K_PLANT)
                           | (crop != before_crop)
                           | (planted != before_planted)))
        for crop_i in range(len(engine_t.CROP_NAMES)):
            self._fixed_market_planted[:, crop_i].add_(
                (new & (crop == crop_i)).sum((-1, -2)))

    def _finish_step(self, ep, seat, opp):
        g = self.shape_gamma if self.shape_gamma > 0.0 else 1.0
        w = self._pot(ep, seat)
        r = (g * w - self._prev_w) * (1.0 / self.shape_scale)
        self._prev_w = w
        if self.opp_lambda:
            wo = self._pot(ep, opp)
            r = r - self.opp_lambda * (g * wo - self._prev_wo) * (1.0 / self.shape_scale)
            self._prev_wo = wo
        if ep.done:
            mine, theirs = ep.money[:, seat], ep.money[:, opp]
            if self.win_bonus:
                win = ((mine > theirs).to(torch.float64)
                       - (mine < theirs).to(torch.float64))
                r = r + self.win_bonus * win
            if self.margin_bonus:
                r = r + self.margin_bonus * torch.tanh(
                    (mine - theirs) / self.margin_scale)
        out = self._obs_td()
        done = torch.full((*self.batch_size, 1), ep.done, dtype=torch.bool,
                          device=self.device)
        out["reward"] = r.to(torch.float32).unsqueeze(-1)
        out["done"] = done
        out["terminated"] = done
        return out

    def _set_seed(self, seed):
        if seed is not None:
            self.base_seed = int(seed)
        return seed
