"""TorchRL EnvBase over engine_t.EpisodeT: the device-agnostic batched env.

One KGTensorEnv is B lockstep two-player episodes with the learner on one
seat and a scripted/frozen opponent on the other, exposed as a single-agent
TorchRL environment of batch_size [B] (the VMAS/Brax pattern: the simulator
itself is the vectorization; no ParallelEnv processes anywhere). The same
class runs on CPU and CUDA -- `device` is the only switch, which is what
finally merges the rl-baseline (CPU) and tensorize (GPU) lines.

Semantics are train_t.py's collect() verbatim:
  * obs        = features_t.encode_t(ep, seat)            (B, 4867) float32
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
    cf8 = X._tabs(dev).crop_first_i8[ep.crop[:, player].reshape(B, NN).int()]
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
    mask[:, :, -1] = (alive & (shed_wheat.view(B, 1) | hand_wheat)
                      & unfed_any.view(B, 1))
    return mask


# ---- kickstart teacher labels (Schmitt et al. 2018 / Lux-S1 recipe) --------
# barnyard_t's per-unit INTENTS (ops["task"/"task_arg"]) mapped into the
# policy's head vocabulary, queried on the LEARNER's own states -- teacher
# supervision without the distribution shift that killed the old line's BC.
# Lossy by measurement, not accident: per-hand plant/place/build fall back
# to AUTO (~7% of barnyard's hand work), the metered multi-order market
# collapses to one priority-picked head index.

_KS_LUTS = {}


def _ks_luts(device):
    import engine_t_idx as X
    key = str(device)
    if key not in _KS_LUTS:
        i64 = torch.int64
        hand = [0] * 18                     # default AUTO
        hand[X.U_PASS] = 1                  # unassigned unit: barnyard idles it
        hand[X.U_HARVEST] = A.HAND_TASKS.index("HARVEST")
        hand[X.U_WATER] = A.HAND_TASKS.index("WATER")
        hand[X.U_CARE] = A.HAND_TASKS.index("CARE")
        hand[X.U_COLLECT] = A.HAND_TASKS.index("COLLECT_FERTILIZER")
        hand[X.U_DIG] = A.HAND_TASKS.index("DIG")
        hand[X.U_FEED] = A.HAND_TASKS.index("FEED")
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
        _KS_LUTS[key] = {
            "hand": torch.tensor(hand, dtype=i64, device=device),
            "farmer": torch.tensor(farmer, dtype=i64, device=device)}
    return _KS_LUTS[key]


def kickstart_labels(ep, player):
    """(teacher_f (B,), teacher_m (B,), teacher_h (B, MAX_HANDS)) int64 --
    barnyard's decision on `player`'s seat in head-index vocabulary.
    Dead hand slots carry -1 (the CE loss skips them)."""
    import barnyard_t
    import engine_t_idx as X
    dev, B = ep.device, ep.B
    ops = barnyard_t.compute(ep, player)
    task, targ = ops["task"], ops["task_arg"]                  # (B, U)
    luts = _ks_luts(dev)
    f = luts["farmer"][task[:, 0]]
    f = torch.where(task[:, 0] == X.U_PLANT, 15 + targ[:, 0], f)
    f = torch.where(task[:, 0] == X.U_PLACE, 20 + targ[:, 0], f)
    h = luts["hand"][task[:, 1:]]                              # (B, U-1)
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
            return sd

        self.net = self._net_from_sd(net_sd(), device)
        self.delta = None
        if any(str(k).startswith("d_") for k in arrays):
            self.delta = self._net_from_sd(net_sd("d_"), device)
        # multi-head exports carry a hands head on exactly one trunk; the
        # snapshot must play it, never silently fall back to AUTO
        self._hands = None
        for pfx, owner in (("", "net"), ("d_", "delta")):
            if f"{pfx}hw" in arrays:
                self._hands = (owner,
                               torch.as_tensor(arrays[f"{pfx}hw"]).to(device),
                               torch.as_tensor(arrays[f"{pfx}hb"]).to(device))

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
        ma = ml.masked_fill(~mm, NEG).argmax(-1)
        if self._hands is None:
            return fa, ma
        hl = self._hand_logits(x)
        hm = hand_task_mask_t(ep, player, hl.shape[-2])
        ha = hl.masked_fill(~hm, NEG).argmax(-1)
        return fa, ma, ha


def _make_opponent(spec, device):
    if spec == "starter" or spec is None:
        return opponents_t.starter_indices
    if spec == "barnyard":
        import barnyard_t
        return barnyard_t.BarnyardOpponent()
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


def build_phi(ep, player, tabs):
    """(B,) float64: curve-capped build credit for one seat."""
    day = min(29, ep._step // ep.turns_per_day)
    a = (ep.animal[:, player] >= 0).sum((-1, -2)).to(torch.float64)
    land = ep.quad_unlocked[:, player].to(torch.float64).sum(-1)
    hands = ep.hands_n[:, player].to(torch.float64)
    ta, tl, th = tabs[0][day], tabs[1][day], tabs[2][day]
    return (400.0 * torch.clamp(a, max=ta)
            + 1000.0 * torch.clamp(land - 1.0, min=0.0, max=tl - 1.0)
            + 100.0 * torch.clamp(hands, max=th))


class KGTensorEnv(EnvBase):
    batch_locked = True

    def __init__(self, B, device="cpu", seat=0, alternate_seat=False,
                 episode_steps=720, base_seed=0, opponent="starter",
                 win_bonus=3.0, margin_bonus=0.0, margin_scale=30000.0,
                 opp_noise=0.0, handicap=0, potential="networth",
                 shape_scale=3000.0, opp_lambda=0.0, multi_head=False,
                 kickstart="", build_bonus=0.0, bank="", bank_frac=0.5,
                 shape_gamma=0.0, ks_every=1):
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
            self._pot = potential_future.future_worth_t
        elif potential == "future-mkt":
            # future-credit with the HOARDING SUBSIDY removed: shed stock
            # valued at min(current market price, base) x 0.9, so selling
            # below base stops being punished at the moment of sale (the
            # documented hack: five runs held 62-100 melons because the
            # potential priced dead inventory at 48x its market value)
            import potential_future
            self._pot = lambda ep, p: potential_future.future_worth_t(
                ep, p, shed_at_market=True)
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
                    torch.tensor(_BUILD_HANDS, dtype=f64, device=device))
            base_pot, bb = self._pot, self.build_bonus

            def _pot_build(ep, player):
                return base_pot(ep, player) + bb * build_phi(ep, player, tabs)

            self._pot = _pot_build
        self._prev_wo = None
        self.opp_fn = _make_opponent(opponent, self.device)
        # when set (e.g. trl_pool.OpponentPool.sample), called at every reset
        # to pick the next episode batch's opponent
        self.opponent_sampler = None
        self._ep = None
        self._episode_index = 0
        self._prev_w = None
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

        # kickstart teacher: "" (off) or "barnyard" -- every learner-seat
        # state gets barnyard's mapped decision alongside the observation
        if kickstart not in ("", "barnyard"):
            raise ValueError(f"unknown kickstart teacher {kickstart!r}")
        self.kickstart = kickstart
        # label every Nth step only: the profiler puts the teacher at 41%
        # of step time (a full barnyard compute per step); -1-filled steps
        # are skipped by the CE, so this trades label density for ~1.7x
        # collection throughput at ks_every=4
        self.ks_every = max(1, int(ks_every))
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
        if self.kickstart:
            if ep._step % self.ks_every == 0:
                tf, tm, th = kickstart_labels(ep, seat)
            else:
                tf = torch.full((self.B,), -1, dtype=torch.int64,
                                device=self.device)
                tm = tf.clone()
                th = torch.full((self.B, A.MAX_HANDS), -1, dtype=torch.int64,
                                device=self.device)
            out["teacher_f"], out["teacher_m"], out["teacher_h"] = tf, tm, th
        return TensorDict(out, batch_size=self.batch_size, device=self.device)

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
        self._prev_w = self._pot(self._ep, self.seat)
        if self.opp_lambda:
            self._prev_wo = self._pot(self._ep, 1 - self.seat)
        return self._obs_td()

    def _step(self, tensordict):
        ep, seat = self._ep, self.seat
        opp = 1 - seat
        action = tensordict["action"]
        fa, ma = action[..., 0], action[..., 1]
        h_idx = None
        if self.multi_head:
            h_idx = torch.zeros((self.B, 2, A.MAX_HANDS), dtype=torch.int64,
                                device=self.device)
            h_idx[:, seat] = action[..., 2:]
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
            ep.step_idx(f_idx, m_idx, override=(opp, ops), h_idx=h_idx)
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
        ep.step_idx(f_idx, m_idx, h_idx=h_idx)
        return self._finish_step(ep, seat, opp)

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
